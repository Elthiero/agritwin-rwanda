"""Nowcast backtest endpoint."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from api.app.data_store import data_store
from api.app.schemas import BacktestRow, Crop, Season
from api.app.settings import get_settings

router = APIRouter()


@router.get("/backtest", response_model=list[BacktestRow])
def get_backtest(
    crop: Annotated[Crop, Query(description="MVP crop")],
    season: Annotated[
        Season, Query(description="A or B. Currently has no effect: see BacktestRow docstring")
    ],
) -> JSONResponse:
    """Nowcast leave-one-year-out backtest metrics (MAPE, its spread across the held-out
    years, and MAE in kg/ha) for every model and lead time, for one crop. See
    docs/decisions.md 2026-09-24 for the honest verdict on what these numbers mean.
    """
    if data_store.backtest is None:
        return JSONResponse(status_code=200, content=[])

    rows = data_store.backtest[data_store.backtest["crop"] == crop.value]
    records: list[dict[str, Any]] = rows.to_dict("records")  # type: ignore[assignment]
    payload = [BacktestRow(**record).model_dump(mode="json") for record in records]

    cache_seconds = get_settings().CACHE_SECONDS
    return JSONResponse(
        content=payload, headers={"Cache-Control": f"public, max-age={cache_seconds}"}
    )
