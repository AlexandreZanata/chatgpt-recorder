"""Background Worker Thread for Auto AI Story Video Production."""

from pathlib import Path
import time
from typing import Dict, List, Optional
from PySide6.QtCore import QThread, Signal

from src.core.ai_scene_planner import plan_scenes_from_duration
from src.core.ai_transcriber import generate_srt_subtitles, transcribe_audio_to_segments
from src.core.motion_renderer import assign_random_motions
from src.core.sdxl_batch_generator import request_local_sdxl_image
from src.core.storyboard_composer import concatenate_scenes_with_audio, render_scene_clip
from src.engine.audio_mixer import get_audio_duration


class AutoStoryWorker(QThread):
    """Background rendering pipeline for automated AI story videos."""

    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, narr_path: Path, bgm_path: Optional[Path], out_path: Path, interval_sec: int, theme: str, model_name: str, has_subtitles: bool, has_motion: bool, preset: str, narr_vol: float, bgm_vol: float):
        super().__init__()
        self.narr_path = narr_path
        self.bgm_path = bgm_path
        self.out_path = out_path
        self.interval_sec = interval_sec
        self.theme = theme
        self.model_name = model_name
        self.has_subtitles = has_subtitles
        self.has_motion = has_motion
        self.preset = preset
        self.narr_vol = narr_vol
        self.bgm_vol = bgm_vol

    def run(self):
        try:
            temp_dir = self.out_path.parent / f"tmp_scenes_{int(time.time())}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            self.progress.emit(10, "Transcrevendo áudio com Whisper (Timestamps palavra por palavra)...")
            segments = transcribe_audio_to_segments(str(self.narr_path))
            srt_file = None
            if self.has_subtitles and segments:
                srt_file = str(temp_dir / "subtitles.srt")
                generate_srt_subtitles(segments, srt_file)

            total_dur = get_audio_duration(self.narr_path)
            self.progress.emit(20, f"Planejando {int(total_dur // self.interval_sec) + 1} cenas com prompts individuais em inglês...")
            scenes = plan_scenes_from_duration(total_dur, float(self.interval_sec), self.theme, segments)
            if self.has_motion:
                scenes = assign_random_motions(scenes)

            aspect = "896*1152" if self.preset != "YouTube Standard (16:9)" else "1152*896"
            w, h = (1080, 1920) if self.preset != "YouTube Standard (16:9)" else (1920, 1080)

            clip_paths = []
            for i, scene in enumerate(scenes):
                pct = int(25 + (i / max(1, len(scenes))) * 60)
                self.progress.emit(pct, f"Gerando imagem da cena {i+1}/{len(scenes)} (Lightning): '{scene['excerpt'][:40]}...'")

                scene_img = temp_dir / f"new_scene_{i+1}.png"
                # Request fresh image via Lightning SDXL
                ok = request_local_sdxl_image(scene["prompt"], str(scene_img), model_name=self.model_name, performance="Lightning", aspect_ratio=aspect)

                # If no direct API response, create fresh thematic gradient canvas
                if not scene_img.exists():
                    self._create_scene_backdrop(scene_img, w, h, i)

                clip_out = str(temp_dir / f"clip_{i+1}.mp4")
                m_type = scene.get("motion_type", "zoom_in") if self.has_motion else "zoom_in"
                render_scene_clip(str(scene_img), scene["duration_sec"], clip_out, motion_type=m_type, width=w, height=h)
                clip_paths.append(clip_out)

            self.progress.emit(90, "Concatenando vídeo com áudio, música e legendas sincronizadas...")
            bgm_str = str(self.bgm_path) if self.bgm_path and self.bgm_path.exists() else None
            concatenate_scenes_with_audio(clip_paths, str(self.narr_path), str(self.out_path), bgm_path=bgm_str, narr_vol=self.narr_vol, bgm_vol=self.bgm_vol, subtitles_srt_path=srt_file)

            self.progress.emit(100, "Vídeo com IA gerado com sucesso!")
            self.finished.emit(True, f"Vídeo salvo em: {self.out_path}")
        except Exception as err:
            self.finished.emit(False, f"Erro na geração de vídeo: {err}")

    def _create_scene_backdrop(self, dest: Path, w: int, h: int, idx: int):
        from PIL import Image, ImageDraw
        colors = [(15, 23, 42), (30, 41, 59), (51, 65, 85), (71, 85, 105)]
        bg = colors[idx % len(colors)]
        img = Image.new("RGB", (w, h), color=bg)
        img.save(dest)
