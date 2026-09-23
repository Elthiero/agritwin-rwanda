"""Thin I/O wrappers for reading raw SAS files. No transformations beyond dtype passthrough."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyreadstat

RAW_SAS_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "sas"


def read_sas_file(path: Path) -> pd.DataFrame:
    """Read a .dta or .sav file, dispatching on extension. Keeps raw column names."""
    reader = pyreadstat.read_sav if path.suffix == ".sav" else pyreadstat.read_dta
    df, _meta = reader(str(path))
    return df


def season_file_paths(year: int, season: str, file_registry: dict) -> dict[str, Path]:
    """Resolve the three raw file paths (production, practice, fertilizer) for one year x season."""
    roles = file_registry[year][season]
    year_dir = RAW_SAS_DIR / str(year)
    return {role: year_dir / filename for role, filename in roles.items()}


def read_season_files(year: int, season: str, file_registry: dict) -> dict[str, pd.DataFrame]:
    paths = season_file_paths(year, season, file_registry)
    return {role: read_sas_file(path) for role, path in paths.items()}
