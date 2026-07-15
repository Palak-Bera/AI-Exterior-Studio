# 01 - Architecture & MVC

## System architecture

```mermaid
graph TD
    subgraph FE [Frontend - Next.js]
        View[Views: pages + components]
        Ctrl[Controllers: hooks / handlers]
        ApiModel[Model: typed API client + types]
        View --> Ctrl --> ApiModel
    end

    ApiModel -->|REST JSON| Routers

    subgraph BE [Backend - FastAPI]
        Routers[API: routers] --> Services
        Services[Services: 3 engines] --> Models
        Models[Models: SQLAlchemy ORM]
        Routers --> Schemas[Schemas: DTO / serialization]
        Services --> Storage[(Files: uploads / masks / outputs)]
        Models --> DB[(SQLite / Postgres)]
    end
```

Everything runs on CPU. Segmentation is the only slow stage; it is designed so
the image embedding is computed once and reused across categories (see `03`).

## Backend layers (models / schemas / services / api)

Conventional FastAPI structure - four clear layers:

- **models** - persistence + domain state (SQLAlchemy ORM).
- **schemas** - Pydantic request/response DTOs (serialization).
- **services** - the three engines: framework-agnostic, unit-testable business logic.
- **api** - FastAPI routers: HTTP routing, validation, wiring the layers together.

## Backend folder structure

```
backend/
  app/
    core/config.py            # all tunables (models, thresholds, paths)
    db/
      base.py                 # declarative Base
      session.py              # engine + get_db dependency
    models/                   # SQLAlchemy ORM
      project.py  region.py  material.py
    schemas/                  # Pydantic DTOs (serialization)
      project.py  region.py  rendering.py  material.py
    services/                 # business logic - the engines
      ingestion_engine.py
      segmentation/           # Grounded SAM (DINO + SAM vit-base)
        base.py  common.py  grounded_sam.py
      rendering/              # pluggable render modes + registry
        base.py  classical.py  controlnet.py
      catalog.py
    api/                      # FastAPI routers (aggregated in api/__init__.py)
      ingestion.py  segmentation.py  rendering.py  materials.py  meta.py
    utils/
      categories.py           # category -> prompts + color taxonomy
      image_io.py             # URL mapping, mask save, polygonize
    main.py                   # app wiring, static mount, lifespan seed
  scripts/generate_textures.py
  storage/{uploads,masks,outputs,textures}
  requirements.txt
```

## Frontend folder structure

```
frontend/
  app/
    layout.tsx
    page.tsx                       # upload view
    studio/[projectId]/page.tsx    # studio controller view
    globals.css
  components/                      # presentational views
    UploadDropzone.tsx
    StudioCanvas.tsx
    CategoryPanel.tsx
    MaterialPicker.tsx
    BeforeAfter.tsx
  lib/                             # model + controller
    api.ts   types.ts   config.ts
```

## Request / data flow (happy path)

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Next.js
    participant BE as FastAPI
    participant SEG as Segmentation Engine
    participant REN as Rendering Engine

    U->>FE: drop photo
    FE->>BE: POST /api/ingestion/upload
    BE-->>FE: project_id + image_url + warnings
    U->>FE: click "Auto-detect"
    FE->>BE: POST /api/segmentation/{id} {categories}
    BE->>SEG: segment_image(path, categories)
    SEG-->>BE: {category: mask}
    BE-->>FE: RegionMap (mask urls + polygons)
    U->>FE: pick category + material
    FE->>BE: POST /api/rendering/{id} {selections}
    BE->>REN: render(image, masks, selections)
    REN-->>BE: output image
    BE-->>FE: input_url + output_url
    FE-->>U: before/after
```

## Async note (CPU reality)

Segmentation on CPU can take ~10-40s the first time. This build runs it
synchronously for simplicity; the documented upgrade path is a background job
(Celery/RQ + Redis) with a `GET /segmentation/{id}/status` poll, without
changing the RegionMap contract.

## Tech stack

| Layer | Choice |
|-------|--------|
| API | FastAPI + Uvicorn |
| ORM / DB | SQLAlchemy 2.x + SQLite (Postgres-ready) |
| Validation | Pydantic v2 + pydantic-settings |
| CV | OpenCV (headless), NumPy, Pillow |
| Segmentation | torch (CPU), transformers (Grounding DINO + SAM) |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind |
