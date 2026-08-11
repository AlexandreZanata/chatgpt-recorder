"""Scan source files for size and complexity violations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .limits import (
    MAX_CYCLOMATIC,
    MAX_FILE_LINES,
    MAX_FUNCTION_LINES,
    SKIP_DIR_NAMES,
    SOURCE_SUFFIXES,
)
from .parse import (
    c_like_function_ranges,
    cyclomatic_for_slice,
    py_function_ranges,
)


@dataclass
class Finding:
    path: Path
    kind: str
    detail: str


def should_skip_dir(name: str) -> bool:
    return name in SKIP_DIR_NAMES or name.startswith(".")


def iter_source_files(root: Path, explicit: list[Path] | None) -> list[Path]:
    if explicit:
        files = []
        for item in explicit:
            path = item if item.is_absolute() else root / item
            if path.is_file() and path.suffix in SOURCE_SUFFIXES:
                files.append(path.resolve())
        return sorted(set(files))

    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        if any(should_skip_dir(part) for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def analyze_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [Finding(path, "encode", "file is not valid UTF-8")]

    lines = text.splitlines()
    if len(lines) > MAX_FILE_LINES:
        findings.append(
            Finding(path, "file-lines", f"{len(lines)} lines (max {MAX_FILE_LINES})")
        )

    suffix = path.suffix
    ranges = (
        py_function_ranges(lines)
        if suffix == ".py"
        else c_like_function_ranges(lines)
    )

    for name, start, end in ranges:
        body_lines = end - start + 1
        if body_lines > MAX_FUNCTION_LINES:
            findings.append(
                Finding(
                    path,
                    "function-lines",
                    f"{name} @ L{start + 1}: {body_lines} lines "
                    f"(max {MAX_FUNCTION_LINES})",
                )
            )
        cyclo = cyclomatic_for_slice(lines[start : end + 1], suffix)
        if cyclo > MAX_CYCLOMATIC:
            findings.append(
                Finding(
                    path,
                    "complexity",
                    f"{name} @ L{start + 1}: cyclomatic {cyclo} "
                    f"(max {MAX_CYCLOMATIC})",
                )
            )
    return findings
