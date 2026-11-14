"""Metadata and Black Ink Void thumbnail generation."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from . import config, logic
from .chat import copy_last, dismiss_notice, log, send_text, wait_for_assistant


def article_excerpt(run_dir: Path, limit: int = 8000) -> str:
    return (run_dir / "article.txt").read_text(encoding="utf-8")[:limit]


def generate_metadata(context, run_dir: Path, topic: str) -> dict:
    page = context.new_page()
    try:
        page.goto("https://chatgpt.com/", timeout=90000)
        page.wait_for_timeout(7000)
        dismiss_notice(page)
        request = (config.prompt("metadata.txt") + "\n\nStory topic: " + topic
                   + "\n\nARTICLE (excerpt, included below):\n" + article_excerpt(run_dir))
        send_text(page, request)
        log(f"metadata prompt sent: {topic}")
        wait_for_assistant(page)
        raw = copy_last(page).strip()
        (run_dir / "metadata.txt").write_text(raw, encoding="utf-8")
        parsed = logic.parse_metadata(raw)
        (run_dir / "metadata.json").write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"metadata saved: title={parsed['title']!r}")
        return parsed
    finally:
        page.close()


def image_data_url(page) -> str | None:
    return page.evaluate(
        """async () => {
          const imgs = [...document.querySelectorAll('img')].filter(
            (i) => i.naturalWidth >= 400 && i.naturalHeight >= 200);
          if (!imgs.length) return null;
          const img = imgs[imgs.length - 1];
          try {
            const resp = await fetch(img.src);
            const blob = await resp.blob();
            return await new Promise((resolve) => {
              const reader = new FileReader();
              reader.onload = () => resolve(reader.result);
              reader.readAsDataURL(blob);
            });
          } catch (error) { return null; }
        }"""
    )


def generate_thumbnail(context, run_dir: Path, timeout: int = 1200) -> Path | None:
    page = context.new_page()
    try:
        page.goto("https://chatgpt.com/", timeout=90000)
        page.wait_for_timeout(7000)
        dismiss_notice(page)
        request = (config.prompt("thumbnail.txt")
                   + "\n\nARTICLE (excerpt, included below):\n" + article_excerpt(run_dir))
        send_text(page, request)
        log("thumbnail prompt sent")
        deadline = time.time() + timeout
        while time.time() < deadline:
            page.wait_for_timeout(5000)
            data = image_data_url(page)
            if data and data.startswith("data:image/"):
                destination = run_dir / "thumbnail.png"
                destination.write_bytes(base64.b64decode(data.split(",", 1)[1]))
                log("thumbnail saved")
                return destination
        (run_dir / "thumbnail-response.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
        raise RuntimeError("thumbnail image was not generated")
    finally:
        page.close()
