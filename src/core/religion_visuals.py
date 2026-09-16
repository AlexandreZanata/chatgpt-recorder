"""Landscape-only visual prompt strategy for the premium religion theme."""

from typing import Dict, Iterable, Sequence


_MOTIF_RULES: Sequence[tuple[tuple[str, ...], tuple[str, ...]]] = (
    (
        ("road", "journey", "jerusalem", "city", "walk", "path", "estrada", "caminho", "cidade", "caminh"),
        (
            "empty ancient road through Judean hills toward a walled city",
            "desert path crossing layered mountains beneath morning clouds",
            "empty hillside trail among olive trees and weathered stones",
        ),
    ),
    (
        ("blind", "see", "sight", "heal", "mercy", "answer", "cego", "visão", "cura", "curou", "misericórdia"),
        (
            "clear spring flowing between sunlit rocks into a tranquil valley",
            "first light breaking through storm clouds over a reflective river",
            "dark valley opening toward a luminous horizon after rain",
        ),
    ),
    (
        ("faith", "hope", "heart", "pray", "trust", "believe", "fé", "esperança", "coração", "oraç", "confia", "crer"),
        (
            "mountain valley at dawn with olive grove and winding path",
            "highland lake reflecting gold beneath monumental mountains",
            "sunbeams crossing cedar forest onto an empty trail",
        ),
    ),
    (
        ("crowd", "voice", "call", "listen", "silent", "speak", "multidão", "voz", "cham", "ouvir", "silêncio", "falar"),
        (
            "windswept field beneath dramatic layered clouds",
            "narrow canyon opening toward a sunlit plain",
            "empty coastal cliff above luminous water and open sky",
        ),
    ),
    (
        ("fear", "discour", "shame", "forgotten", "pain", "dark", "medo", "desânimo", "vergonha", "esquec", "dor", "escur"),
        (
            "heavy clouds parting above a rugged sunlit valley",
            "ancient tree enduring a storm above empty highlands",
            "mist lifting from a shadowed pass toward golden horizon",
        ),
    ),
)

_DEFAULT_MOTIFS = (
    "pristine olive grove across rolling hills at sunrise",
    "quiet river through untouched mountains toward a radiant horizon",
    "weathered stone terraces above a tranquil valley",
    "monumental desert rocks in soft atmospheric light",
)


def _select_motifs(text: str) -> Iterable[str]:
    """Return the first symbolic landscape family matching the narration."""
    normalized = text.lower()
    for keywords, motifs in _MOTIF_RULES:
        if any(keyword in normalized for keyword in keywords):
            return motifs
    return _DEFAULT_MOTIFS


def build_religion_landscape_prompt(
    narrative_text: str,
    bible: Dict[str, str],
    scene_index: int,
) -> str:
    """Convert human-centered narration into an uninhabited symbolic landscape."""
    motifs = tuple(_select_motifs(narrative_text))
    motif = motifs[(max(1, scene_index) - 1) % len(motifs)]
    style = bible.get("prompt_style", "anamorphic 35mm, natural light, fine film grain")
    return (
        f"sacred cinematic landscape, {motif}. "
        "uninhabited, empty foreground, vast depth. "
        f"{style}."
    )


def build_scene_prompt(
    narrative_text: str,
    translated_text: str,
    bible: Dict[str, str],
    scene_index: int,
) -> str:
    """Build either the religion-safe landscape prompt or the original themed prompt."""
    if "religi" in bible.get("master_theme", "").lower():
        return build_religion_landscape_prompt(narrative_text, bible, scene_index)
    prefix = bible.get("prefix", f"{bible.get('master_theme', 'Cinematic')}. Cinematic photography of")
    return f"{prefix} {translated_text}. {bible['camera_lens']}, {bible['lighting']}, {bible['color_palette']}"
