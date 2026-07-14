"""Curate Silsila/Shajra (and related FTP popup content) into mockup pages + PDFs."""
from __future__ import annotations

import re
import shutil
import textwrap
from pathlib import Path

from bs4 import BeautifulSoup

from config import ROOT, SITE, SOURCE

WEB = ROOT / "web"
PDF_DIR = WEB / "assets" / "pdfs"

NAV = """\
                  <li class="nav-item">
                     <a class="nav-link" href="index.html">ALI ISLAMIC UNIVERSITY</a>
                  </li>
                  <li class="nav-item">
                     <a class="nav-link active" href="biographies.html">BIOGRAPHIES</a>
                  </li>
                  <li class="nav-item">
                     <a class="nav-link" href="publications.html">PUBLICATIONS</a>
                  </li>"""

BIO_SIDEBAR = """\
                            <div class="nav flex-column nav-pills" role="navigation">
                                <a class="nav-link" href="biographies.html"><p>Hazrat Pir Sayyed</p><h5>Feroz Shah Qasimi</h5><span>(D.B.A.)</span></a>
                                <a class="nav-link" href="biographies.html#ali"><p>Shahzada Hazrat Sayyed</p><h5>Ali Muhammad Shah Shaheed</h5><span>(R.A.)</span></a>
                                <a class="nav-link" href="biographies.html#anwaar"><p>Shahzada Hazrat Sayyed</p><h5>Anwaar Hussain Shah</h5><span>(R.A.)</span></a>
                                <a class="nav-link" href="biographies.html#qasim"><p>Hazrat Pir Sain</p><h5>Muhammad Qasim Mashori</h5><span>(R.A.)</span></a>
                                <a class="nav-link" href="biographies.html#rashid"><p>Hazrat Pir Sain Sayyed</p><h5>Muhammad Rashid Rozay Dhani</h5><span>(R.A.)</span></a>
                                <a class="nav-link" href="biographies.html#ghawwas"><p>Hazrat Pir</p><h5>Ali Ghawwas, Pir Baba</h5><span>(R.A.)</span></a>
                                <a class="nav-link {qadri_active}" href="silsilatayyabaqadri.html"><h5>Silsila Qadiria</h5></a>
                                <a class="nav-link {naqsh_active}" href="silsilatayyabanaqshbandia.html"><h5>Silsila Naqshbandia</h5></a>
                                <a class="nav-link bottom-link {shajra_active}" href="shajra.html"><h5>Shajra-e-Tayyaba</h5></a>
                            </div>
                            <div class="gray-bg"></div>"""

LINEAGE_DOCS = [
    {
        "source": "silsilatayyabaqadri.html",
        "out": "silsilatayyabaqadri.html",
        "pdf": "silsila-qadiria.pdf",
        "banner": "Silsila Tayyaba — Qadiria",
        "title": "Silsila Tayyaba Tareeqat Qadiria Rashidia Qasimia Ferozia",
        "active": "qadri",
    },
    {
        "source": "silsilatayyabanaqshbandia.html",
        "out": "silsilatayyabanaqshbandia.html",
        "pdf": "silsila-naqshbandia.pdf",
        "banner": "Silsila Tayyaba — Naqshbandia",
        "title": "Silsila Tayyaba Tareeqat Naqshbandia Rashidia Qasimia Ferozia",
        "active": "naqsh",
    },
    {
        "source": "shajra.html",
        "out": "shajra.html",
        "pdf": "shajra-e-tayyaba.pdf",
        "banner": "Shajra-e-Tayyaba",
        "title": "Shajra-e-Tayyaba",
        "active": "shajra",
    },
]

COPYRIGHT = (
    "&copy; Jamat e Qasmia Ferozia Ahle Sunnat Pakistan (Trust). All rights reserved."
)

FOOTER = f"""\
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
"""


def clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s


def extract_content(html_path: Path) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    block = soup.select_one("#textarea_content") or soup.body
    headings: list[str] = []
    lines: list[str] = []
    for tag in block.find_all(["h6", "h5", "h4", "h3", "h2", "h1", "p"]):
        text = clean_text(tag.get_text(" ", strip=True))
        if not text:
            continue
        if tag.name.startswith("h"):
            headings.append(text)
        else:
            lines.append(text)
    return "\n".join(headings), lines


def pdf_safe(s: str) -> str:
    return (
        (s or "")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def write_pdf(path: Path, title: str, headings: str, lines: list[str]) -> None:
    from fpdf import FPDF

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 13)
    pdf.multi_cell(174, 7, pdf_safe(title))
    pdf.ln(3)
    if headings:
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(174, 6, pdf_safe(headings))
        pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    for line in lines:
        pdf.multi_cell(174, 6, pdf_safe(line))
        pdf.ln(1)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))


def page_html(doc: dict, body_inner: str) -> str:
    active = doc["active"]
    sidebar = BIO_SIDEBAR.format(
        qadri_active="active" if active == "qadri" else "",
        naqsh_active="active" if active == "naqsh" else "",
        shajra_active="active" if active == "shajra" else "",
    )
    return f"""<!doctype html>
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
        <title>{doc["title"]} | Ferozi.org</title>
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
{NAV}
               </ul>
            </div>
         </div>
      </nav>
        <div class="container-fluid briographies-banner">
            <div class="container">
                <div class="row">
                    <div class="col-md-12 secred-biographies">
                        <h1>{doc["banner"]}</h1>
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
                    <div class="col-md-12 col-sm-12 col-xs-12">
                        <div class="col-md-4 col-sm-12 col-xs-12 ferozitabs-left">
{sidebar}
                        </div>
                        <div class="col-md-8 col-sm-12 col-xs-12 ferozitabs-right">
{body_inner}
                        </div>
                    </div>
                </div>
            </div>
        </div>
{FOOTER}
   </body>
</html>
"""


def build_lineage_pages() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for doc in LINEAGE_DOCS:
        src = SOURCE / doc["source"]
        if not src.exists():
            print(f"MISSING {src}")
            continue
        headings, lines = extract_content(src)
        pdf_name = doc["pdf"]
        write_pdf(PDF_DIR / pdf_name, doc["title"], headings, lines)
        # also keep copy next to old site assets for parity
        old = SITE / "assets" / "pdfs" / pdf_name
        old.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PDF_DIR / pdf_name, old)

        articles = "\n".join(f"                                    <p>{line}</p>" for line in lines)
        heading_html = f"                                    <h5>{headings}</h5>" if headings else ""
        body = f"""\
                            <div class="lineage-article">
{heading_html}
                                    <p class="pdf-actions">
                                        <a class="btn btn-primary" href="assets/pdfs/{pdf_name}" target="_blank" rel="noopener">Open PDF</a>
                                        <a class="btn btn-primary" href="assets/pdfs/{pdf_name}" download>Download PDF</a>
                                    </p>
{articles}
                            </div>
"""
        out = WEB / doc["out"]
        out.write_text(page_html(doc, body), encoding="utf-8")
        print(f"wrote {out.name} + {pdf_name}")


def wire_biography_links() -> None:
    path = WEB / "biographies.html"
    html = path.read_text(encoding="utf-8")
    replacements = [
        (
            'href="#">Silsila Tayyaba Tareeqat Qadiria Rashidia Qasimia Ferozia</a>',
            'href="silsilatayyabaqadri.html">Silsila Tayyaba Tareeqat Qadiria Rashidia Qasimia Ferozia</a>',
        ),
        (
            'href="#">SilsilaTayyabaTareeqat Naqshbandia Rashidia Qasimia Ferozia</a>',
            'href="silsilatayyabanaqshbandia.html">Silsila Tayyaba Tareeqat Naqshbandia Rashidia Qasimia Ferozia</a>',
        ),
        (
            'href="#">Shajra-e-Tayyaba</a>',
            'href="shajra.html">Shajra-e-Tayyaba</a>',
        ),
    ]
    for old, new in replacements:
        html = html.replace(old, new)
    path.write_text(html, encoding="utf-8")
    print("wired biographies.html lineage links")


def wire_publications_pdfs() -> None:
    """Point publication book panes at curated Flash->PDF replacements."""
    path = WEB / "publications.html"
    if not path.exists():
        return
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

    book_map = [
        ("v-pills-home", "yad-e-baiza-urdu.pdf", "Yaad e Baiza (Urdu)"),
        ("v-pills-profile", "yad-e-baiza-english.pdf", "Yaad e Baiza (English)"),
        ("v-pills-messages", "al-muridu-la-yurid.pdf", "Al Muridu La Yurid"),
        ("v-pills-settings", "10-basic-beliefs-urdu.pdf", "10 Basic Beliefs"),
    ]
    # Reflection tab uses duplicate ids in mockup; fix by order
    panes = soup.select(".ferozitabs-right .tab-pane")
    pdfs = [
        ("yad-e-baiza-urdu.pdf", "Yaad e Baiza (Urdu)"),
        ("yad-e-baiza-english.pdf", "Yaad e Baiza (English)"),
        ("al-muridu-la-yurid.pdf", "Al Muridu La Yurid"),
        ("10-basic-beliefs-urdu.pdf", "10 Basic Beliefs"),
        ("dawat-e-taqwa-booklet.pdf", "Giarhween Shareef / Dawat-e-Taqwa booklet"),
        ("reflection.pdf", "Reflection"),
    ]
    for pane, (pdf, label) in zip(panes, pdfs):
        # Prefixed PDF action block once per pane
        existing = pane.select_one(".pdf-actions")
        if existing:
            existing.decompose()
        actions = soup.new_tag("p")
        actions["class"] = "pdf-actions"
        open_a = soup.new_tag("a", href=f"assets/pdfs/{pdf}", target="_blank", rel="noopener")
        open_a["class"] = "btn btn-primary"
        open_a.string = "Open PDF"
        dl_a = soup.new_tag("a", href=f"assets/pdfs/{pdf}", download=True)
        dl_a["class"] = "btn btn-primary"
        dl_a.string = "Download PDF"
        note = soup.new_tag("span")
        note["style"] = "display:block;margin-top:8px;color:#543707;"
        note.string = f"Flash flipbook replaced with curated PDF — {label}"
        actions.append(open_a)
        actions.append(soup.new_string(" "))
        actions.append(dl_a)
        actions.append(note)
        h4 = pane.find(["h4", "h5"])
        if h4:
            h4.insert_after(actions)
        else:
            pane.insert(0, actions)
        # Point all chapter links in this pane to the PDF
        for a in pane.select("ul.connection-often a"):
            a["href"] = f"assets/pdfs/{pdf}"
            a["target"] = "_blank"
            a["rel"] = "noopener"

    path.write_text(str(soup), encoding="utf-8")
    print("wired publications.html PDF actions")


def ensure_pdf_css() -> None:
    css = WEB / "css" / "style.css"
    marker = "/* curated pdf actions */"
    if marker in css.read_text(encoding="utf-8"):
        return
    css.write_text(
        css.read_text(encoding="utf-8")
        + textwrap.dedent(
            f"""

            {marker}
            .pdf-actions {{
                margin: 1em 0 1.5em;
            }}
            .pdf-actions .btn {{
                background-color: #074489;
                border-color: #074489;
                color: #fff;
                margin-right: 8px;
                margin-bottom: 8px;
            }}
            .pdf-actions .btn:hover {{
                background-color: #d7a53b;
                border-color: #d7a53b;
                color: #fff;
            }}
            .lineage-article p {{
                font-size: 15px;
                line-height: 1.7;
                color: #543707;
            }}
            """
        ),
        encoding="utf-8",
    )


def main() -> int:
    ensure_pdf_css()
    build_lineage_pages()
    wire_biography_links()
    wire_publications_pdfs()
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
