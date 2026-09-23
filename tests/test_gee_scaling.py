"""Unit tests for confirmed Earth Engine scale factors. No network access, no real ee calls."""

import math

from agritwin.gee.scaling import (
    CHIRPS_SCALE,
    MODIS_NDVI_SCALE,
    SENTINEL2_SR_SCALE,
    isda_carbon_organic,
    isda_nitrogen_total,
    isda_ph,
)


def test_modis_ndvi_scale_brings_raw_into_valid_range():
    raw = 6067.79  # observed raw value, Rwanda cropland, Jan 2024
    scaled = raw * MODIS_NDVI_SCALE
    assert -1.0 <= scaled <= 1.0
    assert round(scaled, 3) == 0.607


def test_sentinel2_sr_scale_is_ten_thousandth():
    assert SENTINEL2_SR_SCALE == 0.0001


def test_chirps_scale_is_identity():
    assert CHIRPS_SCALE == 1.0


def test_isda_ph_back_transform():
    # raw 65 -> pH 6.5, a plausible Rwanda topsoil value
    assert isda_ph(65) == 6.5


def test_isda_nitrogen_back_transform_matches_formula():
    raw = 150.0
    expected = math.exp(raw / 100.0) - 1.0
    assert isda_nitrogen_total(raw) == expected


def test_isda_carbon_back_transform_matches_formula():
    raw = 40.0
    expected = math.exp(raw / 10.0) - 1.0
    assert isda_carbon_organic(raw) == expected
