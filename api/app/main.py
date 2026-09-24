"""FastAPI app for AgriTwin Rwanda. Serves precomputed, aggregated results only."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.app.data_store import DATA_VERSION, data_store
from api.app.routers import (
    backtest,
    briefs,
    districts,
    drivers,
    geo,
    kpis,
    meta,
    scenario,
    yield_gap,
)
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
    app.include_router(drivers.router, prefix="/api/v1", tags=["drivers"])
    app.include_router(backtest.router, prefix="/api/v1", tags=["backtest"])
    app.include_router(meta.router, prefix="/api/v1", tags=["meta"])
    app.include_router(kpis.router, prefix="/api/v1", tags=["kpis"])
    app.include_router(districts.router, prefix="/api/v1", tags=["districts"])
    app.include_router(scenario.router, prefix="/api/v1", tags=["scenario"])
    app.include_router(briefs.router, prefix="/api/v1", tags=["briefs"])
    return app


app = create_app()


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "data_version": DATA_VERSION,
    }
