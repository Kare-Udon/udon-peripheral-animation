"""Cleanup stage."""

from __future__ import annotations

import numpy as np
from PIL import Image

from tools.pipeline.presets import get_preset


def run_stage(manifest) -> list[str]:
    preset = get_preset(manifest.preset)
    params = dict(preset)
    params.update(manifest.stages["cleanup"].params)
    remove_isolated_black = bool(params.get("remove_isolated_black", False))
    fill_white_holes = bool(params.get("fill_white_holes", True))

    patterned_path = manifest.root_dir / manifest.stages["pattern"].outputs[0]
    output_path = manifest.root_dir / "final_png" / "001_final.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(patterned_path) as image:
        pixels = np.array(image.convert("L"), dtype=np.uint8)

    cleaned = pixels.copy()
    height, width = pixels.shape
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            neighbors = pixels[y - 1 : y + 2, x - 1 : x + 2]
            white_neighbors = int((neighbors == 255).sum())
            if remove_isolated_black and pixels[y, x] == 255 and white_neighbors <= 1:
                cleaned[y, x] = 0
            elif fill_white_holes and pixels[y, x] == 0 and white_neighbors >= 7:
                cleaned[y, x] = 255

    Image.fromarray(cleaned, mode="L").save(output_path)
    manifest.stages["cleanup"].params = {
        "remove_isolated_black": remove_isolated_black,
        "fill_white_holes": fill_white_holes,
    }
    return [str(output_path.relative_to(manifest.root_dir))]
