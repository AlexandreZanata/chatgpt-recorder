"""Bounded channel/run summaries for the desktop manager and ZaturoBot adapter."""

from __future__ import annotations
import json
from . import channels, config
from .accounts_store import AccountStore


def profiles(store: AccountStore | None = None) -> list[dict]:
    store = store or AccountStore()
    bindings = store.load()["bindings"]
    result = []
    for channel in channels.CHANNELS.values():
        account_id = bindings.get(channel.slug, {}).get("account_id", "legacy")
        profile = store.profile(account_id)
        result.append(
            {
                "id": channel.slug,
                "name": channel.name,
                "channel_id": channel.channel_id,
                "account_id": account_id,
                "browser_configured": (profile / "Default").is_dir(),
            }
        )
    return result


def runs(channel: str, limit: int = 20) -> list[dict]:
    if not 1 <= limit <= 100:
        raise ValueError("run limit must be 1..100")
    channels.apply(channel)
    result = []
    # Existing channel folders are the source of truth; this is an index, not a second catalog.
    candidates = sorted(
        config.RUNS.glob("*/record.json"),
        key=lambda p: p.stat().st_mtime_ns,
        reverse=True,
    )
    for path in candidates[:limit]:
        if (
            path.is_symlink()
            or path.parent.is_symlink()
            or path.stat().st_size > 1024 * 1024
        ):
            continue
        try:
            record = json.loads(path.read_text())
            meta = path.parent / "metadata.json"
            metadata = (
                json.loads(meta.read_text())
                if meta.is_file()
                and not meta.is_symlink()
                and meta.stat().st_size <= 1024 * 1024
                else {}
            )
            upload_path = path.parent / "upload.json"
            upload = (
                json.loads(upload_path.read_text())
                if upload_path.is_file()
                and not upload_path.is_symlink()
                and upload_path.stat().st_size <= 1024 * 1024
                else {}
            )
        except (ValueError, OSError):
            continue
        stages = record.get("stages", {})
        events = (
            stages.values()
            if isinstance(stages, dict)
            else stages
            if isinstance(stages, list)
            else []
        )
        states = [v.get("status", "") for v in events if isinstance(v, dict)]
        state = (
            "scheduled"
            if upload.get("scheduled")
            else "error"
            if "error" in states
            else "ready" if "render" in stages and (path.parent / "video.mp4").is_file()
            else "in_progress"
        )
        artifacts = [
            name
            for name in (
                "thumbnail.png",
                "video.mp4",
                "narration.aac",
                "narration.webm",
                "metadata.json",
            )
            if (path.parent / name).is_file() and not (path.parent / name).is_symlink()
        ]
        result.append(
            {
                "id": path.parent.name[:160],
                "title": str(metadata.get("title", record.get("topic", "")))[:200],
                "topic": str(record.get("topic", ""))[:240],
                "state": state,
                "slot": str(upload.get("slot", record.get("slot", "")))[:40],
                "video_id": str(
                    upload.get(
                        "videoId", upload.get("video_id", record.get("video", ""))
                    )
                )[:32],
                "artifacts": artifacts,
            }
        )
    return result
