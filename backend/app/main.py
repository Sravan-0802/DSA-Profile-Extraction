"""FastAPI application entrypoint.

Serves the API under /api. When frontend/dist exists (production / Replit),
also serves the built React SPA from the same process so only one port is needed.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

settings = get_settings()

# backend/app/main.py → repo root is parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[2]
_FRONTEND_DIST = _REPO_ROOT / "frontend" / "dist"

app = FastAPI(title="DSA Profile Extraction", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


def _mount_spa() -> None:
    """Serve Vite build from the same origin as the API (single-port deploy)."""
    if not _FRONTEND_DIST.is_dir():
        logging.info("No frontend/dist found — API-only mode (local backend).")
        return

    from fastapi import HTTPException

    assets = _FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index = _FRONTEND_DIST / "index.html"

    @app.get("/")
    def spa_index() -> FileResponse:
        return FileResponse(index)

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str) -> FileResponse:
        # API / docs are registered above; anything else under those prefixes is 404.
        if full_path.startswith(("api/", "api")) or full_path.split("/", 1)[0] in {
            "docs",
            "openapi.json",
            "redoc",
        }:
            raise HTTPException(status_code=404, detail="Not found")
        candidate = _FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    logging.info("Serving frontend from %s", _FRONTEND_DIST)


_mount_spa()
