#!/usr/bin/env python3
"""CLI script: Verify distribution zip package contents and structure."""

from __future__ import annotations
import sys
import zipfile
from pathlib import Path

REQUIRED_FILES = {
    "manifest.json",
    "popup.html",
    "src/background.js",
    "src/content-script.js",
    "src/page-injector.js",
    "icons/icon-idle.svg"
}

def verify_zip(zip_path: Path) -> int:
    if not zip_path.is_file():
        print(f"[package-verify] FAIL: Zip archive not found at {zip_path}")
        return 1
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = set(zf.namelist())
        missing = REQUIRED_FILES - namelist
        if missing:
            print(f"[package-verify] FAIL: Missing required files in zip: {missing}")
            return 1
    print(f"[package-verify] OK — All {len(REQUIRED_FILES)} required files verified in {zip_path.name}")
    return 0

def main() -> int:
    root = Path(__file__).resolve().parent.parent
    dist_zip = root / "dist" / "chatgpt-audio-capture-v0.1.0.zip"
    return verify_zip(dist_zip)

if __name__ == "__main__":
    sys.exit(main())
