"""Region model - a detected facade component (the RegionMap contract, persisted).

One row per (project, category). Instance-level polygons are stored inside the
`polygons` JSON so the frontend can render/edit individual shapes while the
binary union mask on disk drives rendering.
"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(32))
    instance_count: Mapped[int] = mapped_column(Integer, default=1)
    mask_path: Mapped[str] = mapped_column(String(512))
    polygons: Mapped[list] = mapped_column(JSON, default=list)
    pixel_area: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    project: Mapped["Project"] = relationship(back_populates="regions")
