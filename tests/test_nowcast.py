"""Unit tests for the nowcast module. Synthetic fixtures only."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agritwin.models.nowcast import (
    FEATURE_COLUMNS,
    attach_lagged_yield,
    attach_prior_season_for_lead,
    build_feature_table,
    build_yield_lookup,
    exclude_low_reliability,
    leave_one_year_out_cv,
    realistic_lookback_seasons,
    summarize_cv,
)

RNG = np.random.default_rng(0)


def _district_yield_row(**overrides) -> dict:
    base = {
        "geo_level": "district",
        "geo_code": "11",
        "crop": "maize",
        "season": "A",
        "year": "2024",
        "yield_kg_ha": 1000.0,
    }
    base.update(overrides)
    return base


def test_realistic_lookback_seasons_season_a_is_always_one_season_back():
    # Season A predictions are always safe using the immediately preceding season
    # (Season B), which already has months of margin at every lead time.
    assert realistic_lookback_seasons("A", lead_months=2) == 1
    assert realistic_lookback_seasons("A", lead_months=3) == 1
    assert realistic_lookback_seasons("A", lead_months=4) == 1


def test_realistic_lookback_seasons_season_b_falls_back_two_seasons_at_short_leads():
    # Season B at lead=2 or lead=3 cannot safely use Season A of the same year (Season
    # A's own report is not published until ~3.5 months after Season A concludes,
    # which lands inside Season B itself); must fall back two seasons instead. At
    # lead=4, Season A of the same year is safe again.
    assert realistic_lookback_seasons("B", lead_months=2) == 2
    assert realistic_lookback_seasons("B", lead_months=3) == 2
    assert realistic_lookback_seasons("B", lead_months=4) == 1


def test_attach_prior_season_for_lead_season_a_uses_immediately_prior_season_b():
    district_yield = pd.DataFrame(
        [
            _district_yield_row(season="B", year="2023", yield_kg_ha=700.0),
            _district_yield_row(season="A", year="2024", yield_kg_ha=1000.0),
        ]
    )
    lookup = build_yield_lookup(district_yield)
    lagged = attach_lagged_yield(district_yield)
    with_prior = attach_prior_season_for_lead(lagged, lookup, lead_months=2)
    row_a_2024 = with_prior[(with_prior.season == "A") & (with_prior.year == 2024)].iloc[0]
    assert row_a_2024["prior_season_yield_kg_ha"] == 700.0


def test_attach_prior_season_for_lead_season_b_short_lead_uses_two_seasons_back():
    district_yield = pd.DataFrame(
        [
            _district_yield_row(season="B", year="2023", yield_kg_ha=600.0),  # 2 back
            _district_yield_row(season="A", year="2024", yield_kg_ha=900.0),  # 1 back
            _district_yield_row(season="B", year="2024", yield_kg_ha=1100.0),
        ]
    )
    lookup = build_yield_lookup(district_yield)
    lagged = attach_lagged_yield(district_yield)

    with_prior_short = attach_prior_season_for_lead(lagged, lookup, lead_months=2)
    row_short = with_prior_short[
        (with_prior_short.season == "B") & (with_prior_short.year == 2024)
    ].iloc[0]
    assert row_short["prior_season_yield_kg_ha"] == 600.0  # two seasons back, not 900.0

    with_prior_long = attach_prior_season_for_lead(lagged, lookup, lead_months=4)
    row_long = with_prior_long[
        (with_prior_long.season == "B") & (with_prior_long.year == 2024)
    ].iloc[0]
    assert row_long["prior_season_yield_kg_ha"] == 900.0  # one season back, safe at lead=4


def test_attach_lagged_yield_last_year_is_same_season_one_year_earlier():
    district_yield = pd.DataFrame(
        [
            _district_yield_row(season="A", year="2023", yield_kg_ha=850.0),
            _district_yield_row(season="A", year="2024", yield_kg_ha=1000.0),
        ]
    )
    lagged = attach_lagged_yield(district_yield)
    row_2024 = lagged[lagged.year == 2024].iloc[0]
    assert row_2024["last_year_yield_kg_ha"] == 850.0


def test_attach_lagged_yield_missing_lag_is_null_not_zero():
    district_yield = pd.DataFrame([_district_yield_row(season="A", year="2019")])
    lagged = attach_lagged_yield(district_yield)
    assert pd.isna(lagged.iloc[0]["last_year_yield_kg_ha"])


def test_attach_prior_season_for_lead_missing_lag_is_null_not_zero():
    district_yield = pd.DataFrame([_district_yield_row(season="A", year="2019")])
    lookup = build_yield_lookup(district_yield)
    lagged = attach_lagged_yield(district_yield)
    with_prior = attach_prior_season_for_lead(lagged, lookup, lead_months=2)
    assert pd.isna(with_prior.iloc[0]["prior_season_yield_kg_ha"])


def test_attach_lagged_yield_excludes_non_district_rows():
    district_yield = pd.DataFrame(
        [_district_yield_row(), _district_yield_row(geo_level="national", geo_code="RWA")]
    )
    lagged = attach_lagged_yield(district_yield)
    assert len(lagged) == 1


def test_build_feature_table_computes_anomalies_and_filters_by_lead_months():
    district_yield = pd.DataFrame([_district_yield_row(season="A", year="2024")])
    district_yield_lagged = attach_lagged_yield(district_yield)
    yield_lookup = build_yield_lookup(district_yield)
    nowcast_features = pd.DataFrame(
        [
            {
                "nisr_district_code": 11.0,
                "season": "A",
                "year": 2024,
                "lead_months": 2,
                "ndvi_mean": 0.55,
                "ndvi_peak": 0.7,
                "rainfall_mm": 400.0,
            },
            {
                "nisr_district_code": 11.0,
                "season": "A",
                "year": 2024,
                "lead_months": 4,
                "ndvi_mean": 0.60,
                "ndvi_peak": 0.75,
                "rainfall_mm": 600.0,
            },
        ]
    )
    ndvi_clim = pd.DataFrame(
        [{"nisr_district_code": 11.0, "season": "A", "ndvi_climatology_mean": 0.50}]
    )
    rain_clim = pd.DataFrame(
        [{"nisr_district_code": 11.0, "season": "A", "rainfall_climatology_mm": 450.0}]
    )
    features = build_feature_table(
        district_yield_lagged, yield_lookup, nowcast_features, ndvi_clim, rain_clim, lead_months=2
    )
    assert len(features) == 1
    assert features.iloc[0]["ndvi_anomaly"] == pytest.approx(0.05)
    assert features.iloc[0]["rainfall_anomaly"] == pytest.approx(-50.0)


def _synthetic_features_df(n_districts: int = 6, n_years: int = 5) -> pd.DataFrame:
    rows = []
    for district in range(1, n_districts + 1):
        base_level = 500.0 + district * 50
        for year in range(2020, 2020 + n_years):
            ndvi_anom = RNG.normal(0, 0.05)
            rainfall_anom = RNG.normal(0, 50)
            true_anomaly = ndvi_anom * 2000 + rainfall_anom * 0.5 + RNG.normal(0, 20)
            rows.append(
                {
                    "district_code": float(district),
                    "crop": "maize",
                    "season": "A",
                    "year": year,
                    "yield_kg_ha": max(base_level + true_anomaly, 1.0),
                    "prior_season_yield_kg_ha": base_level,
                    "last_year_yield_kg_ha": base_level,
                    "ndvi_mean": 0.5 + ndvi_anom,
                    "ndvi_peak": 0.6 + ndvi_anom,
                    "ndvi_anomaly": ndvi_anom,
                    "rainfall_mm": 400.0 + rainfall_anom,
                    "rainfall_anomaly": rainfall_anom,
                }
            )
    return pd.DataFrame(rows)


def test_leave_one_year_out_cv_returns_one_row_per_held_out_year():
    features = _synthetic_features_df(n_districts=6, n_years=5)
    cv = leave_one_year_out_cv(features, min_train_rows=10)
    assert set(cv["held_out_year"]) == set(range(2020, 2025))
    assert {
        "baseline_district_mean_mape",
        "baseline_last_year_mape",
        "ridge_mape",
        "lgbm_mape",
    } <= set(cv.columns)


def test_leave_one_year_out_cv_all_mape_values_are_finite_and_non_negative():
    features = _synthetic_features_df(n_districts=6, n_years=5)
    cv = leave_one_year_out_cv(features, min_train_rows=10)
    mape_cols = [
        "baseline_district_mean_mape",
        "baseline_last_year_mape",
        "ridge_mape",
        "lgbm_mape",
    ]
    for col in mape_cols:
        assert (cv[col] >= 0).all()
        assert cv[col].notna().all()


def test_summarize_cv_weights_by_test_row_count():
    cv = pd.DataFrame(
        [
            {
                "held_out_year": 2020,
                "n_test_rows": 1,
                "baseline_district_mean_mape": 100.0,
                "baseline_last_year_mape": 100.0,
                "ridge_mape": 100.0,
                "lgbm_mape": 100.0,
            },
            {
                "held_out_year": 2021,
                "n_test_rows": 9,
                "baseline_district_mean_mape": 0.0,
                "baseline_last_year_mape": 0.0,
                "ridge_mape": 0.0,
                "lgbm_mape": 0.0,
            },
        ]
    )
    summary = summarize_cv(cv)
    assert summary["ridge_mape"] == pytest.approx(10.0)  # weighted, not (100+0)/2 = 50


def test_feature_columns_never_includes_last_year_yield():
    # last_year_yield_kg_ha is for the baseline comparison only; it must never leak into
    # the model's own input features (that would make the "last year" baseline and the
    # model trivially identical for that one input).
    assert "last_year_yield_kg_ha" not in FEATURE_COLUMNS


def test_leave_one_year_out_cv_handles_all_missing_feature_column_without_crashing():
    # Regression guard: a feature that is 100% missing within a fold's training rows
    # (e.g. prior_season_yield_kg_ha for a crop's very first surveyed season) must not
    # crash Ridge.fit via median()->NaN->fillna(NaN) being a no-op.
    features = _synthetic_features_df(n_districts=6, n_years=5)
    features["prior_season_yield_kg_ha"] = np.nan
    cv = leave_one_year_out_cv(features, min_train_rows=10)
    assert not cv.empty
    assert cv["ridge_mape"].notna().all()


def test_exclude_low_reliability_drops_only_suppressed_rows():
    features = pd.DataFrame(
        [
            {"reliability": "ok", "yield_kg_ha": 800.0},
            {"reliability": "use_with_caution", "yield_kg_ha": 900.0},
            {"reliability": "suppressed", "yield_kg_ha": 1000.0},
        ]
    )
    result = exclude_low_reliability(features)
    assert set(result["reliability"]) == {"ok", "use_with_caution"}
    assert len(result) == 2


def test_exclude_low_reliability_does_not_mutate_the_input():
    features = pd.DataFrame(
        [
            {"reliability": "ok", "yield_kg_ha": 800.0},
            {"reliability": "suppressed", "yield_kg_ha": 1000.0},
        ]
    )
    original_len = len(features)
    exclude_low_reliability(features)
    assert len(features) == original_len
