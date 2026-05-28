from __future__ import annotations

import json

from pydantic import ValidationError
import requests
from sqlalchemy.orm import Session

from backend.research.adapters.model_adapter import OpenAICompatibleJsonClient
from backend.research.config import settings
from backend.research.models import Idea, ResearchGap
from backend.research.schemas import IdeaCreate
from backend.research.services.graph_service import GraphService
from backend.research.services.idea_service import IdeaService


IDEA_SYSTEM_PROMPT = """You generate evidence-grounded research ideas.

Return valid JSON only. Do not include markdown.
Every idea must be testable, tied to the provided gap, and explicit about datasets, baselines, metrics, and risks.
Avoid vague combinations of buzzwords. Prefer concrete hypotheses and experiments.
"""


class StructuredIdeaService:
    def __init__(self, session: Session):
        self.session = session
        self.heuristic = IdeaService(session)
        self.client = OpenAICompatibleJsonClient(
            model=settings.main_model,
            base_url=settings.main_base_url,
            api_key=settings.main_api_key,
        )

    def generate_from_gaps(
        self,
        gap_ids: list[str] | None = None,
        max_ideas_per_gap: int = 2,
    ) -> list[Idea]:
        if not self.client.is_configured:
            return self.heuristic.generate_from_gaps(gap_ids, max_ideas_per_gap)

        query = self.session.query(ResearchGap).order_by(ResearchGap.created_at.desc())
        if gap_ids:
            query = query.filter(ResearchGap.id.in_(gap_ids))
        gaps = query.all()

        try:
            ideas = []
            graph = GraphService(self.session)
            for gap in gaps:
                ideas.extend(self._generate_for_gap(gap, max_ideas_per_gap, graph))
            self.session.commit()
            for idea in ideas:
                self.session.refresh(idea)
            return ideas
        except (requests.RequestException, KeyError, ValueError, ValidationError, json.JSONDecodeError):
            self.session.rollback()
            return self.heuristic.generate_from_gaps(gap_ids, max_ideas_per_gap)

    def _generate_for_gap(
        self,
        gap: ResearchGap,
        max_ideas: int,
        graph: GraphService,
    ) -> list[Idea]:
        payload = self.client.complete_json(
            system_prompt=IDEA_SYSTEM_PROMPT,
            user_prompt=self._build_prompt(gap, max_ideas),
        )
        raw_ideas = payload.get("ideas", [])
        if not isinstance(raw_ideas, list) or not raw_ideas:
            raise ValueError("Model returned no ideas.")

        ideas = []
        for raw_idea in raw_ideas[: max(1, max_ideas)]:
            parsed = IdeaCreate.model_validate(raw_idea)
            idea = self._create_idea(parsed, gap)
            self.session.add(idea)
            self.session.flush()
            self._link_idea_to_gap(graph, idea, gap)
            ideas.append(idea)
        return ideas

    def _create_idea(self, payload: IdeaCreate, gap: ResearchGap) -> Idea:
        return Idea(
            title=payload.title,
            research_question=payload.research_question,
            core_hypothesis=payload.core_hypothesis,
            motivation=payload.motivation or gap.why_important,
            related_gap_ids_json=payload.related_gap_ids or [gap.id],
            related_paper_ids_json=payload.related_paper_ids or gap.source_paper_ids_json or [],
            evidence_ids_json=payload.evidence_ids or gap.evidence_ids_json or [],
            method_sketch=payload.method_sketch,
            expected_contribution=payload.expected_contribution,
            novelty_argument=payload.novelty_argument,
            datasets_json=payload.datasets,
            baselines_json=payload.baselines,
            metrics_json=payload.metrics,
            risks_json=payload.risks,
            resource_requirements=payload.resource_requirements,
            target_venues_json=payload.target_venues,
            score_json={
                "novelty": 3.0,
                "feasibility": 3.0,
                "impact": 3.0,
                "evidence_support": 4.0,
                "experimental_verifiability": 4.0,
                "resource_cost": 3.0,
                "publication_potential": 3.0,
                "overall_score": 3.4,
                "rationale": "Initial structured-model generation score; rerank before proposal use.",
            },
            status="draft",
            version=1,
        )

    def _link_idea_to_gap(self, graph: GraphService, idea: Idea, gap: ResearchGap) -> None:
        idea_node = graph.get_or_create_node(
            node_type="idea",
            label=idea.title,
            canonical_key=idea.id,
            payload={"status": idea.status, "version": idea.version},
        )
        gap_node = graph.get_or_create_node(
            node_type="gap",
            label=gap.title,
            canonical_key=gap.id,
            payload={"gap_type": gap.gap_type, "status": gap.status},
        )
        graph.create_edge(
            source_node=idea_node,
            target_node=gap_node,
            edge_type="idea_addresses_gap",
            evidence_ids=gap.evidence_ids_json or [],
        )

    def _build_prompt(self, gap: ResearchGap, max_ideas: int) -> str:
        schema_hint = {
            "ideas": [
                {
                    "title": "...",
                    "research_question": "...",
                    "core_hypothesis": "...",
                    "motivation": "...",
                    "related_gap_ids": [gap.id],
                    "related_paper_ids": gap.source_paper_ids_json or [],
                    "evidence_ids": gap.evidence_ids_json or [],
                    "method_sketch": "...",
                    "expected_contribution": "...",
                    "novelty_argument": "...",
                    "datasets": ["..."],
                    "baselines": ["..."],
                    "metrics": ["..."],
                    "risks": ["..."],
                    "resource_requirements": "...",
                    "target_venues": ["..."],
                }
            ]
        }
        gap_payload = {
            "gap_id": gap.id,
            "title": gap.title,
            "description": gap.description,
            "gap_type": gap.gap_type,
            "source_paper_ids": gap.source_paper_ids_json or [],
            "evidence_ids": gap.evidence_ids_json or [],
            "why_important": gap.why_important,
            "why_unsolved": gap.why_unsolved,
            "possible_approaches": gap.possible_approaches_json or [],
        }
        return (
            f"Generate {max(1, max_ideas)} ideas for this research gap.\n\n"
            f"Gap JSON:\n{json.dumps(gap_payload, ensure_ascii=False, indent=2)}\n\n"
            f"Return JSON matching this shape:\n{json.dumps(schema_hint, ensure_ascii=False, indent=2)}"
        )
