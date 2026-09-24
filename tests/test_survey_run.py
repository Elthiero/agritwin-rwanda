"""Unit tests for survey/run.py's orchestration logic. Synthetic fixtures, no real I/O."""

from __future__ import annotations

import pandas as pd

from agritwin.survey.run import to_public


def test_to_public_keeps_suppressed_rows_with_the_reliability_flag():
    # CLAUDE.md golden rule 6: low-reliability cells are flagged and greyed out in the
    # UI, not removed. to_public() must not silently drop them; that's a decision for the
    # API/frontend layer to render, not for the export step to make on their behalf.
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
    assert len(public) == 2
    assert set(public["reliability"]) == {"suppressed", "ok"}
    suppressed_row = public[public["geo_code"] == "11"].iloc[0]
    assert suppressed_row["yield_kg_ha"] == 100.0  # the number itself is not hidden


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
