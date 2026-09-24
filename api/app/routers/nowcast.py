"""Nowcast (early yield estimate) endpoints."""

from __future__ import annotations

from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from api.app.data_store import data_store
from api.app.schemas import Crop, NowcastCurveRow, NowcastRow, Season
from api.app.settings import get_settings

router = APIRouter()


@router.get("/nowcast", response_model=list[NowcastRow])
def get_nowcast(
    crop: Annotated[Crop, Query(description="MVP crop")],
    season: Annotated[Season, Query(description="A or B")],
    year: Annotated[int, Query(description="Season year, e.g. 2024")],
    lead: Annotated[
        int, Query(description="Lead months into the season: 2, 3 or 4")
    ] = 3,
) -> JSONResponse:
    """Early yield estimate for every district, for one crop x season x year x lead
    time. Empty list if that combination has no backtest coverage (see NowcastRow
    docstring: served rows are historical leave-one-year-out predictions, not live
    in-season forecasts).
    """
    if data_store.nowcast is None:
        return JSONResponse(status_code=200, content=[])

    rows = data_store.nowcast[
        (data_store.nowcast["crop"] == crop.value)
        & (data_store.nowcast["season"] == season.value)
        & (data_store.nowcast["year"] == year)
        & (data_store.nowcast["lead_months"] == lead)
    ]
    records: list[dict[str, Any]] = rows.to_dict("records")  # type: ignore[assignment]
    # actual_yield_kg_ha is genuinely absent for a not-yet-surveyed year, not a data
    # gap: pandas reads that as NaN (a float column can't hold None), which the JSON
    # encoder rejects, so it is converted to a real null here.
    for record in records:
        if pd.isna(record["actual_yield_kg_ha"]):
            record["actual_yield_kg_ha"] = None
    payload = [NowcastRow(**record).model_dump(mode="json") for record in records]

    cache_seconds = get_settings().CACHE_SECONDS
    return JSONResponse(
        content=payload, headers={"Cache-Control": f"public, max-age={cache_seconds}"}
    )


@router.get("/nowcast/{code}/curve", response_model=list[NowcastCurveRow])
def get_nowcast_curve(
    code: int,
    season: Annotated[Season, Query(description="A or B")],
    year: Annotated[int, Query(description="Season year, e.g. 2024")],
) -> JSONResponse:
    """NDVI and rainfall curve (one point per lead time) vs climatology, for one
    district x season x year. Not crop-specific. 404 for an unknown district code.
    """
    if data_store.district_name(code) is None:
        raise HTTPException(status_code=404, detail=f"Unknown district code: {code}")
    if data_store.nowcast_curve is None:
        return JSONResponse(status_code=200, content=[])

    rows = data_store.nowcast_curve[
        (data_store.nowcast_curve["district_code"] == code)
        & (data_store.nowcast_curve["season"] == season.value)
        & (data_store.nowcast_curve["year"] == year)
    ]
    records: list[dict[str, Any]] = rows.to_dict("records")  # type: ignore[assignment]
    payload = [NowcastCurveRow(**record).model_dump(mode="json") for record in records]

    cache_seconds = get_settings().CACHE_SECONDS
    return JSONResponse(
        content=payload, headers={"Cache-Control": f"public, max-age={cache_seconds}"}
    )
