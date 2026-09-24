"""Unit test for models/run.py's orchestration logic. Synthetic fixtures, monkeypatched I/O."""

from __future__ import annotations

import pandas as pd


def test_run_wires_settings_and_writes_expected_outputs(monkeypatch, tmp_path):
    import agritwin.models.run as run_module

    fake_settings = {"attainable": {"percentile": 90, "kmeans_k": 2, "min_segments": 1}}

    soil = pd.DataFrame(
        {
            "nisr_district_code": [11, 12],
            "soil_ph": [5.5, 6.0],
            "soil_nitrogen": [1.2, 1.5],
            "soil_carbon": [15.0, 18.0],
            "soil_texture_class": [4.0, 5.0],
        }
    )
    cropland = pd.DataFrame({"nisr_district_code": [11, 12], "cropland_fraction": [0.3, 0.5]})
    plot_crop = pd.DataFrame(
        [
            {
                "district_code": 11.0,
                "crop": "maize",
                "season": "A",
                "year": 2024,
                "stratum": 10.0,
                "segment_id": 1,
                "plot_id": 1,
                "weight": 1.0,
                "harvest_kg": 500.0,
                "plot_area_ha": 0.5,
                "yield_kg_ha": 1000.0,
                "qc_flag": "ok",
            },
            {
                "district_code": 12.0,
                "crop": "maize",
                "season": "A",
                "year": 2024,
                "stratum": 10.0,
                "segment_id": 2,
                "plot_id": 2,
                "weight": 1.0,
                "harvest_kg": 400.0,
                "plot_area_ha": 0.5,
                "yield_kg_ha": 800.0,
                "qc_flag": "ok",
            },
        ]
    )
    district_yield = pd.DataFrame(
        [
            {
                "geo_level": "district",
                "geo_code": "11",
                "crop": "maize",
                "season": "A",
                "year": "2024",
                "yield_kg_ha": 900.0,
                "yield_kg_ha_ci_low": 800.0,
                "yield_kg_ha_ci_high": 1000.0,
                "n_plots": 10,
                "n_segments": 6,
                "reliability": "ok",
            }
        ]
    )

    monkeypatch.setattr(run_module, "load_settings", lambda: fake_settings)
    monkeypatch.setattr(pd, "read_csv", lambda path: soil if "soil" in str(path) else cropland)
    monkeypatch.setattr(
        pd,
        "read_parquet",
        lambda path: plot_crop if "stg_sas_plot_crop" in str(path) else district_yield,
    )

    written: dict[str, pd.DataFrame] = {}

    def _record(self: pd.DataFrame, path: object, **_k: object) -> None:
        written.setdefault(str(path), self)

    monkeypatch.setattr(pd.DataFrame, "to_parquet", _record)
    monkeypatch.setattr(pd.DataFrame, "to_csv", _record)

    zones, attainable_yield, yield_gap = run_module.run()

    assert len(zones) == 2
    assert len(attainable_yield) >= 1
    assert len(yield_gap) == 1
    assert any("attainable_yield.parquet" in p for p in written)
    assert any("yield_gap.parquet" in p for p in written)
    assert any("district_zones.csv" in p for p in written)
    assert any("yield_gap.csv" in p for p in written)


def test_run_drivers_writes_artifacts_and_public_csvs(monkeypatch, tmp_path):
    import agritwin.models.run as run_module

    rng = __import__("numpy").random.default_rng(0)
    rows = []
    for district in [11, 12]:
        for i in range(15):
            improved = rng.random() > 0.5
            base = 800.0 + (300.0 if improved else 0.0) + rng.normal(0, 50)
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
                    "harvest_kg": max(base * 0.2, 1.0),
                    "plot_area_ha": 0.2,
                    "yield_kg_ha": max(base, 1.0),
                    "qc_flag": "ok",
                    "improved_seed": improved,
                    "organic_fert": True,
                    "inorganic_fert": False,
                    "pesticide": False,
                    "anti_erosion": True,
                    "land_consolidation": False,
                    "mechanized": None,
                    "irrigated": False,
                    "erosion_degree": 2.0,
                    "sowing_month": 3,
                }
            )
    plot_crop = pd.DataFrame(rows)
    soil = pd.DataFrame(
        {
            "nisr_district_code": [11, 12],
            "soil_ph": [5.5, 6.0],
            "soil_nitrogen": [1.2, 1.5],
            "soil_carbon": [15.0, 18.0],
            "soil_texture_class": [4.0, 5.0],
        }
    )
    rainfall = pd.DataFrame(
        {
            "nisr_district_code": [11, 12],
            "season": ["A", "A"],
            "year": [2024, 2024],
            "rainfall_mm": [450.0, 480.0],
        }
    )
    fake_settings = {
        "scope": {"crops": ["maize"]},
        "drivers": {
            "n_splits": 2,
            "min_plots": 5,
            "target": "log_yield",
            "cv": "group_kfold_district",
            "levers": ["improved_seed", "inorganic_fert"],
        },
        "scenario": {"bootstrap_reps": 3},
        "project": {"data_version": "test"},
    }

    monkeypatch.setattr(run_module, "load_settings", lambda: fake_settings)
    monkeypatch.setattr(run_module, "ARTIFACTS", tmp_path / "artifacts")
    monkeypatch.setattr(
        pd, "read_csv", lambda path: soil if "soil" in str(path) else rainfall
    )
    monkeypatch.setattr(pd, "read_parquet", lambda path: plot_crop)

    written: dict[str, pd.DataFrame] = {}

    def _record(self: pd.DataFrame, path: object, **_k: object) -> None:
        written.setdefault(str(path), self)

    monkeypatch.setattr(pd.DataFrame, "to_csv", _record)

    run_module.run_drivers()

    assert (tmp_path / "artifacts" / "drivers_maize.txt").exists()
    assert (tmp_path / "artifacts" / "drivers_maize_metadata.json").exists()
    assert any("drivers.csv" in p for p in written)
    assert any("drivers_by_district.csv" in p for p in written)
    assert any("scenario.csv" in p for p in written)


def test_run_nowcast_writes_backtest_csv(monkeypatch):
    import agritwin.models.run as run_module

    rng = __import__("numpy").random.default_rng(0)
    district_rows = []
    for district in [11, 12, 13, 14, 15, 16]:
        # season B in year-1 of each season A year, so prior_season_yield_kg_ha (season A's
        # prior season is season B of the previous year) resolves for every row, matching
        # real district_yield data where both seasons exist for every year.
        for year in [2019, 2020, 2021, 2022, 2023, 2024]:
            district_rows.append(
                {
                    "geo_level": "district",
                    "geo_code": str(district),
                    "crop": "maize",
                    "season": "A",
                    "year": str(year),
                    "yield_kg_ha": 800.0 + district * 10 + rng.normal(0, 30),
                    "reliability": "ok",
                }
            )
            district_rows.append(
                {
                    "geo_level": "district",
                    "geo_code": str(district),
                    "crop": "maize",
                    "season": "B",
                    "year": str(year),
                    "yield_kg_ha": 750.0 + district * 10 + rng.normal(0, 30),
                    "reliability": "ok",
                }
            )
    district_yield = pd.DataFrame(district_rows)

    nowcast_rows = []
    for district in [11, 12, 13, 14, 15, 16]:
        for year in [2020, 2021, 2022, 2023, 2024]:
            for lead in [2, 4]:
                nowcast_rows.append(
                    {
                        "nisr_district_code": district,
                        "season": "A",
                        "year": year,
                        "lead_months": lead,
                        "ndvi_mean": 0.5 + rng.normal(0, 0.02),
                        "ndvi_peak": 0.65 + rng.normal(0, 0.02),
                        "rainfall_mm": 400.0 + rng.normal(0, 10),
                    }
                )
    nowcast_features = pd.DataFrame(nowcast_rows)
    ndvi_climatology = pd.DataFrame(
        [
            {"nisr_district_code": d, "season": "A", "ndvi_climatology_mean": 0.5}
            for d in [11, 12, 13, 14, 15, 16]
        ]
    )
    rainfall_climatology = pd.DataFrame(
        [
            {"nisr_district_code": d, "season": "A", "rainfall_climatology_mm": 400.0}
            for d in [11, 12, 13, 14, 15, 16]
        ]
    )

    fake_settings = {
        "scope": {"crops": ["maize"]},
        "nowcast": {"lead_months": [2, 4]},
    }

    def _fake_read_csv(path, **_k):
        path = str(path)
        if "ndvi_climatology" in path:
            return ndvi_climatology
        if "rainfall_climatology" in path:
            return rainfall_climatology
        return nowcast_features

    monkeypatch.setattr(run_module, "load_settings", lambda: fake_settings)
    monkeypatch.setattr(pd, "read_csv", _fake_read_csv)
    monkeypatch.setattr(pd, "read_parquet", lambda path: district_yield)

    written: dict[str, pd.DataFrame] = {}

    def _record(self: pd.DataFrame, path: object, **_k: object) -> None:
        written.setdefault(str(path), self)

    monkeypatch.setattr(pd.DataFrame, "to_csv", _record)

    run_module.run_nowcast()

    assert any("nowcast_backtest.csv" in p for p in written)
    backtest = next(df for p, df in written.items() if "nowcast_backtest.csv" in p)
    assert set(backtest["model"]) == {
        "baseline_district_mean",
        "baseline_last_year",
        "ridge",
        "lgbm",
    }
    assert set(backtest["lead_months"]) == {2, 4}

    assert any("nowcast_curve.csv" in p for p in written)
    curve = next(df for p, df in written.items() if "nowcast_curve.csv" in p)
    expected_curve_cols = {
        "district_code",
        "season",
        "year",
        "lead_months",
        "ndvi_anomaly",
        "rainfall_anomaly",
    }
    assert expected_curve_cols <= set(curve.columns)

    nowcast_path = next(p for p in written if p.endswith("nowcast.csv"))
    nowcast = written[nowcast_path]
    expected_nowcast_cols = {
        "district_code",
        "crop",
        "season",
        "year",
        "lead_months",
        "model",
        "predicted_yield_kg_ha",
        "ci_low",
        "ci_high",
        "is_backtest",
        "reliability",
    }
    assert expected_nowcast_cols <= set(nowcast.columns)
    assert (nowcast["ci_high"] >= nowcast["ci_low"]).all()
