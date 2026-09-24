"""Runner for Earth Engine extraction steps. Invoked by `make gee` (python -m agritwin.gee.run)."""

from __future__ import annotations

import os
from functools import reduce
from pathlib import Path

import loguru
import pandas as pd
from dotenv import load_dotenv

from agritwin.config import load_settings
from agritwin.gee.boundaries import (
    fetch_rwanda_districts,
    hdx_districts_fc,
    parse_gaul_features,
    write_boundaries,
)
from agritwin.gee.extract import (
    fetch_cropland_fraction_district_stats,
    fetch_ndvi_climatology_stats,
    fetch_ndvi_district_stats,
    fetch_ndvi_peak_district_stats,
    fetch_rainfall_climatology_stats,
    fetch_rainfall_district_stats,
    fetch_soil_district_stats,
    parse_district_zonal_stats_hdx,
)
from agritwin.gee.periods import partial_season_date_range, season_date_range

DATA_EXTERNAL = Path(__file__).resolve().parents[3] / "data" / "external"

logger = loguru.logger

SOIL_DATASETS = ["isda_ph", "isda_nitrogen", "isda_carbon", "isda_texture"]
SOIL_VALUE_COLS = {
    "isda_ph": "soil_ph",
    "isda_nitrogen": "soil_nitrogen",
    "isda_carbon": "soil_carbon",
    "isda_texture": "soil_texture_class",
}


def run_boundaries() -> None:
    project_id = os.environ["GEE_PROJECT_ID"]
    fc_geojson = fetch_rwanda_districts(project_id)
    gdf = parse_gaul_features(fc_geojson)
    write_boundaries(gdf, DATA_EXTERNAL / "boundaries" / "rwanda_districts.geojson")


def run_ndvi_rainfall() -> None:
    """Mean NDVI and total rainfall per district x season x year, over the settings scope."""
    project_id = os.environ["GEE_PROJECT_ID"]
    settings = load_settings()
    districts_fc = hdx_districts_fc(project_id)
    scale = settings["gee_extraction"]["scale_m"]
    season_windows = settings["season_windows"]

    ndvi_rows, rainfall_rows = [], []
    for year in settings["scope"]["years"]:
        for season in settings["scope"]["seasons"]:
            start_date, end_date = season_date_range(year, season, season_windows)

            ndvi_fc = fetch_ndvi_district_stats(districts_fc, start_date, end_date, scale["ndvi"])
            ndvi_df = parse_district_zonal_stats_hdx(
                ndvi_fc, value_field="mean", value_col="ndvi_mean"
            )
            ndvi_df["year"], ndvi_df["season"] = year, season
            ndvi_rows.append(ndvi_df)

            rain_fc = fetch_rainfall_district_stats(
                districts_fc, start_date, end_date, scale["rainfall"]
            )
            rain_df = parse_district_zonal_stats_hdx(
                rain_fc, value_field="mean", value_col="rainfall_mm"
            )
            rain_df["year"], rain_df["season"] = year, season
            rainfall_rows.append(rain_df)

    _write_csv(pd.concat(ndvi_rows, ignore_index=True), "ndvi_district_season.csv")
    _write_csv(pd.concat(rainfall_rows, ignore_index=True), "rainfall_district_season.csv")


def run_cropland() -> None:
    """Cropland pixel fraction per district (single ESA WorldCover 2021 snapshot)."""
    project_id = os.environ["GEE_PROJECT_ID"]
    settings = load_settings()
    districts_fc = hdx_districts_fc(project_id)
    scale = settings["gee_extraction"]["scale_m"]["cropland"]

    fc = fetch_cropland_fraction_district_stats(districts_fc, scale)
    df = parse_district_zonal_stats_hdx(fc, value_field="mean", value_col="cropland_fraction")
    _write_csv(df, "cropland_fraction_district.csv")


def run_soil() -> None:
    """Soil pH, nitrogen, carbon and texture class per district (iSDAsoil snapshot)."""
    project_id = os.environ["GEE_PROJECT_ID"]
    settings = load_settings()
    districts_fc = hdx_districts_fc(project_id)
    scale = settings["gee_extraction"]["scale_m"]["soil"]

    tables = []
    for dataset_name in SOIL_DATASETS:
        value_field = "mode" if dataset_name == "isda_texture" else "mean"
        fc = fetch_soil_district_stats(districts_fc, dataset_name, scale)
        df = parse_district_zonal_stats_hdx(
            fc, value_field=value_field, value_col=SOIL_VALUE_COLS[dataset_name]
        )
        tables.append(df)

    merged = reduce(
        lambda left, right: left.merge(right, on=["nisr_district_code", "district_name"]), tables
    )
    _write_csv(merged, "soil_district.csv")


def run_climatology() -> None:
    """Long-run NDVI and rainfall climatology per district x season, for the nowcast's
    anomaly features (docs/AgriTwin_Master_Build_Guide.md section 4.3)."""
    project_id = os.environ["GEE_PROJECT_ID"]
    settings = load_settings()
    districts_fc = hdx_districts_fc(project_id)
    scale = settings["gee_extraction"]["scale_m"]
    season_windows = settings["season_windows"]
    nowcast_cfg = settings["nowcast"]
    ndvi_start, ndvi_end = nowcast_cfg["ndvi_climatology"]
    rain_start, rain_end = nowcast_cfg["rainfall_climatology"]

    ndvi_rows, rain_rows = [], []
    for season in settings["scope"]["seasons"]:
        ndvi_fc = fetch_ndvi_climatology_stats(
            districts_fc, season, season_windows, ndvi_start, ndvi_end, scale["ndvi"]
        )
        ndvi_df = parse_district_zonal_stats_hdx(
            ndvi_fc, value_field="mean", value_col="ndvi_climatology_mean"
        )
        ndvi_df["season"] = season
        ndvi_rows.append(ndvi_df)

        rain_fc = fetch_rainfall_climatology_stats(
            districts_fc, season, season_windows, rain_start, rain_end, scale["rainfall"]
        )
        rain_df = parse_district_zonal_stats_hdx(
            rain_fc, value_field="mean", value_col="rainfall_climatology_mm"
        )
        rain_df["season"] = season
        rain_rows.append(rain_df)

    _write_csv(pd.concat(ndvi_rows, ignore_index=True), "ndvi_climatology_district.csv")
    _write_csv(pd.concat(rain_rows, ignore_index=True), "rainfall_climatology_district.csv")


def run_nowcast_features() -> None:
    """Lead-time (partial-season) NDVI mean/peak and rainfall total per district x season
    x year x lead_months, over settings.nowcast.lead_months."""
    project_id = os.environ["GEE_PROJECT_ID"]
    settings = load_settings()
    districts_fc = hdx_districts_fc(project_id)
    scale = settings["gee_extraction"]["scale_m"]
    season_windows = settings["season_windows"]

    rows = []
    for year in settings["scope"]["years"]:
        for season in settings["scope"]["seasons"]:
            for lead_months in settings["nowcast"]["lead_months"]:
                start_date, cutoff_date = partial_season_date_range(
                    year, season, season_windows, lead_months
                )

                ndvi_mean_fc = fetch_ndvi_district_stats(
                    districts_fc, start_date, cutoff_date, scale["ndvi"]
                )
                ndvi_mean_df = parse_district_zonal_stats_hdx(
                    ndvi_mean_fc, value_field="mean", value_col="ndvi_mean"
                )

                ndvi_peak_fc = fetch_ndvi_peak_district_stats(
                    districts_fc, start_date, cutoff_date, scale["ndvi"]
                )
                ndvi_peak_df = parse_district_zonal_stats_hdx(
                    ndvi_peak_fc, value_field="mean", value_col="ndvi_peak"
                )

                rain_fc = fetch_rainfall_district_stats(
                    districts_fc, start_date, cutoff_date, scale["rainfall"]
                )
                rain_df = parse_district_zonal_stats_hdx(
                    rain_fc, value_field="mean", value_col="rainfall_mm"
                )

                merged = ndvi_mean_df.merge(
                    ndvi_peak_df, on=["nisr_district_code", "district_name"]
                ).merge(rain_df, on=["nisr_district_code", "district_name"])
                merged["year"], merged["season"], merged["lead_months"] = year, season, lead_months
                rows.append(merged)
                logger.info(f"{year} {season} lead={lead_months}mo: {len(merged)} districts")

    _write_csv(pd.concat(rows, ignore_index=True), "nowcast_features_district_season_year.csv")


def _write_csv(df: pd.DataFrame, filename: str) -> None:
    output_dir = DATA_EXTERNAL / "gee"
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / filename, index=False)
    logger.info(f"wrote {len(df)} rows to {output_dir / filename}")


def main() -> None:
    load_dotenv()
    run_boundaries()
    run_ndvi_rainfall()
    run_cropland()
    run_soil()
    run_climatology()
    run_nowcast_features()


if __name__ == "__main__":
    main()
