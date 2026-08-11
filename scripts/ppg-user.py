#!/usr/bin/env python3
"""PPG user CLI: create-owner, list, reset-password, unlock, disable, reset-2fa.

Passwords are read via getpass only — never CLI arguments.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.config import ConfigError, get_settings  # noqa: E402
from backend.db.connection import connect, transaction  # noqa: E402
from backend.db.migrate import migrate  # noqa: E402
from backend.services import admin_2fa  # noqa: E402
from backend.services import user_admin as admin  # noqa: E402


def _db_and_kek(args: argparse.Namespace) -> tuple[Path, bytes]:
    if args.db:
        get_settings.cache_clear()
        settings = get_settings()
        return Path(args.db), settings.kek
    get_settings.cache_clear()
    settings = get_settings()
    return settings.db_path, settings.kek


def _prompt_password() -> str:
    first = getpass.getpass("Password: ")
    second = getpass.getpass("Confirm password: ")
    admin.validate_password(first, second)
    return first


def cmd_create_owner(args: argparse.Namespace) -> int:
    role = args.role
    path, kek = _db_and_kek(args)
    password = _prompt_password()
    conn = connect(path)
    try:
        migrate(conn)
        with transaction(conn):
            row = admin.create_user(
                conn,
                username=args.username,
                password=password,
                role=role,
                kek=kek,
            )
        print(f"created public_id={row.public_id} role={row.role}")
    finally:
        conn.close()
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    path, _kek = _db_and_kek(args)
    conn = connect(path)
    try:
        migrate(conn)
        for public_id, role, status in admin.list_users(conn):
            print(f"{public_id}\t{role}\t{status}")
    finally:
        conn.close()
    return 0


def cmd_reset_password(args: argparse.Namespace) -> int:
    path, _kek = _db_and_kek(args)
    password = _prompt_password()
    conn = connect(path)
    try:
        migrate(conn)
        with transaction(conn):
            admin.reset_password(conn, public_id=args.public_id, password=password)
        print(f"password reset public_id={args.public_id}")
    finally:
        conn.close()
    return 0


def cmd_unlock(args: argparse.Namespace) -> int:
    path, _kek = _db_and_kek(args)
    conn = connect(path)
    try:
        migrate(conn)
        with transaction(conn):
            admin.unlock(conn, public_id=args.public_id)
        print(f"unlocked public_id={args.public_id}")
    finally:
        conn.close()
    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    path, _kek = _db_and_kek(args)
    conn = connect(path)
    try:
        migrate(conn)
        with transaction(conn):
            admin.disable(conn, public_id=args.public_id)
        print(f"disabled public_id={args.public_id}")
    finally:
        conn.close()
    return 0


def cmd_reset_2fa(args: argparse.Namespace) -> int:
    path, kek = _db_and_kek(args)
    conn = connect(path)
    try:
        migrate(conn)
        with transaction(conn):
            public_id = admin_2fa.reset_2fa(
                conn, username=args.username, kek=kek
            )
        print(f"2fa reset public_id={public_id} username={args.username}")
    finally:
        conn.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ppg-user", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create-owner", help="Create owner or operator user")
    p_create.add_argument("--username", required=True)
    p_create.add_argument(
        "--role",
        default="owner",
        choices=("owner", "operator"),
        help="owner (default, single) or operator",
    )
    p_create.add_argument("--db", default=None)
    p_create.set_defaults(func=cmd_create_owner)

    p_list = sub.add_parser("list", help="List public ids and roles")
    p_list.add_argument("--db", default=None)
    p_list.set_defaults(func=cmd_list)

    for name, func, help_text in (
        ("reset-password", cmd_reset_password, "Reset password by public id"),
        ("unlock", cmd_unlock, "Clear lockout counters"),
        ("disable", cmd_disable, "Set status=disabled"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--public-id", required=True)
        p.add_argument("--db", default=None)
        p.set_defaults(func=func)

    p_2fa = sub.add_parser(
        "reset-2fa",
        help="Clear TOTP credential and force re-enrollment",
    )
    p_2fa.add_argument("--username", required=True)
    p_2fa.add_argument("--db", default=None)
    p_2fa.set_defaults(func=cmd_reset_2fa)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (ConfigError, admin.UserAdminError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
