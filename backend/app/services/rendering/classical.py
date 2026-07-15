"""Classical-CV render backend (no diffusion, CPU-friendly, deterministic).

Paint: darker / richer solid fill inside the mask at near-full opacity, with
light luminance modulation so shadows and edge depth survive.

Texture: tile cladding / tile / pattern images into the mask with strong
coverage and a crisp (slightly anti-aliased) alpha.
"""
from __future__ import annotations

from typing import Callable

import cv2
import numpy as np

from app.core.logging_config import get_logger
from app.services.rendering.base import RenderBackend
from app.utils.categories import OPENING_CATEGORIES

logger = get_logger("rendering.classical")

_COMPOSITE_PRIORITY = {
    "wall": 0,
    "rooftop": 1,
    "pillar": 2,
    "balcony": 3,
    "railing": 4,
    "gate": 5,
    "window": 6,
    "door": 7,
}

# Max value (HSV V, 0–1) and min saturation for paint colors.
_MAX_PAINT_VALUE = 0.55
_MIN_PAINT_SAT = 0.35


def _hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        h = "1E3A5F"
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return b, g, r


def _bgr_to_hex(bgr: tuple[int, int, int]) -> str:
    b, g, r = bgr
    return f"#{r:02X}{g:02X}{b:02X}"


def enrich_dark_color(hex_color: str) -> str:
    """Clamp paint to darker, richer colors (lower V, higher S)."""
    bgr = np.uint8([[list(_hex_to_bgr(hex_color))]])
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)[0, 0]
    h, s, v = float(hsv[0]), float(hsv[1]) / 255.0, float(hsv[2]) / 255.0
    s = max(s, _MIN_PAINT_SAT)
    v = min(v, _MAX_PAINT_VALUE)
    out = np.uint8([[[h, int(s * 255), int(v * 255)]]])
    bgr2 = cv2.cvtColor(out, cv2.COLOR_HSV2BGR)[0, 0]
    return _bgr_to_hex((int(bgr2[0]), int(bgr2[1]), int(bgr2[2])))


def _mask_alpha(mask: np.ndarray) -> np.ndarray:
    """Near-full opacity inside the segment; tiny blur only for edge AA."""
    binary = (mask > 0).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    # Soften edge 1–2px so it doesn't look cut-out; core stays ~1.0
    soft = cv2.GaussianBlur(binary.astype(np.float32), (3, 3), 0)
    soft = np.clip(soft, 0.0, 1.0)
    # Lift interior toward full opacity
    soft = np.where(binary > 0, np.maximum(soft, 0.92), soft)
    return np.stack([soft] * 3, axis=-1)


def _apply_paint(img_bgr: np.ndarray, color_hex: str) -> np.ndarray:
    """Full-coverage dark rich paint; keep shading via luminance multiply."""
    color_hex = enrich_dark_color(color_hex)
    bgr = _hex_to_bgr(color_hex)
    solid = np.empty_like(img_bgr)
    solid[:] = bgr

    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0].astype(np.float32) / 255.0
    # Relative shade around mid-grey — keeps balcony recesses visible
    shade = 0.50 + 0.50 * L
    shaded = np.clip(solid.astype(np.float32) * shade[..., None], 0, 255)
    return shaded.astype(np.uint8)


_TILE_SIZES_M = {
    "cadding": (0.50, 0.25),
    "cladding": (0.50, 0.25),
    "tile": (0.40, 0.40),
    "tiles": (0.40, 0.40),
    "pattern": (0.80, 0.80),
    "textures": (0.80, 0.80),
    "plaster": (1.00, 1.00),
    "stone": (0.45, 0.30),
}


def _apply_texture(img_bgr: np.ndarray, texture_path: str) -> np.ndarray:
    texture = cv2.imread(texture_path)
    if texture is None:
        logger.warning("Texture missing on disk: %s", texture_path)
        return img_bgr
    h, w = img_bgr.shape[:2]

    door_h_px = max(80, int(h * 0.25))
    px_per_m = door_h_px / 2.13
    path_l = texture_path.lower().replace("\\", "/")
    key = next((k for k in _TILE_SIZES_M if k in path_l), "pattern")
    tw_m, th_m = _TILE_SIZES_M[key]
    tile_w = max(48, int(tw_m * px_per_m))
    tile_h = max(48, int(th_m * px_per_m))

    tile = cv2.resize(texture, (tile_w, tile_h), interpolation=cv2.INTER_AREA)
    reps_y = int(np.ceil(h / tile_h)) + 1
    reps_x = int(np.ceil(w / tile_w)) + 1
    tiled = np.tile(tile, (reps_y, reps_x, 1))[:h, :w]

    # Strong texture coverage with residual shading from the photo
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0]
    clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
    L_norm = clahe.apply(L).astype(np.float32) / 255.0
    shade = 0.55 + 0.45 * L_norm
    out = tiled.astype(np.float32) * shade[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


class ClassicalBackend(RenderBackend):
    name = "classical"

    def is_available(self) -> bool:
        return True

    def render(
        self,
        canvas_bgr: np.ndarray,
        selections: list[dict],
        mask_loader: Callable[[str], "np.ndarray | None"],
    ) -> np.ndarray:
        canvas = canvas_bgr
        h, w = canvas.shape[:2]

        loaded: dict[str, np.ndarray] = {}
        for sel in selections:
            cat = sel["category"]
            mask = mask_loader(cat)
            if mask is None or mask.sum() == 0:
                logger.warning("  skip category=%s (no mask pixels)", cat)
                continue
            if mask.shape[:2] != (h, w):
                mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
            loaded[cat] = (mask > 0).astype(np.uint8)

        if "wall" in loaded:
            wall = loaded["wall"].copy()
            for cat in OPENING_CATEGORIES:
                if cat in loaded and cat != "wall":
                    wall = np.where(loaded[cat] > 0, 0, wall).astype(np.uint8)
            if "rooftop" in loaded:
                wall = np.where(loaded["rooftop"] > 0, 0, wall).astype(np.uint8)
            loaded["wall"] = wall

        ordered = sorted(
            [s for s in selections if s["category"] in loaded],
            key=lambda s: _COMPOSITE_PRIORITY.get(s["category"], 50),
        )

        applied = 0
        for sel in ordered:
            cat = sel["category"]
            mask = loaded[cat]
            if mask.sum() == 0:
                continue

            if sel["render_path"] == "paint":
                color = enrich_dark_color(sel.get("color") or "#1E3A5F")
                overlay = _apply_paint(canvas, color)
                logger.info("  paint category=%s color=%s (enriched)", cat, color)
            elif sel["render_path"] == "texture" and sel.get("texture_path"):
                overlay = _apply_texture(canvas, sel["texture_path"])
                logger.info("  texture category=%s asset=%s", cat, sel["texture_path"])
            else:
                logger.warning(
                    "  skip category=%s (unsupported render_path=%s)",
                    cat,
                    sel.get("render_path"),
                )
                continue

            alpha = _mask_alpha(mask)
            # Full inpaint inside segmented mask
            canvas = (
                canvas.astype(np.float32) * (1.0 - alpha)
                + overlay.astype(np.float32) * alpha
            ).astype(np.uint8)
            applied += 1

        logger.info("Classical render applied=%d/%d", applied, len(selections))
        return canvas
