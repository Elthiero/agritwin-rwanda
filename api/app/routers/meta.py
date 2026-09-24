"""Metadata endpoint: crops, seasons, years and districts actually in scope."""

from __future__ import annotations

from fastapi import APIRouter

from api.app.data_store import DATA_VERSION, data_store
from api.app.schemas import Crop, DistrictInfo, MetaResponse, Season

router = APIRouter()


@router.get("/meta", response_model=MetaResponse)
def get_meta() -> MetaResponse:
    """Lets the frontend read scope (years, districts) from the real data rather than
    hardcoding it, so it can never drift from what data/public/ actually contains."""
    years: list[int] = []
    if data_store.district_yield is not None:
        years = sorted(int(y) for y in data_store.district_yield["year"].unique())

    districts: list[DistrictInfo] = []
    if data_store.districts_geojson:
        for feature in data_store.districts_geojson["features"]:
            props = feature["properties"]
            code = props.get("district_code")
            if code is not None:
                districts.append(
                    DistrictInfo(district_code=code, district_name=props["district_name"])
                )
        districts.sort(key=lambda d: d.district_code)

    return MetaResponse(
        crops=list(Crop),
        seasons=list(Season),
        years=years,
        districts=districts,
        data_version=DATA_VERSION,
        last_updated=data_store.last_updated,
    )
