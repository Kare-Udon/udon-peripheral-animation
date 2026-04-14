from pathlib import Path

from tools.pipeline.models import JobManifest, StageRecord, StageStatus


def test_manifest_round_trip(tmp_path: Path):
    manifest = JobManifest(
        job_id="demo-job",
        mode="static",
        root_dir=tmp_path,
        input_path=tmp_path / "input" / "demo.png",
        original_size=(100, 200),
        target_size=(68, 140),
        rotated_size=(140, 68),
        preset="anime",
        pattern_set="default_2x2",
        levels=5,
        stage_order=("ingest", "compose"),
        current_stage="compose",
        stages={
            "ingest": StageRecord(status=StageStatus.COMPLETED),
            "compose": StageRecord(
                status=StageStatus.READY,
                params={"crop": "center"},
                outputs=["frames_work/001_composed.png"],
            ),
        },
    )

    manifest_path = tmp_path / "manifest.json"
    manifest.write(manifest_path)

    loaded = JobManifest.read(manifest_path)

    assert loaded.job_id == "demo-job"
    assert loaded.stages["ingest"].status is StageStatus.COMPLETED
    assert loaded.stages["compose"].params["crop"] == "center"
    assert loaded.stages["compose"].outputs == ["frames_work/001_composed.png"]


def test_stage_status_helpers():
    assert StageStatus.PENDING.value == "pending"
    assert StageStatus.READY.value == "ready"
    assert StageStatus.COMPLETED.value == "completed"
    assert StageStatus.FAILED.value == "failed"
    assert StageStatus.STALE.value == "stale"
