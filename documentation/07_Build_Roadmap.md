# 07 - Build Roadmap

Phased build order. Phases 0-5 are implemented in this repository; phases 6+ are
the documented next steps.

## Phase 0 - Skeleton (done)

- FastAPI skeleton: `core/config`, `db`, `models`, `schemas`, `services`, `api`,
  `main.py`.
- Next.js scaffold: App Router, Tailwind, `lib/` API client.

## Phase 1 - Ingestion Engine (done)

- Upload endpoint, validation + normalization, `Project` persistence.
- Frontend upload dropzone with warnings.

## Phase 2 - Segmentation Engine (done)

- Grounded-SAM (Grounding DINO tiny + SAM vit-base) on CPU.
- Category taxonomy + prompt mapping, wall derivation, OpenCV fallback.
- Region persistence + polygonization; category select UI + mask overlay.

## Phase 2b - Segmentation model (done)

- Grounded SAM only (`services/segmentation/`): Grounding DINO tiny + SAM vit-base.
- `GET /meta/models` + `model` field on the segmentation request; 503 if weights missing.
- Frontend loads Grounded SAM at startup.

## Phase 3 - Rendering Engine (done)

- LAB recolor (paint) + physical texture tiling (stone/tile/plaster).
- Multi-region sequential compositing; material catalog seed.
- Material picker + before/after slider.

## Phase 3b - Render-mode selector (done)

- Pluggable render backend registry (`services/rendering/`): `classical` +
  `controlnet` behind `render_image(mode)`.
- `GET /meta/render-modes` + `mode` field on the render request; 503 on
  unavailable modes (or opt-in `RENDER_ALLOW_FALLBACK`).
- ControlNet (SD inpaint + Canny) for photorealistic filling; frontend
  `RenderModeSelector` bar; optional via `requirements-diffusion.txt` (GPU/slow CPU).

## Phase 4 - Wiring & catalog (done)

- `/meta/categories`, `/materials`, static storage mount, CORS, lifespan seed.
- Placeholder texture generator.

## Phase 5 - Docs (done)

- This `documentation/` set.

## Phase 6 - Hardening (next)

- Swap SAM vit-base for MobileSAM/FastSAM; ONNX/OpenVINO + int8 for speed.
- Make segmentation an async job (Celery/RQ + Redis) with status polling.
- Cache SAM image embeddings per project.
- Mask-refinement canvas (brush/eraser) posting edits back.
- Unit tests for engines; pin real tileable textures.

## Phase 7 - Future engines (out of scope now)

- **Estimation Engine** - pixel area -> real area via door-height reference +
  perspective correction; writes `real_area_sqft` onto the RegionMap.
- **Cost Engine** - deterministic quantity + cost from area x editable rates.
- **Report** - HTML -> PDF.

## First-run checklist

Backend:
```powershell
cd backend
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python scripts/generate_textures.py
uvicorn app.main:app --reload --port 8000
```

Frontend:
```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

## Model download list (one-time, ~1 GB)

| Model | Repo | Size |
|-------|------|------|
| Grounding DINO tiny | `IDEA-Research/grounding-dino-tiny` | ~700 MB |
| SAM vit-base | `facebook/sam-vit-base` | ~375 MB |

Set `DEFAULT_SEGMENTATION_MODEL=grounded_sam` (only supported option).
Run `python scripts/download_models.py` once to fetch DINO + SAM weights.

## Known limitations

1. Single photo - only visible surfaces are segmentable.
2. CPU segmentation latency (~10-40 s cold); mitigated by the Phase 6 upgrades.
3. Wall derivation depends on a "building" detection; falls back to GrabCut.
4. Grounding DINO may miss unusual balconies/gates; a refinement canvas is the
   planned mitigation.
5. Texture rendering is illustrative; tiling scale uses an assumed door height.
6. Estimation/cost intentionally absent.
