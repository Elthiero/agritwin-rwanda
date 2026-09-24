"""Per-district composite profile endpoint."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from api.app.data_store import data_store
from api.app.schemas import (
    Crop,
    DistrictInfo,
    DistrictProfile,
    DriverRow,
    Season,
    YearlyGap,
    YearlyYield,
)
from api.app.settings import get_settings

router = APIRouter()


@router.get("/districts/{code}/profile", response_model=DistrictProfile)
def get_district_profile(
    code: int,
    crop: Annotated[Crop, Query(description="MVP crop")],
    season: Annotated[
        Season,
        Query(description="A or B. Has no effect on top_drivers: see DriverRow docstring"),
    ],
) -> JSONResponse:
    """Composite view for one district x crop, assembled from already-precomputed
    data/public/ files: yield trend and yield-gap trend across years, this district's
    top SHAP drivers, and its peer districts (same k-means zone). No new modeling."""
    district_name = data_store.district_name(code)
    if district_name is None:
        raise HTTPException(status_code=404, detail=f"Unknown district_code {code}")

    yield_trend: list[YearlyYield] = []
    if data_store.district_yield is not None:
        # geo_code is a plain string column shared across district/province/national
        # rows ("RWA" for national), so it must be filtered to district level before
        # casting to float, not in the same combined boolean expression (pandas
        # evaluates every operand, it does not short-circuit).
        df = data_store.district_yield
        df = df[df["geo_level"] == "district"]
        rows = df[
            (df["geo_code"].astype(float) == float(code))
            & (df["crop"] == crop.value)
            & (df["season"] == season.value)
        ].sort_values("year")
        yield_trend = [
            YearlyYield(
                year=int(r["year"]),
                yield_kg_ha=r["yield_kg_ha"],
                yield_kg_ha_ci_low=r.get("yield_kg_ha_ci_low"),
                yield_kg_ha_ci_high=r.get("yield_kg_ha_ci_high"),
                reliability=r["reliability"],
            )
            for r in rows.to_dict("records")
        ]

    gap_trend: list[YearlyGap] = []
    if data_store.yield_gap is not None:
        df = data_store.yield_gap
        rows = df[
            (df["district_code"] == float(code))
            & (df["crop"] == crop.value)
            & (df["season"] == season.value)
        ].sort_values("year")
        gap_trend = [
            YearlyGap(
                year=int(r["year"]),
                actual_yield_kg_ha=r["actual_yield_kg_ha"],
                attainable_yield_kg_ha=r.get("attainable_yield_kg_ha"),
                yield_gap_kg_ha=r.get("yield_gap_kg_ha"),
                yield_gap_pct=r.get("yield_gap_pct"),
                reliability=r["reliability"],
            )
            for r in rows.to_dict("records")
        ]

    top_drivers: list[DriverRow] = []
    if data_store.drivers_by_district is not None:
        df = data_store.drivers_by_district
        rows = df[(df["district_code"] == float(code)) & (df["crop"] == crop.value)]
        rows = rows.sort_values("mean_abs_shap", ascending=False).head(5)
        driver_records: list[dict[str, Any]] = rows.to_dict("records")  # type: ignore[assignment]
        top_drivers = [DriverRow(**r) for r in driver_records]

    peer_districts: list[DistrictInfo] = []
    if data_store.district_zones is not None:
        zones = data_store.district_zones
        this_row = zones[zones["nisr_district_code"] == code]
        if not this_row.empty:
            zone_id = this_row.iloc[0]["zone_id"]
            peer_codes = zones[
                (zones["zone_id"] == zone_id) & (zones["nisr_district_code"] != code)
            ]["nisr_district_code"].tolist()
            peer_districts = [
                DistrictInfo(
                    district_code=int(peer_code),
                    district_name=data_store.district_name(int(peer_code)) or "",
                )
                for peer_code in peer_codes
            ]

    payload = DistrictProfile(
        district_code=code,
        district_name=district_name,
        crop=crop,
        yield_trend=yield_trend,
        gap_trend=gap_trend,
        top_drivers=top_drivers,
        peer_districts=peer_districts,
    ).model_dump(mode="json")

    cache_seconds = get_settings().CACHE_SECONDS
    return JSONResponse(
        content=payload, headers={"Cache-Control": f"public, max-age={cache_seconds}"}
    )
