"""In-memory data store for serving precomputed results."""

from __future__ import annotations

import json
from pathlib import Path

import loguru
import pandas as pd

from api.app.settings import get_settings

logger = loguru.logger

DATA_EXTERNAL = Path(__file__).resolve().parents[2] / "data" / "external"


class DataStore:
    """Singleton data store loaded on app startup."""

    def __init__(self):
        self.districts_geojson: dict | None = None
        self.yield_gap: pd.DataFrame | None = None

    def load(self) -> None:
        """Load all data into memory on startup."""
        geojson_path = DATA_EXTERNAL / "boundaries" / "rwanda_districts.geojson"
        if geojson_path.exists():
            with open(geojson_path) as f:
                self.districts_geojson = json.load(f)
            logger.info(f"loaded {len(self.districts_geojson.get('features', []))} districts")
        else:
            logger.warning(f"districts GeoJSON not found at {geojson_path}")

        yield_gap_path = get_settings().DATA_DIR / "public" / "yield_gap.csv"
        if yield_gap_path.exists():
            self.yield_gap = pd.read_csv(yield_gap_path)
            logger.info(f"loaded {len(self.yield_gap)} yield_gap rows")
        else:
            logger.warning(f"yield_gap.csv not found at {yield_gap_path}")

    def clear(self) -> None:
        """Clear data on shutdown."""
        self.districts_geojson = None
        self.yield_gap = None


data_store = DataStore()
