"""Unit tests for the GAUL district boundary parser. No network access, no real ee calls.

Fixtures use district_name/gaul_district_code (not ADM2_NAME/ADM2_CODE): that's
the renamed shape rwanda_districts_fc() actually produces via .select() before
getInfo(), and the shape parse_gaul_features must parse. A prior version of
this file used the raw GAUL names and so never caught a rename mismatch
between boundaries.py and extract.py's parser.
"""

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
            {
                "properties": {"district_name": "Kigali", "gaul_district_code": 1},
                "geometry": SQUARE,
            },
            {
                "properties": {"district_name": "Musanze", "gaul_district_code": 2},
                "geometry": SQUARE,
            },
            {
                "properties": {"district_name": "Huye", "gaul_district_code": 3},
                "geometry": SQUARE,
            },
        ]
    )
    gdf = parse_gaul_features(fc)
    assert len(gdf) == 3
    assert list(gdf["district_name"]) == ["Kigali", "Musanze", "Huye"]
    assert list(gdf["gaul_district_code"]) == [1, 2, 3]


def test_missing_code_raises():
    fc = _fc([{"properties": {"district_name": "Kigali"}, "geometry": SQUARE}])
    with pytest.raises(ValueError, match="district_name or gaul_district_code"):
        parse_gaul_features(fc)


def test_missing_name_raises():
    fc = _fc([{"properties": {"gaul_district_code": 1}, "geometry": SQUARE}])
    with pytest.raises(ValueError, match="district_name or gaul_district_code"):
        parse_gaul_features(fc)
