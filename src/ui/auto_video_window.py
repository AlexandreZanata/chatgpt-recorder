"""Auto Story Video Generator UI Window for the ChatGPT Desktop Suite."""

import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from src.core.ai_scene_planner import plan_scenes_from_duration
from src.core.motion_renderer import assign_random_motions
from src.core.sdxl_batch_generator import get_available_checkpoints


class AutoStoryVideoWindow(tk.Toplevel):
    """Separate dedicated window for automated AI video generation."""

    def __init__(self, parent: Optional[tk.Tk] = None):
        super().__init__(parent)
        self.title("🤖 Auto AI Story Video Studio (RTX 4060)")
        self.geometry("780x620")
        self.configure(bg="#0f172a")

        self.audio_path_var = tk.StringVar()
        self.format_var = tk.StringVar(value="YouTube Standard (16:9)")
        self.interval_var = tk.IntVar(value=60)
        self.theme_var = tk.StringVar(value="Cinematic Miami Luxury, 8k resolution, photorealistic")
        self.model_var = tk.StringVar()
        self.subtitles_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._load_models()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding="16")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        lbl_title = tk.Label(
            main_frame,
            text="🎬 Estúdio de Vídeo Automático com IA & Legendas",
            font=("Helvetica", 14, "bold"),
            bg="#0f172a",
            fg="#10b981"
        )
        lbl_title.pack(anchor="w", pady=(0, 12))

        # Audio Selector
        aud_frame = ttk.LabelFrame(main_frame, text=" 🎙️ Áudio de Narração ", padding="8")
        aud_frame.pack(fill=tk.X, pady=6)
        ttk.Entry(aud_frame, textvariable=self.audio_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(aud_frame, text="Procurar Áudio...", command=self._browse_audio).pack(side=tk.RIGHT)

        # Settings Grid
        cfg_frame = ttk.LabelFrame(main_frame, text=" ⚙️ Configurações de Produção ", padding="8")
        cfg_frame.pack(fill=tk.X, pady=6)

        ttk.Label(cfg_frame, text="Formato de Vídeo:").grid(row=0, column=0, sticky="w", pady=4)
        fmt_cb = ttk.Combobox(cfg_frame, textvariable=self.format_var, state="readonly", width=28)
        fmt_cb["values"] = ("YouTube Standard (16:9)", "YouTube Shorts / Reels (9:16)")
        fmt_cb.grid(row=0, column=1, sticky="w", pady=4, padx=8)

        ttk.Label(cfg_frame, text="Trocar Imagem a Cada:").grid(row=1, column=0, sticky="w", pady=4)
        int_box = ttk.Spinbox(cfg_frame, from_=15, to=180, increment=15, textvariable=self.interval_var, width=10)
        int_box.grid(row=1, column=1, sticky="w", pady=4, padx=8)

        ttk.Label(cfg_frame, text="Modelo IA SDXL:").grid(row=2, column=0, sticky="w", pady=4)
        self.model_cb = ttk.Combobox(cfg_frame, textvariable=self.model_var, state="readonly", width=34)
        self.model_cb.grid(row=2, column=1, sticky="w", pady=4, padx=8)

        ttk.Label(cfg_frame, text="Tema Mestre das Cenas:").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(cfg_frame, textvariable=self.theme_var, width=45).grid(row=3, column=1, sticky="w", pady=4, padx=8)

        ttk.Checkbutton(cfg_frame, text="💬 Incluir Legendas Sincronizadas (.srt)", variable=self.subtitles_var).grid(row=4, column=0, columnspan=2, sticky="w", pady=6)

        # Generate Button
        btn_gen = tk.Button(
            main_frame,
            text="🚀 Planejar Cenas & Renderizar Vídeo Completo",
            font=("Helvetica", 11, "bold"),
            bg="#10b981",
            fg="#ffffff",
            activebackground="#059669",
            padx=12,
            pady=10,
            command=self._on_render
        )
        btn_gen.pack(fill=tk.X, pady=(16, 0))

    def _load_models(self):
        models = get_available_checkpoints()
        if models:
            self.model_cb["values"] = models
            # Default to RealVisXL if present
            pref = [m for m in models if "RealVisXL" in m]
            self.model_var.set(pref[0] if pref else models[0])
        else:
            self.model_cb["values"] = ("Nenhum modelo encontrado",)
            self.model_var.set("Nenhum modelo encontrado")

    def _browse_audio(self):
        path = filedialog.askopenfilename(
            title="Selecione o áudio de narração",
            filetypes=[("Áudio", "*.mp3 *.wav *.m4a *.aac *.ogg"), ("Todos os Arquivos", "*.*")]
        )
        if path:
            self.audio_path_var.set(path)

    def _on_render(self):
        if not self.audio_path_var.get():
            messagebox.showwarning("Aviso", "Selecione um arquivo de áudio de narração!")
            return
        messagebox.showinfo("Sucesso", "Planejamento de cenas iniciado com sucesso!")
