"""Unit tests for the scenario explorer lever grid. Synthetic fixtures only."""

from __future__ import annotations

import numpy as np
import pandas as pd

from agritwin.models.drivers import build_feature_table, fit_final_model
from agritwin.models.scenario import bootstrap_district_scenario, lever_grid, predict_yield_kg_ha

RNG = np.random.default_rng(0)

LEVERS = ["improved_seed", "inorganic_fert", "organic_fert", "irrigated"]


def _synthetic_plot_crop(n_per_district: int = 20, n_districts: int = 3) -> pd.DataFrame:
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


def _soil_df(n_districts: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "nisr_district_code": list(range(1, n_districts + 1)),
            "soil_ph": RNG.uniform(5, 7, n_districts),
            "soil_nitrogen": RNG.uniform(1, 2, n_districts),
            "soil_carbon": RNG.uniform(10, 20, n_districts),
            "soil_texture_class": RNG.integers(1, 6, n_districts).astype(float),
        }
    )


def _rainfall_df(n_districts: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "nisr_district_code": list(range(1, n_districts + 1)),
            "season": ["A"] * n_districts,
            "year": [2024] * n_districts,
            "rainfall_mm": RNG.uniform(300, 600, n_districts),
        }
    )


def _features(n_per_district: int = 20, n_districts: int = 3) -> pd.DataFrame:
    plot_crop = _synthetic_plot_crop(n_per_district, n_districts)
    soil, rainfall = _soil_df(n_districts), _rainfall_df(n_districts)
    return build_feature_table(plot_crop, soil, rainfall, crop="maize")


def test_lever_grid_has_all_combinations():
    grid = lever_grid(LEVERS)
    assert len(grid) == 2 ** len(LEVERS)
    assert len(grid) == len(set(tuple(sorted(c.items())) for c in grid))
    all_on = {lever: True for lever in LEVERS}
    assert all_on in grid


def test_predict_yield_kg_ha_is_positive_and_overrides_lever():
    features = _features()
    model = fit_final_model(features)
    off = predict_yield_kg_ha(model, features, {"improved_seed": False})
    on = predict_yield_kg_ha(model, features, {"improved_seed": True})
    assert (off > 0).all() and (on > 0).all()
    # improved_seed is a strong positive driver in the synthetic data.
    assert on.mean() > off.mean()


def test_bootstrap_district_scenario_shape_and_reliability():
    features = _features(n_per_district=20, n_districts=2)
    model = fit_final_model(features)
    result = bootstrap_district_scenario(
        model, features, levers=LEVERS, n_reps=20, min_plots=5, random_state=1
    )
    assert len(result) == 2 * 2 ** len(LEVERS)
    assert (result["reliability"] == "ok").all()
    assert (result["ci_low"] <= result["ci_high"]).all()
    assert (result["mean_yield_kg_ha"] > 0).all()


def test_bootstrap_district_scenario_suppresses_below_min_plots():
    features = _features(n_per_district=10, n_districts=1)
    model = fit_final_model(features)
    result = bootstrap_district_scenario(
        model, features, levers=LEVERS, n_reps=5, min_plots=100, random_state=1
    )
    assert (result["reliability"] == "suppressed").all()
