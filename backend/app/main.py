"""FastAPI application entrypoint.

Wires the layers together: mounts static storage, registers the API router,
creates tables and seeds the material catalog on startup.
Warms Grounded SAM in a background thread so the UI can open after reload sooner.
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import settings
from app.core.logging_config import get_logger, setup_logging
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.catalog import seed_materials
from app.services.segmentation import activate_model, get_active_model, list_models
from app.utils.model_cache import configure_model_cache

# Import models so their tables are registered on the metadata.
from app import models  # noqa: F401

setup_logging()
logger = get_logger("app")


def _warmup_segmentation_model() -> None:
    """Load default Grounded SAM into RAM after server starts accepting traffic."""
    key = settings.DEFAULT_SEGMENTATION_MODEL or "grounded_sam"
    try:
        logger.info(
            "Startup warmup: loading segmentation model=%s (may take a few minutes on CPU)…",
            key,
        )
        t0 = time.perf_counter()
        activate_model(key)
        logger.info(
            "Startup warmup complete: model=%s (%.1fs)",
            key,
            time.perf_counter() - t0,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Startup warmup failed for '%s' — model will load on first use instead",
            key,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_model_cache()
    logger.info(
        "Starting %s | default_segmentation_model=%s | log_level=%s",
        settings.APP_NAME,
        settings.DEFAULT_SEGMENTATION_MODEL,
        settings.LOG_LEVEL,
    )
    Base.metadata.create_all(bind=engine)
    from app.db.migrate import ensure_material_pricing_columns

    ensure_material_pricing_columns(engine)
    logger.info("Database tables ensured (%s)", settings.DATABASE_URL)
    with SessionLocal() as db:
        seed_materials(db)
    try:
        from app.services.report import ensure_brand_logo
        ensure_brand_logo()
    except Exception:  # noqa: BLE001
        logger.exception("Brand logo setup skipped")
    logger.info("Storage dir: %s", settings.STORAGE_DIR.resolve())
    # Load model in the background so /health stays up during slow CPU weight load.
    threading.Thread(
        target=_warmup_segmentation_model,
        name="sam-warmup",
        daemon=True,
    ).start()
    logger.info("Startup complete - accepting requests (model warming in background)")
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = uuid.uuid4().hex[:8]
    start = time.perf_counter()
    logger.info("--> [%s] %s %s", req_id, request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        logger.exception(
            "xxx [%s] %s %s failed after %.0f ms",
            req_id,
            request.method,
            request.url.path,
            elapsed,
        )
        raise
    elapsed = (time.perf_counter() - start) * 1000
    logger.info(
        "<-- [%s] %s %s -> %s (%.0f ms)",
        req_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/health")
def health():
    models = list_models()
    active = get_active_model()
    loaded = any(m.get("key") == active and m.get("loaded") for m in models)
    return {
        "status": "ok",
        "default_segmentation_model": settings.DEFAULT_SEGMENTATION_MODEL,
        "default_render_mode": "classical",
        "active_segmentation_model": active,
        "model_loaded": loaded,
    }
