from sqlalchemy.orm import Session

from backend.research.models import Evidence, Paper, PaperCard


EVIDENCE_TO_CARD_FIELD = {
    "problem": "problem_json",
    "claim": "contributions_json",
    "comparison": "motivation_json",
    "method": "method_json",
    "dataset": "datasets_json",
    "metric": "metrics_json",
    "result": "results_json",
    "limitation": "limitations_json",
    "future_work": "future_work_json",
}


class PaperCardService:
    def __init__(self, session: Session):
        self.session = session

    def get_card(self, paper_id: str) -> PaperCard | None:
        return self.session.query(PaperCard).filter(PaperCard.paper_id == paper_id).one_or_none()

    def extract_heuristic_card(self, paper_id: str) -> PaperCard:
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

        card = self.get_card(paper_id)
        if card is None:
            card = PaperCard(paper_id=paper_id)
            self.session.add(card)

        fields = {
            "problem_json": {"items": []},
            "motivation_json": {"items": []},
            "contributions_json": {"items": []},
            "method_json": {"items": []},
            "datasets_json": {"items": []},
            "metrics_json": {"items": []},
            "baselines_json": {"items": []},
            "results_json": {"items": []},
            "limitations_json": {"items": []},
            "future_work_json": {"items": []},
            "open_questions_json": {"items": []},
        }
        keywords = set()

        for evidence in evidences:
            target_field = EVIDENCE_TO_CARD_FIELD.get(evidence.evidence_type)
            if target_field:
                fields[target_field]["items"].append(
                    {
                        "text": evidence.summary or evidence.text[:500],
                        "evidence_ids": [evidence.id],
                        "confidence": evidence.confidence,
                    }
                )
            if evidence.evidence_type:
                keywords.add(evidence.evidence_type)

        if not fields["problem_json"]["items"]:
            first = evidences[0]
            fields["problem_json"]["items"].append(
                {
                    "text": first.summary or first.text[:500],
                    "evidence_ids": [first.id],
                    "confidence": max(first.confidence - 0.1, 0.0),
                }
            )

        card.problem_json = fields["problem_json"]
        card.motivation_json = fields["motivation_json"]
        card.contributions_json = fields["contributions_json"]
        card.method_json = fields["method_json"]
        card.datasets_json = fields["datasets_json"]
        card.metrics_json = fields["metrics_json"]
        card.baselines_json = fields["baselines_json"]
        card.results_json = fields["results_json"]
        card.limitations_json = fields["limitations_json"]
        card.future_work_json = fields["future_work_json"]
        card.open_questions_json = fields["open_questions_json"]
        card.keywords_json = {"items": sorted(keywords)}
        card.extraction_model = "heuristic_v0"
        card.extraction_status = "completed"

        self.session.commit()
        self.session.refresh(card)
        return card
