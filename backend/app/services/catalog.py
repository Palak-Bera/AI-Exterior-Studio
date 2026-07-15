"""Material catalog — paint + textures discovered from storage/textures/.

Folder layout (served under /storage/textures/...):
  wall_cadding/      → Wall Cladding options
  wall_tiles/        → Wall Tile options
  texture_patterns/  → Texture Pattern options
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import TEXTURE_DIR
from app.core.logging_config import get_logger
from app.models.material import Material
from app.services.costing import default_rate_for_group

logger = get_logger("catalog")

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# (subdir under textures/, UI group key, display group label)
_TEXTURE_GROUPS: list[tuple[str, str, str]] = [
    ("wall_cadding", "cladding", "Wall Cladding"),
    ("wall_tiles", "tiles", "Wall Tiles"),
    ("texture_patterns", "patterns", "Texture Patterns"),
]


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return s or "texture"


def discover_texture_materials() -> list[dict]:
    """Scan texture folders and build texture material rows."""
    items: list[dict] = []
    for subdir, group, group_label in _TEXTURE_GROUPS:
        folder = TEXTURE_DIR / subdir
        if not folder.is_dir():
            continue
        files = sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
        )
        for i, path in enumerate(files, start=1):
            key = f"{group}_{_slug(path.stem)}"
            items.append({
                "key": key,
                "name": f"{group_label} {i}",
                "render_path": "texture",
                "default_color": None,
                "texture_path": f"storage/textures/{subdir}/{path.name}",
                "group": group,
                "group_label": group_label,
            })
    return items


def material_catalog() -> list[dict]:
    """Paint + discovered textures."""
    paint = {
        "key": "paint",
        "name": "Solid Paint",
        "render_path": "paint",
        "default_color": "#1E3A5F",
        "texture_path": None,
        "group": "paint",
        "group_label": "Paint",
    }
    return [paint, *discover_texture_materials()]


def group_for_material(render_path: str, texture_path: str | None) -> tuple[str, str]:
    if render_path == "paint":
        return "paint", "Paint"
    path = (texture_path or "").replace("\\", "/")
    for subdir, group, label in _TEXTURE_GROUPS:
        if f"/{subdir}/" in f"/{path}":
            return group, label
    return "texture", "Textures"


def seed_materials(db: Session) -> None:
    """Upsert catalog from disk every startup so new texture files appear in the UI."""
    catalog = material_catalog()
    by_key = {m.key: m for m in db.query(Material).all()}
    seen: set[str] = set()
    added = updated = 0

    for item in catalog:
        seen.add(item["key"])
        group = item.get("group") or "texture"
        default_rate = default_rate_for_group(group)
        existing = by_key.get(item["key"])
        if existing is None:
            db.add(
                Material(
                    id=uuid.uuid4().hex,
                    key=item["key"],
                    name=item["name"],
                    render_path=item["render_path"],
                    default_color=item.get("default_color"),
                    texture_path=item.get("texture_path"),
                    is_active=True,
                    rate_inr=default_rate,
                    unit="sqm",
                )
            )
            added += 1
            continue
        changed = False
        for field in ("name", "render_path", "default_color", "texture_path"):
            new_val = item.get(field)
            if getattr(existing, field) != new_val:
                setattr(existing, field, new_val)
                changed = True
        if not existing.is_active:
            existing.is_active = True
            changed = True
        # First-time pricing populate (do not overwrite Cost-page edits).
        if not getattr(existing, "rate_inr", None) or float(existing.rate_inr or 0) <= 0:
            existing.rate_inr = default_rate
            changed = True
        if not getattr(existing, "unit", None):
            existing.unit = "sqm"
            changed = True
        if changed:
            updated += 1

    # Deactivate old placeholder textures (stone/tile/plaster) not on disk anymore.
    for key, row in by_key.items():
        if key not in seen and row.render_path == "texture":
            if row.is_active:
                row.is_active = False
                updated += 1

    db.commit()
    logger.info(
        "Material catalog synced: %d total, +%d new, ~%d updated (textures dir=%s)",
        len(catalog),
        added,
        updated,
        TEXTURE_DIR.resolve(),
    )
