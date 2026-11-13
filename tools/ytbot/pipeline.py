"""Batch orchestration: catalog, assets, render, upload and scheduling."""

from __future__ import annotations

import json
from pathlib import Path

from . import assets, audio_tools, chat, logic, render, youtube


def log(message: str) -> None:
    print(f"[pipeline] {message}", flush=True)


def _open_conversation(context, run_dir: Path):
    record_path = run_dir / "record.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {}
    url = record.get("conversation")
    if not url:
        return None
    page = context.new_page()
    page.goto(url, timeout=90000)
    page.wait_for_timeout(8000)
    return page


def article_stage(context, topic: str) -> Path:
    run_dir = logic.run_path(topic)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "topic.txt").write_text(topic, encoding="utf-8")
    logic.set_run_field(run_dir, topic=topic)
    article = run_dir / "article.txt"
    if article.is_file() and article.stat().st_size >= config.MIN_ARTICLE_CHARS:
        return run_dir
    page = context.new_page()
    try:
        text = chat.generate_article(page, topic, run_dir)
        if len(text) < config.MIN_ARTICLE_CHARS:
            page.close()
            page = context.new_page()
            chat.generate_article(page, topic, run_dir, config.ARTICLE_RETRY)
        logic.set_run_field(run_dir, conversation=page.url)
        logic.record_event(run_dir, "article", "ok", f"{(run_dir / 'article.txt').stat().st_size} bytes")
    finally:
        page.close()
    return run_dir


def _article_audio(context, topic: str, run_dir: Path) -> None:
    narration = next((run_dir / f"narration{ext}" for ext in (".aac", ".webm") if (run_dir / f"narration{ext}").is_file()), None)
    need_article = not (run_dir / "article.txt").is_file()
    need_audio = narration is None
    if not need_article and not need_audio:
        return
    page = context.new_page() if need_article else _open_conversation(context, run_dir)
    if page is None:
        need_article = True
        page = context.new_page()
    try:
        if need_article:
            chat.generate_article(page, topic, run_dir)
            logic.set_run_field(run_dir, conversation=page.url)
            logic.record_event(run_dir, "article", "ok", f"{(run_dir / 'article.txt').stat().st_size} bytes")
        if need_audio:
            chat.capture_audio(page, context, run_dir)
            logic.record_event(run_dir, "audio", "ok")
    finally:
        page.close()


def _extra_assets(context, topic: str, run_dir: Path) -> None:
    if not (run_dir / "metadata.json").is_file():
        assets.generate_metadata(context, run_dir, topic)
        logic.record_event(run_dir, "metadata", "ok")
    if not (run_dir / "thumbnail.png").is_file():
        assets.generate_thumbnail(context, run_dir)
        logic.record_event(run_dir, "thumbnail", "ok")
    if not (run_dir / "video.mp4").is_file():
        fitted = audio_tools.fit_narration(run_dir)
        logic.record_event(run_dir, "duration", "ok", fitted.name)
        render.render_video(run_dir)
        logic.record_event(run_dir, "render", "ok")


def asset_stage(context, topic: str) -> Path:
    run_dir = logic.run_path(topic)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "topic.txt").write_text(topic, encoding="utf-8")
    logic.set_run_field(run_dir, topic=topic)
    logic.record_event(run_dir, "topic", "ok", topic)
    _article_audio(context, topic, run_dir)
    _extra_assets(context, topic, run_dir)
    return run_dir


def _finish_end_screen(context, run_dir: Path, data: dict) -> None:
    page = youtube.open_edit(context, data["videoId"])
    try:
        youtube.wait_for_checks(page)
        youtube.add_end_screen(page)
    finally:
        page.close()
    data["endScreen"] = True
    youtube.write_result(run_dir, data)


def upload_stage(context, topic: str, slot) -> None:
    run_dir = logic.run_path(topic)
    upload_path = run_dir / "upload.json"
    if upload_path.is_file():
        data = json.loads(upload_path.read_text(encoding="utf-8"))
        if not data.get("endScreen"):
            _finish_end_screen(context, run_dir, data)
        if not data.get("scheduled"):
            data = youtube.schedule_existing(context, run_dir, data, logic.slot_from_label(data.get("slot", ""), slot))
        logic.set_run_field(run_dir, slot=data.get("slot", ""), video=data.get("url", ""))
        logic.record_event(run_dir, "upload", "ok", data.get("url", "") + " at " + data.get("slot", ""))
        return
    meta = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    result = youtube.upload_and_schedule_with_context(context, run_dir, meta, slot)
    logic.set_run_field(run_dir, slot=logic.slot_label(slot), video=result["url"])
    logic.record_event(run_dir, "upload", "ok", result["url"] + " at " + result["slot"])
