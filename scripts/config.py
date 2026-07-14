from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
SITE = ROOT / "site"
MOCKUP = Path(r"D:\Projects\ferozi\ferozi html")

FTP_HOST = os.environ.get("FEROZI_FTP_HOST", "ftp.ferozi.org")
FTP_USER = os.environ.get("FEROZI_FTP_USER", "ferozi")
FTP_PASS = os.environ.get("FEROZI_FTP_PASS", "")
FTP_ROOT = os.environ.get("FEROZI_FTP_ROOT", "/public_html")

SKIP_DIRS = {
    "admin",
    "templates",
    "_config",
    "_lib",
    "_internal",
    "_include",
    "_definitions",
    "_groups",
    "_language",
    "_log",
    "cgi-bin",
    "TheAliIslamicUniversity",
    "dawat-e-taqwa.org",
    "dawatetaqwa",
    "veemi",
    "10.1",
    "Friday",
    "DeedarMubarak",
    "Succession",
    "tmp",
    "stats",
    "datafeed",
    "docs",
    ".well-known",
    "smilies",
}

SKIP_FILES_SUFFIX = {".php", ".asp", ".swf", ".map", ".docx"}

MIRROR_DIRS = [
    "flibbok/pages/book2",
    "flibbok2/pages/book2",
    "flibbok3/pages/book2",
    "flibbok4/pages/book2",
    "flibbok/xml",
    "flibbok2/xml",
    "flibbok3/xml",
    "flibbok4/xml",
    "images",
    "include",
    "css",
    "js",
    "Scripts",
    "banner",
    "majestic_gallery",
    "islamic_pic_gallery",
    "audio",
    "sound",
    "uploads",
]

BOOKS = [
    {
        "slug": "yadebaiza",
        "title": "Yad-e-Baiza (Urdu)",
        "lang": "ur",
        "source_html": "yadebaiza.html",
        "flipbook": "flibbok4",
        "pdf": "yad-e-baiza-urdu.pdf",
    },
    {
        "slug": "yadebaiza-english",
        "title": "Yad-e-Baiza (English)",
        "lang": "en",
        "source_html": "yadebaiza-english.html",
        "existing_pdf": "Yad-e-Baiza.pdf",
        "pdf": "yad-e-baiza-english.pdf",
    },
    {
        "slug": "almureedulayurdd",
        "title": "Al Muridu La Yurid (English)",
        "lang": "en",
        "source_html": "almureedulayurdd.html",
        "flipbook": "flibbok",
        "pdf": "al-muridu-la-yurid.pdf",
    },
    {
        "slug": "10basicbelief",
        "title": "10 Basic Beliefs (Urdu)",
        "lang": "ur",
        "source_html": "10basicbelief.html",
        "flipbook": "flibbok3",
        "pdf": "10-basic-beliefs-urdu.pdf",
    },
    {
        "slug": "reflection-book",
        "title": "Reflection (English)",
        "lang": "en",
        "source_html": "reflection-book.html",
        "flipbook": "flibbok2",
        "pdf": "reflection.pdf",
    },
]
