"""Costing DTOs."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.rendering import RegionMaterial


class EstimateRequest(BaseModel):
    selections: list[RegionMaterial]
    facade_width_m: float = Field(default=12.0, gt=0, le=200)
    facade_height_m: float = Field(default=9.0, gt=0, le=200)
    waste_factor: float = Field(default=1.10, ge=1.0, le=2.0)


class CostLineOut(BaseModel):
    category: str
    category_label: str
    material_key: str
    material_name: str
    quantity: float
    unit: str
    rate_inr: float
    line_total_inr: float
    color: str | None = None


class EstimateResponse(BaseModel):
    currency: str
    currency_symbol: str
    facade_width_m: float
    facade_height_m: float
    facade_area_m2: float
    waste_factor: float
    lines: list[CostLineOut]
    subtotal_inr: float
    total_inr: float
    total_display: str
    disclaimer: str
