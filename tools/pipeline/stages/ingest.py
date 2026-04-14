"""Job initialization and input ingestion."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

from tools.pipeline.config import DEFAULT_ROTATED_SIZE, DEFAULT_STAGE_ORDER, DEFAULT_TARGET_SIZE
from tools.pipeline.models import JobManifest, StageRecord, StageStatus


def initialize_job(
    input_path: Path,
    artifacts_root: Path,
    job_id: str,
    preset: str = "anime",
    pattern_set: str = "default_2x2",
    levels: int = 5,
) -> JobManifest:
    job_root = artifacts_root / "jobs" / job_id
    input_dir = job_root / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    copied_input_path = input_dir / input_path.name
    shutil.copy2(input_path, copied_input_path)

    with Image.open(copied_input_path) as image:
        original_size = (image.width, image.height)

    stages: dict[str, StageRecord] = {}
    for name in DEFAULT_STAGE_ORDER:
        stages[name] = StageRecord(status=StageStatus.PENDING)

    stages["ingest"] = StageRecord(
        status=StageStatus.COMPLETED,
        outputs=[str(copied_input_path.relative_to(job_root))],
    )
    stages["compose"] = StageRecord(status=StageStatus.READY)

    manifest = JobManifest(
        job_id=job_id,
        mode="static",
        root_dir=job_root,
        input_path=copied_input_path,
        original_size=original_size,
        target_size=DEFAULT_TARGET_SIZE,
        rotated_size=DEFAULT_ROTATED_SIZE,
        preset=preset,
        pattern_set=pattern_set,
        levels=levels,
        stage_order=DEFAULT_STAGE_ORDER,
        current_stage="compose",
        stages=stages,
    )
    manifest.write(job_root / "manifest.json")
    return manifest
