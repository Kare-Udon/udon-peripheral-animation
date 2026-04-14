from pathlib import Path

import numpy as np
from PIL import Image

from tools.pipeline.main import main
from tools.pipeline.models import JobManifest, StageStatus


def _init_job(tmp_path: Path) -> tuple[Path, Path]:
    input_path = tmp_path / "demo.png"
    image = Image.new("RGB", (100, 60))
    for x in range(100):
        for y in range(60):
            image.putpixel((x, y), (x * 2 % 255, y * 4 % 255, (x + y) % 255))
    image.save(input_path)

    exit_code = main(
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
    assert exit_code == 0
    job_root = tmp_path / "artifacts" / "jobs" / "demo-job"
    return job_root, job_root / "manifest.json"


def test_compose_grayscale_quantize_outputs(tmp_path: Path):
    job_root, manifest_path = _init_job(tmp_path)

    assert main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0
    assert main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0
    assert main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0

    composed = Image.open(job_root / "frames_work" / "001_composed.png")
    grayscale = Image.open(job_root / "grayscale" / "001_gray.png")
    quantized = Image.open(job_root / "quantized" / "001_levels.png")

    assert composed.size == (68, 140)
    assert grayscale.mode == "L"
    assert quantized.mode == "L"

    quantized_values = np.unique(np.array(quantized))
    assert set(quantized_values.tolist()).issubset({0, 1, 2, 3, 4})

    manifest = JobManifest.read(manifest_path)
    assert manifest.stages["compose"].status is StageStatus.COMPLETED
    assert manifest.stages["grayscale"].status is StageStatus.COMPLETED
    assert manifest.stages["quantize"].status is StageStatus.COMPLETED
    assert manifest.stages["pattern"].status is StageStatus.READY
