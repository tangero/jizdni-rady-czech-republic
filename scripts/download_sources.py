#!/usr/bin/env python3
"""
Stažení aktuálních zdrojových GTFS dat do data/sources/.

Zdroje:
    GTFS_CR  - Celostátní informační systém o jízdních řádech (CIS JŘ)
    PID      - Pražská integrovaná doprava (ROPID)

Použití:
    python scripts/download_sources.py            # stáhne všechny zdroje
    python scripts/download_sources.py PID        # jen vybraný zdroj
    python scripts/download_sources.py --force    # stáhne i když se nezměnil

Žádné externí závislosti (pouze stdlib).
"""

import argparse
import email.utils
import json
import os
import shutil
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SOURCES_DIR = PROJECT_DIR / "data" / "sources"

SOURCES = {
    "GTFS_CR": "https://www.spojenka.cz/jrdata/jizdnirady-gtfs.zip",
    "PID": "https://data.pid.cz/PID_GTFS.zip",
}

USER_AGENT = "jizdni-rady-czech-republic/2.2 (+https://github.com/)"


def _remote_last_modified(url: str) -> str:
    """Vrátí hlavičku Last-Modified vzdáleného souboru (nebo prázdný řetězec)."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.headers.get("Last-Modified", "")


def _download(url: str, target: Path) -> None:
    """Stáhne soubor po blocích s průběžným výpisem."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = target.with_suffix(".part")
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as f:
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        while chunk := resp.read(1024 * 1024):
            f.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r    {done / 1e6:6.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    print()
    tmp.replace(target)


def _safe_extract(zip_path: Path, dest: Path) -> list[str]:
    """Rozbalí ZIP (jen ploché .txt soubory, bez path traversal)."""
    extracted = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = Path(info.filename).name
            if info.is_dir() or not name.endswith(".txt") or name != info.filename:
                continue
            with zf.open(info) as src, open(dest / name, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(name)
    return sorted(extracted)


def fetch_source(name: str, url: str, force: bool) -> dict:
    """Stáhne a rozbalí jeden zdroj, vrátí metadata."""
    print(f"\n[{name}] {url}")
    dest = SOURCES_DIR / name
    meta_file = dest / "_source.json"
    old_meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}

    last_modified = _remote_last_modified(url)
    print(f"  Last-Modified: {last_modified or 'neznámé'}")
    if not force and last_modified and old_meta.get("last_modified") == last_modified:
        print("  Beze změny, přeskakuji (použij --force)")
        return old_meta

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    zip_path = dest / "_feed.zip"
    _download(url, zip_path)
    files = _safe_extract(zip_path, dest)
    zip_path.unlink()
    print(f"  Rozbaleno: {', '.join(files)}")

    published = ""
    if last_modified:
        published = email.utils.parsedate_to_datetime(last_modified).date().isoformat()

    meta = {
        "name": name,
        "url": url,
        "last_modified": last_modified,
        "published": published,
        "downloaded": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": files,
    }
    meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Stažení zdrojových GTFS dat")
    parser.add_argument("sources", nargs="*", help=f"Které zdroje stáhnout ({', '.join(SOURCES)})")
    parser.add_argument("--force", action="store_true", help="Stáhnout i nezměněné zdroje")
    args = parser.parse_args()

    unknown = set(args.sources) - set(SOURCES)
    if unknown:
        parser.error(f"Neznámé zdroje: {', '.join(sorted(unknown))}")
    selected = args.sources or list(SOURCES)
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    failed = []
    for name in selected:
        try:
            fetch_source(name, SOURCES[name], args.force)
        except Exception as e:  # noqa: BLE001 - chceme pokračovat dalším zdrojem
            print(f"  CHYBA: {e}")
            failed.append(name)

    if failed:
        print(f"\nNepodařilo se stáhnout: {', '.join(failed)}")
        sys.exit(1)
    print(f"\nHotovo, data v {SOURCES_DIR.relative_to(PROJECT_DIR)}/")


if __name__ == "__main__":
    os.chdir(PROJECT_DIR)
    main()
