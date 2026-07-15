# AI Exterior Studio - Backend (FastAPI)

MVC FastAPI service that powers the three engines:

1. **Ingestion Engine** - validate + normalize uploads (`app/services/ingestion_engine.py`)
2. **Segmentation Engine** - Grounding DINO + SAM vit-base (`app/services/segmentation/`)
3. **Rendering Engine** - Classical CV paint/texture (`app/services/rendering/`)

### Segmentation (Grounded SAM only)

| Key | Model | Runs on | Notes |
|-----|-------|---------|-------|
| `grounded_sam` | Grounding DINO (tiny) + SAM (vit-base) | CPU | Walls, windows, facades, openings |

### Render mode (Classical only — 8 GB RAM)

| Key | Mode | Runs on | Notes |
|-----|------|---------|-------|
| `classical` | LAB recolor / texture tiling | CPU | ControlNet / SD disabled |

## Layout

```
app/
  models/     # SQLAlchemy ORM (Project, Region, Material)
  schemas/    # Pydantic request/response DTOs
  services/   # business logic - the three engines
  api/        # FastAPI routers (ingestion, segmentation, rendering, materials, meta)
  utils/      # shared helpers (categories, image IO)
  core/       # config
  db/         # engine + session
```

## Setup (CPU-only, no GPU required)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install CPU build of torch + matching torchvision first
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Generate placeholder material textures
python scripts/generate_textures.py

# Download Grounding DINO + SAM weights (one-time → storage/models/)
python scripts/download_models.py

# Run
uvicorn app.main:app --reload --port 8000
```

| Model | Folder under `storage/models/` |
|-------|-------------------------------|
| Grounding DINO tiny | `IDEA-Research--grounding-dino-tiny/` |
| SAM vit-base | `facebook--sam-vit-base/` |

The server does **not** download at startup — run the script once manually.

API docs: http://localhost:8000/docs

## Docker

```powershell
docker build -t ai-exterior-studio-backend .
docker run -p 8000:8000 -v aes_storage:/app/storage ai-exterior-studio-backend
```

Run `python scripts/download_models.py` once so weights land in `storage/models/`.

## Core flow

| Step | Endpoint |
|------|----------|
| Upload photo | `POST /api/ingestion/upload` |
| Segment categories | `POST /api/segmentation/{project_id}` `{ "categories": ["wall","balcony","rooftop","gate"], "model": "grounded_sam" }` |
| Read region map | `GET /api/segmentation/{project_id}/regions` |
| List materials | `GET /api/materials` |
| List categories | `GET /api/meta/categories` |
| List models | `GET /api/meta/models` |
| List render modes | `GET /api/meta/render-modes` |
| Render | `POST /api/rendering/{project_id}` `{ "selections": [{"category":"wall","material_key":"paint","color":"#1E3A8A"}], "mode": "classical" }` |

Estimation and cost are intentionally out of scope for this build.
