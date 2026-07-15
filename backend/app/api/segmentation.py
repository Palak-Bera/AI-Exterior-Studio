"""Segmentation routes - run Grounded-SAM and persist the RegionMap."""
from __future__ import annotations

import base64
import io
import uuid

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import MASK_DIR
from app.core.logging_config import get_logger
from app.db.session import get_db
from app.models.project import Project
from app.models.region import Region
from app.schemas.region import (
    MaskEditRequest,
    RegionOut,
    SegmentationRequest,
    SegmentationResponse,
)
from app.services import segmentation
from app.services.segmentation import BackendUnavailable
from app.utils.categories import CATEGORIES, resolve_categories
from app.utils.image_io import (
    category_mask_filename,
    mask_to_polygons,
    save_binary_mask,
    to_media_url,
)

logger = get_logger("api.segmentation")
router = APIRouter(prefix="/segmentation", tags=["segmentation"])


def _region_out(region: Region) -> RegionOut:
    return RegionOut(
        id=region.id,
        project_id=region.project_id,
        category=region.category,
        instance_count=region.instance_count,
        mask_url=to_media_url(region.mask_path),
        polygons=region.polygons,
        pixel_area=region.pixel_area,
        confidence=region.confidence,
    )


def _decode_mask_png(data_url: str, width: int, height: int) -> np.ndarray:
    """Decode a canvas PNG (data URL / base64) into a binary HxW mask."""
    raw = data_url.strip()
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        blob = base64.b64decode(raw)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="Invalid mask image data.") from exc

    try:
        img = Image.open(io.BytesIO(blob)).convert("RGBA")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="Could not decode mask PNG.") from exc

    if img.size != (width, height):
        img = img.resize((width, height), Image.NEAREST)

    arr = np.asarray(img)
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3].astype(np.float32).mean(axis=2)
    binary = ((alpha > 30) | (rgb > 40)).astype(np.uint8)
    return binary


@router.post("/{project_id}", response_model=SegmentationResponse)
def segment(project_id: str, payload: SegmentationRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    categories = resolve_categories(payload.categories)
    model = segmentation.resolve_model(payload.model)
    logger.info(
        "Segmentation requested for project=%s model=%s categories=%s",
        project_id,
        model,
        categories,
    )
    try:
        backend, masks = segmentation.segment_image(project.image_path, categories, model)
    except BackendUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    for region in list(project.regions):
        if region.category in categories:
            db.delete(region)
    db.flush()

    regions: list[Region] = []
    for cat, cm in masks.items():
        if cm.mask.sum() == 0:
            continue
        mask_path = MASK_DIR / category_mask_filename(
            cat, project.filename or project.image_path
        )
        save_binary_mask(cm.mask, mask_path, CATEGORIES[cat]["color"])
        region = Region(
            id=uuid.uuid4().hex,
            project_id=project_id,
            category=cat,
            instance_count=cm.instance_count,
            mask_path=str(mask_path),
            polygons=mask_to_polygons(cm.mask),
            pixel_area=int(cm.mask.sum()),
            confidence=round(cm.confidence, 4),
        )
        db.add(region)
        regions.append(region)

    project.status = "segmented"
    db.commit()
    for r in regions:
        db.refresh(r)

    logger.info(
        "Segmentation persisted: project=%s backend=%s regions=%s",
        project_id,
        backend,
        [r.category for r in regions],
    )
    return SegmentationResponse(
        project_id=project_id,
        backend=backend,
        regions=[_region_out(r) for r in regions],
    )


@router.get("/{project_id}/regions", response_model=SegmentationResponse)
def get_regions(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return SegmentationResponse(
        project_id=project_id,
        backend="stored",
        regions=[_region_out(r) for r in project.regions],
    )


@router.put("/{project_id}/regions/{category}", response_model=RegionOut)
def update_region_mask(
    project_id: str,
    category: str,
    payload: MaskEditRequest,
    db: Session = Depends(get_db),
):
    """Save a user-edited brush/eraser mask for one category."""
    if category not in CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Unknown category '{category}'")

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    binary = _decode_mask_png(payload.mask_data_url, project.width, project.height)
    pixels = int(binary.sum())
    if pixels == 0:
        raise HTTPException(
            status_code=422,
            detail="Edited mask is empty. Paint the area you want to keep, then save.",
        )

    mask_path = MASK_DIR / category_mask_filename(
        category, project.filename or project.image_path
    )
    save_binary_mask(binary, mask_path, CATEGORIES[category]["color"])

    region = next((r for r in project.regions if r.category == category), None)
    if region is None:
        region = Region(
            id=uuid.uuid4().hex,
            project_id=project_id,
            category=category,
            instance_count=1,
            mask_path=str(mask_path),
            polygons=mask_to_polygons(binary),
            pixel_area=pixels,
            confidence=1.0,
        )
        db.add(region)
    else:
        region.mask_path = str(mask_path)
        region.polygons = mask_to_polygons(binary)
        region.pixel_area = pixels
        region.instance_count = max(1, region.instance_count)
        region.confidence = 1.0

    project.status = "segmented"
    db.commit()
    db.refresh(region)
    logger.info(
        "Mask edited: project=%s category=%s pixels=%d path=%s",
        project_id,
        category,
        pixels,
        mask_path,
    )
    return _region_out(region)
