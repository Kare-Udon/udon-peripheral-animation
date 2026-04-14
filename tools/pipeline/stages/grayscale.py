"""Grayscale stage."""

from __future__ import annotations

from PIL import Image, ImageEnhance, ImageOps

from tools.pipeline.presets import get_preset


def _apply_gamma(image: Image.Image, gamma: float) -> Image.Image:
    lookup = [min(255, max(0, int(((value / 255) ** gamma) * 255))) for value in range(256)]
    return image.point(lookup)


def run_stage(manifest) -> list[str]:
    preset = get_preset(manifest.preset)
    params = dict(preset)
    params.update(manifest.stages["grayscale"].params)
    contrast = float(params["contrast"])
    gamma = float(params["gamma"])

    input_path = manifest.root_dir / manifest.stages["compose"].outputs[0]
    output_path = manifest.root_dir / "grayscale" / "001_gray.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as image:
        gray = image.convert("L")
        gray = ImageOps.autocontrast(gray)
        gray = _apply_gamma(gray, gamma)
        gray = ImageEnhance.Contrast(gray).enhance(contrast)
        gray.save(output_path)

    manifest.stages["grayscale"].params = {"contrast": contrast, "gamma": gamma}
    return [str(output_path.relative_to(manifest.root_dir))]
