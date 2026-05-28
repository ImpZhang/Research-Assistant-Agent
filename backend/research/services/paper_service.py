from sqlalchemy.orm import Session

from backend.research.models import Paper
from backend.research.schemas import PaperCreate


class PaperService:
    def __init__(self, session: Session):
        self.session = session

    def list_papers(self) -> list[Paper]:
        return self.session.query(Paper).order_by(Paper.created_at.desc()).all()

    def create_paper(self, payload: PaperCreate) -> Paper:
        paper = Paper(
            title=payload.title,
            authors_json=payload.authors,
            year=payload.year,
            venue=payload.venue,
            filename=payload.filename,
            file_path=payload.file_path,
            domain=payload.domain,
            task=payload.task,
            status="uploaded",
        )
        self.session.add(paper)
        self.session.commit()
        self.session.refresh(paper)
        return paper
