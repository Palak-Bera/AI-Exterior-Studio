"""Region / RegionMap DTOs - the contract shared by segmentation and rendering."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    category: str
    instance_count: int
    mask_url: str
    polygons: list
    pixel_area: int
    confidence: float


class SegmentationRequest(BaseModel):
    # Which categories to detect. Empty => the full default catalog.
    categories: list[str] = []
    # Which segmentation model backend to use. None => server default.
    model: str | None = None


class SegmentationResponse(BaseModel):
    project_id: str
    backend: str
    regions: list[RegionOut]


class MaskEditRequest(BaseModel):
    """PNG mask as a data URL (or raw base64). Opaque/white pixels = selected."""
    mask_data_url: str
