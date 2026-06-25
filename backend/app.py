from contextlib import asynccontextmanager
import hashlib
import logging
import os
from pathlib import Path
import secrets
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.engine import make_url

from backend.research.config import settings
from backend.research.db import engine, init_db
from backend.research.routes import router as research_router
from backend.research.schemas import WriteAuditSummaryResponse
from backend.research.services.benchmark_runner_service import benchmark_profile_summary
from backend.research.services.write_audit_service import (
    append_write_audit_event,
    entity_type_for_path,
    export_write_audit_events,
    is_write_operation,
    operation_for_request,
    render_write_audit_export_jsonl,
    summarize_write_audit_events,
    write_audit_dir,
    write_audit_enabled,
)


STATIC_DIR = Path(__file__).resolve().parent / "static"
WORKBENCH_DIR = STATIC_DIR / "workbench"
WORKBENCH_INDEX = WORKBENCH_DIR / "index.html"
PROTECTED_PATH_PREFIXES = ("/research",)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Research Assistant Agent API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_header(request: Request, call_next):
        _request_id_for(request)
        response = await call_next(request)
        return _attach_request_id_header(request, response)

    @app.middleware("http")
    async def api_key_guard(request: Request, call_next):
        if request.method == "OPTIONS" or not _requires_api_key(request.url.path):
            return await call_next(request)
        configured_key = _configured_api_key()
        if not configured_key:
            return _attach_request_id_header(
                request,
                JSONResponse(
                    status_code=503,
                    content={
                        "detail": (
                            "API key auth is enabled but API_KEY or RESEARCH_ASSISTANT_API_KEY "
                            "is not configured."
                        )
                    },
                ),
            )
        supplied_key = _request_api_key(request)
        if supplied_key:
            request.state.api_key_fingerprint = _secret_fingerprint(supplied_key)
        if not supplied_key or not secrets.compare_digest(supplied_key, configured_key):
            return _attach_request_id_header(
                request,
                JSONResponse(
                    status_code=401,
                    content={"detail": "Valid API key required."},
                    headers={"WWW-Authenticate": "Bearer"},
                ),
            )
        return await call_next(request)

    @app.middleware("http")
    async def write_operation_audit(request: Request, call_next):
        if not write_audit_enabled() or not is_write_operation(request.method, request.url.path):
            return await call_next(request)

        request_id = _request_id_for(request)
        request.state.audit_context = {}
        started_at = time.perf_counter()
        response = None
        error_type = None
        try:
            response = await call_next(request)
            return _attach_request_id_header(request, response)
        except Exception as exc:
            error_type = exc.__class__.__name__
            raise
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            route = request.scope.get("route")
            path_template = getattr(route, "path", request.url.path)
            status_code = getattr(response, "status_code", 500)
            metadata = {
                "query_keys": sorted(request.query_params.keys()),
            }
            api_key_fingerprint = getattr(request.state, "api_key_fingerprint", "")
            if api_key_fingerprint:
                metadata["api_key_fingerprint"] = api_key_fingerprint
            event = {
                "request_id": request_id,
                "actor_type": _audit_actor_type(request),
                "actor_label": _audit_actor_label(request),
                "method": request.method.upper(),
                "path_template": path_template,
                "tool_name": request.headers.get("X-Research-Assistant-Tool") or None,
                "operation": operation_for_request(request.method, path_template),
                "entity_type": entity_type_for_path(path_template),
                "status": "success" if status_code < 400 and error_type is None else "failure",
                "http_status": status_code,
                "error_type": error_type,
                "policy": request.headers.get("X-Research-Assistant-Policy") or "direct_api",
                "duration_ms": duration_ms,
                "commit_sha": os.getenv("APP_COMMIT_SHA") or os.getenv("GIT_COMMIT_SHA") or None,
                "metadata": metadata,
            }
            audit_context = getattr(request.state, "audit_context", {}) or {}
            event.update({key: audit_context.get(key) for key in ("entity_id",)})
            try:
                append_write_audit_event(event)
            except Exception:
                logger.exception("Failed to append write-operation audit event")

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "service": "research-assistant-agent",
            "build": _build_metadata(),
        }

    @app.get("/health/ready")
    def readiness():
        checks = {
            "database": _database_ready(),
            "database_storage": _database_storage_ready(),
            "api_key_auth": _api_key_auth_ready(),
            "request_id_header": _request_id_header_ready(),
            "workbench_assets": _workbench_assets_ready(),
            "model_provider_configuration": _model_provider_configuration_ready(),
            "benchmark_command_runner": _benchmark_command_runner_ready(),
            "paper_upload_dir": _paper_upload_dir_ready(),
            "write_audit_dir": _write_audit_dir_ready(),
            "external_literature_search": _external_literature_search_ready(),
        }
        ready = all(item["ok"] for item in checks.values())
        payload = {
            "status": "ready" if ready else "not_ready",
            "service": "research-assistant-agent",
            "environment": settings.app_env,
            "build": _build_metadata(),
            "checks": checks,
        }
        if ready:
            return payload
        return JSONResponse(status_code=503, content=payload)

    if _audit_admin_export_enabled():

        @app.get("/research/admin/write-audit/summary", response_model=WriteAuditSummaryResponse)
        def write_audit_summary(
            _admin_key_fingerprint: str = Depends(_require_audit_admin_access),
        ) -> WriteAuditSummaryResponse:
            return WriteAuditSummaryResponse(**summarize_write_audit_events())

        @app.get("/research/admin/write-audit/export")
        def write_audit_export(
            _admin_key_fingerprint: str = Depends(_require_audit_admin_access),
            max_records: int = Query(default=100, ge=1, le=1000),
            start_created_at: str = Query(default="", max_length=80),
            end_created_at: str = Query(default="", max_length=80),
        ) -> PlainTextResponse:
            records = export_write_audit_events(
                max_records=max_records,
                start_created_at=start_created_at,
                end_created_at=end_created_at,
            )
            return PlainTextResponse(
                content=render_write_audit_export_jsonl(records),
                media_type="application/x-ndjson",
                headers={"X-Research-Assistant-Export-Records": str(len(records))},
            )

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/workbench")

    @app.get("/workbench", include_in_schema=False)
    def workbench():
        return FileResponse(WORKBENCH_INDEX)

    app.mount(
        "/workbench-assets",
        StaticFiles(directory=WORKBENCH_DIR),
        name="workbench-assets",
    )

    app.include_router(research_router)
    return app


def _build_metadata() -> dict:
    commit_sha = os.getenv("APP_COMMIT_SHA") or os.getenv("GIT_COMMIT_SHA") or "unknown"
    return {"commit_sha": commit_sha}


def _requires_api_key(path: str) -> bool:
    if not _api_key_auth_enabled():
        return False
    return any(
        path == prefix or path.startswith(f"{prefix}/") for prefix in PROTECTED_PATH_PREFIXES
    )


def _api_key_auth_ready() -> dict:
    enabled = _api_key_auth_enabled()
    configured = bool(_configured_api_key())
    payload = {
        "ok": not enabled or configured,
        "enabled": enabled,
        "configured": configured,
        "header": _api_key_header_name(),
    }
    if enabled and not configured:
        payload["error"] = "API key auth is enabled but no API key is configured."
    return payload


def _api_key_auth_enabled() -> bool:
    raw = os.getenv("API_KEY_AUTH_ENABLED")
    if raw is None:
        return settings.api_key_auth_enabled
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _configured_api_key() -> str:
    return os.getenv("API_KEY") or os.getenv("RESEARCH_ASSISTANT_API_KEY") or settings.api_key


def _api_key_header_name() -> str:
    return os.getenv("API_KEY_HEADER_NAME") or settings.api_key_header_name


def _request_id_header_name() -> str:
    configured_header = os.getenv("REQUEST_ID_HEADER_NAME") or settings.request_id_header_name
    return configured_header.strip() or "X-Request-ID"


def _request_id_header_ready() -> dict:
    header = _request_id_header_name()
    return {"ok": bool(header), "header": header}


def _request_id_for(request: Request) -> str:
    request_id = getattr(request.state, "request_id", "")
    if not request_id:
        request_id = request.headers.get(_request_id_header_name()) or uuid.uuid4().hex
        request.state.request_id = request_id
    return request_id


def _attach_request_id_header(request: Request, response):
    request_id_header = _request_id_header_name()
    if request_id_header not in response.headers:
        response.headers[request_id_header] = _request_id_for(request)
    return response


def _write_audit_client_header_name() -> str:
    return os.getenv("WRITE_AUDIT_CLIENT_HEADER_NAME") or settings.write_audit_client_header_name


def _audit_admin_export_enabled() -> bool:
    raw = os.getenv("AUDIT_ADMIN_EXPORT_ENABLED")
    if raw is None:
        return settings.audit_admin_export_enabled
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _configured_audit_admin_key() -> str:
    return os.getenv("AUDIT_ADMIN_KEY") or settings.audit_admin_key


def _audit_admin_key_header_name() -> str:
    return os.getenv("AUDIT_ADMIN_KEY_HEADER_NAME") or settings.audit_admin_key_header_name


def _request_audit_admin_key(request: Request) -> str:
    return request.headers.get(_audit_admin_key_header_name(), "").strip()


def _require_audit_admin_access(request: Request) -> str:
    configured_key = _configured_audit_admin_key()
    if not configured_key:
        raise HTTPException(
            status_code=503,
            detail="Audit admin export is enabled but AUDIT_ADMIN_KEY is not configured.",
        )
    supplied_key = _request_audit_admin_key(request)
    if not supplied_key:
        raise HTTPException(
            status_code=401,
            detail="Audit admin key required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not secrets.compare_digest(supplied_key, configured_key):
        raise HTTPException(status_code=403, detail="Valid audit admin key required.")
    return _secret_fingerprint(supplied_key)


def _audit_actor_label(request: Request) -> str:
    return request.headers.get(_write_audit_client_header_name(), "").strip()


def _audit_actor_type(request: Request) -> str:
    label = _audit_actor_label(request).lower()
    if "workbench" in label:
        return "workbench"
    if "mcp" in label:
        return "mcp_bridge"
    if label:
        return "api_client"
    return "unknown"


def _secret_fingerprint(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}"


def _request_api_key(request: Request) -> str:
    header_key = request.headers.get(_api_key_header_name(), "")
    if header_key:
        return header_key.strip()
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def _model_provider_configuration_ready() -> dict:
    roles = {
        "main": _model_provider_role_status(
            settings.main_model,
            settings.main_base_url,
            settings.main_api_key,
        ),
        "extraction": _model_provider_role_status(
            settings.extraction_model,
            settings.extraction_base_url,
            settings.extraction_api_key,
        ),
        "judge": _model_provider_role_status(
            settings.judge_model,
            settings.judge_base_url,
            settings.judge_api_key,
        ),
        "embedding": _model_provider_role_status(
            settings.embedder,
            settings.embedder_base_url,
            settings.embedder_api_key,
        ),
        "rerank": _model_provider_role_status(
            settings.rerank_model,
            settings.rerank_binding_host,
            settings.rerank_api_key,
        ),
    }
    return {
        "ok": True,
        "fallback_supported": True,
        "roles": roles,
        "retrieval_provider_modes": {
            "embedding": settings.retrieval_embedding_provider,
            "rerank": settings.retrieval_rerank_provider,
        },
        "partial_roles": [name for name, status in roles.items() if status["partially_configured"]],
    }


def _model_provider_role_status(model: str, base_url: str, api_key: str) -> dict:
    configured = bool(model and base_url and api_key)
    partially_configured = bool(model or base_url or api_key) and not configured
    return {
        "configured": configured,
        "mode": "external_model" if configured else "deterministic_fallback",
        "model_configured": bool(model),
        "base_url_configured": bool(base_url),
        "api_key_configured": bool(api_key),
        "partially_configured": partially_configured,
    }


def _benchmark_command_runner_ready() -> dict:
    enabled = _benchmark_runner_enabled()
    output_dir = _benchmark_runner_output_dir()
    allowed_commands = _benchmark_runner_allowed_commands()
    profile_summary = benchmark_profile_summary()
    ok = (not enabled or (bool(output_dir) and bool(allowed_commands))) and profile_summary["ok"]
    payload = {
        "ok": ok,
        "enabled": enabled,
        "output_dir": output_dir,
        "allowed_commands": allowed_commands,
        "timeout_seconds": _benchmark_runner_timeout_seconds(),
        "max_output_chars": _benchmark_runner_max_output_chars(),
        "profiles": profile_summary,
        "shell": False,
    }
    if enabled and not allowed_commands:
        payload["error"] = "Benchmark runner is enabled but no allowed commands are configured."
    return payload


def _benchmark_runner_enabled() -> bool:
    raw = os.getenv("BENCHMARK_RUNNER_ENABLED")
    if raw is None:
        return settings.benchmark_runner_enabled
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _benchmark_runner_output_dir() -> str:
    return os.getenv("BENCHMARK_RUNNER_OUTPUT_DIR") or settings.benchmark_runner_output_dir


def _benchmark_runner_allowed_commands() -> list[str]:
    raw = os.getenv("BENCHMARK_RUNNER_ALLOWED_COMMANDS")
    configured = raw if raw is not None else settings.benchmark_runner_allowed_commands
    return [item.strip() for item in configured.split(",") if item.strip()]


def _benchmark_runner_timeout_seconds() -> int:
    raw = os.getenv("BENCHMARK_RUNNER_TIMEOUT_SECONDS")
    if raw:
        return int(raw)
    return settings.benchmark_runner_timeout_seconds


def _benchmark_runner_max_output_chars() -> int:
    raw = os.getenv("BENCHMARK_RUNNER_MAX_OUTPUT_CHARS")
    if raw:
        return int(raw)
    return settings.benchmark_runner_max_output_chars


def _external_literature_search_ready() -> dict:
    enabled = _external_literature_search_enabled()
    providers, invalid_providers = _external_literature_providers()
    if not enabled:
        return {
            "ok": True,
            "enabled": False,
            "providers": providers,
            "invalid_providers": invalid_providers,
        }

    base_urls_configured = {
        provider: bool(_external_literature_provider_base_url(provider)) for provider in providers
    }
    missing_base_url_providers = [
        provider for provider, configured in base_urls_configured.items() if not configured
    ]
    ok = bool(providers) and not invalid_providers and not missing_base_url_providers
    payload = {
        "ok": ok,
        "enabled": True,
        "providers": providers,
        "invalid_providers": invalid_providers,
        "base_urls_configured": base_urls_configured,
    }
    if "semantic_scholar" in providers:
        payload["semantic_scholar_api_key_configured"] = _semantic_scholar_api_key_configured()
    if not providers:
        payload["error"] = (
            "External literature search is enabled but no supported providers are configured."
        )
    if missing_base_url_providers:
        payload["missing_base_url_providers"] = missing_base_url_providers
    return payload


def _external_literature_search_enabled() -> bool:
    raw = os.getenv("EXTERNAL_LITERATURE_SEARCH_ENABLED")
    if raw is None:
        return settings.external_literature_search_enabled
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _external_literature_providers() -> tuple[list[str], list[str]]:
    raw = os.getenv("EXTERNAL_LITERATURE_PROVIDERS")
    if raw is None:
        raw = settings.external_literature_providers
    providers = []
    invalid_providers = []
    for provider in raw.split(","):
        normalized = provider.strip().lower()
        if not normalized:
            continue
        if normalized in {"semantic-scholar", "semanticscholar"}:
            normalized = "semantic_scholar"
        if normalized in {"openalex", "arxiv", "semantic_scholar"}:
            if normalized not in providers:
                providers.append(normalized)
        elif normalized not in invalid_providers:
            invalid_providers.append(normalized)
    return providers, invalid_providers


def _semantic_scholar_api_key_configured() -> bool:
    if "SEMANTIC_SCHOLAR_API_KEY" in os.environ:
        return bool(os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip())
    return bool(settings.semantic_scholar_api_key.strip())


def _external_literature_provider_base_url(provider: str) -> str:
    env_names = {
        "openalex": "OPENALEX_BASE_URL",
        "arxiv": "ARXIV_BASE_URL",
        "semantic_scholar": "SEMANTIC_SCHOLAR_BASE_URL",
    }
    settings_values = {
        "openalex": settings.openalex_base_url,
        "arxiv": settings.arxiv_base_url,
        "semantic_scholar": settings.semantic_scholar_base_url,
    }
    env_name = env_names[provider]
    if env_name in os.environ:
        return os.environ.get(env_name, "").strip()
    return settings_values[provider].strip()


def _database_ready() -> dict:
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _workbench_assets_ready() -> dict:
    required_files = [
        WORKBENCH_INDEX,
        WORKBENCH_DIR / "app.js",
        WORKBENCH_DIR / "styles.css",
    ]
    missing_files = [path.name for path in required_files if not path.is_file()]
    return {
        "ok": not missing_files,
        "path": str(WORKBENCH_DIR),
        "required_files": [path.name for path in required_files],
        "missing_files": missing_files,
    }


def _database_storage_ready() -> dict:
    raw_database_url = os.getenv("RESEARCH_DB_URL") or settings.research_db_url
    try:
        database_url = make_url(raw_database_url)
    except Exception as exc:
        return {"ok": False, "database_type": "unknown", "error": str(exc)}

    database_type = database_url.get_backend_name()
    if database_type != "sqlite":
        return {
            "ok": True,
            "database_type": database_type,
            "managed_by_app": False,
        }

    database_path = database_url.database or ":memory:"
    if database_path == ":memory:":
        return {
            "ok": True,
            "database_type": "sqlite",
            "path": database_path,
            "persistent": False,
        }

    db_path = Path(database_path)
    parent = db_path.parent if str(db_path.parent) else Path(".")
    return {
        "ok": parent.is_dir() and os.access(parent, os.W_OK),
        "database_type": "sqlite",
        "path": str(db_path),
        "parent": str(parent),
        "persistent": True,
    }


def _paper_upload_dir_ready() -> dict:
    try:
        upload_dir = Path(settings.paper_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        return {
            "ok": upload_dir.is_dir() and os.access(upload_dir, os.W_OK),
            "path": str(upload_dir),
        }
    except Exception as exc:
        return {"ok": False, "path": settings.paper_upload_dir, "error": str(exc)}


def _write_audit_dir_ready() -> dict:
    if not write_audit_enabled():
        return {"ok": True, "enabled": False, "path": str(write_audit_dir())}
    try:
        audit_dir = write_audit_dir()
        audit_dir.mkdir(parents=True, exist_ok=True)
        return {
            "ok": audit_dir.is_dir() and os.access(audit_dir, os.W_OK),
            "enabled": True,
            "path": str(audit_dir),
        }
    except Exception as exc:
        return {"ok": False, "enabled": True, "path": str(write_audit_dir()), "error": str(exc)}


app = create_app()
