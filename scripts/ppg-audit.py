#!/usr/bin/env python3
"""PPG audit ledger CLI: verify, tail, export.

Official: phase 14 README chain formula; docs/SECURITY.md retention notes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.audit.ledger import verify_chain  # noqa: E402
from backend.audit.ops import iter_export_jsonl, tail_entries  # noqa: E402
from backend.config import ConfigError, get_settings  # noqa: E402
from backend.db.connection import connect  # noqa: E402


def _db_path(args: argparse.Namespace) -> Path:
    if args.db:
        return Path(args.db)
    get_settings.cache_clear()
    return get_settings().db_path


def cmd_verify(args: argparse.Namespace) -> int:
    path = _db_path(args)
    conn = connect(path)
    try:
        result = verify_chain(conn)
        if result.ok:
            print(f"verify ok checked={result.checked} path={path}")
            return 0
        print(
            f"verify FAIL first_bad_id={result.first_bad_id}"
            f" reason={result.reason} checked={result.checked}",
            file=sys.stderr,
        )
        return 1
    finally:
        conn.close()


def cmd_tail(args: argparse.Namespace) -> int:
    path = _db_path(args)
    conn = connect(path)
    try:
        rows = tail_entries(conn, args.n)
        for row in rows:
            print(
                json.dumps(
                    {
                        "id": row.id,
                        "ts": row.ts,
                        "action": row.action,
                        "outcome": row.outcome,
                        "actor_role": row.actor_role,
                        "resource_type": row.resource_type,
                        "resource_id": row.resource_id,
                        "meta_redacted": row.meta_redacted,
                        "entry_hash": row.entry_hash,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        print(f"tail count={len(rows)} path={path}", file=sys.stderr)
    finally:
        conn.close()
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    path = _db_path(args)
    out = Path(args.out)
    conn = connect(path)
    try:
        lines = list(iter_export_jsonl(conn, since=args.since))
        out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        print(f"export ok lines={len(lines)} out={out} path={path}")
    finally:
        conn.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ppg-audit", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser("verify", help="Recompute chain; exit 1 on break")
    p_verify.add_argument("--db", default=None, help="DB path (default PPG_DB_PATH)")
    p_verify.set_defaults(func=cmd_verify)

    p_tail = sub.add_parser("tail", help="Last N redacted entries (newest first)")
    p_tail.add_argument("-n", type=int, default=10, help="Number of entries")
    p_tail.add_argument("--db", default=None, help="DB path (default PPG_DB_PATH)")
    p_tail.set_defaults(func=cmd_tail)

    p_export = sub.add_parser("export", help="JSONL archive since ISO timestamp")
    p_export.add_argument("--since", required=True, help="ISO timestamp lower bound")
    p_export.add_argument("--out", required=True, help="Output .jsonl path")
    p_export.add_argument("--db", default=None, help="DB path (default PPG_DB_PATH)")
    p_export.set_defaults(func=cmd_export)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
