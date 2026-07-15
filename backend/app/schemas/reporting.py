"""Report DTOs."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.rendering import RegionMaterial


class ReportRequest(BaseModel):
    selections: list[RegionMaterial]
    # /storage/outputs/... URL or relative path from the last render
    output_url: str
    # Optional facade calibration for cost estimate (metres)
    facade_width_m: float = Field(default=12.0, gt=0, le=200)
    facade_height_m: float = Field(default=9.0, gt=0, le=200)
    waste_factor: float = Field(default=1.10, ge=1.0, le=2.0)
    include_cost: bool = True
