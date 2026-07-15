"""Project DTOs."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    image_url: str
    width: int
    height: int
    status: str
    created_at: datetime


class IngestWarning(BaseModel):
    code: str
    message: str


class IngestResponse(BaseModel):
    project: ProjectOut
    warnings: list[IngestWarning] = []
