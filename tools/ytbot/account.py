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
            config.set_channel_id(match.group(1))
            page.goto(config.STUDIO_UPLOAD, timeout=90000)
            page.wait_for_timeout(7000)
        body = page.locator("body").inner_text()
        if name not in body:
            raise RuntimeError(
                f"could not switch to channel {name!r}; sign in or add it to the bot profile")
        log(f"active channel: {name}")
    finally:
        page.close()
