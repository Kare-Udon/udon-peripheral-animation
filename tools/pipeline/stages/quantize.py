"""Quantize stage."""

from __future__ import annotations

import numpy as np
from PIL import Image

from tools.pipeline.presets import get_preset


def run_stage(manifest) -> list[str]:
    preset = get_preset(manifest.preset)
    params = dict(preset)
    params.update(manifest.stages["quantize"].params)
    thresholds = [int(value) for value in params["thresholds"]]

    input_path = manifest.root_dir / manifest.stages["grayscale"].outputs[0]
    output_path = manifest.root_dir / "quantized" / "001_levels.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as image:
        pixels = np.array(image.convert("L"), dtype=np.uint8)
        quantized = np.digitize(pixels, thresholds, right=False).astype(np.uint8)
        Image.fromarray(quantized, mode="L").save(output_path)

    manifest.stages["quantize"].params = {"thresholds": thresholds}
    return [str(output_path.relative_to(manifest.root_dir))]
