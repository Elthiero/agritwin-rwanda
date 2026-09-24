"""District-level zonal statistics: NDVI, rainfall, cropland fraction, soil.

Each fetch_* function reduces one Earth Engine image to a mean (or mode, for
categorical soil texture) per district, over the district boundaries from
gee/boundaries.py. Dataset ids, bands and the cropland class code come from
config/data_sources.yaml; scale factors and back-transforms come from
gee/scaling.py. Never hardcode any of those here.

NDVI and rainfall are time-varying (fetched per season x year, see
periods.py); cropland fraction and soil are single time-invariant snapshots.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from agritwin.config import gee_dataset_config
from agritwin.gee.scaling import CHIRPS_SCALE, MODIS_NDVI_SCALE, scale_isda_image_ee

if TYPE_CHECKING:
    import ee

_ISDA_FORMULAS = {
    "isda_ph": "ph",
    "isda_nitrogen": "nitrogen_total",
    "isda_carbon": "carbon_organic",
}


def parse_district_zonal_stats(fc_geojson: dict, value_field: str, value_col: str) -> pd.DataFrame:
    """Turn a reduceRegions() FeatureCollection GeoJSON into a per-district table.

    fc_geojson is the shape returned by ee.FeatureCollection.getInfo() after a
    reduceRegions() call over the boundaries.py district FeatureCollection:
    one feature per district, carrying district_name/gaul_district_code plus
    the reducer's output under value_field (e.g. "mean", "sum" or "mode").

    A district with no valid pixels (fully masked, e.g. cloud cover) keeps
    its row with a null value_col rather than being dropped.
    """
    rows = [
        {
            "district_name": feature["properties"]["district_name"],
            "gaul_district_code": feature["properties"]["gaul_district_code"],
            value_col: feature["properties"].get(value_field),
        }
        for feature in fc_geojson["features"]
    ]
    return pd.DataFrame(rows)


def parse_district_zonal_stats_hdx(
    fc_geojson: dict, value_field: str, value_col: str
) -> pd.DataFrame:
    """Like parse_district_zonal_stats, but for a reduceRegions() result over
    boundaries.hdx_districts_fc(), whose features carry nisr_district_code (not
    gaul_district_code) natively, so results built on it need no further crosswalk
    join. See docs/decisions.md 2026-09-23.
    """
    rows = [
        {
            "nisr_district_code": feature["properties"]["nisr_district_code"],
            "district_name": feature["properties"]["district_name"],
            value_col: feature["properties"].get(value_field),
        }
        for feature in fc_geojson["features"]
    ]
    return pd.DataFrame(rows)


def fetch_ndvi_district_stats(
    districts_fc: ee.FeatureCollection, start_date: str, end_date: str, scale_m: int
) -> dict:
    """Mean MODIS NDVI per district over [start_date, end_date)."""
    import ee

    cfg = gee_dataset_config("modis_ndvi")
    img = (
        ee.ImageCollection(cfg["id"])
        .filterDate(start_date, end_date)
        .select("NDVI")
        .mean()
        .multiply(MODIS_NDVI_SCALE)
    )
    return img.reduceRegions(
        collection=districts_fc, reducer=ee.Reducer.mean(), scale=scale_m
    ).getInfo()


def fetch_ndvi_peak_district_stats(
    districts_fc: ee.FeatureCollection, start_date: str, end_date: str, scale_m: int
) -> dict:
    """Peak (max composite) MODIS NDVI per district over [start_date, end_date), for the
    nowcast's "peak NDVI" feature -- distinct from fetch_ndvi_district_stats' mean
    composite (used as a "cumulative greenness" proxy)."""
    import ee

    cfg = gee_dataset_config("modis_ndvi")
    img = (
        ee.ImageCollection(cfg["id"])
        .filterDate(start_date, end_date)
        .select("NDVI")
        .max()
        .multiply(MODIS_NDVI_SCALE)
    )
    return img.reduceRegions(
        collection=districts_fc, reducer=ee.Reducer.mean(), scale=scale_m
    ).getInfo()


def _season_month_filter(start_month: int, end_month: int) -> ee.Filter:
    """A recurring (every-year) calendar-month filter for one season window. Handles a
    season that wraps across the year boundary (e.g. September to February)."""
    import ee

    if start_month <= end_month:
        return ee.Filter.calendarRange(start_month, end_month, "month")
    return ee.Filter.Or(
        ee.Filter.calendarRange(start_month, 12, "month"),
        ee.Filter.calendarRange(1, end_month, "month"),
    )


def fetch_ndvi_climatology_stats(
    districts_fc: ee.FeatureCollection,
    season: str,
    season_windows: dict,
    start_year: int,
    end_year: int,
    scale_m: int,
) -> dict:
    """Mean MODIS NDVI per district over every occurrence of this season's calendar
    window across [start_year, end_year] (a recurring filter, not one long date range),
    for the nowcast's NDVI-anomaly baseline. A season that wraps across the year boundary
    (e.g. Sept-Feb) includes Jan/Feb of start_year and Sept-Dec of end_year at the edges,
    a one-season boundary approximation judged negligible for an 18-year climatology.
    """
    import ee

    cfg = gee_dataset_config("modis_ndvi")
    window = season_windows[season]
    img = (
        ee.ImageCollection(cfg["id"])
        .filter(ee.Filter.calendarRange(start_year, end_year, "year"))
        .filter(_season_month_filter(window["start_month"], window["end_month"]))
        .select("NDVI")
        .mean()
        .multiply(MODIS_NDVI_SCALE)
    )
    return img.reduceRegions(
        collection=districts_fc, reducer=ee.Reducer.mean(), scale=scale_m
    ).getInfo()


def fetch_rainfall_climatology_stats(
    districts_fc: ee.FeatureCollection,
    season: str,
    season_windows: dict,
    start_year: int,
    end_year: int,
    scale_m: int,
) -> dict:
    """Mean seasonal total CHIRPS rainfall per district, averaged across every occurrence
    of this season's calendar window in [start_year, end_year], for the nowcast's
    rainfall-anomaly baseline. Summing every day across all years then dividing by the
    number of years gives the average per-season total (not the average daily value)."""
    import ee

    cfg = gee_dataset_config("chirps_daily")
    window = season_windows[season]
    n_years = end_year - start_year + 1
    img = (
        ee.ImageCollection(cfg["id"])
        .filter(ee.Filter.calendarRange(start_year, end_year, "year"))
        .filter(_season_month_filter(window["start_month"], window["end_month"]))
        .select("precipitation")
        .sum()
        .divide(n_years)
        .multiply(CHIRPS_SCALE)
    )
    return img.reduceRegions(
        collection=districts_fc, reducer=ee.Reducer.mean(), scale=scale_m
    ).getInfo()


def fetch_rainfall_district_stats(
    districts_fc: ee.FeatureCollection, start_date: str, end_date: str, scale_m: int
) -> dict:
    """Total CHIRPS rainfall (mm) per district over [start_date, end_date).

    The temporal sum (days -> season total) happens in .sum() below; the
    spatial reduceRegions step must be Reducer.mean(), not sum(), or the
    result scales with the number of pixels in the district instead of
    representing rainfall depth.
    """
    import ee

    cfg = gee_dataset_config("chirps_daily")
    img = (
        ee.ImageCollection(cfg["id"])
        .filterDate(start_date, end_date)
        .select("precipitation")
        .sum()
        .multiply(CHIRPS_SCALE)
    )
    return img.reduceRegions(
        collection=districts_fc, reducer=ee.Reducer.mean(), scale=scale_m
    ).getInfo()


def fetch_cropland_fraction_district_stats(
    districts_fc: ee.FeatureCollection, scale_m: int
) -> dict:
    """Fraction of cropland (ESA WorldCover) pixels per district."""
    import ee

    cfg = gee_dataset_config("esa_worldcover")
    map_img = ee.ImageCollection(cfg["id"]).first().select(cfg["bands_used"][0])
    img = map_img.eq(cfg["cropland_class"])
    return img.reduceRegions(
        collection=districts_fc, reducer=ee.Reducer.mean(), scale=scale_m
    ).getInfo()


def fetch_soil_district_stats(
    districts_fc: ee.FeatureCollection, dataset_name: str, scale_m: int
) -> dict:
    """Mean (or mode, for categorical texture) iSDAsoil value per district.

    dataset_name is one of "isda_ph", "isda_nitrogen", "isda_carbon", "isda_texture".
    """
    import ee

    cfg = gee_dataset_config(dataset_name)
    img = ee.Image(cfg["id"]).select(cfg["bands_used"][0])
    if dataset_name in _ISDA_FORMULAS:
        img = scale_isda_image_ee(img, _ISDA_FORMULAS[dataset_name])
    reducer = ee.Reducer.mode() if dataset_name == "isda_texture" else ee.Reducer.mean()
    return img.reduceRegions(collection=districts_fc, reducer=reducer, scale=scale_m).getInfo()
