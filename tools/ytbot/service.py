"""Version-one bounded JSON adapter for trusted local ZaturoBot worker commands."""

from __future__ import annotations
import argparse
import json
import sys
from . import channels, config
from .accounts_store import AccountStore
from . import library, service_jobs


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("capabilities")
    commands.add_parser("profiles")
    runs = commands.add_parser("runs")
    runs.add_argument("--channel", choices=sorted(channels.CHANNELS), required=True)
    runs.add_argument("--limit", type=int, default=20)
    submit = commands.add_parser("submit")
    submit.add_argument("--operation-id", required=True)
    submit.add_argument("--channel", choices=sorted(channels.CHANNELS), required=True)
    submit.add_argument("--account", required=True)
    submit.add_argument("--count", type=int, required=True)
    submit.add_argument("--approved-schedule", action="store_true")
    for verb in ["status", "_execute"]:
        command = commands.add_parser(verb)
        command.add_argument("--operation-id", required=True)
    return root


def dispatch(args) -> dict | None:
    if args.command == "capabilities":
        return {
            "schema_version": 1,
            "service": "youtube",
            "max_count": 10,
            "capabilities": [
                "youtube.profiles.list",
                "youtube.runs.list",
                "youtube.batch.submit",
                "youtube.batch.status",
            ],
        }
    if args.command == "profiles":
        return {"schema_version": 1, "profiles": library.profiles(AccountStore())}
    if args.command == "runs":
        return {
            "schema_version": 1,
            "channel": args.channel,
            "runs": library.runs(args.channel, args.limit),
        }
    if args.command == "submit":
        return service_jobs.submit(
            args.operation_id,
            args.channel,
            args.account,
            args.count,
            args.approved_schedule,
        )
    if args.command == "status":
        return service_jobs.status(args.operation_id)
    if args.command == "_execute":
        service_jobs.execute(args.operation_id)
        return None
    raise ValueError("unknown command")


def main() -> int:
    config.configure_timezone()
    args = parser().parse_args()
    try:
        result = dispatch(args)
        if result is not None:
            output = json.dumps(result, ensure_ascii=False)
            if len(output.encode()) > 65536:
                raise ValueError("adapter response exceeds its output limit")
            print(output)
        return 0
    except Exception:
        # Never serialize arbitrary provider/browser exceptions, credentials or local paths.
        print(json.dumps({"schema_version": 1, "error": "operation_rejected"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
