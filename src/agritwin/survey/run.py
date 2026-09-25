"""Runner for the survey step. Invoked by `make marts` (python -m agritwin.survey.run).

Reads clean/'s completed stg_sas_plot_crop, restricts to qc_flag == "ok" rows, and
produces design-based, survey-weighted crop x geography x season x year estimates at
three geographic levels (district, province, national), stacked into one long table with
a geo_level/geo_code discriminator. Writes the full-detail mart (gitignored) and a
suppressed, aggregated public CSV.
"""

from __future__ import annotations

from pathlib import Path

import loguru
import pandas as pd

from agritwin.config import load_settings
from agritwin.survey.core import add_reliability_flag, estimate_ratio, prepare_for_estimation

DATA_STAGING = Path(__file__).resolve().parents[3] / "data" / "staging"
DATA_MARTS = Path(__file__).resolve().parents[3] / "data" / "marts"
DATA_PUBLIC = Path(__file__).resolve().parents[3] / "data" / "public"

logger = loguru.logger

LEVELS: dict[str, list[str]] = {
    "district": ["crop", "district_code", "season", "year"],
    "province": ["crop", "province_code", "season", "year"],
    "national": ["crop", "season", "year"],
}


def _estimate_level(eligible: pd.DataFrame, level: str, group_cols: list[str]) -> pd.DataFrame:
    result = estimate_ratio(eligible, group_cols)
    result.insert(0, "geo_level", level)
    geo_col = group_cols[1] if level != "national" else None
    result.insert(1, "geo_code", result[geo_col].astype(str) if geo_col else "RWA")
    return result


def build_district_yield(plot_crop: pd.DataFrame, settings: dict) -> pd.DataFrame:
    eligible = prepare_for_estimation(plot_crop)
    survey_cfg = settings["survey"]

    frames = [
        _estimate_level(eligible, level, group_cols) for level, group_cols in LEVELS.items()
    ]
    combined = pd.concat(frames, ignore_index=True)
    combined = add_reliability_flag(
        combined, cv_max=survey_cfg["cv_max"], min_segments=survey_cfg["min_segments"]
    )

    ordered = [
        "geo_level",
        "geo_code",
        "crop",
        "season",
        "year",
        "total_production_kg",
        "total_production_kg_se",
        "total_area_ha",
        "total_area_ha_se",
        "yield_kg_ha",
        "yield_kg_ha_se",
        "yield_kg_ha_ci_low",
        "yield_kg_ha_ci_high",
        "yield_kg_ha_cv",
        "n_plots",
        "n_segments",
        "reliability",
    ]
    return combined[ordered]


def to_public(district_yield: pd.DataFrame, mvp_crops: list[str]) -> pd.DataFrame:
    """Aggregated-only view: keeps every row, including "suppressed" ones, since
    CLAUDE.md golden rule 6 requires low-reliability cells to be "flagged... and greyed
    out in the UI", not removed (the API and frontend decide how to render the flag; this
    export just carries it through). Drops the standard-error and CV columns, which are
    safe for internal QC but redundant with the CI already shown, and are never plot- or
    farmer-level so there is nothing privacy-sensitive being kept either way.

    Restricted to `mvp_crops` (settings.scope.crops): `estimate_ratio` runs over every
    crop present in the eligible plots, including ones out of MVP scope (e.g. rice, not
    chosen over sorghum, see docs/decisions.md 2026-09-23), which have no consumer
    anywhere downstream (API's Crop enum, drivers, nowcast, scenario all only know the 4
    MVP crops). Kept in the mart (full detail, gitignored) but dropped here so the public
    export doesn't carry rows nothing ever reads."""
    district_yield = district_yield[district_yield["crop"].isin(mvp_crops)]
    return district_yield[
        [
            "geo_level",
            "geo_code",
            "crop",
            "season",
            "year",
            "total_production_kg",
            "total_area_ha",
            "yield_kg_ha",
            "yield_kg_ha_ci_low",
            "yield_kg_ha_ci_high",
            "n_plots",
            "n_segments",
            "reliability",
        ]
    ]


def run() -> pd.DataFrame:
    settings = load_settings()
    plot_crop = pd.read_parquet(DATA_STAGING / "stg_sas_plot_crop.parquet")

    district_yield = build_district_yield(plot_crop, settings)
    logger.info(
        f"district_yield: {len(district_yield)} rows, "
        f"reliability counts: {district_yield['reliability'].value_counts().to_dict()}"
    )

    DATA_MARTS.mkdir(parents=True, exist_ok=True)
    district_yield.to_parquet(DATA_MARTS / "district_yield.parquet", index=False)
    logger.info(f"wrote {DATA_MARTS / 'district_yield.parquet'}")

    public = to_public(district_yield, settings["scope"]["crops"])
    DATA_PUBLIC.mkdir(parents=True, exist_ok=True)
    public.to_csv(DATA_PUBLIC / "district_yield.csv", index=False)
    logger.info(f"wrote {DATA_PUBLIC / 'district_yield.csv'} ({len(public)} rows)")

    return district_yield


if __name__ == "__main__":
    run()
