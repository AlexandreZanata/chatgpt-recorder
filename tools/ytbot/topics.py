"""Topic selection and generation for the YouTube bot."""

from __future__ import annotations

from . import chat, config, logic


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
