"""Offline artwork and particle settings; video export only decodes bundled loops."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ParticleProfile:
    plate: str = ""
    portrait_plate: str = ""
    color: tuple = (231, 239, 255)
    drift_x: tuple = (10, 42)
    travel_y: tuple = (0.40, 0.75)
    radii: tuple = (0.8, 1.1, 1.5, 2.1)
    count: int = 145
    crf: int = 14
    portrait_crf: int = 12


PARTICLE_PROFILES = {
    "black": ParticleProfile(),
    "religious": ParticleProfile(
        plate="religious_renaissance_plate.png", color=(255, 218, 150),
        portrait_plate="religious_renaissance_shorts_plate.png",
        drift_x=(12, 36), travel_y=(0.40, 0.70),
        radii=(0.8, 0.8, 1.2, 1.2, 1.8, 2.6, 3.6), count=150,
    ),
    "agro": ParticleProfile(
        plate="zaflas_agro_plate.png", color=(255, 225, 160),
        portrait_plate="zaflas_agro_shorts_plate.png",
        drift_x=(10, 30), travel_y=(0.35, 0.65),
        radii=(0.8, 0.8, 1.1, 1.5, 2.2, 3.0), count=100, crf=14,
    ),
    "fallem_prince": ParticleProfile(
        plate="fallem_prince_plate.png", color=(230, 230, 230),
        portrait_plate="fallem_prince_shorts_plate.png",
        drift_x=(8, 26), travel_y=(0.35, 0.60),
        radii=(0.8, 0.8, 1.0, 1.4, 2.0, 2.8), count=90, crf=14,
    ),
}
