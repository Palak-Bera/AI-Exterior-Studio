"""Meta routes - category taxonomy, model catalog, activate selected model."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import rendering, segmentation
from app.services.model_download_status import get_model_status
from app.services.segmentation import BackendUnavailable
from app.utils.categories import CATEGORIES, DEFAULT_CATEGORIES

router = APIRouter(prefix="/meta", tags=["meta"])


class ActivateModelRequest(BaseModel):
    model: str = Field(..., description="Segmentation model key to load into memory")


@router.get("/categories")
def list_categories():
    return {
        "default": DEFAULT_CATEGORIES,
        "categories": [
            {
                "key": key,
                "label": cfg["label"],
                "color": "#%02x%02x%02x" % cfg["color"],
            }
            for key, cfg in CATEGORIES.items()
        ],
    }


@router.get("/models")
def list_models():
    return {
        "models": segmentation.list_models(),
        "active": segmentation.get_active_model(),
    }


@router.post("/models/activate")
def activate_model(payload: ActivateModelRequest):
    """Load the chosen segmentation model into RAM (unloads others)."""
    try:
        return segmentation.activate_model(payload.model)
    except BackendUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"Failed to load model '{payload.model}': {exc}"
        ) from exc


@router.get("/render-modes")
def list_render_modes():
    return {"modes": rendering.list_render_modes()}


@router.get("/model-status")
def model_status():
    return get_model_status()
