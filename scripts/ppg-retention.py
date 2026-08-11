#!/usr/bin/env python3
"""PPG retention CLI: dry-run (default) or --apply blob purge (BR-20).

Prints counts only — never client names, numbers, or paths with PII.
Official: https://www.sqlite.org/lang_datefunc.html · MDN 410 Gone.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.audit.context import anonymous_context  # noqa: E402
from backend.config import ConfigError, get_settings  # noqa: E402
from backend.db.connection import connect, transaction  # noqa: E402
from backend.services.retention_service import purge  # noqa: E402

_TS = "%Y-%m-%dT%H:%M:%SZ"


def _cutoff(retention_days: int) -> str:
    when = datetime.now(UTC) - timedelta(days=retention_days)
    return when.strftime(_TS)


def run(*, apply: bool, db: Path | None) -> int:
    get_settings.cache_clear()
    settings = get_settings()
    path = db or settings.db_path
    older_than = _cutoff(settings.retention_days)
    dry_run = not apply
    conn = connect(path)
    try:
        ctx = anonymous_context(request_id="ppg-retention")
        with transaction(conn):
            result = purge(
                conn,
                older_than,
                dry_run=dry_run,
                blob_dir=settings.blob_dir,
                ctx=ctx,
            )
    finally:
        conn.close()
    mode = "dry-run" if result.dry_run else "apply"
    print(
        f"retention {mode} candidates={result.candidates}"
        f" purged={result.purged} older_than={older_than}"
        f" retention_days={settings.retention_days}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ppg-retention", description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Count candidates without changing state (default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Blank overdue blobs and insert purged tombstones",
    )
    parser.add_argument("--db", default=None, help="DB path (default PPG_DB_PATH)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        db = Path(args.db) if args.db else None
        return run(apply=bool(args.apply), db=db)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
