from pathlib import Path

from PIL import Image

from tools.pipeline.main import main
from tools.pipeline.models import JobManifest, StageStatus


def test_job_init_creates_manifest_and_input_copy(tmp_path: Path):
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

    job_root = tmp_path / "artifacts" / "jobs" / "demo-job"
    manifest_path = job_root / "manifest.json"

    assert manifest_path.exists()
    assert (job_root / "input" / "demo.png").exists()

    manifest = JobManifest.read(manifest_path)
    assert manifest.current_stage == "compose"
    assert manifest.stages["ingest"].status is StageStatus.COMPLETED
    assert manifest.stages["compose"].status is StageStatus.READY


def test_job_init_uses_preset_pattern_set_when_not_overridden(tmp_path: Path):
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
            "anime-job",
            "--preset",
            "anime",
        ]
    )

    assert exit_code == 0

    manifest = JobManifest.read(tmp_path / "artifacts" / "jobs" / "anime-job" / "manifest.json")
    assert manifest.pattern_set == "soft_4x4"
