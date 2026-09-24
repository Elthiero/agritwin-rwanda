"""Unit tests for the driver model. Synthetic fixtures only, small n for speed."""

from __future__ import annotations

import numpy as np
import pandas as pd

from agritwin.models.drivers import (
    FEATURE_COLUMNS,
    build_feature_table,
    compute_district_shap,
    compute_global_shap,
    cross_validate,
    fit_final_model,
)

RNG = np.random.default_rng(0)


def _synthetic_plot_crop(n_per_district: int = 20, n_districts: int = 6) -> pd.DataFrame:
    rows = []
    for district in range(1, n_districts + 1):
        for i in range(n_per_district):
            improved = RNG.random() > 0.5
            base_yield = 800.0 + (300.0 if improved else 0.0) + RNG.normal(0, 50)
            rows.append(
                {
                    "district_code": float(district),
                    "crop": "maize",
                    "season": "A",
                    "year": 2024,
                    "stratum": 10.0,
                    "segment_id": district * 100 + i,
                    "plot_id": i,
                    "weight": 1.0,
                    "harvest_kg": max(base_yield * 0.2, 1.0),
                    "plot_area_ha": 0.2,
                    "yield_kg_ha": max(base_yield, 1.0),
                    "qc_flag": "ok",
                    "improved_seed": improved,
                    "organic_fert": RNG.random() > 0.5,
                    "inorganic_fert": RNG.random() > 0.5,
                    "pesticide": RNG.random() > 0.5,
                    "anti_erosion": RNG.random() > 0.5,
                    "land_consolidation": RNG.random() > 0.5,
                    "mechanized": None,
                    "irrigated": RNG.random() > 0.5,
                    "erosion_degree": RNG.choice([1.0, 2.0, 3.0, 4.0]),
                    "sowing_month": RNG.integers(1, 13),
                }
            )
    return pd.DataFrame(rows)


def _soil_df(n_districts: int = 6) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "nisr_district_code": list(range(1, n_districts + 1)),
            "soil_ph": RNG.uniform(5, 7, n_districts),
            "soil_nitrogen": RNG.uniform(1, 2, n_districts),
            "soil_carbon": RNG.uniform(10, 20, n_districts),
            "soil_texture_class": RNG.integers(1, 6, n_districts).astype(float),
        }
    )


def _rainfall_df(n_districts: int = 6) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "nisr_district_code": list(range(1, n_districts + 1)),
            "season": ["A"] * n_districts,
            "year": [2024] * n_districts,
            "rainfall_mm": RNG.uniform(300, 600, n_districts),
        }
    )


def test_build_feature_table_excludes_zero_yield_and_other_crops():
    plot_crop = _synthetic_plot_crop(n_per_district=5, n_districts=2)
    plot_crop = pd.concat(
        [
            plot_crop,
            pd.DataFrame(
                [
                    {**plot_crop.iloc[0].to_dict(), "crop": "beans"},
                    {**plot_crop.iloc[0].to_dict(), "yield_kg_ha": 0.0, "harvest_kg": 0.0},
                ]
            ),
        ],
        ignore_index=True,
    )
    features = build_feature_table(plot_crop, _soil_df(2), _rainfall_df(2), crop="maize")
    assert (features["crop"] == "maize").all()
    assert (features["yield_kg_ha"] > 0).all()
    assert "log_yield" in features.columns


def test_build_feature_table_joins_soil_and_rainfall():
    plot_crop = _synthetic_plot_crop(n_per_district=3, n_districts=2)
    features = build_feature_table(plot_crop, _soil_df(2), _rainfall_df(2), crop="maize")
    assert features["soil_ph"].notna().all()
    assert features["rainfall_mm"].notna().all()


def test_build_feature_table_boolean_features_become_float_with_nan_preserved():
    plot_crop = _synthetic_plot_crop(n_per_district=3, n_districts=2)
    features = build_feature_table(plot_crop, _soil_df(2), _rainfall_df(2), crop="maize")
    assert features["mechanized"].isna().all()  # every synthetic row has mechanized=None
    assert features["improved_seed"].dropna().isin([0.0, 1.0]).all()


def test_cross_validate_returns_expected_keys_and_model_beats_baseline():
    plot_crop = _synthetic_plot_crop(n_per_district=20, n_districts=6)
    features = build_feature_table(plot_crop, _soil_df(6), _rainfall_df(6), crop="maize")
    metrics = cross_validate(features, n_splits=3)
    assert set(metrics) == {
        "n_splits",
        "n_rows",
        "n_districts",
        "model_mae_log",
        "baseline_mae_log",
        "improvement_over_baseline_pct",
    }
    # improved_seed has a strong, real effect in the synthetic data, so the model should
    # genuinely beat a constant-mean baseline, not just tie or lose to it.
    assert metrics["model_mae_log"] < metrics["baseline_mae_log"]


def test_fit_final_model_and_global_shap_ranks_improved_seed_highly():
    plot_crop = _synthetic_plot_crop(n_per_district=30, n_districts=6)
    features = build_feature_table(plot_crop, _soil_df(6), _rainfall_df(6), crop="maize")
    model = fit_final_model(features)
    shap_summary = compute_global_shap(model, features)

    assert set(shap_summary["feature"]) == set(FEATURE_COLUMNS)
    assert set(shap_summary["direction"]) <= {"positive", "negative"}
    # improved_seed is the dominant synthetic driver, so it should rank at or near the top.
    top_features = shap_summary.head(3)["feature"].tolist()
    assert "improved_seed" in top_features


def test_compute_district_shap_suppresses_below_min_plots():
    plot_crop = _synthetic_plot_crop(n_per_district=30, n_districts=6)
    features = build_feature_table(plot_crop, _soil_df(6), _rainfall_df(6), crop="maize")
    model = fit_final_model(features)
    district_shap = compute_district_shap(model, features, min_plots=100)
    assert (district_shap["reliability"] == "suppressed").all()

    district_shap_ok = compute_district_shap(model, features, min_plots=5)
    assert (district_shap_ok["reliability"] == "ok").all()
    assert set(district_shap_ok["district_code"]) == set(features["district_code"])


def test_compute_district_shap_has_one_row_per_district_per_feature():
    plot_crop = _synthetic_plot_crop(n_per_district=10, n_districts=3)
    features = build_feature_table(plot_crop, _soil_df(3), _rainfall_df(3), crop="maize")
    model = fit_final_model(features)
    district_shap = compute_district_shap(model, features, min_plots=1)
    assert len(district_shap) == 3 * len(FEATURE_COLUMNS)
