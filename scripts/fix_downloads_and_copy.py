"""Fix copyright, home video, rebuild heavy PDF, repair publications downloads."""
from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

from config import ROOT, SOURCE
from make_pdfs import page_paths

WEB = ROOT / "web"
PDF_DIR = WEB / "assets" / "pdfs"

COPYRIGHT = (
    "&copy; Jamat e Qasmia Ferozia Ahle Sunnat Pakistan (Trust). All rights reserved."
)

BOOKS = [
    {
        "id": "yadebaiza-urdu",
        "lang": "Urdu",
        "title": "Yaad e Baiza",
        "subtitle": "(Luminous Hand, as the Miracles of Moses) (PBUH)",
        "pdf": "yad-e-baiza-urdu.pdf",
    },
    {
        "id": "yadebaiza-en",
        "lang": "English",
        "title": "Yaad e Baiza",
        "subtitle": "(Luminous Hand, as the Miracles of Moses) (PBUH)",
        "pdf": "yad-e-baiza-english.pdf",
    },
    {
        "id": "almureed",
        "lang": "English",
        "title": "Al Muridu La Yurid",
        "subtitle": "The Disciple Does Not Seek",
        "pdf": "al-muridu-la-yurid.pdf",
    },
    {
        "id": "ten-beliefs",
        "lang": "Urdu",
        "title": "10 Basic Beliefs",
        "subtitle": "Fundamental Islamic Beliefs",
        "pdf": "10-basic-beliefs-urdu.pdf",
    },
    {
        "id": "dawat",
        "lang": "Urdu",
        "title": "Dawat-e-Taqwa Booklet",
        "subtitle": "Urdu introduction booklet (Book001-Intro)",
        "pdf": "dawat-e-taqwa-booklet.pdf",
    },
    {
        "id": "reflection",
        "lang": "English",
        "title": "Reflection",
        "subtitle": "Reflections on the spiritual path",
        "pdf": "reflection.pdf",
    },
]


def fix_copyright() -> None:
    pattern = re.compile(
        r"(?:2018-\s*)?All rights reserved\s*\|\s*Ferozi Org",
        re.I,
    )
    footer_ops = re.compile(
        r"Operated by Computer Division Jamat-e-Qasmia Ferozia Ahl-e-Sunnat Pakistan \(Trust\)",
        re.I,
    )
    for path in WEB.glob("*.html"):
        html = path.read_text(encoding="utf-8")
        new = pattern.sub(COPYRIGHT, html)
        new = footer_ops.sub(
            "Jamat e Qasmia Ferozia Ahle Sunnat Pakistan (Trust)", new
        )
        # also bare Ferozi Org copyright lines in p tags
        new = re.sub(
            r"<p>\s*All rights reserved\s*\|\s*Ferozi Org\s*</p>",
            f"<p>{COPYRIGHT}</p>",
            new,
            flags=re.I,
        )
        if new != html:
            path.write_text(new, encoding="utf-8")
            print(f"copyright: {path.name}")


def fix_home_video() -> None:
    path = WEB / "index.html"
    html = path.read_text(encoding="utf-8")
    # Replace entire events carousel block with a single video section
    single = """\
      <div class="container-fluid event-program">
         <div class="container">
            <div class="row">
               <div class="col-md-12 col-sm-12 col-xs-12 event-video">
                  <div class="col-md-12 text-center event-content">
                     <h2>Events &amp; Programs</h2>
                     <div class="home-video-wrap">
                        <iframe
                           src="https://www.facebook.com/plugins/video.php?height=314&amp;href=https%3A%2F%2Fwww.facebook.com%2Fferozi313%2Fvideos%2F676027180695372%2F&amp;show_text=false&amp;width=560&amp;t=0"
                           width="560"
                           height="314"
                           style="border:none;overflow:hidden;max-width:100%;"
                           scrolling="no"
                           frameborder="0"
                           allowfullscreen="true"
                           allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
                           title="Ferozi Events &amp; Programs"></iframe>
                     </div>
                  </div>
               </div>
            </div>
         </div>
      </div>
"""
    new, n = re.subn(
        r'<div class="container-fluid event-program">.*?</div>\s*</div>\s*</div>\s*</div>(?=\s*</div>\s*<div class="container-fluid footer-container">)',
        single.rstrip() + "\n",
        html,
        count=1,
        flags=re.S,
    )
    if n != 1:
        # Fallback: between event-program and footer-container
        new, n = re.subn(
            r'(?s)<div class="container-fluid event-program">.*?(?=<div class="container-fluid footer-container">)',
            single,
            html,
            count=1,
        )
    if n != 1:
        raise RuntimeError("Could not locate home events block")
    path.write_text(new, encoding="utf-8")
    print("home video simplified")


def rebuild_yadebaiza_urdu() -> None:
    """Compress flibbok4 pages into a downloadable PDF (not 240MB+)."""
    pages = page_paths("flibbok4")
    pages = [p for p in pages if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    if not pages:
        print("WARN: no flibbok4 pages for urdu PDF")
        return
    out = PDF_DIR / "yad-e-baiza-urdu.pdf"
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    print(f"rebuilding {out.name} from {len(pages)} pages (compressed)...")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        compressed: list[Path] = []
        for i, src in enumerate(pages, 1):
            im = Image.open(src)
            if im.mode != "RGB":
                im = im.convert("RGB")
            # Cap width to keep file portable
            max_w = 1200
            if im.width > max_w:
                ratio = max_w / float(im.width)
                im = im.resize((max_w, int(im.height * ratio)), Image.Resampling.LANCZOS)
            dest = tmp / f"{i:04d}.jpg"
            im.save(dest, "JPEG", quality=55, optimize=True)
            compressed.append(dest)
            if i % 40 == 0:
                print(f"  compressed {i}/{len(pages)}")
        import img2pdf

        out.write_bytes(img2pdf.convert([str(p) for p in compressed]))
    mb = out.stat().st_size / (1024 * 1024)
    print(f"wrote {out.name} ({mb:.1f} MB)")


def ensure_book_pdfs() -> None:
    """Copy known good source PDFs into place if missing/tiny."""
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    mapping = {
        "yad-e-baiza-english.pdf": SOURCE / "Yad-e-Baiza.pdf",
        "dawat-e-taqwa-booklet.pdf": SOURCE / "Book001-Intro.pdf",
    }
    for name, src in mapping.items():
        dest = PDF_DIR / name
        if src.exists() and (not dest.exists() or dest.stat().st_size < 1000):
            shutil.copy2(src, dest)
            print(f"copied {src.name} -> {name}")


def write_publications() -> None:
    nav_links = []
    panes = []
    for i, book in enumerate(BOOKS):
        active = "active" if i == 0 else ""
        selected = "true" if i == 0 else "false"
        bottom = " bottom-link" if i == len(BOOKS) - 1 else ""
        show = " show active" if i == 0 else ""
        pdf = book["pdf"]
        href = f"assets/pdfs/{pdf}"
        nav_links.append(
            f"""                                <a class="nav-link {active}{bottom}" id="tab-{book["id"]}" data-toggle="pill" href="#pane-{book["id"]}" role="tab" aria-controls="pane-{book["id"]}" aria-selected="{selected}">
                                    <p>{book["lang"]}</p>
                                    <h5>{book["title"]}</h5>
                                </a>"""
        )
        panes.append(
            f"""                                <div class="tab-pane fade{show}" id="pane-{book["id"]}" role="tabpanel" aria-labelledby="tab-{book["id"]}">
                                    <h4>{book["title"]}</h4>
                                    <h5>{book["subtitle"]}</h5>
                                    <p class="pdf-actions">
                                        <a class="btn btn-primary" href="{href}" target="_blank" rel="noopener">Open PDF</a>
                                        <a class="btn btn-primary" href="{href}" download="{pdf}">Download PDF</a>
                                    </p>
                                    <p>Read or download this publication as a PDF. No Flash player required.</p>
                                    <ul class="list-group connection-often">
                                        <h4>GET THE BOOK</h4>
                                        <li>
                                            <i class="fas fa-chevron-right"></i>
                                            <a href="{href}" download="{pdf}">Download {book["title"]} ({book["lang"]})</a>
                                        </li>
                                        <li>
                                            <i class="fas fa-chevron-right"></i>
                                            <a href="{href}" target="_blank" rel="noopener">Open in browser</a>
                                        </li>
                                    </ul>
                                </div>"""
        )

    html = f"""<!doctype html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="ie=edge">
        <script type="text/javascript" src="js/jquery-3.3.1.min.js"></script>
        <script type="text/javascript" src="js/bootstrap.js"></script>
        <link rel="stylesheet" href="css/font-awsome/css/fontawesome-all.min.css">
        <link rel="stylesheet" href="css/bootstrap.css">
        <link rel="stylesheet" href="css/style.css">
        <link rel="stylesheet" href="css/owl.carousel.min.css">
        <script src="js/owl.carousel.js"></script>
        <title>Our Publications | Ferozi.org</title>
    </head>
    <body>
    <nav class="navbar navbar-expand-lg navbar-light main-header" id="mainNav">
         <div class="container">
            <a class="navbar-brand hidden-md-down" href="index.html"><img src="images/logo.png" alt="ferozi"></a>
            <button class="navbar-toggler navbar-toggler-right" type="button" data-toggle="collapse"
               data-target="#navbarResponsive" aria-controls="navbarResponsive" aria-expanded="false"
               aria-label="Toggle navigation">
            <i class="fa fa-bars"></i>
            </button>
            <div class="collapse navbar-collapse" id="navbarResponsive">
               <ul class="navbar-nav ml-auto">
                  <li class="nav-item">
                     <a class="nav-link" href="index.html">ALI ISLAMIC UNIVERSITY</a>
                  </li>
                  <li class="nav-item">
                     <a class="nav-link" href="biographies.html">BIOGRAPHIES</a>
                  </li>
                  <li class="nav-item">
                     <a class="nav-link active" href="publications.html">PUBLICATIONS</a>
                  </li>
               </ul>
            </div>
         </div>
      </nav>
        <div class="container-fluid briographies-banner">
            <div class="container">
                <div class="row">
                    <div class="col-md-12 secred-biographies">
                        <h1>OUR PUBLICATIONS</h1>
                    </div>
                </div>
            </div>
            <div class="top-border">
                <img class="biographies-border" src="images/biographies-border.png" alt="">
            </div>
        </div>

        <div class="container-fluid tabs-container">
            <div class="container">
                <div class="row">
                    <div class="col-md-12 col-sm-12">
                        <div class="col-md-4 col-sm-12 ferozitabs-left">
                            <div class="nav flex-column nav-pills" id="v-pills-tab" role="tablist" aria-orientation="vertical">
{chr(10).join(nav_links)}
                            </div>
                            <div class="gray-bg"></div>
                        </div>
                        <div class="col-md-8 col-sm-12 ferozitabs-right requires-chains publication-div">
                            <div class="tab-content" id="v-pills-tabContent">
{chr(10).join(panes)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      <div class="container-fluid footer-container">
         <div class="container">
            <div class="row">
               <div class="col-md-12 text-center" style="padding:2em 0;color:#d7a53b;">
                  <p style="margin:0;color:#fff;">Jamat e Qasmia Ferozia Ahle Sunnat Pakistan (Trust)</p>
               </div>
            </div>
         </div>
      </div>
      <div class="container-fluid right-reserved">
         <div class="container">
            <div class="row">
               <div class="col-md-12 text-center ferozi-rights">
                  <p>{COPYRIGHT}</p>
               </div>
            </div>
         </div>
      </div>
   </body>
</html>
"""
    (WEB / "publications.html").write_text(html, encoding="utf-8")
    print("publications.html rewritten with working downloads")


def fix_lineage_downloads() -> None:
    for name in (
        "silsilatayyabaqadri.html",
        "silsilatayyabanaqshbandia.html",
        "shajra.html",
    ):
        path = WEB / name
        if not path.exists():
            continue
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        for a in soup.select("a[download]"):
            href = a.get("href", "")
            fname = Path(href).name
            if fname:
                a["download"] = fname
        path.write_text(str(soup), encoding="utf-8")
    print("lineage download attrs fixed")


def add_home_video_css() -> None:
    css = WEB / "css" / "style.css"
    text = css.read_text(encoding="utf-8")
    marker = "/* home single video */"
    if marker in text:
        return
    css.write_text(
        text
        + f"""

{marker}
.home-video-wrap {{
  max-width: 780px;
  margin: 1.5em auto 0;
}}
.home-video-wrap iframe {{
  width: 100%;
  max-width: 560px;
  height: 315px;
}}
""",
        encoding="utf-8",
    )


def main() -> int:
    ensure_book_pdfs()
    rebuild_yadebaiza_urdu()
    fix_copyright()
    fix_home_video()
    add_home_video_css()
    write_publications()
    fix_lineage_downloads()
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
