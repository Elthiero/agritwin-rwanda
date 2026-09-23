"""Scale factors and band choices for every Earth Engine dataset AgriTwin uses.

Confirmed by an actual ee.Initialize() + dataset access test on 23 September 2026
(see scripts/test_gee.py). Do not hand-roll these numbers elsewhere; import from
here so a correction only has to happen in one place.

The single most common bug in a pipeline like this is forgetting a scale factor
and silently working with, e.g., MODIS NDVI values in the 0 to 10000 range
instead of -1 to 1. Every extraction function in this module must apply the
matching factor below before returning a DataFrame.
"""

from __future__ import annotations

import math

import ee

# MODIS MOD13Q1: NDVI and EVI stored as int16, scaled by 10000.
MODIS_NDVI_SCALE = 0.0001

# Sentinel-2 SR (harmonized): reflectance bands stored as int, scaled by 10000.
SENTINEL2_SR_SCALE = 0.0001

# CHIRPS daily: already mm/day, no rescale needed.
CHIRPS_SCALE = 1.0

# iSDAsoil back-transforms. Each returns the real-world value from the raw band.
def isda_ph(raw: float) -> float:
    """pH: raw / 10."""
    return raw / 10.0


def isda_nitrogen_total(raw: float) -> float:
    """Total nitrogen, g/kg: exp(raw / 100) - 1."""
    return math.exp(raw / 100.0) - 1.0


def isda_carbon_organic(raw: float) -> float:
    """Organic carbon, g/kg: exp(raw / 10) - 1."""
    return math.exp(raw / 10.0) - 1.0


def scale_modis_ndvi(img: ee.Image) -> ee.Image:
    """Apply the MOD13Q1 scale factor to an NDVI/EVI image."""
    return img.multiply(MODIS_NDVI_SCALE)


def scale_sentinel2_sr(img: ee.Image) -> ee.Image:
    """Apply the Sentinel-2 SR scale factor to reflectance bands."""
    return img.multiply(SENTINEL2_SR_SCALE)


def scale_isda_image_ee(img: ee.Image, formula: str) -> ee.Image:
    """Apply an iSDAsoil back-transform to an ee.Image server-side.

    formula: one of "ph", "nitrogen_total", "carbon_organic".
    """
    if formula == "ph":
        return img.divide(10.0)
    if formula == "nitrogen_total":
        return img.divide(100.0).exp().subtract(1.0)
    if formula == "carbon_organic":
        return img.divide(10.0).exp().subtract(1.0)
    raise ValueError(f"unknown iSDAsoil formula: {formula}")
