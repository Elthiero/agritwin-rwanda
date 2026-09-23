"""Unit tests for the GAUL district boundary parser. No network access, no real ee calls."""

import pytest

from agritwin.gee.boundaries import parse_gaul_features

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[29.0, -2.0], [29.1, -2.0], [29.1, -1.9], [29.0, -1.9], [29.0, -2.0]]],
}


def _fc(features):
    return {"type": "FeatureCollection", "features": features}


def test_row_count_preserved():
    fc = _fc(
        [
            {"properties": {"ADM2_NAME": "Kigali", "ADM2_CODE": 1}, "geometry": SQUARE},
            {"properties": {"ADM2_NAME": "Musanze", "ADM2_CODE": 2}, "geometry": SQUARE},
            {"properties": {"ADM2_NAME": "Huye", "ADM2_CODE": 3}, "geometry": SQUARE},
        ]
    )
    gdf = parse_gaul_features(fc)
    assert len(gdf) == 3
    assert list(gdf["district_name"]) == ["Kigali", "Musanze", "Huye"]
    assert list(gdf["gaul_district_code"]) == [1, 2, 3]


def test_missing_code_raises():
    fc = _fc([{"properties": {"ADM2_NAME": "Kigali"}, "geometry": SQUARE}])
    with pytest.raises(ValueError, match="ADM2_NAME or ADM2_CODE"):
        parse_gaul_features(fc)


def test_missing_name_raises():
    fc = _fc([{"properties": {"ADM2_CODE": 1}, "geometry": SQUARE}])
    with pytest.raises(ValueError, match="ADM2_NAME or ADM2_CODE"):
        parse_gaul_features(fc)
