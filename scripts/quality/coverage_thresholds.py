"""Enforce per-package coverage thresholds from coverage.json."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _pct(covered: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return 100.0 * covered / total


def _package_stats(files: dict, prefix: str) -> tuple[float, float, int]:
    stmts = covered = branches = br_cov = 0
    for path, info in files.items():
        norm = path.replace("\\", "/")
        if not norm.startswith(prefix):
            continue
        summary = info["summary"]
        stmts += summary["num_statements"]
        covered += summary["covered_lines"]
        branches += summary.get("num_branches", 0)
        br_cov += summary.get("covered_branches", 0)
    return _pct(covered, stmts), _pct(br_cov, branches), stmts


def _overall(totals: dict) -> tuple[float, float]:
    line = _pct(totals["covered_lines"], totals["num_statements"])
    branch = _pct(
        totals.get("covered_branches", 0),
        totals.get("num_branches", 0),
    )
    return line, branch


def _planned() -> list[tuple[str, str, float | None, float | None, str]]:
    """Package gates. None mins = deferred until the named phase lands code."""
    return [
        ("backend/security", "prefix", 100.0, 100.0, "phase 12"),
        ("backend/db", "prefix", 100.0, 100.0, "phase 13"),
        ("backend/audit", "prefix", 100.0, 100.0, "phase 14"),
        ("backend/services", "prefix", 95.0, 95.0, "phase 18"),
        ("backend/storage", "prefix", 100.0, 100.0, "phase 18"),
        ("backend/routers", "prefix", None, None, "TODO phase 17+ → 95/95"),
        ("backend (overall)", "overall", None, None, "TODO → 90/90 when ≥90%"),
    ]


def _measure(
    name: str,
    kind: str,
    files: dict,
    totals: dict,
) -> tuple[float, float, int]:
    if kind == "overall":
        line_pct, br_pct = _overall(totals)
        return line_pct, br_pct, totals["num_statements"]
    return _package_stats(files, name.rstrip("/") + "/")


def _check_row(
    name: str,
    line_pct: float,
    br_pct: float,
    stmts: int,
    kind: str,
    line_min: float | None,
    br_min: float | None,
    note: str,
) -> list[str]:
    absent = kind == "prefix" and stmts == 0
    need_l = f"{line_min:.0f}" if line_min is not None else "—"
    need_b = f"{br_min:.0f}" if br_min is not None else "—"
    suffix = " (absent)" if absent else ""
    print(
        f"{name:<22} {line_pct:6.1f}% {need_l:>7} "
        f"{br_pct:6.1f}% {need_b:>7} {note}{suffix}"
    )
    fails: list[str] = []
    if absent:
        return fails
    if line_min is not None and line_pct + 1e-9 < line_min:
        fails.append(f"{name} lines {line_pct:.1f}% < {line_min:.0f}%")
    if br_min is not None and br_pct + 1e-9 < br_min:
        fails.append(f"{name} branches {br_pct:.1f}% < {br_min:.0f}%")
    return fails


def _force_overall(totals: dict) -> list[str]:
    raw = os.environ.get("PPG_COVERAGE_FORCE_OVERALL_MIN")
    if not raw:
        return []
    force_min = float(raw)
    line_pct, _ = _overall(totals)
    print(
        f"{'FORCE overall':<22} {line_pct:6.1f}% {force_min:.0f} "
        f"{'':>7} {'':>7} PPG_COVERAGE_FORCE_OVERALL_MIN"
    )
    if line_pct + 1e-9 < force_min:
        return [f"backend (overall) lines {line_pct:.1f}% < {force_min:.0f}%"]
    return []


def main(argv: list[str]) -> int:
    path = Path(argv[1] if len(argv) > 1 else "coverage.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    files = data["files"]
    totals = data["totals"]
    if totals.get("num_statements", 0) < 1:
        print("[coverage] FAILED: no backend statements measured")
        return 1

    failures: list[str] = []
    print("[coverage] package thresholds:")
    print(f"{'package':<22} {'lines':>7} {'need':>7} {'branch':>7} {'need':>7} note")
    for name, kind, line_min, br_min, note in _planned():
        line_pct, br_pct, stmts = _measure(name, kind, files, totals)
        failures.extend(
            _check_row(name, line_pct, br_pct, stmts, kind, line_min, br_min, note)
        )
    failures.extend(_force_overall(totals))

    if failures:
        print("[coverage] FAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
