"""Batch orchestration: catalog, assets, render, upload and scheduling."""

from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from . import assets, audio_tools, catalog, chat, config, logic, render, runtime, youtube


def log(message: str) -> None:
    print(f"[pipeline] {message}", flush=True)


def _sanitize_topic(topic: str) -> str:
    topic = logic.strip_dashes(topic.strip().strip('"').strip("'"))
    return " ".join(topic.split())


def _read_queued_topics() -> list[str]:
    if not config.TOPICS.is_file():
        return []
    topics = [_sanitize_topic(line) for line in config.TOPICS.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [topic for topic in topics if not (logic.run_path(topic) / "upload.json").is_file()]


def _add_new_topics(candidates: list[str], known: list[str], chosen: list[str], count: int) -> None:
    for topic in candidates:
        topic = _sanitize_topic(topic)
        if topic and not logic.similar_topics(topic, [{"title": t} for t in known + chosen]):
            chosen.append(topic)
        if len(chosen) >= count:
            return


def prepare_topics(context, count: int, scheduled_titles: list[str] | None = None) -> list[str]:
    existing = [item.get("title", "") for item in logic.load_catalog()] + (scheduled_titles or [])
    chosen: list[str] = []
    _add_new_topics(_read_queued_topics(), existing, chosen, count)
    for _ in range(3):
        if len(chosen) >= count:
            break
        generated = chat.generate_topics(context, count - len(chosen) + 2, existing + chosen)
        _add_new_topics(generated, existing, chosen, count)
    if len(chosen) < count:
        raise RuntimeError(f"only {len(chosen)} unique topics available, requested {count}")
    return chosen[:count]


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


def _summary(topics: list[str]) -> None:
    lines = ["", "=== batch summary ==="]
    for topic in topics:
        run_dir = logic.run_path(topic)
        record_path = run_dir / "record.json"
        data = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {}
        lines.append(f"- {topic}: slot={data.get('slot', '?')} video={data.get('video', '?')}")
    print("\n".join(lines), flush=True)


def run_batch(count: int) -> list[str]:
    if not (config.PROFILE / "Default" / "Cookies").is_file():
        runtime.setup_profile()
    runtime.start_hidden_chrome()
    failures = []
    with sync_playwright() as playwright:
        browser, context = runtime.connect_hidden(playwright)
        runtime.configure_downloads(browser)
        runtime.configure_extension(context)
        catalog_data = logic.load_catalog()
        if not catalog_data:
            catalog_data = catalog.scrape_public_catalog(context)
        catalog.write_catalog_markdown(catalog_data)
        studio_payload = catalog.fetch_creator_videos(context)
        scheduled_titles = [item.get("title", "") for item in catalog.studio_videos(studio_payload)]
        topics = prepare_topics(context, count, scheduled_titles)
        log(f"topics: {topics}")
        for topic in topics:
            try:
                asset_stage(context, topic)
            except Exception as error:
                run_dir = logic.run_path(topic)
                run_dir.mkdir(parents=True, exist_ok=True)
                logic.record_event(run_dir, "assets", "error", str(error))
                failures.append((topic, str(error)))
                log(f"asset failure for {topic}: {error}")

    with sync_playwright() as playwright:
        browser, upload_context = runtime.connect_hidden(playwright)
        occupied = logic.scheduled_slots(studio_payload)
        slots = logic.next_slots(len(topics), occupied)
        log(f"planned slots: {[logic.slot_label(slot) for slot in slots]}")
        for topic, slot in zip(topics, slots):
            try:
                upload_stage(upload_context, topic, slot)
            except Exception as error:
                run_dir = logic.run_path(topic)
                logic.record_event(run_dir, "upload", "error", str(error))
                failures.append((topic, str(error)))
                log(f"upload failure for {topic}: {error}")
    logic.write_records_markdown()
    _summary(topics)
    if failures:
        log(f"{len(failures)} failure(s): {failures}")
    return failures
