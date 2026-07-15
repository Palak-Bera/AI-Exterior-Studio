"""Download Grounded SAM weights into storage/models.

Run once manually (not at server startup):

    cd backend
    python scripts/download_models.py

Already-downloaded models are skipped.
"""
from __future__ import annotations

import time
from typing import Any

from app.core.config import settings
from app.core.logging_config import get_logger
from app.utils.model_cache import configure_model_cache
from app.utils.model_paths import (
    is_repo_present,
    local_repo_path,
    model_catalog,
    write_manifest,
)

logger = get_logger("model_download")


def _hf_token() -> str | None:
    return settings.HF_TOKEN.strip() or None


def _download_repo(repo_id: str, *, gated: bool = False) -> str:
    from huggingface_hub import snapshot_download

    dest = local_repo_path(repo_id)
    dest.mkdir(parents=True, exist_ok=True)
    token = _hf_token()
    logger.info("Downloading %s -> %s", repo_id, dest)
    path = snapshot_download(
        repo_id=repo_id,
        local_dir=str(dest),
        token=token,
    )
    logger.info("  done: %s", path)
    return path


def download_all_models() -> dict[str, Any]:
    """Download missing models into storage/models; skip ones already present."""
    configure_model_cache()
    catalog = model_catalog()
    results: dict[str, dict] = {}
    t0 = time.perf_counter()

    logger.info(
        "Model sync into %s (HF_TOKEN=%s) — skipping already downloaded",
        settings.MODEL_CACHE_DIR.resolve(),
        "set" if _hf_token() else "missing",
    )

    for item in catalog:
        key, repo, gated = item["key"], item["repo"], item["gated"]
        dest = local_repo_path(repo)
        if is_repo_present(repo):
            logger.info("Skipping %s (already present at %s)", key, dest)
            results[key] = {
                "status": "ok",
                "repo": repo,
                "path": str(dest.resolve()),
                "skipped": True,
            }
            continue
        try:
            path = _download_repo(repo, gated=gated)
            results[key] = {
                "status": "ok",
                "repo": repo,
                "path": str(dest.resolve()),
                "snapshot": path,
                "skipped": False,
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to download %s (%s): %s", key, repo, exc)
            results[key] = {
                "status": f"failed: {exc}",
                "repo": repo,
                "path": str(dest.resolve()),
                "skipped": False,
            }

    manifest = {
        "version": 1,
        "finished_at": time.time(),
        "duration_sec": round(time.perf_counter() - t0, 1),
        "models": results,
    }
    write_manifest(manifest)
    logger.info("Manifest written: %s", settings.MODEL_CACHE_DIR / "manifest.json")
    logger.info("Download finished in %.1fs", time.perf_counter() - t0)
    return manifest
