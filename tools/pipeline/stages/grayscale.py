"""Grayscale stage."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from tools.pipeline.presets import get_preset
from tools.pipeline.stages.subject import apply_highlight_rolloff, bbox_mask, estimate_subject_mask


def _apply_gamma(image: Image.Image, gamma: float) -> Image.Image:
    lookup = [min(255, max(0, int(((value / 255) ** gamma) * 255))) for value in range(256)]
    return image.point(lookup)


def run_stage(manifest) -> list[str]:
    preset = get_preset(manifest.preset)
    params = dict(preset)
    params.update(manifest.stages["grayscale"].params)
    contrast = float(params["contrast"])
    gamma = float(params["gamma"])
    background_threshold = int(params.get("subject_background_threshold", 248))
    subject_margin = int(params.get("subject_margin", 6))
    rolloff_start = int(params.get("highlight_rolloff_start", 220))
    rolloff_strength = float(params.get("highlight_rolloff_strength", 1.0))

    input_path = manifest.root_dir / manifest.stages["compose"].outputs[0]
    output_path = manifest.root_dir / "grayscale" / "001_gray.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as image:
        gray = image.convert("L")
        base_pixels = np.array(gray, dtype=np.uint8)
        _, bbox = estimate_subject_mask(
            base_pixels,
            background_threshold=background_threshold,
            margin=subject_margin,
        )
        subject_region = bbox_mask(base_pixels.shape, bbox)

        gray = ImageOps.autocontrast(gray)
        gray = _apply_gamma(gray, gamma)
        gray = ImageEnhance.Contrast(gray).enhance(contrast)

        processed = np.array(gray, dtype=np.uint8)
        processed = apply_highlight_rolloff(
            processed,
            subject_region=subject_region,
            start=rolloff_start,
            strength=rolloff_strength,
        )
        Image.fromarray(processed, mode="L").save(output_path)

    manifest.stages["grayscale"].params = {
        "contrast": contrast,
        "gamma": gamma,
        "subject_background_threshold": background_threshold,
        "subject_margin": subject_margin,
        "subject_bbox": list(bbox),
        "highlight_rolloff_start": rolloff_start,
        "highlight_rolloff_strength": rolloff_strength,
    }
    return [str(output_path.relative_to(manifest.root_dir))]
