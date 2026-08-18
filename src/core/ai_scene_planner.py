"""Scene Planner: partitions narration audio into timed blocks and builds master-themed image prompts representing each excerpt."""

from typing import Any, Dict, List
import re


def clean_narrative_excerpt(text: str) -> str:
    """Clean and summarize speech excerpt for AI image generation."""
    clean = re.sub(r"\s+", " ", text).strip()
    clean = re.sub(r"[^a-zA-Z0-9\s,.-]", "", clean)
    return clean[:160] if clean else "dynamic scene moment"


def plan_scenes_from_duration(
    total_duration_sec: float,
    interval_sec: float = 60.0,
    master_theme: str = "Cinematic Miami Luxury, 8k resolution, photorealistic",
    transcript_segments: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Plan video scenes by slicing duration and creating English prompts that visually represent each excerpt."""
    transcript_segments = transcript_segments or []
    scenes = []
    current_time = 0.0
    scene_idx = 1

    while current_time < total_duration_sec:
        start_t = current_time
        end_t = min(current_time + interval_sec, total_duration_sec)
        dur = end_t - start_t

        # Gather transcript text within this specific window
        seg_texts = [
            s.get("text", "").strip()
            for s in transcript_segments
            if s.get("start", 0.0) >= start_t and s.get("end", 0.0) <= (end_t + 1.5)
        ]
        combined_text = " ".join(seg_texts).strip()
        excerpt = clean_narrative_excerpt(combined_text) if combined_text else f"Scene {scene_idx} unfolding"

        # Explicit narrative prompt representing the spoken excerpt in English
        prompt = (
            f"A vivid cinematic photograph representing the excerpt: '{excerpt}'. "
            f"Theme: {master_theme}, highly detailed, sharp focus, 8k, photorealistic masterpiece"
        )

        scenes.append({
            "scene_index": scene_idx,
            "start_sec": round(start_t, 2),
            "end_sec": round(end_t, 2),
            "duration_sec": round(dur, 2),
            "excerpt": excerpt,
            "prompt": prompt,
            "image_path": ""
        })

        current_time = end_t
        scene_idx += 1

    return scenes
