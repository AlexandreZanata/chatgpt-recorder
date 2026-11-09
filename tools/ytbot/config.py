"""Paths, prompts and channel constants for the YouTube automation bot."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".local" / "ytbot"
LEGACY_PROFILE = ROOT / ".local" / "bot" / "profile"
PROFILE = LEGACY_PROFILE if LEGACY_PROFILE.is_dir() else DATA / "profile"
DOWNLOADS = DATA / "downloads"
RUNS = DATA / "runs"
RECORDS = DATA / "records"
CATALOG = DATA / "catalog.json"
TOPICS = DATA / "topics.txt"
PROMPTS = Path(__file__).resolve().parent / "prompts"

GPT_URL = "https://chatgpt.com/g/g-6a7b133f83a48191adc2138982ee98d8-simple-deep-dive"
CHANNEL_HANDLE = "https://www.youtube.com/@fallemprince/videos"
CHANNEL_ID = "UCc288lF54UDCCGhTKIkr7BQ"
STUDIO_UPLOAD = f"https://studio.youtube.com/channel/{CHANNEL_ID}/videos/upload"
STUDIO_EDIT = "https://studio.youtube.com/video/{video_id}/edit"
STUDIO_LOGIN = "https://studio.youtube.com/"
MAIN_CHROME = Path("/home/iiii/.config/google-chrome/Default")
MAIN_LOCAL_STATE = Path("/home/iiii/.config/google-chrome/Local State")
EXT_ID = "hppbbbakngelcnbjhfioognjklbdnphe"
EXT_PATH = ROOT / "dist" / "chrome"
DISPLAY = ":99"
CDP_PORT = 9300
TIMEZONE = "America/Cuiaba"
SLOT_HOURS = (0, 12)
TAG_LIMIT = 425
MIN_LEAD_MINUTES = 60

THUMBNAIL_THEME = "fallem_prince"
NARRATION_VOLUME = 2.0
PRESET = "YouTube Standard (16:9)"
VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS = 1920, 1080, 30
QUICK_OUTRO_SECONDS = 5.0


def prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8").strip()
