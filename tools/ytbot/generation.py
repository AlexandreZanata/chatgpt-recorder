"""Generation-only reuse of the existing assets/render pipeline; never uploads or schedules."""
from __future__ import annotations
from . import config, logic, runtime, topics, pipeline


def run_generation(count, context):
    if not 1 <= count <= 10:
        raise ValueError("generation count must be 1..10")
    existing = []
    for path in sorted(config.RUNS.glob("*/metadata.json")):
        if path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024 * 1024:
            import json
            try:
                existing.append(str(json.loads(path.read_text()).get("title", "")))
            except (ValueError, OSError):
                continue
    selected = topics.prepare_topics(context, count, existing)
    failures = []
    for topic in selected:
        try:
            directory = pipeline.asset_stage(context, topic)
            if not (directory / "video.mp4").is_file():
                raise ValueError("rendered video missing")
            logic.record_event(directory, "ready", "ok")
        except Exception:
            failures.append(topic)
    logic.write_records_markdown()
    return failures
