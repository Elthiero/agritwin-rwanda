"""FastAPI app for AgriTwin Rwanda. Serves precomputed, aggregated results only."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.app.data_store import data_store
from api.app.routers import geo, yield_gap
from api.app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data on startup, nothing on shutdown."""
    data_store.load()
    yield
    data_store.clear()


def create_app() -> FastAPI:
    """Factory for the FastAPI app."""
    settings = get_settings()
    app = FastAPI(
        title="AgriTwin Rwanda",
        description="Early-season crop yield intelligence and yield-gap analysis for Rwanda",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(geo.router, prefix="/api/v1", tags=["geo"])
    app.include_router(yield_gap.router, prefix="/api/v1", tags=["yield-gap"])
    return app


app = create_app()


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "data_version": "2026.10.0",
    }
