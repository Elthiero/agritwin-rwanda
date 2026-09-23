"""
test_gee.py -- confirms Earth Engine works for AgriTwin before the pipeline is built.

First time only:
    pip install earthengine-api python-dotenv
    earthengine authenticate      # opens a browser, log in with the account tied to your project

Set GEE_PROJECT_ID in .env (copy .env.example if you haven't), then:
    python scripts/test_gee.py

Confirmed working against all six datasets on 23 September 2026. If any dataset
check fails, see docs/data/README.md for the registration and API-enable steps.
"""

import os
import sys

import ee
from dotenv import load_dotenv

from agritwin.gee.scaling import (
    MODIS_NDVI_SCALE,
    isda_ph,
)

load_dotenv()
PROJECT_ID = os.environ.get("GEE_PROJECT_ID")

if not PROJECT_ID or PROJECT_ID == "your-earth-engine-project-id":
    print(
        "GEE_PROJECT_ID is not set. Copy .env.example to .env and set GEE_PROJECT_ID "
        "to your real Earth Engine project ID, then run this script again.",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> None:
    print(f"Initializing Earth Engine with project: {PROJECT_ID}")
    ee.Initialize(project=PROJECT_ID)
    print("Initialized OK.\n")

    rwanda = ee.Geometry.Rectangle([28.85, -2.85, 30.90, -1.05])

    checks = [
        ("MODIS NDVI (MOD13Q1)", lambda: ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate("2024-01-01", "2024-02-01").filterBounds(rwanda).first()),
        ("Sentinel-2 SR", lambda: ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterDate("2024-01-01", "2024-02-01").filterBounds(rwanda).first()),
        ("CHIRPS Daily rainfall", lambda: ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filterDate("2024-01-01", "2024-01-05").filterBounds(rwanda).first()),
        ("ESA WorldCover", lambda: ee.ImageCollection("ESA/WorldCover/v200").first()),
        ("iSDAsoil pH", lambda: ee.Image("ISDASOIL/Africa/v1/ph")),
        ("iSDAsoil Total Nitrogen", lambda: ee.Image("ISDASOIL/Africa/v1/nitrogen_total")),
        ("iSDAsoil Organic Carbon", lambda: ee.Image("ISDASOIL/Africa/v1/carbon_organic")),
        ("SRTM elevation", lambda: ee.Image("USGS/SRTMGL1_003")),
    ]

    print("Checking dataset access:")
    for name, get_image in checks:
        try:
            img = get_image()
            band_names = img.bandNames().getInfo()
            print(f"  OK   {name:<28} bands: {band_names}")
        except Exception as e:
            print(f"  FAIL {name:<28} {e}")

    print("\nRunning a real reduceRegion (this is what costs EECU-hours):")
    ndvi_img = (
        ee.ImageCollection("MODIS/061/MOD13Q1")
        .filterDate("2024-01-01", "2024-02-01")
        .filterBounds(rwanda)
        .select("NDVI")
        .mean()
        .multiply(MODIS_NDVI_SCALE)
    )
    result = ndvi_img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=rwanda, scale=250, maxPixels=1e9,
    ).getInfo()
    print(f"  Mean NDVI over Rwanda, Jan 2024 (scaled): {result}")

    print("\nRunning a real iSDAsoil pH reduceRegion, back-transformed:")
    ph_img = ee.Image("ISDASOIL/Africa/v1/ph").select("mean_0_20")
    ph_raw = ph_img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=rwanda, scale=30, maxPixels=1e9,
    ).getInfo()
    raw_val = ph_raw.get("mean_0_20")
    if raw_val is not None:
        print(f"  Mean pH over Rwanda (0-20cm), raw={raw_val:.1f}, real={isda_ph(raw_val):.2f}")

    print(
        "\nAll checks complete. If everything above says OK and you got numbers, "
        "you're good to build the pipeline."
    )


if __name__ == "__main__":
    main()
