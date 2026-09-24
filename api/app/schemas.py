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


class DriverRow(BaseModel):
    """One feature's SHAP-based association with log-yield for one crop, per
    src/agritwin/models/drivers.py. district_code/n_plots/reliability are null for the
    global (all-districts) summary and set for a per-district one (?district= given);
    a "suppressed" district row is still returned, not hidden, per golden rule 6.

    Known deviation from api/CLAUDE.md's ?crop&season[&district] signature: the driver
    model pools Season A and Season B together per crop (data/public/drivers.csv and
    drivers_by_district.csv carry no season column), so there is no season-specific
    result to filter to. `season` is accepted but currently has no effect; see
    docs/decisions.md for why re-training per season was not done as part of this
    endpoint.
    """

    crop: Crop
    district_code: int | None = None
    feature: str
    mean_abs_shap: float
    direction: str
    n_plots: int | None = None
    reliability: Reliability | None = None


class BacktestRow(BaseModel):
    """One model's nowcast backtest metrics for one crop x lead time, per
    src/agritwin/models/nowcast.py's leave_one_year_out_cv. Same season caveat as
    DriverRow: data/public/nowcast_backtest.csv has no season column, the backtest
    pools Season A and B together per crop.
    """

    crop: Crop
    lead_months: int
    model: str
    mape_pct: float
    mape_std_across_years: float
    mae_kg_ha: float
    n_years_tested: int


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
