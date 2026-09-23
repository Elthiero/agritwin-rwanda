"""Unit tests for zonal stats parsing. No network access, no real ee calls."""

import pytest

from agritwin.gee.extract import parse_district_zonal_stats


def _fc(features):
    return {"type": "FeatureCollection", "features": features}


def test_row_count_preserved_and_values_mapped():
    fc = _fc(
        [
            {"properties": {"district_name": "Kigali", "gaul_district_code": 1, "mean": 0.62}},
            {"properties": {"district_name": "Musanze", "gaul_district_code": 2, "mean": 0.71}},
        ]
    )
    df = parse_district_zonal_stats(fc, value_field="mean", value_col="ndvi")
    assert len(df) == 2
    assert list(df["district_name"]) == ["Kigali", "Musanze"]
    assert list(df["ndvi"]) == [0.62, 0.71]


def test_district_with_no_valid_pixels_keeps_null_row():
    fc = _fc(
        [
            {"properties": {"district_name": "Kigali", "gaul_district_code": 1, "mean": 0.62}},
            # fully cloud-masked district: reducer returns no "mean" key at all
            {"properties": {"district_name": "Musanze", "gaul_district_code": 2}},
        ]
    )
    df = parse_district_zonal_stats(fc, value_field="mean", value_col="ndvi")
    assert len(df) == 2
    assert df.loc[df["district_name"] == "Musanze", "ndvi"].isna().all()


def test_raw_gaul_property_names_are_rejected():
    """Regression test: reduceRegions() carries through whatever property names
    the input district FeatureCollection has. If rwanda_districts_fc() ever
    stops renaming ADM2_NAME/ADM2_CODE to district_name/gaul_district_code
    (the bug this guards against), this must fail loudly instead of silently
    dropping every district.
    """
    fc = _fc([{"properties": {"ADM2_NAME": "Kigali", "ADM2_CODE": 1, "mean": 0.62}}])
    with pytest.raises(KeyError, match="district_name"):
        parse_district_zonal_stats(fc, value_field="mean", value_col="ndvi")
