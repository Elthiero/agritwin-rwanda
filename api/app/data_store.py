"""In-memory data store for serving precomputed results."""

from __future__ import annotations

import json
from pathlib import Path

import loguru
import pandas as pd

from api.app.settings import get_settings

logger = loguru.logger

DATA_EXTERNAL = Path(__file__).resolve().parents[2] / "data" / "external"
DATA_REFERENCE = Path(__file__).resolve().parents[2] / "data" / "reference"


class DataStore:
    """Singleton data store loaded on app startup."""

    def __init__(self):
        self.districts_geojson: dict | None = None
        self.yield_gap: pd.DataFrame | None = None
        self.drivers: pd.DataFrame | None = None
        self.drivers_by_district: pd.DataFrame | None = None
        self.backtest: pd.DataFrame | None = None

    def _load_public_csv(self, filename: str) -> pd.DataFrame | None:
        path = get_settings().DATA_DIR / "public" / filename
        if not path.exists():
            logger.warning(f"{filename} not found at {path}")
            return None
        df = pd.read_csv(path)
        logger.info(f"loaded {len(df)} rows from {filename}")
        return df

    def _attach_nisr_district_codes(self) -> None:
        """Add the NISR district_code (used by every model/yield-gap endpoint) to each
        boundary feature, keyed off its existing gaul_district_code. Without this, /districts
        and /yield-gap key the same 30 districts by two different numbering systems."""
        if not self.districts_geojson:
            return
        crosswalk_path = DATA_REFERENCE / "district_crosswalk.csv"
        if not crosswalk_path.exists():
            logger.warning(f"district crosswalk not found at {crosswalk_path}")
            return
        crosswalk = pd.read_csv(crosswalk_path)
        gaul_to_nisr = dict(
            zip(crosswalk["gaul_code"], crosswalk["nisr_district_code"], strict=True)
        )
        for feature in self.districts_geojson.get("features", []):
            gaul_code = feature.get("properties", {}).get("gaul_district_code")
            nisr_code = gaul_to_nisr.get(gaul_code)
            if nisr_code is not None:
                feature["properties"]["district_code"] = int(nisr_code)

    def load(self) -> None:
        """Load all data into memory on startup."""
        geojson_path = DATA_EXTERNAL / "boundaries" / "rwanda_districts.geojson"
        if geojson_path.exists():
            with open(geojson_path) as f:
                self.districts_geojson = json.load(f)
            logger.info(f"loaded {len(self.districts_geojson.get('features', []))} districts")
            self._attach_nisr_district_codes()
        else:
            logger.warning(f"districts GeoJSON not found at {geojson_path}")

        self.yield_gap = self._load_public_csv("yield_gap.csv")
        self.drivers = self._load_public_csv("drivers.csv")
        self.drivers_by_district = self._load_public_csv("drivers_by_district.csv")
        self.backtest = self._load_public_csv("nowcast_backtest.csv")

    def clear(self) -> None:
        """Clear data on shutdown."""
        self.districts_geojson = None
        self.yield_gap = None
        self.drivers = None
        self.drivers_by_district = None
        self.backtest = None


data_store = DataStore()
