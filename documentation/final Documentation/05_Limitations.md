# 05 — Limitations

**Problem-statement deliverable:** *Documentation explaining limitations of the system*

Estimates and visuals are planning aids. Treat them as approximate.

## 1. Advisory costing (explicit)

- Outputs are **not** legally binding quotations or contractor bills.  
- Rates are catalogue defaults or user edits — not live market surveys.  
- Labour is folded into a single blended `rate_inr` per material, not a separate labour schedule.  
- Waste is a flat **10%** factor, not site-specific wastage.

## 2. Area & quantity accuracy

| Limitation | Impact |
|------------|--------|
| User must enter facade W×H | Wrong dimensions scale every line item |
| Mask fraction = area fraction | Perspective / depth / foreshortening not corrected |
| No door-height or window-scale reference | Automatic metric scale unavailable |
| Single photo | Only visible surfaces; sides/back omitted |
| Unit categories use instance counts | Missed or merged detections skew piece counts |
| No paint L / tile piece / railing RFT packing | Quantities are sqm or pcs only |

Improve accuracy by correcting masks carefully and measuring the real facade width/height with a tape.

## 3. Segmentation

- Grounding DINO can miss unusual architecture, heavy occlusion, night photos, or cluttered scenes.  
- Wall quality depends on building box quality and opening subtraction.  
- Soft edges / vegetation may bleed into masks — use brush/eraser.  
- Parapet may appear as part of wall or rooftop depending on prompt hits.  
- CPU-only; **cold start is slow**; unsuitable for high-concurrency production without a job queue.

## 4. Visualization / rendering

- Rendering is **classical OpenCV** (recolor + texture tiling), not photorealistic diffusion.  
- Textures tile approximately; fine mortar joints and specular materials will not match showroom photos.  
- Lighting approximation preserves luminance shading but is not full global illumination.  
- ControlNet / Stable Diffusion paths exist conceptually in earlier design docs but are **disabled** (memory / RAM budget ~8 GB).  
- Structure preservation is strong for paint; texture placement can still look “stamped” on complex geometry.

## 5. Product / platform gaps

| Gap | Note |
|-----|------|
| No authentication | Local single-user demo |
| No multi-design named variants | Last render overwrites output image |
| No multi-photo / 360 capture | One elevation at a time |
| Building-presence rejection soft | Severe non-house images may still upload; quality warnings only |
| Region UX | Brush/erase yes; full redraw/rename/delete region polish is limited |

## 6. Assumptions that can fail

- Shot is approximately frontal  
- Building is low-rise residential exterior  
- Masks after edit represent surfaces that will actually be finished  
- User rates reflect local market  

If these fail, both visualization quality and cost credibility degrade.

## 7. Honest positioning

| Strength | Bound |
|----------|-------|
| Fast visual “what if” on the user’s own photo | Not a construction drawing |
| Transparent qty × rate math | Not a surveyor’s BOQ |
| Editable rates + PDF for contractor talks | Not a signed quotation |

The problem statement asked for **reasonably accurate** area for costing purposes. This prototype meets that bar when the user calibrates facade size and corrects masks; it does **not** claim centimetre survey accuracy.
