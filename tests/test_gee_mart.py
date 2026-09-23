"""Unit tests for GEE feature mart joins. No file I/O, synthetic fixtures."""

import pandas as pd

from agritwin.features.gee_mart import join_gee_features


def test_row_count_preserved_after_join():
    """Joining time-varying (season x year) with time-invariant (district)
    should preserve the row count of the time-varying data (season x year).
    """
    ndvi = pd.DataFrame(
        {
            "nisr_district_code": [11, 11, 43, 43],
            "district_name": ["Kigali", "Kigali", "Musanze", "Musanze"],
            "gaul_district_code": [1, 1, 2, 2],
            "year": [2024, 2024, 2024, 2024],
            "season": ["A", "B", "A", "B"],
            "ndvi_mean": [0.62, 0.71, 0.68, 0.75],
        }
    )
    rainfall = pd.DataFrame(
        {
            "nisr_district_code": [11, 11, 43, 43],
            "district_name": ["Kigali", "Kigali", "Musanze", "Musanze"],
            "gaul_district_code": [1, 1, 2, 2],
            "year": [2024, 2024, 2024, 2024],
            "season": ["A", "B", "A", "B"],
            "rainfall_mm": [450.0, 520.0, 480.0, 550.0],
        }
    )
    cropland = pd.DataFrame(
        {
            "nisr_district_code": [11, 43],
            "district_name": ["Kigali", "Musanze"],
            "gaul_district_code": [1, 2],
            "cropland_fraction": [0.45, 0.38],
        }
    )
    soil = pd.DataFrame(
        {
            "nisr_district_code": [11, 43],
            "district_name": ["Kigali", "Musanze"],
            "gaul_district_code": [1, 2],
            "soil_ph": [6.2, 5.8],
            "soil_nitrogen": [1.2, 1.5],
            "soil_carbon": [15.0, 18.0],
            "soil_texture_class": [4.0, 6.0],
        }
    )
    result = join_gee_features(ndvi, rainfall, cropland, soil)
    assert len(result) == 4
    assert list(result.columns) == [
        "nisr_district_code",
        "district_name",
        "gaul_district_code",
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


def test_broadcast_time_invariant_across_seasons_and_years():
    """A single district row in cropland/soil should appear in every
    (season, year) combination of the time-varying data.
    """
    ndvi = pd.DataFrame(
        {
            "nisr_district_code": [11, 11],
            "district_name": ["Kigali", "Kigali"],
            "gaul_district_code": [1, 1],
            "year": [2024, 2025],
            "season": ["A", "A"],
            "ndvi_mean": [0.62, 0.65],
        }
    )
    rainfall = pd.DataFrame(
        {
            "nisr_district_code": [11, 11],
            "district_name": ["Kigali", "Kigali"],
            "gaul_district_code": [1, 1],
            "year": [2024, 2025],
            "season": ["A", "A"],
            "rainfall_mm": [450.0, 460.0],
        }
    )
    cropland = pd.DataFrame(
        {
            "nisr_district_code": [11],
            "district_name": ["Kigali"],
            "gaul_district_code": [1],
            "cropland_fraction": [0.45],
        }
    )
    soil = pd.DataFrame(
        {
            "nisr_district_code": [11],
            "district_name": ["Kigali"],
            "gaul_district_code": [1],
            "soil_ph": [6.2],
            "soil_nitrogen": [1.2],
            "soil_carbon": [15.0],
            "soil_texture_class": [4.0],
        }
    )
    result = join_gee_features(ndvi, rainfall, cropland, soil)
    assert len(result) == 2
    assert (result["cropland_fraction"] == 0.45).all()
    assert (result["soil_ph"] == 6.2).all()


def test_no_nulls_in_key_columns():
    """All key columns (district, year, season) must be non-null after join."""
    ndvi = pd.DataFrame(
        {
            "nisr_district_code": [11],
            "district_name": ["Kigali"],
            "gaul_district_code": [1],
            "year": [2024],
            "season": ["A"],
            "ndvi_mean": [0.62],
        }
    )
    rainfall = pd.DataFrame(
        {
            "nisr_district_code": [11],
            "district_name": ["Kigali"],
            "gaul_district_code": [1],
            "year": [2024],
            "season": ["A"],
            "rainfall_mm": [450.0],
        }
    )
    cropland = pd.DataFrame(
        {
            "nisr_district_code": [11],
            "district_name": ["Kigali"],
            "gaul_district_code": [1],
            "cropland_fraction": [0.45],
        }
    )
    soil = pd.DataFrame(
        {
            "nisr_district_code": [11],
            "district_name": ["Kigali"],
            "gaul_district_code": [1],
            "soil_ph": [6.2],
            "soil_nitrogen": [1.2],
            "soil_carbon": [15.0],
            "soil_texture_class": [4.0],
        }
    )
    result = join_gee_features(ndvi, rainfall, cropland, soil)
    assert not result[
        ["nisr_district_code", "district_name", "gaul_district_code", "year", "season"]
    ].isna().any().any()
