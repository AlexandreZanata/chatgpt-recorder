"""Per-channel profiles for prompts, language, duration and video style."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    slug: str
    name: str
    handle: str
    channel_id: str
    prompts: str
    background: str
    language: str
    min_article_chars: int
    article_retry: str
    narration_volume: float = 2.0
    slots: tuple[int, ...] = (0, 12)


CHANNELS = {
    "fallem-prince": Channel(
        slug="fallem-prince",
        name="fallem prince",
        handle="@fallemprince",
        channel_id="UCc288lF54UDCCGhTKIkr7BQ",
        prompts="fallem_prince",
        background="fallem_prince",
        language="en",
        min_article_chars=40000,
        article_retry="Target narration length: at least 6,500 words.",
    ),
    "whispers-from-heaven": Channel(
        slug="whispers-from-heaven",
        name="Whispers From Heaven",
        handle="",
        channel_id="",
        prompts="whispers_from_heaven",
        background="whispers_from_heaven",
        language="en",
        min_article_chars=11000,
        article_retry=(
            "Target narration length: 2,200 to 2,600 words, about 15 minutes "
            "at a calm pace."
        ),
    ),
}


def get(slug: str) -> Channel:
    channel = CHANNELS.get(slug)
    if channel is None:
        options = ", ".join(sorted(CHANNELS))
        raise SystemExit(f"unknown channel: {slug}. Options: {options}")
    return channel


def apply(slug: str) -> Channel:
    from . import config
    channel = get(slug)
    config.apply_channel(channel)
    return channel
