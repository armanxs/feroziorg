"""Fix banner heading, Vimeo home/gallery, and Giarhween/Dawat publication mapping."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

WEB = Path(__file__).resolve().parents[1] / "web"

BANNER_HEADING = "Jamat e Qasmia Ferozia Ahle Sunnat Pakistan (Trust)"

HOME_VIMEO_ID = "109252144"
HOME_VIMEO_TITLE = (
    "17 Oct 2014 Friday Sermon by Murshid Kareem — "
    "Saen Pir Syed Feroz Shah Qasmi"
)


def fetch_ferozi_videos() -> list[dict]:
    url = "https://vimeo.com/api/v2/ferozi1/videos.json"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    videos = []
    for v in data:
        videos.append(
            {
                "id": str(v["id"]),
                "title": v.get("title") or f"Vimeo {v['id']}",
                "upload_date": (v.get("upload_date") or "")[:10],
                "thumbnail": v.get("thumbnail_medium") or v.get("thumbnail_small") or "",
            }
        )
    return videos


def fix_banner_heading() -> None:
    path = WEB / "index.html"
    html = path.read_text(encoding="utf-8")
    new_html, n = re.subn(
        r"(<div class=\"col-lg-6 col-md-12 col-sm-12 col-xs-12 float-right banner-text\">\s*<h5>)(.*?)(</h5>)",
        rf"\1{BANNER_HEADING}\3",
        html,
        flags=re.S,
    )
    path.write_text(new_html, encoding="utf-8")
    print(f"banner headings updated: {n}")


def fix_home_vimeo() -> None:
    path = WEB / "index.html"
    html = path.read_text(encoding="utf-8")
    embed = f"""<div class="container-fluid event-program">
<div class="container">
<div class="row">
<div class="col-md-12 col-sm-12 col-xs-12 event-video">
<div class="col-md-12 text-center event-content">
<h2>Events &amp; Programs</h2>
<p class="home-video-caption">{HOME_VIMEO_TITLE}</p>
<div class="home-video-wrap">
<iframe
  src="https://player.vimeo.com/video/{HOME_VIMEO_ID}?title=0&amp;byline=0&amp;portrait=0"
  width="640"
  height="360"
  frameborder="0"
  allow="autoplay; fullscreen; picture-in-picture"
  allowfullscreen
  title="{HOME_VIMEO_TITLE}"></iframe>
</div>
<p class="home-video-more"><a href="video-gallery.html">Browse more videos from Ferozi on Vimeo</a></p>
</div>
</div>
</div>
</div>
</div>
"""
    new_html, n = re.subn(
        r'(?s)<div class="container-fluid event-program">.*?(?=<div class="container-fluid footer-container">)',
        embed + "\n",
        html,
        count=1,
    )
    if n != 1:
        raise RuntimeError("home events block not found")
    path.write_text(new_html, encoding="utf-8")
    print("home video set to Vimeo", HOME_VIMEO_ID)


def rewrite_video_gallery(videos: list[dict]) -> None:
    path = WEB / "video-gallery.html"
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

    # Keep existing nav/footer; replace main content after banner
    banner = soup.select_one(".briographies-banner")
    footer = soup.select_one(".footer-container") or soup.select_one(".right-reserved")
    if not banner or not footer:
        raise RuntimeError("video-gallery structure unexpected")

    # Remove everything between banner and footer
    node = banner.next_sibling
    while node and node != footer:
        nxt = node.next_sibling
        if getattr(node, "name", None) or (isinstance(node, str) and node.strip()):
            node.extract()
        node = nxt

    figures = []
    for v in videos:
        figures.append(
            f"""
                        <figure class="col-md-4 col-sm-6 col-xs-12 vimeo-card">
                            <div class="embed-responsive embed-responsive-16by9">
                                <iframe class="embed-responsive-item"
                                    src="https://player.vimeo.com/video/{v['id']}?title=0&byline=0&portrait=0"
                                    allow="autoplay; fullscreen; picture-in-picture"
                                    allowfullscreen
                                    title="{v['title']}"></iframe>
                            </div>
                            <div class="video-text col-md-12">
                                <h3 class="my-2">{v['title']}</h3>
                                <h5>{v['upload_date']}</h5>
                                <p><a href="https://vimeo.com/{v['id']}" target="_blank" rel="noopener">Open on Vimeo</a></p>
                            </div>
                        </figure>"""
        )

    gallery_html = f"""
        <div class="container-fluid tabs-container vimeo-gallery">
            <div class="container">
                <div class="row">
                    <div class="col-md-12">
                        <p class="gallery-intro">Videos from the official Ferozi Vimeo account
                        (<a href="https://vimeo.com/ferozi1" target="_blank" rel="noopener">@ferozi1</a>.</p>
                    </div>
                    <div class="col-md-12 col-sm-12 col-xs-12 tabs-video">
                        <div class="row mdb-lightbox no-margin">
{''.join(figures)}
                        </div>
                    </div>
                </div>
            </div>
        </div>
"""
    banner.insert_after(BeautifulSoup(gallery_html, "html.parser"))

    # Update titles
    if soup.title:
        soup.title.string = "Video Gallery | Ferozi.org"
    h1 = soup.select_one(".secred-biographies h1")
    if h1:
        h1.string = "Video Gallery"
    desc = soup.head.find("meta", attrs={"name": "description"}) if soup.head else None
    if desc:
        desc["content"] = (
            "Video gallery of Friday sermons and programs by Hazrat Pir Sayyed Feroz Shah Qasimi "
            "from the official Ferozi Vimeo account."
        )

    path.write_text(str(soup), encoding="utf-8")
    print(f"video gallery rebuilt with {len(videos)} Vimeo videos")


def fix_publications_giarhween() -> None:
    """Replace mistaken Giarhween→Dawat mapping with correct Dawat-e-Taqwa booklet entry.

    Live site listed Giarhween Sharif as href='#4' with no file. Book001-Intro.pdf is
    specifically the Dawat-e-Taqwa booklet — keep that as its own publication.
    """
    path = WEB / "publications.html"
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

    # Update left nav label
    tab = soup.select_one("#tab-giarhween")
    if tab:
        tab["id"] = "tab-dawat"
        tab["href"] = "#pane-dawat"
        tab["aria-controls"] = "pane-dawat"
        p = tab.find("p")
        h5 = tab.find("h5")
        if p:
            p.string = "Urdu"
        if h5:
            h5.string = "Dawat-e-Taqwa Booklet"

    pane = soup.select_one("#pane-giarhween")
    if pane:
        pane["id"] = "pane-dawat"
        pane["aria-labelledby"] = "tab-dawat"
        h4 = pane.find("h4")
        h5 = pane.find("h5")
        if h4:
            h4.string = "Dawat-e-Taqwa Booklet"
        if h5:
            h5.string = "Urdu introduction booklet"
        for a in pane.select("a[href*='dawat-e-taqwa']"):
            # keep same PDF but fix link labels
            if a.string and "Giarhween" in a.string:
                a.string = "Download Dawat-e-Taqwa Booklet (Urdu)"
        note = pane.find("p", string=re.compile(r"Read or download", re.I))
        if note:
            note.string = (
                "This is the Dawat-e-Taqwa booklet (Book001-Intro.pdf) from the live site. "
                "Giarhween Shareef was listed on the old publications menu but had no downloadable "
                "file on the FTP archive."
            )

    path.write_text(str(soup), encoding="utf-8")
    print("publications: Giarhween replaced with Dawat-e-Taqwa Booklet")


def add_css() -> None:
    css = WEB / "css" / "style.css"
    text = css.read_text(encoding="utf-8")
    marker = "/* vimeo gallery */"
    if marker in text:
        return
    css.write_text(
        text
        + f"""

{marker}
.home-video-caption {{
  color: #543707;
  margin: 0.5em 0 1em;
}}
.home-video-more {{
  margin-top: 1em;
}}
.home-video-more a {{
  color: #074489;
  font-family: 'latobold', sans-serif;
}}
.home-video-wrap iframe {{
  width: 100%;
  max-width: 640px;
  height: 360px;
}}
.vimeo-gallery .gallery-intro {{
  margin: 1em 0 1.5em;
  color: #333;
}}
.vimeo-card {{
  margin-bottom: 2em;
}}
.vimeo-card .video-text h3 {{
  font-size: 16px;
  color: #074489;
  line-height: 1.4;
}}
.vimeo-card .video-text h5 {{
  font-size: 13px;
  color: #666;
}}
""",
        encoding="utf-8",
    )


def main() -> int:
    videos = fetch_ferozi_videos()
    fix_banner_heading()
    fix_home_vimeo()
    rewrite_video_gallery(videos)
    fix_publications_giarhween()
    add_css()
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
