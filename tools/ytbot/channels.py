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
    "zaflas": Channel(
        slug="zaflas",
        name="Zaflas",
        handle="@zaflas",
        channel_id="UCi2aftoK7vlS3A6OozMHXKg",
        prompts="zaflas_agro",
        background="agro",
        language="pt-BR",
        min_article_chars=40000,
        article_retry=(
            "Target narration length: 6,000 to 7,200 Brazilian Portuguese words, "
            "about 30 minutes at the channel's narration pace. Preserve the "
            "fixed Zaflas Agro opening identification and final sign-off."
        ),
    ),
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
        handle="@WhispersFromHeaven1",
        channel_id="UCEE9qAtucy5OZcjvcyytu4w",
        prompts="whispers_from_heaven",
        background="whispers_from_heaven",
        language="en",
        min_article_chars=13000,
        article_retry=(
            "Target narration length: 2,600 to 3,200 words, about 17 to 20 "
            "minutes at a calm pace."
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
