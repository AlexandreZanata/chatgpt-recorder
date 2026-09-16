from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import time
from typing import Any, Callable, Dict, List, Optional
from PySide6.QtCore import QThread, Signal

from src.core.ai_scene_planner import plan_adaptive_scenes
from src.core.ai_transcriber import generate_srt_subtitles, slice_srt_for_window, transcribe_audio_to_segments
from src.core.generation_profiles import GenerationProfile, get_generation_profile
from src.core.motion_renderer import apply_motion_preference
from src.core.sdxl_batch_generator import DirectSDXLGenerator
from src.core.storyboard_composer import assemble_clips_to_video, render_scene_clip
from src.engine.audio_mixer import get_audio_duration


def _pipeline_scenes(
    scenes: List[Dict[str, Any]],
    bible: Dict[str, str],
    segments: List[Dict[str, Any]],
    temp_dir: Path,
    dims: tuple,
    has_subtitles: bool,
    prog_cb: Callable[[int, str], None],
    generation_profile: GenerationProfile,
    model_name: Optional[str] = None
) -> List[Path]:
    """Execute overlapped diffusion generation and background NVENC clip rendering."""
    inf_w, inf_h, out_w, out_h = dims
    total = len(scenes)
    clips_dir = temp_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    chk_dir = Path.home() / "PESSOAL-PROJETOS-ALEXANDRE" / "Fooocus" / "models" / "checkpoints"
    chk_p = str(chk_dir / model_name) if model_name and (chk_dir / model_name).exists() else None
    generator = DirectSDXLGenerator(checkpoint_path=chk_p, profile=generation_profile)
    prompts = [sc["prompt"] for sc in scenes]
    neg_p = bible.get("negative_prompt", "")
    generator.load_pipeline(prompts=prompts, negative_prompt=neg_p)
    clip_paths: List[Optional[Path]] = [None] * total

    with ThreadPoolExecutor(max_workers=2) as nvenc_pool:
        futures = []
        for idx, sc in enumerate(scenes):
            img_p = temp_dir / f"scene_{idx+1}.webp"
            clip_p = clips_dir / f"clip_{idx+1}.mp4"
            sc["image_path"] = str(img_p)

            generator.generate_scene_image(
                prompt=sc["prompt"], negative_prompt=neg_p, out_path=img_p,
                width=inf_w, height=inf_h, steps=generation_profile.steps,
                seed=sc.get("seed", 42 + idx), scene_idx=idx
            )
            pct = 25 + int(((idx + 1) / total) * 35)
            prog_cb(pct, f"Cena {idx+1}/{total} visual gerada ({generation_profile.status_label})...")

            sub_file = None
            if has_subtitles and segments:
                sc_srt = temp_dir / f"sub_{idx+1}.srt"
                sub_file = slice_srt_for_window(segments, sc["start_sec"], sc["end_sec"], str(sc_srt))

            m_type = sc.get("motion_type", "zoom_in_center")
            fut = nvenc_pool.submit(
                render_scene_clip, str(img_p), sc["duration_sec"], str(clip_p),
                m_type, out_w, out_h, 30, sub_file
            )
            futures.append((idx, fut, clip_p))

        generator.unload()
        prog_cb(62, "Todas as imagens concluídas. Finalizando clips animados (NVENC)...")

        for idx, fut, p in futures:
            fut.result()
            clip_paths[idx] = p
            pct = 62 + int(((idx + 1) / total) * 28)
            prog_cb(pct, f"Clip {idx+1}/{total} animado e legendado (NVENC)...")

    return [c for c in clip_paths if c is not None]


class AutoStoryWorker(QThread):
    """Memory-bounded, ultra-high-throughput rendering worker for automated AI story videos."""

    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(
        self,
        narr_path: Path,
        bgm_path: Optional[Path],
        out_path: Path,
        interval_sec: int,
        theme: str,
        model_name: str,
        has_subtitles: bool,
        has_motion: bool,
        preset: str,
        narr_vol: float,
        bgm_vol: float
    ):
        super().__init__()
        self.narr_path = Path(narr_path).resolve()
        self.bgm_path = Path(bgm_path).resolve() if bgm_path else None
        self.out_path = Path(out_path).resolve()
        self.interval_sec = interval_sec
        self.theme = theme
        self.model_name = model_name
        self.has_subtitles = has_subtitles
        self.has_motion = has_motion
        self.preset = preset
        self.narr_vol = narr_vol
        self.bgm_vol = bgm_vol

    def run(self):
        """Execute the four-stage ultra-fast pipelined video production."""
        temp_dir = self.out_path.parent / f"tmp_scenes_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            is_short = self.preset != "YouTube Standard (16:9)"
            generation_profile = get_generation_profile(self.theme, is_short)
            out_size = (1080, 1920) if is_short else (1920, 1080)
            dims = (*generation_profile.inference_size, *out_size)

            self.progress.emit(10, "Fase 1/4: Transcrevendo com Whisper Turbo (GPU)...")
            segments = transcribe_audio_to_segments(str(self.narr_path))

            srt_file = None
            if self.has_subtitles and segments:
                srt_file = str(temp_dir / "subtitles.srt")
                generate_srt_subtitles(segments, srt_file)

            total_dur = get_audio_duration(self.narr_path)
            self.progress.emit(20, "Fase 2/4: Planejando cenas semânticas e Visual Bible...")
            manifest = plan_adaptive_scenes(
                total_dur, segments, theme=self.theme, is_short=is_short, interval_sec=float(self.interval_sec)
            )
            manifest["scenes"] = apply_motion_preference(
                manifest["scenes"], enabled=self.has_motion
            )

            (temp_dir / "story_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            self.progress.emit(25, f"Fase 3/4: Gerando com {generation_profile.status_label}...")
            clip_paths = _pipeline_scenes(
                manifest["scenes"], manifest["visual_bible"], segments, temp_dir,
                dims, self.has_subtitles, lambda p, m: self.progress.emit(p, f"Fase 3/4: {m}"),
                generation_profile,
                model_name=self.model_name
            )

            self.progress.emit(92, "Fase 4/4: Montando áudio e vídeo final (Stream-Copy NVENC)...")
            bgm_str = str(self.bgm_path) if self.bgm_path and self.bgm_path.exists() else None

            assemble_clips_to_video(
                clip_paths=clip_paths,
                audio_path=str(self.narr_path),
                output_video_path=str(self.out_path),
                bgm_path=bgm_str,
                narr_vol=self.narr_vol,
                bgm_vol=self.bgm_vol,
                subtitles_srt_path=srt_file,
                subtitles_preburned=self.has_subtitles
            )

            self.progress.emit(100, "Vídeo com IA gerado com sucesso!")
            self.finished.emit(True, f"Vídeo salvo em: {self.out_path}")
        except Exception as err:
            self.finished.emit(False, f"Erro na geração de vídeo: {err}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
