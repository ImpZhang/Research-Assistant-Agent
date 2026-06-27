from __future__ import annotations

import time

from backend.research.db import SessionLocal
from backend.research.models import Evidence, Paper, ResearchGap
from backend.research.schemas import IdeaCreate
from backend.research.services.structured_idea_service import StructuredIdeaService


def test_structured_idea_prompt_includes_geolocalization_evidence_and_constraints() -> None:
    marker = f"structuredidea{time.time_ns()}"
    session = SessionLocal()
    try:
        paper = Paper(
            title=f"{marker} GeoToken paper",
            filename="structured_idea_prompt.txt",
            source_type="pytest",
            status="indexed",
        )
        session.add(paper)
        session.flush()
        evidence = Evidence(
            paper_id=paper.id,
            evidence_type="claim",
            text=(
                f"{marker} hierarchical geolocalization uses S2 cells and reports "
                "IM2GPS3K and YFCC4K evaluation with coordinate-level metrics."
            ),
            summary=f"{marker} hierarchy and coordinate evaluation evidence.",
            supports="GeoToken hierarchical geolocalization benchmark claim",
            confidence=0.8,
        )
        session.add(evidence)
        session.flush()
        gap = ResearchGap(
            title=f"{marker} hierarchical geolocalization gap",
            description="hierarchical geolocalization can propagate token-level mistakes",
            gap_type="evaluation_gap",
            source_paper_ids_json=[paper.id],
            evidence_ids_json=[evidence.id],
            why_important="Coordinate-level geolocalization failures can be hidden by aggregate results.",
            why_unsolved="The evidence does not isolate hierarchy error propagation.",
            possible_approaches_json=["evaluate hierarchy-aware calibration"],
            feasibility_score=3.0,
            novelty_score=3.0,
            risk_level="medium",
            status="generated",
        )
        session.add(gap)
        session.commit()

        prompt = StructuredIdeaService(session)._build_prompt(gap, 1)

        assert "Evidence JSON" in prompt
        assert marker in prompt
        assert "Do not propose a generic accuracy-improvement idea" in prompt
        assert "hierarchy-aware token calibration" in prompt
        assert "IM2GPS3K" in prompt
        assert "Median geodesic error" in prompt
        assert "GeoToken source-paper comparison baseline" not in prompt
    finally:
        session.rollback()
        session.query(ResearchGap).filter(ResearchGap.title.like(f"%{marker}%")).delete(
            synchronize_session=False
        )
        session.query(Evidence).filter(Evidence.text.like(f"%{marker}%")).delete(
            synchronize_session=False
        )
        session.query(Paper).filter(Paper.title.like(f"%{marker}%")).delete(
            synchronize_session=False
        )
        session.commit()
        session.close()


def test_structured_idea_rewrites_duplicate_generic_geolocalization_title() -> None:
    marker = f"structuredtitle{time.time_ns()}"
    session = SessionLocal()
    try:
        paper = Paper(
            title=f"{marker} GeoToken paper",
            filename="structured_idea_title.txt",
            source_type="pytest",
            status="indexed",
        )
        session.add(paper)
        session.flush()
        evidence = Evidence(
            paper_id=paper.id,
            evidence_type="result",
            text=(
                f"{marker} hierarchical geolocalization with S2 cells is evaluated on "
                "IM2GPS3K and YFCC4K using geodesic coordinate metrics."
            ),
            summary=f"{marker} S2 hierarchy benchmark evidence.",
            supports="GeoToken hierarchy error propagation",
            confidence=0.8,
        )
        session.add(evidence)
        session.flush()
        gap = ResearchGap(
            title=f"{marker} hierarchical geolocalization gap",
            description="hierarchical geolocalization can propagate S2 token mistakes",
            gap_type="evaluation_gap",
            source_paper_ids_json=[paper.id],
            evidence_ids_json=[evidence.id],
            why_important="Coordinate-level geolocalization failures can be hidden by aggregate results.",
            why_unsolved="The evidence does not isolate hierarchy error propagation.",
            possible_approaches_json=["evaluate hierarchy-aware calibration"],
            status="generated",
        )
        session.add(gap)
        session.commit()
        service = StructuredIdeaService(session)
        payload = IdeaCreate(
            title="Gap-Targeted Method for worldwide geolocalization",
            research_question="Can the idea improve geolocalization?",
            core_hypothesis="A targeted method improves the gap.",
            motivation="The benchmark hides hierarchy errors.",
            method_sketch="Calibrate hierarchy predictions and evaluate coordinate errors.",
            expected_contribution="A clearer hierarchy-error evaluation.",
            novelty_argument="The idea targets a specific hierarchy failure.",
            datasets=["IM2GPS3K"],
            baselines=["GeoToken"],
            metrics=["Median geodesic error"],
            risks=["May only help one benchmark."],
            resource_requirements="Small benchmark slice.",
            target_venues=["GeoAI workshop"],
        )
        seen = set()
        seen_mechanisms = {
            service._title_mechanism_key(
                "Region-Balanced Hard Negative Mining for Worldwide Geolocalization"
            )
        }

        idea = service._create_idea(payload, gap, 0, seen, seen_mechanisms)

        assert idea.title != "Gap-Targeted Method for worldwide geolocalization"
        assert "Hierarchy-Error Calibration" in idea.title
        assert "IM2GPS3K-Style Worldwide Geolocalization" in idea.title
        assert service._title_key(idea.title) in seen
        assert service._title_mechanism_key(idea.title) in seen_mechanisms

        duplicate_mechanism_payload = payload.model_copy(
            update={"title": "Region-Balanced Hard Negative Mining for Worldwide Geolocalization"}
        )
        second_idea = service._create_idea(
            duplicate_mechanism_payload,
            gap,
            0,
            seen,
            seen_mechanisms,
        )

        assert not second_idea.title.startswith("Region-Balanced Hard Negative Mining")
        assert service._title_mechanism_key(second_idea.title) in seen_mechanisms
    finally:
        session.rollback()
        session.query(ResearchGap).filter(ResearchGap.title.like(f"%{marker}%")).delete(
            synchronize_session=False
        )
        session.query(Evidence).filter(Evidence.text.like(f"%{marker}%")).delete(
            synchronize_session=False
        )
        session.query(Paper).filter(Paper.title.like(f"%{marker}%")).delete(
            synchronize_session=False
        )
        session.commit()
        session.close()
