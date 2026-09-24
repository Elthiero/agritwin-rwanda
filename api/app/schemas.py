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


class NowcastRow(BaseModel):
    """One district's early yield estimate for one crop x season x year x lead time,
    from src/agritwin/models/nowcast.py's leave-one-year-out out-of-fold predictions.
    `model` is whichever of the 4 candidates had the lowest backtest MAPE for this crop
    x lead_months (see /backtest and data/public/nowcast_backtest.csv); per
    docs/decisions.md 2026-09-24, that is often baseline_district_mean, not a fancier
    model, and this field says which one was actually used. `ci_low`/`ci_high` are a
    normal-approximation interval from that model's own backtest residual spread, per
    CLAUDE.md golden rule 6. `is_backtest` is True for every row currently served: every
    year here has a completed SAS survey, so this is 2019-2025 historical hold-out data,
    not a live in-season prediction."""

    district_code: int
    crop: Crop
    season: Season
    year: int
    lead_months: int
    model: str
    predicted_yield_kg_ha: float
    ci_low: float
    ci_high: float
    actual_yield_kg_ha: float | None = None
    is_backtest: bool
    reliability: Reliability


class NowcastCurveRow(BaseModel):
    """District-level NDVI and CHIRPS rainfall signal at one lead time into a season,
    against its own multi-year climatology (MODIS 2001-2018, CHIRPS 1991-2020), per
    src/agritwin/models/nowcast.py's build_curve_table. Not crop-specific: the
    satellite signal is the same regardless of which crop is grown in that district."""

    district_code: int
    season: Season
    year: int
    lead_months: int
    ndvi_mean: float
    ndvi_climatology_mean: float
    ndvi_anomaly: float
    rainfall_mm: float
    rainfall_climatology_mm: float
    rainfall_anomaly: float


class KpiRow(BaseModel):
    """National-level yield estimate for one crop, for one season x year, per
    src/agritwin/survey/ (geo_level == "national"). One row per MVP crop, not a single
    blended number, so each keeps its own CI and reliability."""

    crop: Crop
    season: Season
    year: int
    yield_kg_ha: float
    yield_kg_ha_ci_low: float | None = None
    yield_kg_ha_ci_high: float | None = None
    n_plots: int
    reliability: Reliability


class DistrictInfo(BaseModel):
    """Minimal district identity: code plus display name."""

    district_code: int
    district_name: str


class YearlyYield(BaseModel):
    """One year's district-level weighted yield estimate, per src/agritwin/survey/."""

    year: int
    yield_kg_ha: float
    yield_kg_ha_ci_low: float | None = None
    yield_kg_ha_ci_high: float | None = None
    reliability: Reliability


class YearlyGap(BaseModel):
    """One year's actual vs. attainable yield for a district, per
    src/agritwin/models/attainable.py."""

    year: int
    actual_yield_kg_ha: float
    attainable_yield_kg_ha: float | None = None
    yield_gap_kg_ha: float | None = None
    yield_gap_pct: float | None = None
    reliability: Reliability


class DistrictProfile(BaseModel):
    """Composite per-district view assembled from data/public/ only (no new modeling):
    yield trend and yield-gap trend across years, this district's top SHAP drivers, and
    its peer districts (same k-means zone, per src/agritwin/models/attainable.py's
    zone assignment, the same fallback used in place of a real agro-ecological-zone
    layer)."""

    district_code: int
    district_name: str
    crop: Crop
    yield_trend: list[YearlyYield]
    gap_trend: list[YearlyGap]
    top_drivers: list[DriverRow]
    peer_districts: list[DistrictInfo]


class ScenarioRow(BaseModel):
    """One lever configuration's predicted mean yield for one district x crop, per
    src/agritwin/models/scenario.py. Model-based estimate, not causal (CLAUDE.md rule
    5): a hypothetical input to the driver model, not a simulation of a real
    intervention. Same season caveat as DriverRow/BacktestRow: season is accepted but
    has no effect, since the driver model pools both seasons."""

    crop: Crop
    district_code: int
    improved_seed: bool
    inorganic_fert: bool
    organic_fert: bool
    irrigated: bool
    mean_yield_kg_ha: float
    ci_low: float
    ci_high: float
    n_plots: int
    reliability: Reliability


class MetaResponse(BaseModel):
    """Crops, seasons, years and districts that actually have data behind them, so the
    frontend never hardcodes scope that could drift from data/public/."""

    crops: list[Crop]
    seasons: list[Season]
    years: list[int]
    districts: list[DistrictInfo]
    data_version: str
    last_updated: str | None = None


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
                        "properties": {
                            "district_name": "Kigali",
                            "gaul_district_code": 1,
                            "district_code": 12,
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[29.0, -2.0], [29.1, -2.0]]],
                        },
                    }
                ],
            }
        }
    )
