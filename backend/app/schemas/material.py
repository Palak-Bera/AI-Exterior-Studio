"""Material catalog DTOs."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    name: str
    render_path: str
    default_color: str | None = None
    texture_url: str | None = None
    group: str = "texture"
    group_label: str = "Textures"
    rate_inr: float = 0.0
    unit: str = "sqm"  # sqm | unit
    currency: str = "INR"


class MaterialRateUpdate(BaseModel):
    key: str
    rate_inr: float = Field(ge=0)
    unit: str = Field(default="sqm", pattern="^(sqm|unit)$")


class MaterialRatesBulkUpdate(BaseModel):
    rates: list[MaterialRateUpdate]
