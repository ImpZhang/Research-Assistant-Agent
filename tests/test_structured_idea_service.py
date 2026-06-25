from __future__ import annotations

import time

from backend.research.db import SessionLocal
from backend.research.models import Evidence, Paper, ResearchGap
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
