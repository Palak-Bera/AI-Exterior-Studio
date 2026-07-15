"""PDF redesign report: brand header, before/after images, selected materials."""
from __future__ import annotations

import shutil
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.core.config import OUTPUT_DIR, settings
from app.core.logging_config import get_logger
from app.services.costing import format_inr
from app.utils.categories import CATEGORIES

logger = get_logger("report")

BRAND_NAME = "AI Exterior Studio"
BRAND_TAGLINE = "Exterior Redesign Report"
# Logo navy (~#0A2F58)
ACCENT = colors.Color(10 / 255, 47 / 255, 88 / 255)
INK = colors.Color(11 / 255, 18 / 255, 32 / 255)
MUTED = colors.Color(92 / 255, 107 / 255, 122 / 255)
LINE = colors.Color(213 / 255, 220 / 255, 230 / 255)


def brand_logo_path() -> Path:
    return settings.STORAGE_DIR / "brand" / "logo.png"


def ensure_brand_logo() -> Path:
    """Prefer the uploaded AES logo; sync to logo.png for a stable public URL."""
    brand_dir = settings.STORAGE_DIR / "brand"
    brand_dir.mkdir(parents=True, exist_ok=True)
    canonical = brand_logo_path()

    # Prefer named uploads (space or hyphen variants) over a tiny generated mark.
    candidates = [
        brand_dir / "logo AES.png",
        brand_dir / "logo-AES.png",
        brand_dir / "logo_aes.png",
        canonical,
    ]
    source: Path | None = None
    for p in candidates:
        if p.is_file() and p.stat().st_size > 8_000:
            source = p
            break

    if source is not None:
        if source.resolve() != canonical.resolve():
            shutil.copy2(source, canonical)
            logger.info("Brand logo synced: %s -> %s", source.name, canonical.name)
        return canonical

    # Fallback AE mark only when nothing is uploaded.
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = 12
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=48,
        fill=(10, 47, 88, 255),
    )
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 96)
    except OSError:
        try:
            font = ImageFont.truetype("arialbd.ttf", 96)
        except OSError:
            font = ImageFont.load_default()
    text = "AE"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - tw) / 2, (size - th) / 2 - 8),
        text,
        fill=(255, 255, 255, 255),
        font=font,
    )
    img.save(canonical, format="PNG")
    logger.info("Brand logo fallback written: %s", canonical.resolve())
    return canonical


def resolve_storage_file(url_or_path: str) -> Path:
    """Map /storage/... URL or relative path to an absolute file path."""
    raw = (url_or_path or "").strip().split("?", 1)[0]
    if not raw:
        raise FileNotFoundError("Empty image path")
    # Strip absolute API URLs → keep path after /storage/
    if "://" in raw:
        idx = raw.find("/storage/")
        if idx >= 0:
            raw = raw[idx:]
        else:
            raw = raw.rsplit("/", 1)[-1]
    p = Path(raw)
    if p.is_file():
        return p.resolve()
    # /storage/outputs/foo.jpg -> storage/outputs/foo.jpg
    normalized = raw.lstrip("/").replace("\\", "/")
    if normalized.startswith("storage/"):
        candidate = Path(normalized)
        if not candidate.is_file():
            candidate = settings.STORAGE_DIR / normalized.removeprefix("storage/")
    elif normalized.startswith("outputs/"):
        candidate = OUTPUT_DIR / Path(normalized).name
    else:
        candidate = settings.STORAGE_DIR / normalized.removeprefix("storage/")
    if candidate.is_file():
        return candidate.resolve()
    # Fallback: filename under outputs/
    by_name = OUTPUT_DIR / Path(normalized).name
    if by_name.is_file():
        return by_name.resolve()
    raise FileNotFoundError(f"Image not found: {url_or_path}")


def _fit_image(path: Path, max_w: float, max_h: float) -> tuple[ImageReader, float, float]:
    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = min(max_w / w, max_h / h)
        dw, dh = w * scale, h * scale
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return ImageReader(buf), dw, dh


def build_redesign_pdf(
    *,
    project_name: str,
    project_id: str,
    before_path: Path,
    after_path: Path,
    selections: list[dict],
    cost_estimate: dict | None = None,
) -> bytes:
    """
    selections items: {category, material_name, color?}
    cost_estimate: output of estimate_cost() (INR)
    """
    ensure_brand_logo()
    logo = brand_logo_path()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4
    margin = 18 * mm

    # ---- Header (full AES logo) ----
    header_h = 28 * mm
    c.setFillColor(colors.white)
    c.rect(0, page_h - header_h - 4 * mm, page_w, header_h + 4 * mm, fill=1, stroke=0)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.2)
    c.line(margin, page_h - header_h - 2 * mm, page_w - margin, page_h - header_h - 2 * mm)

    logo_h = 22 * mm
    logo_w = 22 * mm
    c.drawImage(
        str(logo),
        margin,
        page_h - header_h + 1 * mm,
        width=logo_w,
        height=logo_h,
        mask="auto",
        preserveAspectRatio=True,
    )
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(margin + logo_w + 4 * mm, page_h - 14 * mm, BRAND_TAGLINE)

    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(page_w - margin, page_h - 12 * mm, datetime.now().strftime("%d %b %Y"))
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawRightString(page_w - margin, page_h - 17 * mm, f"Project · {project_name[:40]}")

    y = page_h - header_h - 12 * mm

    # ---- Title ----
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(margin, y, "Before & After")
    y -= 8 * mm

    # ---- Before / After images ----
    gap = 6 * mm
    col_w = (page_w - 2 * margin - gap) / 2
    img_max_h = 58 * mm if cost_estimate else 72 * mm

    before_img, bw, bh = _fit_image(before_path, col_w, img_max_h)
    after_img, aw, ah = _fit_image(after_path, col_w, img_max_h)
    row_h = max(bh, ah)

    # Labels
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, "ORIGINAL")
    c.drawString(margin + col_w + gap, y, "REDESIGN")
    y -= 4 * mm

    c.setStrokeColor(LINE)
    c.setLineWidth(0.8)
    c.roundRect(margin, y - row_h - 2 * mm, col_w, row_h + 4 * mm, 4, stroke=1, fill=0)
    c.roundRect(
        margin + col_w + gap, y - row_h - 2 * mm, col_w, row_h + 4 * mm, 4, stroke=1, fill=0
    )
    c.drawImage(before_img, margin + (col_w - bw) / 2, y - row_h, width=bw, height=bh)
    c.drawImage(
        after_img,
        margin + col_w + gap + (col_w - aw) / 2,
        y - row_h,
        width=aw,
        height=ah,
    )
    y -= row_h + 12 * mm

    # ---- Materials ----
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(margin, y, "Selected materials")
    y -= 7 * mm

    # Table header
    row_h = 7 * mm
    cols = [margin, margin + 45 * mm, margin + 110 * mm, page_w - margin]
    headers = ["Element", "Material / Finish", "Color"]

    c.setFillColor(ACCENT)
    c.roundRect(margin, y - row_h + 2 * mm, page_w - 2 * margin, row_h, 3, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(cols[0] + 2 * mm, y - 4 * mm, headers[0])
    c.drawString(cols[1] + 2 * mm, y - 4 * mm, headers[1])
    c.drawString(cols[2] + 2 * mm, y - 4 * mm, headers[2])
    y -= row_h

    if not selections:
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(margin + 2 * mm, y - 4 * mm, "No materials selected.")
        y -= row_h
    else:
        c.setFont("Helvetica", 8)
        for i, sel in enumerate(selections):
            if y < 45 * mm:
                c.showPage()
                y = page_h - 25 * mm
                c.setFont("Helvetica", 8)

            bg = colors.Color(0.97, 0.98, 0.99) if i % 2 == 0 else colors.white
            c.setFillColor(bg)
            c.rect(margin, y - row_h + 2 * mm, page_w - 2 * margin, row_h, fill=1, stroke=0)
            c.setStrokeColor(LINE)
            c.line(margin, y - row_h + 2 * mm, page_w - margin, y - row_h + 2 * mm)

            cat = sel.get("category", "")
            label = CATEGORIES.get(cat, {}).get("label", cat.replace("_", " ").title())
            material = sel.get("material_name") or sel.get("material_key") or "—"
            color = sel.get("color") or "—"

            c.setFillColor(INK)
            c.drawString(cols[0] + 2 * mm, y - 4 * mm, str(label)[:28])
            c.drawString(cols[1] + 2 * mm, y - 4 * mm, str(material)[:36])
            c.drawString(cols[2] + 2 * mm, y - 4 * mm, str(color)[:18])
            y -= row_h

    # ---- Cost estimate (INR) ----
    if cost_estimate:
        y -= 6 * mm
        if y < 70 * mm:
            c.showPage()
            y = page_h - 25 * mm

        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(margin, y, "Cost estimate (INR)")
        y -= 5 * mm
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8)
        calib = (
            f"Facade approx. {cost_estimate.get('facade_width_m')} m × "
            f"{cost_estimate.get('facade_height_m')} m "
            f"({cost_estimate.get('facade_area_m2')} m²) · "
            f"waste ×{cost_estimate.get('waste_factor', 1.1)}"
        )
        c.drawString(margin, y, calib)
        y -= 7 * mm

        cost_cols = [
            margin,
            margin + 32 * mm,
            margin + 78 * mm,
            margin + 100 * mm,
            margin + 122 * mm,
            page_w - margin,
        ]
        cost_headers = ["Element", "Material", "Qty", "Rate (Rs.)", "Amount (Rs.)"]
        row_h = 7 * mm
        c.setFillColor(ACCENT)
        c.roundRect(margin, y - row_h + 2 * mm, page_w - 2 * margin, row_h, 3, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8)
        for i, h in enumerate(cost_headers):
            c.drawString(cost_cols[i] + 1.5 * mm, y - 4 * mm, h)
        y -= row_h

        lines = cost_estimate.get("lines") or []
        c.setFont("Helvetica", 8)
        for i, line in enumerate(lines):
            if y < 40 * mm:
                c.showPage()
                y = page_h - 25 * mm
                c.setFont("Helvetica", 8)

            bg = colors.Color(0.97, 0.98, 0.99) if i % 2 == 0 else colors.white
            c.setFillColor(bg)
            c.rect(margin, y - row_h + 2 * mm, page_w - 2 * margin, row_h, fill=1, stroke=0)
            c.setStrokeColor(LINE)
            c.line(margin, y - row_h + 2 * mm, page_w - margin, y - row_h + 2 * mm)

            qty = line.get("quantity", 0)
            unit = line.get("unit", "sqm")
            qty_txt = f"{qty:.2f} {unit}"
            rate_txt = format_inr(float(line.get("rate_inr") or 0), for_pdf=True)
            amt_txt = format_inr(float(line.get("line_total_inr") or 0), for_pdf=True)

            c.setFillColor(INK)
            c.drawString(cost_cols[0] + 1.5 * mm, y - 4 * mm, str(line.get("category_label", ""))[:16])
            c.drawString(cost_cols[1] + 1.5 * mm, y - 4 * mm, str(line.get("material_name", ""))[:22])
            c.drawString(cost_cols[2] + 1.5 * mm, y - 4 * mm, qty_txt[:12])
            c.drawRightString(cost_cols[4] - 1.5 * mm, y - 4 * mm, rate_txt)
            c.drawRightString(page_w - margin - 1.5 * mm, y - 4 * mm, amt_txt)
            y -= row_h

        y -= 3 * mm
        total = float(cost_estimate.get("total_inr") or 0)
        c.setFillColor(ACCENT)
        c.roundRect(margin, y - 10 * mm, page_w - 2 * margin, 10 * mm, 3, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin + 3 * mm, y - 6.5 * mm, "Estimated total")
        c.drawRightString(
            page_w - margin - 3 * mm,
            y - 6.5 * mm,
            format_inr(total, for_pdf=True),
        )
        y -= 14 * mm

        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7)
        disclaimer = cost_estimate.get("disclaimer") or ""
        # Wrap disclaimer lightly
        max_chars = 105
        while disclaimer:
            chunk = disclaimer[:max_chars]
            if len(disclaimer) > max_chars:
                split = chunk.rfind(" ")
                if split > 40:
                    chunk = chunk[:split]
            c.drawString(margin, y, chunk)
            disclaimer = disclaimer[len(chunk):].lstrip()
            y -= 3.5 * mm

    # ---- Footer ----
    c.setStrokeColor(LINE)
    c.line(margin, 18 * mm, page_w - margin, 18 * mm)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(margin, 12 * mm, f"{BRAND_NAME} · Confidential client preview · Prices in INR")
    c.drawRightString(page_w - margin, 12 * mm, f"ID {project_id[:12]}")

    c.save()
    data = buffer.getvalue()
    buffer.close()
    logger.info(
        "PDF report built: project=%s selections=%d cost=%s bytes=%d",
        project_id,
        len(selections),
        bool(cost_estimate),
        len(data),
    )
    return data
