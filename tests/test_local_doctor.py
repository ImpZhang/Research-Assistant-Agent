from pathlib import Path
import subprocess


def test_local_doctor_runs_read_only_diagnostics() -> None:
    completed = subprocess.run(
        ["bash", "scripts/check_local_doctor.sh"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "== Local agent readiness ==" in completed.stdout
    assert "== Model provider configuration ==" in completed.stdout
    assert "== Local backup manifest ==" in completed.stdout
    assert "== SQLite maintenance report ==" in completed.stdout
    assert "== Geolocalization benchmark readiness ==" in completed.stdout
    assert "Local doctor completed." in completed.stdout
    assert "API_KEY=" not in completed.stdout


def test_local_doctor_uses_inspect_only_geoloc_check() -> None:
    script = Path("scripts/check_local_doctor.sh").read_text(encoding="utf-8")

    assert "scripts/prepare_local_geoloc_benchmark.py --inspect-only" in script
    assert "scripts/check_local_agent_readiness.sh" in script
    assert "scripts/check_model_provider_config.py" in script
    assert "scripts/build_local_backup_manifest.py" in script
    assert "scripts/check_sqlite_maintenance.py" in script
