from pathlib import Path

import numpy as np
from PIL import Image

from tools.pipeline.main import main
from tools.pipeline.models import JobManifest, StageStatus


def test_cleanup_and_preview_outputs(tmp_path: Path):
    input_path = tmp_path / "demo.png"
    image = Image.new("RGB", (120, 80), color="black")
    for x in range(120):
        for y in range(80):
            if (x + y) % 7 == 0:
                image.putpixel((x, y), (255, 255, 255))
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

    for _ in range(6):
        assert main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0

    job_root = tmp_path / "artifacts" / "jobs" / "demo-job"
    final_image = Image.open(job_root / "final_png" / "001_final.png")
    preview_image = Image.open(job_root / "preview" / "001_contact.png")

    assert set(np.unique(np.array(final_image)).tolist()).issubset({0, 255})
    assert preview_image.size[0] > 68
    assert preview_image.size[1] > 140

    manifest = JobManifest.read(job_root / "manifest.json")
    assert manifest.stages["cleanup"].status is StageStatus.COMPLETED
    assert manifest.stages["preview"].status is StageStatus.COMPLETED
    assert manifest.stages["export_lvgl"].status is StageStatus.READY
