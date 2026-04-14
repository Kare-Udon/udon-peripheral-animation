"""Export final PNG to LVGL indexed 1-bit C assets."""

from __future__ import annotations

import re

import numpy as np
from PIL import Image


def _sanitize_name(job_id: str) -> str:
    return re.sub(r"[^0-9A-Za-z_]+", "_", job_id).strip("_") or "generated_art"


def _pack_indexed_1bit(image: Image.Image) -> list[int]:
    pixels = np.array(image.convert("L"), dtype=np.uint8)
    bits = (pixels > 0).astype(np.uint8)

    height, width = bits.shape
    bytes_per_row = (width + 7) // 8
    packed: list[int] = []
    for y in range(height):
        for byte_index in range(bytes_per_row):
            byte = 0
            for bit_index in range(8):
                x = byte_index * 8 + bit_index
                value = int(bits[y, x]) if x < width else 0
                byte |= value << (7 - bit_index)
            packed.append(byte)
    return packed


def _format_bytes(values: list[int], indent: str = "        ") -> str:
    lines: list[str] = []
    row: list[str] = []
    for index, value in enumerate(values, start=1):
        row.append(f"0x{value:02x}")
        if index % 16 == 0:
            lines.append(indent + ", ".join(row) + ",")
            row = []
    if row:
        lines.append(indent + ", ".join(row) + ",")
    return "\n".join(lines)


def run_stage(manifest) -> list[str]:
    input_path = manifest.root_dir / manifest.stages["cleanup"].outputs[0]
    asset_name = _sanitize_name(manifest.job_id)
    c_path = manifest.root_dir / "lvgl" / f"{asset_name}.c"
    h_path = manifest.root_dir / "lvgl" / f"{asset_name}.h"
    c_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as image:
        image = image.convert("L")
        image = image.point(lambda px: 255 if px > 0 else 0)
        rotated = image.transpose(Image.Transpose.ROTATE_270)

    packed = [
        0x00,
        0x00,
        0x00,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        *_pack_indexed_1bit(rotated),
    ]

    width, height = rotated.size
    c_text = f"""#include <lvgl.h>

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

#ifndef LV_ATTRIBUTE_IMG_{asset_name.upper()}
#define LV_ATTRIBUTE_IMG_{asset_name.upper()}
#endif

const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST LV_ATTRIBUTE_IMG_{asset_name.upper()} uint8_t
    {asset_name}_map[] = {{
{_format_bytes(packed)}
}};

const lv_img_dsc_t {asset_name} = {{
    .header.cf = LV_IMG_CF_INDEXED_1BIT,
    .header.always_zero = 0,
    .header.reserved = 0,
    .header.w = {width},
    .header.h = {height},
    .data_size = {len(packed)},
    .data = {asset_name}_map,
}};
"""

    h_text = f"""#pragma once

#include <lvgl.h>

extern const lv_img_dsc_t {asset_name};
"""

    c_path.write_text(c_text)
    h_path.write_text(h_text)
    manifest.stages["export_lvgl"].params = {"asset_name": asset_name}
    return [
        str(c_path.relative_to(manifest.root_dir)),
        str(h_path.relative_to(manifest.root_dir)),
    ]
