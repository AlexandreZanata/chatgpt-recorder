"""ChatGPT article generation and Read aloud audio capture."""

from __future__ import annotations

import re
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import config, logic

AUDIO_LOCK = threading.Lock()
COPY_LOCK = threading.Lock()


def log(message: str) -> None:
    print(f"[chat] {message}", flush=True)


def dismiss_notice(page) -> None:
    for name in ("Keep using GPT", "Use plugin"):
        button = page.get_by_role("button", name=name, exact=True)
        if button.count():
            button.first.click(force=True)
            page.wait_for_timeout(1200)
            return


def send_text(page, text: str) -> None:
    page.evaluate("document.querySelector('[role=\"textbox\"]').focus()")
    page.keyboard.insert_text(text)
    page.wait_for_timeout(400)
    send = page.locator('button[aria-label="Send"]')
    if send.count() and send.first.is_enabled() and send.first.get_attribute("aria-disabled") != "true":
        send.first.click()
    else:
        page.keyboard.press("Enter")
    page.wait_for_timeout(500)


def extract_assistant_text(page) -> str:
    body = page.locator("body").inner_text()
    marker = "ChatGPT said:"
    start = body.rfind(marker)
    text = body[start + len(marker):] if start != -1 else body
    for stop in ("ChatGPT can make mistakes", "Latest response",
                 "Simple Deep Dive is now a plugin", "Thinking effort"):
        index = text.find(stop)
        if index != -1:
            text = text[:index]
    return clean_article(text)


def wait_for_assistant(page, timeout: int = 1800) -> None:
    deadline = time.time() + timeout
    stable = 0
    last_len = 0
    while time.time() < deadline:
        if page.locator('button[aria-label="Copy"]').count() >= 1:
            page.wait_for_timeout(2500)
            return
        body = page.locator("body").inner_text()
        if "Something went wrong" in body or "Error generating" in body:
            raise RuntimeError("ChatGPT reported a generation error")
        length = len(body)
        streaming = page.locator('button[aria-label="Stop"]').count() > 0
        if not streaming and length > 2000 and length == last_len:
            stable += 1
            if stable >= 2:
                page.wait_for_timeout(1000)
                return
        else:
            stable = 0
        last_len = length
        page.wait_for_timeout(2000)
    raise TimeoutError("assistant response did not finish")


def copy_last(page) -> str:
    with COPY_LOCK:
        has_copy = page.evaluate("document.querySelectorAll('button[aria-label=\"Copy\"]').length") > 0
        if has_copy:
            page.evaluate(
                "()=>{const b=[...document.querySelectorAll('button[aria-label=\"Copy\"]')];"
                "if(b.length)b[b.length-1].click()}"
            )
            page.wait_for_timeout(700)
            text = page.evaluate("navigator.clipboard.readText()")
            if text:
                return text
        return extract_assistant_text(page)


def clean_article(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("—", ",").replace("–", ",")
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def generate_article(page, topic: str, run_dir: Path) -> str:
    page.goto(config.GPT_URL, timeout=90000)
    page.wait_for_timeout(7000)
    dismiss_notice(page)
    send_text(page, config.prompt("article_header.txt") + "\n\nTheme: " + topic)
    log(f"article prompt sent: {topic}")
    wait_for_assistant(page)
    text = clean_article(copy_last(page))
    if len(text) < 2000:
        raise RuntimeError(f"article is too short ({len(text)} chars)")
    (run_dir / "article.md").write_text(text, encoding="utf-8")
    (run_dir / "article.txt").write_text(text, encoding="utf-8")
    log(f"article saved: {len(text)} chars")
    return text


def _audio_entry(context, start: str):
    workers = [w for w in context.service_workers if config.EXT_ID in (w.url or "")]
    if not workers:
        return None
    history = workers[0].evaluate("chrome.storage.local.get('captureHistory')").get("captureHistory", [])
    fresh = [item for item in history if str(item.get("capturedAt", "")) >= start]
    if not fresh:
        return None
    entry = fresh[0]
    items = workers[0].evaluate(f"chrome.downloads.search({{id:{entry['downloadId']}}})")
    return entry, items[0] if items else {}


def _save_audio(entry, item, run_dir: Path) -> Path | None:
    if entry.get("status") != "complete" or item.get("state") != "complete":
        return None
    source = Path(item["filename"])
    suffix = ".aac" if "aac" in (item.get("mime") or "") else ".webm"
    destination = run_dir / f"narration{suffix}"
    shutil.copy2(source, destination)
    return destination


def capture_audio(page, context, run_dir: Path, timeout: int = 3600) -> Path:
    start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    clicked = page.evaluate(
        "()=>{const b=[...document.querySelectorAll('button[aria-label=\"Read aloud\"]')];"
        "if(!b.length)return 'none'; b[b.length-1].click(); return 'clicked'}"
    )
    log(f"read aloud: {clicked}")
    if clicked == "none":
        raise RuntimeError("Read aloud button was not available")
    deadline = time.time() + timeout
    while time.time() < deadline:
        with AUDIO_LOCK:
            page.wait_for_timeout(5000)
            found = _audio_entry(context, start)
            if not found:
                continue
            entry, item = found
            log(f"audio {entry.get('status')} / {item.get('state')} / {item.get('fileSize')} bytes")
            destination = _save_audio(entry, item, run_dir)
            if destination:
                log(f"audio saved: {destination.name} ({destination.stat().st_size} bytes)")
                return destination
    raise TimeoutError("audio capture timed out")


def generate_topics(context, count: int, existing: list[str]) -> list[str]:
    page = context.new_page()
    try:
        page.goto("https://chatgpt.com/", timeout=90000)
        page.wait_for_timeout(7000)
        dismiss_notice(page)
        titles = "\n".join(existing[-120:])
        request = config.prompt("topics.txt").replace("{titles}", titles)
        send_text(page, request + f"\n\nRequested number of topics: {count}")
        wait_for_assistant(page, timeout=600)
        raw = copy_last(page)
        topics = []
        for line in raw.splitlines():
            line = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip().strip('"\'')
            line = re.sub(r"[—–]", ",", line).strip()
            if 3 <= len(line) <= 140:
                topics.append(line)
        return topics[:count]
    finally:
        page.close()
