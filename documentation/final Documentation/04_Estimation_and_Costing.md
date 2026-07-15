# 04 — Estimation & Costing

**Problem-statement deliverable:** *Documentation explaining how the estimation works*

Source of truth in code: `backend/app/services/costing.py`.

## 1. Design principle

**Costing is deterministic.** Segmentation supplies pixel masks; the user supplies approximate facade dimensions and (optionally) rates. No generative model invents rupees. Every line item is explainable as quantity × rate.

## 2. Inputs

| Input | Source | Default |
|-------|--------|---------|
| Category masks (`pixel_area`, `instance_count`) | Segmentation / mask edit | — |
| Image size (`width` × `height`) | Ingested project image | — |
| Facade width & height (m) | Studio UI | 12 m × 9 m |
| Waste factor | Engine constant | **1.10** (10%) |
| Material `rate_inr` & `unit` | Material catalog / Cost page | Group defaults if rate ≤ 0 |
| Material selections | Studio (category → material) | — |

## 3. Surface / quantity model

### 3.1 Facade area

\[
A_{\text{facade}} = W_{\text{facade}} \times H_{\text{facade}} \quad (\mathrm{m}^2)
\]

Widths/heights are clamped to a minimum of **0.5 m** to avoid division-by-zero nonsense.

### 3.2 Area-based materials (`unit == "sqm"`)

Most facade finishes (paint, cladding, tiles, patterns):

\[
q = \left(\frac{\text{pixel\_area}}{\text{image\_width} \times \text{image\_height}}\right) \times A_{\text{facade}} \times w
\]

where \(w \geq 1\) is the waste factor (default **1.10**).

- If \(0 < q < 0.25\), quantity is raised to **0.25 sqm** (avoids ₹0 for tiny valid patches).  
- Display unit: **sqm**.

**Interpretation:** The fraction of the photo covered by the mask is treated as the same fraction of the user-stated facade area. This is approximate and assumes a roughly frontal elevation.

### 3.3 Piece-based categories (`unit == "unit"`)

Categories: **gate, door, window, pillar**.

\[
q = \max(1,\; \text{instance\_count})
\]

Display unit: **pcs**.

### 3.4 What is *not* computed (yet)

- Paint volume in litres (no coats × coverage curve)  
- Tile packing by piece size  
- Railing length in running metres  
- Separate labour vs material columns  

Those are natural extensions of the same RegionMap (see Limitations).

## 4. Cost formula

For each selection line:

\[
\text{line\_total} = q \times \text{rate\_inr}
\]

\[
\text{grand total} = \sum \text{line\_totals}
\]

Subtotal equals total in the current build (no tax / contingency line beyond the waste factor).

Currency: **INR (₹)**. PDF uses `Rs.` for font glyph safety.

## 5. Default rates (₹)

Used when the stored rate is missing or ≤ 0:

| Material group | Default rate | Typical unit |
|----------------|--------------|--------------|
| paint | 55 | ₹/sqm |
| cladding | 2200 | ₹/sqm |
| tiles | 1100 | ₹/sqm |
| patterns | 1500 | ₹/sqm |
| texture (fallback) | 1200 | ₹/sqm |

Users override these on **`/cost`** via `PUT /api/materials/rates`. Recalculation uses the new rates on the next estimate — no re-segmentation required.

## 6. Worked example

- Image: 1200 × 900 px → 1 080 000 px  
- Facade: 12 m × 9 m → **108 m²**  
- Wall mask: 270 000 px → fraction **0.25**  
- Material: exterior emulsion (paint) at ₹55/sqm  
- Waste: 1.10  

\[
q = 0.25 \times 108 \times 1.10 = 29.7\;\mathrm{sqm}
\]

\[
\text{line} = 29.7 \times 55 = ₹1{,}633.50
\]

Add other category lines (balcony cladding, gate pieces, …) for the grand total.

## 7. Live estimate vs PDF

| Path | Endpoint | Behaviour |
|------|----------|-----------|
| Live studio panel | `POST /api/costing/{project_id}/estimate` | JSON line items + totals + disclaimer |
| PDF report | `POST /api/reporting/{project_id}/pdf` | Same logic embedded with images (requires prior render) |

## 8. Disclaimer (shown in API and PDF)

> Approximate estimate based on selected finishes, detected mask coverage, and rates from the Cost page. **Not a formal quotation.**

This matches problem-statement Section 7: cost estimates are **advisory**.
