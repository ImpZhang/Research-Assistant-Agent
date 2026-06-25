from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.research.config import settings
from backend.research.models import ExperimentPlan, ExperimentRun, ResearchTask
from backend.research.services.experiment_run_service import ExperimentRunService


BUILTIN_BENCHMARK_PROFILES: list[dict[str, Any]] = [
    {
        "id": "json-metrics-smoke",
        "label": "JSON metrics smoke",
        "description": "Runs a tiny local command that emits a benchmark metrics JSON payload.",
        "benchmark_name": "Workbench benchmark smoke",
        "dataset": "local-smoke",
        "split": "validation",
        "baseline_name": "recorded baseline",
        "primary_metric": "primary_metric",
        "metric_direction": "higher_is_better",
        "command_args": [
            "python3",
            "-c",
            "import json; print(json.dumps({'metrics': {'primary_metric': {'value': 0.0}}}))",
        ],
        "working_directory": ".",
        "metrics_output_path": "",
        "parse_stdout_json": True,
        "timeout_seconds": 30,
        "required_paths": [],
        "config": {"profile_kind": "smoke"},
    },
    {
        "id": "geoloc-country-accuracy-jsonl",
        "label": "Geolocalization country accuracy JSONL",
        "description": (
            "Evaluates geolocalization predictions against project-local JSONL ground truth "
            "and emits country accuracy plus optional geodesic-distance metrics."
        ),
        "benchmark_name": "Geolocalization country accuracy",
        "dataset": "project-local geoloc JSONL",
        "split": "validation",
        "baseline_name": "nearest recorded baseline",
        "primary_metric": "country_accuracy",
        "metric_direction": "higher_is_better",
        "command_args": [
            "python3",
            "scripts/benchmark_geoloc_predictions.py",
            "--ground-truth",
            "data/benchmarks/geoloc/validation.jsonl",
            "--predictions",
            "outputs/predictions/geoloc/validation.jsonl",
            "--baseline-country-accuracy",
            "0.0",
        ],
        "working_directory": ".",
        "metrics_output_path": "",
        "parse_stdout_json": True,
        "timeout_seconds": 120,
        "required_paths": [
            "scripts/benchmark_geoloc_predictions.py",
            "data/benchmarks/geoloc/validation.jsonl",
            "outputs/predictions/geoloc/validation.jsonl",
        ],
        "config": {
            "profile_kind": "geolocalization",
            "ground_truth_path": "data/benchmarks/geoloc/validation.jsonl",
            "predictions_path": "outputs/predictions/geoloc/validation.jsonl",
            "metric_contract": "country_accuracy plus optional mean/median geodesic km",
        },
    },
]


def list_benchmark_profile_payloads(project_root: Path | None = None) -> list[dict[str, Any]]:
    root = (project_root or Path.cwd()).resolve()
    profiles_by_id: dict[str, dict[str, Any]] = {}
    for profile in BUILTIN_BENCHMARK_PROFILES:
        normalized = _normalize_profile(profile, source="builtin")
        profiles_by_id[normalized["id"]] = normalized
    for profile in _load_manifest_profiles(root):
        normalized = _normalize_profile(profile, source="manifest")
        profiles_by_id[normalized["id"]] = normalized
    return [_profile_payload(profile, root) for profile in profiles_by_id.values()]


def get_benchmark_profile_payload(
    profile_id: str, project_root: Path | None = None
) -> dict[str, Any]:
    normalized_id = profile_id.strip()
    if not normalized_id:
        raise ValueError("Benchmark profile_id is empty.")
    for profile in list_benchmark_profile_payloads(project_root):
        if profile["id"] == normalized_id:
            return profile
    raise ValueError(f"Benchmark profile not found: {normalized_id}")


def benchmark_profile_manifest_path(project_root: Path | None = None) -> str:
    root = (project_root or Path.cwd()).resolve()
    return _relative_path(_manifest_path(root), root)


def benchmark_runner_enabled() -> bool:
    return _runner_enabled()


def benchmark_profile_summary(project_root: Path | None = None) -> dict[str, Any]:
    root = (project_root or Path.cwd()).resolve()
    try:
        manifest_path = benchmark_profile_manifest_path(root)
    except ValueError:
        manifest_path = (
            os.getenv("BENCHMARK_PROFILE_MANIFEST_PATH") or settings.benchmark_profile_manifest_path
        )
    try:
        profiles = list_benchmark_profile_payloads(root)
    except ValueError as exc:
        return {
            "ok": False,
            "manifest_path": manifest_path,
            "profile_count": 0,
            "runnable_profile_count": 0,
            "runnable_profiles": [],
            "error": str(exc),
        }
    return {
        "ok": True,
        "manifest_path": manifest_path,
        "profile_count": len(profiles),
        "runnable_profile_count": sum(1 for profile in profiles if profile["runnable"]),
        "runnable_profiles": [profile["id"] for profile in profiles if profile["runnable"]],
    }


class BenchmarkCommandRunnerService:
    def __init__(self, session: Session):
        self.session = session

    def execute(
        self,
        experiment_plan_id: str,
        *,
        title: str = "",
        task_id: str | None = None,
        profile_id: str = "",
        benchmark_name: str = "Primary benchmark",
        dataset: str = "",
        split: str = "",
        baseline_name: str = "",
        primary_metric: str = "",
        metric_direction: str = "higher_is_better",
        candidate_result: float | None = None,
        baseline_result: float | None = None,
        metric_results: dict[str, Any] | None = None,
        command_args: list[str] | None = None,
        working_directory: str = ".",
        metrics_output_path: str = "",
        parse_stdout_json: bool = True,
        config: dict[str, Any] | None = None,
        artifact_links: list[dict[str, Any]] | None = None,
        timeout_seconds: int | None = None,
        reproducibility_notes: str = "",
        created_by: str = "system",
    ) -> ExperimentRun:
        if not _runner_enabled():
            raise PermissionError("Benchmark command runner is disabled.")
        plan = self.session.get(ExperimentPlan, experiment_plan_id)
        if plan is None:
            raise ValueError("Experiment plan not found")
        self._validate_task(task_id, plan.idea_id)

        project_root = Path.cwd().resolve()
        profile = None
        if profile_id.strip():
            profile = get_benchmark_profile_payload(profile_id, project_root)
            if not command_args and not profile["runnable"]:
                reason = profile["disabled_reason"] or "profile is not runnable"
                raise ValueError(f"Benchmark profile {profile['id']} is not runnable: {reason}")
            title = title or f"Benchmark profile execution - {profile['label']}"
            benchmark_name = _profile_text_value(
                benchmark_name,
                default_value="Primary benchmark",
                profile_value=profile["benchmark_name"],
            )
            dataset = _profile_text_value(
                dataset, default_value="", profile_value=profile["dataset"]
            )
            split = _profile_text_value(split, default_value="", profile_value=profile["split"])
            baseline_name = _profile_text_value(
                baseline_name,
                default_value="",
                profile_value=profile["baseline_name"],
            )
            primary_metric = _profile_text_value(
                primary_metric,
                default_value="",
                profile_value=profile["primary_metric"],
            )
            if metric_direction == "higher_is_better":
                metric_direction = profile["metric_direction"] or metric_direction
            command_args = command_args or profile["command_args"]
            if working_directory == ".":
                working_directory = profile["working_directory"] or "."
            metrics_output_path = metrics_output_path or profile["metrics_output_path"]
            if timeout_seconds is None:
                timeout_seconds = profile["timeout_seconds"]
            config = {
                **(profile.get("config") or {}),
                **(config or {}),
                "benchmark_profile_id": profile["id"],
                "benchmark_profile_source": profile["source"],
            }

        args = self._validate_command_args(command_args or [])
        work_dir = self._safe_working_directory(project_root, working_directory)
        run_dir = self._prepare_run_dir(project_root)
        timeout = timeout_seconds or _runner_timeout_seconds()

        started_at = datetime.now(UTC)
        started = time.perf_counter()
        stdout = ""
        stderr = ""
        exit_code: int | None = None
        timed_out = False
        error_type = ""
        try:
            completed = subprocess.run(
                args,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                check=False,
            )
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            exit_code = completed.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = _coerce_text(exc.stdout)
            stderr = _coerce_text(exc.stderr)
            exit_code = None
            timed_out = True
            error_type = "TimeoutExpired"
        except OSError as exc:
            stderr = str(exc)
            exit_code = None
            error_type = exc.__class__.__name__
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        completed_at = datetime.now(UTC)

        stdout_path = self._write_text(run_dir / "stdout.txt", stdout)
        stderr_path = self._write_text(run_dir / "stderr.txt", stderr)
        execution_payload = {
            "command_args": args,
            "working_directory": str(work_dir.relative_to(project_root)),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_ms": duration_ms,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "error_type": error_type,
            "timeout_seconds": timeout,
        }
        command_path = self._write_json(run_dir / "command.json", execution_payload)

        combined_metrics = dict(metric_results or {})
        if parse_stdout_json:
            combined_metrics.update(_extract_metrics_from_json_text(stdout))
        if metrics_output_path:
            combined_metrics.update(self._read_metrics_file(work_dir, metrics_output_path))
        metric_name = (primary_metric or "primary_metric").strip()
        combined_metrics.update(
            _benchmark_delta_metric(
                metric_name=metric_name,
                metric_direction=metric_direction,
                candidate_result=candidate_result,
                baseline_result=baseline_result,
            )
        )
        metrics_path = self._write_json(run_dir / "metrics.json", combined_metrics)

        status = self._run_status(exit_code, timed_out, combined_metrics)
        runner_artifacts = [
            {"label": "benchmark_stdout", "path": _relative_path(stdout_path, project_root)},
            {"label": "benchmark_stderr", "path": _relative_path(stderr_path, project_root)},
            {"label": "benchmark_command", "path": _relative_path(command_path, project_root)},
            {"label": "benchmark_metrics", "path": _relative_path(metrics_path, project_root)},
        ]
        parameters = {
            "execution_kind": "benchmark_command",
            "benchmark_name": benchmark_name.strip() or "Primary benchmark",
            "dataset": dataset.strip(),
            "split": split.strip(),
            "baseline_name": baseline_name.strip(),
            "primary_metric": metric_name,
            "metric_direction": metric_direction,
            "command_args": args,
            "working_directory": str(work_dir.relative_to(project_root)),
            "metrics_output_path": metrics_output_path.strip(),
            "parse_stdout_json": parse_stdout_json,
            "config": config or {},
            "dry_run": False,
            "runner": execution_payload,
            "runner_output_dir": _relative_path(run_dir, project_root),
        }
        if profile is not None:
            parameters["benchmark_profile"] = {
                "id": profile["id"],
                "label": profile["label"],
                "source": profile["source"],
            }
        return ExperimentRunService(self.session).create_run(
            experiment_plan_id,
            title=title or f"Benchmark execution - {parameters['benchmark_name']}",
            task_id=task_id,
            status=status,
            dataset_snapshot=_dataset_snapshot(parameters["benchmark_name"], dataset, split),
            parameters=parameters,
            metric_results=combined_metrics,
            artifact_links=[*(artifact_links or []), *runner_artifacts],
            conclusion=_execution_conclusion(
                benchmark_name=parameters["benchmark_name"],
                metric_name=metric_name,
                metrics=combined_metrics,
                status=status,
                exit_code=exit_code,
                timed_out=timed_out,
                error_type=error_type,
            ),
            notes=_execution_notes(
                command_args=args,
                reproducibility_notes=reproducibility_notes,
                run_dir=run_dir,
                project_root=project_root,
            ),
            created_by=created_by,
        )

    def _validate_task(self, task_id: str | None, idea_id: str) -> None:
        if not task_id:
            return
        task = self.session.get(ResearchTask, task_id)
        if task is None:
            raise ValueError("Research task not found")
        if task.idea_id and task.idea_id != idea_id:
            raise ValueError("Research task belongs to a different idea")

    def _validate_command_args(self, command_args: list[str]) -> list[str]:
        args = [str(item) for item in command_args if str(item).strip()]
        if not args:
            raise ValueError("Benchmark command_args must contain at least one argument.")
        command = args[0]
        command_key = Path(command).name
        allowed = _allowed_commands()
        if command not in allowed and command_key not in allowed:
            raise ValueError(
                "Benchmark command is not allowed by BENCHMARK_RUNNER_ALLOWED_COMMANDS."
            )
        return args

    def _safe_working_directory(self, project_root: Path, working_directory: str) -> Path:
        requested = working_directory.strip() or "."
        candidate = (project_root / requested).resolve()
        if candidate != project_root and project_root not in candidate.parents:
            raise ValueError("Benchmark working_directory must stay inside the project root.")
        if not candidate.exists() or not candidate.is_dir():
            raise ValueError("Benchmark working_directory does not exist.")
        return candidate

    def _prepare_run_dir(self, project_root: Path) -> Path:
        output_root = _output_root(project_root)
        output_root.mkdir(parents=True, exist_ok=True)
        run_dir = output_root / f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:10]}"
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    def _write_text(self, path: Path, text: str) -> Path:
        clipped = text[: _max_output_chars()]
        path.write_text(clipped, encoding="utf-8")
        return path

    def _write_json(self, path: Path, payload: dict[str, Any]) -> Path:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _read_metrics_file(self, work_dir: Path, metrics_output_path: str) -> dict[str, Any]:
        path = _safe_relative_file(work_dir, metrics_output_path)
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _normalize_metric_payload(payload)

    def _run_status(
        self,
        exit_code: int | None,
        timed_out: bool,
        metrics: dict[str, Any],
    ) -> str:
        if timed_out or exit_code not in {0, None}:
            return "failed"
        if exit_code is None:
            return "failed"
        if metrics:
            return "completed"
        return "inconclusive"


def _normalize_profile(profile: dict[str, Any], *, source: str) -> dict[str, Any]:
    raw_profile_id = str(profile.get("id", "")).strip()
    if not raw_profile_id:
        raise ValueError("Benchmark profile id is required.")
    raw_direction = str(profile.get("metric_direction", "higher_is_better")).strip()
    metric_direction = (
        raw_direction
        if raw_direction in {"higher_is_better", "lower_is_better"}
        else "higher_is_better"
    )
    timeout = profile.get("timeout_seconds")
    return {
        "id": raw_profile_id,
        "label": str(profile.get("label") or raw_profile_id).strip(),
        "description": str(profile.get("description", "")).strip(),
        "source": source,
        "benchmark_name": str(profile.get("benchmark_name") or "Primary benchmark").strip(),
        "dataset": str(profile.get("dataset", "")).strip(),
        "split": str(profile.get("split", "")).strip(),
        "baseline_name": str(profile.get("baseline_name", "")).strip(),
        "primary_metric": str(profile.get("primary_metric", "")).strip(),
        "metric_direction": metric_direction,
        "command_args": [
            str(item) for item in profile.get("command_args", []) if str(item).strip()
        ],
        "working_directory": str(profile.get("working_directory") or ".").strip(),
        "metrics_output_path": str(profile.get("metrics_output_path", "")).strip(),
        "parse_stdout_json": bool(profile.get("parse_stdout_json", True)),
        "timeout_seconds": int(timeout) if timeout is not None else None,
        "required_paths": [
            str(item) for item in profile.get("required_paths", []) if str(item).strip()
        ],
        "config": dict(profile.get("config") or {}),
    }


def _profile_payload(profile: dict[str, Any], project_root: Path) -> dict[str, Any]:
    missing_paths = _missing_profile_paths(project_root, profile["required_paths"])
    disabled_reason = _profile_disabled_reason(project_root, profile, missing_paths)
    return {
        **profile,
        "runnable": not disabled_reason,
        "disabled_reason": disabled_reason,
        "missing_paths": missing_paths,
    }


def _profile_disabled_reason(
    project_root: Path,
    profile: dict[str, Any],
    missing_paths: list[str],
) -> str:
    if not _runner_enabled():
        return "Benchmark runner is disabled."
    if not profile["command_args"]:
        return "Profile has no command_args."
    if not _profile_command_allowed(profile["command_args"]):
        return "Profile command is not allowed by BENCHMARK_RUNNER_ALLOWED_COMMANDS."
    try:
        requested_work_dir = profile["working_directory"] or "."
        work_dir = _safe_profile_path(project_root, requested_work_dir)
    except ValueError as exc:
        return str(exc)
    if not work_dir.exists() or not work_dir.is_dir():
        return "Profile working_directory does not exist."
    if missing_paths:
        return "Profile is missing required project paths: " + ", ".join(missing_paths)
    return ""


def _profile_command_allowed(command_args: list[str]) -> bool:
    if not command_args:
        return False
    command = command_args[0]
    command_key = Path(command).name
    allowed = _allowed_commands()
    return command in allowed or command_key in allowed


def _missing_profile_paths(project_root: Path, required_paths: list[str]) -> list[str]:
    missing = []
    for raw_path in required_paths:
        path = _safe_profile_path(project_root, raw_path)
        if not path.exists():
            missing.append(raw_path)
    return missing


def _safe_profile_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    candidate = path if path.is_absolute() else project_root / path
    resolved = candidate.resolve()
    if resolved != project_root and project_root not in resolved.parents:
        raise ValueError("Benchmark profile paths must stay inside the project root.")
    return resolved


def _load_manifest_profiles(project_root: Path) -> list[dict[str, Any]]:
    manifest = _manifest_path(project_root)
    if not manifest.exists():
        return []
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("profiles"), list):
        return [item for item in payload["profiles"] if isinstance(item, dict)]
    raise ValueError("Benchmark profile manifest must be a JSON list or object with profiles list.")


def _manifest_path(project_root: Path) -> Path:
    configured = (
        os.getenv("BENCHMARK_PROFILE_MANIFEST_PATH") or settings.benchmark_profile_manifest_path
    )
    path = Path(configured)
    candidate = path if path.is_absolute() else project_root / path
    resolved = candidate.resolve()
    if resolved != project_root and project_root not in resolved.parents:
        raise ValueError("BENCHMARK_PROFILE_MANIFEST_PATH must stay inside the project root.")
    return resolved


def _profile_text_value(value: str, *, default_value: str, profile_value: str) -> str:
    text = (value or "").strip()
    if not text or text == default_value:
        return profile_value or text
    return text


def _runner_enabled() -> bool:
    raw = os.getenv("BENCHMARK_RUNNER_ENABLED")
    if raw is None:
        return settings.benchmark_runner_enabled
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _runner_timeout_seconds() -> int:
    raw = os.getenv("BENCHMARK_RUNNER_TIMEOUT_SECONDS")
    if raw:
        return max(1, min(int(raw), 3600))
    return settings.benchmark_runner_timeout_seconds


def _allowed_commands() -> set[str]:
    raw = os.getenv("BENCHMARK_RUNNER_ALLOWED_COMMANDS")
    configured = raw if raw is not None else settings.benchmark_runner_allowed_commands
    return {item.strip() for item in configured.split(",") if item.strip()}


def _max_output_chars() -> int:
    raw = os.getenv("BENCHMARK_RUNNER_MAX_OUTPUT_CHARS")
    if raw:
        return max(1000, int(raw))
    return settings.benchmark_runner_max_output_chars


def _output_root(project_root: Path) -> Path:
    configured = os.getenv("BENCHMARK_RUNNER_OUTPUT_DIR") or settings.benchmark_runner_output_dir
    path = Path(configured)
    candidate = path if path.is_absolute() else project_root / path
    resolved = candidate.resolve()
    if resolved != project_root and project_root not in resolved.parents:
        raise ValueError("BENCHMARK_RUNNER_OUTPUT_DIR must stay inside the project root.")
    return resolved


def _safe_relative_file(work_dir: Path, raw_path: str) -> Path:
    if not raw_path.strip():
        raise ValueError("metrics_output_path is empty.")
    path = Path(raw_path)
    if path.is_absolute():
        raise ValueError("metrics_output_path must be relative.")
    resolved = (work_dir / path).resolve()
    if resolved != work_dir and work_dir not in resolved.parents:
        raise ValueError("metrics_output_path must stay inside the working directory.")
    return resolved


def _extract_metrics_from_json_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {}
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return {}
    return _normalize_metric_payload(payload)


def _normalize_metric_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else payload
    return dict(metrics) if isinstance(metrics, dict) else {}


def _benchmark_delta_metric(
    *,
    metric_name: str,
    metric_direction: str,
    candidate_result: float | None,
    baseline_result: float | None,
) -> dict[str, Any]:
    if candidate_result is None and baseline_result is None:
        return {}
    delta = None
    improved = None
    if candidate_result is not None and baseline_result is not None:
        delta = round(float(candidate_result) - float(baseline_result), 6)
        improved = delta > 0 if metric_direction == "higher_is_better" else delta < 0
    return {
        metric_name: {
            "value": candidate_result,
            "candidate": candidate_result,
            "baseline": baseline_result,
            "delta": delta,
            "direction": metric_direction,
            "improved": improved,
            "dry_run": False,
        }
    }


def _dataset_snapshot(benchmark_name: str, dataset: str, split: str) -> str:
    parts = [benchmark_name.strip() or "Primary benchmark"]
    if dataset.strip():
        parts.append(f"dataset={dataset.strip()}")
    if split.strip():
        parts.append(f"split={split.strip()}")
    return "; ".join(parts)


def _execution_conclusion(
    *,
    benchmark_name: str,
    metric_name: str,
    metrics: dict[str, Any],
    status: str,
    exit_code: int | None,
    timed_out: bool,
    error_type: str,
) -> str:
    if timed_out:
        return f"{benchmark_name} timed out before producing a final benchmark result."
    if status == "failed":
        return f"{benchmark_name} failed with exit code {exit_code}; inspect captured artifacts."
    primary = metrics.get(metric_name)
    if isinstance(primary, dict) and primary.get("improved") is True:
        return f"{benchmark_name} improved on {metric_name} against the recorded baseline."
    if isinstance(primary, dict) and primary.get("improved") is False:
        return f"{benchmark_name} did not improve on {metric_name} against the recorded baseline."
    if status == "completed":
        return f"{benchmark_name} completed with captured benchmark metrics."
    if error_type:
        return f"{benchmark_name} ended without metrics after {error_type}."
    return f"{benchmark_name} ended without captured benchmark metrics."


def _execution_notes(
    *,
    command_args: list[str],
    reproducibility_notes: str,
    run_dir: Path,
    project_root: Path,
) -> str:
    notes = [
        "Benchmark execution mode: local command runner.",
        "Command args: " + json.dumps(command_args, ensure_ascii=False),
        f"Runner artifacts: {_relative_path(run_dir, project_root)}",
    ]
    if reproducibility_notes.strip():
        notes.append(reproducibility_notes.strip())
    return "\n".join(notes)


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
