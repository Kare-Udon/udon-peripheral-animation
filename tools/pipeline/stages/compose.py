"""Compose stage for center-cropping and resizing input images."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def _center_crop_box(width: int, height: int, target_width: int, target_height: int) -> tuple[int, int, int, int]:
    source_ratio = width / height
    target_ratio = target_width / target_height

    if source_ratio > target_ratio:
        cropped_width = int(height * target_ratio)
        left = (width - cropped_width) // 2
        return left, 0, left + cropped_width, height

    cropped_height = int(width / target_ratio)
    top = (height - cropped_height) // 2
    return 0, top, width, top + cropped_height


def run_stage(manifest) -> list[str]:
    target_width, target_height = manifest.target_size
    params = dict(manifest.stages["compose"].params)
    crop_mode = params.get("crop", "center")
    output_path = manifest.root_dir / "frames_work" / "001_composed.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(manifest.input_path) as image:
        image = image.convert("RGB")
        if crop_mode != "center":
            raise ValueError(f"unsupported crop mode: {crop_mode}")
        crop_box = _center_crop_box(image.width, image.height, target_width, target_height)
        image = image.crop(crop_box)
        image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        image.save(output_path)

    manifest.stages["compose"].params = {"crop": crop_mode, "size": [target_width, target_height]}
    return [str(output_path.relative_to(manifest.root_dir))]
