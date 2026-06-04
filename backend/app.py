from contextlib import asynccontextmanager
import os
from pathlib import Path
import secrets

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.research.config import settings
from backend.research.db import engine, init_db
from backend.research.routes import router as research_router


STATIC_DIR = Path(__file__).resolve().parent / "static"
WORKBENCH_DIR = STATIC_DIR / "workbench"
WORKBENCH_INDEX = WORKBENCH_DIR / "index.html"
PROTECTED_PATH_PREFIXES = ("/research",)


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
    async def api_key_guard(request: Request, call_next):
        if request.method == "OPTIONS" or not _requires_api_key(request.url.path):
            return await call_next(request)
        configured_key = _configured_api_key()
        if not configured_key:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "API key auth is enabled but API_KEY or RESEARCH_ASSISTANT_API_KEY "
                        "is not configured."
                    )
                },
            )
        supplied_key = _request_api_key(request)
        if not supplied_key or not secrets.compare_digest(supplied_key, configured_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Valid API key required."},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "research-assistant-agent"}

    @app.get("/health/ready")
    def readiness():
        checks = {
            "database": _database_ready(),
            "paper_upload_dir": _paper_upload_dir_ready(),
        }
        ready = all(item["ok"] for item in checks.values())
        payload = {
            "status": "ready" if ready else "not_ready",
            "service": "research-assistant-agent",
            "environment": settings.app_env,
            "checks": checks,
        }
        if ready:
            return payload
        return JSONResponse(status_code=503, content=payload)

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


app = create_app()


def _requires_api_key(path: str) -> bool:
    if not _api_key_auth_enabled():
        return False
    return any(
        path == prefix or path.startswith(f"{prefix}/") for prefix in PROTECTED_PATH_PREFIXES
    )


def _api_key_auth_enabled() -> bool:
    raw = os.getenv("API_KEY_AUTH_ENABLED")
    if raw is None:
        return settings.api_key_auth_enabled
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _configured_api_key() -> str:
    return os.getenv("API_KEY") or os.getenv("RESEARCH_ASSISTANT_API_KEY") or settings.api_key


def _api_key_header_name() -> str:
    return os.getenv("API_KEY_HEADER_NAME") or settings.api_key_header_name


def _request_api_key(request: Request) -> str:
    header_key = request.headers.get(_api_key_header_name(), "")
    if header_key:
        return header_key.strip()
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def _database_ready() -> dict:
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


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
