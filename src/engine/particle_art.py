"""Deterministic periodic particle artwork for bundled Standard-mode loops."""

from math import exp, pi, sin
import random

import numpy as np
from PIL import Image, ImageOps

from src.engine.particle_profiles import PARTICLE_PROFILES, ParticleProfile
from src.engine.particle_render import composite_particle
from src.engine.standard_backgrounds import BACKGROUND_DIR

LOOP_SECONDS = 24


def _base_canvas(profile: ParticleProfile, width: int, height: int) -> Image.Image:
    """Fit generated artwork or paint the original enigmatic black backdrop."""
    if profile.plate:
        plate = profile.portrait_plate if height > width else profile.plate
        with Image.open(BACKGROUND_DIR / plate) as source:
            return ImageOps.fit(source.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)
    x, y = np.meshgrid(np.linspace(0, 1, width), np.linspace(0, 1, height))
    mist = np.exp(-(((x - 0.30) / 0.62) ** 2 + ((y - 0.43) / 0.25) ** 2))
    vignette = np.clip(1 - 0.42 * ((x - 0.5) ** 2 + (y - 0.42) ** 2), 0, 1)
    base = np.zeros((height, width, 3)) + (1, 2, 4)
    base += mist[..., None] * np.array([7, 9, 13])
    base *= vignette[..., None]
    noise = np.random.default_rng(42).uniform(-0.6, 0.6, (height, width, 1))
    return Image.fromarray(np.uint8(np.clip(base + noise, 0, 255)))


def _lifetime_glow(progress: float) -> float:
    """Smoothstep fades hide recycling with zero velocity in opacity at the seam."""
    fade = min(1.0, progress / 0.12, (1.0 - progress) / 0.12)
    return fade * fade * (3 - 2 * fade)


class ParticleLoop:
    """Visible motion repeats exactly, with invisible individual particle recycling."""

    def __init__(self, theme: str, width: int = 1280, height: int = 720):
        if theme not in PARTICLE_PROFILES:
            raise ValueError(f"Unknown particle theme: {theme}")
        profile = PARTICLE_PROFILES[theme]
        self.base = _base_canvas(profile, width, height)
        self.soften_center = bool(profile.plate)
        self.color = profile.color
        self.width, self.height = width, height
        self.base_pixels = np.asarray(self.base, dtype=np.float32)
        rng = random.Random(731)
        self.particles = [
            (rng.uniform(0.03, 0.97) * width, rng.uniform(0.03, 0.87) * height,
             rng.uniform(*profile.drift_x) * width / 1280,
             rng.uniform(*profile.travel_y) * height, rng.uniform(0, 2 * pi),
             rng.choice(profile.radii), rng.uniform(0.55, 1.0))
            for _ in range(profile.count)
        ]

    def frame(self, seconds: float) -> Image.Image:
        """Evaluate the periodic animation directly, with no accumulated state."""
        frame = self.base_pixels.copy()
        cycle = (seconds % LOOP_SECONDS) / LOOP_SECONDS
        for cx, cy, ax, ay, offset, radius, brightness in self.particles:
            progress = (cycle + offset / (2 * pi)) % 1.0
            phase = 2 * pi * progress
            depth = 0.8 + 0.15 * radius
            x = cx + ax * sin(phase + offset)
            y = cy + ay * depth * (0.5 - progress)
            glow = brightness * (0.88 + 0.12 * sin(phase + offset)) * _lifetime_glow(progress)
            if self.soften_center:
                # Keep the luminous foreground dust softer behind centered subtitles.
                nx, ny = x / self.width, y / self.height
                center = exp(-((nx - 0.5) / 0.28) ** 2 - ((ny - 0.5) / 0.24) ** 2)
                glow *= 1.15 * (1 - 0.30 * center)
            composite_particle(frame, x, y, max(0.5, radius * min(self.width, self.height) / 720),
                               175 * glow, self.color)
        return Image.fromarray(np.uint8(np.clip(frame, 0, 255)))
