"""Mirror live ferozi.org static assets from FTP into source/."""
from __future__ import annotations

import ftplib
import sys
import zipfile
from pathlib import Path

from config import FTP_HOST, FTP_PASS, FTP_ROOT, FTP_USER, MIRROR_DIRS, SKIP_DIRS, SOURCE

ROOT_HTML = SOURCE
BOOK_FLIPBOOKS = ["flibbok", "flibbok2", "flibbok3", "flibbok4"]
SKIP_PREFIXES = ("lz_", "chat_", "carrier_", "button_mail")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def download_file(ftp: ftplib.FTP, remote: str, local: Path) -> None:
    ensure_parent(local)
    with open(local, "wb") as fh:
        ftp.retrbinary(f"RETR {remote}", fh.write)


def list_dir(ftp: ftplib.FTP, remote: str) -> list[str]:
    try:
        return ftp.nlst(remote)
    except ftplib.error_perm as exc:
        print(f"  skip list {remote}: {exc}", flush=True)
        return []


def resolve_entry(remote_dir: str, entry: str) -> tuple[str, str] | tuple[None, None]:
    if entry in (".", "..") or ".." in entry:
        return None, None
    remote_dir = remote_dir.rstrip("/")
    if entry.startswith("/"):
        remote_path = entry
        name = entry.rstrip("/").split("/")[-1]
    else:
        name = entry
        remote_path = f"{remote_dir}/{name}"
    if not name or name == ".":
        return None, None
    return remote_path, name


def mirror_dir(ftp: ftplib.FTP, remote_dir: str, local_dir: Path) -> None:
    local_dir.mkdir(parents=True, exist_ok=True)
    for entry in list_dir(ftp, remote_dir):
        resolved = resolve_entry(remote_dir, entry)
        if resolved == (None, None):
            continue
        remote_path, name = resolved
        if name in SKIP_DIRS:
            continue
        if any(name.startswith(p) for p in SKIP_PREFIXES):
            continue
        local_path = local_dir / name
        try:
            size = ftp.size(remote_path)
        except ftplib.error_perm:
            mirror_dir(ftp, remote_path, local_path)
            continue
        if local_path.exists() and local_path.stat().st_size == size:
            continue
        print(f"  get {remote_path}", flush=True)
        try:
            download_file(ftp, remote_path, local_path)
        except ftplib.error_perm as exc:
            print(f"  failed {remote_path}: {exc}", flush=True)


def mirror_html_root(ftp: ftplib.FTP) -> None:
    ROOT_HTML.mkdir(parents=True, exist_ok=True)
    for entry in list_dir(ftp, FTP_ROOT):
        resolved = resolve_entry(FTP_ROOT, entry)
        if resolved == (None, None):
            continue
        remote_path, name = resolved
        if not name.lower().endswith((".html", ".pdf", ".xml", ".js", ".css")):
            continue
        local = ROOT_HTML / name
        try:
            size = ftp.size(remote_path)
        except ftplib.error_perm:
            continue
        if local.exists() and size and local.stat().st_size == size:
            continue
        print(f"  get {remote_path}", flush=True)
        download_file(ftp, remote_path, local)


def mirror_flipbooks(ftp: ftplib.FTP) -> None:
    for book in BOOK_FLIPBOOKS:
        local_xml = SOURCE / book / "xml" / "Pages.xml"
        remote_xml = f"{FTP_ROOT}/{book}/xml/Pages.xml"
        try:
            size = ftp.size(remote_xml)
        except ftplib.error_perm:
            print(f"  missing {remote_xml}", flush=True)
            size = None
        if size and (not local_xml.exists() or local_xml.stat().st_size != size):
            print(f"  get {remote_xml}", flush=True)
            download_file(ftp, remote_xml, local_xml)

        zip_remote = f"{FTP_ROOT}/{book}/pages/book2.zip"
        local_zip = SOURCE / book / "pages" / "book2.zip"
        local_pages = SOURCE / book / "pages" / "book2"
        try:
            size = ftp.size(zip_remote)
        except ftplib.error_perm:
            size = None
        if size:
            if not local_zip.exists() or local_zip.stat().st_size != size:
                print(f"  get {zip_remote}", flush=True)
                download_file(ftp, zip_remote, local_zip)
            if not local_pages.exists() or not any(local_pages.rglob("*.jpg")):
                print(f"  extracting {local_zip}", flush=True)
                extract_root = SOURCE / book / "pages"
                extract_root.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(local_zip, "r") as zf:
                    zf.extractall(extract_root)
            continue
        pages_remote = f"{FTP_ROOT}/{book}/pages/book2"
        print(f"Mirroring {book}/pages/book2...", flush=True)
        mirror_dir(ftp, pages_remote, local_pages)


def main() -> int:
    print("Connecting to FTP...", flush=True)
    ftp = ftplib.FTP(FTP_HOST, timeout=180)
    ftp.login(FTP_USER, FTP_PASS)
    print("Mirroring HTML/PDF root files...", flush=True)
    mirror_html_root(ftp)
    print("Mirroring flipbooks (priority)...", flush=True)
    mirror_flipbooks(ftp)
    for folder in MIRROR_DIRS:
        if folder.startswith("flibbok"):
            continue
        remote = f"{FTP_ROOT}/{folder}"
        local = SOURCE / Path(folder)
        print(f"Mirroring {folder}...", flush=True)
        mirror_dir(ftp, remote, local)
    ftp.quit()
    print("Mirror complete.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
