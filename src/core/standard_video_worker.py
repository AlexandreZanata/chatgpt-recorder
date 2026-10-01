"""Standard-mode rendering with optional subtitles and bundled particle loops."""

from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtCore import QThread, Signal

from src.core.ai_transcriber import transcribe_audio_to_segments
from src.engine.audio_mixer import get_audio_duration
from src.engine.standard_backgrounds import resolve_standard_background
from src.engine.subtitle_generator import save_ass_subtitles
from src.engine.video_composer import render_single_pass_video


class RenderWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, img: Path, narr: Path, bgm: Path | None, out: Path,
                 n_vol: float, m_vol: float, preset: str, quick_outro: bool = False,
                 has_subtitles: bool = True, background_theme: str = ""):
        super().__init__()
        self.img, self.narr, self.bgm, self.out = img, narr, bgm, out
        self.n_vol, self.m_vol, self.preset, self.quick_outro = n_vol, m_vol, preset, quick_outro
        self.has_subtitles, self.background_theme = has_subtitles, background_theme

    def _subtitle_file(self, directory: Path, width: int, height: int) -> Path | None:
        """Skip transcription entirely when the user disables subtitles."""
        if not self.has_subtitles:
            return None
        self.progress.emit(2, "Transcribing narration for synchronized subtitles...")
        segments = transcribe_audio_to_segments(str(self.narr))
        if not segments:
            raise RuntimeError("No subtitles could be transcribed. Check narration or disable subtitles.")
        return save_ass_subtitles(segments, directory / "narration.ass",
                                  font_size=round(min(width, height) * 0.09),
                                  width=width, height=height, alignment=5,
                                  outline_width=4, margin_horizontal=round(width * 0.10))

    def run(self):
        try:
            total_dur = get_audio_duration(self.narr)
            outro = 0.0 if self.preset != "YouTube Standard (16:9)" else (5.0 if self.quick_outro else 30.0)
            render_dur = total_dur + outro if total_dur > 0 else 0.0
            if render_dur <= 0:
                raise ValueError("Could not determine narration duration.")
            w, h = (1920, 1080) if self.preset == "YouTube Standard (16:9)" else (1080, 1920)
            background, is_video = resolve_standard_background(self.img, self.background_theme,
                                                                portrait=h > w)

            def on_progress(pct_val: float, sec_val: float):
                self.progress.emit(int(pct_val), f"Single-Pass GPU Encoding ({sec_val:.1f}s / {render_dur:.1f}s)...")

            with TemporaryDirectory(prefix="standard-video-") as directory:
                subtitle = self._subtitle_file(Path(directory), w, h)
                self.progress.emit(5, f"Single-Pass GPU Encoding (0.0s / {render_dur:.1f}s)...")
                ok = render_single_pass_video(
                    background, self.narr, self.bgm, subtitle, self.out,
                    narr_vol=self.n_vol, bgm_vol=self.m_vol, width=w, height=h,
                    fps=30 if is_video else 15, progress_callback=on_progress,
                    total_duration=render_dur, background_is_video=is_video,
                )
            self.progress.emit(100, "Rendering complete!")
            self.finished.emit(ok, f"Video rendered at {self.out}" if ok else "GPU rendering failed.")
        except Exception as err:
            self.finished.emit(False, str(err))
