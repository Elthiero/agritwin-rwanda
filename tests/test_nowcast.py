"""Unit tests for the nowcast module. Synthetic fixtures only."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agritwin.models.nowcast import (
    FEATURE_COLUMNS,
    attach_lagged_yield,
    build_feature_table,
    leave_one_year_out_cv,
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


def test_attach_lagged_yield_prior_season_wraps_to_previous_year_for_season_a():
    district_yield = pd.DataFrame(
        [
            _district_yield_row(season="B", year="2023", yield_kg_ha=700.0),
            _district_yield_row(season="A", year="2024", yield_kg_ha=1000.0),
        ]
    )
    lagged = attach_lagged_yield(district_yield)
    row_a_2024 = lagged[(lagged.season == "A") & (lagged.year == 2024)].iloc[0]
    assert row_a_2024["prior_season_yield_kg_ha"] == 700.0


def test_attach_lagged_yield_prior_season_same_year_for_season_b():
    district_yield = pd.DataFrame(
        [
            _district_yield_row(season="A", year="2024", yield_kg_ha=900.0),
            _district_yield_row(season="B", year="2024", yield_kg_ha=1100.0),
        ]
    )
    lagged = attach_lagged_yield(district_yield)
    row_b_2024 = lagged[(lagged.season == "B") & (lagged.year == 2024)].iloc[0]
    assert row_b_2024["prior_season_yield_kg_ha"] == 900.0


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
    assert pd.isna(lagged.iloc[0]["prior_season_yield_kg_ha"])
    assert pd.isna(lagged.iloc[0]["last_year_yield_kg_ha"])


def test_attach_lagged_yield_excludes_non_district_rows():
    district_yield = pd.DataFrame(
        [_district_yield_row(), _district_yield_row(geo_level="national", geo_code="RWA")]
    )
    lagged = attach_lagged_yield(district_yield)
    assert len(lagged) == 1


def test_build_feature_table_computes_anomalies_and_filters_by_lead_months():
    district_yield_lagged = attach_lagged_yield(
        pd.DataFrame([_district_yield_row(season="A", year="2024")])
    )
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
        district_yield_lagged, nowcast_features, ndvi_clim, rain_clim, lead_months=2
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
