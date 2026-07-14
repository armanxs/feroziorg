"""Replace Flash embeds with HTML5 audio, image galleries, PDFs, or Vimeo."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from config import BOOKS, SITE, SOURCE

AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
SKIP_NAMES = {"thumbs.db"}

FLIPBOOK_BY_FOLDER = {b["flipbook"]: b for b in BOOKS if b.get("flipbook")}
BOOK_BY_HTML = {b["source_html"]: b for b in BOOKS}

VIMEO_PROGRAMS = """
<div class="vimeo-responsive">
  <iframe src="https://vimeo.com/album/5664265/embed" allowfullscreen
          frameborder="0" title="Ferozi.org Programs" loading="lazy"></iframe>
</div>"""


def normalize_web_path(path: str) -> str:
    path = path.replace("\\", "/").strip()
    if path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


def asset_exists(web_path: str) -> bool:
    rel = normalize_web_path(web_path)
    return (SITE / rel).exists() or (SOURCE / rel).exists()


def parse_ac_fl_movie(script_text: str) -> str | None:
    if not script_text:
        return None
    for key in ("movie", "src"):
        m = re.search(rf"'{key}'\s*,\s*'([^']+)'", script_text, re.I)
        if m:
            return normalize_web_path(m.group(1))
    return None


def parse_flash_bases(html: str) -> list[str]:
    bases: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(
        r"AC_FL_RunContent\s*\([^)]*'(?:movie|src)'\s*,\s*'([^']+)'",
        html,
        re.I | re.S,
    ):
        base = normalize_web_path(m.group(1))
        if base not in seen:
            seen.add(base)
            bases.append(base)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["embed", "object", "param"]):
        src = tag.get("src") or tag.get("value") or ""
        if ".swf" in src.lower() or (tag.name == "param" and tag.get("name", "").lower() == "movie"):
            src = normalize_web_path(src.replace(".swf", ""))
            if src and src not in seen:
                seen.add(src)
                bases.append(src)
    return bases


def xml_candidates_for_base(base: str) -> list[Path]:
    base = base.replace(".swf", "")
    name = Path(base).name
    parent = Path(base).parent
    cands = [
        SOURCE / f"{base}.xml",
        SOURCE / parent / f"{name}.xml",
        SOURCE / parent / "playlist.xml",
    ]
    if parent.as_posix() != ".":
        folder_name = parent.name.lower()
        cands.append(SOURCE / parent / f"{folder_name}.xml")
    out: list[Path] = []
    seen: set[Path] = set()
    for p in cands:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def parse_audio_xml(xml_path: Path) -> list[dict[str, str]]:
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return []
    tracks: list[dict[str, str]] = []
    for track in root.findall(".//track"):
        file = normalize_web_path(track.findtext("file", "") or "")
        if not file:
            continue
        title = (track.findtext("title") or "").strip() or Path(file).stem
        artist = (track.findtext("artist") or "").strip()
        tracks.append({"file": file, "title": title, "artist": artist})
    return tracks


def tracks_from_folder(folder: Path, web_prefix: str) -> list[dict[str, str]]:
    if not folder.is_dir():
        return []
    tracks: list[dict[str, str]] = []
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() not in AUDIO_EXT or f.name.lower() in SKIP_NAMES:
            continue
        tracks.append(
            {
                "file": f"{web_prefix}/{f.name}",
                "title": f.stem.replace("-", " ").replace("_", " "),
                "artist": "",
            }
        )
    return tracks


def resolve_audio_tracks(base: str) -> list[dict[str, str]]:
    base = normalize_web_path(base).replace(".swf", "")
    for xml_path in xml_candidates_for_base(base):
        if xml_path.exists():
            tracks = [t for t in parse_audio_xml(xml_path) if asset_exists(t["file"])]
            if tracks:
                return tracks
    folder = SOURCE / base
    if folder.is_dir():
        parent = str(Path(base).parent).replace("\\", "/")
        web_prefix = base if parent == "." else base
        if not any(folder.glob("*.mp3")):
            web_prefix = base
        tracks = tracks_from_folder(folder, web_prefix)
        if tracks:
            return [t for t in tracks if asset_exists(t["file"])]
    # Parent folder mp3s (e.g. audio/Arifana when base is audio/Arifana/arifana)
    parent_folder = SOURCE / str(Path(base).parent)
    if parent_folder.is_dir() and parent_folder != folder:
        prefix = str(Path(base).parent).replace("\\", "/")
        tracks = tracks_from_folder(parent_folder, prefix)
        if tracks:
            return [t for t in tracks if asset_exists(t["file"])]
    return []


def audio_playlist_html(tracks: list[dict[str, str]]) -> str:
    if not tracks:
        return (
            '<p class="flash-fallback-note">Audio tracks for this section are not in the '
            "local archive yet. Run <code>python scripts/mirror_media.py</code> to sync from FTP.</p>"
        )
    items = []
    for track in tracks:
        src = normalize_web_path(track["file"])
        label = track["title"]
        if track.get("artist"):
            label = f'{label} <span class="audio-artist">— {track["artist"]}</span>'
        items.append(
            f'<li class="audio-track">'
            f'<div class="audio-track-title">{label}</div>'
            f'<audio controls preload="none" src="{src}"></audio>'
            f"</li>"
        )
    return f'<ul class="audio-playlist">{"".join(items)}</ul>'


def gallery_image_dir_from_xml(xml_path: Path) -> str:
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return "islamic_pic_gallery/images"
    image_dir = (root.attrib.get("imageDir") or "images/").replace("\\", "/")
    image_dir = image_dir.replace("./", "").strip("/")
    if image_dir.startswith("islamic_pic_gallery/"):
        return image_dir
    if "/" in image_dir:
        return image_dir
    return f"islamic_pic_gallery/{image_dir}".rstrip("/")


def gallery_from_xml(xml_path: Path) -> str:
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return ""
    image_dir = gallery_image_dir_from_xml(xml_path)
    sections: list[str] = []
    for cat in root.findall("category"):
        cat_name = cat.attrib.get("name", "Gallery")
        cells: list[str] = []
        for image in cat.findall("image"):
            fname = (image.findtext("img") or image.findtext("thumb") or "").strip()
            if not fname or fname.lower() in SKIP_NAMES:
                continue
            title = (image.findtext("title") or fname).strip()
            src = f"{image_dir}/{fname}"
            if not asset_exists(src):
                continue
            cells.append(
                f'<div class="col-6 col-md-4 col-lg-3">'
                f'<a class="gallery-thumb" href="{src}" target="_blank" rel="noopener">'
                f'<img src="{src}" alt="{title}" class="img-fluid" loading="lazy"></a>'
                f'<p class="gallery-caption small text-muted">{title}</p></div>'
            )
        if cells:
            sections.append(
                f'<div class="gallery-category"><h3 class="gallery-category-title">{cat_name}</h3>'
                f'<div class="row g-3">{"".join(cells)}</div></div>'
            )
    if not sections:
        return ""
    return f'<section class="flash-gallery-recovery">{"".join(sections)}</section>'


def majestic_gallery_html() -> str:
    sections: list[str] = []
    root = SOURCE / "majestic_gallery"
    if not root.exists():
        return ""
    for section_dir in sorted(root.iterdir()):
        if not section_dir.is_dir():
            continue
        full_dir = section_dir / "Full"
        if not full_dir.is_dir():
            continue
        cells: list[str] = []
        for img in sorted(full_dir.iterdir()):
            if img.suffix.lower() not in IMAGE_EXT:
                continue
            rel = img.relative_to(SOURCE).as_posix()
            if not asset_exists(rel):
                continue
            title = img.stem
            cells.append(
                f'<div class="col-6 col-md-4 col-lg-3">'
                f'<a class="gallery-thumb" href="{rel}" target="_blank" rel="noopener">'
                f'<img src="{rel}" alt="{title}" class="img-fluid" loading="lazy"></a></div>'
            )
        if cells:
            sections.append(
                f'<div class="gallery-category"><h3 class="gallery-category-title">{section_dir.name}</h3>'
                f'<div class="row g-3">{"".join(cells)}</div></div>'
            )
    if not sections:
        return ""
    return f'<section class="flash-gallery-recovery majestic-gallery">{"".join(sections)}</section>'


def flipbook_embed_html(flipbook_folder: str) -> str:
    book = FLIPBOOK_BY_FOLDER.get(flipbook_folder)
    if not book:
        return ""
    pdf = f"assets/pdfs/{book['pdf']}"
    return f"""
    <div class="flipbook-recovery">
      <p class="lead">Read <strong>{book['title']}</strong> as PDF — no Flash required.</p>
      <div class="d-flex flex-wrap gap-2 mb-3">
        <a class="btn btn-gold" href="{book['source_html']}">Open reader</a>
        <a class="btn btn-outline-sacred" href="{pdf}" target="_blank" rel="noopener">View PDF</a>
        <a class="btn btn-outline-sacred" href="{pdf}" download>Download PDF</a>
      </div>
      <object data="{pdf}" type="application/pdf" class="pdf-object">
        <p><a href="{pdf}">Download the PDF</a>.</p>
      </object>
    </div>"""


def replacement_for_flash_base(base: str, *, page_name: str = "") -> str:
    base = normalize_web_path(base).replace(".swf", "")

    if base in ("video", "video.swf") or base.endswith("/video"):
        return f'<section class="video-recovery">{VIMEO_PROGRAMS}</section>'

    if "islamic_pic_gallery" in base or base.endswith("/gallery"):
        xml_path = SOURCE / "islamic_pic_gallery" / "gallery.xml"
        html = gallery_from_xml(xml_path) if xml_path.exists() else ""
        if page_name == "gallery.html":
            majestic = majestic_gallery_html()
            if majestic:
                html = (html + majestic) if html else majestic
        return html or (
            '<p class="flash-fallback-note">Photo gallery images are not synced yet. '
            "Run <code>python scripts/mirror_media.py</code>.</p>"
        )

    if base.startswith("audio/") or "/audio/" in f"/{base}/":
        tracks = resolve_audio_tracks(base)
        return audio_playlist_html(tracks)

    return ""


def replace_flash_in_html(html: str, *, page_name: str = "") -> str:
    soup = BeautifulSoup(html, "html.parser")
    replacements: list[tuple[Tag, str]] = []

    for script in list(soup.find_all("script")):
        text = script.string or ""
        if "AC_FL_RunContent" not in text:
            continue
        base = parse_ac_fl_movie(text)
        if not base:
            script.decompose()
            continue
        repl = replacement_for_flash_base(base, page_name=page_name)
        parent = script.parent if isinstance(script.parent, Tag) else None
        script.decompose()
        if parent:
            for sib in list(parent.find_all(["object", "noscript"])):
                sib.decompose()
        if repl and parent:
            if parent.name in ("h5", "h6", "p") and len(parent.get_text(strip=True)) < 5:
                parent.replace_with(BeautifulSoup(repl, "html.parser"))
            elif parent.find("audio") or parent.find(class_="flash-gallery-recovery"):
                continue
            else:
                parent.insert(0, BeautifulSoup(repl, "html.parser"))

    for tag in list(soup.find_all(["object", "embed"])):
        attrs = tag.attrs or {}
        src = (attrs.get("src") or attrs.get("value") or "").lower()
        if "swf" not in src and not (tag.name == "object" and "movie" in str(attrs).lower()):
            continue
        base = normalize_web_path(re.sub(r"\.swf$", "", src, flags=re.I))
        repl = replacement_for_flash_base(base, page_name=page_name)
        parent = tag.parent if isinstance(tag.parent, Tag) else None
        tag.decompose()
        if repl and parent and parent.name not in ("html", "body", "[document]"):
            replacements.append((parent, repl))

    for iframe in list(soup.find_all("iframe")):
        src = iframe.get("src", "")
        m = re.search(r"(flibbok\d?)", src, re.I)
        if not m:
            continue
        repl = flipbook_embed_html(m.group(1).lower())
        if repl:
            wrapper = soup.new_tag("div")
            wrapper.append(BeautifulSoup(repl, "html.parser"))
            iframe.replace_with(wrapper)

    for parent, repl_html in replacements:
        if parent.find("audio") or parent.find(class_="flash-gallery-recovery"):
            continue
        block = BeautifulSoup(repl_html, "html.parser")
        # Replace empty flash wrapper <p> with recovery content
        if parent.name == "p" and len(parent.get_text(strip=True)) < 3:
            parent.replace_with(block)
        else:
            parent.insert(0, block)

    return str(soup)


def recover_flash_content(html: str, *, page_name: str = "") -> str:
    if not re.search(r"AC_FL_RunContent|shockwave-flash|\.swf|flibbok\d", html, re.I):
        return html
    return replace_flash_in_html(html, page_name=page_name)
