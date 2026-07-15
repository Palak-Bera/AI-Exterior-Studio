"""Ensure texture folders exist. Prefer real assets under:

  storage/textures/wall_cadding/
  storage/textures/wall_tiles/
  storage/textures/texture_patterns/

Only writes legacy flat placeholders (stone/tile/plaster.jpg) when those
category folders have no images yet.

Run:  python scripts/generate_textures.py
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

OUT = Path("storage/textures")
OUT.mkdir(parents=True, exist_ok=True)

_CATEGORY_DIRS = ("wall_cadding", "wall_tiles", "texture_patterns")
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _noise(h: int, w: int, base: tuple[int, int, int], amp: int) -> np.ndarray:
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = base
    noise = np.random.randint(-amp, amp, (h, w, 1)).astype(np.int16)
    return np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def make_stone() -> np.ndarray:
    img = _noise(256, 256, (120, 125, 130), 30)
    for y in range(0, 256, 42):
        cv2.line(img, (0, y), (256, y), (70, 72, 75), 2)
    for x in range(0, 256, 64):
        cv2.line(img, (x, 0), (x, 256), (70, 72, 75), 2)
    return img


def make_tile() -> np.ndarray:
    img = _noise(256, 256, (210, 215, 220), 12)
    for y in range(0, 257, 64):
        cv2.line(img, (0, y), (256, y), (150, 150, 155), 3)
    for x in range(0, 257, 64):
        cv2.line(img, (x, 0), (x, 256), (150, 150, 155), 3)
    return img


def make_plaster() -> np.ndarray:
    return _noise(256, 256, (200, 195, 185), 18)


def _has_category_textures() -> bool:
    for name in _CATEGORY_DIRS:
        folder = OUT / name
        if not folder.is_dir():
            continue
        if any(p.suffix.lower() in _IMAGE_EXTS for p in folder.iterdir() if p.is_file()):
            return True
    return False


if __name__ == "__main__":
    for name in _CATEGORY_DIRS:
        (OUT / name).mkdir(parents=True, exist_ok=True)

    if _has_category_textures():
        print(f"Found category textures under {OUT.resolve()} — skipping placeholders.")
    else:
        cv2.imwrite(str(OUT / "stone.jpg"), make_stone())
        cv2.imwrite(str(OUT / "tile.jpg"), make_tile())
        cv2.imwrite(str(OUT / "plaster.jpg"), make_plaster())
        print(f"Wrote legacy placeholder textures to {OUT.resolve()}")
