"""Local model directory layout under storage/models (outside application code)."""
from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings

MANIFEST_NAME = "manifest.json"


def repo_dir_name(repo_id: str) -> str:
    """IDEA-Research/grounding-dino-tiny -> IDEA-Research--grounding-dino-tiny"""
    return repo_id.replace("/", "--")


def local_repo_path(repo_id: str) -> Path:
    return settings.MODEL_CACHE_DIR / repo_dir_name(repo_id)


def manifest_path() -> Path:
    return settings.MODEL_CACHE_DIR / MANIFEST_NAME


def resolve_model_source(repo_id: str) -> str:
    """Prefer a local snapshot in storage/models; fall back to the HF repo id."""
    local = local_repo_path(repo_id)
    if local.is_dir() and any(local.iterdir()):
        return str(local.resolve())
    return repo_id


def read_manifest() -> dict | None:
    path = manifest_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_manifest(payload: dict) -> None:
    settings.MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def model_catalog() -> list[dict]:
    """Grounded SAM weights downloaded by scripts/download_models.py."""
    return [
        {"key": "grounding_dino", "repo": settings.GROUNDING_DINO_MODEL, "gated": False},
        {"key": "sam", "repo": settings.SAM_MODEL, "gated": False},
    ]


def is_repo_present(repo_id: str) -> bool:
    """True when a usable local snapshot exists (ignores empty / incomplete dirs)."""
    local = local_repo_path(repo_id)
    if not local.is_dir():
        return False
    markers = (
        "config.json",
        "model_index.json",
        "preprocessor_config.json",
        "pytorch_model.bin",
        "model.safetensors",
    )
    for marker in markers:
        if (local / marker).is_file():
            return True
    for path in local.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.lower()
        if name.endswith((".safetensors", ".bin", ".pt", ".ckpt")) and ".cache" not in path.parts:
            return True
    return False


def core_models_ready() -> bool:
    return is_repo_present(settings.GROUNDING_DINO_MODEL) and is_repo_present(settings.SAM_MODEL)
