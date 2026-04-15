"""Quantize stage."""

from __future__ import annotations

import numpy as np
from PIL import Image

from tools.pipeline.presets import get_preset
from tools.pipeline.stages.subject import adaptive_thresholds, estimate_subject_mask


def _edge_strength(pixels: np.ndarray) -> np.ndarray:
    vertical = np.zeros_like(pixels, dtype=np.float32)
    horizontal = np.zeros_like(pixels, dtype=np.float32)
    vertical[1:-1, :] = np.abs(pixels[2:, :] - pixels[:-2, :])
    horizontal[:, 1:-1] = np.abs(pixels[:, 2:] - pixels[:, :-2])
    return np.maximum(vertical, horizontal)


def run_stage(manifest) -> list[str]:
    preset = get_preset(manifest.preset)
    params = dict(preset)
    params.update(manifest.stages["quantize"].params)
    raw_base_thresholds = params.get("base_thresholds", params["thresholds"])
    base_thresholds = [int(value) for value in raw_base_thresholds]
    thresholds = list(base_thresholds)
    subject_aware = bool(params.get("subject_aware", True))
    subject_background_threshold = int(params.get("subject_background_threshold", 248))
    subject_margin = int(params.get("subject_margin", 6))
    subject_percentiles = [int(value) for value in params.get("subject_percentiles", [35, 55, 74, 90])]
    subject_blend = float(params.get("subject_blend", 0.8))
    edge_boost = max(0, int(params.get("edge_boost", 0)))
    edge_threshold = int(params.get("edge_threshold", 12))

    input_path = manifest.root_dir / manifest.stages["grayscale"].outputs[0]
    output_path = manifest.root_dir / "quantized" / "001_levels.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as image:
        pixels = np.array(image.convert("L"), dtype=np.int16)
        if subject_aware:
            subject_mask, _ = estimate_subject_mask(
                pixels.astype(np.uint8),
                background_threshold=subject_background_threshold,
                margin=subject_margin,
            )
            thresholds = adaptive_thresholds(
                base_thresholds=base_thresholds,
                subject_pixels=pixels[subject_mask].astype(np.uint8),
                percentiles=subject_percentiles,
                blend=subject_blend,
            )
        quantized = np.digitize(pixels, thresholds, right=False).astype(np.uint8)
        if edge_boost > 0:
            edges = _edge_strength(pixels)
            edge_mask = (pixels < 250) & (edges >= edge_threshold)
            quantized = np.where(edge_mask, np.clip(quantized - edge_boost, 0, manifest.levels - 1), quantized)
        Image.fromarray(quantized, mode="L").save(output_path)

    manifest.stages["quantize"].params = {
        "thresholds": thresholds,
        "base_thresholds": base_thresholds,
        "subject_aware": subject_aware,
        "subject_background_threshold": subject_background_threshold,
        "subject_margin": subject_margin,
        "subject_percentiles": subject_percentiles,
        "subject_blend": subject_blend,
        "edge_boost": edge_boost,
        "edge_threshold": edge_threshold,
    }
    return [str(output_path.relative_to(manifest.root_dir))]
