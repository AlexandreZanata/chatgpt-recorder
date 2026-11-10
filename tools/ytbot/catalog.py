"""Channel catalog and YouTube Studio schedule discovery."""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import config, logic


def scrape_public_catalog(context) -> list[dict]:
    page = context.new_page()
    videos: dict[str, dict] = {}
    try:
        page.goto(config.CHANNEL_HANDLE, timeout=90000)
        page.wait_for_timeout(8000)
        for _ in range(80):
            found = page.evaluate(
                """() => {
                  const map = {};
                  for (const a of document.querySelectorAll('a[href*="/watch?v="]')) {
                    const id = new URL(a.href).searchParams.get('v');
                    if (!id) continue;
                    if (!map[id]) map[id] = {id, title: '', duration: ''};
                    const text = (a.innerText || '').trim();
                    if ((a.className || '').toString().includes('Title') && text) map[id].title = text;
                    if (/^\\d+:\\d{2}(:\\d{2})?$/.test(text)) map[id].duration = text;
                  }
                  return Object.values(map);
                }"""
            )
            before = len(videos)
            for item in found:
                if item["title"]:
                    videos.setdefault(item["id"], {}).update(item)
            page.mouse.wheel(0, 6000)
            page.wait_for_timeout(1800)
            if len(videos) == before and _ > 3:
                break
    finally:
        page.close()
    data = sorted(videos.values(), key=lambda item: item.get("title", ""))
    config.DATA.mkdir(parents=True, exist_ok=True)
    config.CATALOG.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def fetch_creator_videos(context) -> dict:
    page = context.new_page()
    payload: dict = {}
    def on_response(response):
        if "list_creator_videos" in response.url:
            try:
                payload.setdefault("data", response.json())
            except Exception:
                pass
    page.on("response", on_response)
    try:
        page.goto(config.STUDIO_UPLOAD, timeout=90000)
        page.wait_for_timeout(10000)
        from . import runtime
        runtime.select_channel(page)
        page.wait_for_timeout(8000)
    finally:
        page.close()
    return payload.get("data", {})


def studio_videos(payload: dict) -> list[dict]:
    found: list[dict] = []
    def walk(node):
        if isinstance(node, dict):
            if node.get("videoId") and isinstance(node.get("title"), str):
                found.append({"id": node["videoId"], "title": node["title"]})
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(payload)
    return found


def load_schedule(context) -> set[tuple]:
    payload = fetch_creator_videos(context)
    return logic.scheduled_slots(payload)


def write_catalog_markdown(data: list[dict]) -> None:
    lines = ["# Channel catalog", "", f"Videos: {len(data)}", "", "| Duration | Title |", "|---|---|"]
    for item in data:
        lines.append(f"| {item.get('duration', '?')} | {item.get('title', '')} |")
    config.DATA.mkdir(parents=True, exist_ok=True)
    (config.DATA / "catalog.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def is_scheduled(context, video_id: str) -> bool:
    payload = fetch_creator_videos(context)
    found = []
    def walk(node):
        if isinstance(node, dict):
            if node.get("videoId") == video_id:
                details = node.get("scheduledPublishingDetails") or {}
                if details.get("scheduledPublishings"):
                    found.append(True)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(payload)
    return bool(found)
