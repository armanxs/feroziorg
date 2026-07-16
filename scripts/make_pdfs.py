"""Build PDFs from flipbook page images listed in Pages.xml.

Pages are embedded at their native pixel size (no downscaling) as RGB JPEG.
The source flipbook JPEGs are frequently bloated CMYK files (a 340x475 page
stored as ~700 KB); re-encoding to RGB JPEG removes that waste with no visible
quality change. Every PDF is kept under MAX_PDF_BYTES so it deploys to
Cloudflare (Workers/Pages hard-cap assets at 25 MiB per file); if a book would
exceed the cap the JPEG quality is lowered a step at a time until it fits.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import img2pdf
from PIL import Image

from config import BOOKS, ROOT, SITE, SOURCE

WEB_PDF = ROOT / "web" / "assets" / "pdfs"

# Stay safely under Cloudflare's 25 MiB per-asset limit.
MAX_PDF_BYTES = 24 * 1024 * 1024
# Quality ladder tried from best to worst until the PDF fits the cap.
QUALITY_LADDER = [92, 88, 82, 75, 68, 60, 50]


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


def to_rgb_jpeg(src: Path, dest: Path, quality: int) -> tuple[int, int]:
    """Re-encode a page to RGB JPEG at native resolution (no resize)."""
    with Image.open(src) as im:
        w, h = im.size
        if im.mode == "RGB":
            rgb = im
        elif im.mode == "RGBA":
            background = Image.new("RGB", im.size, (255, 255, 255))
            background.paste(im, mask=im.split()[3])
            rgb = background
        else:
            rgb = im.convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        rgb.save(dest, format="JPEG", quality=quality, optimize=True, progressive=True)
        return w, h


def render_pdf(pages: list[Path], out: Path, tmp_dir: Path, quality: int) -> None:
    prepared: list[str] = []
    for i, page in enumerate(pages):
        dest = tmp_dir / f"{i:04d}.jpg"
        to_rgb_jpeg(page, dest, quality)
        prepared.append(str(dest))
    with open(out, "wb") as fh:
        fh.write(img2pdf.convert(prepared))


def build_pdf(book: dict) -> Path:
    out = SITE / "assets" / "pdfs" / book["pdf"]
    out.parent.mkdir(parents=True, exist_ok=True)
    if book.get("existing_pdf"):
        src_pdf = SOURCE / book["existing_pdf"]
        if src_pdf.exists():
            out.write_bytes(src_pdf.read_bytes())
            print(f"  copied {src_pdf.name} -> {out.name} ({out.stat().st_size // 1024} KB)")
            return out
    flipbook = book["flipbook"]
    pages = page_paths(flipbook)
    pages = [p for p in pages if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    if not pages:
        raise RuntimeError(f"No pages for {book['title']}")

    print(f"  building {out.name} from {len(pages)} images (native pixels, RGB JPEG)...")
    with tempfile.TemporaryDirectory(prefix="ferozi-pdf-") as tmp:
        tmp_dir = Path(tmp)
        for quality in QUALITY_LADDER:
            render_pdf(pages, out, tmp_dir, quality)
            size = out.stat().st_size
            print(f"    quality={quality} -> {size // 1024} KB")
            if size <= MAX_PDF_BYTES:
                break
        else:
            raise RuntimeError(
                f"{out.name} still {out.stat().st_size // 1024} KB at lowest quality; "
                "consider downscaling pages"
            )
    print(f"  wrote {out} ({out.stat().st_size // 1024} KB)")
    return out


def sync_to_web(pdf_path: Path) -> None:
    WEB_PDF.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_path, WEB_PDF / pdf_path.name)


def main() -> int:
    for book in BOOKS:
        if book.get("flipbook") or book.get("existing_pdf"):
            try:
                pdf = build_pdf(book)
                sync_to_web(pdf)
            except Exception as exc:
                print(f"ERROR {book['title']}: {exc}")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
