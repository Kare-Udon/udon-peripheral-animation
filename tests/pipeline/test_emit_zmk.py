from pathlib import Path

from PIL import Image

from tools.pipeline.main import main
from tools.pipeline.models import JobManifest, StageStatus


def test_emit_zmk_exports_from_existing_job(tmp_path: Path):
    input_path = tmp_path / "demo.png"
    Image.new("RGB", (90, 160), color="white").save(input_path)

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

    for _ in range(6):
        assert main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0

    exit_code = main(
        [
            "emit-zmk",
            "demo-job",
            "--artifacts-root",
            str(tmp_path / "artifacts"),
        ]
    )

    assert exit_code == 0

    job_root = tmp_path / "artifacts" / "jobs" / "demo-job"
    assert (job_root / "lvgl" / "demo_job.c").exists()
    assert (job_root / "lvgl" / "demo_job.h").exists()

    manifest = JobManifest.read(job_root / "manifest.json")
    assert manifest.stages["export_lvgl"].status is StageStatus.COMPLETED
