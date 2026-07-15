"""Facade category taxonomy shared across the pipeline.

Each category maps a UI label to the free-text prompt(s) fed to Grounding DINO
and to a display color used for mask overlays in the frontend.
"""
from __future__ import annotations

# category_key -> {prompts, color (RGB), derive}
CATEGORIES: dict[str, dict] = {
    "wall": {
        "label": "Walls",
        "prompts": ["wall", "building facade", "exterior wall"],
        "color": (239, 68, 68),
        # Walls are a background class; derive as building - openings.
        "derive_from_building": True,
    },
    "balcony": {
        "label": "Balconies",
        "prompts": ["balcony", "balcony railing"],
        "color": (245, 158, 11),
        "derive_from_building": False,
    },
    "rooftop": {
        "label": "Rooftop",
        "prompts": ["roof", "rooftop"],
        "color": (168, 85, 247),
        "derive_from_building": False,
    },
    "gate": {
        "label": "Gate",
        "prompts": ["gate", "front gate", "metal gate"],
        "color": (14, 165, 233),
        "derive_from_building": False,
    },
    "window": {
        "label": "Windows",
        "prompts": ["window"],
        "color": (59, 130, 246),
        "derive_from_building": False,
    },
    "door": {
        "label": "Door",
        "prompts": ["door"],
        "color": (34, 197, 94),
        "derive_from_building": False,
    },
    "railing": {
        "label": "Railing",
        "prompts": ["railing"],
        "color": (250, 204, 21),
        "derive_from_building": False,
    },
    "pillar": {
        "label": "Pillar",
        "prompts": ["pillar", "column"],
        "color": (236, 72, 153),
        "derive_from_building": False,
    },
}

DEFAULT_CATEGORIES = ["wall", "balcony", "rooftop", "gate", "window", "door"]

# Openings subtracted from the building silhouette to derive the wall mask.
OPENING_CATEGORIES = ["window", "door", "balcony", "gate", "railing"]


def resolve_categories(requested: list[str] | None) -> list[str]:
    if not requested:
        return list(DEFAULT_CATEGORIES)
    return [c for c in requested if c in CATEGORIES]
