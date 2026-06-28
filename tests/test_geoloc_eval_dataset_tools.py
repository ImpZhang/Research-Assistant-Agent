import json
import os
from pathlib import Path
import subprocess
import sys


def test_geoloc_eval_dataset_builder_and_checker(tmp_path: Path) -> None:
    database_path = tmp_path / "eval-dataset.db"
    report_path = tmp_path / "real_paper_eval_fixture.json"
    output_dir = tmp_path / "dataset"
    quality_json = output_dir / "quality.json"
    quality_md = output_dir / "quality.md"
    env = {
        **os.environ,
        "RESEARCH_DB_URL": f"sqlite:///{database_path}",
        "PYTHONPATH": str(Path.cwd()),
        "RETRIEVAL_EMBEDDING_PROVIDER": "local",
        "RETRIEVAL_RERANK_PROVIDER": "disabled",
    }
    subprocess.run(
        [
            sys.executable,
            "-c",
            f"""
import json
from pathlib import Path

from backend.research.db import SessionLocal, init_db
from backend.research.models import Chunk, Evidence, Paper, PaperSection

init_db()
with SessionLocal() as session:
    paper_a = Paper(
        id="paper-a",
        title="Fixture GeoRanker Evaluation Paper",
        filename="fixture-georanker.pdf",
        domain="image geolocalization",
        status="parsed",
    )
    paper_b = Paper(
        id="paper-b",
        title="Fixture Cross View Geolocalization Paper",
        filename="fixture-cross-view.pdf",
        domain="cross-view geolocalization",
        status="parsed",
    )
    session.add_all([paper_a, paper_b])
    session.flush()
    for paper, prefix in [(paper_a, "ranking"), (paper_b, "crossview")]:
        section = PaperSection(
            id=f"section-{{prefix}}",
            paper_id=paper.id,
            title="Evaluation",
            section_type="evaluation",
            text=f"{{prefix}} evaluation section",
            order_index=1,
        )
        session.add(section)
        for index, topic in enumerate(
            ["long-tail regions", "hard negative mining", "coordinate accuracy"],
            start=1,
        ):
            chunk = Chunk(
                id=f"chunk-{{prefix}}-{{index}}",
                paper_id=paper.id,
                section_id=section.id,
                chunk_id=f"chunk-{{prefix}}-{{index}}",
                text=(
                    f"The {{prefix}} study evaluates {{topic}} with geolocalization "
                    f"benchmarks and region-aware retrieval diagnostics."
                ),
                token_count=18,
            )
            evidence = Evidence(
                id=f"evidence-{{prefix}}-{{index}}",
                paper_id=paper.id,
                section_id=section.id,
                chunk_id=chunk.chunk_id,
                evidence_type="evaluation_signal",
                text=(
                    f"The {{prefix}} evidence reports {{topic}} for image "
                    f"geolocalization under benchmark retrieval settings."
                ),
                summary=f"{{prefix}} {{topic}} geolocalization benchmark evidence.",
                supports=f"{{prefix}} {{topic}} evaluation claim",
                confidence=0.91,
            )
            session.add_all([chunk, evidence])
    session.commit()

report = {{
    "papers": [
        {{"status": "completed", "filename": "fixture-georanker.pdf", "paper": {{"id": "paper-a"}}}},
        {{"status": "completed", "filename": "fixture-cross-view.pdf", "paper": {{"id": "paper-b"}}}},
    ]
}}
Path({str(report_path)!r}).write_text(json.dumps(report), encoding="utf-8")
""",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )

    built = subprocess.run(
        [
            sys.executable,
            "scripts/build_geoloc_eval_dataset.py",
            "--report",
            str(report_path),
            "--output-dir",
            str(output_dir),
            "--dataset-id",
            "fixture_geoloc_eval",
            "--min-query-count",
            "4",
            "--max-query-count",
            "8",
            "--replay-count",
            "4",
            "--json",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    manifest = json.loads(built.stdout)
    assert manifest["query_count"] == 6
    assert manifest["replay_case_count"] == 4
    assert (output_dir / "query_evidence.jsonl").exists()
    assert (output_dir / "replay_cases.jsonl").exists()

    checked = subprocess.run(
        [
            sys.executable,
            "scripts/check_geoloc_eval_dataset.py",
            "--dataset-dir",
            str(output_dir),
            "--min-queries",
            "4",
            "--max-queries",
            "8",
            "--min-replay-cases",
            "4",
            "--max-replay-cases",
            "4",
            "--min-papers",
            "2",
            "--min-queries-per-paper",
            "2",
            "--run-retrieval",
            "--min-hit-at-8",
            "1.0",
            "--min-replay-pass-rate",
            "1.0",
            "--write-json",
            str(quality_json),
            "--write-markdown",
            str(quality_md),
            "--json",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    quality = json.loads(checked.stdout)
    assert quality["status"] == "pass"
    assert quality["metrics"]["retrieval"]["hit_at_8"] == 1.0
    assert quality["metrics"]["replay"]["pass_rate"] == 1.0
    assert "# Geoloc Evaluation Dataset Quality Report" in quality_md.read_text(encoding="utf-8")
