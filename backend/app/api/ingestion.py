"""Ingestion routes - upload + project retrieval."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.session import get_db
from app.models.project import Project
from app.schemas.project import IngestResponse, ProjectOut
from app.services import ingestion_engine
from app.utils.image_io import to_media_url

logger = get_logger("api.ingestion")
router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _to_out(project: Project) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        filename=project.filename,
        image_url=to_media_url(project.image_path),
        width=project.width,
        height=project.height,
        status=project.status,
        created_at=project.created_at,
    )


@router.post("/upload", response_model=IngestResponse)
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()
    try:
        result = ingestion_engine.ingest(raw, file.filename or "upload.jpg", file.content_type)
    except ingestion_engine.IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    project = Project(
        id=result.project_id,
        filename=result.filename,
        image_path=str(result.image_path),
        width=result.width,
        height=result.height,
        status="ingested",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info("Project created: id=%s dims=%dx%d warnings=%d",
                project.id, project.width, project.height, len(result.warnings))

    return IngestResponse(project=_to_out(project), warnings=result.warnings)


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_out(project)
