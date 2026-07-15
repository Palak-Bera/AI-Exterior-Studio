"""Project model - one uploaded exterior photo and its derived assets."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    image_path: Mapped[str] = mapped_column(String(512))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="ingested")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    regions: Mapped[list["Region"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
