from pathlib import Path

from PIL import Image

from tools.pipeline.main import main
from tools.pipeline.models import JobManifest, StageStatus
from tools.pipeline.stages.export_lvgl import _pack_indexed_1bit


def test_pack_indexed_1bit_uses_black_as_set_bit():
    image = Image.new("L", (8, 1), color=255)
    for x in range(0, 8, 2):
        image.putpixel((x, 0), 0)

    assert _pack_indexed_1bit(image) == [0xAA]


def test_export_lvgl_generates_c_and_h_files(tmp_path: Path):
    input_path = tmp_path / "demo.png"
    image = Image.new("RGB", (90, 160), color="white")
    for x in range(90):
        for y in range(160):
            if (x // 5 + y // 5) % 2 == 0:
                image.putpixel((x, y), (0, 0, 0))
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

    for _ in range(7):
        assert main(["stage", "next", "demo-job", "--artifacts-root", str(tmp_path / "artifacts")]) == 0

    job_root = tmp_path / "artifacts" / "jobs" / "demo-job"
    c_path = job_root / "lvgl" / "demo_job.c"
    h_path = job_root / "lvgl" / "demo_job.h"

    assert c_path.exists()
    assert h_path.exists()

    c_text = c_path.read_text()
    h_text = h_path.read_text()

    assert "LV_IMG_CF_INDEXED_1BIT" in c_text
    assert "const lv_img_dsc_t demo_job =" in c_text
    assert "const lv_img_dsc_t demo_job_inverted =" in c_text
    assert "CONFIG_NICE_VIEW_WIDGET_INVERTED" not in c_text
    assert ".header.w = 140" in c_text
    assert ".header.h = 68" in c_text
    assert ".data_size = 1232" in c_text
    assert "extern const lv_img_dsc_t demo_job;" in h_text
    assert "extern const lv_img_dsc_t demo_job_inverted;" in h_text

    manifest = JobManifest.read(job_root / "manifest.json")
    assert manifest.stages["export_lvgl"].status is StageStatus.COMPLETED
    assert manifest.current_stage is None
