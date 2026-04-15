"""CLI entrypoint for the stage-based image pipeline."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from tools.pipeline.models import JobManifest, StageStatus
from tools.pipeline.stages.ingest import initialize_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    job_parser = subparsers.add_parser("job")
    job_subparsers = job_parser.add_subparsers(dest="job_command", required=True)

    init_parser = job_subparsers.add_parser("init")
    init_parser.add_argument("input_path")
    init_parser.add_argument("--artifacts-root", default="artifacts")
    init_parser.add_argument("--job-id", required=True)
    init_parser.add_argument("--preset", default="anime")
    init_parser.add_argument("--pattern-set")
    init_parser.add_argument("--levels", type=int, default=5)

    status_parser = job_subparsers.add_parser("status")
    status_parser.add_argument("job_id")
    status_parser.add_argument("--artifacts-root", default="artifacts")

    stage_parser = subparsers.add_parser("stage")
    stage_subparsers = stage_parser.add_subparsers(dest="stage_command", required=True)

    next_parser = stage_subparsers.add_parser("next")
    next_parser.add_argument("job_id")
    next_parser.add_argument("--artifacts-root", default="artifacts")

    run_parser = stage_subparsers.add_parser("run")
    run_parser.add_argument("job_id")
    run_parser.add_argument("stage_name")
    run_parser.add_argument("--artifacts-root", default="artifacts")

    rerun_parser = stage_subparsers.add_parser("rerun")
    rerun_parser.add_argument("job_id")
    rerun_parser.add_argument("stage_name")
    rerun_parser.add_argument("--artifacts-root", default="artifacts")
    rerun_parser.add_argument("--set", dest="overrides", action="append", default=[])

    emit_parser = subparsers.add_parser("emit-zmk")
    emit_parser.add_argument("job_id")
    emit_parser.add_argument("--artifacts-root", default="artifacts")

    return parser


def _load_manifest(artifacts_root: Path, job_id: str) -> JobManifest:
    return JobManifest.read(artifacts_root / "jobs" / job_id / "manifest.json")


def _save_manifest(manifest: JobManifest) -> None:
    manifest.write(manifest.manifest_path())


def _find_first_actionable_stage(manifest: JobManifest) -> str | None:
    for stage_name in manifest.stage_order:
        if manifest.stages[stage_name].status is StageStatus.READY:
            return stage_name
    for stage_name in manifest.stage_order:
        if manifest.stages[stage_name].status is StageStatus.STALE:
            return stage_name
    return None


def _placeholder_output_for(stage_name: str) -> str:
    mapping = {
        "compose": "frames_work/001_composed.txt",
        "grayscale": "grayscale/001_gray.txt",
        "quantize": "quantized/001_levels.txt",
        "pattern": "patterned/001_bw.txt",
        "cleanup": "final_png/001_final.txt",
        "preview": "preview/001_contact.txt",
        "export_lvgl": "lvgl/generated_art.txt",
    }
    return mapping.get(stage_name, f"{stage_name}/output.txt")


def _run_placeholder_stage(manifest: JobManifest, stage_name: str) -> list[str]:
    relative_output = _placeholder_output_for(stage_name)
    output_path = manifest.root_dir / relative_output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"placeholder output for {stage_name}\n")
    return [relative_output]


def _execute_stage(manifest: JobManifest, stage_name: str) -> None:
    module_name = f"tools.pipeline.stages.{stage_name}"
    outputs: list[str]
    try:
        stage_module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        outputs = _run_placeholder_stage(manifest, stage_name)
    else:
        if hasattr(stage_module, "run_stage"):
            outputs = stage_module.run_stage(manifest)
        else:
            outputs = _run_placeholder_stage(manifest, stage_name)

    manifest.stages[stage_name].status = StageStatus.COMPLETED
    manifest.stages[stage_name].outputs = outputs
    manifest.stages[stage_name].error = None

    downstream = manifest.downstream_stages(stage_name)
    if downstream:
        next_stage = downstream[0]
        if manifest.stages[next_stage].status is StageStatus.PENDING:
            manifest.stages[next_stage].status = StageStatus.READY
        manifest.current_stage = next_stage
    else:
        manifest.current_stage = None


def _mark_downstream_stale(manifest: JobManifest, stage_name: str) -> None:
    downstream = manifest.downstream_stages(stage_name)
    for downstream_stage in downstream:
        manifest.stages[downstream_stage].status = StageStatus.STALE
    manifest.current_stage = downstream[0] if downstream else None


def _print_status(manifest: JobManifest) -> None:
    print(f"job_id: {manifest.job_id}")
    print(f"mode: {manifest.mode}")
    print(f"current_stage: {manifest.current_stage}")
    for stage_name in manifest.stage_order:
        print(f"{stage_name}: {manifest.stages[stage_name].status.value}")


def _parse_override(value: str):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value


def _apply_overrides(manifest: JobManifest, stage_name: str, overrides: list[str]) -> None:
    if not overrides:
        return
    for item in overrides:
        key, sep, value = item.partition("=")
        if not sep:
            raise ValueError(f"invalid override: {item}")
        manifest.stages[stage_name].params[key] = _parse_override(value)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "job" and args.job_command == "init":
        initialize_job(
            input_path=Path(args.input_path),
            artifacts_root=Path(args.artifacts_root),
            job_id=args.job_id,
            preset=args.preset,
            pattern_set=args.pattern_set,
            levels=args.levels,
        )
        return 0

    if args.command == "job" and args.job_command == "status":
        manifest = _load_manifest(Path(args.artifacts_root), args.job_id)
        _print_status(manifest)
        return 0

    if args.command == "stage" and args.stage_command == "next":
        manifest = _load_manifest(Path(args.artifacts_root), args.job_id)
        stage_name = _find_first_actionable_stage(manifest)
        if stage_name is None:
            parser.error("no actionable stage found")
        _execute_stage(manifest, stage_name)
        _save_manifest(manifest)
        return 0

    if args.command == "stage" and args.stage_command == "run":
        manifest = _load_manifest(Path(args.artifacts_root), args.job_id)
        status = manifest.stages[args.stage_name].status
        if status not in {StageStatus.READY, StageStatus.STALE}:
            parser.error(f"stage {args.stage_name} is not runnable from status {status.value}")
        _execute_stage(manifest, args.stage_name)
        _save_manifest(manifest)
        return 0

    if args.command == "stage" and args.stage_command == "rerun":
        manifest = _load_manifest(Path(args.artifacts_root), args.job_id)
        _apply_overrides(manifest, args.stage_name, args.overrides)
        _execute_stage(manifest, args.stage_name)
        _mark_downstream_stale(manifest, args.stage_name)
        _save_manifest(manifest)
        return 0

    if args.command == "emit-zmk":
        manifest = _load_manifest(Path(args.artifacts_root), args.job_id)
        cleanup_status = manifest.stages["cleanup"].status
        if cleanup_status is not StageStatus.COMPLETED:
            parser.error("cleanup stage must be completed before export")
        _execute_stage(manifest, "export_lvgl")
        _save_manifest(manifest)
        return 0

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
