"""Rwanda district boundary loaders.

Two independent sources are supported:

- FAO/GAUL/2015/level2 via Earth Engine (`rwanda_districts_fc`): the original source,
  still used to key the existing `data/external/gee/*.csv` outputs (gaul_district_code).
- The HDX COD-AB admin2 layer (`hdx_districts_fc`), downloaded once and reconciled to
  NISR's own `district_code` via `data/reference/district_crosswalk.csv` (see
  docs/decisions.md 2026-09-23 and docs/data-sources.md). This is the source that
  carries `nisr_district_code` natively, so extraction results built on it need no
  further district-key join.

Dataset id, filter and field names for GAUL come from config/data_sources.yaml
(gee.datasets.gaul_districts); never hardcode them elsewhere.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import geopandas as gpd
import loguru
import pandas as pd

from agritwin.config import gee_dataset_config

if TYPE_CHECKING:
    import ee

logger = loguru.logger

DISTRICT_CROSSWALK_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "reference" / "district_crosswalk.csv"
)
PUBLIC_DISTRICTS_GEOJSON_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "public" / "geo" / "districts_adm2.geojson"
)


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


def load_district_crosswalk() -> pd.DataFrame:
    """Thin I/O wrapper: the SAS district_code <-> HDX/GAUL crosswalk table.

    See data/reference/district_crosswalk.csv, docs/data-sources.md and
    docs/decisions.md 2026-09-23 for how this was built and validated.
    """
    return pd.read_csv(DISTRICT_CROSSWALK_PATH)


def load_hdx_districts_geojson() -> dict:
    """Thin I/O wrapper: the committed, simplified HDX district GeoJSON.

    Already carries nisr_district_code/district_name/province/hdx_pcode per feature
    (built once from the raw HDX shapefile joined to the crosswalk; see
    docs/data-sources.md). No network access needed to load this.
    """
    with open(PUBLIC_DISTRICTS_GEOJSON_PATH) as f:
        return json.load(f)


def hdx_districts_fc(project_id: str) -> ee.FeatureCollection:
    """The HDX-derived Rwanda district FeatureCollection, built client-side from the
    committed GeoJSON (data/public/geo/districts_adm2.geojson), not from an uploaded
    Earth Engine table asset. Each feature already carries nisr_district_code, so
    extraction results built on this collection need no further district-key join
    against the crosswalk. See docs/decisions.md 2026-09-23 for why a client-side
    FeatureCollection was used instead of an ingested EE table asset (no GCS bucket
    dependency, no async ingestion wait, and 30 simplified polygons are well within
    the payload limit for direct FeatureCollection construction).
    """
    import ee

    ee.Initialize(project=project_id)
    geojson = load_hdx_districts_geojson()
    features = [
        ee.Feature(feature["geometry"], feature["properties"])
        for feature in geojson["features"]
    ]
    return ee.FeatureCollection(features)
