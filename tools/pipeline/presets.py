"""Preset values for the pipeline."""

from __future__ import annotations

PRESETS: dict[str, dict[str, object]] = {
    "portrait": {
        "contrast": 1.1,
        "gamma": 0.95,
        "thresholds": [51, 102, 153, 204],
    },
    "anime": {
        "contrast": 1.15,
        "gamma": 0.92,
        "thresholds": [42, 96, 150, 208],
    },
    "icon": {
        "contrast": 1.2,
        "gamma": 1.0,
        "thresholds": [64, 112, 160, 224],
    },
    "photo": {
        "contrast": 1.05,
        "gamma": 0.98,
        "thresholds": [48, 96, 144, 200],
    },
}


def get_preset(name: str) -> dict[str, object]:
    return dict(PRESETS.get(name, PRESETS["anime"]))
