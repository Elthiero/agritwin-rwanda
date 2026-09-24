"""Driver model (SHAP) endpoint."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from api.app.data_store import data_store
from api.app.schemas import Crop, DriverRow, Season
from api.app.settings import get_settings

router = APIRouter()


@router.get("/drivers", response_model=list[DriverRow])
def get_drivers(
    crop: Annotated[Crop, Query(description="MVP crop")],
    season: Annotated[
        Season, Query(description="A or B. Currently has no effect: see DriverRow docstring")
    ],
    district: Annotated[
        int | None,
        Query(description="NISR district_code; omit for the global (all-districts) summary"),
    ] = None,
) -> JSONResponse:
    """SHAP-based driver ranking for one crop, either global or for one district.
    Includes "suppressed" district rows (too few plots), not hidden, per golden rule 6.
    """
    if district is not None:
        source = data_store.drivers_by_district
        if source is None:
            return JSONResponse(status_code=200, content=[])
        rows = source[
            (source["crop"] == crop.value) & (source["district_code"] == float(district))
        ]
    else:
        source = data_store.drivers
        if source is None:
            return JSONResponse(status_code=200, content=[])
        rows = source[source["crop"] == crop.value]

    records: list[dict[str, Any]] = rows.to_dict("records")  # type: ignore[assignment]
    payload = [DriverRow(**record).model_dump(mode="json") for record in records]

    cache_seconds = get_settings().CACHE_SECONDS
    return JSONResponse(
        content=payload, headers={"Cache-Control": f"public, max-age={cache_seconds}"}
    )
