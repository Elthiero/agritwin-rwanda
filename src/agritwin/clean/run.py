"""Runner for the clean step. Invoked by `make clean` (python -m agritwin.clean.run).

Reads harmonize's stg_sas_plot_crop.parquet and stg_sas_value_labels.parquet, adds
yield_kg_ha and qc_flag, and overwrites stg_sas_plot_crop.parquet with the completed
canonical schema (see src/agritwin/CLAUDE.md). Never drops or reorders rows.
"""

from __future__ import annotations

from pathlib import Path

import loguru
import pandas as pd

from agritwin.clean.core import clean_plot_crop
from agritwin.config import load_settings

DATA_STAGING = Path(__file__).resolve().parents[3] / "data" / "staging"

logger = loguru.logger


def run() -> pd.DataFrame:
    settings = load_settings()
    plot_crop = pd.read_parquet(DATA_STAGING / "stg_sas_plot_crop.parquet")
    value_labels = pd.read_parquet(DATA_STAGING / "stg_sas_value_labels.parquet")

    rows_in = len(plot_crop)
    cleaned = clean_plot_crop(plot_crop, value_labels, settings)
    if len(cleaned) != rows_in:
        raise ValueError(f"clean/ changed row count ({rows_in} -> {len(cleaned)}); it must not")

    flag_counts = cleaned["qc_flag"].value_counts().to_dict()
    logger.info(f"stg_sas_plot_crop: {len(cleaned)} rows, qc_flag counts: {flag_counts}")

    cleaned.to_parquet(DATA_STAGING / "stg_sas_plot_crop.parquet", index=False)
    logger.info(f"wrote {DATA_STAGING / 'stg_sas_plot_crop.parquet'}")
    return cleaned


if __name__ == "__main__":
    run()
