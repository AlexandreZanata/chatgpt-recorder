"""Command line entry point for the local YouTube automation bot."""

from __future__ import annotations

import argparse
import json

from . import catalog, channels, config, logic, runtime


def command_setup(_args) -> None:
    runtime.setup_profile()
    runtime.start_hidden_chrome()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser, context = runtime.connect_hidden(playwright)
        runtime.configure_downloads(browser)
        runtime.configure_extension(context)
    print("[ytbot] runtime ready in hidden workspace", config.DISPLAY)


def command_catalog(args) -> None:
    if args.channel:
        channels.apply(args.channel)
    runtime.start_hidden_chrome()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser, context = runtime.connect_hidden(playwright)
        data = catalog.scrape_public_catalog(context)
        catalog.write_catalog_markdown(data)
    print(f"[ytbot] catalog: {len(data)} videos")


def command_check(args) -> None:
    if args.channel:
        channels.apply(args.channel)
    matches = logic.similar_topics(args.topic, logic.load_catalog())
    if matches:
        print("[ytbot] topic is similar to:")
        for title in matches:
            print("  - " + title)
    else:
        print("[ytbot] topic is new")


def command_run(args) -> None:
    channels.apply(args.channel)
    from .batch import run_batch
    from .account_commands import apply_bound_account
    from .accounts_store import AccountStore
    selected = apply_bound_account(args.channel, args.account)
    from .service_jobs import channel_lock
    with AccountStore().profile_lock(selected), channel_lock(args.channel):
        failures = run_batch(args.count, args.parallel, args.upload_cdp or None)
    print("[ytbot] process finished")
    if failures:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ytbot", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="prepare cookies, extension and hidden Chrome").set_defaults(func=command_setup)
    catalog_parser = sub.add_parser("catalog", help="refresh the channel catalog")
    catalog_parser.add_argument("--channel", choices=sorted(channels.CHANNELS), default="")
    catalog_parser.set_defaults(func=command_catalog)
    check = sub.add_parser("check", help="check a topic against the catalog")
    check.add_argument("topic")
    check.add_argument("--channel", choices=sorted(channels.CHANNELS), default="")
    check.set_defaults(func=command_check)
    run = sub.add_parser("run", help="generate, render, upload and schedule videos")
    run.add_argument("--channel", choices=sorted(channels.CHANNELS), required=True,
                     help="channel profile; ask the user when it is not specified")
    run.add_argument("--count", type=int, default=1)
    run.add_argument("--account", default=None, help="explicit registered browser account (otherwise the channel binding or legacy session)")
    run.add_argument("--parallel", type=int, default=0,
                     help="tabs used for article and audio stages (0 = one per video)")
    run.add_argument("--upload-cdp", type=int, default=0)
    run.set_defaults(func=command_run)
    from .account_commands import add_parser
    add_parser(sub)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)
