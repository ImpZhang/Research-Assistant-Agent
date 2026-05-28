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
