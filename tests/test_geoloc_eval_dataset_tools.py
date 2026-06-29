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


def test_geoloc_hard_question_builder_and_checker(tmp_path: Path) -> None:
    database_path = tmp_path / "hard-questions.db"
    output_dir = tmp_path / "dataset"
    report_path = tmp_path / "real_paper_eval_fixture.json"
    questions_path = tmp_path / "hard_questions.jsonl"
    quality_json = output_dir / "hard_question_quality.json"
    quality_md = output_dir / "hard_question_quality.md"
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

    subprocess.run(
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
    question_rows = [
        {
            "id": "hq_fixture_0001",
            "intent": "evaluation_gap",
            "difficulty": "hard",
            "target_papers": ["GeoRanker"],
            "required_terms": ["ranking", "long-tail regions", "benchmark retrieval"],
            "question": (
                "If I improve ranking for long-tail regions, what GeoRanker evidence "
                "shows the benchmark retrieval behavior I must compare against?"
            ),
        },
        {
            "id": "hq_fixture_0002",
            "intent": "cross_view_design",
            "difficulty": "hard",
            "target_papers": ["Cross View"],
            "required_terms": ["crossview", "hard negative mining", "geolocalization"],
            "question": (
                "For cross view geolocalization, what hard negative mining evidence "
                "should constrain a new retrieval design?"
            ),
        },
        {
            "id": "hq_fixture_0003",
            "intent": "method_contrast",
            "difficulty": "hard",
            "target_papers": ["GeoRanker", "Cross View"],
            "required_terms": ["ranking", "crossview", "coordinate accuracy"],
            "question": (
                "How should I compare ranking coordinate accuracy evidence with "
                "crossview coordinate accuracy evidence before writing a new idea?"
            ),
        },
        {
            "id": "hq_fixture_0004",
            "intent": "baseline_choice",
            "difficulty": "hard",
            "target_papers": ["GeoRanker"],
            "required_terms": ["ranking", "coordinate accuracy", "benchmark"],
            "question": (
                "Which ranking coordinate accuracy benchmark evidence is the baseline "
                "I should not misrepresent in a proposal?"
            ),
        },
    ]
    questions_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in question_rows
        ),
        encoding="utf-8",
    )

    built = subprocess.run(
        [
            sys.executable,
            "scripts/build_geoloc_hard_questions.py",
            "--dataset-dir",
            str(output_dir),
            "--questions",
            str(questions_path),
            "--dataset-id",
            "fixture_hard_questions",
            "--min-hard-questions",
            "4",
            "--json",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    manifest = json.loads(built.stdout)
    assert manifest["hard_question_count"] == 4
    assert manifest["hard_replay_case_count"] == 4
    assert (output_dir / "hard_questions.jsonl").exists()
    assert (output_dir / "hard_question_replay_cases.jsonl").exists()

    checked = subprocess.run(
        [
            sys.executable,
            "scripts/check_geoloc_hard_questions.py",
            "--dataset-dir",
            str(output_dir),
            "--min-hard-questions",
            "4",
            "--min-paper-coverage",
            "2",
            "--min-intent-coverage",
            "4",
            "--run-retrieval",
            "--min-any-hit-at-8",
            "1.0",
            "--min-all-hit-at-8",
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
    assert quality["metrics"]["retrieval"]["any_hit_at_8"] == 1.0
    assert quality["metrics"]["retrieval"]["all_hit_at_8"] == 1.0
    assert quality["metrics"]["replay"]["pass_rate"] == 1.0
    assert "# Geoloc Hard-Question Quality Report" in quality_md.read_text(encoding="utf-8")


def test_geoloc_realistic_gold_builder_and_checker(tmp_path: Path) -> None:
    database_path = tmp_path / "realistic-gold.db"
    output_dir = tmp_path / "dataset"
    report_path = tmp_path / "real_paper_eval_fixture.json"
    gold_spec_path = tmp_path / "realistic_gold.jsonl"
    quality_json = output_dir / "realistic_quality.json"
    quality_md = output_dir / "realistic_quality.md"
    failure_replay_path = output_dir / "realistic_failure_replay_cases.jsonl"
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

    subprocess.run(
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
    gold_rows = [
        {
            "id": "rg_fixture_0001",
            "intent": "realistic_baseline",
            "difficulty": "realistic_hard",
            "query": (
                "For a proposal about ranking long-tail regions, which benchmark "
                "retrieval evidence should constrain the novelty claim?"
            ),
            "blind_leak_terms": ["GeoRanker"],
            "gold_targets": [
                {
                    "role": "primary",
                    "paper_alias": "GeoRanker",
                    "evidence_type": "evaluation_signal",
                    "section_hint": "Evaluation",
                    "required_terms": ["ranking", "long-tail regions", "benchmark"],
                    "rationale": "Marks the ranking long-tail benchmark evidence as primary gold.",
                }
            ],
        },
        {
            "id": "rg_fixture_0002",
            "intent": "realistic_cross_view",
            "difficulty": "realistic_hard",
            "query": (
                "For cross-view retrieval, which evidence discusses hard negative "
                "mining under geolocalization benchmark settings?"
            ),
            "blind_leak_terms": ["Cross View"],
            "gold_targets": [
                {
                    "role": "primary",
                    "paper_alias": "Cross View",
                    "evidence_type": "evaluation_signal",
                    "section_hint": "Evaluation",
                    "required_terms": ["crossview", "hard negative mining", "benchmark"],
                    "rationale": "Marks the cross-view hard-negative benchmark evidence as primary gold.",
                }
            ],
        },
    ]
    gold_spec_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in gold_rows),
        encoding="utf-8",
    )

    built = subprocess.run(
        [
            sys.executable,
            "scripts/build_geoloc_realistic_eval.py",
            "--dataset-dir",
            str(output_dir),
            "--gold-spec",
            str(gold_spec_path),
            "--dataset-id",
            "fixture_realistic_gold",
            "--min-questions",
            "2",
            "--json",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    manifest = json.loads(built.stdout)
    assert manifest["question_count"] == 2
    assert manifest["replay_case_count"] == 2
    assert manifest["quality_policy"]["no_per_query_paper_filter"] is True
    assert (output_dir / "realistic_gold_questions.jsonl").exists()
    assert (output_dir / "realistic_replay_cases.jsonl").exists()

    records = [
        json.loads(line)
        for line in (output_dir / "realistic_gold_questions.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert records[0]["primary_gold_evidence_ids"] == ["evidence-ranking-1"]
    assert records[0]["gold_targets"][0]["label_rationale"]
    assert records[0]["evaluation_mode"] == "realistic_no_per_query_paper_filter"

    checked = subprocess.run(
        [
            sys.executable,
            "scripts/check_geoloc_realistic_eval.py",
            "--dataset-dir",
            str(output_dir),
            "--min-questions",
            "2",
            "--min-paper-coverage",
            "2",
            "--min-primary-hit-at-8",
            "1.0",
            "--min-mrr-primary",
            "1.0",
            "--min-replay-pass-rate",
            "1.0",
            "--write-json",
            str(quality_json),
            "--write-markdown",
            str(quality_md),
            "--write-failure-replay",
            str(failure_replay_path),
            "--json",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    quality = json.loads(checked.stdout)
    assert quality["status"] == "pass"
    assert quality["evaluation_mode"] == "realistic_no_per_query_paper_filter"
    assert quality["metrics"]["retrieval"]["per_query_paper_filter"] is False
    assert quality["metrics"]["retrieval"]["primary_hit_at_8"] == 1.0
    assert quality["metrics"]["replay"]["pass_rate"] == 1.0
    assert "# Geoloc Realistic Gold Evaluation Report" in quality_md.read_text(encoding="utf-8")
    assert failure_replay_path.read_text(encoding="utf-8") == ""
