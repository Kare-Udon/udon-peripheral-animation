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


def test_quantize_edge_boost_preserves_subtle_line_detail(tmp_path: Path):
    input_path = tmp_path / "detail.png"
    Image.new("RGB", (68, 140), color="white").save(input_path)

    assert (
        main(
            [
                "job",
                "init",
                str(input_path),
                "--artifacts-root",
                str(tmp_path / "artifacts"),
                "--job-id",
                "edge-boost-job",
                "--preset",
                "anime",
            ]
        )
        == 0
    )

    job_root = tmp_path / "artifacts" / "jobs" / "edge-boost-job"
    grayscale_dir = job_root / "grayscale"
    grayscale_dir.mkdir(parents=True, exist_ok=True)
    gray = Image.new("L", (68, 140), color=240)
    for y in range(20, 120):
        gray.putpixel((34, y), 220)
        gray.putpixel((35, y), 220)
    gray.save(grayscale_dir / "001_gray.png")

    manifest = JobManifest.read(job_root / "manifest.json")
    manifest.stages["compose"].status = StageStatus.COMPLETED
    manifest.stages["grayscale"].status = StageStatus.COMPLETED
    manifest.stages["grayscale"].outputs = ["grayscale/001_gray.png"]
    manifest.stages["quantize"].status = StageStatus.READY
    manifest.stages["quantize"].params = {
        "subject_aware": False,
        "base_thresholds": [42, 96, 150, 208],
        "thresholds": [42, 96, 150, 208],
        "edge_boost": 1,
        "edge_threshold": 10,
    }
    manifest.write(job_root / "manifest.json")

    assert (
        main(
            [
                "stage",
                "run",
                "edge-boost-job",
                "quantize",
                "--artifacts-root",
                str(tmp_path / "artifacts"),
            ]
        )
        == 0
    )

    boosted = np.array(Image.open(job_root / "quantized" / "001_levels.png").convert("L"))

    assert (
        main(
            [
                "stage",
                "rerun",
                "edge-boost-job",
                "quantize",
                "--artifacts-root",
                str(tmp_path / "artifacts"),
                "--set",
                "edge_boost=0",
            ]
        )
        == 0
    )

    unboosted = np.array(Image.open(job_root / "quantized" / "001_levels.png").convert("L"))
    boosted_band = boosted[20:120, 34:36].mean()
    unboosted_band = unboosted[20:120, 34:36].mean()

    assert boosted_band < unboosted_band


def test_quantize_subject_aware_thresholds_preserve_bright_subject_levels(tmp_path: Path):
    input_path = tmp_path / "subject.png"
    Image.new("RGB", (68, 140), color="white").save(input_path)

    assert (
        main(
            [
                "job",
                "init",
                str(input_path),
                "--artifacts-root",
                str(tmp_path / "artifacts"),
                "--job-id",
                "subject-aware-job",
                "--preset",
                "anime",
            ]
        )
        == 0
    )

    job_root = tmp_path / "artifacts" / "jobs" / "subject-aware-job"
    grayscale_dir = job_root / "grayscale"
    grayscale_dir.mkdir(parents=True, exist_ok=True)
    gray = Image.new("L", (68, 140), color=255)
    for y in range(32, 108):
        for x in range(18, 50):
            gray.putpixel((x, y), 236)
    for y in range(46, 94):
        for x in range(24, 44, 2):
            gray.putpixel((x, y), 224)
    gray.save(grayscale_dir / "001_gray.png")

    manifest = JobManifest.read(job_root / "manifest.json")
    manifest.stages["compose"].status = StageStatus.COMPLETED
    manifest.stages["grayscale"].status = StageStatus.COMPLETED
    manifest.stages["grayscale"].outputs = ["grayscale/001_gray.png"]
    manifest.stages["quantize"].status = StageStatus.READY
    manifest.stages["quantize"].params = {
        "base_thresholds": [42, 96, 150, 208],
        "thresholds": [42, 96, 150, 208],
        "subject_aware": True,
        "subject_percentiles": [35, 55, 74, 90],
        "subject_blend": 0.8,
        "edge_boost": 0,
    }
    manifest.write(job_root / "manifest.json")

    assert (
        main(
            [
                "stage",
                "run",
                "subject-aware-job",
                "quantize",
                "--artifacts-root",
                str(tmp_path / "artifacts"),
            ]
        )
        == 0
    )

    subject_aware = np.array(Image.open(job_root / "quantized" / "001_levels.png").convert("L"))

    assert (
        main(
            [
                "stage",
                "rerun",
                "subject-aware-job",
                "quantize",
                "--artifacts-root",
                str(tmp_path / "artifacts"),
                "--set",
                "subject_aware=false",
                "--set",
                "edge_boost=0",
            ]
        )
        == 0
    )

    fixed = np.array(Image.open(job_root / "quantized" / "001_levels.png").convert("L"))
    region = (slice(32, 108), slice(18, 50))

    assert np.count_nonzero(subject_aware[region] < 4) > np.count_nonzero(fixed[region] < 4)
