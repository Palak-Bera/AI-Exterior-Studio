"""Shared helpers for segmentation backends.

Kept framework-free (numpy/OpenCV/PIL only) so every model strategy can reuse
the same mask cleanup, wall-derivation, category matching and IO logic.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from app.core.config import settings


def load_working_image(image_path: str) -> tuple[Image.Image, int, int]:
    """Load an image and downscale it to the CPU working resolution.

    Returns (working_image, original_width, original_height).
    """
    img = Image.open(image_path).convert("RGB")
    w0, h0 = img.size
    longest = max(w0, h0)
    if longest > settings.SEG_WORKING_LONG_EDGE:
        scale = settings.SEG_WORKING_LONG_EDGE / longest
        img = img.resize((round(w0 * scale), round(h0 * scale)), Image.LANCZOS)
    return img, w0, h0


def clean_mask(mask: np.ndarray) -> np.ndarray:
    kernel = np.ones((5, 5), np.uint8)
    m = cv2.morphologyEx((mask > 0).astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel)
    return m


def match_category(label: str, phrase_map: dict[str, str]) -> str | None:
    label = label.lower().strip()
    if label in phrase_map:
        return phrase_map[label]
    for phrase, cat in phrase_map.items():
        if phrase in label or label in phrase:
            return cat
    return None


def grabcut_foreground(bgr: np.ndarray) -> np.ndarray:
    """Rough building silhouette using GrabCut + HSV sky/ground priors."""
    h, w = bgr.shape[:2]
    mask = np.full((h, w), cv2.GC_BGD, np.uint8)
    rect = (int(w * 0.10), int(h * 0.10), int(w * 0.90), int(h * 0.90))
    cv2.rectangle(mask, (rect[0], rect[1]), (rect[2], rect[3]), cv2.GC_PR_FGD, -1)

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    hue, sat, val = cv2.split(hsv)
    y = np.indices((h, w))[0]
    mask[(hue > 95) & (hue < 135) & (sat > 30) & (val > 120)] = cv2.GC_BGD  # sky
    mask[(sat < 15) & (val < 40)] = cv2.GC_BGD  # deep shadow / road
    mask[y > int(h * 0.90)] = cv2.GC_BGD

    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, mask, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)


def fallback_building(image: Image.Image) -> np.ndarray:
    bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    return grabcut_foreground(bgr)


def derive_wall(building: np.ndarray, openings_union: np.ndarray) -> np.ndarray:
    """wall = building silhouette - dilated openings (windows/doors/etc)."""
    dilated = cv2.dilate(openings_union, np.ones((7, 7), np.uint8), 1)
    wall = np.clip(building.astype(int) - dilated.astype(int), 0, 1).astype(np.uint8)
    return clean_mask(wall)


def upscale_masks(masks: dict, w0: int, h0: int) -> None:
    """Resize every CategoryMask in-place back to the stored image resolution."""
    for cm in masks.values():
        if cm.mask.shape[:2] != (h0, w0):
            cm.mask = cv2.resize(cm.mask, (w0, h0), interpolation=cv2.INTER_NEAREST)
