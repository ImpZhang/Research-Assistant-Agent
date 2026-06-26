#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from typing import Any


CHAT_ROLES = {
    "main": {
        "model": ("MAIN_MODEL", "MODEL"),
        "base_url": ("MAIN_BASE_URL", "BASE_URL"),
        "api_key": ("MAIN_API_KEY", "ARK_API_KEY"),
    },
    "extraction": {
        "model": ("EXTRACTION_MODEL", "MAIN_MODEL", "MODEL"),
        "base_url": ("EXTRACTION_BASE_URL", "MAIN_BASE_URL", "BASE_URL"),
        "api_key": ("EXTRACTION_API_KEY", "MAIN_API_KEY", "ARK_API_KEY"),
    },
    "judge": {
        "model": ("JUDGE_MODEL", "MAIN_MODEL", "MODEL"),
        "base_url": ("JUDGE_BASE_URL", "MAIN_BASE_URL", "BASE_URL"),
        "api_key": ("JUDGE_API_KEY", "MAIN_API_KEY", "ARK_API_KEY"),
    },
}

EMBEDDING_ROLE = {
    "model": ("EMBEDDER",),
    "base_url": ("EMBEDDER_BASE_URL",),
    "api_key": ("EMBEDDER_API_KEY",),
}
RERANK_ROLE = {
    "model": ("RERANK_MODEL",),
    "base_url": ("RERANK_BINDING_HOST",),
    "api_key": ("RERANK_API_KEY",),
}


def main() -> int:
    args = parse_args()
    report = build_report(require_real=args.require_real)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print_human_report(report)
    return 0 if report["ok"] else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check model-provider environment variable readiness without printing "
            "secret values or calling real providers."
        )
    )
    parser.add_argument(
        "--require-real",
        action="store_true",
        help="Require all chat, embedding, and rerank roles to be configured.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def build_report(*, require_real: bool) -> dict[str, Any]:
    roles: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    warnings: list[str] = []

    for role_name, variables in CHAT_ROLES.items():
        role = role_report(variables)
        role["required_for_real"] = True
        role["fallback"] = "deterministic local fallback" if role_name == "main" else "main role"
        roles[role_name] = role
        if require_real and not role["configured"]:
            errors.append(f"{role_name} model provider is required but not fully configured.")
        elif not role["configured"]:
            warnings.append(
                f"{role_name} model provider is not configured; fallback remains active."
            )

    embedding_mode = env_value("RETRIEVAL_EMBEDDING_PROVIDER", default="auto").casefold()
    embedding = role_report(EMBEDDING_ROLE)
    embedding["mode"] = embedding_mode
    embedding["required_for_real"] = require_real or embedding_mode == "external"
    embedding["fallback"] = "local hash retrieval"
    roles["embedding"] = embedding
    if embedding["required_for_real"] and not embedding["configured"]:
        errors.append("embedding provider is required but not fully configured.")
    elif not embedding["configured"]:
        warnings.append(
            "embedding provider is not configured; local hash retrieval remains active."
        )

    rerank_mode = env_value("RETRIEVAL_RERANK_PROVIDER", default="auto").casefold()
    rerank = role_report(RERANK_ROLE)
    rerank["mode"] = rerank_mode
    rerank["required_for_real"] = require_real or rerank_mode == "external"
    rerank["fallback"] = "rerank disabled"
    roles["rerank"] = rerank
    if rerank["required_for_real"] and not rerank["configured"]:
        errors.append("rerank provider is required but not fully configured.")
    elif not rerank["configured"]:
        warnings.append("rerank provider is not configured; learned rerank remains inactive.")

    return {
        "ok": not errors,
        "require_real": require_real,
        "roles": roles,
        "errors": errors,
        "warnings": warnings,
        "real_smoke_command": (
            "ALLOW_REAL_MODEL_PROVIDER_SMOKE=1 .venv/bin/python scripts/smoke_model_providers.py"
        ),
    }


def role_report(variable_groups: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    fields: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for field, names in variable_groups.items():
        selected = first_present_name(names)
        configured = selected != ""
        fields[field] = {
            "configured": configured,
            "source": selected,
            "accepted_variables": list(names),
        }
        if not configured:
            missing.append(" or ".join(names))
    return {
        "configured": not missing,
        "fields": fields,
        "missing": missing,
    }


def first_present_name(names: tuple[str, ...]) -> str:
    for name in names:
        if env_present(name):
            return name
    return ""


def env_present(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def env_value(name: str, *, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def print_human_report(report: dict[str, Any]) -> None:
    print("Model provider configuration check")
    print(f"Require real providers: {'yes' if report['require_real'] else 'no'}")
    print(f"OK: {'yes' if report['ok'] else 'no'}")
    for role_name, role in report["roles"].items():
        print(f"{role_name}: configured={'yes' if role['configured'] else 'no'}")
        if role.get("mode"):
            print(f"{role_name}: mode={role['mode']}")
        if role["missing"]:
            print(f"{role_name}: missing={', '.join(role['missing'])}")
    for warning in report["warnings"]:
        print(f"Warning: {warning}")
    for error in report["errors"]:
        print(f"Error: {error}")
    print(f"Real provider smoke: {report['real_smoke_command']}")


if __name__ == "__main__":
    raise SystemExit(main())
