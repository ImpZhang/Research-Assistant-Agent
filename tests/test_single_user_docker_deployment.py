import json
from pathlib import Path
import subprocess
import sys


def test_single_user_docker_deployment_check_passes_on_repo() -> None:
    completed = run_docker_check("--json")
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    assert payload["check_count"] >= 5
    assert payload["failures"] == []
    assert "API_KEY=" not in completed.stdout
    assert "does not run Docker" in " ".join(payload["notes"])


def test_single_user_docker_deployment_check_reports_missing_tokens(tmp_path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / ".dockerignore").write_text(".env\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("APP_ENV=production\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/deployment.md").write_text("docker compose up --build\n", encoding="utf-8")

    completed = run_docker_check("--project-root", str(tmp_path), "--json", check=False)
    payload = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert payload["failures"]
    assert any(failure["missing_tokens"] for failure in payload["failures"])


def test_single_user_docker_deployment_check_can_write_reports(tmp_path) -> None:
    copy_contract_files(tmp_path)
    json_path = "outputs/docker/static-check.json"
    markdown_path = "outputs/docker/static-check.md"
    completed = run_docker_check(
        "--project-root",
        str(tmp_path),
        "--write-json",
        json_path,
        "--write-markdown",
        markdown_path,
        "--markdown",
    )

    assert "# Single User Docker Deployment Check" in completed.stdout
    assert (tmp_path / json_path).exists()
    assert (tmp_path / markdown_path).exists()
    payload = json.loads((tmp_path / json_path).read_text(encoding="utf-8"))
    assert payload["ok"] is True


def run_docker_check(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(Path("scripts/check_single_user_docker_deployment.py")), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def copy_contract_files(target: Path) -> None:
    root = Path.cwd()
    for relative in [
        "Dockerfile",
        "docker-compose.yml",
        ".dockerignore",
        ".env.example",
        "docs/deployment.md",
    ]:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text((root / relative).read_text(encoding="utf-8"), encoding="utf-8")
