"""API layer - FastAPI routers grouped into a single api_router."""
from fastapi import APIRouter

from app.api import costing, ingestion, materials, meta, rendering, reporting, segmentation

api_router = APIRouter()
api_router.include_router(ingestion.router)
api_router.include_router(segmentation.router)
api_router.include_router(rendering.router)
api_router.include_router(reporting.router)
api_router.include_router(costing.router)
api_router.include_router(materials.router)
api_router.include_router(meta.router)
