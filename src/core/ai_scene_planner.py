"""Scene Planner: partitions narration audio into timed blocks and builds master-themed image prompts."""

from typing import Any, Dict, List
import re


def sanitize_prompt_keywords(text: str) -> str:
    """Extract clean descriptive words from transcript text."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    words = [w.lower() for w in clean.split() if len(w) > 3]
    # Remove common stop words
    stop = {"this", "that", "with", "from", "have", "they", "will", "would", "there", "about"}
    filtered = [w for w in words if w not in stop]
    return ", ".join(filtered[:8]) if filtered else "dynamic scene, high detail"


def plan_scenes_from_duration(
    total_duration_sec: float,
    interval_sec: float = 60.0,
    master_theme: str = "Cinematic Miami Luxury, 8k resolution, photorealistic",
    transcript_segments: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Plan video scenes by slicing total duration into intervals with tailored prompts."""
    transcript_segments = transcript_segments or []
    scenes = []
    current_time = 0.0
    scene_idx = 1

    while current_time < total_duration_sec:
        start_t = current_time
        end_t = min(current_time + interval_sec, total_duration_sec)
        dur = end_t - start_t

        # Gather transcript text within this window
        seg_texts = [
            s.get("text", "").strip()
            for s in transcript_segments
            if s.get("start", 0.0) >= start_t and s.get("end", 0.0) <= (end_t + 2.0)
        ]
        combined_text = " ".join(seg_texts).strip()
        keywords = sanitize_prompt_keywords(combined_text) if combined_text else f"scene {scene_idx}"

        prompt = f"{master_theme}, depicting {keywords}, cinematic composition, 8k"
        scenes.append({
            "scene_index": scene_idx,
            "start_sec": round(start_t, 2),
            "end_sec": round(end_t, 2),
            "duration_sec": round(dur, 2),
            "summary_text": combined_text[:120] if combined_text else f"Section {scene_idx}",
            "prompt": prompt,
            "image_path": ""
        })

        current_time = end_t
        scene_idx += 1

    return scenes
