# AI-Based Exterior House Renovation & Cost Estimation System

## Approach Document — Architecture, Tech Stack & Step-by-Step Build Plan

**Role:** Full AI Engineer | **Deliverable:** Working prototype + documentation
**Scope:** Exterior-only, low-rise residential buildings, advisory cost estimates

---

## 1. Restated Requirements (What I Am Building)

The platform is a **pre-construction planning assistant**. One sentence per module:

| # | Module | Requirement |
|---|--------|-------------|
| R1 | Media Upload | Accept exterior house photos; validate quality; guide the user on bad input |
| R2 | Structure Identification | Detect walls, windows, balconies, pillars, parapet, gate, roof edges → editable region map |
| R3 | Material Selection | Catalog of materials (paint, stone cladding, tiles, texture, glass/metal railing, panels); apply per-region |
| R4 | Renovation Visualization | Photorealistic redesign of the **user's actual house** preserving structure; before/after compare |
| R5 | Surface Area Estimation | Approximate real-world area per region using reference-object scaling + perspective correction |
| R6 | Quantity Calculation | Material quantity + wastage + coverage per region (sq.ft paint, tile count, cladding qty, railing length) |
| R7 | Cost Estimation | Material + labor + per-category + grand total; user-editable rates with live recalculation |
| R8 | Report Generation | Downloadable PDF: original, redesign, materials, quantities, cost breakdown |

**Key insight that shapes the whole design:** this is really **two systems glued by one data structure**:

1. An **AI perception + generation pipeline** (R1–R4) whose output is a *region map* (polygon masks with labels).
2. A **deterministic calculation engine** (R5–R8) that consumes the region map. Costing must be **rule-based and transparent, never an AI guess** — a homeowner must be able to trace every rupee back to an area × rate formula. Trust in the numbers is the product.

The `region map` (label + pixel mask + estimated real-world area + assigned material) is the single contract between the AI half and the calculation half.

---

## 2. System Architecture

```
┌────────────────────────  FRONTEND (React) ─────────────────────────┐
│ Upload → Region Review/Edit → Material Picker → Before/After View  │
│                → Editable Cost Table → PDF Download                │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ REST (FastAPI)
┌──────────────────────────────┴─────────────────────────────────────┐
│                      BACKEND (Python / FastAPI)                    │
│                                                                    │
│  1. Ingestion Service      — quality checks, EXIF, resize          │
│  2. Segmentation Service   — facade component detection (GPU)      │
│  3. Rendering Service      — material application (GPU)            │
│  4. Estimation Engine      — scale inference → areas → quantities  │
│  5. Costing Engine         — rates × quantities, pure functions    │
│  6. Report Service         — HTML → PDF                            │
│                                                                    │
│  PostgreSQL (projects, catalogs, rates)  ·  S3/local (images)      │
│  Task queue (Celery/RQ) for GPU jobs  ·  Redis (job status)        │
└────────────────────────────────────────────────────────────────────┘
```

Why this shape:

- **GPU work (segmentation, rendering) is async** behind a task queue — jobs take 5–30 s; the UI polls a job status endpoint. Everything else is synchronous and instant.
- **Estimation and costing are pure functions** over the region map + catalog. Editing a rate re-runs only the costing engine (milliseconds) — no AI re-run. This directly satisfies R7's "modify rates → recalculated costs".
- Every stage writes its output to the project record, so the user can re-edit and resume (non-functional requirement: save/re-edit projects).

---

## 3. Tech Stack (with justification)

| Layer | Choice | Why |
|-------|--------|-----|
| Backend API | **Python + FastAPI** | The whole AI ecosystem is Python; FastAPI gives async, typed schemas (Pydantic), auto docs |
| Frontend | **React + Konva.js (or Fabric.js)** | Konva/Fabric give the interactive mask/polygon editing canvas needed for region review (R2) |
| Segmentation | **Grounded-SAM** (Grounding DINO + Segment Anything) | Zero-shot: text prompts like "window", "balcony railing", "wall" → boxes → SAM masks. **No training data needed** — critical for a prototype deadline. Fallback/upgrade: fine-tuned Mask2Former on facade datasets (CMP Facade, ETH Zurich Facade) |
| Image generation | **Stable Diffusion (SDXL) Inpainting + ControlNet** | Inpainting confines changes to the selected region mask; ControlNet (Canny/depth/MLSD conditioning) **preserves the original building geometry** — the requirement that rules out plain img2img |
| Simple materials (flat paint) | **Classical CV recolor** (OpenCV: recolor in LAB space, keep L-channel shading) | For plain paint, diffusion is overkill and less faithful; keeping the luminance channel preserves real lighting/shadows perfectly |
| Depth / perspective | **Depth-Anything or MiDaS** (monocular depth) + OpenCV homography | Supports perspective-corrected area estimation on angled photos |
| DB | **PostgreSQL** | Projects, region maps (JSONB), material catalog, rate cards |
| Queue | **Celery + Redis** (or RQ) | Async GPU jobs with progress states |
| Storage | **S3-compatible / local disk** | Original, masks, renders |
| PDF | **WeasyPrint or Playwright HTML→PDF** | Report = same HTML the UI shows; one template, two outputs |
| Serving GPU models | **Single GPU box (or Replicate/Modal API for the demo)** | For an interview prototype, hosted inference APIs (Replicate/Segmind) remove infra risk; architecture stays identical if self-hosted later |

**Deliberate non-choices:** no NeRF/3D reconstruction (single photo, low-rise scope — 2D + depth prior is enough and 10× simpler); no LLM anywhere in the costing path (determinism > cleverness where money is involved); no training a custom segmentation model up front (zero-shot first, fine-tune only if demo images prove it necessary).

---

## 4. Step-by-Step Approach

### Phase 0 — Ground work (Day 1)

1. Collect 15–20 test images: straight-on and angled shots of independent houses, varied lighting. These drive every accuracy decision later.
2. Define the **core data contract** (`RegionMap`): `{region_id, label, polygon/mask, pixel_area, real_area_sqft, confidence, material_id?}`. Every module reads/writes this.
3. Seed the **material catalog**: 8–12 materials with `unit (sqft/rft/piece)`, `coverage (e.g. paint: 120 sqft/L/coat)`, `wastage % default`, `material rate`, `labor rate`. Store as data, not code.

### Phase 1 — Upload & quality gate (R1)

1. Accept JPEG/PNG; strip EXIF; auto-rotate; resize to a working resolution (e.g. 1024–2048 px long edge).
2. Quality checks — each one produces a *user-actionable message*:
   - blur: variance-of-Laplacian below threshold → "image is blurry, retake"
   - exposure: histogram clipping → "too dark/bright"
   - building presence: run a cheap detector (Grounding DINO prompt "house/building") → reject selfies/interiors
   - resolution floor.
3. Persist project + image; return `project_id`.

### Phase 2 — Structure identification (R2) — the AI core #1

1. **Detection:** Grounding DINO with a prompt list: `wall, window, door, balcony, railing, pillar, parapet, gate, roof`. Take boxes above confidence threshold.
2. **Segmentation:** feed each box to SAM → pixel mask per component.
3. **Wall derivation trick:** SAM on "wall" is unreliable (walls are the background). More robust: segment the full building silhouette, then **wall = building − (windows ∪ doors ∪ balconies ∪ …)**. Set-subtraction beats direct detection for background classes.
4. Post-process: merge duplicate/overlapping masks (IoU), simplify masks to polygons (Douglas-Peucker) so the frontend can edit them, order regions by size.
5. **Human-in-the-loop review UI:** overlay colored polygons on the photo; user can rename a label, delete a false positive, redraw/adjust a polygon, or draw a missed region. *This step is what makes the whole product viable — it converts "model is 85% right" into "output is 100% usable". Budget real effort here.*

### Phase 3 — Material application & visualization (R3, R4) — the AI core #2

Route by material type (this two-path design is the most important rendering decision):

1. **Path A — color/finish changes (paint, texture paint):** classical CV. Convert to LAB, replace chroma inside the region mask with the target color, **keep the L (luminance) channel** → original shadows, lighting and wall texture remain, so the result looks like *their* house, guaranteed structure preservation, ~1 s, free.
2. **Path B — material replacement (stone cladding, tiles, panels, railings):** SDXL **inpainting** restricted to the region mask, conditioned with **ControlNet** (Canny edges or depth from the original) so window frames, edges and proportions survive; prompt template per catalog material ("natural slate stone cladding, exterior wall, photorealistic") + negative prompts. Generate 2–3 candidates, let the user pick.
3. Compose multi-region designs by applying regions sequentially (large background regions first), caching each intermediate so switching one region doesn't re-render the rest.
4. Before/after slider in the UI; save named design variants for comparison (R3 "switch between designs").

### Phase 4 — Surface area estimation (R5) — the honesty-critical module

Pixel masks → real-world sqft. Chain of methods, most reliable first:

1. **Reference-object scaling (primary):** detect the main door (already have it from Phase 2); assume standard height **7 ft** (Indian standard 6'8"–7'). `scale = 7 ft / door_pixel_height` → `sqft_per_pixel²= scale²`. Windows (~4 ft) and floor-to-floor height (~10 ft) act as cross-checks; if two references disagree wildly, lower the confidence and tell the user.
2. **Perspective correction:** for angled shots, estimate the wall plane (vanishing points via MLSD line detection, or plane fit on monocular depth) and compute a homography to a fronto-parallel view; measure pixel areas *after* rectification. Skip when the shot is nearly frontal (detect via vanishing-point angle).
3. **User override (trump card):** one optional input — "enter the width of the front wall in feet" — recalibrates the global scale and beats all vision estimates. Cheap to build, massively improves trust and accuracy.
4. Railings are measured in **running feet** (mask length along its principal axis × scale), not area.
5. **Every area carries a confidence band** (e.g. ±15%) shown in the UI and the report. The spec says "reasonably accurate, not perfect" — the professional move is to quantify the error, not hide it.

### Phase 5 — Quantity & cost engines (R6, R7) — deterministic, no AI

1. Quantity per region (pure functions over the catalog):
   - paint: `area × coats / coverage_per_litre` → litres
   - tiles/cladding: `ceil(area × (1 + wastage%) / piece_area)` → pieces (wastage default 10%, editable)
   - railing: running feet
2. Cost per region: `material_qty × material_rate + labor_qty × labor_rate`; category subtotals; grand total.
3. Rates live in a **rate-card table** (editable per project). Editing a rate re-runs only this engine — instant recalculation, satisfying R7 exactly.
4. Unit tests on this engine — it's the easiest module to test and the one where a bug destroys credibility.

### Phase 6 — Report (R8)

One HTML template: original photo, chosen redesign, region table (label, material, area ± confidence), quantity table, cost table with assumptions (door-height reference used, wastage %, rate source, date). Render to PDF (WeasyPrint). Explicit disclaimer: *advisory estimate, not a quotation*.

### Phase 7 — Hardening & demo prep

1. Run the full pipeline on all Phase-0 test images; record where segmentation or rendering fails → those become the documented limitations.
2. Pre-compute 2–3 polished demo projects (never demo live GPU generation cold).
3. Measure and state end-to-end timings.

---

## 5. How the Estimation Works (for the documentation deliverable)

`photo → masks (Grounded-SAM) → pixel areas → real scale (door = 7 ft reference, perspective-corrected, user-overridable) → sqft per region → quantity = f(area, coverage, wastage) → cost = quantity × editable rates`.

Every arrow is inspectable: the user can see the mask, the assumed reference, the computed area, the wastage %, and the rate — and can correct any of them. AI proposes; arithmetic decides; the human confirms.

---

## 6. Known Limitations (state these up front — they are the mark of a real engineer)

1. **Single-photo geometry:** only surfaces visible in the photo are measured; side/rear walls need extra photos (each processed independently) or manual entry.
2. **Scale accuracy** depends on the door-height assumption — non-standard doors skew everything until the user overrides with one real measurement (±10–20% typical error without override).
3. **Diffusion rendering is illustrative,** not a contractual finish sample; texture scale may drift on very large walls (tiling artifacts).
4. **Occlusions** (trees, vehicles, people) reduce measured area; the region editor is the mitigation.
5. **Extreme angles / heavy lens distortion** degrade both segmentation and homography; the quality gate rejects the worst cases.
6. **Rates are location-sensitive;** shipped defaults are placeholders — the editable rate card is the real mechanism.
7. Costs are **advisory** — no structural, waterproofing, or scaffolding engineering is computed.

---

## 7. Prototype Scope Recommendation (what to actually demo)

Full depth on the golden path, honest stubs elsewhere:

- ✅ Upload + quality gate → region detection + **editable region overlay** → paint (CV path) + one diffusion material (stone cladding) → door-reference area estimation with user override → editable cost table → PDF.
- ⏸️ Stubbed/simplified: auth, multi-user scaling, full 12-material catalog (ship 4–5), multi-photo fusion.

This demonstrates every required capability (upload, material application, redesigned output, area estimation, cost estimation) while spending effort where the AI-engineering signal is strongest: the segmentation + structure-preserving rendering + transparent estimation chain.
