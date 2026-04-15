"""Subject-region helpers for portrait-aware processing."""

from __future__ import annotations

import numpy as np


def estimate_subject_mask(
    pixels: np.ndarray,
    background_threshold: int = 248,
    margin: int = 0,
    min_pixels: int = 16,
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    mask = pixels < background_threshold
    height, width = pixels.shape

    if int(mask.sum()) < min_pixels:
        inset_x = max(1, width // 6)
        inset_y = max(1, height // 6)
        bbox = (inset_x, inset_y, width - inset_x, height - inset_y)
        return mask, bbox

    ys, xs = np.where(mask)
    x0 = max(0, int(xs.min()) - margin)
    y0 = max(0, int(ys.min()) - margin)
    x1 = min(width, int(xs.max()) + 1 + margin)
    y1 = min(height, int(ys.max()) + 1 + margin)
    return mask, (x0, y0, x1, y1)


def bbox_mask(shape: tuple[int, int], bbox: tuple[int, int, int, int]) -> np.ndarray:
    height, width = shape
    x0, y0, x1, y1 = bbox
    region = np.zeros((height, width), dtype=bool)
    region[y0:y1, x0:x1] = True
    return region


def apply_highlight_rolloff(
    pixels: np.ndarray,
    subject_region: np.ndarray,
    start: int = 220,
    strength: float = 0.5,
) -> np.ndarray:
    result = pixels.astype(np.float32).copy()
    if strength >= 1.0:
        return pixels.astype(np.uint8)
    mask = subject_region & (result > start)
    result[mask] = start + (result[mask] - start) * strength
    return np.clip(result, 0, 255).astype(np.uint8)


def adaptive_thresholds(
    base_thresholds: list[int],
    subject_pixels: np.ndarray,
    percentiles: list[int],
    blend: float,
) -> list[int]:
    if subject_pixels.size == 0:
        return list(base_thresholds)

    adaptive = [
        int(np.percentile(subject_pixels.astype(np.float32), percentile))
        for percentile in percentiles
    ]
    thresholds: list[int] = []
    for index, base in enumerate(base_thresholds):
        blended = int(round(base * (1.0 - blend) + adaptive[index] * blend))
        if thresholds:
            blended = max(thresholds[-1] + 1, blended)
        thresholds.append(min(254, blended))
    return thresholds
