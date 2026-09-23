"""Geographic data endpoints (districts, basemaps, etc.)."""

from __future__ import annotations

from fastapi import APIRouter

from api.app.data_store import data_store
from api.app.schemas import GeoJSONResponse

router = APIRouter()


@router.get("/districts", response_model=GeoJSONResponse)
def get_districts() -> GeoJSONResponse:
    """Serve simplified Rwanda district boundaries as GeoJSON."""
    if not data_store.districts_geojson:
        return GeoJSONResponse(features=[])
    return GeoJSONResponse(**data_store.districts_geojson)
