"""ControlNet + Stable Diffusion inpainting render backend.

For each material selection, the masked region is repainted from a text prompt
describing the material, while a Canny-edge ControlNet keeps the building's
structure (window frames, edges, rooflines) intact. Unmasked pixels are never
altered - each pass is feather-composited back only inside its mask.

Optional/heavy: requires `diffusers` (see backend/requirements-diffusion.txt).
Runs on CUDA if available, else CPU (slow). Import/lifecycle is guarded so the
rest of the app runs without it.
"""
from __future__ import annotations

import importlib.util
import threading
import time
from typing import Callable

import cv2
import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.rendering.base import RenderBackend, RenderUnavailable
from app.utils.model_paths import is_repo_present, resolve_model_source

logger = get_logger("rendering.controlnet")

# material_key -> prompt fragment describing the finished surface.
_MATERIAL_PROMPTS = {
    "stone": "natural stone cladding wall, realistic stone masonry",
    "tiles": "clean ceramic wall tiles, even grout lines",
    "plaster": "smooth textured plaster wall finish",
}

# render_path fallback when a specific material_key is unknown.
_RENDER_PATH_PROMPTS = {
    "texture": "new wall cladding material",
    "paint": "freshly painted exterior wall",
}

_NEGATIVE_PROMPT = (
    "blurry, low quality, distorted, deformed, extra windows, extra doors, "
    "warped geometry, text, watermark, people, cartoon, unrealistic"
)

# Small nearest-color table so paint hex codes become human words for the prompt.
_COLOR_NAMES = {
    "white": (245, 245, 245), "black": (20, 20, 20), "grey": (128, 128, 128),
    "red": (200, 30, 30), "maroon": (110, 20, 20), "orange": (230, 130, 30),
    "yellow": (230, 210, 40), "cream": (240, 230, 200), "beige": (225, 210, 180),
    "brown": (120, 80, 40), "green": (40, 160, 60), "olive": (120, 130, 50),
    "teal": (30, 130, 130), "blue": (40, 80, 200), "navy": (25, 35, 90),
    "sky blue": (120, 180, 230), "purple": (120, 50, 160), "pink": (230, 130, 170),
    "terracotta": (200, 100, 70),
}


def _nearest_color_name(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        return "neutral"
    best, best_d = "neutral", 1e9
    for name, (cr, cg, cb) in _COLOR_NAMES.items():
        d = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if d < best_d:
            best, best_d = name, d
    return best


def _prompt_for(sel: dict) -> str:
    key = sel.get("material_key")
    if sel.get("render_path") == "paint":
        color = _nearest_color_name(sel.get("color") or "#1E3A8A")
        base = f"{color} painted exterior wall"
    else:
        base = _MATERIAL_PROMPTS.get(key) or _RENDER_PATH_PROMPTS.get(
            sel.get("render_path"), "new wall material"
        )
    return f"{base}, exterior of a house, photorealistic, natural daylight, high detail"


def _round8(x: int) -> int:
    return max(8, (x // 8) * 8)


class ControlNetBackend(RenderBackend):
    name = "controlnet"

    _instance: "ControlNetBackend | None" = None
    _lock = threading.Lock()
    _loaded = False

    def is_available(self) -> bool:
        return (
            importlib.util.find_spec("diffusers") is not None
            and importlib.util.find_spec("torch") is not None
            and is_repo_present(settings.SD_INPAINT_MODEL)
            and is_repo_present(settings.CONTROLNET_MODEL)
        )

    @classmethod
    def instance(cls) -> "ControlNetBackend":
        with cls._lock:
            if cls._instance is None:
                cls._instance = ControlNetBackend()
            return cls._instance

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                import torch
                from diffusers import (
                    ControlNetModel,
                    StableDiffusionControlNetInpaintPipeline,
                )
            except Exception as exc:  # noqa: BLE001
                raise RenderUnavailable(
                    "ControlNet render requires `diffusers` (and torch). Install "
                    "backend/requirements-diffusion.txt to enable this mode."
                ) from exc

            self.torch = torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.dtype = torch.float16 if self.device == "cuda" else torch.float32
            if self.device == "cpu":
                logger.warning("ControlNet running on CPU - expect ~1-3 min per render.")
                if settings.TORCH_THREADS > 0:
                    torch.set_num_threads(settings.TORCH_THREADS)

            t0 = time.perf_counter()
            cn_src = resolve_model_source(settings.CONTROLNET_MODEL)
            sd_src = resolve_model_source(settings.SD_INPAINT_MODEL)
            logger.info("Loading ControlNet %s + inpaint %s (device=%s)...",
                        cn_src, sd_src, self.device)
            try:
                controlnet = ControlNetModel.from_pretrained(
                    cn_src, torch_dtype=self.dtype
                )
                pipe = StableDiffusionControlNetInpaintPipeline.from_pretrained(
                    sd_src,
                    controlnet=controlnet,
                    torch_dtype=self.dtype,
                    safety_checker=None,
                    requires_safety_checker=False,
                )
                pipe = pipe.to(self.device)
                if self.device == "cpu":
                    pipe.enable_attention_slicing()
                    if hasattr(pipe, "enable_vae_slicing"):
                        pipe.enable_vae_slicing()
                self.pipe = pipe
            except Exception as exc:  # noqa: BLE001 - download / load failure
                raise RenderUnavailable(
                    f"ControlNet weights could not be loaded: {exc}"
                ) from exc
            logger.info("ControlNet pipeline ready (%.1fs)", time.perf_counter() - t0)
            self._loaded = True

    def _canny(self, bgr: np.ndarray) -> Image.Image:
        edges = cv2.Canny(bgr, settings.CANNY_LOW, settings.CANNY_HIGH)
        rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        return Image.fromarray(rgb)

    def render(
        self,
        canvas_bgr: np.ndarray,
        selections: list[dict],
        mask_loader: Callable[[str], "np.ndarray | None"],
    ) -> np.ndarray:
        self._ensure_loaded()
        h0, w0 = canvas_bgr.shape[:2]

        # Working resolution for diffusion (multiple of 8).
        longest = max(h0, w0)
        scale = min(1.0, settings.SD_WORKING_LONG_EDGE / longest)
        wr, hr = _round8(int(w0 * scale)), _round8(int(h0 * scale))
        work = cv2.resize(canvas_bgr, (wr, hr), interpolation=cv2.INTER_AREA)
        control = self._canny(work)

        t0 = time.perf_counter()
        changed_union = np.zeros((hr, wr), np.uint8)
        applied = 0
        for sel in selections:
            mask = mask_loader(sel["category"])
            if mask is None or mask.sum() == 0:
                logger.warning("  skip category=%s (no mask pixels)", sel["category"])
                continue
            mask_r = cv2.resize(mask, (wr, hr), interpolation=cv2.INTER_NEAREST)
            if mask_r.sum() == 0:
                continue

            prompt = _prompt_for(sel)
            logger.info("  inpaint category=%s prompt=%r", sel["category"], prompt)

            init_pil = Image.fromarray(cv2.cvtColor(work, cv2.COLOR_BGR2RGB))
            mask_pil = Image.fromarray((mask_r > 0).astype(np.uint8) * 255)

            generator = self.torch.Generator(device=self.device).manual_seed(0)
            result = self.pipe(
                prompt=prompt,
                negative_prompt=_NEGATIVE_PROMPT,
                image=init_pil,
                mask_image=mask_pil,
                control_image=control,
                num_inference_steps=settings.SD_STEPS,
                guidance_scale=settings.SD_GUIDANCE,
                controlnet_conditioning_scale=float(settings.CONTROLNET_SCALE),
                height=hr,
                width=wr,
                generator=generator,
            ).images[0]

            gen_bgr = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
            alpha = cv2.GaussianBlur((mask_r > 0).astype(np.float32) * 255.0, (5, 5), 0) / 255.0
            alpha3 = np.stack([alpha] * 3, axis=-1)
            work = (work.astype(np.float32) * (1 - alpha3)
                    + gen_bgr.astype(np.float32) * alpha3).astype(np.uint8)
            changed_union = np.maximum(changed_union, (mask_r > 0).astype(np.uint8))
            applied += 1

        logger.info("ControlNet render applied=%d/%d (%.1fs)",
                    applied, len(selections), time.perf_counter() - t0)

        if applied == 0:
            return canvas_bgr

        # Paste only the diffused (changed) regions back onto the full-res
        # original so unmasked pixels keep their native resolution.
        work_full = cv2.resize(work, (w0, h0), interpolation=cv2.INTER_CUBIC)
        union_full = cv2.resize(changed_union * 255, (w0, h0), interpolation=cv2.INTER_LINEAR)
        alpha = cv2.GaussianBlur(union_full.astype(np.float32), (9, 9), 0) / 255.0
        alpha3 = np.stack([alpha] * 3, axis=-1)
        out = (canvas_bgr.astype(np.float32) * (1 - alpha3)
               + work_full.astype(np.float32) * alpha3).astype(np.uint8)
        return out
