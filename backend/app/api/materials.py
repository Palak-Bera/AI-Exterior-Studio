"""Materials routes - catalog + Cost-page rate updates (INR)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.material import Material
from app.schemas.material import MaterialOut, MaterialRatesBulkUpdate
from app.services.catalog import group_for_material
from app.utils.image_io import to_media_url

router = APIRouter(prefix="/materials", tags=["materials"])


def _to_out(m: Material) -> MaterialOut:
    group, group_label = group_for_material(m.render_path, m.texture_path)
    return MaterialOut(
        key=m.key,
        name=m.name,
        render_path=m.render_path,
        default_color=m.default_color,
        texture_url=to_media_url(m.texture_path) if m.texture_path else None,
        group=group,
        group_label=group_label,
        rate_inr=float(m.rate_inr or 0),
        unit=m.unit or "sqm",
        currency="INR",
    )


@router.get("", response_model=list[MaterialOut])
def list_materials(db: Session = Depends(get_db)):
    items = (
        db.query(Material)
        .filter(Material.is_active.is_(True))
        .order_by(Material.render_path.asc(), Material.name.asc())
        .all()
    )
    out = [_to_out(m) for m in items]
    order = {"paint": 0, "cladding": 1, "tiles": 2, "patterns": 3}
    out.sort(key=lambda m: (order.get(m.group, 9), m.name))
    return out


@router.put("/rates", response_model=list[MaterialOut])
def update_material_rates(payload: MaterialRatesBulkUpdate, db: Session = Depends(get_db)):
    """Update material rates from the Cost page (values in Indian Rupees)."""
    if not payload.rates:
        raise HTTPException(status_code=422, detail="No rates provided")

    by_key = {m.key: m for m in db.query(Material).all()}
    updated: list[Material] = []
    for row in payload.rates:
        mat = by_key.get(row.key)
        if not mat:
            continue
        mat.rate_inr = float(row.rate_inr)
        mat.unit = row.unit
        updated.append(mat)

    if not updated:
        raise HTTPException(status_code=404, detail="No matching materials found")

    db.commit()
    order = {"paint": 0, "cladding": 1, "tiles": 2, "patterns": 3}
    outs = [_to_out(m) for m in updated if m.is_active]
    outs.sort(key=lambda m: (order.get(m.group, 9), m.name))
    return outs
