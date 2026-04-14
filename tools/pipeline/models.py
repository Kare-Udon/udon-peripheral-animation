"""Core models for pipeline jobs and stage state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class StageStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"


@dataclass
class StageRecord:
    status: StageStatus
    params: dict[str, Any] = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status": self.status.value,
            "params": self.params,
            "outputs": self.outputs,
        }
        if self.error is not None:
            data["error"] = self.error
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StageRecord":
        return cls(
            status=StageStatus(data["status"]),
            params=dict(data.get("params", {})),
            outputs=list(data.get("outputs", [])),
            error=data.get("error"),
        )


@dataclass
class JobManifest:
    job_id: str
    mode: str
    root_dir: Path
    input_path: Path
    original_size: tuple[int, int]
    target_size: tuple[int, int]
    rotated_size: tuple[int, int]
    preset: str
    pattern_set: str
    levels: int
    stage_order: tuple[str, ...]
    current_stage: str | None
    stages: dict[str, StageRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "mode": self.mode,
            "root_dir": str(self.root_dir),
            "input": {
                "path": str(self.input_path),
                "original_size": list(self.original_size),
            },
            "target": {
                "width": self.target_size[0],
                "height": self.target_size[1],
                "rotated_width": self.rotated_size[0],
                "rotated_height": self.rotated_size[1],
            },
            "preset": self.preset,
            "pattern_set": self.pattern_set,
            "levels": self.levels,
            "stage_order": list(self.stage_order),
            "current_stage": self.current_stage,
            "stages": {name: record.to_dict() for name, record in self.stages.items()},
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n")

    def manifest_path(self) -> Path:
        return self.root_dir / "manifest.json"

    def stage_index(self, stage_name: str) -> int:
        return self.stage_order.index(stage_name)

    def downstream_stages(self, stage_name: str) -> tuple[str, ...]:
        return self.stage_order[self.stage_index(stage_name) + 1 :]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobManifest":
        target = data["target"]
        input_data = data["input"]
        return cls(
            job_id=data["job_id"],
            mode=data["mode"],
            root_dir=Path(data["root_dir"]),
            input_path=Path(input_data["path"]),
            original_size=tuple(input_data["original_size"]),
            target_size=(target["width"], target["height"]),
            rotated_size=(target["rotated_width"], target["rotated_height"]),
            preset=data["preset"],
            pattern_set=data["pattern_set"],
            levels=data["levels"],
            stage_order=tuple(data["stage_order"]),
            current_stage=data.get("current_stage"),
            stages={
                name: StageRecord.from_dict(record)
                for name, record in data.get("stages", {}).items()
            },
        )

    @classmethod
    def read(cls, path: Path) -> "JobManifest":
        return cls.from_dict(json.loads(path.read_text()))
