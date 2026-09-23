"""Unit tests for zonal stats parsing. No network access, no real ee calls."""

import inspect

import pytest

from agritwin.gee.extract import (
    fetch_rainfall_district_stats,
    parse_district_zonal_stats,
    parse_district_zonal_stats_hdx,
)


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


def test_hdx_zonal_stats_carries_nisr_district_code_not_gaul():
    fc = _fc(
        [
            {
                "properties": {
                    "nisr_district_code": 11,
                    "district_name": "Nyarugenge",
                    "province": "Kigali City",
                    "hdx_pcode": "RW11",
                    "mean": 0.62,
                }
            },
        ]
    )
    df = parse_district_zonal_stats_hdx(fc, value_field="mean", value_col="ndvi")
    assert list(df["nisr_district_code"]) == [11]
    assert list(df["district_name"]) == ["Nyarugenge"]
    assert "gaul_district_code" not in df.columns
    assert list(df["ndvi"]) == [0.62]


def test_rainfall_spatial_reducer_is_mean_not_sum():
    """Regression test: the spatial reduceRegions() reducer must average pixels
    (rainfall depth) not sum them. Summing scales the result with the number
    of pixels covering the district, which once produced seasonal totals up
    to ~43,000 mm for a country where a season's total is roughly 300-900 mm.
    The temporal .sum() over days within the date range stays correct.
    """
    source = inspect.getsource(fetch_rainfall_district_stats)
    reduce_call = source.split("reduceRegions", 1)[1]
    assert "ee.Reducer.mean()" in reduce_call
    assert "ee.Reducer.sum()" not in reduce_call
