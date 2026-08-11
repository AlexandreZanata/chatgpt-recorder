#!/usr/bin/env python3
"""PPG key CLI: generate-kek, status, rotate-dek (SQLite crypto_keys).

Never prints key material. Imports keys.json once into SQLite when present.
"""

from __future__ import annotations

import argparse
import base64
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

def _kek() -> bytes:
    from backend.config import get_settings

    get_settings.cache_clear()
    return get_settings().kek


def _open_store():
    from backend.config import get_settings
    from backend.db.connection import connect, transaction
    from backend.db.migrate import migrate
    from backend.db.repositories.keys import SqliteKeyStore, import_json_keystore

    get_settings.cache_clear()
    settings = get_settings()
    conn = connect(settings.db_path)
    migrate(conn)
    json_path = settings.blob_dir / "keys.json"
    if json_path.is_file():
        with transaction(conn):
            import_json_keystore(conn, json_path)
    return conn, SqliteKeyStore(conn)


def cmd_generate_kek(_: argparse.Namespace) -> int:
    encoded = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
    print(encoded)
    print(
        "WARNING: Shown once. Store as systemd LoadCredential / 0400 file "
        "(or PPG_KEK in a gitignored .env for dev). Loss is unrecoverable.",
        file=sys.stderr,
    )
    return 0


def _age_days(created_at: str) -> str:
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError:
        return "?"
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - created
    return f"{max(delta.days, 0)}d"


def cmd_status(_: argparse.Namespace) -> int:
    conn, store = _open_store()
    try:
        rows = store.list_entries()
        if not rows:
            print("No DEKs registered.")
            return 0
        print(f"{'id':<36}  {'purpose':<6}  {'state':<8}  {'created_at':<25}  age")
        for entry in rows:
            state = "retired" if entry.retired_at else "active"
            print(
                f"{entry.id:<36}  {entry.purpose:<6}  {state:<8}  "
                f"{entry.created_at:<25}  {_age_days(entry.created_at)}"
            )
    finally:
        conn.close()  # type: ignore[attr-defined]
    return 0


def cmd_rotate_dek(args: argparse.Namespace) -> int:
    from backend.db.connection import transaction
    from backend.security.keys import PURPOSES, rotate_dek

    purpose = args.purpose
    if purpose not in PURPOSES:
        print(f"error: purpose must be one of {', '.join(PURPOSES)}", file=sys.stderr)
        return 2
    conn, store = _open_store()
    try:
        with transaction(conn):
            fresh = rotate_dek(purpose, store=store, kek=_kek())
        print(f"rotated purpose={purpose} new_id={fresh.id}")
    finally:
        conn.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    # Hardcoded so `generate-kek` works before venv deps exist on a fresh VPS.
    purposes = ("field", "blob", "index")
    parser = argparse.ArgumentParser(prog="ppg-keys", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate-kek", help="Print one base64 32-byte KEK")
    gen.set_defaults(func=cmd_generate_kek)
    status = sub.add_parser("status", help="List DEK ids/purposes/ages")
    status.set_defaults(func=cmd_status)
    rotate = sub.add_parser("rotate-dek", help="Retire active DEK; create replacement")
    rotate.add_argument("--purpose", required=True, choices=list(purposes))
    rotate.set_defaults(func=cmd_rotate_dek)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        name = type(exc).__name__
        if name == "ConfigError":
            print(f"config error: {exc}", file=sys.stderr)
            return 1
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
