import numpy as np

from tools.pipeline.stages.subject import (
    adaptive_thresholds,
    apply_highlight_rolloff,
    estimate_subject_mask,
)


def test_estimate_subject_mask_finds_bright_subject_on_white_background():
    pixels = np.full((12, 12), 255, dtype=np.uint8)
    pixels[3:9, 4:8] = 228

    mask, bbox = estimate_subject_mask(pixels, background_threshold=248, margin=1)

    assert mask.sum() == 24
    assert bbox == (3, 2, 9, 10)


def test_apply_highlight_rolloff_only_darkens_subject_region():
    pixels = np.full((10, 10), 255, dtype=np.uint8)
    pixels[2:8, 2:8] = 236
    pixels[4:6, 4:6] = 246
    mask = np.zeros((10, 10), dtype=bool)
    mask[2:8, 2:8] = True

    rolled = apply_highlight_rolloff(pixels, mask, start=220, strength=0.35)

    assert rolled[0, 0] == 255
    assert rolled[4, 4] < pixels[4, 4]
    assert rolled[2:8, 2:8].mean() < pixels[2:8, 2:8].mean()


def test_adaptive_thresholds_raise_cutoffs_for_bright_subject():
    base = [64, 112, 160, 224]
    subject_pixels = np.array([205, 210, 216, 220, 226, 232, 238, 244], dtype=np.uint8)

    adapted = adaptive_thresholds(
        base_thresholds=base,
        subject_pixels=subject_pixels,
        percentiles=[20, 45, 70, 90],
        blend=0.9,
    )

    assert adapted[0] > base[0]
    assert adapted[1] > base[1]
    assert adapted[2] > base[2]
    assert adapted[0] < adapted[1] < adapted[2] < adapted[3]
