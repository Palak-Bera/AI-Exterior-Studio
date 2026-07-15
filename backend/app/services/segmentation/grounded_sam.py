"""Grounded-SAM backend - Grounding DINO (tiny) + SAM (vit-base), CPU friendly.

Grounding DINO turns category text prompts into boxes; SAM turns each box into a
pixel mask in a single forward pass. Walls are derived (building minus openings).
"""
from __future__ import annotations

import importlib.util
import threading
import time

import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.segmentation.base import BackendUnavailable, CategoryMask, SegBackend
from app.services.segmentation.common import (
    clean_mask,
    derive_wall,
    fallback_building,
    match_category,
)
from app.utils.categories import CATEGORIES, OPENING_CATEGORIES
from app.utils.model_paths import resolve_model_source

logger = get_logger("segmentation.grounded_sam")


class GroundedSamBackend(SegBackend):
    name = "grounded_sam"

    _instance: "GroundedSamBackend | None" = None
    _lock = threading.Lock()
    _loaded = False

    def is_available(self) -> bool:
        return (
            importlib.util.find_spec("torch") is not None
            and importlib.util.find_spec("transformers") is not None
        )

    @classmethod
    def instance(cls) -> "GroundedSamBackend":
        with cls._lock:
            if cls._instance is None:
                cls._instance = GroundedSamBackend()
            return cls._instance

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                import torch
                from transformers import (
                    AutoModelForZeroShotObjectDetection,
                    AutoProcessor,
                    SamModel,
                    SamProcessor,
                )
            except Exception as exc:  # noqa: BLE001
                raise BackendUnavailable(
                    "Grounded-SAM failed to import torch/transformers/torchvision: "
                    f"{exc}. Install matching CPU wheels: "
                    "pip install torch==2.5.1 torchvision==0.20.1 "
                    "--index-url https://download.pytorch.org/whl/cpu"
                ) from exc

            if settings.TORCH_THREADS > 0:
                torch.set_num_threads(settings.TORCH_THREADS)
            logger.info("Loading Grounded-SAM on CPU (torch_threads=%s)...",
                        torch.get_num_threads())

            self.torch = torch
            self.device = "cpu"

            try:
                t0 = time.perf_counter()
                dino_src = resolve_model_source(settings.GROUNDING_DINO_MODEL)
                logger.info("Loading Grounding DINO: %s", dino_src)
                self.dino_processor = AutoProcessor.from_pretrained(dino_src)
                self.dino = AutoModelForZeroShotObjectDetection.from_pretrained(
                    dino_src
                ).to(self.device).eval()
                logger.info("Grounding DINO ready (%.1fs)", time.perf_counter() - t0)

                t1 = time.perf_counter()
                sam_src = resolve_model_source(settings.SAM_MODEL)
                logger.info("Loading SAM: %s", sam_src)
                self.sam_processor = SamProcessor.from_pretrained(sam_src)
                self.sam = SamModel.from_pretrained(sam_src).to(self.device).eval()
                logger.info("SAM ready (%.1fs) | Grounded-SAM total %.1fs",
                            time.perf_counter() - t1, time.perf_counter() - t0)
                self._loaded = True
            except BackendUnavailable:
                raise
            except Exception as exc:  # noqa: BLE001
                raise BackendUnavailable(
                    f"Grounded-SAM weights failed to load: {exc}"
                ) from exc

    def warmup(self) -> None:
        self._ensure_loaded()

    def is_loaded(self) -> bool:
        return self._loaded

    def unload(self) -> None:
        with self._lock:
            if not self._loaded:
                return
            for attr in ("dino", "sam", "dino_processor", "sam_processor", "torch"):
                if hasattr(self, attr):
                    delattr(self, attr)
            self._loaded = False
            import gc

            gc.collect()
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:  # noqa: BLE001
                pass
            logger.info("Grounded-SAM unloaded (RAM freed)")

    def _detect(self, image: Image.Image, phrases: list[str]) -> list[dict]:
        text = ". ".join(phrases) + "."
        inputs = self.dino_processor(images=image, text=text.lower(), return_tensors="pt")
        with self.torch.no_grad():
            outputs = self.dino(**inputs)
        results = self.dino_processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            box_threshold=settings.BOX_THRESHOLD,
            text_threshold=settings.TEXT_THRESHOLD,
            target_sizes=[image.size[::-1]],
        )[0]
        dets = []
        labels = results.get("labels") or results.get("text_labels") or []
        for box, score, label in zip(results["boxes"], results["scores"], labels):
            dets.append({
                "box": [float(v) for v in box.tolist()],
                "score": float(score),
                "label": str(label),
            })
        return dets

    def _masks_for_boxes(self, image: Image.Image, boxes: list[list[float]]) -> list[np.ndarray]:
        if not boxes:
            return []
        inputs = self.sam_processor(image, input_boxes=[boxes], return_tensors="pt")
        with self.torch.no_grad():
            outputs = self.sam(**inputs)
        masks = self.sam_processor.image_processor.post_process_masks(
            outputs.pred_masks.cpu(),
            inputs["original_sizes"].cpu(),
            inputs["reshaped_input_sizes"].cpu(),
        )[0]
        iou = outputs.iou_scores.cpu()[0]
        best = iou.argmax(dim=1)
        return [masks[i, best[i]].numpy().astype(np.uint8) for i in range(masks.shape[0])]

    def segment(self, image: Image.Image, categories: list[str]) -> dict[str, CategoryMask]:
        self._ensure_loaded()
        w, h = image.size
        need_wall = "wall" in categories
        detect_cats = [c for c in categories if c != "wall"]
        if need_wall:
            detect_cats = list(dict.fromkeys(detect_cats + OPENING_CATEGORIES))

        phrase_map: dict[str, str] = {}
        phrases: list[str] = []
        for cat in detect_cats:
            for p in CATEGORIES[cat]["prompts"]:
                phrase_map[p.lower()] = cat
                phrases.append(p)
        if need_wall:
            phrases.append("building")

        logger.info("Detecting on %dx%d with prompts=%s", w, h, phrases)
        t0 = time.perf_counter()
        dets = self._detect(image, phrases)
        logger.info("Grounding DINO found %d boxes (%.1fs)", len(dets), time.perf_counter() - t0)
        if not dets:
            logger.warning("No detections above threshold - returning empty result")
            return {}

        t1 = time.perf_counter()
        masks = self._masks_for_boxes(image, [d["box"] for d in dets])
        logger.info("SAM produced %d masks (%.1fs)", len(masks), time.perf_counter() - t1)

        per_cat: dict[str, list[tuple[np.ndarray, float]]] = {}
        building = np.zeros((h, w), np.uint8)
        for det, mask in zip(dets, masks):
            label = det["label"].lower().strip()
            if "building" in label or "facade" in label:
                building = np.maximum(building, mask)
                continue
            cat = match_category(label, phrase_map)
            if cat is not None:
                per_cat.setdefault(cat, []).append((mask, det["score"]))

        result: dict[str, CategoryMask] = {}
        openings_union = np.zeros((h, w), np.uint8)
        for cat, items in per_cat.items():
            union = np.zeros((h, w), np.uint8)
            for m, _ in items:
                union = np.maximum(union, m)
            if cat in OPENING_CATEGORIES:
                openings_union = np.maximum(openings_union, union)
            if cat in categories:
                result[cat] = CategoryMask(
                    mask=clean_mask(union),
                    confidence=float(np.mean([s for _, s in items])),
                    instance_count=len(items),
                )

        if need_wall:
            if building.sum() == 0:
                logger.info("No 'building' box - deriving silhouette via GrabCut")
                building = fallback_building(image)
            wall_conf = float(np.mean([d["score"] for d in dets])) if dets else 0.5
            result["wall"] = CategoryMask(derive_wall(building, openings_union), wall_conf, 1)

        for cat, cm in result.items():
            logger.info("  category=%-8s instances=%d pixels=%d conf=%.3f",
                        cat, cm.instance_count, int(cm.mask.sum()), cm.confidence)
        return result
