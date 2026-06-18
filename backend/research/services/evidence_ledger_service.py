from sqlalchemy.orm import Session

from backend.research.models import (
    Evidence,
    ExperimentAnalysis,
    Idea,
    IdeaAssumptionAudit,
    IdeaEvidenceLedger,
    NoveltyCheck,
    ProposalDraft,
    ProposalReview,
    RelatedWorkMatrix,
)
from backend.research.services.artifact_graph_service import ArtifactGraphService
from backend.research.services.graph_service import GraphService


class IdeaEvidenceLedgerService:
    def __init__(self, session: Session):
        self.session = session

    def create_ledger(
        self,
        idea_id: str,
        *,
        claims: list[str] | None = None,
        created_by: str = "system",
    ) -> IdeaEvidenceLedger:
        idea = self.session.get(Idea, idea_id)
        if idea is None:
            raise ValueError("Idea not found")

        evidences = self._load_evidence(idea.evidence_ids_json or [])
        draft = self._latest(ProposalDraft, idea.id)
        review = self._latest(ProposalReview, idea.id)
        analysis = self._latest(ExperimentAnalysis, idea.id)
        novelty_check = self._latest(NoveltyCheck, idea.id)
        matrix = self._latest(RelatedWorkMatrix, idea.id)
        audit = self._latest(IdeaAssumptionAudit, idea.id)

        ledger_claims = self._build_claims(
            idea,
            claims=claims,
            draft=draft,
            evidences=evidences,
            review=review,
            analysis=analysis,
            novelty_check=novelty_check,
            matrix=matrix,
            audit=audit,
        )
        evidence_links = self._build_evidence_links(evidences, ledger_claims)
        counterevidence = self._counterevidence(
            novelty_check=novelty_check,
            review=review,
            analysis=analysis,
            matrix=matrix,
        )
        missing_evidence = self._missing_evidence(
            idea=idea,
            review=review,
            matrix=matrix,
            audit=audit,
            ledger_claims=ledger_claims,
        )
        risk_register = self._risk_register(
            idea=idea,
            novelty_check=novelty_check,
            review=review,
            analysis=analysis,
            missing_evidence=missing_evidence,
        )
        evidence_quality = self._evidence_quality(evidence_links)
        coverage_score = self._coverage_score(
            ledger_claims=ledger_claims,
            evidence_links=evidence_links,
            evidence_quality=evidence_quality,
            missing_evidence=missing_evidence,
            counterevidence=counterevidence,
            analysis=analysis,
        )
        summary = self._summary(
            ledger_claims=ledger_claims,
            evidence_links=evidence_links,
            evidence_quality=evidence_quality,
            counterevidence=counterevidence,
            missing_evidence=missing_evidence,
            risk_register=risk_register,
            coverage_score=coverage_score,
        )
        ledger = IdeaEvidenceLedger(
            idea_id=idea.id,
            status="completed",
            claims_json=ledger_claims,
            evidence_links_json=evidence_links,
            counterevidence_json=counterevidence,
            missing_evidence_json=missing_evidence,
            risk_register_json=risk_register,
            source_artifacts_json={
                "latest_proposal_draft_id": draft.id if draft else "",
                "latest_proposal_review_id": review.id if review else "",
                "latest_experiment_analysis_id": analysis.id if analysis else "",
                "latest_novelty_check_id": novelty_check.id if novelty_check else "",
                "latest_related_work_matrix_id": matrix.id if matrix else "",
                "latest_assumption_audit_id": audit.id if audit else "",
                "evidence_ids": [evidence.id for evidence in evidences],
            },
            summary_json=summary,
            coverage_score=coverage_score,
            created_by=created_by or "system",
        )
        self.session.add(ledger)
        self.session.flush()
        ledger.markdown_export = self._render_markdown(ledger, idea)
        self.session.commit()
        self.session.refresh(ledger)
        ArtifactGraphService(GraphService(self.session)).link_idea_evidence_ledger(ledger)
        self.session.commit()
        self.session.refresh(ledger)
        return ledger

    def list_for_idea(self, idea_id: str, limit: int = 20) -> list[IdeaEvidenceLedger]:
        if self.session.get(Idea, idea_id) is None:
            raise ValueError("Idea not found")
        limit = max(1, min(limit, 100))
        return (
            self.session.query(IdeaEvidenceLedger)
            .filter(IdeaEvidenceLedger.idea_id == idea_id)
            .order_by(IdeaEvidenceLedger.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_ledger(self, idea_id: str, ledger_id: str) -> IdeaEvidenceLedger | None:
        return (
            self.session.query(IdeaEvidenceLedger)
            .filter(IdeaEvidenceLedger.id == ledger_id, IdeaEvidenceLedger.idea_id == idea_id)
            .first()
        )

    def _latest(self, model, idea_id: str):
        return (
            self.session.query(model)
            .filter(model.idea_id == idea_id)
            .order_by(model.created_at.desc())
            .first()
        )

    def _load_evidence(self, evidence_ids: list[str]) -> list[Evidence]:
        if not evidence_ids:
            return []
        records = self.session.query(Evidence).filter(Evidence.id.in_(evidence_ids)).all()
        by_id = {record.id: record for record in records}
        return [by_id[evidence_id] for evidence_id in evidence_ids if evidence_id in by_id]

    def _build_claims(
        self,
        idea: Idea,
        *,
        claims: list[str] | None,
        draft: ProposalDraft | None,
        evidences: list[Evidence],
        review: ProposalReview | None,
        analysis: ExperimentAnalysis | None,
        novelty_check: NoveltyCheck | None,
        matrix: RelatedWorkMatrix | None,
        audit: IdeaAssumptionAudit | None,
    ) -> list[dict]:
        claim_texts = self._clean_list(claims) or self._default_claim_texts(idea, draft)
        ledger_claims = []
        for idx, text in enumerate(claim_texts[:8], start=1):
            claim_id = f"C{idx}"
            claim_type = self._claim_type(idx, text)
            support_ids = [
                evidence.id
                for evidence in evidences
                if self._overlaps(text, evidence.summary, evidence.supports, evidence.text)
            ]
            if not support_ids:
                support_ids = self._typed_support_evidence_ids(claim_type, evidences)
            if evidences and not support_ids and idx == 1:
                support_ids = [evidence.id for evidence in evidences[:3]]
            challenge_signals = self._claim_challenges(
                text,
                review=review,
                analysis=analysis,
                novelty_check=novelty_check,
                matrix=matrix,
                audit=audit,
            )
            support_level = self._support_level(
                support_count=len(support_ids),
                challenge_count=len(challenge_signals),
                analysis=analysis,
            )
            ledger_claims.append(
                {
                    "claim_id": claim_id,
                    "claim": text,
                    "claim_type": claim_type,
                    "support_level": support_level,
                    "supporting_evidence_ids": support_ids,
                    "challenge_signals": challenge_signals[:6],
                    "next_validation": self._next_validation(text, support_level),
                }
            )
        return ledger_claims

    def _default_claim_texts(self, idea: Idea, draft: ProposalDraft | None) -> list[str]:
        texts = [
            idea.core_hypothesis,
            idea.novelty_argument,
            idea.expected_contribution,
            idea.method_sketch,
        ]
        if draft:
            texts.extend(
                [
                    draft.novelty_statement,
                    draft.method_summary,
                    draft.experiment_summary,
                ]
            )
        return self._clean_list(texts) or [
            "The idea has a falsifiable research claim worth testing.",
        ]

    def _typed_support_evidence_ids(
        self, claim_type: str, evidences: list[Evidence], limit: int = 3
    ) -> list[str]:
        preferred_types = {
            "hypothesis": ["limitation", "future_work", "problem", "result"],
            "novelty": ["limitation", "future_work", "comparison", "problem"],
            "method": ["method", "dataset", "problem", "limitation"],
            "evaluation": ["result", "dataset", "comparison", "method"],
            "contribution": ["result", "future_work", "limitation", "problem", "claim"],
        }.get(claim_type, [])
        support_ids: list[str] = []
        for evidence_type in preferred_types:
            for evidence in evidences:
                if evidence.evidence_type != evidence_type or evidence.id in support_ids:
                    continue
                support_ids.append(evidence.id)
                if len(support_ids) >= limit:
                    return support_ids
        return support_ids

    def _build_evidence_links(
        self,
        evidences: list[Evidence],
        ledger_claims: list[dict],
    ) -> list[dict]:
        links = []
        for evidence in evidences:
            linked_claim_ids = [
                claim["claim_id"]
                for claim in ledger_claims
                if evidence.id in claim.get("supporting_evidence_ids", [])
            ]
            links.append(
                {
                    "evidence_id": evidence.id,
                    "paper_id": evidence.paper_id,
                    "evidence_type": evidence.evidence_type,
                    "summary": self._clean(evidence.summary or evidence.supports or evidence.text),
                    "confidence": evidence.confidence,
                    "linked_claim_ids": linked_claim_ids,
                    "support_role": "direct_support" if linked_claim_ids else "context",
                }
            )
        return links

    def _counterevidence(
        self,
        *,
        novelty_check: NoveltyCheck | None,
        review: ProposalReview | None,
        analysis: ExperimentAnalysis | None,
        matrix: RelatedWorkMatrix | None,
    ) -> list[dict]:
        items = []
        if novelty_check:
            for signal in (novelty_check.collision_signals_json or [])[:6]:
                items.append(
                    {
                        "source_type": "novelty_check",
                        "source_id": novelty_check.id,
                        "signal": self._clean(str(signal.get("label") or signal)),
                        "severity": novelty_check.risk_level or "medium",
                    }
                )
        if matrix:
            for item in (matrix.items_json or [])[:6]:
                overlap = float(item.get("overlap_score") or 0.0)
                if overlap >= 0.35:
                    items.append(
                        {
                            "source_type": "related_work_matrix",
                            "source_id": matrix.id,
                            "signal": self._clean(
                                f"High-overlap related work: {item.get('title', '')}"
                            ),
                            "severity": "high" if overlap >= 0.65 else "medium",
                        }
                    )
        if review:
            for concern in (review.concerns_json or [])[:6]:
                items.append(
                    {
                        "source_type": "proposal_review",
                        "source_id": review.id,
                        "signal": self._clean(str(concern)),
                        "severity": "medium",
                    }
                )
        if analysis and analysis.decision in {"contradicts_hypothesis", "inconclusive"}:
            for concern in (analysis.concerns_json or [])[:6]:
                items.append(
                    {
                        "source_type": "experiment_analysis",
                        "source_id": analysis.id,
                        "signal": self._clean(str(concern)),
                        "severity": "high"
                        if analysis.decision == "contradicts_hypothesis"
                        else "medium",
                    }
                )
        return self._dedupe_dicts(items, key="signal")

    def _missing_evidence(
        self,
        *,
        idea: Idea,
        review: ProposalReview | None,
        matrix: RelatedWorkMatrix | None,
        audit: IdeaAssumptionAudit | None,
        ledger_claims: list[dict],
    ) -> list[dict]:
        items = []
        for claim in ledger_claims:
            if not claim.get("supporting_evidence_ids"):
                items.append(
                    {
                        "gap": f"No direct evidence is linked to claim {claim['claim_id']}.",
                        "source_type": "claim_coverage",
                        "source_id": claim["claim_id"],
                        "priority": "high",
                    }
                )
        if len(idea.evidence_ids_json or []) < 2:
            items.append(
                {
                    "gap": "The idea has fewer than two linked evidence records.",
                    "source_type": "idea",
                    "source_id": idea.id,
                    "priority": "high",
                }
            )
        if review:
            for item in (review.missing_evidence_json or [])[:8]:
                items.append(
                    {
                        "gap": self._clean(str(item)),
                        "source_type": "proposal_review",
                        "source_id": review.id,
                        "priority": "high",
                    }
                )
        if matrix:
            for item in (matrix.missing_searches_json or [])[:8]:
                items.append(
                    {
                        "gap": f"Missing related-work search: {self._clean(str(item))}",
                        "source_type": "related_work_matrix",
                        "source_id": matrix.id,
                        "priority": "medium",
                    }
                )
        if audit:
            for item in (audit.assumptions_json or [])[:8]:
                if item.get("status") in {"untested", "needs_search", "needs_more_evidence"}:
                    items.append(
                        {
                            "gap": self._clean(
                                str(item.get("validation_signal") or item.get("assumption"))
                            ),
                            "source_type": "assumption_audit",
                            "source_id": audit.id,
                            "priority": "high" if item.get("risk_level") == "high" else "medium",
                        }
                    )
        return self._dedupe_dicts(items, key="gap")

    def _risk_register(
        self,
        *,
        idea: Idea,
        novelty_check: NoveltyCheck | None,
        review: ProposalReview | None,
        analysis: ExperimentAnalysis | None,
        missing_evidence: list[dict],
    ) -> list[dict]:
        risks = [
            {"risk": self._clean(str(item)), "source_type": "idea", "severity": "medium"}
            for item in (idea.risks_json or [])
        ]
        if novelty_check and novelty_check.risk_level not in {"", "low"}:
            risks.append(
                {
                    "risk": self._clean(novelty_check.summary),
                    "source_type": "novelty_check",
                    "severity": novelty_check.risk_level,
                }
            )
        if review:
            risks.extend(
                {
                    "risk": self._clean(str(item)),
                    "source_type": "proposal_review",
                    "severity": "medium",
                }
                for item in (review.concerns_json or [])[:6]
            )
        if analysis:
            risks.extend(
                {
                    "risk": self._clean(str(item)),
                    "source_type": "experiment_analysis",
                    "severity": "high"
                    if analysis.decision == "contradicts_hypothesis"
                    else "medium",
                }
                for item in (analysis.concerns_json or [])[:6]
            )
        if missing_evidence:
            risks.append(
                {
                    "risk": f"{len(missing_evidence)} evidence gaps remain open.",
                    "source_type": "evidence_ledger",
                    "severity": "high" if len(missing_evidence) >= 4 else "medium",
                }
            )
        if not risks:
            risks.append(
                {
                    "risk": "No explicit risk has been recorded yet; verify assumptions before execution.",
                    "source_type": "evidence_ledger",
                    "severity": "medium",
                }
            )
        return self._dedupe_dicts(risks, key="risk")

    def _evidence_quality(self, evidence_links: list[dict]) -> dict:
        direct_links = [link for link in evidence_links if link.get("linked_claim_ids")]
        context_links = [link for link in evidence_links if not link.get("linked_claim_ids")]
        direct_types = {
            link.get("evidence_type") for link in direct_links if link.get("evidence_type")
        }
        direct_papers = {link.get("paper_id") for link in direct_links if link.get("paper_id")}
        return {
            "direct_evidence_link_count": len(direct_links),
            "context_evidence_link_count": len(context_links),
            "linked_evidence_type_count": len(direct_types),
            "linked_evidence_types": sorted(direct_types),
            "linked_source_paper_count": len(direct_papers),
            "linked_source_paper_ids": sorted(direct_papers),
        }

    def _coverage_score(
        self,
        *,
        ledger_claims: list[dict],
        evidence_links: list[dict],
        evidence_quality: dict,
        missing_evidence: list[dict],
        counterevidence: list[dict],
        analysis: ExperimentAnalysis | None,
    ) -> float:
        if not ledger_claims:
            return 0.0
        supported_claims = len(
            [claim for claim in ledger_claims if claim.get("supporting_evidence_ids")]
        )
        claim_support = supported_claims / len(ledger_claims)
        direct_evidence_bonus = min(evidence_quality["direct_evidence_link_count"], 8) / 24
        type_diversity_bonus = min(evidence_quality["linked_evidence_type_count"], 4) / 20
        source_diversity_bonus = min(evidence_quality["linked_source_paper_count"], 3) / 30
        analysis_bonus = 0.15 if analysis and analysis.decision == "supports_hypothesis" else 0.0
        missing_penalty = min(len(missing_evidence), 8) * 0.04
        counter_penalty = min(len(counterevidence), 8) * 0.03
        return round(
            max(
                0.0,
                min(
                    1.0,
                    claim_support * 0.6
                    + direct_evidence_bonus
                    + type_diversity_bonus
                    + source_diversity_bonus
                    + analysis_bonus
                    - missing_penalty
                    - counter_penalty,
                ),
            ),
            4,
        )

    def _summary(
        self,
        *,
        ledger_claims: list[dict],
        evidence_links: list[dict],
        evidence_quality: dict,
        counterevidence: list[dict],
        missing_evidence: list[dict],
        risk_register: list[dict],
        coverage_score: float,
    ) -> dict:
        supported = len([claim for claim in ledger_claims if claim.get("supporting_evidence_ids")])
        high_risks = len([risk for risk in risk_register if risk.get("severity") == "high"])
        return {
            "claim_count": len(ledger_claims),
            "supported_claim_count": supported,
            "unsupported_claim_count": len(ledger_claims) - supported,
            "evidence_link_count": len(evidence_links),
            **evidence_quality,
            "counterevidence_count": len(counterevidence),
            "missing_evidence_count": len(missing_evidence),
            "high_risk_count": high_risks,
            "coverage_score": coverage_score,
            "decision_hint": self._decision_hint(coverage_score, len(missing_evidence), high_risks),
        }

    def _decision_hint(
        self,
        coverage_score: float,
        missing_count: int,
        high_risk_count: int,
    ) -> str:
        if coverage_score >= 0.75 and high_risk_count == 0:
            return "ready_for_advisor_discussion"
        if coverage_score >= 0.5 and missing_count <= 2:
            return "needs_targeted_evidence"
        return "evidence_building_required"

    def _render_markdown(self, ledger: IdeaEvidenceLedger, idea: Idea) -> str:
        summary = ledger.summary_json or {}
        lines = [
            f"# Evidence Ledger: {idea.title}",
            "",
            f"- Ledger ID: `{ledger.id}`",
            f"- Idea ID: `{idea.id}`",
            f"- Coverage Score: {ledger.coverage_score}",
            f"- Decision Hint: `{summary.get('decision_hint', '')}`",
            f"- Created By: {ledger.created_by}",
            "",
            "## Source Artifacts",
            "",
        ]
        for key, value in (ledger.source_artifacts_json or {}).items():
            lines.append(f"- {key}: `{value}`")

        lines.extend(["", "## Claims", ""])
        for claim in ledger.claims_json or []:
            lines.extend(
                [
                    f"### {claim.get('claim_id', '')}. {claim.get('claim', '')}",
                    "",
                    f"- Type: `{claim.get('claim_type', '')}`",
                    f"- Support Level: `{claim.get('support_level', '')}`",
                    f"- Supporting Evidence IDs: {self._inline_ids(claim.get('supporting_evidence_ids') or [])}",
                    f"- Next Validation: {claim.get('next_validation', '')}",
                    "",
                ]
            )
            challenges = claim.get("challenge_signals") or []
            if challenges:
                lines.append("Challenge signals:")
                lines.extend(f"- {item}" for item in challenges)
                lines.append("")

        lines.extend(["", "## Evidence Quality Signals", ""])
        lines.extend(
            [
                f"- Direct Evidence Links: {summary.get('direct_evidence_link_count', 0)}",
                f"- Context Evidence Links: {summary.get('context_evidence_link_count', 0)}",
                f"- Linked Evidence Types: {self._inline_ids(summary.get('linked_evidence_types') or [])}",
                f"- Linked Source Papers: {self._inline_ids(summary.get('linked_source_paper_ids') or [])}",
            ]
        )

        lines.extend(["", "## Evidence Links", ""])
        if ledger.evidence_links_json:
            for link in ledger.evidence_links_json:
                lines.append(
                    f"- `{link.get('evidence_id', '')}` `{link.get('support_role', '')}` "
                    f"claims={self._inline_ids(link.get('linked_claim_ids') or [])}: "
                    f"{link.get('summary', '')}"
                )
        else:
            lines.append("- No linked evidence records.")

        lines.extend(["", "## Counterevidence And Challenges", ""])
        self._append_dict_items(lines, ledger.counterevidence_json or [], "signal")
        lines.extend(["", "## Missing Evidence", ""])
        self._append_dict_items(lines, ledger.missing_evidence_json or [], "gap")
        lines.extend(["", "## Risk Register", ""])
        self._append_dict_items(lines, ledger.risk_register_json or [], "risk")
        return "\n".join(lines).strip() + "\n"

    def _claim_challenges(
        self,
        claim: str,
        *,
        review: ProposalReview | None,
        analysis: ExperimentAnalysis | None,
        novelty_check: NoveltyCheck | None,
        matrix: RelatedWorkMatrix | None,
        audit: IdeaAssumptionAudit | None,
    ) -> list[str]:
        signals = []
        if review:
            signals.extend(
                str(item)
                for item in (review.concerns_json or [])
                if self._overlaps(claim, str(item))
            )
            signals.extend(
                str(item)
                for item in (review.missing_evidence_json or [])
                if self._overlaps(claim, str(item))
            )
        if analysis and analysis.decision != "supports_hypothesis":
            signals.extend(str(item) for item in (analysis.concerns_json or [])[:4])
        if novelty_check and novelty_check.risk_level not in {"", "low"}:
            signals.append(f"Novelty risk is {novelty_check.risk_level}: {novelty_check.summary}")
        if matrix:
            signals.extend(
                f"Related-work gap remains: {item}"
                for item in (matrix.missing_searches_json or [])[:3]
            )
        if audit:
            signals.extend(
                str(item.get("assumption"))
                for item in (audit.assumptions_json or [])
                if item.get("risk_level") == "high"
            )
        return self._clean_list(signals)

    def _support_level(
        self,
        *,
        support_count: int,
        challenge_count: int,
        analysis: ExperimentAnalysis | None,
    ) -> str:
        if analysis and analysis.decision == "supports_hypothesis" and support_count:
            return "experiment_supported"
        if support_count >= 2 and challenge_count == 0:
            return "supported"
        if support_count:
            return "partially_supported"
        if challenge_count:
            return "challenged"
        return "unsupported"

    def _claim_type(self, idx: int, text: str) -> str:
        lower = text.lower()
        if idx == 1 or "hypothesis" in lower:
            return "hypothesis"
        if "novel" in lower or "different" in lower:
            return "novelty"
        if "method" in lower or "approach" in lower:
            return "method"
        if "experiment" in lower or "metric" in lower:
            return "evaluation"
        return "contribution"

    def _next_validation(self, claim: str, support_level: str) -> str:
        if support_level in {"unsupported", "challenged"}:
            return f"Attach direct evidence or design a falsification check for: {claim}"
        if support_level == "partially_supported":
            return "Add independent supporting evidence and check nearest related work."
        return "Keep this claim linked when drafting advisor-facing materials."

    def _append_dict_items(self, lines: list[str], items: list[dict], key: str) -> None:
        if not items:
            lines.append("- none")
            return
        for item in items:
            details = []
            if item.get("source_type"):
                details.append(f"source={item['source_type']}")
            if item.get("priority"):
                details.append(f"priority={item['priority']}")
            if item.get("severity"):
                details.append(f"severity={item['severity']}")
            suffix = f" ({', '.join(details)})" if details else ""
            lines.append(f"- {item.get(key, '')}{suffix}")

    def _dedupe_dicts(self, items: list[dict], *, key: str) -> list[dict]:
        seen = set()
        deduped = []
        for item in items:
            value = self._clean(str(item.get(key) or ""))
            if not value or value in seen:
                continue
            seen.add(value)
            deduped.append({**item, key: value})
        return deduped

    def _overlaps(self, seed: str, *texts: str) -> bool:
        seed_terms = self._terms(seed)
        if not seed_terms:
            return False
        text_terms: set[str] = set()
        for text in texts:
            text_terms.update(self._terms(text))
        return len(seed_terms.intersection(text_terms)) >= 2

    def _terms(self, text: str) -> set[str]:
        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "will",
            "can",
            "into",
            "than",
            "idea",
            "research",
            "method",
        }
        return {
            token.strip(".,;:!?()[]{}").lower()
            for token in (text or "").split()
            if len(token.strip(".,;:!?()[]{}")) >= 4
            and token.strip(".,;:!?()[]{}").lower() not in stopwords
        }

    def _clean_list(self, items: list[str] | None) -> list[str]:
        cleaned = []
        for item in items or []:
            text = self._clean(str(item))
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned

    def _inline_ids(self, ids: list[str]) -> str:
        return ", ".join(f"`{item}`" for item in ids) if ids else "`none`"

    def _clean(self, text: str) -> str:
        return " ".join((text or "").split())
