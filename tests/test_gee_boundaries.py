"""Unit tests for the GAUL district boundary parser. No network access, no real ee calls.

Fixtures use district_name/gaul_district_code (not ADM2_NAME/ADM2_CODE): that's
the renamed shape rwanda_districts_fc() actually produces via .select() before
getInfo(), and the shape parse_gaul_features must parse. A prior version of
this file used the raw GAUL names and so never caught a rename mismatch
between boundaries.py and extract.py's parser.
"""

import pytest

from agritwin.gee.boundaries import (
    load_district_crosswalk,
    load_hdx_districts_geojson,
    parse_gaul_features,
)

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


def test_hdx_districts_geojson_has_thirty_features_with_expected_properties():
    # Local file read only, no network/ee calls: confirms the committed boundary
    # file (built from the HDX download, see docs/data-sources.md) is loadable and
    # matches the crosswalk this data was built from.
    geojson = load_hdx_districts_geojson()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 30
    props = geojson["features"][0]["properties"]
    assert {"nisr_district_code", "district_name", "province", "hdx_pcode"} <= set(props)


def test_hdx_districts_geojson_codes_match_crosswalk():
    geojson = load_hdx_districts_geojson()
    crosswalk = load_district_crosswalk()
    geojson_codes = {f["properties"]["nisr_district_code"] for f in geojson["features"]}
    assert geojson_codes == set(crosswalk["nisr_district_code"])
