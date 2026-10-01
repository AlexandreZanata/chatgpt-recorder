"""Subpixel glow compositing used only while building bundled particle videos."""

from math import ceil, floor

import numpy as np


def composite_particle(frame: np.ndarray, x: float, y: float, radius: float,
                       opacity: float, color: tuple) -> None:
    """Blend a continuous Gaussian glow without rounding its center or opacity."""
    half = max(6, ceil(radius * 7))
    left, top = max(0, floor(x) - half), max(0, floor(y) - half)
    right = min(frame.shape[1], floor(x) + half + 1)
    bottom = min(frame.shape[0], floor(y) + half + 1)
    if left >= right or top >= bottom:
        return
    dx = np.arange(left, right, dtype=np.float32) - x
    dy = np.arange(top, bottom, dtype=np.float32) - y
    distance = dy[:, None] ** 2 + dx[None, :] ** 2
    halo = 0.28 * np.exp(-distance / (radius * radius * 11))
    core = 0.72 * np.exp(-distance / (radius * radius * 0.8))
    alpha = np.clip((halo + core) * opacity / 255, 0, 1)[..., None]
    patch = frame[top:bottom, left:right]
    patch += (np.asarray(color, dtype=np.float32) - patch) * alpha
