"""PDF report routes — before/after + materials + INR cost estimate."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.session import get_db
from app.models.material import Material
from app.models.project import Project
from app.models.region import Region
from app.schemas.reporting import ReportRequest
from app.services.catalog import group_for_material
from app.services.costing import estimate_cost
from app.services.report import build_redesign_pdf, ensure_brand_logo, resolve_storage_file
from app.utils.categories import CATEGORIES

logger = get_logger("api.reporting")
router = APIRouter(prefix="/reporting", tags=["reporting"])


@router.post("/{project_id}/pdf")
def generate_pdf(project_id: str, payload: ReportRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not payload.selections:
        raise HTTPException(status_code=422, detail="No material selections provided")
    if not payload.output_url:
        raise HTTPException(
            status_code=422,
            detail="Render an output first, then generate the PDF report.",
        )

    ensure_brand_logo()
    try:
        before_path = resolve_storage_file(project.image_path)
        after_path = resolve_storage_file(payload.output_url)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    materials = {m.key: m for m in db.query(Material).all()}
    materials_by_key: dict[str, dict] = {}
    for key, m in materials.items():
        group, _ = group_for_material(m.render_path, m.texture_path)
        materials_by_key[key] = {
            "name": m.name,
            "rate_inr": float(m.rate_inr or 0),
            "unit": m.unit or "sqm",
            "group": group,
        }

    rows: list[dict] = []
    for sel in payload.selections:
        mat = materials.get(sel.material_key)
        rows.append({
            "category": sel.category,
            "material_key": sel.material_key,
            "material_name": mat.name if mat else sel.material_key,
            "color": sel.color if (mat and mat.render_path == "paint") else (sel.color or None),
        })
        if sel.category not in CATEGORIES:
            logger.warning("Report includes unknown category=%s", sel.category)

    cost_estimate = None
    if payload.include_cost:
        regions = db.query(Region).filter(Region.project_id == project_id).all()
        regions_by_cat = {
            r.category: {
                "pixel_area": r.pixel_area,
                "instance_count": r.instance_count,
            }
            for r in regions
        }
        cost_estimate = estimate_cost(
            selections=[s.model_dump() for s in payload.selections],
            regions_by_category=regions_by_cat,
            materials_by_key=materials_by_key,
            image_width=project.width or 1,
            image_height=project.height or 1,
            facade_width_m=payload.facade_width_m,
            facade_height_m=payload.facade_height_m,
            waste_factor=payload.waste_factor,
        )

    pdf_bytes = build_redesign_pdf(
        project_name=project.filename or project_id,
        project_id=project_id,
        before_path=Path(before_path),
        after_path=Path(after_path),
        selections=rows,
        cost_estimate=cost_estimate,
    )

    safe_name = Path(project.filename or "exterior").stem.replace(" ", "_")
    filename = f"AI_Exterior_Studio_Report_{safe_name}.pdf"
    logger.info("PDF ready: project=%s file=%s cost=%s", project_id, filename, bool(cost_estimate))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
