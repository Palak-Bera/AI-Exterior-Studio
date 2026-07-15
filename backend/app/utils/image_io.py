"""Image helpers: URL mapping, mask persistence, polygon extraction."""
from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np

from app.core.config import settings

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def to_media_url(path: str | Path) -> str:
    """Map a storage path to a public /storage URL served by StaticFiles."""
    p = Path(path)
    try:
        rel = p.relative_to(settings.STORAGE_DIR)
    except ValueError:
        rel = Path(p.name)
    return "/storage/" + rel.as_posix()


def image_stem(filename_or_path: str | Path) -> str:
    """Safe stem from an upload filename or storage path (e.g. 'bunglow 1')."""
    stem = Path(filename_or_path).stem.strip() or "image"
    stem = _UNSAFE_CHARS.sub("_", stem).strip(" .")
    return stem or "image"


def category_mask_filename(category: str, image_name: str | Path) -> str:
    """Gate_bunglow 1.png, Window_bunglow 1.png, …"""
    return f"{category.capitalize()}_{image_stem(image_name)}.png"


def render_output_filename(
    image_name: str | Path,
    *,
    project_id: str | None = None,
    stamp: str | int | None = None,
) -> str:
    """Output_bunglow 1_<project>_<stamp>.jpg — unique per render for cache safety."""
    parts = [f"Output_{image_stem(image_name)}"]
    if project_id:
        parts.append(project_id[:8])
    if stamp is not None:
        parts.append(str(stamp))
    return "_".join(parts) + ".jpg"


def save_binary_mask(mask: np.ndarray, out_path: Path, color: tuple[int, int, int]) -> None:
    """Persist a binary mask as an RGBA PNG tinted with the category color."""
    h, w = mask.shape[:2]
    r, g, b = color
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    on = mask > 0
    rgba[on, 0] = b  # OpenCV writes BGRA
    rgba[on, 1] = g
    rgba[on, 2] = r
    rgba[on, 3] = 200
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), rgba)


def mask_to_polygons(mask: np.ndarray, epsilon_ratio: float = 0.01,
                     min_area: int = 200) -> list[list[list[int]]]:
    """Convert a binary mask to simplified polygons (Douglas-Peucker)."""
    contours, _ = cv2.findContours(
        (mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    polygons: list[list[list[int]]] = []
    for cnt in contours:
        if cv2.contourArea(cnt) < min_area:
            continue
        eps = epsilon_ratio * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, eps, True)
        polygons.append([[int(p[0][0]), int(p[0][1])] for p in approx])
    return polygons
