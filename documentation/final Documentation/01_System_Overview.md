# 01 — System Overview

## 1. Problem

Homeowners planning exterior renovation face three barriers before construction:

| Gap | Effect |
|-----|--------|
| **Visualization** | They cannot see how *their* house will look with new cladding, paint, or tiles |
| **Material selection** | Choice of finish, location, and durability is guesswork or brochure-based |
| **Cost uncertainty** | Quotations vary; area, wastage, and labour are opaque |

The product is a **pre-construction planning assistant**: upload a photo, choose finishes, see a redesign of the actual house, and get an approximate quantity and cost breakdown suitable for discussion with contractors.

## 2. Goals (from problem statement)

1. Accept exterior images of a residential building  
2. Generate redesigned visual options using selected materials  
3. Estimate material quantities required  
4. Calculate a transparent renovation cost  

## 3. Target users

| Role | Use |
|------|-----|
| **Primary** | Homeowners, new house owners before finishing |
| **Secondary** | Contractors, architects, builders, consultants, material suppliers |

## 4. Scope of this prototype

### In scope

- Single exterior photo upload with quality guidance  
- AI segmentation of major facade categories  
- Manual mask refinement (brush / eraser)  
- Material catalog (paint + textures: cladding, tiles, patterns)  
- Classical CV rendering preserving structure and lighting  
- Before / after comparison  
- Surface quantity from mask coverage × user facade size  
- INR cost estimate with editable rates  
- Downloadable PDF report  

### Out of scope (by design)

- Interior design  
- Structural / engineering calculations  
- Professional CAD drawings or survey equipment  
- Legally binding quotations (estimates are **advisory**)  
- Multi-photo fusion, NeRF / full 3D reconstruction  
- User authentication / multi-tenant accounts (single-user local demo)  

## 5. Assumptions (aligned with problem statement)

- Residential, low-rise (independent house, bungalow, small apartment)  
- Exterior renovation only  
- User can approximate facade width and height in metres  
- One photo shows the primary elevation of interest  
- Cost estimates are for planning discussion, not contracts  

## 6. Constraints met

| Constraint | How we satisfy it |
|------------|-------------------|
| No architectural drawings required | Photo-only input |
| No specialised measuring equipment | User facade W×H + mask fractions |
| Rely primarily on visual media | Upload → segment → render pipeline |
| Usable by non-technical users | Guided studio UI, category buttons, cost page |
| Reasonable time on standard connections | CPU classical render (~seconds); segmentation slower on first load |

## 7. Solution shape (one sentence)

**AI perceives regions; deterministic math costs them** — segmentation and rendering produce a RegionMap; quantity and cost are pure formulas over that map plus editable rates, never opaque model guesses for money.
