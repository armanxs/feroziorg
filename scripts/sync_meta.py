"""Pull page titles and meta tags from live FTP source into web/ pages."""
from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
WEB = ROOT / "web"

# web page -> source page (and optional live-known overrides)
MAP = {
    "index.html": "index.html",
    "biographies.html": "blessed_personalities.html",
    "publications.html": "our_publication.html",
    "silsilatayyabaqadri.html": "silsilatayyabaqadri.html",
    "silsilatayyabanaqshbandia.html": "silsilatayyabanaqshbandia.html",
    "shajra.html": "shajra.html",
    "video-gallery.html": "Videos.html",
}

# Prefer exact live titles / descriptions where known
OVERRIDES = {
    "index.html": {
        "title": "Welcome To The Official Website Of Jamat-e-Qasmia Ferozia Ahl-e-Sunnat Pakistan (Trust) - Home",
        "description": (
            "Official website of Jamat-e-Qasmia Ferozia Ahl-e-Sunnat Pakistan (Trust). "
            "His Illustrious Majesty Yusuf-ul-Aulia, Hazart pir Sayyed Feroz Shah Qasimi "
            "(Damat Barakatuhumul Aliah). Seekers of divinity and mysticism at Dargha-e-Aaliah Qasimia Ferozia."
        ),
        "keywords": (
            "Ferozi, Jamat-e-Qasmia Ferozia, Ahl-e-Sunnat, Pir Sayyed Feroz Shah Qasimi, "
            "Qadiria, Naqshbandia, Sufism, Pakistan, Dargha-e-Aaliah Qasimia Ferozia"
        ),
    },
    "biographies.html": {
        "title": "Ferozi - Blessed Personalities",
        "description": (
            "Sacred biographies of Hazrat Pir Sayyed Feroz Shah Qasimi and the blessed "
            "personalities of Jamat-e-Qasmia Ferozia Ahl-e-Sunnat Pakistan (Trust), "
            "including Silsila Tayyaba and Shajra-e-Tayyaba."
        ),
    },
    "publications.html": {
        "title": "Ferozi - Our Publications",
        "description": (
            "Publications of Jamat-e-Qasmia Ferozia Ahl-e-Sunnat Pakistan (Trust): "
            "Yaad-e-Baiza, Al Muridu La Yurid, 10 Basic Beliefs, Reflection, and more — "
            "available as PDF downloads."
        ),
    },
    "video-gallery.html": {
        "title": "Video Gallery | Ferozi.org",
        "description": (
            "Video gallery of Friday sermons and programs by Hazrat Pir Sayyed Feroz Shah Qasimi "
            "from the official Ferozi Vimeo account."
        ),
    },
    "silsilatayyabaqadri.html": {
        "title": "Ferozi Succession - Silsila Tayyaba Tareeqat Qadiria Rashidia Qasimia Ferozia",
        "description": (
            "Silsila Tayyaba Tareeqat Qadiria Rashidia Qasimia Ferozia — spiritual chain of "
            "Hazrat Pir Sayyed Feroz Shah Qasimi Qadiri Naqshbandi Tirmizi Buneri (D.B.A.)."
        ),
    },
    "silsilatayyabanaqshbandia.html": {
        "title": "Ferozi Succession - Silsila Tayyaba Tareeqat Naqshbandia Rashidia Qasimia Ferozia",
        "description": (
            "Silsila Tayyaba Tareeqat Naqshbandia Rashidia Qasimia Ferozia — spiritual chain of "
            "Hazrat Pir Sayyed Feroz Shah Qasimi Qadiri Naqshbandi Tirmizi Buneri (D.B.A.)."
        ),
    },
    "shajra.html": {
        "title": (
            "Ferozi Succession - Sayyed-us-Sadaat, Qasim-ul-Khairat, Hazrat Pir Sayyed Ferozi Shah "
            "Qasimi Qadiri Naqshbandi Tirmizi Buneri`s (D.B.A) Shajra-e-Tayyaba"
        ),
        "description": (
            "Shajra-e-Tayyaba of Sayyed-us-Sadaat, Qasim-ul-Khairat, Hazrat Pir Sayyed Ferozi Shah "
            "Qasimi Qadiri Naqshbandi Tirmizi Buneri (D.B.A.)."
        ),
    },
}


SKIP_META = {
    "viewport",
    "content-type",
    "x-ua-compatible",
    "generator",
}


def extract_from_source(src_name: str) -> dict:
    path = SOURCE / src_name
    if not path.exists():
        return {}
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    data: dict = {"title": "", "description": "", "keywords": "", "author": ""}
    if soup.title and soup.title.string:
        data["title"] = " ".join(soup.title.string.split())
    for m in soup.find_all("meta"):
        name = (m.get("name") or m.get("property") or "").strip().lower()
        content = (m.get("content") or "").strip()
        if not name or not content or name in SKIP_META:
            continue
        if name in {"description", "keywords", "author"}:
            data[name] = content
    return data


def upsert_meta(soup: BeautifulSoup, name: str, content: str) -> None:
    if not content:
        return
    tag = soup.head.find("meta", attrs={"name": name}) if soup.head else None
    if tag:
        tag["content"] = content
    else:
        tag = soup.new_tag("meta", attrs={"name": name, "content": content})
        # insert after charset/viewport if present
        anchor = None
        for candidate in soup.head.find_all("meta"):
            anchor = candidate
        if anchor:
            anchor.insert_after(tag)
        else:
            soup.head.append(tag)


def apply_to_page(web_name: str, meta: dict) -> None:
    path = WEB / web_name
    if not path.exists():
        print(f"skip missing {web_name}")
        return
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    if not soup.head:
        print(f"no head {web_name}")
        return

    title = meta.get("title") or ""
    if title:
        if soup.title:
            soup.title.string = title
        else:
            t = soup.new_tag("title")
            t.string = title
            soup.head.insert(0, t)

    upsert_meta(soup, "description", meta.get("description", ""))
    upsert_meta(soup, "keywords", meta.get("keywords", ""))
    if meta.get("author"):
        upsert_meta(soup, "author", meta["author"])

    # Keep charset/viewport intact; ensure language
    if not soup.html.get("lang"):
        soup.html["lang"] = "en"

    path.write_text(str(soup), encoding="utf-8")
    print(f"updated {web_name}: {title[:80]}")


def main() -> int:
    for web_name, src_name in MAP.items():
        meta = extract_from_source(src_name) if src_name else {}
        override = OVERRIDES.get(web_name, {})
        merged = {**meta, **{k: v for k, v in override.items() if v}}
        # Fallback titles if source empty
        if not merged.get("title"):
            fallbacks = {
                "video-gallery.html": "Video Gallery | Ferozi.org",
                "publications.html": "Our Publications | Ferozi.org",
                "biographies.html": "Sacred Biographies | Ferozi.org",
            }
            merged["title"] = fallbacks.get(web_name, "Ferozi.org")
        if not merged.get("description"):
            merged["description"] = (
                "Jamat-e-Qasmia Ferozia Ahl-e-Sunnat Pakistan (Trust) — "
                "spirituality, Sufism, and sacred tradition. Official website of Ferozi.org."
            )
        if not merged.get("keywords"):
            merged["keywords"] = (
                "Ferozi, Jamat-e-Qasmia Ferozia, Ahl-e-Sunnat Pakistan, "
                "Pir Sayyed Feroz Shah Qasimi, Sufism"
            )
        apply_to_page(web_name, merged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
