"""Translate unchanged desktop mode fields into the existing render workers."""

from pathlib import Path

from src.core.auto_story_worker import AutoStoryWorker
from src.core.standard_video_worker import RenderWorker
from src.engine.standard_backgrounds import resolve_standard_background
from src.ui.standard_controls import selected_standard_theme


def make_standard_worker(fields, no_bgm, quick_outro, output):
    image = Path(fields["in_img"].text().strip())
    narration = Path(fields["in_narr"].text().strip())
    theme = selected_standard_theme(fields)
    portrait = fields["preset"].currentText() == "YouTube Shorts / Reels (9:16)"
    background, _ = resolve_standard_background(image, theme, portrait=portrait)
    if not background.is_file() or not narration.is_file():
        raise ValueError("Select valid narration and a background image or particle theme.")
    has_music = not no_bgm and bool(fields["in_bgm"].text().strip())
    music = Path(fields["in_bgm"].text().strip()) if has_music else None
    return RenderWorker(
        image, narration, music, Path(output), fields["s_narr"].value() / 100.0,
        fields["s_music"].value() / 100.0, fields["preset"].currentText(),
        quick_outro=quick_outro, has_subtitles=fields["subtitles"].isChecked(), background_theme=theme,
    )


def make_story_worker(fields, output):
    narration = Path(fields["in_narr"].text().strip())
    if not narration.is_file():
        raise ValueError("Select valid narration audio.")
    has_music = not fields["no_bgm"].isChecked() and bool(fields["in_bgm"].text().strip())
    music = Path(fields["in_bgm"].text().strip()) if has_music else None
    theme = fields["theme"]
    theme_value = theme.currentText() if hasattr(theme, "currentText") else theme.text()
    return AutoStoryWorker(
        narration, music, Path(output), fields["interval"].value(), theme_value,
        fields["model"].currentText(), fields["subtitles"].isChecked(),
        fields["motion"].isChecked(), fields["preset"].currentText(),
        fields["s_narr"].value() / 100.0, fields["s_music"].value() / 100.0,
    )
