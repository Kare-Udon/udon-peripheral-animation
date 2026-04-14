"""Cleanup stage."""

from __future__ import annotations

import numpy as np
from PIL import Image


def run_stage(manifest) -> list[str]:
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
            black_neighbors = int((neighbors == 255).sum())
            if pixels[y, x] == 255 and black_neighbors <= 1:
                cleaned[y, x] = 0
            elif pixels[y, x] == 0 and black_neighbors >= 7:
                cleaned[y, x] = 255

    Image.fromarray(cleaned, mode="L").save(output_path)
    manifest.stages["cleanup"].params = {"despeckle": 1}
    return [str(output_path.relative_to(manifest.root_dir))]
