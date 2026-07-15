"""Configure Hugging Face / local model cache paths from settings."""
from __future__ import annotations

import os

from app.core.config import settings


def configure_model_cache() -> None:
    """Point HF hub + transformers caches at MODEL_CACHE_DIR before any download/load."""
    cache_root = settings.MODEL_CACHE_DIR.resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    hf_home = cache_root / "huggingface"
    hf_home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(hf_home))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(hf_home / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(hf_home / "transformers"))
    if settings.HF_TOKEN:
        os.environ.setdefault("HF_TOKEN", settings.HF_TOKEN)
