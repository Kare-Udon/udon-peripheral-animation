from pathlib import Path

from PIL import Image

from tools.pipeline.main import main
from tools.pipeline.models import JobManifest, StageStatus


def _init_job(tmp_path: Path) -> Path:
    input_path = tmp_path / "demo.png"
    Image.new("RGB", (20, 30), color="white").save(input_path)
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
    return tmp_path / "artifacts" / "jobs" / "demo-job" / "manifest.json"


def test_stage_next_executes_first_ready_stage(tmp_path: Path):
    manifest_path = _init_job(tmp_path)

    exit_code = main(
        [
            "stage",
            "next",
            "demo-job",
            "--artifacts-root",
            str(tmp_path / "artifacts"),
        ]
    )

    assert exit_code == 0

    manifest = JobManifest.read(manifest_path)
    assert manifest.stages["compose"].status is StageStatus.COMPLETED
    assert manifest.stages["compose"].outputs == ["frames_work/001_composed.png"]
    assert manifest.stages["grayscale"].status is StageStatus.READY
    assert manifest.current_stage == "grayscale"


def test_stage_rerun_marks_downstream_stale(tmp_path: Path):
    manifest_path = _init_job(tmp_path)

    assert (
        main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0
    )
    assert (
        main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0
    )

    exit_code = main(
        [
            "stage",
            "rerun",
            "demo-job",
            "compose",
            "--artifacts-root",
            str(tmp_path / "artifacts"),
        ]
    )

    assert exit_code == 0

    manifest = JobManifest.read(manifest_path)
    assert manifest.stages["compose"].status is StageStatus.COMPLETED
    assert manifest.stages["grayscale"].status is StageStatus.STALE
    assert manifest.stages["quantize"].status is StageStatus.STALE


def test_job_status_prints_stage_summary(tmp_path: Path, capsys):
    _init_job(tmp_path)

    exit_code = main(
        [
            "job",
            "status",
            "demo-job",
            "--artifacts-root",
            str(tmp_path / "artifacts"),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "demo-job" in output
    assert "compose: ready" in output
