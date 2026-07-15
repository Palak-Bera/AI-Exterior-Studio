"""Rendering routes - apply selected materials to segmented regions."""
from __future__ import annotations

import time

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.session import get_db
from app.models.material import Material
from app.models.project import Project
from app.schemas.rendering import RegionMaterial, RenderRequest, RenderResponse
from app.services import rendering
from app.services.rendering import RenderUnavailable
from app.services.rendering.classical import enrich_dark_color
from app.utils.image_io import render_output_filename, to_media_url

logger = get_logger("api.rendering")
router = APIRouter(prefix="/rendering", tags=["rendering"])


@router.post("/{project_id}", response_model=RenderResponse)
def render(project_id: str, payload: RenderRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not payload.selections:
        raise HTTPException(status_code=422, detail="No material selections provided")

    mode = rendering.resolve_mode(payload.mode)
    logger.info(
        "Render requested: project=%s mode=%s selections=%s",
        project_id,
        mode,
        [(s.category, s.material_key) for s in payload.selections],
    )
    regions = {r.category: r for r in project.regions}
    materials = {m.key: m for m in db.query(Material).all()}

    selections = []
    applied: list[RegionMaterial] = []
    skipped: list[str] = []
    for sel in payload.selections:
        region = regions.get(sel.category)
        material = materials.get(sel.material_key)
        if region is None:
            skipped.append(sel.category)
            logger.warning("Skip selection category=%s (no region mask)", sel.category)
            continue
        if material is None:
            raise HTTPException(
                status_code=422, detail=f"Unknown material '{sel.material_key}'"
            )
        color = sel.color or material.default_color
        if material.render_path == "paint" and color:
            color = enrich_dark_color(color)
        selections.append({
            "category": sel.category,
            "render_path": material.render_path,
            "color": color,
            "texture_path": material.texture_path,
            "material_key": material.key,
            "name": material.name,
        })
        applied.append(
            RegionMaterial(
                category=sel.category,
                material_key=sel.material_key,
                color=color,
            )
        )

    if not selections:
        detail = "No valid segmented regions for the selected elements."
        if skipped:
            detail += f" Missing masks: {', '.join(skipped)}."
        raise HTTPException(status_code=422, detail=detail)

    def mask_loader(category: str) -> np.ndarray | None:
        region = regions.get(category)
        if region is None:
            return None
        rgba = cv2.imread(region.mask_path, cv2.IMREAD_UNCHANGED)
        if rgba is None:
            return None
        alpha = rgba[:, :, 3] if rgba.ndim == 3 and rgba.shape[2] == 4 else rgba[:, :, 0]
        return (alpha > 10).astype(np.uint8)

    stamp = int(time.time())
    out_name = render_output_filename(
        project.filename or project.image_path,
        project_id=project_id,
        stamp=stamp,
    )

    try:
        backend, out_path = rendering.render_image(
            project.image_path,
            selections,
            mask_loader,
            mode,
            output_name=out_name,
        )
    except RenderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    project.status = "rendered"
    db.commit()

    logger.info(
        "Render persisted: project=%s applied=%d skipped=%s output=%s",
        project_id,
        len(applied),
        skipped,
        out_path,
    )
    return RenderResponse(
        project_id=project_id,
        input_url=to_media_url(project.image_path),
        output_url=to_media_url(out_path),
        backend=backend,
        applied=applied,
    )
