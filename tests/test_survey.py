"""Unit tests for the survey module. Synthetic fixtures only, no data/raw or data/staging
reads. Uses small, deterministic samp_weight values so point estimates are checkable by
hand against the Horvitz-Thompson expansion formula (sum(w*y)), independent of samplics'
internal Taylor-linearization implementation for variance.
"""

from __future__ import annotations

import pandas as pd
import pytest

from agritwin.survey.core import (
    add_reliability_flag,
    build_psu_key,
    canonicalize_stratum,
    estimate_ratio,
    prepare_for_estimation,
)


def _row(**overrides) -> dict:
    base = {
        "year": 2024,
        "season": "A",
        "district_code": 11.0,
        "province_code": 1.0,
        "stratum": 10.0,
        "segment_id": 1,
        "plot_id": 1,
        "crop": "maize",
        "pure_stand": True,
        "qc_flag": "ok",
        "weight": 1.0,
        "harvest_kg": 500.0,
        "plot_area_ha": 0.1,
    }
    base.update(overrides)
    return base


def test_canonicalize_stratum_differs_by_year_for_same_code():
    df = pd.DataFrame([_row(year=2019, stratum=11.0), _row(year=2020, stratum=10.0)])
    result = canonicalize_stratum(df)
    assert list(result) == ["hillside", "hillside"]


def test_canonicalize_stratum_2021_code_11_treated_as_hillside():
    # See docs/survey-design.md: 2021 season-B-only code 11, evidenced as equivalent to
    # code 10 (season A), not left as an unlabeled separate category.
    df = pd.DataFrame([_row(year=2021, season="B", stratum=11.0)])
    assert list(canonicalize_stratum(df)) == ["hillside"]


def test_canonicalize_stratum_unknown_code_is_null_not_guessed():
    df = pd.DataFrame([_row(year=2024, stratum=999.0)])
    result = canonicalize_stratum(df)
    assert result.isna().all()


def test_build_psu_key_distinguishes_same_segment_id_across_years():
    df = pd.DataFrame([_row(year=2019, segment_id=5), _row(year=2024, segment_id=5)])
    keys = build_psu_key(df)
    assert keys.iloc[0] != keys.iloc[1]


def test_prepare_for_estimation_excludes_non_ok_null_crop_and_null_weight():
    df = pd.DataFrame(
        [
            _row(),  # eligible
            _row(qc_flag="not_pure_stand"),  # excluded: not ok
            _row(crop=None),  # excluded: null crop
            _row(weight=None),  # excluded: null weight
            _row(weight=0.0),  # excluded: non-positive weight
        ]
    )
    eligible = prepare_for_estimation(df)
    assert len(eligible) == 1
    assert {"stratum_canonical", "psu_key", "design_block"} <= set(eligible.columns)
    assert eligible.iloc[0]["design_block"] == "plot"


def test_estimate_ratio_point_estimates_match_horvitz_thompson_by_hand():
    rows = [
        _row(segment_id=1, plot_id=1, weight=2.0, harvest_kg=400.0, plot_area_ha=0.1),
        _row(segment_id=1, plot_id=2, weight=2.0, harvest_kg=600.0, plot_area_ha=0.2),
        _row(segment_id=2, plot_id=3, weight=3.0, harvest_kg=300.0, plot_area_ha=0.1),
        _row(segment_id=2, plot_id=4, weight=3.0, harvest_kg=300.0, plot_area_ha=0.1),
    ]
    df = pd.DataFrame(rows)
    eligible = prepare_for_estimation(df)
    result = estimate_ratio(eligible, ["crop", "district_code", "season", "year"])

    expected_production = 2 * 400 + 2 * 600 + 3 * 300 + 3 * 300
    expected_area = 2 * 0.1 + 2 * 0.2 + 3 * 0.1 + 3 * 0.1
    assert len(result) == 1
    assert result.iloc[0]["total_production_kg"] == pytest.approx(expected_production)
    assert result.iloc[0]["total_area_ha"] == pytest.approx(expected_area)
    assert result.iloc[0]["yield_kg_ha"] == pytest.approx(expected_production / expected_area)
    assert result.iloc[0]["n_plots"] == 4
    assert result.iloc[0]["n_segments"] == 2


def test_estimate_ratio_is_reproducible_from_the_same_input():
    rows = [
        _row(segment_id=1, plot_id=1, weight=1.5),
        _row(segment_id=2, plot_id=2, weight=2.5, harvest_kg=800.0, plot_area_ha=0.2),
    ]
    df = pd.DataFrame(rows)
    eligible = prepare_for_estimation(df)
    result_a = estimate_ratio(eligible, ["crop", "district_code", "season", "year"])
    result_b = estimate_ratio(eligible, ["crop", "district_code", "season", "year"])
    pd.testing.assert_frame_equal(
        result_a.sort_values("crop").reset_index(drop=True),
        result_b.sort_values("crop").reset_index(drop=True),
    )


def test_estimate_ratio_handles_all_zero_production_domain_without_crashing():
    # A domain where every sampled plot reports zero harvest (total crop failure):
    # samplics' internal CV computation divides by the point estimate unconditionally
    # and raises ZeroDivisionError on 0.0/0.0 if this isn't handled explicitly.
    rows = [
        _row(segment_id=1, plot_id=1, harvest_kg=0.0),
        _row(segment_id=2, plot_id=2, harvest_kg=0.0),
    ]
    df = pd.DataFrame(rows)
    eligible = prepare_for_estimation(df)
    result = estimate_ratio(eligible, ["crop", "district_code", "season", "year"])
    assert len(result) == 1
    assert result.iloc[0]["total_production_kg"] == 0.0
    assert result.iloc[0]["yield_kg_ha"] == 0.0
    assert pd.isna(result.iloc[0]["yield_kg_ha_cv"])  # undefined (0/0), not approximated


def test_estimate_ratio_keeps_2019_and_2020_as_separate_design_blocks():
    # 2019 is segment-level weighted, 2020+ is plot-level (docs/decisions.md 2026-09-23).
    # Estimating both years together must not raise even though their design differs,
    # since each design block is estimated independently inside estimate_ratio.
    rows = [
        _row(year=2019, stratum=11.0, segment_id=1, plot_id=1),
        _row(year=2019, stratum=11.0, segment_id=2, plot_id=2),
        _row(year=2024, stratum=10.0, segment_id=1, plot_id=1),
        _row(year=2024, stratum=10.0, segment_id=2, plot_id=2),
    ]
    df = pd.DataFrame(rows)
    eligible = prepare_for_estimation(df)
    result = estimate_ratio(eligible, ["crop", "district_code", "season", "year"])
    assert set(result["year"]) == {"2019", "2024"}


def test_add_reliability_flag_suppresses_below_min_segments():
    df = pd.DataFrame(
        [
            {"n_segments": 3, "yield_kg_ha_cv": 0.05},
            {"n_segments": 50, "yield_kg_ha_cv": 0.05},
        ]
    )
    out = add_reliability_flag(df, cv_max=0.20, min_segments=10)
    assert list(out["reliability"]) == ["suppressed", "ok"]


def test_add_reliability_flag_flags_high_cv_as_use_with_caution():
    df = pd.DataFrame(
        [
            {"n_segments": 50, "yield_kg_ha_cv": 0.35},
            {"n_segments": 50, "yield_kg_ha_cv": 0.05},
        ]
    )
    out = add_reliability_flag(df, cv_max=0.20, min_segments=10)
    assert list(out["reliability"]) == ["use_with_caution", "ok"]


def test_add_reliability_flag_suppression_takes_priority_over_cv():
    df = pd.DataFrame([{"n_segments": 2, "yield_kg_ha_cv": 0.90}])
    out = add_reliability_flag(df, cv_max=0.20, min_segments=10)
    assert list(out["reliability"]) == ["suppressed"]


def test_weights_are_non_null_and_positive_after_prepare_for_estimation():
    df = pd.DataFrame(
        [_row(), _row(weight=None), _row(weight=0.0), _row(weight=-1.0)]
    )
    eligible = prepare_for_estimation(df)
    assert eligible["weight"].notna().all()
    assert (eligible["weight"] > 0).all()
