from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.research.db import init_db
from backend.research.routes import router as research_router


STATIC_DIR = Path(__file__).resolve().parent / "static"
WORKBENCH_DIR = STATIC_DIR / "workbench"
WORKBENCH_INDEX = WORKBENCH_DIR / "index.html"


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

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "research-assistant-agent"}

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
