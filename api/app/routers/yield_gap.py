"""District yield gap endpoint."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from api.app.data_store import data_store
from api.app.schemas import Crop, Season, YieldGapRow
from api.app.settings import get_settings

router = APIRouter()


@router.get("/yield-gap", response_model=list[YieldGapRow])
def get_yield_gap(
    crop: Annotated[Crop, Query(description="MVP crop")],
    season: Annotated[Season, Query(description="A or B")],
    year: Annotated[int, Query(description="Survey year, e.g. 2024")],
) -> JSONResponse:
    """Per-district actual vs. attainable yield and the gap between them, for one
    crop x season x year. Returns every district with data for that combination,
    including "suppressed" (low-reliability) rows, per CLAUDE.md golden rule 6: the
    frontend greys those out, this endpoint does not hide them.
    """
    if data_store.yield_gap is None:
        return JSONResponse(status_code=200, content=[])

    df = data_store.yield_gap
    rows = df[(df["crop"] == crop.value) & (df["season"] == season.value) & (df["year"] == year)]

    records: list[dict[str, Any]] = rows.to_dict("records")  # type: ignore[assignment]
    payload = [YieldGapRow(**record).model_dump(mode="json") for record in records]

    cache_seconds = get_settings().CACHE_SECONDS
    return JSONResponse(
        content=payload, headers={"Cache-Control": f"public, max-age={cache_seconds}"}
    )
