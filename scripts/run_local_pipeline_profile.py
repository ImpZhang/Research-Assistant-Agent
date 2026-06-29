#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_PATH = "configs/local_pipeline_profiles.json"
ALLOWED_EXECUTABLES = {"bash", "python3", ".venv/bin/python"}


def main() -> int:
    args = parse_args()
    profiles = load_profiles(resolve_project_path(args.profile_manifest))
    if args.list:
        print(
            json.dumps(
                {"profiles": summarize_profiles(profiles)}, ensure_ascii=False, sort_keys=True
            )
        )
        return 0
    if not args.profile:
        raise SystemExit("--profile is required unless --list is used")
    profile = profiles.get(args.profile)
    if profile is None:
        raise SystemExit(f"unknown profile: {args.profile}")
    report = run_profile(
        profile,
        dry_run=args.dry_run,
        allow_external=args.allow_external
        or os.getenv("ALLOW_REAL_PIPELINE_PROFILE", "").lower() in {"1", "true", "yes", "on"},
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] in {"completed", "dry_run"} else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List or run committed local pipeline profiles without printing secrets."
    )
    parser.add_argument("--profile-manifest", default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--list", action="store_true", help="List available profiles as JSON.")
    parser.add_argument("--profile", default="", help="Profile id to run.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print resolved commands without running."
    )
    parser.add_argument(
        "--allow-external",
        action="store_true",
        help="Allow profiles that call external providers or real model APIs.",
    )
    return parser.parse_args()


def load_profiles(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = {}
    for profile in payload.get("profiles") or []:
        profile_id = str(profile.get("id") or "")
        if not profile_id:
            raise SystemExit("profile without id")
        if profile_id in profiles:
            raise SystemExit(f"duplicate profile id: {profile_id}")
        profiles[profile_id] = profile
    return profiles


def summarize_profiles(profiles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": profile_id,
            "description": profile.get("description", ""),
            "external_provider": bool(profile.get("external_provider")),
            "command_count": len(profile.get("commands") or []),
        }
        for profile_id, profile in sorted(profiles.items())
    ]


def run_profile(
    profile: dict[str, Any],
    *,
    dry_run: bool,
    allow_external: bool,
) -> dict[str, Any]:
    external_provider = bool(profile.get("external_provider"))
    profile_timeout_seconds = positive_int_or_none(profile.get("timeout_seconds"))
    commands = [
        resolve_command(command, default_timeout_seconds=profile_timeout_seconds)
        for command in profile.get("commands") or []
    ]
    if external_provider and not allow_external:
        return {
            "profile_id": profile.get("id", ""),
            "status": "blocked_external_provider",
            "external_provider": True,
            "commands": [command_report(command, skipped=True) for command in commands],
            "message": "Profile requires --allow-external or ALLOW_REAL_PIPELINE_PROFILE=1.",
        }
    if dry_run:
        return {
            "profile_id": profile.get("id", ""),
            "status": "dry_run",
            "external_provider": external_provider,
            "commands": [command_report(command, skipped=True) for command in commands],
        }

    env = {**os.environ, **{str(k): str(v) for k, v in (profile.get("env") or {}).items()}}
    results = []
    for command in commands:
        started = command_report(command, skipped=False)
        try:
            completed = subprocess.run(
                command["args"],
                cwd=PROJECT_ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=command.get("timeout_seconds"),
            )
        except subprocess.TimeoutExpired as exc:
            started.update(
                {
                    "returncode": None,
                    "timed_out": True,
                    "timeout_seconds": command.get("timeout_seconds"),
                    "stdout_tail": tail(exc.stdout),
                    "stderr_tail": tail(exc.stderr),
                }
            )
            results.append(started)
            return {
                "profile_id": profile.get("id", ""),
                "status": "timeout",
                "external_provider": external_provider,
                "commands": results,
            }
        started.update(
            {
                "returncode": completed.returncode,
                "timed_out": False,
                "stdout_tail": tail(completed.stdout),
                "stderr_tail": tail(completed.stderr),
            }
        )
        results.append(started)
        if completed.returncode != 0:
            return {
                "profile_id": profile.get("id", ""),
                "status": "failed",
                "external_provider": external_provider,
                "commands": results,
            }
    return {
        "profile_id": profile.get("id", ""),
        "status": "completed",
        "external_provider": external_provider,
        "commands": results,
    }


def resolve_command(
    command: dict[str, Any],
    *,
    default_timeout_seconds: int | None = None,
) -> dict[str, Any]:
    raw_args = [str(arg) for arg in (command.get("args") or [])]
    if not raw_args:
        raise SystemExit(f"profile command {command.get('name', '')} has no args")
    if raw_args[0] not in ALLOWED_EXECUTABLES:
        raise SystemExit(f"executable is not allowed in profile command: {raw_args[0]}")
    args = []
    for arg in raw_args:
        if arg.startswith("glob:"):
            matches = sorted(PROJECT_ROOT.glob(arg.removeprefix("glob:")))
            if not matches:
                raise SystemExit(f"profile glob matched no files: {arg}")
            args.extend(path.relative_to(PROJECT_ROOT).as_posix() for path in matches)
        else:
            args.append(arg)
    return {
        "name": str(command.get("name") or raw_args[0]),
        "args": args,
        "timeout_seconds": positive_int_or_none(
            command.get("timeout_seconds"),
            default=default_timeout_seconds,
        ),
    }


def command_report(command: dict[str, Any], *, skipped: bool) -> dict[str, Any]:
    payload = {
        "name": command["name"],
        "args": command["args"],
        "skipped": skipped,
    }
    if command.get("timeout_seconds") is not None:
        payload["timeout_seconds"] = command["timeout_seconds"]
    return payload


def tail(value: str | bytes | None, max_chars: int = 2000) -> str:
    if not value:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value[-max_chars:]


def positive_int_or_none(value: Any, *, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"timeout_seconds must be a positive integer: {value}") from exc
    if parsed <= 0:
        raise SystemExit(f"timeout_seconds must be a positive integer: {value}")
    return parsed


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise SystemExit(f"path must stay inside project root: {path}") from exc
    return resolved


if __name__ == "__main__":
    raise SystemExit(main())
