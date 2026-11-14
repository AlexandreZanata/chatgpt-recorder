"""Switch the active YouTube brand account/channel in the bot profile."""

from __future__ import annotations

import re

from . import config


def log(message: str) -> None:
    print(f"[account] {message}", flush=True)


def ensure_channel(context, name: str | None = None) -> None:
    name = name or config.CHANNEL_NAME
    page = context.new_page()
    try:
        page.goto("https://www.youtube.com/", timeout=90000)
        page.wait_for_timeout(7000)
        page.keyboard.press("Escape")
        page.evaluate(
            "()=>document.querySelectorAll('tp-yt-iron-overlay-backdrop').forEach(e=>e.remove())")
        page.locator("#avatar-btn").click()
        page.wait_for_timeout(2000)
        active = page.evaluate(
            "()=>document.querySelector('ytd-active-account-header-renderer #account-name')"
            "?.innerText?.trim() || ''")
        if active == name:
            page.keyboard.press("Escape")
            page.goto("https://studio.youtube.com/", timeout=90000)
            page.wait_for_timeout(7000)
            verify_channel_identity(page.url, config.CHANNEL_ID)
            log(f"active channel: {name}")
            return
        switcher = None
        for label in ("Mudar de conta", "Switch account"):
            locator = page.get_by_text(label, exact=True)
            if locator.count():
                switcher = locator.first
                break
        if switcher is None:
            raise RuntimeError("account switcher not found")
        switcher.click()
        page.wait_for_timeout(2500)
        link = page.get_by_text(name, exact=True)
        if link.count():
            link.first.click()
            page.wait_for_timeout(6000)
        page.goto("https://studio.youtube.com/", timeout=90000)
        page.wait_for_timeout(9000)
        match = re.search(r"studio\.youtube\.com/channel/(UC[\w-]+)", page.url)
        if match:
            verify_channel_identity(page.url, config.CHANNEL_ID)
            page.goto(config.STUDIO_UPLOAD, timeout=90000)
            page.wait_for_timeout(7000)
        verify_channel_identity(page.url, config.CHANNEL_ID)
        body = page.locator("body").inner_text()
        if name not in body:
            raise RuntimeError(
                f"could not switch to channel {name!r}; sign in or add it to the bot profile")
        log(f"active channel: {name}")
    finally:
        page.close()


def verify_channel_identity(url: str, expected: str) -> str:
    """A matching display name alone never authorizes an upload to another channel."""
    match = re.search(r"^https://studio\.youtube\.com/channel/(UC[\w-]+)(?:[/?#]|$)", url)
    if match is None or match.group(1) != expected:
        raise RuntimeError("YouTube channel identity mismatch; select the intended channel in this account")
    return match.group(1)
