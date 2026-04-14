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
