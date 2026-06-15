from dataclasses import dataclass
import os
from pathlib import Path
import re

from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy.orm import Session

from backend.research.config import settings
from backend.research.models import Chunk, Evidence, Paper, PaperSection
from backend.research.services.graph_service import GraphService


SECTION_PATTERNS = [
    ("abstract", r"^\s*(abstract|摘要)\s*$"),
    ("introduction", r"^\s*(\d+\.?\s*)?(introduction|引言)\s*$"),
    ("related_work", r"^\s*(\d+\.?\s*)?(related work|background|相关工作)\s*$"),
    ("method", r"^\s*(\d+\.?\s*)?(method|methodology|approach|model|framework|方法|模型|框架)\s*$"),
    ("experiment", r"^\s*(\d+\.?\s*)?(experiment|experiments|evaluation|实验|评估)\s*$"),
    ("result", r"^\s*(\d+\.?\s*)?(results|result|analysis|结果|分析)\s*$"),
    ("limitation", r"^\s*(\d+\.?\s*)?(limitations|limitation|局限|不足)\s*$"),
    (
        "future_work",
        r"^\s*(\d+\.?\s*)?(future work|future directions|next steps|未来工作|后续工作)\s*$",
    ),
    ("conclusion", r"^\s*(\d+\.?\s*)?(conclusion|conclusions|discussion|结论|讨论)\s*$"),
    ("reference", r"^\s*(references|bibliography|参考文献)\s*$"),
]

SECTION_TO_EVIDENCE = {
    "abstract": "claim",
    "introduction": "problem",
    "related_work": "comparison",
    "method": "method",
    "experiment": "dataset",
    "result": "result",
    "limitation": "limitation",
    "future_work": "future_work",
    "conclusion": "future_work",
    "reference": "citation",
    "full_text": "claim",
}


@dataclass
class IngestionResult:
    paper: Paper
    section_count: int
    chunk_count: int
    evidence_count: int


class DocumentIngestionService:
    def __init__(self, session: Session):
        self.session = session

    async def ingest_upload(self, file: UploadFile) -> IngestionResult:
        upload_dir = Path(os.getenv("PAPER_UPLOAD_DIR") or settings.paper_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = Path(file.filename or "uploaded_document").name
        suffix = Path(filename).suffix.lower()
        allowed_extensions = self._allowed_upload_extensions()
        if suffix not in allowed_extensions:
            allowed = ", ".join(sorted(allowed_extensions))
            raise ValueError(
                f"Unsupported file type: {suffix or 'none'}. Supported types: {allowed}"
            )

        file_path = upload_dir / filename
        content = await file.read()
        if not content:
            raise ValueError("Uploaded file is empty.")
        max_bytes = self._upload_max_bytes()
        if max_bytes > 0 and len(content) > max_bytes:
            raise ValueError(
                f"Uploaded file is too large: {len(content)} bytes. Max allowed size is {max_bytes} bytes."
            )
        self._validate_upload_content(filename, suffix, content)
        file_path.write_bytes(content)

        text = self._extract_text(file_path)
        if not text.strip():
            raise ValueError("No text could be extracted from the uploaded file.")

        paper = Paper(
            title=self._guess_title(filename, text),
            filename=filename,
            file_path=str(file_path),
            source_type="upload",
            status="parsed",
        )
        self.session.add(paper)
        self.session.flush()
        graph = GraphService(self.session)
        paper_node = graph.get_or_create_node(
            node_type="paper",
            label=paper.title,
            canonical_key=paper.id,
            payload={"filename": filename, "source_type": "upload"},
        )

        sections = self._detect_sections(text)
        section_count = 0
        chunk_count = 0
        evidence_count = 0

        for order_index, section in enumerate(sections):
            section_row = PaperSection(
                paper_id=paper.id,
                title=section["title"],
                section_type=section["section_type"],
                level=1,
                page_start=None,
                page_end=None,
                text=section["text"],
                order_index=order_index,
            )
            self.session.add(section_row)
            self.session.flush()
            section_count += 1

            section_chunks = self._split_text(section["text"])
            root_chunk_id = ""
            for chunk_idx, chunk_text in enumerate(section_chunks):
                chunk_id = f"{paper.id}::{section_row.id}::chunk::{chunk_idx}"
                if not root_chunk_id:
                    root_chunk_id = chunk_id
                chunk = Chunk(
                    paper_id=paper.id,
                    section_id=section_row.id,
                    chunk_id=chunk_id,
                    parent_chunk_id="",
                    root_chunk_id=root_chunk_id,
                    chunk_level=1,
                    chunk_idx=chunk_idx,
                    page_number=None,
                    text=chunk_text,
                    token_count=len(chunk_text.split()),
                )
                self.session.add(chunk)
                chunk_count += 1

            evidence_text = self._pick_evidence_text(section["text"])
            if evidence_text:
                evidence = Evidence(
                    paper_id=paper.id,
                    section_id=section_row.id,
                    chunk_id=root_chunk_id,
                    evidence_type=SECTION_TO_EVIDENCE.get(section["section_type"], "claim"),
                    text=evidence_text,
                    summary=evidence_text[:500],
                    supports=section["title"],
                    confidence=0.55,
                    page_number=None,
                    metadata_json={"source": "heuristic_section_extraction"},
                )
                self.session.add(evidence)
                self.session.flush()
                evidence_node = graph.get_or_create_node(
                    node_type="evidence",
                    label=f"{evidence.evidence_type}: {section['title']}",
                    canonical_key=evidence.id,
                    payload={
                        "paper_id": paper.id,
                        "evidence_type": evidence.evidence_type,
                        "section_type": section["section_type"],
                    },
                )
                graph.create_edge(
                    source_node=paper_node,
                    target_node=evidence_node,
                    edge_type="paper_has_evidence",
                    evidence_ids=[evidence.id],
                )
                evidence_count += 1

        paper.status = "indexed"
        self.session.commit()
        self.session.refresh(paper)
        return IngestionResult(
            paper=paper,
            section_count=section_count,
            chunk_count=chunk_count,
            evidence_count=evidence_count,
        )

    def _allowed_upload_extensions(self) -> set[str]:
        raw = (
            os.getenv("PAPER_UPLOAD_ALLOWED_EXTENSIONS") or settings.paper_upload_allowed_extensions
        )
        extensions = set()
        for item in raw.split(","):
            extension = item.strip().lower()
            if not extension:
                continue
            extensions.add(extension if extension.startswith(".") else f".{extension}")
        return extensions or {".txt", ".md", ".pdf"}

    def _upload_max_bytes(self) -> int:
        raw = os.getenv("PAPER_UPLOAD_MAX_BYTES") or str(settings.paper_upload_max_bytes)
        try:
            value = int(raw)
        except ValueError:
            return settings.paper_upload_max_bytes
        return value if value > 0 else settings.paper_upload_max_bytes

    def _validate_upload_content(self, filename: str, suffix: str, content: bytes) -> None:
        if suffix == ".pdf" and not content.startswith(b"%PDF-"):
            raise ValueError(f"Uploaded file {filename} does not appear to be a PDF document.")
        if suffix in {".txt", ".md"}:
            if b"\x00" in content:
                raise ValueError(f"Uploaded file {filename} appears to be binary, not text.")
            try:
                content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"Uploaded file {filename} must be UTF-8 encoded text.") from exc

    def _extract_text(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            reader = PdfReader(str(file_path))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            return "\n\n".join(pages)
        if suffix in {".txt", ".md"}:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        raise ValueError(f"Unsupported file type: {suffix}. Supported types: .pdf, .txt, .md")

    def _guess_title(self, filename: str, text: str) -> str:
        for line in text.splitlines():
            candidate = line.strip()
            if 8 <= len(candidate) <= 180:
                return candidate
        return Path(filename).stem

    def _normalize_section_heading(self, line: str) -> str:
        normalized = line.strip()
        normalized = re.sub(r"^#{1,6}\s*", "", normalized)
        normalized = re.sub(r"\s*#{1,6}$", "", normalized)
        return normalized.strip(" *_`")

    def _detect_sections(self, text: str) -> list[dict]:
        lines = text.splitlines()
        matches: list[tuple[int, str, str]] = []
        for idx, line in enumerate(lines):
            normalized = self._normalize_section_heading(line)
            if len(normalized) > 80:
                continue
            for section_type, pattern in SECTION_PATTERNS:
                if re.match(pattern, normalized, flags=re.IGNORECASE):
                    matches.append((idx, normalized, section_type))
                    break

        if not matches:
            return [{"title": "Full Text", "section_type": "full_text", "text": text.strip()}]

        sections = []
        for pos, (line_idx, title, section_type) in enumerate(matches):
            next_idx = matches[pos + 1][0] if pos + 1 < len(matches) else len(lines)
            section_text = "\n".join(lines[line_idx + 1 : next_idx]).strip()
            if not section_text:
                continue
            sections.append({"title": title, "section_type": section_type, "text": section_text})

        if not sections:
            return [{"title": "Full Text", "section_type": "full_text", "text": text.strip()}]
        return sections

    def _split_text(self, text: str, chunk_size: int = 1600, overlap: int = 200) -> list[str]:
        cleaned = " ".join(text.split())
        if len(cleaned) <= chunk_size:
            return [cleaned]

        chunks = []
        start = 0
        while start < len(cleaned):
            end = min(start + chunk_size, len(cleaned))
            chunks.append(cleaned[start:end].strip())
            if end >= len(cleaned):
                break
            start = max(0, end - overlap)
        return [chunk for chunk in chunks if chunk]

    def _pick_evidence_text(self, text: str, limit: int = 900) -> str:
        cleaned = " ".join(text.split())
        if not cleaned:
            return ""
        return cleaned[:limit]
