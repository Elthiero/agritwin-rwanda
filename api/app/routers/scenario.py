"""Scenario explorer endpoint: precomputed lever grid."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from api.app.data_store import data_store
from api.app.schemas import Crop, ScenarioRow, Season
from api.app.settings import get_settings

router = APIRouter()


@router.get("/scenario/{code}", response_model=list[ScenarioRow])
def get_scenario(
    code: int,
    crop: Annotated[Crop, Query(description="MVP crop")],
    season: Annotated[
        Season, Query(description="A or B. Currently has no effect: see ScenarioRow docstring")
    ],
) -> JSONResponse:
    """The 16 lever-configuration means and bootstrap intervals for one district x crop,
    per src/agritwin/models/scenario.py. Always model-based, not causal (CLAUDE.md rule
    5)."""
    if data_store.district_name(code) is None:
        raise HTTPException(status_code=404, detail=f"Unknown district_code {code}")

    if data_store.scenario is None:
        return JSONResponse(status_code=200, content=[])

    df = data_store.scenario
    rows = df[(df["district_code"] == float(code)) & (df["crop"] == crop.value)]

    records: list[dict[str, Any]] = rows.to_dict("records")  # type: ignore[assignment]
    payload = [
        ScenarioRow(**{**record, "district_code": code}).model_dump(mode="json")
        for record in records
    ]

    cache_seconds = get_settings().CACHE_SECONDS
    return JSONResponse(
        content=payload, headers={"Cache-Control": f"public, max-age={cache_seconds}"}
    )
