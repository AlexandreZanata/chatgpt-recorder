"""UI layout helpers for Classic Video Mode and Auto AI Story Mode."""

from pathlib import Path
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSlider, QSpinBox, QWidget
)
from PySide6.QtCore import Qt

from src.core.sdxl_batch_generator import get_available_checkpoints


def create_classic_fields(form: QFormLayout, parent_browse_cb, img_dir, aud_dir, bgm_dir):
    """Build input fields for Classic 1-Image Video Mode."""
    filter_a = "Audio (*.aac *.m4a *.mp3 *.wav *.ogg *.flac)"
    w_img, in_img = create_file_row("Background Image:", "Image (*.png *.jpg *.webp)", img_dir, parent_browse_cb)
    w_narr, in_narr = create_file_row("Narration Audio:", filter_a, aud_dir, parent_browse_cb)
    w_bgm, in_bgm = create_file_row("Background Music:", filter_a, bgm_dir, parent_browse_cb)
    w_ns, s_narr = create_slider_row("Narration Volume:", 0, 200, 200)
    w_ms, s_music = create_slider_row("Music Volume:", 0, 50, 15)

    preset = QComboBox()
    preset.addItems(["YouTube Standard (16:9)", "YouTube Shorts / Reels (9:16)"])

    return {
        "rows": [("Background Image:", w_img), ("Narration Audio:", w_narr),
                 ("Background Music:", w_bgm), ("Narration Volume:", w_ns),
                 ("Music Volume:", w_ms), ("Video Preset:", preset)],
        "in_img": in_img, "in_narr": in_narr, "in_bgm": in_bgm,
        "s_narr": s_narr, "s_music": s_music, "preset": preset
    }


def create_auto_story_fields(form: QFormLayout, parent_browse_cb, aud_dir, bgm_dir):
    """Build input fields for Auto AI Story Video Mode."""
    filter_a = "Audio (*.aac *.m4a *.mp3 *.wav *.ogg *.flac)"
    w_narr, in_narr = create_file_row("Narration Audio:", filter_a, aud_dir, parent_browse_cb)
    w_bgm, in_bgm = create_file_row("Background Music:", filter_a, bgm_dir, parent_browse_cb)
    w_ns, s_narr = create_slider_row("Narration Volume:", 0, 200, 200)
    w_ms, s_music = create_slider_row("Music Volume:", 0, 50, 15)

    preset = QComboBox()
    preset.addItems(["YouTube Standard (16:9)", "YouTube Shorts / Reels (9:16)"])

    spin_interval = QSpinBox()
    spin_interval.setRange(15, 180)
    spin_interval.setSingleStep(15)
    spin_interval.setValue(60)
    spin_interval.setSuffix(" segundos")

    in_theme = QLineEdit("Cinematic Miami Luxury, 8k resolution, photorealistic")
    cb_model = QComboBox()
    models = get_available_checkpoints() or ["RealVisXL_V5.0_fp16.safetensors", "juggernautXL_v8Rundiffusion.safetensors"]
    cb_model.addItems(models)

    cb_subtitles = QCheckBox("💬 Incluir Legendas Sincronizadas (.srt)")
    cb_subtitles.setChecked(True)
    cb_motion = QCheckBox("🎥 Movimento Dinâmico Ken Burns (Zoom/Pan Aleatório)")
    cb_motion.setChecked(True)

    return {
        "rows": [("Narration Audio:", w_narr), ("Background Music:", w_bgm),
                 ("Narration Volume:", w_ns), ("Music Volume:", w_ms),
                 ("Video Preset:", preset), ("Trocar Imagem a Cada:", spin_interval),
                 ("Tema Mestre das Cenas:", in_theme), ("Modelo IA SDXL:", cb_model),
                 ("", cb_subtitles), ("", cb_motion)],
        "in_narr": in_narr, "in_bgm": in_bgm, "s_narr": s_narr, "s_music": s_music,
        "preset": preset, "interval": spin_interval, "theme": in_theme,
        "model": cb_model, "subtitles": cb_subtitles, "motion": cb_motion
    }


def create_file_row(label: str, filter_str: str, default_dir: Path, browse_cb):
    widget = QWidget()
    box = QHBoxLayout(widget)
    box.setContentsMargins(0, 0, 0, 0)
    line = QLineEdit()
    btn = QPushButton("Browse...")
    btn.clicked.connect(lambda: browse_cb(line, filter_str, default_dir))
    box.addWidget(line)
    box.addWidget(btn)
    return widget, line


def create_slider_row(label: str, min_v: int, max_v: int, default_v: int):
    widget = QWidget()
    box = QHBoxLayout(widget)
    box.setContentsMargins(0, 0, 0, 0)
    slider = QSlider(Qt.Horizontal)
    slider.setRange(min_v, max_v)
    slider.setValue(default_v)
    lbl = QLabel(f"{default_v}%")
    slider.valueChanged.connect(lambda v: lbl.setText(f"{v}%"))
    box.addWidget(slider)
    box.addWidget(lbl)
    return widget, slider
