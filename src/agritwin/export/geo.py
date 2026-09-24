"""Simplify the raw GAUL district boundaries for public/API/web consumption.

The raw boundaries (data/external/boundaries/rwanda_districts.geojson, from
gee/boundaries.py) carry full-resolution GAUL polygons meant for accurate zonal
statistics, not for shipping to a browser. This module produces the smaller,
simplified, NISR-district_code-joined version other consumers should use instead.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd


def simplify_boundaries(gdf: gpd.GeoDataFrame, tolerance_m: float) -> gpd.GeoDataFrame:
    """Simplify each district polygon's geometry to within tolerance_m metres.

    Simplified in a projected (metric) CRS (UTM 36S, the correct zone for Rwanda) so
    tolerance_m means metres, not degrees, then reprojected back to EPSG:4326 for
    GeoJSON output. Row count and column set are unchanged, only the geometry column.
    """
    projected = gdf.to_crs("EPSG:32736")
    projected["geometry"] = projected["geometry"].simplify(tolerance_m, preserve_topology=True)
    return projected.to_crs("EPSG:4326")


def attach_district_codes(gdf: gpd.GeoDataFrame, crosswalk: pd.DataFrame) -> gpd.GeoDataFrame:
    """Join the NISR district_code onto each feature via gaul_district_code, the same
    crosswalk api/app/data_store.py uses at API load time
    (data/reference/district_crosswalk.csv). A feature with no crosswalk match keeps
    district_code null rather than being dropped."""
    gdf = gdf.copy()
    gaul_to_nisr = dict(zip(crosswalk["gaul_code"], crosswalk["nisr_district_code"], strict=True))
    gdf["district_code"] = gdf["gaul_district_code"].map(gaul_to_nisr)
    return gdf
