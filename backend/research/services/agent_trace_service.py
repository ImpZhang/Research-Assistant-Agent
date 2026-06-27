import re
from typing import Any

from sqlalchemy.orm import Session

from backend.research.models import AgentRun, ReplayCase, ToolCallRecord, utc_now
from backend.research.schemas import AgentRunCreate, ReplayCaseCreate, ToolCallRecordCreate


SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
)
SECRET_VALUE_PATTERN = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})")
MAX_TRACE_TEXT_LENGTH = 4000


class AgentTraceService:
    def __init__(self, session: Session):
        self.session = session

    def create_run(self, payload: AgentRunCreate) -> AgentRun:
        run = AgentRun(
            run_type=payload.run_type,
            status=payload.status,
            question=_redact_text(payload.question),
            input_json=_redact_json(payload.input),
            output_json=_redact_json(payload.output),
            error=_redact_text(payload.error),
            model_name=payload.model_name,
            latency_ms=max(0, payload.latency_ms),
            token_usage_json=_redact_json(payload.token_usage),
            metadata_json=_redact_json(payload.metadata),
            created_by=payload.created_by,
            finished_at=utc_now()
            if payload.status in {"completed", "failed", "canceled"}
            else None,
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def list_runs(
        self,
        limit: int = 50,
        run_type: str | None = None,
        status: str | None = None,
    ) -> list[AgentRun]:
        query = self.session.query(AgentRun).order_by(AgentRun.created_at.desc())
        if run_type:
            query = query.filter(AgentRun.run_type == run_type)
        if status:
            query = query.filter(AgentRun.status == status)
        return query.limit(_bounded_limit(limit)).all()

    def get_run(self, run_id: str) -> AgentRun | None:
        return self.session.get(AgentRun, run_id)

    def create_tool_call(self, agent_run_id: str, payload: ToolCallRecordCreate) -> ToolCallRecord:
        run = self.get_run(agent_run_id)
        if run is None:
            raise ValueError("Agent run not found")
        record = ToolCallRecord(
            agent_run_id=agent_run_id,
            tool_name=payload.tool_name,
            tool_arguments_json=_redact_json(payload.tool_arguments),
            tool_result_summary=_redact_text(payload.tool_result_summary),
            status=payload.status,
            error=_redact_text(payload.error),
            latency_ms=max(0, payload.latency_ms),
            side_effect=payload.side_effect,
            metadata_json=_redact_json(payload.metadata),
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def list_tool_calls(self, agent_run_id: str, limit: int = 100) -> list[ToolCallRecord]:
        return (
            self.session.query(ToolCallRecord)
            .filter(ToolCallRecord.agent_run_id == agent_run_id)
            .order_by(ToolCallRecord.created_at.asc())
            .limit(_bounded_limit(limit, maximum=500))
            .all()
        )

    def create_replay_case(self, payload: ReplayCaseCreate) -> ReplayCase:
        if payload.source_agent_run_id and self.get_run(payload.source_agent_run_id) is None:
            raise ValueError("Source agent run not found")
        replay_case = ReplayCase(
            source_agent_run_id=payload.source_agent_run_id,
            case_type=payload.case_type,
            query=_redact_text(payload.query),
            expected_json=_redact_json(payload.expected),
            observed_json=_redact_json(payload.observed),
            verdict=payload.verdict,
            notes=_redact_text(payload.notes),
            metadata_json=_redact_json(payload.metadata),
        )
        self.session.add(replay_case)
        self.session.commit()
        self.session.refresh(replay_case)
        return replay_case

    def list_replay_cases(
        self,
        limit: int = 50,
        case_type: str | None = None,
        verdict: str | None = None,
    ) -> list[ReplayCase]:
        query = self.session.query(ReplayCase).order_by(ReplayCase.created_at.desc())
        if case_type:
            query = query.filter(ReplayCase.case_type == case_type)
        if verdict:
            query = query.filter(ReplayCase.verdict == verdict)
        return query.limit(_bounded_limit(limit)).all()

    def get_replay_case(self, case_id: str) -> ReplayCase | None:
        return self.session.get(ReplayCase, case_id)


def _bounded_limit(limit: int, maximum: int = 200) -> int:
    return max(1, min(limit, maximum))


def _redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if _sensitive_key(str(key)):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _redact_json(item)
        return redacted
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _redact_text(value: str) -> str:
    redacted = SECRET_VALUE_PATTERN.sub("[redacted]", value or "")
    if len(redacted) > MAX_TRACE_TEXT_LENGTH:
        return redacted[:MAX_TRACE_TEXT_LENGTH] + "...[truncated]"
    return redacted


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)
