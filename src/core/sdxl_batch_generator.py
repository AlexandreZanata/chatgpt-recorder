"""Direct in-process SDXL engine with measured fast and premium quality profiles."""

import gc
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import torch

from src.core.generation_profiles import GenerationProfile, configure_scheduler, get_generation_profile

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
if hasattr(torch, "cuda") and torch.cuda.is_available():
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True


def get_default_checkpoint() -> str:
    """Find the best available local SDXL checkpoint."""
    chk_dir = Path.home() / "PESSOAL-PROJETOS-ALEXANDRE" / "Fooocus" / "models" / "checkpoints"
    for name in ["RealVisXL_V5.0_fp16.safetensors", "juggernautXL_v8Rundiffusion.safetensors", "CyberRealisticXLPlay_V10.0_FP16.safetensors"]:
        p = chk_dir / name
        if p.exists():
            return str(p)
    safes = list(chk_dir.glob("*.safetensors")) if chk_dir.exists() else []
    return str(safes[0]) if safes else ""


THEME_MODELS = {
    "deep black": "RealVisXL_V5.0_fp16.safetensors",
    "agro zaflas": "juggernautXL_v8Rundiffusion.safetensors",
    "religiao primium word": "RealVisXL_V5.0_fp16.safetensors",
    "religião primium word": "RealVisXL_V5.0_fp16.safetensors"
}


def get_model_for_theme(theme: str) -> str:
    """Return the locked high-performance checkpoint associated with the specified theme."""
    clean = theme.lower().strip().replace("ã", "a")
    for key, model in THEME_MODELS.items():
        if key in clean or (key.startswith("religiao") and "religi" in clean):
            return model
    return "RealVisXL_V5.0_fp16.safetensors"


def get_available_checkpoints(models_dir: Optional[str] = None) -> List[str]:
    """Scan and list all available SDXL checkpoint files."""
    if not models_dir:
        models_dir = str(Path.home() / "PESSOAL-PROJETOS-ALEXANDRE" / "Fooocus" / "models" / "checkpoints")
    dir_path = Path(models_dir)
    return [f.name for f in dir_path.glob("*.safetensors")] if dir_path.exists() else []


class DirectSDXLGenerator:
    """Resident SDXL pipeline configured for a measured theme quality profile."""

    def __init__(self, checkpoint_path: Optional[str] = None, profile: Optional[GenerationProfile] = None):
        self.checkpoint_path = checkpoint_path or get_default_checkpoint()
        self.profile = profile or get_generation_profile("", is_short=False)
        self.pipe: Optional[Any] = None
        self.pre_encoded: Optional[Any] = None

    def load_pipeline(
        self,
        prompts: Optional[List[str]] = None,
        negative_prompt: str = ""
    ):
        """Load SDXL checkpoint, pre-encode prompts on CUDA if provided, then load UNet to CUDA."""
        from diffusers import StableDiffusionXLPipeline

        if not Path(self.checkpoint_path).exists():
            raise FileNotFoundError(f"Checkpoint not found: {self.checkpoint_path}")

        torch.cuda.empty_cache()
        self.pipe = StableDiffusionXLPipeline.from_single_file(
            self.checkpoint_path, torch_dtype=torch.float16, use_safetensors=True
        )

        free_b = torch.cuda.mem_get_info()[0] if torch.cuda.is_available() else 0
        use_offload = free_b < 5.5 * (1024 ** 3)

        if prompts:
            self.pipe.text_encoder.to("cuda")
            self.pipe.text_encoder_2.to("cuda")
            with torch.no_grad():
                self.pre_encoded = self.pipe.encode_prompt(
                    prompt=prompts, negative_prompt=[negative_prompt] * len(prompts), device="cuda"
                )
            self.pipe.text_encoder.to("cpu")
            self.pipe.text_encoder_2.to("cpu")
            torch.cuda.empty_cache()

        lora_p = Path.home() / "PESSOAL-PROJETOS-ALEXANDRE" / "Fooocus" / "models" / "loras" / "sdxl_lightning_4step_lora.safetensors"
        configure_scheduler(self.pipe, self.profile, lora_p)

        self.pipe.vae.config.force_upcast = False
        self.pipe.vae.enable_slicing()
        self.pipe.vae.enable_tiling()

        if use_offload:
            self.pipe.enable_sequential_cpu_offload()
        else:
            self.pipe.unet.to("cuda")
            self.pipe.vae.to("cuda")

    def generate_scene_image(
        self,
        prompt: str,
        negative_prompt: str,
        out_path: Path,
        width: int = 1024,
        height: int = 576,
        steps: int = 4,
        seed: int = 42,
        scene_idx: Optional[int] = None
    ) -> Path:
        """Generate a single scene visual using resident pipeline and save to disk."""
        if self.pipe is None:
            self.load_pipeline()

        gen = torch.Generator(device="cuda").manual_seed(seed)
        if self.pre_encoded is not None and scene_idx is not None:
            kwargs = {
                "prompt_embeds": self.pre_encoded[0][scene_idx:scene_idx+1],
                "negative_prompt_embeds": self.pre_encoded[1][scene_idx:scene_idx+1],
                "pooled_prompt_embeds": self.pre_encoded[2][scene_idx:scene_idx+1],
                "negative_pooled_prompt_embeds": self.pre_encoded[3][scene_idx:scene_idx+1],
                "num_inference_steps": steps, "width": width, "height": height,
                "guidance_scale": self.profile.guidance_scale, "generator": gen
            }
        else:
            kwargs = {
                "prompt": prompt, "negative_prompt": negative_prompt,
                "num_inference_steps": steps, "width": width, "height": height,
                "guidance_scale": self.profile.guidance_scale, "generator": gen
            }
        image = self.pipe(**kwargs).images[0]

        out_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(out_path), format="WEBP", lossless=True, method=1)
        return out_path

    def unload(self):
        """Completely release pipeline from GPU memory."""
        self.pre_encoded = None
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def generate_scenes_batch(
    scenes: List[Dict[str, Any]],
    visual_bible: Dict[str, str],
    out_dir: Path,
    width: int = 1024,
    height: int = 576,
    steps: int = 4,
    progress_cb: Optional[Callable[[int, str], None]] = None
) -> List[Path]:
    """Execute resident batch generation across all planned scenes."""
    generator = DirectSDXLGenerator()
    prompts = [sc["prompt"] for sc in scenes]
    neg_p = visual_bible.get("negative_prompt", "")
    generator.load_pipeline(prompts=prompts, negative_prompt=neg_p)
    generated_paths: List[Path] = []
    total = len(scenes)

    try:
        for idx, scene in enumerate(scenes):
            if progress_cb:
                pct = int(25 + (idx / max(1, total)) * 55)
                progress_cb(pct, f"Gerando cena {idx+1}/{total} (SDXL Lightning): '{scene['excerpt'][:35]}...'")

            img_file = out_dir / f"scene_{idx+1}.webp"
            generator.generate_scene_image(
                prompt=scene["prompt"],
                negative_prompt=neg_p,
                out_path=img_file,
                width=width,
                height=height,
                steps=steps,
                seed=scene.get("seed", 42),
                scene_idx=idx
            )
            scene["image_path"] = str(img_file)
            generated_paths.append(img_file)
    finally:
        generator.unload()

    return generated_paths
