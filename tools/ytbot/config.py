"""Paths, prompts and channel constants for the YouTube automation bot."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".local" / "ytbot"
LEGACY_PROFILE = ROOT / ".local" / "bot" / "profile"
PROFILE = LEGACY_PROFILE if LEGACY_PROFILE.is_dir() else DATA / "profile"
DOWNLOADS = DATA / "downloads"
DATA_DIR = DATA
RUNS = DATA_DIR / "runs"
RECORDS = DATA_DIR / "records"
CATALOG = DATA_DIR / "catalog.json"
TOPICS = DATA_DIR / "topics.txt"
PROMPTS_ROOT = Path(__file__).resolve().parent / "prompts"
PROMPTS = PROMPTS_ROOT / "fallem_prince"

GPT_URL = "https://chatgpt.com/g/g-6a7b133f83a48191adc2138982ee98d8-simple-deep-dive"
CHANNEL = None
CHANNEL_NAME = "fallem prince"
CHANNEL_HANDLE = "https://www.youtube.com/@fallemprince/videos"
CHANNEL_ID = "UCc288lF54UDCCGhTKIkr7BQ"
STUDIO_UPLOAD = f"https://studio.youtube.com/channel/{CHANNEL_ID}/videos/upload"
STUDIO_EDIT = "https://studio.youtube.com/video/{video_id}/edit"
STUDIO_LOGIN = "https://studio.youtube.com/"
MAIN_CHROME = Path.home() / ".config" / "google-chrome" / "Default"
MAIN_LOCAL_STATE = Path.home() / ".config" / "google-chrome" / "Local State"
EXT_PATH = ROOT / "dist" / "chrome"
EXT_ID = "".join(
    chr(ord("a") + int(digit, 16))
    for digit in hashlib.sha256(str(EXT_PATH).encode("utf-8")).hexdigest()[:32]
)
DISPLAY = ":99"
CDP_PORT = 9300
ACCOUNT_ID = "legacy"
BROWSER_MODE = "system"
TIMEZONE = "America/Cuiaba"
SLOT_HOURS = (0, 12)
TAG_LIMIT = 425
MIN_LEAD_MINUTES = 60

THUMBNAIL_THEME = "fallem_prince"
NARRATION_VOLUME = 2.0
MIN_ARTICLE_CHARS = 40000
ARTICLE_RETRY = "Target narration length: at least 6,500 words."
PRESET = "YouTube Standard (16:9)"
VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS = 1920, 1080, 30
QUICK_OUTRO_SECONDS = 5.0


def apply_channel(channel) -> None:
    global CHANNEL, CHANNEL_NAME, CHANNEL_HANDLE, CHANNEL_ID, STUDIO_UPLOAD
    global PROMPTS, THUMBNAIL_THEME, NARRATION_VOLUME, MIN_ARTICLE_CHARS
    global ARTICLE_RETRY, SLOT_HOURS, DATA_DIR, RUNS, RECORDS, CATALOG, TOPICS
    CHANNEL = channel
    CHANNEL_NAME = channel.name
    CHANNEL_ID = channel.channel_id
    CHANNEL_HANDLE = (
        f"https://www.youtube.com/{channel.handle}/videos" if channel.handle else ""
    )
    STUDIO_UPLOAD = (
        f"https://studio.youtube.com/channel/{CHANNEL_ID}/videos/upload"
        if CHANNEL_ID
        else "https://studio.youtube.com/"
    )
    DATA_DIR = (
        DATA if channel.slug == "fallem-prince" else DATA / "channels" / channel.slug
    )
    RUNS = DATA_DIR / "runs"
    RECORDS = DATA_DIR / "records"
    CATALOG = DATA_DIR / "catalog.json"
    TOPICS = DATA_DIR / "topics.txt"
    PROMPTS = PROMPTS_ROOT / channel.prompts
    THUMBNAIL_THEME = channel.background
    NARRATION_VOLUME = channel.narration_volume
    MIN_ARTICLE_CHARS = channel.min_article_chars
    ARTICLE_RETRY = channel.article_retry
    SLOT_HOURS = channel.slots


def set_channel_id(channel_id: str) -> None:
    global CHANNEL_ID, STUDIO_UPLOAD
    CHANNEL_ID = channel_id
    STUDIO_UPLOAD = f"https://studio.youtube.com/channel/{channel_id}/videos/upload"


def prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8").strip()


def configure_timezone() -> None:
    """Apply the existing channel scheduling timezone inside this process, not the OS."""
    import os
    import time

    os.environ["TZ"] = TIMEZONE
    time.tzset()
