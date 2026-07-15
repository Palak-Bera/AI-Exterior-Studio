# 06 — API Reference

Base URL (local): `http://localhost:8000`  
API prefix: `/api`  
Interactive docs: `http://localhost:8000/docs`

## Health & static

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | Liveness + backend meta |
| GET | `/storage/...` | Static serving of uploads, masks, outputs, textures |

## Ingestion

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/ingestion/upload` | `multipart/form-data` field `file` | `project_id`, image URL, size, warnings |
| GET | `/api/ingestion/projects/{project_id}` | — | Project metadata |

**Rejects:** unreadable image, wrong type, oversize, below minimum resolution.  
**Warns (still accepts):** blurry, too dark, too bright.

## Segmentation

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/segmentation/{project_id}` | `{ "categories": string[], "model"?: "grounded_sam" }` | RegionMap list (masks, polygons, areas) |
| GET | `/api/segmentation/{project_id}/regions` | — | Current RegionMap |
| PUT | `/api/segmentation/{project_id}/regions/{category}` | Mask edit payload (edited mask) | Updated region |

Empty `categories` → defaults: wall, balcony, rooftop, gate, window, door.

## Materials & rates

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/api/materials` | — | Catalog (paint + textures, rates, units) |
| PUT | `/api/materials/rates` | Rate update list | Confirmation |

## Meta

| Method | Path | Response |
|--------|------|----------|
| GET | `/api/meta/categories` | Default + full category taxonomy |
| GET | `/api/meta/models` | Available segmentation backends |
| POST | `/api/meta/models/activate` | Activate model key |
| GET | `/api/meta/render-modes` | Available render modes (`classical`) |
| GET | `/api/meta/model-status` | Download / readiness of weights |

## Rendering

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/rendering/{project_id}` | `{ "selections": [{ category, material_key, color? }], "mode"?: "classical" }` | `input_url`, `output_url`, applied list |

Requires segmented regions for selected categories.

## Costing

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/costing/{project_id}/estimate` | selections + `facade_width_m`, `facade_height_m`, optional waste | Lines, subtotal, total INR, disclaimer |

See [04_Estimation_and_Costing.md](04_Estimation_and_Costing.md) for formulas.

## Reporting

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/reporting/{project_id}/pdf` | selections + facade dims (same spirit as costing) | PDF download |

Requires a prior successful render (`output_url` present).

## Typical error codes

| Code | Meaning |
|------|---------|
| 404 | Unknown project |
| 422 | Unusable upload, missing region, unknown material, empty selections, no render for PDF |

## RegionMap fields (serialization)

| Field | Description |
|-------|-------------|
| `category` | Facade label |
| `mask_url` | Tinted RGBA preview |
| `polygons` | Contours for overlays |
| `pixel_area` | Mask pixel count |
| `instance_count` | Merged detections |
| `confidence` | Mean detector score |
