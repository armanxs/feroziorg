"""Build PDFs from flipbook page images listed in Pages.xml."""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import img2pdf

from config import BOOKS, SITE, SOURCE


def resolve_page(flipbook: str, src: str) -> Path | None:
    rel = src.replace("/", "\\")
    candidates = [
        SOURCE / flipbook / rel,
        SOURCE / flipbook / Path(src).name,
    ]
    name = Path(src).name.lower()
    book_dir = SOURCE / flipbook
    if book_dir.exists():
        for path in book_dir.rglob("*"):
            if path.is_file() and path.name.lower() == name:
                candidates.append(path)
    for path in candidates:
        if path.exists():
            return path
    return None


def page_paths(flipbook: str) -> list[Path]:
    xml_path = SOURCE / flipbook / "xml" / "Pages.xml"
    if not xml_path.exists():
        raise FileNotFoundError(xml_path)
    root = ET.parse(xml_path).getroot()
    paths: list[Path] = []
    for page in root.findall("page"):
        src = page.attrib.get("src", "")
        local = resolve_page(flipbook, src)
        if local is None:
            print(f"  missing page: {src}")
            continue
        paths.append(local)
    return paths


def natural_sort_key(path: Path) -> tuple:
    name = path.stem.lower()
    m = re.search(r"(\d+)", name)
    if m:
        return (0, int(m.group(1)), name)
    return (1, name)


def build_pdf(book: dict) -> Path:
    out = SITE / "assets" / "pdfs" / book["pdf"]
    out.parent.mkdir(parents=True, exist_ok=True)
    if book.get("existing_pdf"):
        src_pdf = SOURCE / book["existing_pdf"]
        if src_pdf.exists():
            out.write_bytes(src_pdf.read_bytes())
            print(f"  copied {src_pdf.name} -> {out.name}")
            return out
    flipbook = book["flipbook"]
    pages = page_paths(flipbook)
    # img2pdf only accepts JPEG/PNG — skip psd/db
    pages = [p for p in pages if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    if not pages:
        raise RuntimeError(f"No pages for {book['title']}")
    # Preserve XML order (important for book flow)
    print(f"  building {out.name} from {len(pages)} images...")
    with open(out, "wb") as fh:
        fh.write(img2pdf.convert([str(p) for p in pages]))
    print(f"  wrote {out} ({out.stat().st_size // 1024} KB)")
    return out


def main() -> int:
    for book in BOOKS:
        if book.get("flipbook") or book.get("existing_pdf"):
            try:
                build_pdf(book)
            except Exception as exc:
                print(f"ERROR {book['title']}: {exc}")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
