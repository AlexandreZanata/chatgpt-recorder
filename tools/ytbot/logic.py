"""Pure text, scheduling and record helpers for the YouTube bot."""

from __future__ import annotations

import difflib
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from . import config

MONTHS = {
    1: "jan.", 2: "fev.", 3: "mar.", 4: "abr.", 5: "mai.", 6: "jun.",
    7: "jul.", 8: "ago.", 9: "set.", 10: "out.", 11: "nov.", 12: "dez.",
}
STOPWORDS = {
    "the", "of", "how", "why", "what", "a", "an", "to", "in", "and", "for",
    "with", "is", "are", "our", "you", "your", "we", "us", "do", "does", "on",
}


def slug(text: str, limit: int = 70) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (value[:limit].rstrip("-") or "topic")


def strip_dashes(text: str, title: bool = False) -> str:
    replacement = ": " if title else ", "
    text = re.sub(r"\s*[—–]\s*", replacement, text)
    text = re.sub(r"\s+([,;:.!?])", r"\1", text)
    text = re.sub(r"\s*,\s*,+", ", ", text)
    text = re.sub(r"\s*,\s*\.", ".", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def parse_metadata(text: str) -> dict:
    titles = re.findall(r"^\s*\d+\.\s*(.+)$", text, re.M)
    title = strip_dashes(titles[0].strip(), title=True) if titles else "Untitled"
    match = re.search(r"DESCRIPTION:\s*(.*?)(?:\n\s*\\?#|\n\s*TAGS:)", text, re.S | re.I)
    description = strip_dashes(match.group(1).strip()) if match else ""
    hashtags = " ".join(
        line.replace("\\#", "#").strip().lower()
        for line in text.splitlines() if line.strip().startswith(("#", "\\#"))
    )
    hashtags = re.sub(r"[—–]", "", hashtags)
    tags_match = re.search(r"TAGS:\s*(.+)", text, re.S | re.I)
    tags = []
    if tags_match:
        for tag in tags_match.group(1).split(","):
            tag = strip_dashes(tag.strip().lstrip("#"))
            if tag:
                tags.append(tag)
    limited, total = [], 0
    for tag in tags:
        if total + len(tag) + 2 > config.TAG_LIMIT:
            continue
        limited.append(tag)
        total += len(tag) + 2
    tags_text = ", ".join(limited)
    full_description = description + "\n\n" + hashtags
    if tags_text:
        full_description += "\n\nTAGS: " + tags_text
    return {
        "title": title,
        "description": full_description.strip(),
        "hashtags": hashtags,
        "tags": tags_text,
    }


def _walk_scheduled(node, found: list) -> None:
    if isinstance(node, dict):
        details = node.get("scheduledPublishingDetails")
        if isinstance(details, dict):
            found.extend(details.get("scheduledPublishings", []))
        for value in node.values():
            _walk_scheduled(value, found)
    elif isinstance(node, list):
        for value in node:
            _walk_scheduled(value, found)


def scheduled_slots(payload: dict) -> set[tuple[date, int]]:
    entries: list = []
    _walk_scheduled(payload, entries)
    slots = set()
    for entry in entries:
        try:
            moment = datetime.fromtimestamp(int(entry["scheduledTimeSeconds"]))
        except (KeyError, TypeError, ValueError, OSError):
            continue
        if moment.hour in config.SLOT_HOURS and moment.minute == 0:
            slots.add((moment.date(), moment.hour))
    return slots


def next_slots(count: int, occupied: set[tuple[date, int]], start: datetime | None = None,
               lead_minutes: int = config.MIN_LEAD_MINUTES) -> list[datetime]:
    now = start or datetime.now()
    earliest = now + timedelta(minutes=lead_minutes)
    chosen: list[datetime] = []
    day = earliest.date()
    while len(chosen) < count and day < earliest.date() + timedelta(days=120):
        for hour in config.SLOT_HOURS:
            moment = datetime.combine(day, datetime.min.time()).replace(hour=hour)
            if moment < earliest or (day, hour) in occupied:
                continue
            chosen.append(moment)
            if len(chosen) == count:
                break
        day += timedelta(days=1)
    return chosen


def format_pt_date(value: date) -> str:
    return f"{value.day} de {MONTHS[value.month]} de {value.year}"


def slot_label(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


def meaningful_words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOPWORDS}


def similar_topics(topic: str, catalog: list[dict]) -> list[str]:
    words = meaningful_words(topic)
    matches = []
    for item in catalog:
        title = item.get("title", "")
        ratio = difflib.SequenceMatcher(None, topic.lower(), title.lower()).ratio()
        overlap = len(words & meaningful_words(title)) / max(1, len(words))
        if ratio >= 0.76 or overlap >= 0.75:
            matches.append(title)
    return matches


def load_catalog() -> list[dict]:
    if not config.CATALOG.is_file():
        return []
    return json.loads(config.CATALOG.read_text(encoding="utf-8"))


def run_path(topic: str) -> Path:
    return config.RUNS / slug(topic)


def record_event(run_dir: Path, stage: str, status: str, detail: str = "") -> None:
    config.RECORDS.mkdir(parents=True, exist_ok=True)
    entry = {"at": datetime.now().isoformat(timespec="seconds"), "stage": stage,
             "status": status, "detail": detail}
    with (config.RECORDS / "records.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
    record_path = run_dir / "record.json"
    data = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {}
    data.setdefault("stages", []).append(entry)
    record_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def set_run_field(run_dir: Path, **fields) -> None:
    record_path = run_dir / "record.json"
    data = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {}
    data.update(fields)
    record_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_records_markdown() -> None:
    config.RECORDS.mkdir(parents=True, exist_ok=True)
    lines = ["# YouTube bot records", "", "| Topic | Slot | Video | Stages |", "|---|---|---|---|"]
    for record_path in sorted(config.RUNS.glob("*/record.json")):
        data = json.loads(record_path.read_text(encoding="utf-8"))
        stages = ", ".join(sorted({s.get("stage", "") for s in data.get("stages", [])}))
        lines.append(f"| {data.get('topic', record_path.parent.name)} | {data.get('slot', '')} | "
                     f"{data.get('video', '')} | {stages} |")
    (config.RECORDS / "RECORDS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
