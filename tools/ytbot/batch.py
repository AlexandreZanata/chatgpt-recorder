"""Parallel batch orchestration for the YouTube bot."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from playwright.sync_api import sync_playwright

from . import account, catalog, config, logic, pipeline, runtime
from .topics import prepare_topics


def log(message: str) -> None:
    print(f"[batch] {message}", flush=True)


def _local_state() -> tuple[set[tuple], list[str]]:
    occupied: set[tuple] = set()
    titles: list[str] = []
    for upload_path in config.RUNS.glob("*/upload.json"):
        data = json.loads(upload_path.read_text(encoding="utf-8"))
        if data.get("scheduled"):
            slot = logic.slot_from_label(data.get("slot", ""), None)
            if slot:
                occupied.add((slot.date(), slot.hour))
        meta_path = upload_path.parent / "metadata.json"
        if meta_path.is_file():
            titles.append(json.loads(meta_path.read_text(encoding="utf-8")).get("title", ""))
    return occupied, titles


def _asset_worker(topic: str) -> None:
    with sync_playwright() as playwright:
        _browser, context = runtime.connect_hidden(playwright)
        pipeline.asset_stage(context, topic)


def _record_asset_failure(topic: str, error: Exception, failures: list) -> None:
    run_dir = logic.run_path(topic)
    run_dir.mkdir(parents=True, exist_ok=True)
    logic.record_event(run_dir, "assets", "error", str(error))
    failures.append((topic, str(error)))
    log(f"asset failure for {topic}: {error}")


def _asset_phase(context, topics: list[str], parallel: int) -> list:
    failures: list = []
    if parallel <= 1:
        for topic in topics:
            try:
                pipeline.asset_stage(context, topic)
            except Exception as error:
                _record_asset_failure(topic, error, failures)
        return failures
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {pool.submit(_asset_worker, topic): topic for topic in topics}
        for future, topic in futures.items():
            try:
                future.result()
            except Exception as error:
                _record_asset_failure(topic, error, failures)
    return failures


def _summary(topics: list[str]) -> None:
    lines = ["", "=== batch summary ==="]
    for topic in topics:
        record_path = logic.run_path(topic) / "record.json"
        data = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {}
        lines.append(f"- {topic}: slot={data.get('slot', '?')} video={data.get('video', '?')}")
    print("\n".join(lines), flush=True)


def _refresh_catalog(context) -> None:
    data = logic.load_catalog()
    if not data and config.CHANNEL_HANDLE:
        data = catalog.scrape_public_catalog(context)
    if data:
        catalog.write_catalog_markdown(data)


def _upload_context(playwright, context, upload_cdp):
    if not upload_cdp:
        return context
    browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{upload_cdp}")
    upload_context = browser.contexts[0]
    account.ensure_channel(upload_context)
    return upload_context


def run_batch(count: int, parallel: int = 0, upload_cdp: int | None = None) -> list:
    if not (config.PROFILE / "Default" / "Cookies").is_file():
        runtime.setup_profile()
    runtime.start_hidden_chrome()
    failures: list = []
    with sync_playwright() as playwright:
        browser, context = runtime.connect_hidden(playwright)
        runtime.configure_downloads(browser)
        runtime.configure_extension(context)
        account.ensure_channel(context)
        _refresh_catalog(context)
        upload_context = _upload_context(playwright, context, upload_cdp)
        studio_payload = catalog.fetch_creator_videos(upload_context)
        local_occupied, local_titles = _local_state()
        scheduled_titles = [item.get("title", "") for item in catalog.studio_videos(studio_payload)] + local_titles
        occupied = logic.scheduled_slots(studio_payload) | local_occupied
        topics = prepare_topics(context, count, scheduled_titles)
        slots = logic.next_slots(len(topics), occupied)
        workers = parallel if parallel > 0 else len(topics)
        log(f"topics: {topics}")
        log(f"tabs: {workers}, slots: {[logic.slot_label(slot) for slot in slots]}")
        failures += _asset_phase(context, topics, workers)
        for topic, slot in zip(topics, slots):
            try:
                pipeline.upload_stage(upload_context, topic, slot)
            except Exception as error:
                logic.record_event(logic.run_path(topic), "upload", "error", str(error))
                failures.append((topic, str(error)))
                log(f"upload failure for {topic}: {error}")
    logic.write_records_markdown()
    _summary(topics)
    if failures:
        log(f"{len(failures)} failure(s): {failures}")
    return failures
