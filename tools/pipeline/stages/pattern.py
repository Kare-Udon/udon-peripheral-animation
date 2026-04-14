"""Pattern mapping stage."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


def _load_patterns() -> dict[int, np.ndarray]:
    pattern_path = Path(__file__).resolve().parents[1] / "patterns" / "default_2x2.json"
    raw_patterns = json.loads(pattern_path.read_text())
    return {int(key): np.array(value, dtype=np.uint8) for key, value in raw_patterns.items()}


def run_stage(manifest) -> list[str]:
    quantized_path = manifest.root_dir / manifest.stages["quantize"].outputs[0]
    output_path = manifest.root_dir / "patterned" / "001_bw.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    patterns = _load_patterns()
    with Image.open(quantized_path) as image:
        levels = np.array(image.convert("L"), dtype=np.uint8)

    height, width = levels.shape
    canvas = np.zeros((height, width), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            tile = patterns[int(levels[y, x])]
            canvas[y, x] = tile[y % tile.shape[0], x % tile.shape[1]]

    Image.fromarray(canvas, mode="L").save(output_path)
    manifest.stages["pattern"].params = {"pattern_set": manifest.pattern_set}
    return [str(output_path.relative_to(manifest.root_dir))]
