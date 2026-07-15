"""Cost estimation API — approximate redesign cost in INR."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.material import Material
from app.models.project import Project
from app.models.region import Region
from app.schemas.costing import EstimateRequest, EstimateResponse
from app.services.catalog import group_for_material
from app.services.costing import estimate_cost

router = APIRouter(prefix="/costing", tags=["costing"])


@router.post("/{project_id}/estimate", response_model=EstimateResponse)
def project_estimate(
    project_id: str,
    payload: EstimateRequest,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not payload.selections:
        raise HTTPException(status_code=422, detail="No material selections provided")

    regions = db.query(Region).filter(Region.project_id == project_id).all()
    regions_by_cat = {
        r.category: {
            "pixel_area": r.pixel_area,
            "instance_count": r.instance_count,
        }
        for r in regions
    }

    materials = {m.key: m for m in db.query(Material).filter(Material.is_active.is_(True)).all()}
    materials_by_key: dict[str, dict] = {}
    for key, m in materials.items():
        group, _ = group_for_material(m.render_path, m.texture_path)
        materials_by_key[key] = {
            "name": m.name,
            "rate_inr": float(m.rate_inr or 0),
            "unit": m.unit or "sqm",
            "group": group,
        }

    result = estimate_cost(
        selections=[s.model_dump() for s in payload.selections],
        regions_by_category=regions_by_cat,
        materials_by_key=materials_by_key,
        image_width=project.width or 1,
        image_height=project.height or 1,
        facade_width_m=payload.facade_width_m,
        facade_height_m=payload.facade_height_m,
        waste_factor=payload.waste_factor,
    )
    return EstimateResponse(**result)
