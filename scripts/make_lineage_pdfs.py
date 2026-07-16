"""Generate the lineage PDFs (Shajra / Silsila) from the finished web pages.

The lineage pages are text-only lists that are already rendered inline in
web/*.html (with the corrected honorifics, e.g. "(R.A.)"). We build the
downloadable PDF straight from that HTML so the button target is a real file
and always matches on-page content. Output is written to both web/ and site/.
"""
from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup
from fpdf import FPDF

from config import ROOT, SITE

WEB = ROOT / "web"
WEB_PDF = WEB / "assets" / "pdfs"
SITE_PDF = SITE / "assets" / "pdfs"

DOCS = [
    ("silsilatayyabaqadri.html", "silsila-qadiria.pdf"),
    ("silsilatayyabanaqshbandia.html", "silsila-naqshbandia.pdf"),
    ("shajra.html", "shajra-e-tayyaba.pdf"),
]


def pdf_safe(s: str) -> str:
    return (
        (s or "")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("`", "'")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def extract(html_path: Path) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    article = soup.select_one(".ferozitabs-right .lineage-article") or soup.select_one(
        ".ferozitabs-right"
    )
    heading_tag = article.find("h5")
    heading = heading_tag.get_text(" ", strip=True) if heading_tag else ""
    lines = [
        p.get_text(" ", strip=True)
        for p in article.find_all("p")
        if "pdf-actions" not in (p.get("class") or []) and p.get_text(strip=True)
    ]
    return heading, lines


def write_pdf(path: Path, heading: str, lines: list[str]) -> None:
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)
    if heading:
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(174, 6, pdf_safe(heading))
        pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    for line in lines:
        pdf.multi_cell(174, 6, pdf_safe(line))
        pdf.ln(1)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))


def main() -> int:
    WEB_PDF.mkdir(parents=True, exist_ok=True)
    SITE_PDF.mkdir(parents=True, exist_ok=True)
    for page, pdf_name in DOCS:
        src = WEB / page
        if not src.exists():
            print(f"MISSING {src}")
            return 1
        heading, lines = extract(src)
        if not lines:
            print(f"WARN no content extracted from {page}")
        out = WEB_PDF / pdf_name
        write_pdf(out, heading, lines)
        (SITE_PDF / pdf_name).write_bytes(out.read_bytes())
        print(f"wrote {pdf_name} ({out.stat().st_size // 1024} KB, {len(lines)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
