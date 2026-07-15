"""Material model - the catalog of finishes that can be applied to a region."""
from __future__ import annotations

from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    # "paint" -> LAB recolor path, "texture" -> tiling path
    render_path: Mapped[str] = mapped_column(String(16))
    default_color: Mapped[str | None] = mapped_column(String(9), nullable=True)
    texture_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Cost page: rate in Indian Rupees per unit (sqm or pcs)
    rate_inr: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(16), default="sqm")  # sqm | unit
