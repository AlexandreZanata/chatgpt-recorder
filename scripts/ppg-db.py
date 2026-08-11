#!/usr/bin/env python3
"""PPG database CLI: migrate, status, integrity-check, vacuum.

Never prints row contents — counts and status only.
Official: https://www.sqlite.org/pragma.html
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.config import ConfigError, get_settings  # noqa: E402
from backend.db.connection import connect  # noqa: E402
from backend.db.migrate import migrate  # noqa: E402

# Static COUNT SQL — never string-format table names into execute().
_COUNT_SQL: dict[str, str] = {
    "schema_migrations": "SELECT COUNT(*) FROM schema_migrations",
    "crypto_keys": "SELECT COUNT(*) FROM crypto_keys",
    "users": "SELECT COUNT(*) FROM users",
    "totp_credentials": "SELECT COUNT(*) FROM totp_credentials",
    "recovery_codes": "SELECT COUNT(*) FROM recovery_codes",
    "sessions": "SELECT COUNT(*) FROM sessions",
    "documents": "SELECT COUNT(*) FROM documents",
    "document_events": "SELECT COUNT(*) FROM document_events",
    "document_signatures": "SELECT COUNT(*) FROM document_signatures",
    "audit_log": "SELECT COUNT(*) FROM audit_log",
    "login_attempts": "SELECT COUNT(*) FROM login_attempts",
    "rate_limits": "SELECT COUNT(*) FROM rate_limits",
}


def _db_path(args: argparse.Namespace) -> Path:
    if args.db:
        return Path(args.db)
    get_settings.cache_clear()
    return get_settings().db_path


def cmd_migrate(args: argparse.Namespace) -> int:
    path = _db_path(args)
    conn = connect(path)
    try:
        migrate(conn)
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        print(f"migrate ok path={path} user_version={version}")
    finally:
        conn.close()
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    path = _db_path(args)
    conn = connect(path)
    try:
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        print(f"path={path}")
        print(f"user_version={version}")
        for table, sql in _COUNT_SQL.items():
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type=? AND name=?",
                ("table", table),
            ).fetchone()
            if not exists:
                print(f"rows.{table}=missing")
                continue
            count = conn.execute(sql).fetchone()[0]
            print(f"rows.{table}={count}")
        wal = Path(str(path) + "-wal")
        print(f"wal_bytes={wal.stat().st_size if wal.is_file() else 0}")
    finally:
        conn.close()
    return 0


def cmd_integrity(args: argparse.Namespace) -> int:
    path = _db_path(args)
    conn = connect(path)
    try:
        check = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={check}")
        fk_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
        print(f"foreign_key_check_rows={len(fk_rows)}")
        if check != "ok" or fk_rows:
            return 1
    finally:
        conn.close()
    return 0


def cmd_vacuum(args: argparse.Namespace) -> int:
    path = _db_path(args)
    conn = connect(path)
    try:
        wal = Path(str(path) + "-wal")
        if wal.is_file() and wal.stat().st_size > 0:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            if wal.is_file() and wal.stat().st_size > 0:
                print("error: WAL still busy; refuse vacuum", file=sys.stderr)
                return 1
        conn.execute("VACUUM")
        print("vacuum ok")
    finally:
        conn.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ppg-db", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    mapping = (
        ("migrate", cmd_migrate, "Apply pending migrations"),
        ("status", cmd_status, "Version, row counts, WAL size"),
        ("integrity-check", cmd_integrity, "integrity_check + foreign_key_check"),
        ("vacuum", cmd_vacuum, "VACUUM (refuses if WAL busy)"),
    )
    for name, func, help_text in mapping:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--db", default=None, help="DB path (default PPG_DB_PATH)")
        p.set_defaults(func=func)
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
