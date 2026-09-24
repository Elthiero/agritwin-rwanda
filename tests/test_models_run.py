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
