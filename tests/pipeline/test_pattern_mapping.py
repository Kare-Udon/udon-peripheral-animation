from pathlib import Path

import numpy as np
from PIL import Image

from tools.pipeline.main import main
from tools.pipeline.models import JobManifest, StageStatus


def _run_until_pattern(tmp_path: Path) -> tuple[Path, Path]:
    input_path = tmp_path / "demo.png"
    image = Image.new("RGB", (96, 96))
    for x in range(96):
        for y in range(96):
            value = int((x + y) / 192 * 255)
            image.putpixel((x, y), (value, value, value))
    image.save(input_path)

    assert (
        main(
            [
                "job",
                "init",
                str(input_path),
                "--artifacts-root",
                str(tmp_path / "artifacts"),
                "--job-id",
                "demo-job",
                "--pattern-set",
                "default_2x2",
            ]
        )
        == 0
    )

    for _ in range(4):
        assert main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0

    job_root = tmp_path / "artifacts" / "jobs" / "demo-job"
    return job_root, job_root / "manifest.json"


def test_pattern_stage_emits_black_and_white_pixels(tmp_path: Path):
    job_root, manifest_path = _run_until_pattern(tmp_path)

    patterned = Image.open(job_root / "patterned" / "001_bw.png")
    values = np.unique(np.array(patterned))

    assert patterned.mode == "L"
    assert set(values.tolist()).issubset({0, 255})

    manifest = JobManifest.read(manifest_path)
    assert manifest.stages["pattern"].status is StageStatus.COMPLETED
    assert manifest.stages["cleanup"].status is StageStatus.READY


def test_cleanup_preserves_sparse_dither_by_default(tmp_path: Path):
    job_root, manifest_path = _run_until_pattern(tmp_path)

    assert main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0

    patterned = np.array(Image.open(job_root / "patterned" / "001_bw.png").convert("L"))
    cleaned = np.array(Image.open(job_root / "final_png" / "001_final.png").convert("L"))

    assert np.count_nonzero(patterned == 0) <= np.count_nonzero(cleaned == 0)

    manifest = JobManifest.read(manifest_path)
    assert manifest.stages["cleanup"].params["fill_white_holes"] is False


def test_pattern_stage_uses_selected_pattern_set(tmp_path: Path):
    job_root, manifest_path = _run_until_pattern(tmp_path)

    patterned_default = np.array(Image.open(job_root / "patterned" / "001_bw.png").convert("L"))

    assert (
        main(
            [
                "stage",
                "rerun",
                "demo-job",
                "pattern",
                "--artifacts-root",
                str(tmp_path / "artifacts"),
                "--set",
                "pattern_set=soft_4x4",
            ]
        )
        == 0
    )

    patterned_soft = np.array(Image.open(job_root / "patterned" / "001_bw.png").convert("L"))

    assert not np.array_equal(patterned_default, patterned_soft)

    manifest = JobManifest.read(manifest_path)
    assert manifest.stages["pattern"].params["pattern_set"] == "soft_4x4"
