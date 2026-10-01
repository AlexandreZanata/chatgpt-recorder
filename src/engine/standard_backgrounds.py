"""Bundled seamless backgrounds used only by Standard video mode."""

from pathlib import Path

BACKGROUND_DIR = Path(__file__).resolve().parents[2] / "assets" / "backgrounds"
BACKGROUND_THEMES = {
    "religious": ("Catholic Renaissance · golden particles", "religious_particles.mp4"),
    "black": ("Enigmatic black · white particles", "enigmatic_black.mp4"),
    "agro": ("Zaflas Agro · golden fields and pollen", "zaflas_agro.mp4"),
    "fallem_prince": ("fallem prince · monochrome engraving", "fallem_prince.mp4"),
}
PORTRAIT_BACKGROUND_FILES = {
    theme: f"{Path(filename).stem}_shorts.mp4"
    for theme, (_, filename) in BACKGROUND_THEMES.items()
}


def resolve_standard_background(image_path: Path, theme: str = "",
                                portrait: bool = False) -> tuple[Path, bool]:
    """A selected loop overrides the image; no selection preserves the still image."""
    if not theme:
        return image_path, False
    if theme not in BACKGROUND_THEMES:
        raise ValueError(f"Unknown Standard background theme: {theme}")
    filename = PORTRAIT_BACKGROUND_FILES[theme] if portrait else BACKGROUND_THEMES[theme][1]
    path = BACKGROUND_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Bundled background is missing: {path}")
    return path, True
