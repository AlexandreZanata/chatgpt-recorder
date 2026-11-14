#!/usr/bin/env python3
"""Refuse private runtime paths and recognizable credentials in Git-visible files."""

from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(
    ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root
).split(b"\0")
failures = []
markers = [
    b"-----BEGIN " + b"PRIVATE KEY-----",
    b"-----BEGIN OPENSSH " + b"PRIVATE KEY-----",
]
for item in set(paths):
    if not item:
        continue
    path = Path(item.decode())
    if path.parts[0] == ".local" or path.name in {
        ".env",
        "credentials.json",
        "token.json",
    }:
        failures.append(str(path))
        continue
    file = root / path
    if not file.is_file() or file.stat().st_size > 2 * 1024 * 1024:
        continue
    data = file.read_bytes()
    if any(marker in data for marker in markers):
        failures.append(str(path))
if failures:
    print(
        "Publication refused for private paths/material: "
        + ", ".join(sorted(failures)),
        file=sys.stderr,
    )
    sys.exit(1)
print("Publication path/key checks passed (ignored private files are not opened).")
