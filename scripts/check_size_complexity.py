#!/usr/bin/env python3
"""CLI: enforce file ≤200, function ≤80, cyclomatic ≤10."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from quality.limits import MAX_CYCLOMATIC, MAX_FILE_LINES, MAX_FUNCTION_LINES
from quality.scan import analyze_file, iter_source_files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    files = iter_source_files(root, args.paths or None)

    if not files:
        print("[size-complexity] No source files to check — OK")
        return 0

    findings = []
    for path in files:
        findings.extend(analyze_file(path))

    if findings:
        print("[size-complexity] FAILED — harness hard caps exceeded:")
        for item in findings:
            rel = (
                item.path.relative_to(root)
                if item.path.is_relative_to(root)
                else item.path
            )
            print(f"  - [{item.kind}] {rel}: {item.detail}")
        print(
            f"\nCaps: file≤{MAX_FILE_LINES}, function≤{MAX_FUNCTION_LINES}, "
            f"cyclomatic≤{MAX_CYCLOMATIC}"
        )
        return 1

    print(
        f"[size-complexity] OK — {len(files)} file(s) within "
        f"file≤{MAX_FILE_LINES}, function≤{MAX_FUNCTION_LINES}, "
        f"cyclomatic≤{MAX_CYCLOMATIC}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
