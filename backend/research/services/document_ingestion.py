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


SECTION_NUMBERING_PREFIX = r"((\d+(?:\.\d+)*|[ivxlcdm]+)\.?\s*)?"


SECTION_PATTERNS = [
    ("abstract", r"^\s*(abstract|摘要)\s*[-:：.]?\s*$"),
    ("introduction", rf"^\s*{SECTION_NUMBERING_PREFIX}(introduction|引言)\s*$"),
    (
        "related_work",
        rf"^\s*{SECTION_NUMBERING_PREFIX}(related\s*work|background|preliminaries|相关工作)\s*$",
    ),
    (
        "method",
        rf"^\s*{SECTION_NUMBERING_PREFIX}(method|methods|methodology|approach|model|framework|implementation|方法|模型|框架)\s*$",
    ),
    (
        "experiment",
        rf"^\s*{SECTION_NUMBERING_PREFIX}(experiment|experiments|experimental\s*setup|evaluation|benchmark|ablation\s*study|实验|评估)\s*$",
    ),
    (
        "result",
        rf"^\s*{SECTION_NUMBERING_PREFIX}(results|result|analysis|results\s*and\s*discussion|结果|分析)\s*$",
    ),
    ("limitation", rf"^\s*{SECTION_NUMBERING_PREFIX}(limitations|limitation|局限|不足)\s*$"),
    (
        "future_work",
        rf"^\s*{SECTION_NUMBERING_PREFIX}(future\s*work|future directions|next steps|未来工作|后续工作)\s*$",
    ),
    (
        "conclusion",
        rf"^\s*{SECTION_NUMBERING_PREFIX}(conclusion|conclusions|discussion|conclusion\s*and\s*future\s*work|结论|讨论)\s*$",
    ),
    ("reference", r"^\s*(references|bibliography|参考文献)\s*\.?\s*$"),
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

        has_substantive_sections = any(
            section["section_type"] not in {"full_text", "reference"} for section in sections
        )

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

            section_text = section["text"]
            section_chunks = self._split_text(section_text)
            parent_chunk_id = f"{paper.id}::{section_row.id}::parent"
            root_chunk_id = parent_chunk_id
            # 父 chunk 保存章节级上下文；子 chunk 继续保持较小粒度，专门用于召回。
            if section_text.strip():
                parent_chunk = Chunk(
                    paper_id=paper.id,
                    section_id=section_row.id,
                    chunk_id=parent_chunk_id,
                    parent_chunk_id="",
                    root_chunk_id=parent_chunk_id,
                    chunk_level=0,
                    chunk_idx=-1,
                    page_number=None,
                    text=section_text,
                    token_count=len(section_text.split()),
                )
                self.session.add(parent_chunk)
                chunk_count += 1
            for chunk_idx, chunk_text in enumerate(section_chunks):
                chunk_id = f"{paper.id}::{section_row.id}::chunk::{chunk_idx}"
                chunk = Chunk(
                    paper_id=paper.id,
                    section_id=section_row.id,
                    chunk_id=chunk_id,
                    parent_chunk_id=parent_chunk_id,
                    root_chunk_id=root_chunk_id,
                    chunk_level=1,
                    chunk_idx=chunk_idx,
                    page_number=None,
                    text=chunk_text,
                    token_count=len(chunk_text.split()),
                )
                self.session.add(chunk)
                chunk_count += 1

            section_evidence_keys: set[str] = set()
            evidence_text = self._pick_evidence_text(
                section["text"],
                section_type=section["section_type"],
                has_substantive_sections=has_substantive_sections,
            )
            if evidence_text:
                self._create_evidence(
                    paper=paper,
                    paper_node=paper_node,
                    graph=graph,
                    section_row=section_row,
                    section=section,
                    chunk_id=root_chunk_id,
                    evidence_text=evidence_text,
                    source="heuristic_section_extraction",
                )
                section_evidence_keys.add(self._evidence_key(evidence_text))
                evidence_count += 1

            if section["section_type"] != "reference" and len(section_chunks) > 1:
                for chunk_idx, chunk_text in enumerate(section_chunks[1:4], start=1):
                    topup_text = self._pick_evidence_text(
                        chunk_text,
                        limit=700,
                        section_type=section["section_type"],
                        has_substantive_sections=False,
                    )
                    topup_key = self._evidence_key(topup_text)
                    if not topup_text or topup_key in section_evidence_keys:
                        continue
                    self._create_evidence(
                        paper=paper,
                        paper_node=paper_node,
                        graph=graph,
                        section_row=section_row,
                        section=section,
                        chunk_id=f"{paper.id}::{section_row.id}::chunk::{chunk_idx}",
                        evidence_text=topup_text,
                        source="heuristic_chunk_topup",
                        supports=f"{section['title']} (chunk {chunk_idx + 1})",
                        confidence=0.5,
                    )
                    section_evidence_keys.add(topup_key)
                    evidence_count += 1

            for structured in self._extract_structured_evidence(
                section["text"],
                section_type=section["section_type"],
                section_title=section["title"],
            ):
                structured_key = self._evidence_key(structured["text"])
                if not structured_key or structured_key in section_evidence_keys:
                    continue
                self._create_evidence(
                    paper=paper,
                    paper_node=paper_node,
                    graph=graph,
                    section_row=section_row,
                    section=section,
                    chunk_id=root_chunk_id,
                    evidence_text=structured["text"],
                    source=structured["source"],
                    supports=structured["supports"],
                    confidence=structured["confidence"],
                    evidence_type=structured["evidence_type"],
                    metadata=structured["metadata"],
                )
                section_evidence_keys.add(structured_key)
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
        fallback = self._title_from_filename(filename)
        for line in text.splitlines()[:80]:
            candidate = line.strip()
            candidate = " ".join(candidate.split())
            if 8 <= len(candidate) <= 180 and not self._looks_like_title_noise(candidate):
                return candidate
        return fallback

    def _title_from_filename(self, filename: str) -> str:
        stem = Path(filename).stem.replace("_", " ").strip()
        zotero_match = re.match(r"^.+?\s+等\s+-\s+\d{4}\s+-\s+(.+)$", stem)
        if zotero_match:
            return zotero_match.group(1).strip()
        return stem or "uploaded_document"

    def _looks_like_title_noise(self, candidate: str) -> bool:
        lower = candidate.lower()
        noisy_markers = [
            "latest updates:",
            "contents lists available",
            "journal homepage",
            "available online",
            "sciencedirect",
            "elsevier",
            "springer",
            "ieee transactions",
            "acm reference format",
            "proceedings of",
            "copyright",
            "all rights reserved",
            "issn",
            "isbn",
            "doi:",
            "http://",
            "https://",
            "www.",
            "department of",
            "university",
            "arxiv:",
        ]
        if any(marker in lower for marker in noisy_markers):
            return True
        words = re.findall(r"[A-Za-z][A-Za-z-]+", candidate)
        if len(words) < 3:
            return True
        numeric_chars = sum(char.isdigit() for char in candidate)
        if numeric_chars / max(len(candidate), 1) > 0.25:
            return True
        return False

    def _extract_structured_evidence(
        self,
        text: str,
        *,
        section_type: str,
        section_title: str,
    ) -> list[dict]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        records: list[dict] = []
        for idx, line in enumerate(lines):
            caption_type = self._caption_type(line)
            if caption_type:
                records.append(
                    {
                        "evidence_type": caption_type,
                        "text": self._caption_block(lines, idx),
                        "supports": f"{section_title} structured caption",
                        "source": "heuristic_structured_caption_extraction",
                        "confidence": 0.68,
                        "metadata": {
                            "structured_signal": caption_type,
                            "line_index": idx,
                        },
                    }
                )
            elif section_type in {"experiment", "result"} and self._looks_like_result_line(line):
                records.append(
                    {
                        "evidence_type": "result",
                        "text": self._result_context(lines, idx),
                        "supports": f"{section_title} quantitative result",
                        "source": "heuristic_result_signal_extraction",
                        "confidence": 0.66,
                        "metadata": {
                            "structured_signal": "quantitative_result",
                            "line_index": idx,
                        },
                    }
                )
            if len(records) >= 12:
                break
        return records

    def _caption_type(self, line: str) -> str:
        normalized = " ".join(line.split())
        if re.match(r"^(table)\s+[A-Za-z0-9IVXivx_.:-]+\s+.+", normalized, flags=re.I):
            return "table"
        if re.match(r"^(figure|fig\.)\s+[A-Za-z0-9IVXivx_.:-]+\s+.+", normalized, flags=re.I):
            return "figure_caption"
        return ""

    def _caption_block(self, lines: list[str], start_idx: int, max_chars: int = 900) -> str:
        block = [lines[start_idx]]
        for line in lines[start_idx + 1 : start_idx + 3]:
            if self._caption_type(line):
                break
            if self._normalize_section_heading(line).lower() in {
                "abstract",
                "introduction",
                "method",
                "methods",
                "results",
                "conclusion",
                "references",
            }:
                break
            if len(line.split()) < 4:
                break
            block.append(line)
        return " ".join(" ".join(block).split())[:max_chars]

    def _looks_like_result_line(self, line: str) -> bool:
        normalized = " ".join(line.split())
        lower = normalized.lower()
        if not any(char.isdigit() for char in normalized):
            return False
        result_markers = [
            "%",
            "accuracy",
            "auc",
            "baseline",
            "benchmark",
            "error",
            "f1",
            "improve",
            "km",
            "median",
            "metric",
            "outperform",
            "precision",
            "recall",
            "result",
            "r@",
            "top-1",
            "top1",
            "top-k",
        ]
        return any(marker in lower for marker in result_markers)

    def _result_context(self, lines: list[str], idx: int, max_chars: int = 900) -> str:
        return " ".join(lines[idx].split())[:max_chars]

    def _evidence_key(self, text: str) -> str:
        return " ".join((text or "").lower().split())[:500]

    def _create_evidence(
        self,
        *,
        paper: Paper,
        paper_node,
        graph: GraphService,
        section_row: PaperSection,
        section: dict,
        chunk_id: str,
        evidence_text: str,
        source: str,
        supports: str | None = None,
        confidence: float = 0.55,
        evidence_type: str | None = None,
        metadata: dict | None = None,
    ) -> Evidence:
        metadata_json = {"source": source}
        if metadata:
            metadata_json.update(metadata)
        evidence = Evidence(
            paper_id=paper.id,
            section_id=section_row.id,
            chunk_id=chunk_id,
            evidence_type=evidence_type
            or SECTION_TO_EVIDENCE.get(section["section_type"], "claim"),
            text=evidence_text,
            summary=evidence_text[:500],
            supports=supports or section["title"],
            confidence=confidence,
            page_number=None,
            metadata_json=metadata_json,
        )
        self.session.add(evidence)
        self.session.flush()
        evidence_node = graph.get_or_create_node(
            node_type="evidence",
            label=f"{evidence.evidence_type}: {evidence.supports}",
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
        return evidence

    def _normalize_section_heading(self, line: str) -> str:
        normalized = line.strip()
        normalized = re.sub(r"^#{1,6}\s*", "", normalized)
        normalized = re.sub(r"\s*#{1,6}$", "", normalized)
        normalized = normalized.strip(" *_`")
        normalized = re.sub(r"[-:：.]\s*$", "", normalized)
        return normalized.strip()

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
        first_match_idx = matches[0][0]
        if first_match_idx > 0:
            preamble_text = "\n".join(lines[:first_match_idx]).strip()
            if preamble_text:
                sections.append(
                    {
                        "title": "Full Text",
                        "section_type": "full_text",
                        "text": preamble_text,
                    }
                )

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

    def _pick_evidence_text(
        self,
        text: str,
        limit: int = 900,
        *,
        section_type: str = "",
        has_substantive_sections: bool = False,
    ) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if self._looks_like_review_checklist(lines):
            return ""
        if section_type == "full_text":
            lines = self._strip_full_text_metadata_lines(lines)
        lines = self._drop_leading_non_prose_lines(lines)
        cleaned = " ".join(" ".join(lines).split())
        if (
            section_type == "full_text"
            and has_substantive_sections
            and self._looks_like_metadata_preamble(cleaned)
        ):
            return ""
        if not cleaned:
            return ""
        return cleaned[:limit]

    def _strip_full_text_metadata_lines(self, lines: list[str]) -> list[str]:
        for idx, line in enumerate(lines):
            match = re.match(r"^(abstract|摘要)\s*[-:：.]*\s*(.*)$", line, flags=re.IGNORECASE)
            if match:
                first_line = match.group(2).strip()
                return ([first_line] if first_line else []) + lines[idx + 1 :]
        return lines

    def _drop_leading_non_prose_lines(self, lines: list[str]) -> list[str]:
        for idx, line in enumerate(lines):
            if self._looks_like_substantive_prose_line(line):
                return lines[idx:]
        return lines

    def _looks_like_substantive_prose_line(self, line: str) -> bool:
        normalized = " ".join(line.split())
        lower = normalized.lower()
        if lower.startswith(("figure ", "fig. ", "table ", "question:", "answer:", "guidelines:")):
            return False
        words = re.findall(r"[A-Za-z][A-Za-z-]+", normalized)
        if len(words) < 6:
            return False
        numeric_chars = sum(char.isdigit() for char in normalized)
        if numeric_chars / max(len(normalized), 1) > 0.2:
            return False
        return True

    def _looks_like_metadata_preamble(self, cleaned: str) -> bool:
        if len(cleaned) > 700:
            return False
        lower = cleaned.lower()
        if any(
            keyword in lower
            for keyword in [
                "abstract",
                "this paper",
                "we propose",
                "we present",
                "we study",
                "challenge",
                "problem",
                "evaluation",
            ]
        ):
            return False
        return True

    def _looks_like_review_checklist(self, lines: list[str]) -> bool:
        if not lines:
            return False
        joined = " ".join(lines[:12]).lower()
        return (
            joined.startswith("question: does the paper discuss")
            and "answer:" in joined
            and "guidelines:" in joined
        )
