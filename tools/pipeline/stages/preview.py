"""Preview contact sheet stage."""

from __future__ import annotations

from PIL import Image


def _load_panel(manifest, stage_name: str, fallback: str | None = None) -> Image.Image:
    if stage_name == "input":
        return Image.open(manifest.input_path).convert("RGB")

    outputs = manifest.stages[stage_name].outputs
    if outputs:
        return Image.open(manifest.root_dir / outputs[0]).convert("RGB")

    if fallback is not None:
        return Image.open(manifest.root_dir / fallback).convert("RGB")

    raise ValueError(f"no output available for stage {stage_name}")


def run_stage(manifest) -> list[str]:
    panels = [
        _load_panel(manifest, "input"),
        _load_panel(manifest, "compose"),
        _load_panel(manifest, "grayscale"),
        _load_panel(manifest, "quantize"),
        _load_panel(manifest, "pattern"),
        _load_panel(manifest, "cleanup"),
    ]

    panel_width, panel_height = manifest.target_size
    normalized = [panel.resize((panel_width, panel_height)) for panel in panels]
    contact = Image.new("RGB", (panel_width * 3, panel_height * 2), color="white")

    for index, panel in enumerate(normalized):
        x = (index % 3) * panel_width
        y = (index // 3) * panel_height
        contact.paste(panel, (x, y))

    output_path = manifest.root_dir / "preview" / "001_contact.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    contact.save(output_path)
    manifest.stages["preview"].params = {"layout": "2x3"}
    return [str(output_path.relative_to(manifest.root_dir))]
