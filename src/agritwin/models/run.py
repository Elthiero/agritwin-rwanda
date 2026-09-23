"""Runner for the attainable-yield step of `make train` (python -m agritwin.models.run).

Reads clean/'s stg_sas_plot_crop, survey/'s district_yield mart, and the static
district-level soil/cropland GEE outputs; writes zone assignments, attainable yield, and
yield gap.
"""

from __future__ import annotations

from pathlib import Path

import loguru
import pandas as pd

from agritwin.config import load_settings
from agritwin.models.attainable import (
    assign_zones,
    compute_attainable_yield,
    compute_yield_gap,
    prepare_eligible_plots,
)

DATA_STAGING = Path(__file__).resolve().parents[3] / "data" / "staging"
DATA_MARTS = Path(__file__).resolve().parents[3] / "data" / "marts"
DATA_EXTERNAL = Path(__file__).resolve().parents[3] / "data" / "external"
DATA_PUBLIC = Path(__file__).resolve().parents[3] / "data" / "public"

logger = loguru.logger


def run() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    settings = load_settings()
    attainable_cfg = settings["attainable"]

    soil = pd.read_csv(DATA_EXTERNAL / "gee" / "soil_district.csv")
    cropland = pd.read_csv(DATA_EXTERNAL / "gee" / "cropland_fraction_district.csv")
    zones = assign_zones(soil, cropland, k=attainable_cfg["kmeans_k"])
    n_districts = zones["nisr_district_code"].nunique()
    n_zones = zones["zone_id"].nunique()
    logger.info(f"assigned {n_districts} districts to {n_zones} zones")

    plot_crop = pd.read_parquet(DATA_STAGING / "stg_sas_plot_crop.parquet")
    eligible = prepare_eligible_plots(plot_crop, zones)

    attainable_yield = compute_attainable_yield(
        eligible,
        percentile=attainable_cfg["percentile"],
        min_segments=attainable_cfg["min_segments"],
    )
    logger.info(
        f"attainable_yield: {len(attainable_yield)} rows, "
        f"reliability counts: {attainable_yield['reliability'].value_counts().to_dict()}"
    )

    district_yield = pd.read_parquet(DATA_MARTS / "district_yield.parquet")
    yield_gap = compute_yield_gap(district_yield, attainable_yield, zones)
    logger.info(
        f"yield_gap: {len(yield_gap)} rows, "
        f"reliability counts: {yield_gap['reliability'].value_counts().to_dict()}"
    )

    DATA_MARTS.mkdir(parents=True, exist_ok=True)
    attainable_yield.to_parquet(DATA_MARTS / "attainable_yield.parquet", index=False)
    yield_gap.to_parquet(DATA_MARTS / "yield_gap.parquet", index=False)
    logger.info(f"wrote attainable_yield.parquet and yield_gap.parquet to {DATA_MARTS}")

    DATA_PUBLIC.mkdir(parents=True, exist_ok=True)
    zones.to_csv(DATA_PUBLIC / "district_zones.csv", index=False)

    public_gap = yield_gap[yield_gap["reliability"] != "suppressed"].drop(columns="reliability")
    public_gap.to_csv(DATA_PUBLIC / "yield_gap.csv", index=False)
    logger.info(f"wrote district_zones.csv and yield_gap.csv ({len(public_gap)} rows)")

    return zones, attainable_yield, yield_gap


if __name__ == "__main__":
    run()
