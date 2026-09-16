"""Measured SDXL generation profiles for the available AI Story themes."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import unicodedata


@dataclass(frozen=True)
class GenerationProfile:
    """Immutable sampler, resolution, and guidance configuration."""

    name: str
    sampler: str
    steps: int
    guidance_scale: float
    inference_size: tuple[int, int]
    use_lightning: bool

    @property
    def status_label(self) -> str:
        """Return a concise label suitable for progress messages."""
        if self.use_lightning:
            return f"SDXL Lightning {self.steps}-step"
        return f"DPM++ 2M Karras {self.steps}-step"


def _normalized_theme(theme: str) -> str:
    """Normalize accents and casing for stable theme matching."""
    decomposed = unicodedata.normalize("NFKD", theme.lower().strip())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def get_generation_profile(theme: str, is_short: bool) -> GenerationProfile:
    """Select the measured quality profile while preserving each theme's style."""
    portrait_size = (704, 1216)
    landscape_size = (1216, 704)
    inference_size = portrait_size if is_short else landscape_size
    if "religi" in _normalized_theme(theme):
        return GenerationProfile(
            name="religion_premium",
            sampler="dpmpp_2m_karras",
            steps=12,
            guidance_scale=4.5,
            inference_size=inference_size,
            use_lightning=False,
        )
    return GenerationProfile(
        name="high_resolution_fast",
        sampler="euler_trailing_lightning",
        steps=4,
        guidance_scale=0.0,
        inference_size=inference_size,
        use_lightning=True,
    )


def configure_scheduler(
    pipeline: Any,
    profile: GenerationProfile,
    lightning_lora_path: Path,
) -> None:
    """Configure a pipeline with the sampler validated for its step profile."""
    if profile.use_lightning:
        from diffusers import EulerDiscreteScheduler

        if not lightning_lora_path.exists():
            raise FileNotFoundError(f"Lightning LoRA not found: {lightning_lora_path}")
        pipeline.load_lora_weights(str(lightning_lora_path))
        pipeline.fuse_lora()
        pipeline.scheduler = EulerDiscreteScheduler.from_config(
            pipeline.scheduler.config,
            timestep_spacing="trailing",
        )
        return

    from diffusers import DPMSolverMultistepScheduler

    pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
        pipeline.scheduler.config,
        algorithm_type="dpmsolver++",
        solver_order=2,
        use_karras_sigmas=True,
    )
