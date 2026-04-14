from pathlib import Path

from PIL import Image

from tools.pipeline.main import main
from tools.pipeline.models import JobManifest, StageStatus


def test_stage_rerun_applies_parameter_overrides(tmp_path: Path):
    input_path = tmp_path / "demo.png"
    Image.new("RGB", (80, 120), color="white").save(input_path)

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
    assert main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0
    assert main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0

    exit_code = main(
        [
            "stage",
            "rerun",
            "demo-job",
            "grayscale",
            "--artifacts-root",
            str(tmp_path / "artifacts"),
            "--set",
            "gamma=0.5",
            "--set",
            "contrast=1.3",
        ]
    )

    assert exit_code == 0

    manifest = JobManifest.read(tmp_path / "artifacts" / "jobs" / "demo-job" / "manifest.json")
    assert manifest.stages["grayscale"].status is StageStatus.COMPLETED
    assert manifest.stages["grayscale"].params["gamma"] == 0.5
    assert manifest.stages["grayscale"].params["contrast"] == 1.3
    assert manifest.stages["quantize"].status is StageStatus.STALE
