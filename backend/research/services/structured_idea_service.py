from __future__ import annotations

import json

from pydantic import ValidationError
import requests
from sqlalchemy.orm import Session

from backend.research.adapters.model_adapter import OpenAICompatibleJsonClient
from backend.research.config import settings
from backend.research.models import Evidence, Idea, ResearchGap
from backend.research.schemas import IdeaCreate
from backend.research.services.graph_service import GraphService
from backend.research.services.idea_service import IdeaService


IDEA_SYSTEM_PROMPT = """You generate evidence-grounded research ideas.

Return valid JSON only. Do not include markdown.
Every idea must be testable, tied to the provided gap, and explicit about datasets, baselines, metrics, and risks.
Avoid vague combinations of buzzwords. Prefer concrete hypotheses and experiments.
For image geolocalization topics, avoid generic "improve accuracy" ideas. Name the failure mode, method intervention, benchmark slice, baseline family, and geodesic/top-k metric that would prove the claim.
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
        except (
            requests.RequestException,
            KeyError,
            ValueError,
            ValidationError,
            json.JSONDecodeError,
        ):
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
        evidence_payload = self._evidence_payload(gap)
        topic = self.heuristic._gap_topic(gap)
        experiment_profile = self.heuristic._experiment_profile(topic, gap)
        domain_guidance = self._domain_guidance(topic, evidence_payload, experiment_profile)
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
            f"Evidence JSON:\n{json.dumps(evidence_payload, ensure_ascii=False, indent=2)}\n\n"
            f"Suggested experiment profile:\n"
            f"{json.dumps(experiment_profile, ensure_ascii=False, indent=2)}\n\n"
            f"Quality constraints:\n{domain_guidance}\n\n"
            f"Return JSON matching this shape:\n{json.dumps(schema_hint, ensure_ascii=False, indent=2)}"
        )

    def _evidence_payload(self, gap: ResearchGap, limit: int = 8) -> list[dict]:
        evidence_ids = gap.evidence_ids_json or []
        evidences = []
        if evidence_ids:
            evidences = (
                self.session.query(Evidence)
                .filter(Evidence.id.in_(evidence_ids))
                .order_by(Evidence.created_at.asc())
                .limit(limit)
                .all()
            )
        if len(evidences) < limit and (gap.source_paper_ids_json or []):
            existing_ids = {evidence.id for evidence in evidences}
            candidates = (
                self.session.query(Evidence)
                .filter(Evidence.paper_id.in_(gap.source_paper_ids_json or []))
                .order_by(Evidence.created_at.asc())
                .limit(limit * 2)
                .all()
            )
            for evidence in candidates:
                if evidence.id in existing_ids:
                    continue
                evidences.append(evidence)
                existing_ids.add(evidence.id)
                if len(evidences) >= limit:
                    break

        return [
            {
                "evidence_id": evidence.id,
                "type": evidence.evidence_type,
                "supports": evidence.supports,
                "summary": evidence.summary[:500],
                "text": evidence.text[:900],
            }
            for evidence in evidences
        ]

    def _domain_guidance(
        self,
        topic: str,
        evidence_payload: list[dict],
        experiment_profile: dict,
    ) -> str:
        combined = " ".join(
            [
                topic,
                json.dumps(evidence_payload, ensure_ascii=False),
                json.dumps(experiment_profile, ensure_ascii=False),
            ]
        ).lower()
        if self.heuristic._is_geolocalization_topic(combined):
            return "\n".join(
                [
                    "- Do not propose a generic accuracy-improvement idea.",
                    "- The title must name a concrete mechanism or evaluation slice, not only the task.",
                    "- The hypothesis must identify one failure mode such as region imbalance, long-tail geography, candidate retrieval miss, reasoning inconsistency, hierarchy error propagation, or benchmark leakage.",
                    "- The method sketch must include a specific intervention such as distance-aware reranking, hierarchy-aware token calibration, evidence-guided VLM reasoning, region-balanced hard negative mining, or coordinate uncertainty calibration.",
                    "- Use the suggested datasets, baselines, metrics, and risks unless the evidence clearly supports better paper-specific choices.",
                    "- The novelty argument must contrast against the source paper and at least one named baseline family.",
                ]
            )
        return "\n".join(
            [
                "- Avoid generic extensions; anchor the idea in the cited evidence.",
                "- The title must name the intervention and evaluation slice.",
                "- Prefer a small, executable first experiment with a clear baseline and failure metric.",
            ]
        )
