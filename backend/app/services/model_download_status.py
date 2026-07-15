"""Report whether Grounded SAM weights exist under storage/models (no startup download)."""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.utils.model_paths import core_models_ready, is_repo_present, model_catalog, read_manifest


_SEG_STATUS_GROUPS = ("grounding_dino", "sam")


def get_model_status() -> dict[str, Any]:
    """Return readiness based on storage/models folders and manifest.json."""
    manifest = read_manifest()
    groups: dict[str, str] = {}

    if manifest and "models" in manifest:
        for key, info in manifest["models"].items():
            if key in _SEG_STATUS_GROUPS:
                groups[key] = str(info.get("status", "unknown"))

    for item in model_catalog():
        key, repo = item["key"], item["repo"]
        if key not in _SEG_STATUS_GROUPS:
            continue
        if is_repo_present(repo):
            groups[key] = groups.get(key, "ok")

    ready = core_models_ready()
    return {
        "ready": ready,
        "status": "ready" if ready else "missing",
        "groups": groups,
        "core_models_ready": ready,
        "message": (
            "Grounding DINO + SAM weights found in storage/models."
            if ready
            else "Missing weights. Run: python scripts/download_models.py"
        ),
        "models_dir": str(settings.MODEL_CACHE_DIR.resolve()),
    }
