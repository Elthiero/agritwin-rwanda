"""Pydantic response schemas for API endpoints."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class Crop(StrEnum):
    """MVP crop scope, per config/crops.yaml canonical and config/settings.yaml scope.crops."""

    maize = "maize"
    beans = "beans"
    irish_potato = "irish_potato"
    sorghum = "sorghum"


class Season(StrEnum):
    """Seasons A and B only; Season C is excluded from MVP (see src/agritwin/CLAUDE.md)."""

    A = "A"
    B = "B"


class Reliability(StrEnum):
    """Matches src/agritwin/survey/core.py's add_reliability_flag output."""

    ok = "ok"
    use_with_caution = "use_with_caution"
    suppressed = "suppressed"


class YieldGapRow(BaseModel):
    """One district x crop x season x year yield gap figure. Every numeric estimate
    carries its confidence interval (where computed) and a reliability flag, per
    api/CLAUDE.md: a "suppressed" row is still returned so the frontend can grey it out,
    not silently omitted."""

    district_code: int
    crop: Crop
    season: Season
    year: int
    actual_yield_kg_ha: float
    actual_yield_kg_ha_ci_low: float | None = None
    actual_yield_kg_ha_ci_high: float | None = None
    attainable_yield_kg_ha: float | None = None
    yield_gap_kg_ha: float | None = None
    yield_gap_pct: float | None = None
    n_plots: int
    reliability: Reliability


class GeoJSONResponse(BaseModel):
    """GeoJSON FeatureCollection response."""

    type: str = "FeatureCollection"
    features: list[dict[str, Any]]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"district_name": "Kigali", "gaul_district_code": 1},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[29.0, -2.0], [29.1, -2.0]]],
                        },
                    }
                ],
            }
        }
    )
