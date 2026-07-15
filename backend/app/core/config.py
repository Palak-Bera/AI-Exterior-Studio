"""Central application configuration.

All tunables (model names, thresholds, storage paths, segmentation backend)
live here so the engines stay free of hard-coded constants.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "AI Exterior Studio"
    API_PREFIX: str = "/api"
    LOG_LEVEL: str = "INFO"

    # Storage (relative to the backend working directory)
    STORAGE_DIR: Path = Path("storage")

    # Database — on Railway, prefer sqlite:////app/storage/ai_exterior_studio.db
    # so the file lives on the mounted volume.
    DATABASE_URL: str = "sqlite:///./ai_exterior_studio.db"

    # CORS — JSON list or comma-separated origins (Railway frontend public URL).
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
        if value is None or value == "":
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                return json.loads(text)
            return [part.strip() for part in text.split(",") if part.strip()]
        return value


    # ---- Segmentation Engine -------------------------------------------------
    # Only backend: Grounding DINO (tiny) + SAM (vit-base).
    DEFAULT_SEGMENTATION_MODEL: str = "grounded_sam"

    GROUNDING_DINO_MODEL: str = "IDEA-Research/grounding-dino-tiny"
    SAM_MODEL: str = "facebook/sam-vit-base"

    # Optional Hugging Face token (public DINO/SAM repos usually need none).
    HF_TOKEN: str = ""

    # Local model weights directory (storage/models — outside app code).
    # Run `python scripts/download_models.py` once to populate.
    MODEL_CACHE_DIR: Path = Path("storage/models")

    TORCH_THREADS: int = 0  # 0 = let torch decide

    # Detection thresholds
    BOX_THRESHOLD: float = 0.30
    TEXT_THRESHOLD: float = 0.25

    # ---- Rendering Engine ----------------------------------------------------
    # Paint/texture is Classical CV only (LAB recolor + tiling). ControlNet / SD
    # inpainting are disabled to fit ~8 GB RAM machines.
    DEFAULT_RENDER_MODE: str = "classical"
    # Kept for env compatibility; classical is the only supported mode.
    RENDER_ALLOW_FALLBACK: bool = False

    # Legacy ControlNet settings (unused — weights not loaded at runtime).
    SD_INPAINT_MODEL: str = "stable-diffusion-v1-5/stable-diffusion-inpainting"
    CONTROLNET_MODEL: str = "lllyasviel/control_v11p_sd15_canny"
    SD_WORKING_LONG_EDGE: int = 768
    SD_STEPS: int = 25
    SD_GUIDANCE: float = 7.5
    CONTROLNET_SCALE: float = 0.7
    CANNY_LOW: int = 100
    CANNY_HIGH: int = 200

    # ---- Ingestion Engine ----------------------------------------------------
    MAX_IMAGE_LONG_EDGE: int = 1536      # stored working resolution
    SEG_WORKING_LONG_EDGE: int = 1024    # downscale for CPU inference
    MIN_IMAGE_LONG_EDGE: int = 512       # reject anything smaller
    BLUR_LAPLACIAN_MIN: float = 60.0     # below => too blurry
    DARK_MEAN_MIN: float = 25.0          # below => too dark
    BRIGHT_MEAN_MAX: float = 235.0       # above => too bright
    ALLOWED_CONTENT_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]
    MAX_UPLOAD_BYTES: int = 20 * 1024 * 1024  # 20 MB


settings = Settings()

# Derived storage sub-directories - created eagerly at import time.
UPLOAD_DIR = settings.STORAGE_DIR / "uploads"
MASK_DIR = settings.STORAGE_DIR / "masks"
OUTPUT_DIR = settings.STORAGE_DIR / "outputs"
TEXTURE_DIR = settings.STORAGE_DIR / "textures"

for _d in (UPLOAD_DIR, MASK_DIR, OUTPUT_DIR, TEXTURE_DIR):
    _d.mkdir(parents=True, exist_ok=True)
