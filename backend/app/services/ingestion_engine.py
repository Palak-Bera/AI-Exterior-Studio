"""Ingestion Engine.

Responsibility: turn a raw upload into a clean, normalized working image plus a
persisted Project record, while surfacing user-actionable quality warnings.

Steps: validate bytes -> decode -> EXIF auto-rotate -> resize to working res ->
quality checks (blur / exposure / resolution) -> persist.
"""
from __future__ import annotations

import io
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.core.config import UPLOAD_DIR, settings
from app.core.logging_config import get_logger

logger = get_logger("ingestion")


@dataclass
class IngestResult:
    project_id: str
    image_path: Path
    filename: str
    width: int
    height: int
    warnings: list[dict] = field(default_factory=list)


class IngestionError(ValueError):
    """Raised when an upload is unusable and must be rejected."""


def _decode_and_orient(raw: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)  # honor camera orientation, strip EXIF
        return img.convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise IngestionError("Could not read the image file.") from exc


def _resize_long_edge(img: Image.Image, long_edge: int) -> Image.Image:
    w, h = img.size
    longest = max(w, h)
    if longest <= long_edge:
        return img
    scale = long_edge / longest
    return img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)


def _quality_warnings(bgr: np.ndarray) -> list[dict]:
    warnings: list[dict] = []
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    focus = cv2.Laplacian(gray, cv2.CV_64F).var()
    if focus < settings.BLUR_LAPLACIAN_MIN:
        warnings.append({
            "code": "blurry",
            "message": "Image looks blurry - a sharper photo will improve detection.",
        })

    mean = float(gray.mean())
    if mean < settings.DARK_MEAN_MIN:
        warnings.append({"code": "too_dark", "message": "Image is very dark; retake in better light."})
    elif mean > settings.BRIGHT_MEAN_MAX:
        warnings.append({"code": "too_bright", "message": "Image is overexposed; reduce brightness."})

    return warnings


def ingest(raw: bytes, original_name: str, content_type: str | None) -> IngestResult:
    logger.info("Ingest start: name=%r content_type=%s size=%.1f KB",
                original_name, content_type, len(raw) / 1024)

    if content_type and content_type not in settings.ALLOWED_CONTENT_TYPES:
        logger.warning("Rejected upload: unsupported content_type=%s", content_type)
        raise IngestionError(f"Unsupported file type: {content_type}")
    if len(raw) > settings.MAX_UPLOAD_BYTES:
        logger.warning("Rejected upload: too large (%.1f MB)", len(raw) / 1024 / 1024)
        raise IngestionError("File is too large (max 20 MB).")

    img = _decode_and_orient(raw)
    orig_w, orig_h = img.size
    img = _resize_long_edge(img, settings.MAX_IMAGE_LONG_EDGE)
    w, h = img.size
    logger.info("Decoded image: original=%dx%d -> working=%dx%d", orig_w, orig_h, w, h)

    if max(w, h) < settings.MIN_IMAGE_LONG_EDGE:
        logger.warning("Rejected upload: resolution too low (%dx%d)", w, h)
        raise IngestionError(
            f"Image resolution too low (min {settings.MIN_IMAGE_LONG_EDGE}px on the long edge)."
        )

    bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    warnings = _quality_warnings(bgr)
    if warnings:
        logger.info("Quality warnings: %s", [w_["code"] for w_ in warnings])

    project_id = uuid.uuid4().hex
    ext = ".jpg"
    out_path = UPLOAD_DIR / f"{project_id}{ext}"
    cv2.imwrite(str(out_path), bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    logger.info("Ingest done: project_id=%s saved=%s", project_id, out_path)

    return IngestResult(
        project_id=project_id,
        image_path=out_path,
        filename=original_name,
        width=w,
        height=h,
        warnings=warnings,
    )
