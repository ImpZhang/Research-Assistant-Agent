import json
import os
from pathlib import Path
import subprocess
import sys


PROVIDER_KEYS = [
    "MODEL_PROVIDER_CONFIG_LOAD_DOTENV",
    "MODEL_PROVIDER_CONFIG_DOTENV_PATH",
    "MODEL",
    "BASE_URL",
    "ARK_API_KEY",
    "MAIN_MODEL",
    "MAIN_BASE_URL",
    "MAIN_API_KEY",
    "EXTRACTION_MODEL",
    "EXTRACTION_BASE_URL",
    "EXTRACTION_API_KEY",
    "JUDGE_MODEL",
    "JUDGE_BASE_URL",
    "JUDGE_API_KEY",
    "EMBEDDER",
    "EMBEDDER_BASE_URL",
    "EMBEDDER_API_KEY",
    "RETRIEVAL_EMBEDDING_PROVIDER",
    "RERANK_MODEL",
    "RERANK_BINDING_HOST",
    "RERANK_API_KEY",
    "RETRIEVAL_RERANK_PROVIDER",
]


def test_model_provider_config_allows_default_fallbacks() -> None:
    completed = run_config_check("--json", env=clean_provider_env())
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    assert payload["roles"]["main"]["configured"] is False
    assert payload["roles"]["embedding"]["mode"] == "auto"
    assert "local hash retrieval remains active" in " ".join(payload["warnings"])


def test_model_provider_config_require_real_uses_presence_without_printing_keys() -> None:
    secret = "sk-test-secret-never-print"
    env = clean_provider_env()
    env.update(
        {
            "MAIN_MODEL": "qwen3-32b",
            "MAIN_BASE_URL": "https://example.test/v1",
            "MAIN_API_KEY": secret,
            "EXTRACTION_MODEL": "qwen3-32b",
            "EXTRACTION_BASE_URL": "https://example.test/v1",
            "EXTRACTION_API_KEY": secret,
            "JUDGE_MODEL": "qwen3-32b",
            "JUDGE_BASE_URL": "https://example.test/v1",
            "JUDGE_API_KEY": secret,
            "EMBEDDER": "text-embedding-v1",
            "EMBEDDER_BASE_URL": "https://example.test/v1",
            "EMBEDDER_API_KEY": secret,
            "RERANK_MODEL": "qwen3-rerank",
            "RERANK_BINDING_HOST": "https://example.test/v1",
            "RERANK_API_KEY": secret,
        }
    )

    completed = run_config_check("--require-real", "--json", env=env)
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    assert all(role["configured"] for role in payload["roles"].values())
    assert secret not in completed.stdout
    assert secret not in completed.stderr
    assert payload["roles"]["main"]["fields"]["api_key"]["source"] == "MAIN_API_KEY"


def test_model_provider_config_external_mode_requires_embedding() -> None:
    env = clean_provider_env()
    env["RETRIEVAL_EMBEDDING_PROVIDER"] = "external"
    completed = run_config_check("--json", env=env, check=False)
    payload = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert "embedding provider is required" in " ".join(payload["errors"])


def test_model_provider_config_loads_dotenv_without_printing_secret(tmp_path) -> None:
    secret = "sk-dotenv-secret-never-print"
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "MAIN_MODEL=qwen3-32b",
                "MAIN_BASE_URL=https://example.test/v1",
                f"MAIN_API_KEY={secret}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    env = clean_provider_env()
    env["MODEL_PROVIDER_CONFIG_LOAD_DOTENV"] = "true"
    env["MODEL_PROVIDER_CONFIG_DOTENV_PATH"] = str(dotenv_path)

    completed = run_config_check("--json", env=env)
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    assert payload["roles"]["main"]["configured"] is True
    assert payload["roles"]["main"]["fields"]["api_key"]["source"] == "MAIN_API_KEY"
    assert secret not in completed.stdout
    assert secret not in completed.stderr


def run_config_check(
    *args: str, env: dict[str, str], check: bool = True
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(Path("scripts/check_model_provider_config.py")), *args],
        capture_output=True,
        text=True,
        check=check,
        env=env,
    )


def clean_provider_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in PROVIDER_KEYS:
        env.pop(key, None)
    env["MODEL_PROVIDER_CONFIG_LOAD_DOTENV"] = "false"
    return env
