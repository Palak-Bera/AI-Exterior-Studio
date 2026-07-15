"""Rendering Engine - classical paint/texture only (8 GB RAM friendly).

Public API:
    render_image(image_path, selections, mask_loader, mode, output_name=None)
        -> (backend_used, output_path)
    list_render_modes() -> [ {key,label,description,default,requires_gpu,available} ]

ControlNet / SD inpainting are intentionally not exposed — they exceed typical
8 GB RAM budgets. The controlnet module may still exist on disk but is unused.
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2

from app.core.config import OUTPUT_DIR
from app.core.logging_config import get_logger
from app.services.rendering.base import RenderBackend, RenderUnavailable
from app.services.rendering.classical import ClassicalBackend
from app.utils.image_io import render_output_filename

logger = get_logger("rendering")

__all__ = ["render_image", "list_render_modes", "resolve_mode", "RenderUnavailable"]

_FACTORIES = {
    "classical": ClassicalBackend,
}

MODES = [
    {
        "key": "classical",
        "label": "Classical CV",
        "description": "LAB recolor / texture tiling. CPU-only, low RAM — the only paint mode on this build.",
        "requires_gpu": False,
    },
]


def _get_backend(key: str) -> RenderBackend:
    return _FACTORIES[key]()


def resolve_mode(mode: str | None) -> str:
    # Always classical — ControlNet/SD disabled for RAM constraints.
    if mode and mode != "classical":
        logger.warning(
            "Render mode '%s' requested but only 'classical' is enabled; using classical.",
            mode,
        )
    return "classical"


def list_render_modes() -> list[dict]:
    default = "classical"
    out = []
    for m in MODES:
        try:
            available = _get_backend(m["key"]).is_available()
        except Exception:  # noqa: BLE001
            available = False
        out.append({**m, "default": m["key"] == default, "available": available})
    return out


def render_image(
    image_path: str,
    selections: list[dict],
    mask_loader,
    mode: str | None = None,
    *,
    output_name: str | None = None,
) -> tuple[str, Path]:
    """Composite the given material selections with classical paint/texture.

    Saves as Output_<imageName>.jpg under storage/outputs/ (or `output_name` if given).
    """
    mode = resolve_mode(mode)
    logger.info("Render start: image=%s mode=%s selections=%d",
                image_path, mode, len(selections))
    t0 = time.perf_counter()

    canvas = cv2.imread(image_path)
    if canvas is None:
        logger.error("Source image could not be read: %s", image_path)
        raise ValueError("Source image could not be read for rendering.")

    backend = _get_backend(mode)
    used = mode
    try:
        if not backend.is_available():
            raise RenderUnavailable(
                f"Render mode '{mode}' is not available on this host."
            )
        canvas = backend.render(canvas, selections, mask_loader)
    except RenderUnavailable:
        raise
    except Exception:  # noqa: BLE001
        logger.exception("Classical render failed")
        raise

    filename = output_name or render_output_filename(image_path)
    out_path = OUTPUT_DIR / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    logger.info("Render done: backend=%s output=%s (%.1fs)",
                used, out_path, time.perf_counter() - t0)
    return used, out_path
