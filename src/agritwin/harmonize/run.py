"""Runner for the harmonize step. Invoked by `make stage` (python -m agritwin.harmonize.run).

Joins each year's production/practice/fertilizer SAS files, renames to the canonical
stg_sas_plot_crop schema, and stacks all years x seasons into one table. Writes a second,
small sidecar table logging the confidence of every (year, variable) mapping used.
"""

from __future__ import annotations

from pathlib import Path

import loguru
import pandas as pd

from agritwin.config import load_crops, load_file_registry, load_settings, load_variable_map
from agritwin.harmonize.core import (
    OUTPUT_COLUMNS,
    apply_crop_codes,
    build_confidence_table,
    join_season_files,
    rename_to_canonical,
)
from agritwin.harmonize.io import read_season_files

DATA_STAGING = Path(__file__).resolve().parents[3] / "data" / "staging"

logger = loguru.logger


def crop_code_map(crops_cfg: dict, year: int) -> dict[int, str]:
    """Crop code -> canonical crop name for a given year. Every /audit-sas run to date has
    confirmed the same codes apply across 2019-2025, so a year-specific block is only
    consulted if one exists; otherwise the 2024 block (the reference year) is reused."""
    source_codes = crops_cfg["source_codes"]
    return source_codes.get(year, source_codes[2024])


def harmonize_season(
    year: int, season: str, file_registry: dict, variable_map: dict, crops_cfg: dict
) -> pd.DataFrame:
    year_map = variable_map[year]["production"]
    files = read_season_files(year, season, file_registry)

    production_rows_in = len(files["production"])
    joined = join_season_files(year, files, year_map)
    rows_out = len(joined)
    if rows_out != production_rows_in:
        raise ValueError(
            f"{year} season {season}: join changed row count ({production_rows_in} -> {rows_out}); "
            "expected an exact match since production is the join base"
        )

    renamed = rename_to_canonical(joined, year, season, year_map)
    result = apply_crop_codes(renamed, crop_code_map(crops_cfg, year))
    return result[OUTPUT_COLUMNS]


def run() -> pd.DataFrame:
    settings = load_settings()
    file_registry = load_file_registry()
    variable_map = load_variable_map()
    crops_cfg = load_crops()

    years = settings["scope"]["years"]
    seasons = settings["scope"]["seasons"]  # Seasons A and B only; Season C excluded per MVP scope

    frames = []
    for year in years:
        for season in seasons:
            df = harmonize_season(year, season, file_registry, variable_map, crops_cfg)
            logger.info(f"{year} season {season}: {len(df)} rows")
            frames.append(df)

    stacked = pd.concat(frames, ignore_index=True)
    logger.info(f"stg_sas_plot_crop: {len(stacked)} rows total, {stacked['year'].nunique()} years")

    confidence = build_confidence_table(variable_map)

    DATA_STAGING.mkdir(parents=True, exist_ok=True)
    stacked.to_parquet(DATA_STAGING / "stg_sas_plot_crop.parquet", index=False)
    confidence.to_parquet(DATA_STAGING / "stg_sas_variable_confidence.parquet", index=False)
    logger.info(f"wrote {DATA_STAGING / 'stg_sas_plot_crop.parquet'}")
    logger.info(f"wrote {DATA_STAGING / 'stg_sas_variable_confidence.parquet'}")

    return stacked


if __name__ == "__main__":
    run()
