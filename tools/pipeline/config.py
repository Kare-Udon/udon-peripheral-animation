"""Shared pipeline defaults."""

from __future__ import annotations

DEFAULT_TARGET_SIZE = (68, 140)
DEFAULT_ROTATED_SIZE = (140, 68)
DEFAULT_STAGE_ORDER = (
    "ingest",
    "compose",
    "grayscale",
    "quantize",
    "pattern",
    "cleanup",
    "preview",
    "export_lvgl",
)
