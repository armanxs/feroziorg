"""Generate responsive static site from mirrored source HTML."""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

from config import BOOKS, MOCKUP, ROOT, SITE, SOURCE
from flash_recovery import gallery_from_xml, majestic_gallery_html, recover_flash_content

NAV = [
    {"label": "HOME", "href": "index.html"},
    {"label": "MEMBERSHIP", "href": "membership.html"},
    {
        "label": "GIST OF ISLAM",
        "href": "giftofislam.html",
        "children": [
            {"label": "Tareeqat", "href": "tareeqat.html"},
            {"label": "Shariat", "href": "shariat.html"},
            {"label": "Maarifat", "href": "maarifat.html"},
            {"label": "Haqeeqat", "href": "haqeeqat.html"},
        ],
    },
    {"label": "ISLAMIC LITERATURE", "href": "islamic_literature.html"},
    {"label": "CONTACT US", "href": "contactus.html"},
]

PANEL = [
    {"label": "Ferozi Calendar", "href": "calendar.html"},
    {"label": "Blessed Personalities", "href": "blessed_personalities.html"},
    {"label": "The Majestic Gallery", "href": "gallery.html"},
    {"label": "Our Publications", "href": "our_publication.html"},
    {"label": "Our Projects", "href": "our_project.html"},
]

BOOK_BY_HTML = {b["source_html"]: b for b in BOOKS}

PLACEHOLDER_MARKERS = (
    "currently updating the content for this section",
    "under editing and will soon be published",
)

# FTP typo: misconceptions links to ilm4.html but file is iml4.html
SOURCE_ALIASES = {"ilm4.html": "iml4.html"}
OUTPUT_ALIASES = {"iml4.html": "ilm4.html"}

CONTENT_ALIASES: dict[str, str] = {
    "tareeqat.html": "theguide.html",
    "maarifat.html": "reflection.html",
    "haqeeqat.html": "reflection.html",
}

SHARIAT_INTRO = """
<div class="section-intro">
  <p class="lead">Shariat is the sacred Islamic law — the foundation upon which Tareeqat, Maarifat, and Haqeeqat are built.</p>
  <p>Jamat-e-Qasimia Ferozia Ahl-e-Sunnat Pakistan (Trust) adheres to complete codes of Shariah (Islamic Law) and Tareeqat under the guidance of Hazrat Pir Syed Feroz Shah Qasimi (D.B.A.). Every spiritual practice is rooted in the commands of the Qur'an and Sunnah.</p>
  <p>Explore related literature: <a href="donteatpork.html">Why Muslims Don't Eat Pork</a> · <a href="misconceptions.html">Misconceptions of Islam</a> · <a href="our_publication.html">Our Publications</a></p>
</div>"""

GIST_SECTION = "giftofislam.html"
GIST_PAGES = {GIST_SECTION, "tareeqat.html", "shariat.html", "maarifat.html", "haqeeqat.html"}
EXCLUDED_PAGES = frozenset({
    "thiholyprophet.html",
    "fundamentalsaboutprophethood.html",
    "lifeofholyprophet.html",
    "media.html",
    "islamicpic.html",
    "Videos.html",
    "Islamicart.html",
    "audio.html",
    "speechesandprograms.html",
    "test.html",
    "naats.html",
    "arifana.html",
    "azan.html",
    "arabic.html",
    "duroods.html",
    "dua.html",
    "quran.html",
    "hamds.html",
    "persian.html",
    "english.html",
    "punjabi.html",
    "sindhi.html",
    "manqabat.html",
    "salam.html",
    "miscellaneous.html",
    "afzalnoshahi.html",
    "azamchishti.html",
    "khursheedahmed.html",
    "malizahoori.html",
    "marghoobahmed.html",
    "owais.html",
    "rehanqadri.html",
    "sfasihuddin.html",
    "siddiqueismail.html",
    "waheedzafar.html",
    "hooriarafique.html",
    "ecards.html",
})
LIT_SECTION = "islamic_literature.html"
LIT_PAGES = {LIT_SECTION, "chronology.html", "donteatpork.html", "misconceptions.html"}
BIO_SECTION = "blessed_personalities.html"
BIO_PAGES = {
    BIO_SECTION,
    "hazratppirsayyedferozshahqasimi.html",
    "shahzadahazratsayyedali.html",
    "hazratsayyedanwaarhusain.html",
    "pirsainmuhammadqasim.html",
    "sainsayyedmuhammadrashid.html",
    "sayyedalighawwas.html",
    "silsilatayyabaqadri.html",
    "silsilatayyabanaqshbandia.html",
    "shajra.html",
}

_SECTION_NAV: dict[str, list[dict[str, str]]] | None = None


def resolve_source_path(name: str) -> Path:
    alias = SOURCE_ALIASES.get(name)
    if alias:
        path = SOURCE / alias
        if path.exists():
            return path
    return SOURCE / name


def output_names_for(name: str) -> list[str]:
    names = [name]
    extra = OUTPUT_ALIASES.get(name)
    if extra and extra not in names:
        names.append(extra)
    return names


def is_placeholder(text: str) -> bool:
    lower = text.lower()
    return any(m in lower for m in PLACEHOLDER_MARKERS)


def extract_popup_links(html_path: Path) -> list[dict[str, str]]:
    if not html_path.exists():
        return []
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    node = (
        soup.select_one("#textarea_content")
        or soup.select_one("#datacontainer")
        or soup.select_one("#textarea2_temp")
        or soup.select_one("#left_subcontent")
    )
    if not node:
        return []
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for a in node.find_all("a"):
        href = a.get("href", "")
        for attr, val in a.attrs.items():
            if attr.startswith("on") and isinstance(val, str):
                m = re.search(r"MM_openBrWindow\s*\(\s*['\"]([^'\"]+)['\"]", val, re.I)
                if m:
                    href = m.group(1)
        if not href.endswith(".html") or href.startswith("http") or href in ("#", "#6"):
            continue
        href = OUTPUT_ALIASES.get(href, href)
        label = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if not label or href in seen or len(label) > 120:
            continue
        seen.add(href)
        links.append({"label": label, "href": href})
    return links


def build_section_nav_map() -> dict[str, list[dict[str, str]]]:
    global _SECTION_NAV
    if _SECTION_NAV is not None:
        return _SECTION_NAV

    _SECTION_NAV = {
        GIST_SECTION: [
            {"label": "Gist of Islam", "href": GIST_SECTION},
            {"label": "Tareeqat", "href": "tareeqat.html"},
            {"label": "Shariat", "href": "shariat.html"},
            {"label": "Maarifat", "href": "maarifat.html"},
            {"label": "Haqeeqat", "href": "haqeeqat.html"},
        ],
        LIT_SECTION: [
            {"label": "Islamic Literature", "href": LIT_SECTION},
            {"label": "Chronology", "href": "chronology.html"},
            {"label": "Don't Eat Pork", "href": "donteatpork.html"},
            {"label": "Misconceptions of Islam", "href": "misconceptions.html"},
        ],
        BIO_SECTION: [
            {"label": "Blessed Personalities", "href": BIO_SECTION},
            {"label": "Hazrat Pir Sayyed Feroz Shah Qasimi (D.B.A.)", "href": "hazratppirsayyedferozshahqasimi.html"},
            {"label": "Shahzada Hazrat Sayyed Ali Muhammad Shah Shaheed (R.A.)", "href": "shahzadahazratsayyedali.html"},
            {"label": "Shahzada Hazrat Sayyed Anwaar Husain Shah (R.A.)", "href": "hazratsayyedanwaarhusain.html"},
            {"label": "Hazrat Pir Sain Muhammad Qasim Mashori (R.A.)", "href": "pirsainmuhammadqasim.html"},
            {"label": "Hazrat Pir Sain Sayyed Muhammad Rashid Rozay Dhani (R.A.)", "href": "sainsayyedmuhammadrashid.html"},
            {"label": "Hazrat Sayyed Ali Ghawwas, Pir Baba (R.A.)", "href": "sayyedalighawwas.html"},
            {"label": "Silsila Qadiria", "href": "silsilatayyabaqadri.html"},
            {"label": "Silsila Naqshbandia", "href": "silsilatayyabanaqshbandia.html"},
            {"label": "Shajra", "href": "shajra.html"},
        ],
        "misconceptions.html": [
            {"label": "Misconceptions of Islam", "href": "misconceptions.html"},
            *extract_popup_links(SOURCE / "misconceptions.html"),
        ],
        "chronology.html": [
            {"label": "Chronology", "href": "chronology.html"},
            *extract_popup_links(SOURCE / "chronology.html"),
        ],
    }
    return _SECTION_NAV


def section_for_page(name: str) -> str | None:
    if name in EXCLUDED_PAGES:
        return None
    if name in GIST_PAGES:
        return GIST_SECTION
    if name in LIT_PAGES:
        return LIT_SECTION
    if name in BIO_PAGES:
        return BIO_SECTION
    if re.fullmatch(r"ilm\d+\.html", name) or name == "iml4.html":
        return "misconceptions.html"
    if re.fullmatch(r"\d+thcentury\.html", name):
        return "chronology.html"
    return None


def is_article_page(name: str, source_path: Path) -> bool:
    if name in BIO_PAGES and name != BIO_SECTION:
        return True
    if re.fullmatch(r"ilm\d+\.html", name) or name in ("iml4.html",):
        return True
    if re.fullmatch(r"\d+thcentury\.html", name):
        return True
    raw = source_path.read_text(encoding="utf-8", errors="replace") if source_path.exists() else ""
    return "include/popup.css" in raw and name not in LIT_PAGES | GIST_PAGES | EXCLUDED_PAGES


def section_sidebar_html(section_key: str, active: str) -> str:
    nav = build_section_nav_map().get(section_key, [])
    if not nav:
        return ""
    items = []
    for link in nav:
        cls = "active" if link["href"] == active else ""
        items.append(f'<li><a class="{cls}" href="{link["href"]}">{link["label"]}</a></li>')
    title = nav[0]["label"] if nav else "In this section"
    return f"""
        <div class="section-sidebar">
          <p class="section-sidebar-title">{title}</p>
          <ul class="section-sidebar-links">{"".join(items)}</ul>
        </div>"""


def unwrap_content_divs(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for _ in range(12):
        changed = False
        for div in soup.find_all("div"):
            div_id = div.get("id", "")
            if div_id.startswith("textarea") and not div.get_text(strip=True):
                if not div.find(["img", "iframe", "video", "table", "ul", "ol", "h2", "h3", "h4", "h5", "h6", "p"]):
                    div.decompose()
                    changed = True
        if not changed:
            break
    for div in soup.find_all("div"):
        if div.get("id", "").startswith("textarea") and len(div.contents) == 1:
            child = div.contents[0]
            if isinstance(child, Tag) and child.name == "div":
                div.unwrap()
    return str(soup)


def gist_hub_intro() -> str:
    return """
    <div class="section-intro">
      <p class="lead">The Gist of Islam is understood through four interconnected paths — each guiding the seeker toward the Divine.</p>
      <div class="row g-3 gist-cards">
        <div class="col-md-6"><a class="gist-card" href="tareeqat.html"><strong>Tareeqat</strong><span>The spiritual path and guidance of the Murshid</span></a></div>
        <div class="col-md-6"><a class="gist-card" href="shariat.html"><strong>Shariat</strong><span>Islamic law and sacred commandments</span></a></div>
        <div class="col-md-6"><a class="gist-card" href="maarifat.html"><strong>Maarifat</strong><span>Intimate knowledge and recognition of Allah</span></a></div>
        <div class="col-md-6"><a class="gist-card" href="haqeeqat.html"><strong>Haqeeqat</strong><span>The ultimate reality and truth of existence</span></a></div>
      </div>
    </div>"""


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", name).strip("-").lower()


def extract_title(soup: BeautifulSoup, fallback: str) -> str:
    if soup.title and soup.title.string:
        t = soup.title.string.strip()
        t = re.sub(r"^Ferozi\s*-\s*", "", t, flags=re.I)
        t = re.sub(r"^Ferozi\.org\s*-\s*", "", t, flags=re.I)
        t = re.sub(r"^Welcome To.*-\s*", "", t, flags=re.I)
        if t:
            return t
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return fallback


def make_responsive_iframes(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for iframe in soup.find_all("iframe"):
        parent = iframe.parent
        if parent and parent.name == "div":
            style = parent.get("style", "")
            if "padding:" in style and "position:relative" in style.replace(" ", ""):
                iframe["loading"] = "lazy"
                iframe["class"] = (iframe.get("class") or []) + ["embed-iframe"]
                continue
        iframe.attrs.pop("width", None)
        iframe.attrs.pop("height", None)
        iframe["loading"] = "lazy"
        iframe["class"] = (iframe.get("class") or []) + ["embed-iframe"]
        wrapper = soup.new_tag("div")
        wrapper["class"] = "ratio ratio-16x9 embed-wrap"
        iframe.replace_with(wrapper)
        wrapper.append(iframe)
    for p in soup.find_all("p"):
        if len(p.contents) == 1 and getattr(p.contents[0], "name", None) == "div":
            p.unwrap()
    for img in soup.find_all("img"):
        if not img.get("alt"):
            img["alt"] = ""
        img["class"] = list(set((img.get("class") or []) + ["img-fluid"]))
        src = img.get("src", "")
        if src.startswith("/"):
            img["src"] = src.lstrip("/")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/"):
            a["href"] = href.lstrip("/")
        if href.endswith(".php"):
            a["href"] = href.replace(".php", ".html")
    return str(soup)


def fix_legacy_content(content: str, page_title: str, *, page_name: str = "") -> str:
    """Repair popup links, strip noise, and recover content lost to Flash."""
    content = recover_flash_content(content, page_name=page_name)
    soup = BeautifulSoup(content, "html.parser")

    header = soup.select_one("#header img, .legacy-header-img img")
    if not header:
        pass  # header injected separately in extract_body_content

    for a in soup.find_all("a"):
        href = a.get("href", "")
        for attr, val in list(a.attrs.items()):
            if attr.startswith("on") and isinstance(val, str):
                m = re.search(r"MM_openBrWindow\s*\(\s*['\"]([^'\"]+)['\"]", val, re.I)
                if m:
                    href = m.group(1)
                    a["href"] = OUTPUT_ALIASES.get(href, href)
                    del a[attr]
        onclick = a.get("onclick", "")
        match = re.search(r"MM_openBrWindow\s*\(\s*['\"]([^'\"]+)['\"]", onclick, re.I)
        if match:
            a["href"] = OUTPUT_ALIASES.get(match.group(1), match.group(1))
            if "onclick" in a.attrs:
                del a["onclick"]
        elif a.get("href") in ("#", "#6") and onclick:
            match2 = re.search(r"['\"]([^'\"]+\.html)['\"]", onclick)
            if match2:
                a["href"] = OUTPUT_ALIASES.get(match2.group(1), match2.group(1))
                del a["onclick"]
        for attr in list(a.attrs):
            if attr not in ("href", "class", "title", "target", "rel"):
                if attr.startswith("on") or '"' in attr or ')' in attr:
                    del a[attr]

    for tag in soup.find_all(["object", "embed"]):
        if tag.get("type", "").startswith("application/x-shockwave") or "swf" in tag.get("src", "").lower():
            tag.decompose()
    for script in soup.find_all("script"):
        if script.string and "AC_FL_RunContent" in script.string:
            script.decompose()

    for h1 in soup.find_all("h1"):
        if h1.get_text(strip=True).lower() == page_title.strip().lower():
            h1.decompose()

    for h6 in soup.find_all("h6"):
        if not h6.get_text(strip=True):
            h6.decompose()

    for br in soup.find_all("br"):
        nxt = br.next_sibling
        if isinstance(nxt, Tag) and nxt.name == "br":
            br.decompose()

    text = soup.get_text(strip=True)
    has_recovery = soup.select_one(
        ".flash-gallery-recovery, .video-recovery, .audio-playlist, "
        ".flipbook-recovery, .flash-fallback-note"
    )
    if ("gallery.swf" in content or not text or len(text) < 40) and not has_recovery:
        gallery_html = gallery_images_html(page_name=page_name)
        if gallery_html:
            soup.append(BeautifulSoup(gallery_html, "html.parser"))

    cleaned = str(soup)
    cleaned = re.sub(r"<noscript>[\s\S]*?</noscript>", "", cleaned, flags=re.I)
    footer_soup = BeautifulSoup(cleaned, "html.parser")
    for p in footer_soup.find_all("p"):
        text = p.get_text().lower()
        if "powered by: computer division" in text:
            p.decompose()
        elif "info@ferozi.org" in text and any(
            marker in text for marker in ("copyright", "operated by", "rights reserved", "developed by")
        ):
            p.decompose()
    cleaned = str(footer_soup)
    cleaned = re.sub(r'<p[^>]*>\s*<a[^>]*>\s*Back\s*</a>\s*</p>', "", cleaned, flags=re.I)
    cleaned = unwrap_content_divs(cleaned)
    return cleaned


def extract_body_content(html_path: Path, *, page_name: str = "") -> tuple[str, str]:
    name = page_name or html_path.name
    orig_path = SOURCE / name
    if name in CONTENT_ALIASES:
        alias_path = SOURCE / CONTENT_ALIASES[name]
        if alias_path.exists():
            html_path = alias_path

    raw = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    title = extract_title(soup, html_path.stem.replace("_", " ").title())
    if orig_path.exists() and name in CONTENT_ALIASES:
        orig_soup = BeautifulSoup(orig_path.read_text(encoding="utf-8", errors="replace"), "html.parser")
        title = extract_title(orig_soup, name.replace(".html", "").replace("_", " ").title())

    article = is_article_page(name, html_path)

    node = (
        soup.select_one("#textarea_content")
        or soup.select_one("#datacontainer")
        or soup.select_one("#textarea2_temp")
        or soup.select_one("#left_subcontent")
        or soup.select_one("#textarea1")
        or soup.select_one("#leftcontainer")
        or soup.select_one("#wrap")
    )
    if not node:
        body = soup.body or soup
        content = "".join(str(c) for c in body.children if isinstance(c, Tag))
    else:
        for bad in node.select("#menu_pannel, #header, .menu_pannel"):
            bad.decompose()
        content = node.decode_contents()

    header_img = soup.select_one("#header img")
    if header_img and header_img.get("src") and not article:
        src = header_img["src"].lstrip("/")
        content = f'<figure class="legacy-header-img"><img src="{src}" alt="" class="img-fluid"></figure>\n{content}'

    content = fix_legacy_content(content, title, page_name=name)
    content = re.sub(r"<script[\s\S]*?</script>", "", content, flags=re.I)
    content = re.sub(r"mmLoadMenus\(\);?", "", content)
    content = make_responsive_iframes(content)

    if name == GIST_SECTION and is_placeholder(content):
        content = gist_hub_intro() + content

    if name == "shariat.html" and is_placeholder(content):
        content = SHARIAT_INTRO + content

    if name == BIO_SECTION:
        soup_hub = BeautifulSoup(content, "html.parser")
        for ul in soup_hub.find_all("ul"):
            if ul.find("a", href=re.compile(r"hazrat|shahzada|pirsain|sayyed")):
                ul.decompose()
        content = str(soup_hub)

    if name == "calendar.html":
        content = re.sub(r'<a href="#">', "<span>", content)
        content = re.sub(r"</a>", "</span>", content)

    return title, content


def gallery_images_html(page_name: str = "") -> str:
    """Build image grid from gallery.xml, majestic_gallery, or gallery1.html."""
    xml_path = SOURCE / "islamic_pic_gallery" / "gallery.xml"
    if xml_path.exists():
        html = gallery_from_xml(xml_path)
        if html:
            if page_name == "gallery.html":
                majestic = majestic_gallery_html()
                if majestic:
                    html += majestic
            return html
    gallery_src = SOURCE / "gallery1.html"
    imgs: list[str] = []
    if gallery_src.exists():
        raw = gallery_src.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if not src or "logo" in src.lower() or "header" in src.lower() or "ferozi_session" in src:
                continue
            if src.startswith("/"):
                src = src.lstrip("/")
            imgs.append(src)
    if not imgs:
        site_img = SITE / "images"
        if site_img.exists():
            for f in sorted(site_img.rglob("*")):
                if f.suffix.lower() in (".jpg", ".jpeg", ".png") and f.stat().st_size > 2048:
                    fname = f.name.lower()
                    if any(x in fname for x in ("header", "logo", "border", "arrow", "gray-bg", "banner")):
                        continue
                    imgs.append(str(f.relative_to(SITE)).replace("\\", "/"))
                if len(imgs) >= 12:
                    break
    if not imgs:
        return ""
    cells = []
    for src in imgs:
        cells.append(
            f'<div class="col-6 col-md-4 col-lg-3">'
            f'<a class="gallery-thumb" href="{src}" target="_blank" rel="noopener">'
            f'<img src="{src}" alt="Gallery image" class="img-fluid" loading="lazy"></a></div>'
        )
    return f'<section class="photo-gallery-grid"><div class="row g-3">{"".join(cells)}</div></section>'


def nav_html(active: str) -> str:
    items = []
    for item in NAV:
        active_cls = "active" if item["href"] == active else ""
        if item.get("children"):
            child_links = "".join(
                f'<li><a class="dropdown-item" href="{c["href"]}">{c["label"]}</a></li>'
                for c in item["children"]
            )
            items.append(
                f"""<li class="nav-item dropdown">
                  <a class="nav-link dropdown-toggle {active_cls}" href="{item['href']}" role="button"
                     data-bs-toggle="dropdown" aria-expanded="false">{item['label']}</a>
                  <ul class="dropdown-menu dropdown-menu-dark">{child_links}</ul>
                </li>"""
            )
        else:
            items.append(
                f'<li class="nav-item"><a class="nav-link {active_cls}" href="{item["href"]}">{item["label"]}</a></li>'
            )
    return "\n".join(items)


def panel_html(active: str) -> str:
    links = []
    for p in PANEL:
        cls = "active" if p["href"] == active else ""
        links.append(f'<li><a class="{cls}" href="{p["href"]}">{p["label"]}</a></li>')
    return "\n".join(links)


def ferozi_strip_html(active: str = "") -> str:
    items = []
    for p in PANEL:
        cls = "active" if p["href"] == active else ""
        items.append(f'<a class="ferozi-strip-link {cls}" href="{p["href"]}">{p["label"]}</a>')
    return "\n".join(items)


def extract_home_videos(html_path: Path) -> list[tuple[str, str]]:
    """Parse h3 + iframe pairs from raw home HTML."""
    if not html_path.exists():
        return []
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    videos: list[tuple[str, str]] = []
    for h3 in soup.find_all("h3"):
        title = h3.get_text(strip=True)
        if not title or title.lower() == "recent programs":
            nxt = h3.find_next_sibling()
            while nxt and nxt.name != "h3":
                if nxt.name == "p" and nxt.find("iframe"):
                    videos.append((title, make_responsive_iframes(str(nxt))))
                    break
                nxt = nxt.find_next_sibling()
            continue
        nxt = h3.find_next_sibling("p")
        if nxt and nxt.find("iframe"):
            videos.append((title, make_responsive_iframes(str(nxt))))
    return videos


BIOGRAPHY_TABS = [
    {
        "file": "hazratppirsayyedferozshahqasimi.html",
        "tab_id": "bio-feroz",
        "line1": "Hazrat Pir Sayyed",
        "line2": "Feroz Shah Qasimi",
        "suffix": "(D.B.A.)",
    },
    {
        "file": "shahzadahazratsayyedali.html",
        "tab_id": "bio-ali",
        "line1": "Shahzada Hazrat Sayyed",
        "line2": "Ali Muhammad Shah Shaheed",
        "suffix": "(R.A.)",
    },
    {
        "file": "hazratsayyedanwaarhusain.html",
        "tab_id": "bio-anwaar",
        "line1": "Shahzada Hazrat Sayyed",
        "line2": "Anwaar Hussain Shah",
        "suffix": "(R.A.)",
    },
    {
        "file": "pirsainmuhammadqasim.html",
        "tab_id": "bio-qasim",
        "line1": "Hazrat Pir Sain",
        "line2": "Muhammad Qasim Mashori",
        "suffix": "(R.A.)",
    },
    {
        "file": "sainsayyedmuhammadrashid.html",
        "tab_id": "bio-rashid",
        "line1": "Hazrat Pir Sain Sayyed",
        "line2": "Muhammad Rashid Rozay Dhani",
        "suffix": "(R.A.)",
    },
    {
        "file": "sayyedalighawwas.html",
        "tab_id": "bio-ghawwas",
        "line1": "Hazrat Pir",
        "line2": "Ali Ghawwas, Pir Baba",
        "suffix": "(R.A.)",
    },
]


def mockup_page_banner(title: str, subtitle: str = "") -> str:
    sub = f'<p class="inner-banner-sub">{subtitle}</p>' if subtitle else ""
    return f"""
  <div class="inner-banner-mockup">
    <div class="container">
      <div class="row">
        <div class="col-12 inner-banner-title">
          <h1>{title}</h1>
          {sub}
        </div>
      </div>
    </div>
    <div class="inner-banner-ornament">
      <img src="images/biographies-border.png" alt="" aria-hidden="true">
    </div>
  </div>"""


def ferozi_pills_link_html(section_key: str, active_href: str) -> str:
    nav = build_section_nav_map().get(section_key, [])
    pills = []
    scroll_cls = " ferozi-pills--scroll" if len(nav) > 8 else ""
    for i, link in enumerate(nav):
        is_active = link["href"] == active_href
        active_cls = " active" if is_active else ""
        bottom = " bottom-link" if i == len(nav) - 1 else ""
        label = link["label"]
        pills.append(
            f'<a class="nav-link{active_cls}{bottom}" href="{link["href"]}">'
            f"<h5>{label}</h5></a>"
        )
    return (
        f'<div class="nav flex-column nav-pills ferozi-pills{scroll_cls}" role="navigation">'
        f'{"".join(pills)}</div>'
        f'<div class="gray-bg" aria-hidden="true"></div>'
    )


def ferozi_pills_tab_html(items: list[dict], active_tab: str) -> str:
    pills = []
    for i, item in enumerate(items):
        is_active = item["tab_id"] == active_tab
        active_cls = " active" if is_active else ""
        bottom = " bottom-link" if i == len(items) - 1 else ""
        aria = "true" if is_active else "false"
        suffix = f'<span>{item["suffix"]}</span>' if item.get("suffix") else ""
        pills.append(
            f'<button class="nav-link{active_cls}{bottom}" id="{item["tab_id"]}-tab" '
            f'data-bs-toggle="pill" data-bs-target="#{item["tab_id"]}" type="button" '
            f'role="tab" aria-controls="{item["tab_id"]}" aria-selected="{aria}">'
            f'<p>{item.get("line1", "")}</p>'
            f'<h5>{item.get("line2", "")}</h5>'
            f"{suffix}</button>"
        )
    return (
        f'<div class="nav flex-column nav-pills ferozi-pills" id="feroziPills" role="tablist">'
        f'{"".join(pills)}</div>'
        f'<div class="gray-bg" aria-hidden="true"></div>'
    )


def bio_section_pills_link_html(active_href: str) -> str:
    pills = []
    for i, bio in enumerate(BIOGRAPHY_TABS):
        is_active = bio["file"] == active_href
        active_cls = " active" if is_active else ""
        bottom = ""
        suffix = f'<span>{bio["suffix"]}</span>' if bio.get("suffix") else ""
        pills.append(
            f'<a class="nav-link{active_cls}{bottom}" href="{bio["file"]}">'
            f'<p>{bio.get("line1", "")}</p>'
            f'<h5>{bio.get("line2", "")}</h5>'
            f"{suffix}</a>"
        )
    extras = [
        ("Silsila Qadiria", "silsilatayyabaqadri.html"),
        ("Silsila Naqshbandia", "silsilatayyabanaqshbandia.html"),
        ("Shajra-e-Tayyaba", "shajra.html"),
    ]
    for j, (label, href) in enumerate(extras):
        is_active = href == active_href
        active_cls = " active" if is_active else ""
        bottom = " bottom-link" if j == len(extras) - 1 else ""
        pills.append(
            f'<a class="nav-link{active_cls}{bottom}" href="{href}"><h5>{label}</h5></a>'
        )
    return (
        f'<div class="nav flex-column nav-pills ferozi-pills" role="navigation">'
        f'{"".join(pills)}</div>'
        f'<div class="gray-bg" aria-hidden="true"></div>'
    )


def publication_tab_items() -> list[dict]:
    items = []
    for book in BOOKS:
        lang = "Urdu" if book["lang"] == "ur" else "English"
        title = book["title"]
        m = re.match(r"^(.+?)\s*\((?:Urdu|English)\)\s*$", title)
        line2 = m.group(1) if m else title
        line2 = line2.replace("Yad-e-Baiza", "Yaad e Baiza").replace("-", " ")
        items.append(
            {
                "tab_id": f"pub-{book['slug']}",
                "line1": lang,
                "line2": line2,
                "book": book,
            }
        )
    return items


def publication_pills_link_html(active_html: str) -> str:
    pills = []
    for i, item in enumerate(publication_tab_items()):
        book = item["book"]
        is_active = book["source_html"] == active_html
        active_cls = " active" if is_active else ""
        bottom = " bottom-link" if i == len(BOOKS) - 1 else ""
        pills.append(
            f'<a class="nav-link{active_cls}{bottom}" href="{book["source_html"]}">'
            f'<p>{item["line1"]}</p>'
            f'<h5>{item["line2"]}</h5></a>'
        )
    return (
        f'<div class="nav flex-column nav-pills ferozi-pills" role="navigation">'
        f'{"".join(pills)}</div>'
        f'<div class="gray-bg" aria-hidden="true"></div>'
    )


def publication_tab_pane_html(book: dict) -> str:
    pdf_href = f"assets/pdfs/{book['pdf']}"
    title = book["title"]
    m = re.match(r"^(.+?)\s*\((?:Urdu|English)\)\s*$", title)
    display = m.group(1).replace("Yad-e-Baiza", "Yaad e Baiza") if m else title
    return f"""
      <div class="requires-chains publication-pane">
        <h4>{display}</h4>
        <p>Sacred publication — read on any device or download the PDF.</p>
        <ul class="list-group connection-often">
          <li><i class="fas fa-chevron-right"></i>
            <a href="{book['source_html']}">Open full reader with PDF preview</a></li>
          <li><i class="fas fa-chevron-right"></i>
            <a href="{pdf_href}" target="_blank" rel="noopener">View PDF in browser</a></li>
          <li><i class="fas fa-chevron-right"></i>
            <a href="{pdf_href}" download>Download PDF</a></li>
          <li class="down-chevron">
            <a href="{pdf_href}" target="_blank" rel="noopener" aria-label="Open PDF">
              <i class="fas fa-chevron-down"></i></a></li>
        </ul>
      </div>"""


def mockup_two_col_layout(pills_html: str, content_html: str) -> str:
    return f"""
  <div class="tabs-container-mockup">
    <div class="container">
      <div class="row g-0 tabs-row">
        <div class="col-lg-4 ferozitabs-left">
          {pills_html}
        </div>
        <div class="col-lg-8 ferozitabs-right">
          <div class="tab-content ferozi-tab-content">
            {content_html}
          </div>
        </div>
      </div>
    </div>
  </div>"""


def page_display_title(name: str, title: str) -> str:
    if name in GIST_PAGES and name != GIST_SECTION:
        labels = {"tareeqat.html": "Tareeqat", "shariat.html": "Shariat", "maarifat.html": "Maarifat", "haqeeqat.html": "Haqeeqat"}
        return labels.get(name, name.replace(".html", "").title())
    if name == "calendar.html":
        return "Ferozi Calendar"
    if len(title) > 72:
        parts = [p.strip() for p in re.split(r"\s[-–|]\s", title) if p.strip()]
        if parts:
            return parts[-1]
    return title


def page_shell(
    title: str,
    active: str,
    body: str,
    lang: str = "en",
    *,
    page_class: str = "",
    hero_html: str = "",
    short_title: bool = False,
    full_width: bool = False,
    section_sidebar: str = "",
    sidebar_active: str = "",
    article_mode: bool = False,
    mockup_layout: bool = False,
) -> str:
    direction = 'dir="rtl"' if lang == "ur" else ""
    ur_font = "urdu-content" if lang == "ur" else ""
    display_title = page_display_title(sidebar_active or "", title) if short_title else title
    if not short_title:
        display_title = title
    elif len(display_title) > 80:
        display_title = page_display_title(sidebar_active or "", title)
    banner_block = ""
    if not hero_html and not article_mode:
        banner_block = f"""
        <div class="page-banner">
          <img src="images/banner.png" alt="" class="banner-bg" aria-hidden="true">
          <div class="banner-overlay">
            <h1 class="page-title">{display_title}</h1>
          </div>
        </div>
        <img src="images/biographies-border.png" alt="" class="section-ornament" aria-hidden="true">"""
    if article_mode:
        page_class = f"{page_class} page-article".strip()
    if mockup_layout:
        main_layout = f"""
  {hero_html}
  <div class="site-body site-body-page site-body-mockup">
    <main class="main-col-full mockup-inner-main">
      {body}
    </main>
  </div>"""
    elif full_width or not section_sidebar:
        main_layout = f"""
  {hero_html}
  <div class="site-body site-body-page">
    <main class="main-col-full">
      {banner_block}
      <div class="content-wrap content-wrap-page {ur_font}">
        {body}
      </div>
    </main>
  </div>"""
    else:
        main_layout = f"""
  {hero_html}
  <div class="site-body site-body-page">
    <div class="row g-0 layout-row layout-with-sidebar">
      <aside class="col-lg-3 col-xl-3 section-sidebar-col order-lg-1">
        {section_sidebar}
      </aside>
      <main class="col-lg-9 col-xl-9 main-col order-lg-2">
        {banner_block}
        <div class="content-wrap content-wrap-page {ur_font}">
          {body}
        </div>
      </main>
    </div>
  </div>"""
    return f"""<!DOCTYPE html>
<html lang="{lang}" {direction}>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>{title} | Ferozi.org</title>
  <meta name="description" content="Jamat-e-Qasmia Ferozia Ahl-e-Sunnat Pakistan (Trust) — spirituality, Sufism, and sacred tradition. {display_title}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Lato:wght@300;400;600;700&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css" rel="stylesheet">
  <link href="css/site.css" rel="stylesheet">
</head>
<body class="ferozi-site {page_class}">
  <header class="site-header sticky-top">
    <nav class="navbar navbar-expand-lg navbar-dark main-nav">
      <div class="container-xl nav-inner">
        <a class="navbar-brand brand-mark" href="index.html">
          <img src="images/logo.png" alt="Hazrat Pir Sayyed Feroz Shah Qasimi — Qadri, Naqshbandi, Tirmizi, Buneri" class="brand-logo" width="170" height="147">
        </a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav"
                aria-controls="mainNav" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="mainNav">
          <ul class="navbar-nav ms-lg-auto align-items-lg-center">
            {nav_html(active)}
          </ul>
        </div>
      </div>
    </nav>
  </header>

  {main_layout}

  <footer class="site-footer">
    <div class="container py-4">
      <p class="mb-2 opacity-75">Operated by Computer Division Jamat-e-Qasmia Ferozia Ahl-e-Sunnat Pakistan (Trust)</p>
      <p class="mb-0 small opacity-75">Copyright &copy; 2001-2026 Ferozi.org. All Rights reserved.</p>
    </div>
  </footer>
  <div class="footer-gold-bar">Peace · Spirituality · Sacred Tradition</div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script src="js/site.js"></script>
</body>
</html>"""


def build_publications_page() -> str:
    items = publication_tab_items()
    panes = []
    for i, item in enumerate(items):
        active = " show active" if i == 0 else ""
        panes.append(
            f'<div class="tab-pane fade{active}" id="{item["tab_id"]}" role="tabpanel" '
            f'aria-labelledby="{item["tab_id"]}-tab">'
            f'{publication_tab_pane_html(item["book"])}</div>'
        )
    pills = ferozi_pills_tab_html(items, items[0]["tab_id"])
    banner = mockup_page_banner("Our Publications")
    body = banner + mockup_two_col_layout(pills, "".join(panes))
    return page_shell(
        "Our Publications",
        "our_publication.html",
        body,
        mockup_layout=True,
        page_class="page-mockup-inner page-publications",
    )


def build_biographies_page() -> str:
    panes = []
    for i, bio in enumerate(BIOGRAPHY_TABS):
        source_path = SOURCE / bio["file"]
        if not source_path.exists():
            continue
        _, content = extract_body_content(source_path, page_name=bio["file"])
        active = " show active" if i == 0 else ""
        panes.append(
            f'<div class="tab-pane fade{active}" id="{bio["tab_id"]}" role="tabpanel" '
            f'aria-labelledby="{bio["tab_id"]}-tab">'
            f'<div class="legacy-content mockup-content-pane">{content}</div></div>'
        )
    pills = ferozi_pills_tab_html(BIOGRAPHY_TABS, BIOGRAPHY_TABS[0]["tab_id"])
    banner = mockup_page_banner("Sacred Biographies")
    body = banner + mockup_two_col_layout(pills, "".join(panes))
    return page_shell(
        "Sacred Biographies",
        "blessed_personalities.html",
        body,
        mockup_layout=True,
        page_class="page-mockup-inner page-biographies",
    )


def build_book_page(book: dict) -> str:
    pdf_href = f"assets/pdfs/{book['pdf']}"
    cover = ""
    cover_path = SOURCE / "flibbok4" / "pages" / "book2" / "yadebaiza.jpg"
    if book["slug"] == "yadebaiza-english" and cover_path.exists():
        shutil.copy2(cover_path, SITE / "images" / "covers" / "yadebaiza-english.jpg")
        cover = "images/covers/yadebaiza-english.jpg"
    elif book.get("flipbook"):
        xml_pages = SOURCE / book["flipbook"] / "xml" / "Pages.xml"
        if xml_pages.exists():
            first = BeautifulSoup(xml_pages.read_text(encoding="utf-8", errors="replace"), "xml").find("page")
            if first and first.get("src"):
                src = SOURCE / book["flipbook"] / first["src"]
                if src.exists():
                    dest = SITE / "images" / "covers" / f"{book['slug']}.jpg"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                    cover = f"images/covers/{book['slug']}.jpg"
    cover_html = f'<img src="{cover}" alt="{book["title"]} cover" class="book-cover img-fluid">' if cover else ""
    pdf_href = f"assets/pdfs/{book['pdf']}"
    reader_body = f"""
      <div class="requires-chains publication-pane book-reader-pane">
        <div class="row g-4 align-items-start">
          <div class="col-md-4 col-lg-3 text-center">{cover_html}</div>
          <div class="col-md-8 col-lg-9">
            <h4>{book['title']}</h4>
            <p>This publication is provided as a PDF for reading on any device — no Flash required.</p>
            <ul class="list-group connection-often">
              <li><i class="fas fa-chevron-right"></i>
                <a href="{pdf_href}" target="_blank" rel="noopener">Open PDF</a></li>
              <li><i class="fas fa-chevron-right"></i>
                <a href="{pdf_href}" download>Download PDF</a></li>
              <li><i class="fas fa-chevron-right"></i>
                <a href="our_publication.html">&larr; All Publications</a></li>
              <li class="down-chevron">
                <a href="{pdf_href}" target="_blank" rel="noopener" aria-label="Open PDF">
                  <i class="fas fa-chevron-down"></i></a></li>
            </ul>
            <div class="pdf-embed d-none d-md-block mt-4">
              <object data="{pdf_href}" type="application/pdf" class="pdf-object">
                <p>PDF preview not supported. <a href="{pdf_href}">Download the PDF</a>.</p>
              </object>
            </div>
          </div>
        </div>
      </div>"""
    pills = publication_pills_link_html(book["source_html"])
    banner = mockup_page_banner("Our Publications")
    body = banner + mockup_two_col_layout(pills, reader_body)
    return page_shell(
        book["title"],
        "our_publication.html",
        body,
        lang=book["lang"],
        mockup_layout=True,
        page_class="page-mockup-inner page-publications",
    )


VIMEO_FEATURED = """
<section class="home-featured-video">
  <h2 class="section-heading text-center">Recent Programs</h2>
  <p class="section-sub text-center">Sacred gatherings and Urs Shareef programs</p>
  <div class="vimeo-featured">
    <div class="vimeo-responsive">
      <iframe src="https://vimeo.com/album/5664265/embed" allowfullscreen
              frameborder="0" title="Ferozi.org Recent Programs" loading="lazy"></iframe>
    </div>
  </div>
</section>"""

MOCKUP_HOME_URDU_H5 = "،ان کی شاندار عظمت حضرت پیر سید فیروز شاہ قاسمی (دامت باراکتوموم اللہہ"
MOCKUP_HOME_URDU_P = (
    "اس دور کے سب سے زیادہ مقدس، مذہبی، مذہبی اور روحانی طور پر متعارف کرانے کی ضرورت "
    "نہیں ہے جنہوں نے عقیدت سنتوں کے جانشین کے طور پر متعارف کرایا ہے، جو ان کی جانوں "
    "کے ہر لمحے اللہ تعالی کے احترام میں کھوئے ہوئے ہیں محبوب نبی صلی اللہ علیہ وسلم "
    "ہزارت محمد (سلف اللہ و الحی علی الہیہ). دریافت، صوفیانہ اور پیدائش رسول اللہ (ص) "
    "و علیا-تھاممام) درگاہ الاسلام قاسمیہ فیروزز میں سپاہی اور فضلات کے ساتھ عائد کیا "
    "جا رہا ہے."
)


def build_home() -> str:
    slides = ["images/ferozi1.png", "images/banner1.png", "images/banner2.png"]
    slide_html = []
    for i, img in enumerate(slides):
        fname = img.split("/")[-1]
        if not (SITE / "images" / fname).exists() and (MOCKUP / "images" / fname).exists():
            pass
        elif not (SITE / "images" / fname).exists():
            img = "images/ferozi1.png"
        active = " active" if i == 0 else ""
        slide_html.append(
            f"""
        <div class="carousel-item{active}">
          <div class="img-testimonials">
            <div class="testimonial description-div row g-0 align-items-start">
              <div class="col-lg-6 banner-img">
                <img src="{img}" alt="Hazrat Pir Sayyed Feroz Shah Qasimi">
              </div>
              <div class="col-lg-6 banner-text">
                <h5>{MOCKUP_HOME_URDU_H5}</h5>
                <p>{MOCKUP_HOME_URDU_P}</p>
              </div>
            </div>
          </div>
        </div>"""
        )

    hero_html = f"""
  <div class="container-fluid mockup-banner banner">
    <div class="row">
      <div class="container">
        <div id="homeHeroCarousel" class="carousel slide mockup-hero-carousel" data-bs-ride="carousel" data-bs-interval="8000">
          <div class="carousel-inner">
            {''.join(slide_html)}
          </div>
          <div class="controls-top">
            <button type="button" data-bs-target="#homeHeroCarousel" data-bs-slide="prev" aria-label="Previous">
              <i class="fas fa-chevron-left"></i>
            </button>
            <button type="button" data-bs-target="#homeHeroCarousel" data-bs-slide="next" aria-label="Next">
              <i class="fas fa-chevron-right"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>"""

    body = f"""
    <div class="container-fluid publication-biography">
      <div class="top-border">
        <img class="publication-topborder" src="images/publication-border.png" alt="" aria-hidden="true">
      </div>
      <div class="row g-0 our-publication">
        <div class="col-md-6 publication-operated">
          <div class="padding-operates padding-left">
            <h4>OUR</h4>
            <h2>PUBLICATIONS</h2>
            <p>Operated by Computer Division Jamat-e-Qasmia Ferozia Ahl-e-Sunnat Pakistan (Trust)</p>
            <ul class="mockup-browse-list">
              <li><a href="our_publication.html">BROWSE MORE<i class="fas fa-chevron-right"></i></a></li>
            </ul>
          </div>
        </div>
        <div class="col-md-6 biography-operated">
          <div class="padding-operates padding-right">
            <h4>SACRED</h4>
            <h2>BIOGRAPHY</h2>
            <p>Operated by Computer Division Jamat-e-Qasmia Ferozia Ahl-e-Sunnat Pakistan (Trust)</p>
            <ul class="mockup-browse-list">
              <li><a href="blessed_personalities.html">BROWSE MORE<i class="fas fa-chevron-right"></i></a></li>
            </ul>
          </div>
        </div>
      </div>
      <div class="bottom-border">
        <img class="publication-bottomborder" src="images/publication-border.png" alt="" aria-hidden="true">
      </div>
    </div>

    <div class="container-fluid event-program">
      <div class="container">
        <div class="row">
          <div class="col-12 event-video">
            <div id="homeEventCarousel" class="carousel slide event-gallery-control" data-bs-ride="false">
              <div class="carousel-inner">
                <div class="carousel-item active">
                  <div class="event-content text-center">
                    <h2>Events &amp; Programs</h2>
                    <p>Sacred gatherings and Urs Shareef programs</p>
                    <div class="event-embed">
                      <iframe src="https://vimeo.com/album/5664265/embed" allowfullscreen
                              title="Ferozi.org Programs" loading="lazy"></iframe>
                    </div>
                  </div>
                </div>
              </div>
              <div class="row prev-next g-0">
                <div class="col-md-6 prev-event">
                  <div class="row g-0 align-items-center">
                    <div class="col-auto fda-left">
                      <button type="button" data-bs-target="#homeEventCarousel" data-bs-slide="prev" aria-label="Previous program">
                        <i class="fas fa-chevron-left"></i>
                      </button>
                    </div>
                    <div class="col fda-right">
                      <h4>PREVIOUS PROGRAM</h4>
                      <span>Urs Shareef</span>
                    </div>
                  </div>
                </div>
                <div class="col-md-6 next-event">
                  <div class="row g-0 align-items-center justify-content-end">
                    <div class="col fdb-right text-md-end">
                      <h4>URS SHAREEF</h4>
                      <span>Recent</span>
                    </div>
                    <div class="col-auto fdb-left">
                      <button type="button" data-bs-target="#homeEventCarousel" data-bs-slide="next" aria-label="Next program">
                        <i class="fas fa-chevron-right"></i>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="browse-event text-center">
                <a class="btn btn-browse-events" href="https://vimeo.com/album/5664265" target="_blank" rel="noopener">BROWSE ALL EVENTS</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>"""

    return page_shell(
        "Welcome — Jamat-e-Qasmia Ferozia Ahl-e-Sunnat Pakistan (Trust)",
        "index.html",
        body,
        page_class="page-home page-home-mockup",
        hero_html=hero_html,
        short_title=True,
        full_width=True,
    )


def prepare_logo() -> None:
    """Copy project logo and knock out white background for the dark header."""
    src = ROOT / "logo.png"
    dest = SITE / "images" / "logo.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return
    try:
        from PIL import Image
    except ImportError:
        shutil.copy2(src, dest)
        return

    im = Image.open(src).convert("RGBA")
    pixels = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r >= 238 and g >= 238 and b >= 238:
                pixels[x, y] = (r, g, b, 0)
            elif r >= 220 and g >= 215 and b >= 205 and abs(r - g) < 20:
                # soften light cream fringe pixels
                pixels[x, y] = (r, g, b, min(a, 180))
    im.save(dest, "PNG", optimize=True)


def copy_assets() -> None:
    mockup_img = MOCKUP / "images"
    (SITE / "images").mkdir(parents=True, exist_ok=True)
    prepare_logo()
    if mockup_img.exists():
        for name in [
            "banner.png", "banner1.png", "banner2.png", "banner3.png",
            "ferozi1.png", "ferozi2.png", "ferozi3.png",
            "biographies-border.png", "publication-border.png",
            "arrow.png", "arrow-bg.png", "gray-bg.png",
        ]:
            f = mockup_img / name
            if f.exists():
                shutil.copy2(f, SITE / "images" / name)
    for folder in ["css", "js", "include", "banner", "majestic_gallery", "islamic_pic_gallery", "audio", "sound", "uploads"]:
        src = SOURCE / folder
        if src.exists():
            dest = SITE / folder
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
    src_images = SOURCE / "images"
    if src_images.exists():
        for f in src_images.rglob("*"):
            if f.is_file():
                rel = f.relative_to(src_images)
                dest = SITE / "images" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists() or dest.stat().st_size < f.stat().st_size:
                    shutil.copy2(f, dest)
    covers = SITE / "images" / "covers"
    covers.mkdir(parents=True, exist_ok=True)
    booklet = SOURCE / "Book001-Intro.pdf"
    if booklet.exists():
        shutil.copy2(booklet, SITE / "assets" / "pdfs" / "dawat-e-taqwa-booklet.pdf")


def write_css_js() -> None:
    (SITE / "css" / "site.css").write_text(
        (Path(__file__).parent / "site.css").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (SITE / "js" / "site.js").write_text(
        (Path(__file__).parent / "site.js").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def build_inner_page(name: str) -> str:
    source_path = resolve_source_path(name)
    if not source_path.exists():
        return ""
    title, content = extract_body_content(source_path, page_name=name)
    section_key = section_for_page(name)
    article = is_article_page(name, source_path)
    active = name
    for item in NAV:
        if item["href"] == name:
            active = name
        for child in item.get("children", []):
            if child["href"] == name:
                active = item["href"]
    display_title = page_display_title(name, title)
    banner = mockup_page_banner(display_title)
    article_cls = " article-content" if article else ""
    content_wrap = f'<div class="legacy-content{article_cls} mockup-content-pane">{content}</div>'
    if section_key == BIO_SECTION and name != BIO_SECTION:
        pills = bio_section_pills_link_html(name)
        body = banner + mockup_two_col_layout(pills, content_wrap)
    elif section_key:
        pills = ferozi_pills_link_html(section_key, name)
        body = banner + mockup_two_col_layout(pills, content_wrap)
    else:
        body = (
            banner
            + '<div class="mockup-content-single"><div class="container">'
            + content_wrap
            + "</div></div>"
        )
    return page_shell(
        title,
        active,
        body,
        short_title=True,
        mockup_layout=True,
        page_class="page-mockup-inner",
    )


def main() -> int:
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "assets" / "pdfs").mkdir(parents=True, exist_ok=True)
    copy_assets()
    write_css_js()

    html_files = sorted(SOURCE.glob("*.html"))
    if not html_files:
        print("No HTML in source/. Run mirror.py first.")
        return 1

    print(f"Building {len(html_files)} pages...")
    SITE.joinpath("index.html").write_text(build_home(), encoding="utf-8")
    SITE.joinpath("our_publication.html").write_text(build_publications_page(), encoding="utf-8")
    SITE.joinpath("blessed_personalities.html").write_text(build_biographies_page(), encoding="utf-8")

    for book in BOOKS:
        out = SITE / book["source_html"]
        out.write_text(build_book_page(book), encoding="utf-8")

    skip = {"index.html", "our_publication.html", "blessed_personalities.html"} | {
        b["source_html"] for b in BOOKS
    } | EXCLUDED_PAGES
    built: dict[str, str] = {}
    for html_path in html_files:
        name = html_path.name
        if name in skip or name.startswith("_"):
            continue
        page = build_inner_page(name)
        if page:
            built[name] = page

    for name, page in built.items():
        for out_name in output_names_for(name):
            (SITE / out_name).write_text(page, encoding="utf-8")

    if "iml4.html" in built and "ilm4.html" not in built:
        (SITE / "ilm4.html").write_text(build_inner_page("ilm4.html"), encoding="utf-8")

    removed = 0
    for name in EXCLUDED_PAGES:
        path = SITE / name
        if path.exists():
            path.unlink()
            removed += 1

    print(f"Site written to {SITE} ({removed} excluded pages removed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
