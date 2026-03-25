from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Iterable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bookkeeping_tool.web.api import create_api_router


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT.parents[1]


def _candidate_frontend_dirs() -> Iterable[object]:
    yield resources.files("bookkeeping_tool.web.static")
    yield SOURCE_ROOT / "frontend" / "dist"


def resolve_frontend_dist() -> object | None:
    for candidate in _candidate_frontend_dirs():
        if candidate.joinpath("index.html").exists():
            return candidate
    return None


def create_app(project_root: str | Path) -> FastAPI:
    project_root = Path(project_root)
    frontend_dist = resolve_frontend_dist()

    app = FastAPI(title="Bookkeeping Dashboard")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_api_router(project_root))

    if frontend_dist is not None:
        assets_dir = frontend_dist.joinpath("assets")
        favicon_path = frontend_dist.joinpath("favicon.svg")

        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        if favicon_path.exists():
            @app.get("/favicon.svg", include_in_schema=False)
            def favicon() -> FileResponse:
                return FileResponse(favicon_path)

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(frontend_dist.joinpath("index.html"))

    return app
