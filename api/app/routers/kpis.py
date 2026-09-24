"""National KPI cards endpoint."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from api.app.data_store import data_store
from api.app.schemas import Crop, KpiRow, Season
from api.app.settings import get_settings

router = APIRouter()


@router.get("/kpis", response_model=list[KpiRow])
def get_kpis(
    year: Annotated[int, Query(description="Survey year, e.g. 2024")],
    season: Annotated[Season, Query(description="A or B")],
) -> JSONResponse:
    """National-level yield estimate for every MVP crop, for one season x year, from
    src/agritwin/survey/'s national geo_level rows. One row per crop with its own CI and
    reliability, not a single blended national number."""
    if data_store.district_yield is None:
        return JSONResponse(status_code=200, content=[])

    mvp_crops = {c.value for c in Crop}
    df = data_store.district_yield
    rows = df[
        (df["geo_level"] == "national")
        & (df["season"] == season.value)
        & (df["year"] == year)
        & (df["crop"].isin(mvp_crops))
    ]

    records: list[dict[str, Any]] = rows.to_dict("records")  # type: ignore[assignment]
    payload = [
        KpiRow(
            crop=record["crop"],
            season=record["season"],
            year=int(record["year"]),
            yield_kg_ha=record["yield_kg_ha"],
            yield_kg_ha_ci_low=record.get("yield_kg_ha_ci_low"),
            yield_kg_ha_ci_high=record.get("yield_kg_ha_ci_high"),
            n_plots=int(record["n_plots"]),
            reliability=record["reliability"],
        ).model_dump(mode="json")
        for record in records
    ]

    cache_seconds = get_settings().CACHE_SECONDS
    return JSONResponse(
        content=payload, headers={"Cache-Control": f"public, max-age={cache_seconds}"}
    )
