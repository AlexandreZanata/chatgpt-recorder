#!/usr/bin/env python3
"""Concatenate design/components/*.css into design/app.css (no @import).

stdlib only. Idempotent: identical inputs → byte-identical output.
Run before deploy or after editing a component CSS file:

  python3 scripts/build-frontend-css.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "frontend" / "design"
ORDER = (
    "button.css",
    "field.css",
    "badge.css",
    "card.css",
    "status-line.css",
    "toast.css",
    "progress.css",
    "skeleton.css",
    "empty-state.css",
    "data-table.css",
    "key-value.css",
    "copy-field.css",
    "dialog.css",
    "code-input.css",
    "app-shell.css",
)


def build() -> bytes:
    parts = ["/* Generated: scripts/build-frontend-css.py — do not hand-edit. */\n"]
    for name in ORDER:
        path = DESIGN / "components" / name
        text = path.read_text(encoding="utf-8")
        parts.append(f"\n/* --- {name} --- */\n")
        parts.append(text if text.endswith("\n") else text + "\n")
    return "".join(parts).encode("utf-8")


def main() -> int:
    out = DESIGN / "app.css"
    data = build()
    if out.is_file() and out.read_bytes() == data:
        print(f"[build-frontend-css] unchanged {out.relative_to(ROOT)} ({len(data)} bytes)")
        return 0
    out.write_bytes(data)
    print(f"[build-frontend-css] wrote {out.relative_to(ROOT)} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
