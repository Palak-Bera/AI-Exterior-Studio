"""Rendering DTOs."""
from __future__ import annotations

from pydantic import BaseModel


class RegionMaterial(BaseModel):
    category: str
    material_key: str
    # Overrides the material default color (paint path only), e.g. "#1E3A8A".
    color: str | None = None


class RenderRequest(BaseModel):
    selections: list[RegionMaterial]
    # Which render mode to use. None => server default (classical).
    mode: str | None = None


class RenderResponse(BaseModel):
    project_id: str
    input_url: str
    output_url: str
    backend: str
    applied: list[RegionMaterial]
