"""Download essential site images from FTP."""
import ftplib
from pathlib import Path

from config import FTP_HOST, FTP_PASS, FTP_ROOT, FTP_USER, SOURCE, MOCKUP

CRITICAL = [
    "ursdec2021.jpg",
    "header.jpg",
    "header2.jpg",
    "header3.jpg",
    "header4.jpg",
    "header5.jpg",
    "header8.jpg",
    "ferozi_session.jpg",
    "urs.jpg",
    "emr2012.jpg",
    "Ttlyadebeza.JPG",
    "logo.jpg",
    "banner.jpg",
]

GALLERY_PATHS = [
    "New Folder/New Folder/PICT0911.jpg",
    "New Folder/New Folder/PICT1109.jpg",
    "New Folder/New Folder/PICT1111.jpg",
    "New Folder/New Folder/Ttlyadebeza.JPG",
]


def main() -> None:
    dest = SOURCE / "images"
    dest.mkdir(parents=True, exist_ok=True)
    mockup = MOCKUP / "images"
    site_images = Path(__file__).resolve().parents[1] / "site" / "images"
    site_images.mkdir(parents=True, exist_ok=True)
    if mockup.exists():
        for name in ["logo.png", "banner.png", "biographies-border.png", "publication-border.png", "arrow.png", "gray-bg.png", "ferozi1.png"]:
            f = mockup / name
            if f.exists():
                import shutil
                shutil.copy2(f, site_images / name)
    ftp = ftplib.FTP(FTP_HOST, timeout=120)
    ftp.login(FTP_USER, FTP_PASS)
    for name in CRITICAL:
        remote = f"{FTP_ROOT}/images/{name}"
        local = dest / name
        try:
            with open(local, "wb") as fh:
                print(f"get {name}")
                ftp.retrbinary(f"RETR {remote}", fh.write)
        except ftplib.error_perm as exc:
            print(f"skip {name}: {exc}")
    for rel in GALLERY_PATHS:
        remote = f"{FTP_ROOT}/images/{rel}"
        local = dest / rel
        local.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(local, "wb") as fh:
                print(f"get {rel}")
                ftp.retrbinary(f"RETR {remote}", fh.write)
        except ftplib.error_perm as exc:
            print(f"skip {rel}: {exc}")
    ftp.quit()
    import shutil
    if dest.exists():
        for f in dest.rglob("*"):
            if f.is_file():
                rel = f.relative_to(dest)
                out = site_images / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, out)


if __name__ == "__main__":
    main()
