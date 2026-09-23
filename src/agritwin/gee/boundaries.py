"""Rwanda district boundary loader (FAO/GAUL/2015/level2 via Earth Engine).

Dataset id, filter and field names come from config/data_sources.yaml
(gee.datasets.gaul_districts); never hardcode them elsewhere.

GAUL's ADM2_CODE is its own code, not the NISR survey district_code used in
stg_sas_plot_crop. Reconciling the two (by name, since Kigali sub-division
and spelling differ) is a separate future step and is not done here.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import geopandas as gpd
import loguru

from agritwin.config import gee_dataset_config

if TYPE_CHECKING:
    import ee

logger = loguru.logger


def parse_gaul_features(fc_geojson: dict) -> gpd.GeoDataFrame:
    """Turn a GAUL FeatureCollection GeoJSON dict into a district table.

    fc_geojson is the shape returned by ee.FeatureCollection.getInfo(), after
    rwanda_districts_fc() has already renamed ADM2_NAME/ADM2_CODE to
    district_name/gaul_district_code server-side.

    Returns a GeoDataFrame with one row per input feature (district_name,
    gaul_district_code, geometry). Row count is preserved; a feature missing
    district_name or gaul_district_code raises rather than being silently dropped.
    """
    geojson_features = []
    for feature in fc_geojson["features"]:
        props = feature["properties"]
        name = props.get("district_name")
        code = props.get("gaul_district_code")
        if name is None or code is None:
            raise ValueError(f"GAUL feature missing district_name or gaul_district_code: {props}")
        geojson_features.append(
            {
                "type": "Feature",
                "properties": {"district_name": name, "gaul_district_code": int(code)},
                "geometry": feature["geometry"],
            }
        )
    return gpd.GeoDataFrame.from_features(geojson_features, crs="EPSG:4326")


def rwanda_districts_fc(project_id: str) -> ee.FeatureCollection:
    """Thin I/O wrapper: the GAUL Rwanda admin2 FeatureCollection, not yet materialized.

    Reused as the zonal-statistics region set by gee/extract.py, so a
    boundaries refresh and an extraction run always see the same districts.
    """
    import ee

    cfg = gee_dataset_config("gaul_districts")
    ee.Initialize(project=project_id)
    return (
        ee.FeatureCollection(cfg["id"])
        .filter(ee.Filter.eq(cfg["filter_field"], cfg["filter_value"]))
        .select(["ADM2_NAME", "ADM2_CODE"], ["district_name", "gaul_district_code"])
    )


def fetch_rwanda_districts(project_id: str) -> dict:
    """Thin I/O wrapper: pull the GAUL Rwanda admin2 FeatureCollection from Earth Engine."""
    info = rwanda_districts_fc(project_id).getInfo()
    assert info is not None, "GAUL Rwanda FeatureCollection query returned no result"
    return info


def write_boundaries(gdf: gpd.GeoDataFrame, output_path: Path) -> None:
    """Thin I/O wrapper: write the district boundary table as GeoJSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver="GeoJSON")
    logger.info(f"wrote {len(gdf)} districts to {output_path}")
