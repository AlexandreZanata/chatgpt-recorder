"""Visible account sign-in and explicit profile selection; existing upload flow is reused."""

from __future__ import annotations
import json
import os
import signal
import subprocess
from pathlib import Path
from . import browser_install, config, runtime
from .accounts_store import AccountStore

SIGN_IN = "https://accounts.google.com/ServiceLogin?service=youtube&continue=https%3A%2F%2Fstudio.youtube.com%2F"


def browser_connect(identifier: str, store: AccountStore | None = None, *, managed: bool = False) -> None:
    store = store or AccountStore()
    with store.profile_lock(identifier):
        store.activate(identifier)
        # Only this dedicated bot account is stopped; the normal Chrome profile is never touched.
        runtime.stop_hidden_chrome()
        if managed:
            store.use_managed_browser(identifier)
            store.activate(identifier)
        if not config.EXT_PATH.is_dir():
            subprocess.run(
                ["python3", str(config.ROOT / "scripts/build-chrome.py")], check=True
            )
        (config.PROFILE / "Default").mkdir(mode=0o700, parents=True, exist_ok=True)
        runtime._write_preferences()
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            raise ValueError(
                "open account connection from the logged-in graphical Linux session"
            )
        process = subprocess.Popen(
            [
                browser_install.executable(),
                *browser_install.arguments(),
                f"--user-data-dir={config.PROFILE}",
                "--profile-directory=Default",
                "--no-first-run",
                "--no-default-browser-check",
                "--new-window",
                SIGN_IN,
                "https://chatgpt.com/",
            ],
            env=browser_install.environment(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # The account window's explicit Finish button ends only its own browser.
        finished_by_owner = False

        def finish(_signal, _frame):
            nonlocal finished_by_owner
            finished_by_owner = True
            process.terminate()

        previous = signal.signal(signal.SIGTERM, finish)
        try:
            code = process.wait()
            if code and not finished_by_owner:
                raise RuntimeError("the sign-in browser could not finish; check installation and the desktop session")
        finally:
            signal.signal(signal.SIGTERM, previous)


def verify_browser(
    channel_slug: str, identifier: str, store: AccountStore | None = None
) -> None:
    from . import account, channels
    from playwright.sync_api import sync_playwright

    store = store or AccountStore()
    with store.profile_lock(identifier):
        channels.apply(channel_slug)
        store.activate(identifier)
        runtime.start_hidden_chrome()
        with sync_playwright() as playwright:
            _browser, context = runtime.connect_hidden(playwright)
            account.ensure_channel(context)
        store.bind(channel_slug, identifier, channels.get(channel_slug).channel_id)


def check_connection(channel_slug: str, identifier: str, store: AccountStore | None = None) -> dict:
    """Inspect the selected dedicated session without generating or uploading media."""
    from . import account, channels
    from playwright.sync_api import sync_playwright

    store = store or AccountStore()
    result = {"channel_verified": False, "extension_ready": False,
              "chatgpt_authenticated": False}
    with store.profile_lock(identifier):
        channels.apply(channel_slug)
        store.activate(identifier)
        runtime.start_hidden_chrome()
        with sync_playwright() as playwright:
            _browser, context = runtime.connect_hidden(playwright)
            try:
                account.ensure_channel(context)
                result["channel_verified"] = True
            except Exception:
                pass
            page = context.new_page()
            try:
                page.goto(f"chrome-extension://{config.EXT_ID}/popup.html", timeout=20000)
                result["extension_ready"] = page.evaluate("typeof chrome.storage?.local === 'object'")
            except Exception:
                pass
            finally:
                page.close()
            page = context.new_page()
            try:
                page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=60000)
                result["chatgpt_authenticated"] = page.evaluate("""async () => {
                    try {
                        const response = await fetch('/api/auth/session', {credentials: 'include'});
                        const value = await response.json();
                        return response.ok && !!value.user;
                    } catch (_) { return false; }
                }""")
            except Exception:
                pass
            finally:
                page.close()
    result["ready"] = all(result.values())
    return result


def apply_bound_account(channel: str, explicit: str | None = None) -> str:
    store = AccountStore()
    binding = store.load()["bindings"].get(channel, {})
    selected = explicit or binding.get("account_id", "legacy")
    store.activate(selected)
    return selected


def execute(args) -> None:
    store = AccountStore()
    if args.account_command == "list":
        print(json.dumps(store.public_accounts(), ensure_ascii=False))
    elif args.account_command == "add":
        print(json.dumps(store.create(args.id, args.label), ensure_ascii=False))
    elif args.account_command == "connect":
        browser_connect(args.account, store, managed=args.managed)
    elif args.account_command == "oauth":
        from .oauth import connect

        print(
            json.dumps(
                connect(store, args.account, Path(args.client)), ensure_ascii=False
            )
        )
    elif args.account_command == "bind":
        from .oauth import verified_channels

        if args.verify_browser:
            verify_browser(args.channel, args.account, store)
        else:
            if not args.channel_id or not any(
                item["id"] == args.channel_id
                for item in verified_channels(store, args.account)
            ):
                raise ValueError(
                    "authorize this exact channel with Google or use --verify-browser"
                )
            store.bind(args.channel, args.account, args.channel_id)
        print("Channel identity bound to the selected account.")
    elif args.account_command == "ui":
        from src.ui.accounts_window import run_accounts

        run_accounts()
    elif args.account_command == "check":
        import contextlib
        import sys

        with contextlib.redirect_stdout(sys.stderr):
            result = check_connection(args.channel, args.account, store)
        print(json.dumps(result))
        if not result["ready"]:
            raise SystemExit(1)


def add_parser(sub) -> None:
    parser = sub.add_parser(
        "accounts", help="manage visible Google sign-in and channel account bindings"
    )
    accounts = parser.add_subparsers(dest="account_command", required=True)
    accounts.add_parser("list")
    add = accounts.add_parser("add")
    add.add_argument("--id", required=True)
    add.add_argument("--label", required=True)
    browser = accounts.add_parser("connect")
    browser.add_argument("--account", required=True)
    browser.add_argument("--managed", action="store_true", help="use a separate automatic-extension profile, preserving the previous system-browser profile")
    oauth = accounts.add_parser("oauth")
    oauth.add_argument("--account", required=True)
    oauth.add_argument("--client", required=True)
    bind = accounts.add_parser("bind")
    bind.add_argument("--account", required=True)
    from .channels import CHANNELS

    bind.add_argument("--channel", choices=sorted(CHANNELS), required=True)
    bind.add_argument("--channel-id")
    bind.add_argument("--verify-browser", action="store_true")
    accounts.add_parser("ui")
    check = accounts.add_parser("check", help="check channel, capture extension and ChatGPT session")
    check.add_argument("--account", required=True)
    check.add_argument("--channel", choices=sorted(CHANNELS), required=True)
    parser.set_defaults(func=execute)
