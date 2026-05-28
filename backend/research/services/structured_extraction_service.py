from __future__ import annotations

import json

from pydantic import ValidationError
import requests
from sqlalchemy.orm import Session

from backend.research.adapters.model_adapter import OpenAICompatibleJsonClient
from backend.research.config import settings
from backend.research.models import Evidence, Paper, PaperCard
from backend.research.schemas import PaperCardPayload
from backend.research.services.paper_card_service import PaperCardService


PAPER_CARD_SYSTEM_PROMPT = """You extract structured research paper cards.

Return valid JSON only. Do not include markdown.
Every field must be grounded in the provided evidence ids.
If a field is not supported, return an empty list for that field.
"""


class StructuredExtractionService:
    def __init__(self, session: Session):
        self.session = session
        self.heuristic = PaperCardService(session)
        self.client = OpenAICompatibleJsonClient(
            model=settings.extraction_model,
            base_url=settings.extraction_base_url,
            api_key=settings.extraction_api_key,
        )

    def extract_paper_card(self, paper_id: str) -> PaperCard:
        if not self.client.is_configured:
            card = self.heuristic.extract_heuristic_card(paper_id)
            card.extraction_model = "heuristic_v0_no_model_configured"
            card.extraction_status = "completed"
            self.session.commit()
            self.session.refresh(card)
            return card

        paper = self.session.get(Paper, paper_id)
        if paper is None:
            raise ValueError("Paper not found")

        evidences = (
            self.session.query(Evidence)
            .filter(Evidence.paper_id == paper_id)
            .order_by(Evidence.created_at.asc())
            .all()
        )
        if not evidences:
            raise ValueError("Paper has no evidence records. Ingest or reprocess it first.")

        user_prompt = self._build_prompt(paper, evidences)
        try:
            payload = self.client.complete_json(
                system_prompt=PAPER_CARD_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            parsed = PaperCardPayload.model_validate(payload)
        except (requests.RequestException, KeyError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            card = self.heuristic.extract_heuristic_card(paper_id)
            card.extraction_model = f"heuristic_v0_after_model_error:{type(exc).__name__}"
            card.extraction_status = "completed_with_model_fallback"
            self.session.commit()
            self.session.refresh(card)
            return card

        card = self.heuristic.get_card(paper_id)
        if card is None:
            card = PaperCard(paper_id=paper_id)
            self.session.add(card)

        card.problem_json = {"items": [item.model_dump() for item in parsed.problem]}
        card.motivation_json = {"items": [item.model_dump() for item in parsed.motivation]}
        card.contributions_json = {"items": [item.model_dump() for item in parsed.contributions]}
        card.method_json = {"items": [item.model_dump() for item in parsed.method]}
        card.datasets_json = {"items": [item.model_dump() for item in parsed.datasets]}
        card.metrics_json = {"items": [item.model_dump() for item in parsed.metrics]}
        card.baselines_json = {"items": [item.model_dump() for item in parsed.baselines]}
        card.results_json = {"items": [item.model_dump() for item in parsed.results]}
        card.limitations_json = {"items": [item.model_dump() for item in parsed.limitations]}
        card.future_work_json = {"items": [item.model_dump() for item in parsed.future_work]}
        card.keywords_json = {"items": parsed.keywords}
        card.open_questions_json = {"items": [item.model_dump() for item in parsed.open_questions]}
        card.extraction_model = settings.extraction_model
        card.extraction_status = "completed"
        self.session.commit()
        self.session.refresh(card)
        return card

    def _build_prompt(self, paper: Paper, evidences: list[Evidence]) -> str:
        evidence_payload = [
            {
                "evidence_id": evidence.id,
                "type": evidence.evidence_type,
                "supports": evidence.supports,
                "text": evidence.text[:1200],
            }
            for evidence in evidences[:24]
        ]
        schema_hint = {
            "problem": [{"text": "...", "evidence_ids": ["..."], "confidence": 0.0}],
            "motivation": [],
            "contributions": [],
            "method": [],
            "datasets": [],
            "metrics": [],
            "baselines": [],
            "results": [],
            "limitations": [],
            "future_work": [],
            "keywords": [],
            "open_questions": [],
        }
        return (
            f"Paper title: {paper.title}\n\n"
            f"Evidence JSON:\n{json.dumps(evidence_payload, ensure_ascii=False, indent=2)}\n\n"
            f"Return JSON matching this shape:\n{json.dumps(schema_hint, ensure_ascii=False, indent=2)}"
        )
