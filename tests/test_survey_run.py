"""Unit tests for survey/run.py's orchestration logic. Synthetic fixtures, no real I/O."""

from __future__ import annotations

import pandas as pd

from agritwin.survey.run import to_public


def test_to_public_drops_suppressed_rows():
    district_yield = pd.DataFrame(
        [
            {
                "geo_level": "district",
                "geo_code": "11",
                "crop": "maize",
                "season": "A",
                "year": "2024",
                "total_production_kg": 1000.0,
                "total_production_kg_se": 100.0,
                "total_area_ha": 10.0,
                "total_area_ha_se": 1.0,
                "yield_kg_ha": 100.0,
                "yield_kg_ha_se": 10.0,
                "yield_kg_ha_ci_low": 80.0,
                "yield_kg_ha_ci_high": 120.0,
                "yield_kg_ha_cv": 0.10,
                "n_plots": 5,
                "n_segments": 3,
                "reliability": "suppressed",
            },
            {
                "geo_level": "district",
                "geo_code": "12",
                "crop": "maize",
                "season": "A",
                "year": "2024",
                "total_production_kg": 5000.0,
                "total_production_kg_se": 300.0,
                "total_area_ha": 40.0,
                "total_area_ha_se": 2.0,
                "yield_kg_ha": 125.0,
                "yield_kg_ha_se": 8.0,
                "yield_kg_ha_ci_low": 110.0,
                "yield_kg_ha_ci_high": 140.0,
                "yield_kg_ha_cv": 0.06,
                "n_plots": 40,
                "n_segments": 25,
                "reliability": "ok",
            },
        ]
    )
    public = to_public(district_yield)
    assert "suppressed" not in set(public["reliability"])
    assert len(public) == 1
    assert public.iloc[0]["geo_code"] == "12"


def test_to_public_never_has_a_row_below_the_suppression_threshold():
    # Every remaining row's n_segments must reflect a reliability decision already made
    # (not re-derived here); this just confirms suppression happened, whatever the
    # configured min_segments threshold was upstream.
    district_yield = pd.DataFrame(
        [
            {
                "geo_level": "national",
                "geo_code": "RWA",
                "crop": "beans",
                "season": "B",
                "year": "2024",
                "total_production_kg": 100.0,
                "total_production_kg_se": 50.0,
                "total_area_ha": 1.0,
                "total_area_ha_se": 0.5,
                "yield_kg_ha": 100.0,
                "yield_kg_ha_se": 40.0,
                "yield_kg_ha_ci_low": 20.0,
                "yield_kg_ha_ci_high": 180.0,
                "yield_kg_ha_cv": 0.40,
                "n_plots": 2,
                "n_segments": 2,
                "reliability": "suppressed",
            }
        ]
    )
    public = to_public(district_yield)
    assert len(public) == 0


def test_to_public_drops_internal_standard_error_columns():
    district_yield = pd.DataFrame(
        [
            {
                "geo_level": "national",
                "geo_code": "RWA",
                "crop": "maize",
                "season": "A",
                "year": "2024",
                "total_production_kg": 1000.0,
                "total_production_kg_se": 100.0,
                "total_area_ha": 10.0,
                "total_area_ha_se": 1.0,
                "yield_kg_ha": 100.0,
                "yield_kg_ha_se": 10.0,
                "yield_kg_ha_ci_low": 80.0,
                "yield_kg_ha_ci_high": 120.0,
                "yield_kg_ha_cv": 0.10,
                "n_plots": 40,
                "n_segments": 25,
                "reliability": "ok",
            }
        ]
    )
    public = to_public(district_yield)
    assert "total_production_kg_se" not in public.columns
    assert "total_area_ha_se" not in public.columns
    assert "yield_kg_ha_se" not in public.columns
    assert "yield_kg_ha_cv" not in public.columns
