"""Unit tests for the attainable-yield module. Synthetic fixtures only."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agritwin.models.attainable import (
    assign_zones,
    attach_zone,
    compute_attainable_yield,
    compute_yield_gap,
    weighted_percentile,
)


def test_weighted_percentile_with_uniform_weights_matches_unweighted():
    values = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    weights = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0])
    result = weighted_percentile(values, weights, 90)
    expected = np.percentile(values.to_numpy(), 90)
    assert result == pytest.approx(expected, rel=0.15)  # midpoint method vs linear, close not exact


def test_weighted_percentile_heavier_weight_pulls_the_percentile_toward_it():
    values = pd.Series([10.0, 100.0])
    weights_even = pd.Series([1.0, 1.0])
    weights_skewed = pd.Series([1.0, 100.0])  # almost all weight on the 100.0 observation
    even_result = weighted_percentile(values, weights_even, 50)
    skewed_result = weighted_percentile(values, weights_skewed, 50)
    assert skewed_result > even_result


def test_weighted_percentile_order_independent():
    values = pd.Series([30.0, 10.0, 20.0])
    weights = pd.Series([1.0, 2.0, 1.0])
    result_a = weighted_percentile(values, weights, 90)
    result_b = weighted_percentile(values.iloc[::-1], weights.iloc[::-1], 90)
    assert result_a == pytest.approx(result_b)


def test_assign_zones_is_deterministic_and_covers_every_district():
    soil = pd.DataFrame(
        {
            "nisr_district_code": [11, 12, 13, 21],
            "soil_ph": [5.5, 6.0, 5.8, 6.2],
            "soil_nitrogen": [1.2, 1.5, 1.1, 1.6],
            "soil_carbon": [15.0, 18.0, 14.0, 20.0],
            "soil_texture_class": [4.0, 4.0, 5.0, 3.0],
        }
    )
    cropland = pd.DataFrame(
        {"nisr_district_code": [11, 12, 13, 21], "cropland_fraction": [0.3, 0.5, 0.2, 0.6]}
    )
    zones_a = assign_zones(soil, cropland, k=2, random_state=0)
    zones_b = assign_zones(soil, cropland, k=2, random_state=0)
    pd.testing.assert_frame_equal(
        zones_a.sort_values("nisr_district_code").reset_index(drop=True),
        zones_b.sort_values("nisr_district_code").reset_index(drop=True),
    )
    assert set(zones_a["nisr_district_code"]) == {11, 12, 13, 21}
    assert zones_a["zone_id"].nunique() == 2


def test_attach_zone_joins_on_district_code():
    plot_crop = pd.DataFrame({"district_code": [11.0, 12.0], "harvest_kg": [500.0, 600.0]})
    zones = pd.DataFrame({"nisr_district_code": [11, 12], "zone_id": [0, 1]})
    result = attach_zone(plot_crop, zones)
    assert list(result["zone_id"]) == [0, 1]
    assert "nisr_district_code" not in result.columns


def _eligible_row(**overrides) -> dict:
    base = {
        "zone_id": 0,
        "crop": "maize",
        "season": "A",
        "year": 2024,
        "segment_id": 1,
        "weight": 1.0,
        "yield_kg_ha": 1000.0,
    }
    base.update(overrides)
    return base


def test_compute_attainable_yield_pools_across_years():
    rows = [
        _eligible_row(year=2019, segment_id=1, yield_kg_ha=800.0),
        _eligible_row(year=2024, segment_id=2, yield_kg_ha=1200.0),
    ]
    df = pd.DataFrame(rows)
    result = compute_attainable_yield(df, percentile=90, min_segments=1)
    assert len(result) == 1  # one (zone, crop, season) group, both years pooled into it
    assert result.iloc[0]["n_years"] == 2
    assert result.iloc[0]["n_plots"] == 2


def test_compute_attainable_yield_suppresses_below_min_segments():
    rows = [_eligible_row(segment_id=1), _eligible_row(segment_id=2)]
    df = pd.DataFrame(rows)
    result = compute_attainable_yield(df, percentile=90, min_segments=5)
    assert result.iloc[0]["reliability"] == "suppressed"


def test_compute_attainable_yield_separates_different_zone_crop_season_groups():
    rows = [
        _eligible_row(zone_id=0, crop="maize", season="A"),
        _eligible_row(zone_id=1, crop="maize", season="A"),
        _eligible_row(zone_id=0, crop="beans", season="A"),
        _eligible_row(zone_id=0, crop="maize", season="B"),
    ]
    df = pd.DataFrame(rows)
    result = compute_attainable_yield(df, percentile=90, min_segments=1)
    assert len(result) == 4


def _district_yield_row(**overrides) -> dict:
    base = {
        "geo_level": "district",
        "geo_code": "11",
        "crop": "maize",
        "season": "A",
        "year": "2024",
        "yield_kg_ha": 800.0,
        "yield_kg_ha_ci_low": 700.0,
        "yield_kg_ha_ci_high": 900.0,
        "n_plots": 40,
        "n_segments": 25,
        "reliability": "ok",
    }
    base.update(overrides)
    return base


def _attainable_row(**overrides) -> dict:
    base = {
        "zone_id": 0,
        "crop": "maize",
        "season": "A",
        "attainable_yield_kg_ha": 1000.0,
        "n_plots": 50,
        "n_segments": 30,
        "reliability": "ok",
    }
    base.update(overrides)
    return base


def test_compute_yield_gap_matches_actual_to_its_district_zone():
    district_yield = pd.DataFrame(
        [
            _district_yield_row(),
            _district_yield_row(geo_level="national", geo_code="RWA", yield_kg_ha=900.0),
        ]
    )
    attainable_yield = pd.DataFrame([_attainable_row()])
    zones = pd.DataFrame({"nisr_district_code": [11], "zone_id": [0]})

    result = compute_yield_gap(district_yield, attainable_yield, zones)
    assert len(result) == 1  # national row excluded, not a district row
    row = result.iloc[0]
    assert row["actual_yield_kg_ha"] == 800.0
    assert row["actual_yield_kg_ha_ci_low"] == 700.0
    assert row["actual_yield_kg_ha_ci_high"] == 900.0
    assert row["attainable_yield_kg_ha"] == 1000.0
    assert row["yield_gap_kg_ha"] == pytest.approx(200.0)
    assert row["yield_gap_pct"] == pytest.approx(20.0)
    assert row["n_plots"] == 40  # the actual side's sample size, not attainable's
    assert row["reliability"] == "ok"


def test_compute_yield_gap_is_still_computed_when_actual_is_low_reliability():
    # golden rule 6: low-reliability cells are flagged and greyed out, not hidden. The
    # gap number must still be present; only the reliability flag changes.
    district_yield = pd.DataFrame([_district_yield_row(reliability="use_with_caution")])
    attainable_yield = pd.DataFrame([_attainable_row()])
    zones = pd.DataFrame({"nisr_district_code": [11], "zone_id": [0]})

    result = compute_yield_gap(district_yield, attainable_yield, zones)
    assert result.iloc[0]["yield_gap_kg_ha"] == pytest.approx(200.0)
    assert result.iloc[0]["reliability"] == "use_with_caution"


def test_compute_yield_gap_reliability_is_the_worse_of_actual_and_attainable():
    district_yield = pd.DataFrame([_district_yield_row(reliability="ok")])
    attainable_yield = pd.DataFrame([_attainable_row(reliability="suppressed")])
    zones = pd.DataFrame({"nisr_district_code": [11], "zone_id": [0]})

    result = compute_yield_gap(district_yield, attainable_yield, zones)
    assert result.iloc[0]["reliability"] == "suppressed"


def test_compute_yield_gap_null_only_when_no_matching_attainable_group():
    district_yield = pd.DataFrame([_district_yield_row(crop="sorghum")])
    attainable_yield = pd.DataFrame([_attainable_row(crop="maize")])  # no sorghum group
    zones = pd.DataFrame({"nisr_district_code": [11], "zone_id": [0]})

    result = compute_yield_gap(district_yield, attainable_yield, zones)
    assert pd.isna(result.iloc[0]["yield_gap_kg_ha"])
    assert pd.isna(result.iloc[0]["yield_gap_pct"])
    assert result.iloc[0]["reliability"] == "suppressed"
    assert result.iloc[0]["reliability"] == "suppressed"
