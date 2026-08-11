"""Fail if secret-like names are compared with ``==`` (use tokens_equal).

Scans backend/ and scripts/ Python sources. Append ``# secret-compare-ok`` to
allow a line intentionally (rare). Official: hmac.compare_digest.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SCAN_DIRS = (ROOT / "backend", ROOT / "scripts")
_PATTERN = re.compile(
    r"(?i)(?:"
    r"\b(?:token|secret|password|passwd|passphrase|kek|csrf|api_key|apikey)\w*"
    r"\s*=="
    r"|"
    r"==\s*(?:token|secret|password|passwd|passphrase|kek|csrf|api_key|apikey)\w*"
    r")"
)
_ALLOW = re.compile(r"secret-compare-ok|compare_digest|tokens_equal")
_SKIP_NAME = frozenset({"check_secret_compare.py"})


def _iter_py_files() -> list[Path]:
    files: list[Path] = []
    for base in _SCAN_DIRS:
        if not base.is_dir():
            continue
        files.extend(path for path in base.rglob("*.py") if path.name not in _SKIP_NAME)
    return sorted(files)


def main() -> int:
    hits: list[str] = []
    for path in _iter_py_files():
        rel = path.relative_to(ROOT)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _ALLOW.search(line):
                continue
            if _PATTERN.search(line):
                hits.append(f"{rel}:{lineno}: {line.strip()}")
    if hits:
        print("[lint] FAIL: secret-like values compared with ==", file=sys.stderr)
        print("Use backend.security.tokens.tokens_equal / hmac.compare_digest.", file=sys.stderr)
        for hit in hits:
            print(f"  {hit}", file=sys.stderr)
        return 1
    print("[lint] secret == compare check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
