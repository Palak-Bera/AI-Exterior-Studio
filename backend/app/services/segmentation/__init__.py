"""Segmentation Engine — Grounding DINO + SAM (vit-base) only.

Public API:
    segment_image(image_path, categories, model) -> (backend_used, {cat: CategoryMask})
    list_models() -> [ {key,label,description,default,requires_gpu,gated,available,loaded} ]
    activate_model(model) -> {model, loaded, ...}
"""
from __future__ import annotations

import threading
import time

from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.segmentation.base import BackendUnavailable, CategoryMask, SegBackend
from app.services.segmentation.common import load_working_image, upscale_masks
from app.services.segmentation.grounded_sam import GroundedSamBackend

logger = get_logger("segmentation")

__all__ = [
    "segment_image",
    "list_models",
    "activate_model",
    "get_active_model",
    "CategoryMask",
    "BackendUnavailable",
]

_FACTORIES = {
    "grounded_sam": GroundedSamBackend.instance,
}

MODELS = [
    {
        "key": "grounded_sam",
        "label": "Grounded SAM",
        "description": "Grounding DINO + SAM (vit-base). Detects walls, windows, facades, and more.",
        "requires_gpu": False,
        "gated": False,
    },
]

_active_lock = threading.Lock()
_active_model: str | None = None


def _get_backend(key: str) -> SegBackend:
    return _FACTORIES[key]()


def resolve_model(model: str | None) -> str:
    if model and model in _FACTORIES:
        return model
    if _active_model and _active_model in _FACTORIES:
        return _active_model
    return settings.DEFAULT_SEGMENTATION_MODEL


def get_active_model() -> str | None:
    return _active_model


def list_models() -> list[dict]:
    default = _active_model or settings.DEFAULT_SEGMENTATION_MODEL
    out = []
    for m in MODELS:
        try:
            backend = _get_backend(m["key"])
            available = backend.is_available()
            loaded = backend.is_loaded() if available else False
        except Exception:  # noqa: BLE001
            available = False
            loaded = False
        out.append({
            **m,
            "default": m["key"] == default,
            "available": available,
            "loaded": loaded,
            "active": m["key"] == _active_model,
        })
    return out


def activate_model(model: str) -> dict:
    """Load Grounded SAM into RAM."""
    global _active_model

    if model not in _FACTORIES:
        raise BackendUnavailable(
            f"Unknown segmentation model '{model}'. Only 'grounded_sam' is supported."
        )

    with _active_lock:
        logger.info("Activating segmentation model=%s", model)
        t0 = time.perf_counter()

        backend = _get_backend(model)
        if not backend.is_available():
            raise BackendUnavailable(
                f"Model '{model}' is not available "
                "(missing Grounding DINO / SAM weights). "
                "Run: python scripts/download_models.py"
            )

        backend.warmup()
        _active_model = model
        elapsed = time.perf_counter() - t0
        logger.info("Model '%s' loaded and active (%.1fs)", model, elapsed)
        return {
            "model": model,
            "loaded": True,
            "active": True,
            "load_seconds": round(elapsed, 2),
            "label": next((m["label"] for m in MODELS if m["key"] == model), model),
        }


def segment_image(
    image_path: str, categories: list[str], model: str | None = None
) -> tuple[str, dict[str, CategoryMask]]:
    """Segment the requested categories with Grounded SAM."""
    model = resolve_model(model)
    if model not in _FACTORIES:
        raise BackendUnavailable(
            f"Unknown segmentation model '{model}'. Only 'grounded_sam' is supported."
        )

    logger.info("Segment request: model=%s categories=%s image=%s",
                model, categories, image_path)
    work_img, w0, h0 = load_working_image(image_path)
    logger.info("Working image loaded: full=%dx%d", w0, h0)
    t0 = time.perf_counter()

    backend = _get_backend(model)
    if not backend.is_available():
        raise BackendUnavailable(
            f"Model '{model}' is not available "
            "(missing Grounding DINO / SAM weights). "
            "Run: python scripts/download_models.py"
        )
    if not backend.is_loaded():
        backend.warmup()
    masks = backend.segment(work_img, categories)

    upscale_masks(masks, w0, h0)
    logger.info("Segment done: backend=%s categories_found=%d (%.1fs total)",
                model, len(masks), time.perf_counter() - t0)
    return model, masks
