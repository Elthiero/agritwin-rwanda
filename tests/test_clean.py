"""Unit tests for the clean module. Synthetic fixtures only, no data/raw or data/staging reads."""

from __future__ import annotations

import pandas as pd
import pytest

from agritwin.clean.core import (
    FLAG_ABOVE_CAP,
    FLAG_AREA_TOO_SMALL,
    FLAG_MISSING_DATA,
    FLAG_NOT_PURE_STAND,
    FLAG_NOT_SSF,
    FLAG_OK,
    FLAG_OUTLIER_LOW,
    FLAG_ZERO_AREA,
    clean_plot_crop,
    compute_yield_kg_ha,
    resolve_ssf,
)

SETTINGS = {
    "yield_qc": {
        "min_plot_area_sqm": 20,
        "trim_lower_pct": 0.5,
        "trim_upper_pct": 99.5,
        "max_yield_kg_ha": {"maize": 12000},
    }
}

VALUE_LABELS = pd.DataFrame(
    [
        {
            "year": 2024,
            "variable": "farmer_type",
            "code": 1,
            "label": "Small scale farmer as individual",
        },
        {
            "year": 2024,
            "variable": "farmer_type",
            "code": 3,
            "label": "Large scale farmer as individual",
        },
    ]
)


def _row(**overrides) -> dict:
    base = {
        "year": 2024,
        "season": "A",
        "farmer_type": 1,
        "plot_area_sqm": 1000.0,
        "plot_area_ha": 0.1,
        "pure_stand": True,
        "crop": "maize",
        "harvest_kg": 500.0,
    }
    base.update(overrides)
    return base


def test_row_count_preserved():
    df = pd.DataFrame([_row(), _row(harvest_kg=200.0)])
    out = clean_plot_crop(df, VALUE_LABELS, SETTINGS)
    assert len(out) == 2


def test_eligible_row_flagged_ok_with_correct_yield():
    df = pd.DataFrame([_row(harvest_kg=500.0, plot_area_ha=0.1)])
    out = clean_plot_crop(df, VALUE_LABELS, SETTINGS)
    assert out.iloc[0]["qc_flag"] == FLAG_OK
    assert out.iloc[0]["yield_kg_ha"] == pytest.approx(5000.0)


def test_missing_harvest_flagged_and_yield_null():
    df = pd.DataFrame([_row(harvest_kg=None)])
    out = clean_plot_crop(df, VALUE_LABELS, SETTINGS)
    assert out.iloc[0]["qc_flag"] == FLAG_MISSING_DATA
    assert pd.isna(out.iloc[0]["yield_kg_ha"])


def test_missing_area_flagged_and_yield_null():
    df = pd.DataFrame([_row(plot_area_sqm=None, plot_area_ha=None)])
    out = clean_plot_crop(df, VALUE_LABELS, SETTINGS)
    assert out.iloc[0]["qc_flag"] == FLAG_MISSING_DATA
    assert pd.isna(out.iloc[0]["yield_kg_ha"])


def test_zero_area_flagged_and_yield_null_not_inf():
    df = pd.DataFrame([_row(plot_area_sqm=0.0, plot_area_ha=0.0)])
    out = clean_plot_crop(df, VALUE_LABELS, SETTINGS)
    assert out.iloc[0]["qc_flag"] == FLAG_ZERO_AREA
    assert pd.isna(out.iloc[0]["yield_kg_ha"])


def test_area_too_small_flagged_but_yield_still_computed():
    df = pd.DataFrame([_row(plot_area_sqm=10.0, plot_area_ha=0.001, harvest_kg=5.0)])
    out = clean_plot_crop(df, VALUE_LABELS, SETTINGS)
    assert out.iloc[0]["qc_flag"] == FLAG_AREA_TOO_SMALL
    assert out.iloc[0]["yield_kg_ha"] == pytest.approx(5000.0)


def test_not_pure_stand_flagged():
    df = pd.DataFrame([_row(pure_stand=False)])
    out = clean_plot_crop(df, VALUE_LABELS, SETTINGS)
    assert out.iloc[0]["qc_flag"] == FLAG_NOT_PURE_STAND


def test_not_ssf_flagged_for_lsf_code():
    df = pd.DataFrame([_row(farmer_type=3)])  # code 3 = "Large scale farmer" this year
    out = clean_plot_crop(df, VALUE_LABELS, SETTINGS)
    assert out.iloc[0]["qc_flag"] == FLAG_NOT_SSF


def test_not_ssf_flagged_for_unresolvable_farmer_type():
    df = pd.DataFrame([_row(farmer_type=99)])  # no label for this code
    out = clean_plot_crop(df, VALUE_LABELS, SETTINGS)
    assert out.iloc[0]["qc_flag"] == FLAG_NOT_SSF


def test_above_plausibility_cap_flagged():
    df = pd.DataFrame([_row(harvest_kg=2000.0, plot_area_ha=0.1)])  # 20,000 kg/ha > 12,000 cap
    out = clean_plot_crop(df, VALUE_LABELS, SETTINGS)
    assert out.iloc[0]["qc_flag"] == FLAG_ABOVE_CAP


def test_outlier_trim_flags_extreme_values_within_eligible_group():
    # 100 normal rows tightly clustered around 5000 kg/ha, one very low and one very high
    # outlier, all eligible (pure-stand, SSF, same crop/season/year) so the trim group is
    # exactly them. A large normal cluster keeps the 0.5th/99.5th percentile bounds well
    # inside the cluster regardless of interpolation method, unlike a tiny n.
    rows = [_row(harvest_kg=500.0 + (i % 5), plot_area_ha=0.1) for i in range(100)]
    rows.append(_row(harvest_kg=1.0, plot_area_ha=0.1))  # ~10 kg/ha: extreme low
    rows.append(_row(harvest_kg=50000.0, plot_area_ha=0.1))  # 500,000 kg/ha: extreme high
    df = pd.DataFrame(rows)
    out = clean_plot_crop(df, VALUE_LABELS, SETTINGS)
    assert out.iloc[-2]["qc_flag"] == FLAG_OUTLIER_LOW
    assert out.iloc[-1]["qc_flag"] == FLAG_ABOVE_CAP  # 500,000 kg/ha also exceeds the 12,000 cap
    assert (out.iloc[:100]["qc_flag"] == FLAG_OK).all()


def test_resolve_ssf_distinguishes_codes_and_years():
    lookup = resolve_ssf(VALUE_LABELS)
    assert lookup[(2024, 1)] is True
    assert lookup[(2024, 3)] is False
    assert (2024, 99) not in lookup


def test_compute_yield_kg_ha_is_null_safe_series_op():
    df = pd.DataFrame(
        [
            _row(harvest_kg=1000.0, plot_area_ha=0.5),
            _row(harvest_kg=None, plot_area_ha=0.5),
            _row(harvest_kg=1000.0, plot_area_ha=0.0),
        ]
    )
    result = compute_yield_kg_ha(df)
    assert result.iloc[0] == pytest.approx(2000.0)
    assert pd.isna(result.iloc[1])
    assert pd.isna(result.iloc[2])
