"""Run full pipeline: mirror -> pdfs -> build."""
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent


def run(name: str) -> None:
    print(f"\n=== {name} ===")
    subprocess.check_call([sys.executable, str(SCRIPTS / name)])


def main() -> int:
    run("mirror.py")
    run("mirror_media.py")
    run("make_pdfs.py")
    run("build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
