from fastapi.testclient import TestClient

from backend.app import create_app


def test_health() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_research_status() -> None:
    client = TestClient(create_app())
    response = client.get("/research/status")
    assert response.status_code == 200
    body = response.json()
    assert body["phase"] == "phase_0_foundation"
    assert "sqlalchemy_models" in body["implemented_capabilities"]


def test_upload_text_paper() -> None:
    client = TestClient(create_app())
    content = b"""Research Assistant Agent Test Paper

Abstract
This paper proposes a small evidence-grounded research assistant test fixture.

Introduction
Research assistants need structured evidence rather than only raw chunks.

Method
The method extracts sections, chunks, and evidence records.

Conclusion
Future work should add structured paper-card extraction.
"""
    response = client.post(
        "/research/papers/upload",
        files={"file": ("test_paper.txt", content, "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["paper"]["status"] == "indexed"
    assert body["section_count"] >= 3
    assert body["chunk_count"] >= body["section_count"]
    assert body["evidence_count"] >= 3

    evidence_response = client.get(f"/research/papers/{body['paper']['id']}/evidence")
    assert evidence_response.status_code == 200
    assert len(evidence_response.json()) == body["evidence_count"]


def test_extract_paper_card_from_evidence() -> None:
    client = TestClient(create_app())
    content = b"""Paper Card Extraction Test

Abstract
This paper proposes a research assistant that turns evidence into paper cards.

Introduction
The problem is that raw chunks are too low-level for idea generation.

Method
The system maps evidence records into structured paper-card fields.

Conclusion
Future work should replace heuristic extraction with LLM structured extraction.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("paper_card_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    extract = client.post(f"/research/papers/{paper_id}/card/extract")
    assert extract.status_code == 200
    card = extract.json()
    assert card["paper_id"] == paper_id
    assert card["extraction_status"] == "completed"
    assert card["payload"]["problem"]
    assert card["payload"]["method"]
    assert card["payload"]["future_work"]

    fetched = client.get(f"/research/papers/{paper_id}/card")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == card["id"]


def test_mine_research_gaps_from_evidence() -> None:
    client = TestClient(create_app())
    content = b"""Gap Mining Test Paper

Introduction
Current research assistants still struggle to convert raw literature into testable research gaps.

Method
The system stores evidence as first-class records.

Limitations
This preliminary version does not yet check novelty against external literature.

Conclusion
Future work should connect gap mining to idea generation and reviewer simulation.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("gap_mining_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    response = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["gaps"]
    assert any(gap["gap_type"] in {"method_gap", "application_gap"} for gap in body["gaps"])
    assert all(gap["evidence_ids"] for gap in body["gaps"])

    gap_id = body["gaps"][0]["id"]
    fetched = client.get(f"/research/gaps/{gap_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == gap_id


def test_generate_ideas_from_gap() -> None:
    client = TestClient(create_app())
    content = b"""Idea Generation Test Paper

Introduction
Research assistants need a way to turn literature gaps into testable hypotheses.

Limitations
The current pipeline does not yet create executable experiments from generated ideas.

Conclusion
Future work should connect idea generation to reviewer criticism.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("idea_generation_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    gaps = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 2})
    assert gaps.status_code == 200
    gap_id = gaps.json()["gaps"][0]["id"]

    generated = client.post(f"/research/gaps/{gap_id}/ideas")
    assert generated.status_code == 200
    body = generated.json()
    assert len(body["ideas"]) == 2
    assert all(idea["related_gap_ids"] == [gap_id] for idea in body["ideas"])
    assert all(idea["evidence_ids"] for idea in body["ideas"])
    assert all(idea["score"]["overall_score"] for idea in body["ideas"])

    idea_id = body["ideas"][0]["id"]
    fetched = client.get(f"/research/ideas/{idea_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == idea_id
