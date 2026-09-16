"""Semantic Scene Planner: adaptive chunking, Visual Bible, and single-pass manifest generation."""

import hashlib
import json
import re
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request

from src.core.motion_renderer import assign_random_motions

_DISCOURSE_MARKERS = {
    "mas", "porem", "porém", "contudo", "entretanto", "no entanto", "however", "meanwhile", "therefore", "furthermore", "suddenly", "next"
}
_HUMAN_KW = ("homem", "mulher", "pessoa", "orac", "oraç", "rez", "samarit", "jesus", "cristo", "man", "woman", "person", "prayer", "pray")


_THEME_BIBLES = {
    "deep black": {
        "master_theme": "deep black",
        "camera_lens": "hand-drawn 2D animation keyframe, precise graphic novel inkwork, layered cinematic composition",
        "lighting": "stark chiaroscuro contrast, deep inky black shadows, crisp white highlights, intentional negative space",
        "color_palette": "pure monochrome black and white ink, zero color, consistent line weight, fine paper texture",
        "negative_prompt": "photorealistic, hyperrealistic, realistic photo, human photograph, realistic skin, 3d render, cgi, color, sepia, grey wash, blurry, soft, muddy lines, uneven line weight, text, watermark",
        "prefix": "premium black and white animated ink illustration, coherent graphic novel art direction,"
    },
    "agro zaflas": {
        "master_theme": "agro zaflas",
        "camera_lens": "Hasselblad 35mm f/4 editorial photograph, sharp natural textures, layered foreground and horizon",
        "lighting": "golden hour sunlight, atmospheric morning rays, realistic soft shadows, controlled highlights",
        "color_palette": "true-to-life agricultural greens, golden fields, fertile earth, clean blue sky, subtle film grade",
        "negative_prompt": "black and white, monochrome, dark, gloomy, cartoon, 3d render, illustration, drawing, sketch, text, watermark, logo, blurry, distorted, chaotic clutter, overprocessed, oversaturated, plastic texture",
        "prefix": "premium minimalist agribusiness editorial photography, precise commercial art direction,"
    },
    "religiao primium word": {
        "master_theme": "religião primium word",
        "camera_lens": "ARRI Alexa 35 film still, anamorphic 35mm lens, layered foreground midground and horizon, restrained composition",
        "lighting": "natural golden sunrise, atmospheric volumetric sunbeams, soft highlight rolloff, realistic warm divine glow",
        "color_palette": "warm amber and golden tones, muted teal shadows, rich natural earth, tranquil sky, subtle fine film grain",
        "negative_prompt": "crowd, deformed hands, extra fingers, mutated limbs, duplicate person, cross-eyed, artificial halo, kitsch, fantasy spectacle, messy clutter, cartoon, 3d render, cgi, illustration, plastic skin, oversaturated, overprocessed, text, watermark, blurry",
        "prefix": "reverent cinematic landscape photography, sacred natural grandeur, quiet contemplative atmosphere,"
    }
}


def build_visual_bible(theme: str) -> Dict[str, str]:
    """Generate master Visual Bible defining coherent aesthetic identity for all scenes."""
    t_low = theme.lower().strip().replace("ã", "a")
    for key, val in _THEME_BIBLES.items():
        if key in t_low or ("religi" in key and "religi" in t_low):
            return val
    return {
        "master_theme": theme.strip() or "Cinematic documentary photography, photorealistic masterpiece",
        "camera_lens": "50mm prime lens, f/2.0 aperture, cinematic composition, sharp focus, 8k",
        "lighting": "natural volumetric lighting, soft directional highlights, deep balanced shadows",
        "color_palette": "photorealistic, subtle warm tones, rich textures, 35mm film still look",
        "negative_prompt": "cartoon, 3d render, anime, illustration, text, watermark, blurry, deformed limbs, oversaturated",
        "prefix": f"{theme.strip() or 'Cinematic'}. Cinematic photography of"
    }


def translate_to_english_prompt(text: str) -> str:
    """Translate or adapt excerpt into an English visual prompt for CLIP."""
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return "dynamic cinematic moment"
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q=" + urllib.parse.quote(clean)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            trans = "".join([p[0] for p in data[0] if p[0]]).strip()
            return re.sub(r"[^a-zA-Z0-9\s,.-]", "", trans)[:100]
    except Exception:
        return re.sub(r"[^a-zA-Z0-9\s,.-]", "", clean)[:100]


def is_semantic_split_point(text: str, pause_sec: float, elapsed_sec: float, min_dur: float) -> bool:
    """Determine whether a candidate segment transition constitutes a natural semantic break."""
    if elapsed_sec < min_dur:
        return False
    if pause_sec >= 0.70 or any(text.rstrip().endswith(punct) for punct in [".", "!", "?", "..."]):
        return True
    first_word = re.sub(r"[^\w\s]", "", text.split()[0].lower()) if text.split() else ""
    return first_word in _DISCOURSE_MARKERS


def _plan_interval_scenes(
    total_dur: float,
    transcript_segments: List[Dict[str, Any]],
    bible: Dict[str, str],
    interval_sec: float
) -> List[Dict[str, Any]]:
    """Partition audio into consistent duration intervals mapped to spoken transcript."""
    scenes = []
    curr = 0.0
    idx = 1
    while curr < total_dur:
        end = min(total_dur, curr + interval_sec)
        if total_dur - end < 10.0:
            end = total_dur
        texts = [
            s.get("text", "").strip() for s in transcript_segments
            if s.get("start", 0.0) < end and s.get("end", 0.0) > curr
        ]
        combined = " ".join([t for t in texts if t]).strip() or f"Visual scene sequence {idx}"
        scenes.append(_create_scene_entry(idx, curr, end, combined, bible))
        curr = end
        idx += 1
    return assign_random_motions(scenes)


def plan_adaptive_scenes(
    total_duration_sec: float,
    transcript_segments: List[Dict[str, Any]],
    theme: str = "deep black",
    is_short: bool = False,
    interval_sec: Optional[float] = 30.0
) -> Dict[str, Any]:
    """Plan scenes adaptively or by fixed intervals based on speech and constraints."""
    bible = build_visual_bible(theme)
    if interval_sec and interval_sec > 0:
        scenes = _plan_interval_scenes(total_duration_sec, transcript_segments, bible, interval_sec)
        return {"total_duration": round(total_duration_sec, 2), "visual_bible": bible, "scenes": scenes}

    min_dur = 3.5 if is_short else 12.0
    max_dur = 8.5 if is_short else 32.0

    if not transcript_segments:
        return _fallback_uniform_scenes(total_duration_sec, bible, min_dur, max_dur)

    scenes: List[Dict[str, Any]] = []
    chunk_texts: List[str] = []
    chunk_start, last_end = 0.0, 0.0

    for seg in transcript_segments:
        start, end = seg.get("start", 0.0), seg.get("end", 0.0)
        text = seg.get("text", "").strip()
        pause = max(0.0, start - last_end)
        elapsed = end - chunk_start

        if chunk_texts and (elapsed >= max_dur or is_semantic_split_point(text, pause, elapsed, min_dur)):
            combined = " ".join(chunk_texts).strip()
            scenes.append(_create_scene_entry(len(scenes) + 1, chunk_start, last_end, combined, bible))
            chunk_texts = [text]
            chunk_start = start
        else:
            chunk_texts.append(text)
        last_end = end

    if chunk_texts:
        combined = " ".join(chunk_texts).strip()
        scenes.append(_create_scene_entry(len(scenes) + 1, chunk_start, total_duration_sec, combined, bible))

    return {"total_duration": round(total_duration_sec, 2), "visual_bible": bible, "scenes": assign_random_motions(scenes)}


def _create_scene_entry(scene_idx: int, start: float, end: float, text: str, bible: Dict[str, str]) -> Dict[str, Any]:
    """Format single scene entry with deterministic seed and translated English prompt."""
    dur = max(1.0, round(end - start, 2))
    clean_text = re.sub(r"\s+", " ", text).strip()
    en_desc = translate_to_english_prompt(clean_text)

    prefix = bible.get("prefix", f"{bible.get('master_theme', 'Cinematic')}. Cinematic photography of")
    if "religi" in bible.get("master_theme", "").lower() and any(k in clean_text.lower() for k in _HUMAN_KW):
        prefix = "reverent cinematic film still, solitary figure in quiet prayer within vast sacred nature, understated human scale,"

    prompt = f"{prefix} {en_desc}. {bible['camera_lens']}, {bible['lighting']}, {bible['color_palette']}"
    seed = int(hashlib.sha256(f"{clean_text}_{scene_idx}".encode()).hexdigest()[:8], 16) % (2**31 - 1)

    return {
        "scene_index": scene_idx, "start_sec": round(start, 2), "end_sec": round(end, 2),
        "duration_sec": dur, "excerpt": clean_text[:140], "prompt": prompt,
        "seed": seed, "motion_type": "zoom_in_center"
    }


def _fallback_uniform_scenes(total_dur: float, bible: Dict[str, str], min_dur: float, max_dur: float) -> Dict[str, Any]:
    """Generate uniform pacing when transcript segments are absent."""
    step, scenes, curr, idx = (min_dur + max_dur) / 2.0, [], 0.0, 1
    while curr < total_dur:
        scenes.append(_create_scene_entry(idx, curr, min(total_dur, curr + step), f"Visual scene sequence {idx}", bible))
        curr, idx = min(total_dur, curr + step), idx + 1
    return {"total_duration": round(total_dur, 2), "visual_bible": bible, "scenes": assign_random_motions(scenes)}


def clean_narrative_excerpt(text: str) -> str:
    """Clean and summarize speech excerpt for AI image generation."""
    c = re.sub(r"[^a-zA-Z0-9\s,.-]", "", re.sub(r"\s+", " ", text).strip())
    return c[:160] if c else "dynamic scene moment"


def plan_scenes_from_duration(total_duration_sec: float, interval_sec: float = 60.0, master_theme: str = "Cinematic Miami Luxury, 8k resolution, photorealistic", transcript_segments: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Backwards-compatible uniform scene generator."""
    scenes, curr, idx = [], 0.0, 1
    while curr < total_duration_sec:
        end_t = min(curr + interval_sec, total_duration_sec)
        scenes.append({"scene_index": idx, "start_sec": round(curr, 2), "end_sec": round(end_t, 2), "duration_sec": round(end_t - curr, 2), "excerpt": f"Scene {idx}", "prompt": f"A vivid cinematic photograph. Theme: {master_theme}", "image_path": ""})
        curr, idx = end_t, idx + 1
    return scenes
