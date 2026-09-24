"""Join Earth Engine district-level features into one mart table.

Combines NDVI and rainfall (which vary by season and year) with cropland
and soil (which are static per district) into a single district x season x
year feature table.
"""

from __future__ import annotations

from pathlib import Path

import loguru
import pandas as pd

logger = loguru.logger

DATA_EXTERNAL = Path(__file__).resolve().parents[3] / "data" / "external"


def load_gee_outputs() -> dict[str, pd.DataFrame]:
    """Load the four GEE extraction CSVs from data/external/gee/."""
    gee_dir = DATA_EXTERNAL / "gee"
    return {
        "ndvi": pd.read_csv(gee_dir / "ndvi_district_season.csv"),
        "rainfall": pd.read_csv(gee_dir / "rainfall_district_season.csv"),
        "cropland": pd.read_csv(gee_dir / "cropland_fraction_district.csv"),
        "soil": pd.read_csv(gee_dir / "soil_district.csv"),
    }


def join_gee_features(
    ndvi_df: pd.DataFrame,
    rainfall_df: pd.DataFrame,
    cropland_df: pd.DataFrame,
    soil_df: pd.DataFrame,
) -> pd.DataFrame:
    """Join time-varying NDVI/rainfall with time-invariant cropland/soil.

    ndvi_df, rainfall_df: 420 rows each, one per (district, season, year).
    cropland_df, soil_df: 30 rows each, one per district. Broadcast to all
    season/year combinations when joined.

    Returns a single 420-row DataFrame with columns:
    nisr_district_code, district_name, year, season, ndvi_mean, rainfall_mm,
    cropland_fraction, soil_ph, soil_nitrogen, soil_carbon, soil_texture_class.
    All four inputs are already keyed by nisr_district_code natively: gee/run.py
    extracts every GEE dataset over boundaries.hdx_districts_fc() (HDX district
    polygons, which carry nisr_district_code directly), not the GAUL boundaries used
    only for the /districts boundary GeoJSON. There is no gaul_district_code here and
    no crosswalk join needed (see docs/decisions.md 2026-09-23).
    """
    district_keys = ["nisr_district_code", "district_name"]
    merged = ndvi_df.merge(rainfall_df, on=district_keys + ["year", "season"])
    merged = merged.merge(cropland_df, on=district_keys)
    merged = merged.merge(soil_df, on=district_keys)
    return merged[
        [
            "nisr_district_code",
            "district_name",
            "year",
            "season",
            "ndvi_mean",
            "rainfall_mm",
            "cropland_fraction",
            "soil_ph",
            "soil_nitrogen",
            "soil_carbon",
            "soil_texture_class",
        ]
    ]


def write_gee_mart(df: pd.DataFrame, output_path: Path) -> None:
    """Write the joined GEE feature mart to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"wrote {len(df)} rows to {output_path}")
