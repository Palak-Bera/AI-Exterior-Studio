"""Cost estimation engine — approximate redesign cost in Indian Rupees (INR).

Quantities come from mask pixel coverage mapped onto a user-calibrated facade
area (width × height in metres). Material rates come from the Cost page
(stored on each Material.rate_inr).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.logging_config import get_logger
from app.utils.categories import CATEGORIES

logger = get_logger("costing")

CURRENCY = "INR"
CURRENCY_SYMBOL = "₹"
DEFAULT_WASTE_FACTOR = 1.10
DEFAULT_FACADE_WIDTH_M = 12.0
DEFAULT_FACADE_HEIGHT_M = 9.0

# Default catalogue rates (₹ / unit). Editable on the Cost page.
DEFAULT_RATES_INR: dict[str, float] = {
    "paint": 55.0,       # ₹/sqm exterior emulsion (material + application approx)
    "cladding": 2200.0,  # ₹/sqm wall cladding
    "tiles": 1100.0,     # ₹/sqm exterior wall tiles
    "patterns": 1500.0,  # ₹/sqm textured patterns
    "texture": 1200.0,   # fallback
}

# Categories where finishes are priced per piece rather than area.
UNIT_CATEGORIES = frozenset({"gate", "door", "window", "pillar"})


def default_rate_for_group(group: str) -> float:
    return float(DEFAULT_RATES_INR.get(group, DEFAULT_RATES_INR["texture"]))


def default_unit_for_category(category: str) -> str:
    return "unit" if category in UNIT_CATEGORIES else "sqm"


@dataclass
class CostLine:
    category: str
    category_label: str
    material_key: str
    material_name: str
    quantity: float
    unit: str
    rate_inr: float
    line_total_inr: float
    color: str | None = None

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "category_label": self.category_label,
            "material_key": self.material_key,
            "material_name": self.material_name,
            "quantity": round(self.quantity, 2),
            "unit": self.unit,
            "rate_inr": round(self.rate_inr, 2),
            "line_total_inr": round(self.line_total_inr, 2),
            "color": self.color,
        }


def format_inr(amount: float, *, for_pdf: bool = False) -> str:
    """Indian-style grouping.

    UI: ₹1,23,456.78
    PDF: Rs. 1,23,456.78  (Helvetica has no ₹ glyph — avoids black boxes)
    """
    neg = amount < 0
    n = abs(float(amount))
    whole = int(n)
    frac = f"{n - whole:.2f}"[1:]  # ".xx"
    s = str(whole)
    if len(s) <= 3:
        grouped = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts: list[str] = []
        while rest:
            parts.append(rest[-2:])
            rest = rest[:-2]
        grouped = ",".join(reversed(parts)) + "," + last3
    symbol = "Rs. " if for_pdf else CURRENCY_SYMBOL
    out = f"{symbol}{grouped}{frac}"
    return f"-{out}" if neg else out


def estimate_cost(
    *,
    selections: list[dict],
    regions_by_category: dict[str, dict],
    materials_by_key: dict[str, dict],
    image_width: int,
    image_height: int,
    facade_width_m: float = DEFAULT_FACADE_WIDTH_M,
    facade_height_m: float = DEFAULT_FACADE_HEIGHT_M,
    waste_factor: float = DEFAULT_WASTE_FACTOR,
) -> dict:
    """
    Build an approximate cost estimate.

    selections: [{category, material_key, color?}]
    regions_by_category: {cat: {pixel_area, instance_count}}
    materials_by_key: {key: {name, rate_inr, unit, group}}
    """
    facade_w = max(0.5, float(facade_width_m or DEFAULT_FACADE_WIDTH_M))
    facade_h = max(0.5, float(facade_height_m or DEFAULT_FACADE_HEIGHT_M))
    waste = max(1.0, float(waste_factor or DEFAULT_WASTE_FACTOR))
    facade_area_m2 = facade_w * facade_h
    img_px = max(1, int(image_width) * int(image_height))

    lines: list[CostLine] = []
    for sel in selections:
        cat = sel.get("category") or ""
        mkey = sel.get("material_key") or ""
        mat = materials_by_key.get(mkey) or {}
        region = regions_by_category.get(cat) or {}
        pixel_area = int(region.get("pixel_area") or 0)
        instance_count = max(1, int(region.get("instance_count") or 1))

        rate = float(mat.get("rate_inr") or 0)
        if rate <= 0:
            rate = default_rate_for_group(mat.get("group") or "texture")

        # Prefer material unit from Cost page; fall back by category.
        unit = (mat.get("unit") or "").strip().lower() or default_unit_for_category(cat)

        if unit == "unit":
            qty = float(instance_count)
            unit_label = "pcs"
        else:
            fraction = pixel_area / img_px if pixel_area > 0 else 0.0
            qty = fraction * facade_area_m2 * waste
            unit_label = "sqm"
            # Tiny masks: still price a minimum patch so totals aren't ₹0.
            if qty > 0 and qty < 0.25:
                qty = 0.25

        line_total = qty * rate
        label = CATEGORIES.get(cat, {}).get("label", cat.replace("_", " ").title())
        lines.append(
            CostLine(
                category=cat,
                category_label=label,
                material_key=mkey,
                material_name=mat.get("name") or mkey,
                quantity=qty,
                unit=unit_label,
                rate_inr=rate,
                line_total_inr=line_total,
                color=sel.get("color"),
            )
        )

    subtotal = sum(L.line_total_inr for L in lines)
    result = {
        "currency": CURRENCY,
        "currency_symbol": CURRENCY_SYMBOL,
        "facade_width_m": round(facade_w, 2),
        "facade_height_m": round(facade_h, 2),
        "facade_area_m2": round(facade_area_m2, 2),
        "waste_factor": round(waste, 2),
        "lines": [L.as_dict() for L in lines],
        "subtotal_inr": round(subtotal, 2),
        "total_inr": round(subtotal, 2),
        "total_display": format_inr(subtotal),
        "disclaimer": (
            "Approximate estimate based on selected finishes, detected mask coverage, "
            "and rates from the Cost page. Not a formal quotation."
        ),
    }
    logger.info(
        "Cost estimate: lines=%d facade=%.1fx%.1fm total=%s",
        len(lines),
        facade_w,
        facade_h,
        result["total_display"],
    )
    return result
