"""Mirror Flash-replacement media from FTP: audio playlists, photo galleries."""
from __future__ import annotations

import ftplib
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from config import FTP_HOST, FTP_PASS, FTP_ROOT, FTP_USER, SOURCE

SKIP_EXT = {".swf", ".as", ".db", ".php", ".map", ".docx"}
KEEP_EXT = {".xml", ".mp3", ".wav", ".m4a", ".jpg", ".jpeg", ".png", ".gif", ".html", ".js", ".css"}
SKIP_NAMES = {"thumbs.db"}
FTP_TIMEOUT = 600
MAX_RETRIES = 3

PRIORITY_DIRS = ["audio", "islamic_pic_gallery", "majestic_gallery"]


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def connect_ftp() -> ftplib.FTP:
    ftp = ftplib.FTP(FTP_HOST, timeout=FTP_TIMEOUT)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.set_pasv(True)
    return ftp


def download_file(ftp: ftplib.FTP, remote: str, local: Path) -> bool:
    try:
        size = ftp.size(remote)
    except ftplib.error_perm:
        return False
    if local.exists() and size and local.stat().st_size == size:
        return False
    ensure_parent(local)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  get {remote}", flush=True)
            with open(local, "wb") as fh:
                ftp.retrbinary(f"RETR {remote}", fh.write)
            if size and local.stat().st_size != size:
                print(f"  warn size mismatch {remote}", flush=True)
            return True
        except (TimeoutError, OSError, ftplib.error_temp) as exc:
            print(f"  retry {attempt}/{MAX_RETRIES} {remote}: {exc}", flush=True)
            if local.exists():
                local.unlink(missing_ok=True)
            if attempt == MAX_RETRIES:
                return False
            time.sleep(2 * attempt)
    return False


def discover_flash_bases() -> set[str]:
    bases: set[str] = set()
    for html_path in SOURCE.glob("*.html"):
        raw = html_path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(
            r"AC_FL_RunContent\s*\([^)]*'(?:movie|src)'\s*,\s*'([^']+)'",
            raw,
            re.I | re.S,
        ):
            bases.add(m.group(1).replace(".swf", "").strip())
        for m in re.finditer(r'(?:src|value)=["\']([^"\']+\.swf)["\']', raw, re.I):
            bases.add(m.group(1).replace(".swf", "").strip())
    return bases


def xml_candidates_for_base(base: str) -> list[Path]:
    base = base.replace(".swf", "")
    name = Path(base).name
    parent = Path(base).parent
    cands = [SOURCE / f"{base}.xml", SOURCE / parent / f"{name}.xml"]
    out: list[Path] = []
    seen: set[Path] = set()
    for p in cands:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def sync_audio_for_base(ftp: ftplib.FTP, base: str) -> int:
    if not base.startswith("audio/"):
        return 0
    count = 0
    base = base.replace(".swf", "")
    for xml_local in xml_candidates_for_base(base):
        remote_xml = f"{FTP_ROOT}/{xml_local.relative_to(SOURCE).as_posix()}"
        if download_file(ftp, remote_xml, xml_local):
            count += 1
        if not xml_local.exists():
            continue
        try:
            root = ET.parse(xml_local).getroot()
        except ET.ParseError:
            continue
        for track in root.findall(".//track"):
            file_path = (track.findtext("file") or "").strip().lstrip("/")
            if not file_path:
                continue
            local_mp3 = SOURCE / file_path.replace("/", "\\")
            remote_mp3 = f"{FTP_ROOT}/{file_path}"
            if download_file(ftp, remote_mp3, local_mp3):
                count += 1
    folder = SOURCE / base
    remote_folder = f"{FTP_ROOT}/{base}"
    try:
        entries = ftp.nlst(remote_folder)
    except ftplib.error_perm:
        return count
    for entry in entries:
        name = entry.rstrip("/").split("/")[-1]
        if Path(name).suffix.lower() not in {".mp3", ".wav", ".m4a", ".xml"}:
            continue
        local = folder / name
        remote = f"{remote_folder}/{name}"
        if download_file(ftp, remote, local):
            count += 1
    return count


def sync_gallery(ftp: ftplib.FTP) -> int:
    count = 0
    xml_local = SOURCE / "islamic_pic_gallery" / "gallery.xml"
    remote_xml = f"{FTP_ROOT}/islamic_pic_gallery/gallery.xml"
    if download_file(ftp, remote_xml, xml_local):
        count += 1
    if not xml_local.exists():
        return count
    try:
        root = ET.parse(xml_local).getroot()
    except ET.ParseError:
        return count
    for image in root.findall(".//image"):
        fname = (image.findtext("img") or image.findtext("thumb") or "").strip()
        if not fname or fname.lower() in SKIP_NAMES:
            continue
        local = SOURCE / "islamic_pic_gallery" / "images" / fname
        remote = f"{FTP_ROOT}/islamic_pic_gallery/images/{fname}"
        if download_file(ftp, remote, local):
            count += 1
    return count


def sync_majestic_gallery(ftp: ftplib.FTP) -> int:
    count = 0
    remote_root = f"{FTP_ROOT}/majestic_gallery"

    def walk(remote_dir: str, local_dir: Path) -> None:
        nonlocal count
        try:
            entries = ftp.nlst(remote_dir)
        except ftplib.error_perm:
            return
        for entry in entries:
            name = entry.rstrip("/").split("/")[-1]
            if name in (".", "..") or name == "thumbs":
                continue
            remote_path = entry if entry.startswith("/") else f"{remote_dir.rstrip('/')}/{name}"
            local_path = local_dir / name
            try:
                size = ftp.size(remote_path)
            except ftplib.error_perm:
                walk(remote_path, local_path)
                continue
            if Path(name).suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            if download_file(ftp, remote_path, local_path):
                count += 1

    walk(remote_root, SOURCE / "majestic_gallery")
    return count


def should_download(name: str) -> bool:
    lower = name.lower()
    if lower in SKIP_NAMES:
        return False
    ext = Path(name).suffix.lower()
    if ext in SKIP_EXT:
        return False
    return ext in KEEP_EXT or not ext


def mirror_tree(ftp: ftplib.FTP, remote_dir: str, local_dir: Path) -> int:
    local_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    try:
        entries = ftp.nlst(remote_dir)
    except ftplib.error_perm as exc:
        print(f"  skip {remote_dir}: {exc}", flush=True)
        return 0
    for entry in entries:
        if entry in (".", "..") or ".." in entry:
            continue
        name = entry.rstrip("/").split("/")[-1]
        remote_path = entry if entry.startswith("/") else f"{remote_dir.rstrip('/')}/{name}"
        if name.startswith(".") or name == "thumbs":
            continue
        local_path = local_dir / name
        try:
            ftp.size(remote_path)
        except ftplib.error_perm as exc:
            if "regular files" in str(exc).lower() or "directory" in str(exc).lower():
                count += mirror_tree(ftp, remote_path, local_path)
            elif name == "thumbs":
                pass
            else:
                count += mirror_tree(ftp, remote_path, local_path)
            continue
        if not should_download(name):
            continue
        if download_file(ftp, remote_path, local_path):
            count += 1
    return count


def main() -> int:
    full = "--full" in sys.argv
    print("Connecting to FTP for media sync...", flush=True)
    ftp = connect_ftp()
    total = 0
    errors = 0

    print("Discovering Flash references in HTML...", flush=True)
    bases = discover_flash_bases()
    print(f"  found {len(bases)} flash embed(s)", flush=True)

    print("Syncing audio playlists from discovered paths...", flush=True)
    for base in sorted(bases):
        if not base.startswith("audio/"):
            continue
        try:
            total += sync_audio_for_base(ftp, base)
        except Exception as exc:
            errors += 1
            print(f"  skip audio {base}: {exc}", flush=True)
            try:
                ftp.close()
            except Exception:
                pass
            ftp = connect_ftp()

    for label, sync_fn in (
        ("islamic_pic_gallery", sync_gallery),
        ("majestic_gallery", sync_majestic_gallery),
    ):
        print(f"Syncing {label}...", flush=True)
        try:
            total += sync_fn(ftp)
        except Exception as exc:
            errors += 1
            print(f"  skip {label}: {exc}", flush=True)
            try:
                ftp.close()
            except Exception:
                pass
            ftp = connect_ftp()

    if full:
        for folder in PRIORITY_DIRS:
            remote = f"{FTP_ROOT}/{folder}"
            local = SOURCE / folder
            print(f"Full sync {folder}...", flush=True)
            try:
                total += mirror_tree(ftp, remote, local)
            except Exception as exc:
                errors += 1
                print(f"  skip full {folder}: {exc}", flush=True)

    ftp.quit()
    print(f"Media sync complete ({total} files downloaded, {errors} section errors).", flush=True)
    return 1 if errors and total == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
