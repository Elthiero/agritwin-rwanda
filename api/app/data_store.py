"""In-memory data store for serving precomputed results."""

from __future__ import annotations

import json
from pathlib import Path

import loguru

logger = loguru.logger

DATA_EXTERNAL = Path(__file__).resolve().parents[2] / "data" / "external"


class DataStore:
    """Singleton data store loaded on app startup."""

    def __init__(self):
        self.districts_geojson: dict | None = None

    def load(self) -> None:
        """Load all data into memory on startup."""
        geojson_path = DATA_EXTERNAL / "boundaries" / "rwanda_districts.geojson"
        if geojson_path.exists():
            with open(geojson_path) as f:
                self.districts_geojson = json.load(f)
            logger.info(f"loaded {len(self.districts_geojson.get('features', []))} districts")
        else:
            logger.warning(f"districts GeoJSON not found at {geojson_path}")

    def clear(self) -> None:
        """Clear data on shutdown."""
        self.districts_geojson = None


data_store = DataStore()
