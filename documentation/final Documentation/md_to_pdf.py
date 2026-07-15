"""Convert final Documentation .md files to PDF via markdown + xhtml2pdf.

Separate PDFs are generated first; the merged pack is built by concatenating
those PDFs (pypdf) so it always matches the individual files exactly.
Mermaid diagrams are rendered via mermaid.ink and embedded as images.
"""
from __future__ import annotations

import base64
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

import markdown
from xhtml2pdf import pisa

DOC_DIR = Path(__file__).resolve().parent
PDF_DIR = DOC_DIR / "PDF"
DIAG_DIR = PDF_DIR / "diagrams"

CSS = """
@page {
  size: A4;
  margin: 16mm 14mm 16mm 14mm;
}
body {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #1a1a1a;
}
h1 { font-size: 18pt; color: #0f172a; margin: 0 0 12pt 0; border-bottom: 1.5pt solid #334155; padding-bottom: 6pt; }
h2 { font-size: 13pt; color: #1e293b; margin: 16pt 0 8pt 0; }
h3 { font-size: 11.5pt; color: #334155; margin: 12pt 0 6pt 0; }
p, li { margin: 0 0 6pt 0; }
ul, ol { margin: 0 0 8pt 16pt; padding: 0; }
a { color: #1d4ed8; text-decoration: none; }
code {
  font-family: Courier, monospace;
  font-size: 9pt;
  background: #f1f5f9;
  padding: 1pt 3pt;
}
pre {
  font-family: Courier, monospace;
  font-size: 8.5pt;
  background: #f8fafc;
  border: 0.5pt solid #cbd5e1;
  padding: 8pt;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0 0 10pt 0;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 12pt 0;
  font-size: 9.5pt;
}
th, td {
  border: 0.5pt solid #94a3b8;
  padding: 5pt 6pt;
  text-align: left;
  vertical-align: top;
}
th { background: #e2e8f0; font-weight: bold; }
blockquote {
  margin: 8pt 0;
  padding: 6pt 10pt;
  border-left: 3pt solid #64748b;
  background: #f8fafc;
  color: #334155;
}
hr { border: none; border-top: 0.5pt solid #cbd5e1; margin: 14pt 0; }
.diagram {
  text-align: center;
  margin: 10pt 0 14pt 0;
}
.diagram img {
  max-width: 100%;
  width: 520pt;
}
.cover h1 { border: none; font-size: 22pt; margin-bottom: 6pt; }
.cover .meta { color: #475569; margin-bottom: 18pt; }
.cover table { width: 90%; }
"""

MERMAID_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)

DOC_ORDER = [
    "01_System_Overview.md",
    "02_System_Architecture.md",
    "03_User_Workflow.md",
    "04_Estimation_and_Costing.md",
    "05_Limitations.md",
    "06_API_Reference.md",
    "07_Setup_and_Deployment.md",
]


def render_mermaid(source: str) -> Path:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    cleaned = source.strip() + "\n"
    digest = hashlib.sha1(cleaned.encode("utf-8")).hexdigest()[:16]
    out = DIAG_DIR / f"mermaid_{digest}.jpg"
    if out.exists() and out.stat().st_size > 100:
        return out

    encoded = base64.urlsafe_b64encode(cleaned.encode("utf-8")).decode("ascii")
    url = f"https://mermaid.ink/img/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "AI-Exterior-Studio-Docs/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()
    if len(data) < 100:
        raise RuntimeError("mermaid.ink returned empty image")
    out.write_bytes(data)
    return out


def img_data_uri(path: Path) -> str:
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    mime = "image/jpeg" if raw[:2] == b"\xff\xd8" else "image/png"
    return f"data:{mime};base64,{b64}"


def preprocess_md(text: str) -> str:
    def repl(match: re.Match) -> str:
        body = match.group(1).strip()
        try:
            img_path = render_mermaid(body)
            uri = img_data_uri(img_path)
            return f'\n\n<div class="diagram"><img src="{uri}" alt="Diagram"/></div>\n\n'
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN mermaid render failed: {exc}", file=sys.stderr)
            return f"\n\n```\n{body}\n```\n\n"

    return MERMAID_RE.sub(repl, text)


def md_to_html(md_text: str, title: str) -> str:
    body = markdown.markdown(
        preprocess_md(md_text),
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>{title}</title>
<style>{CSS}</style></head>
<body>{body}</body></html>"""


def write_pdf(html: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as fh:
        result = pisa.CreatePDF(html, dest=fh, encoding="utf-8", link_callback=None)
    if result.err:
        raise RuntimeError(f"PDF generation failed for {out_path.name} (errors={result.err})")


def convert_file(md_path: Path) -> Path:
    title = md_path.stem.replace("_", " ")
    html = md_to_html(md_path.read_text(encoding="utf-8"), title)
    out = PDF_DIR / f"{md_path.stem}.pdf"
    write_pdf(html, out)
    return out


def write_cover_pdf(md_files: list[Path], out_path: Path) -> Path:
    rows = []
    for md in md_files:
        first = md.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        rows.append(f"<tr><td>{md.stem.split('_')[0]}</td><td>{first}</td></tr>")
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>Cover</title><style>{CSS}</style></head>
<body class="cover">
<h1>AI Exterior Studio</h1>
<p class="meta"><strong>Final Documentation Pack</strong><br/>
AI-Based Exterior House Renovation &amp; Cost Estimation System</p>
<p>This merged PDF contains the same content as the individual chapter PDFs, in order:</p>
<table>
<thead><tr><th>#</th><th>Document</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body></html>"""
    write_pdf(html, out_path)
    return out_path


def merge_pdfs(pdf_paths: list[Path], out_path: Path) -> Path:
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    for path in pdf_paths:
        reader = PdfReader(str(path))
        for page in reader.pages:
            writer.add_page(page)
    with out_path.open("wb") as fh:
        writer.write(fh)
    return out_path


def list_docs() -> list[Path]:
    files: list[Path] = []
    for name in DOC_ORDER:
        path = DOC_DIR / name
        if path.exists():
            files.append(path)
        else:
            print(f"  WARN missing expected doc: {name}", file=sys.stderr)
    known = {p.name for p in files}
    for path in sorted(DOC_DIR.glob("[0-9][0-9]_*.md")):
        if path.name not in known:
            files.append(path)
    return files


def ensure_pypdf() -> None:
    try:
        import pypdf  # noqa: F401
    except ImportError:
        import subprocess

        print("Installing pypdf...", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf", "-q"])


def main() -> int:
    ensure_pypdf()

    md_files = list_docs()
    if not md_files:
        print("No documentation .md files found", file=sys.stderr)
        return 1

    print(f"Converting {len(md_files)} markdown files -> {PDF_DIR}")
    chapter_pdfs: list[Path] = []
    for md in md_files:
        print(f"  .. {md.name}")
        out = convert_file(md)
        chapter_pdfs.append(out)
        print(f"  OK  {md.name} -> PDF/{out.name}")

    cover = PDF_DIR / "_cover.pdf"
    write_cover_pdf(md_files, cover)
    print("  OK  cover page")

    combined = PDF_DIR / "AI_Exterior_Studio_Final_Documentation.pdf"
    merge_pdfs([cover, *chapter_pdfs], combined)
    cover.unlink(missing_ok=True)
    print(f"  OK  MERGED -> PDF/{combined.name} (cover + {len(chapter_pdfs)} chapters)")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
