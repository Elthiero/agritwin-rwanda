"""Runner for `make train` (python -m agritwin.models.run): attainable yield / yield gap,
then the per-crop driver model.

Reads clean/'s stg_sas_plot_crop, survey/'s district_yield mart, and the static
district-level soil/cropland/rainfall GEE outputs.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
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
from agritwin.models.drivers import (
    FEATURE_COLUMNS,
    build_feature_table,
    compute_district_shap,
    compute_global_shap,
    cross_validate,
    fit_final_model,
)
from agritwin.models.nowcast import (
    attach_lagged_yield,
    build_yield_lookup,
    exclude_low_reliability,
    leave_one_year_out_cv,
    summarize_cv,
)
from agritwin.models.nowcast import (
    build_feature_table as build_nowcast_feature_table,
)

DATA_STAGING = Path(__file__).resolve().parents[3] / "data" / "staging"
DATA_MARTS = Path(__file__).resolve().parents[3] / "data" / "marts"
DATA_EXTERNAL = Path(__file__).resolve().parents[3] / "data" / "external"
DATA_PUBLIC = Path(__file__).resolve().parents[3] / "data" / "public"
ARTIFACTS = Path(__file__).resolve().parents[3] / "artifacts"

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

    # Every row kept, including "suppressed" ones: CLAUDE.md golden rule 6 flags and
    # greys out low-reliability cells in the UI, it does not hide them.
    yield_gap.to_csv(DATA_PUBLIC / "yield_gap.csv", index=False)
    logger.info(f"wrote district_zones.csv and yield_gap.csv ({len(yield_gap)} rows)")

    return zones, attainable_yield, yield_gap


def _git_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def run_drivers() -> None:
    settings = load_settings()
    drivers_cfg = settings["drivers"]

    plot_crop = pd.read_parquet(DATA_STAGING / "stg_sas_plot_crop.parquet")
    soil = pd.read_csv(DATA_EXTERNAL / "gee" / "soil_district.csv")
    rainfall = pd.read_csv(DATA_EXTERNAL / "gee" / "rainfall_district_season.csv")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    global_rows, district_rows = [], []

    for crop in settings["scope"]["crops"]:
        features_df = build_feature_table(plot_crop, soil, rainfall, crop)
        n_splits = drivers_cfg["n_splits"]
        if features_df["district_code"].nunique() < n_splits:
            logger.warning(f"{crop}: too few districts for {n_splits}-fold CV, skipped")
            continue

        metrics = cross_validate(features_df, n_splits=drivers_cfg["n_splits"])
        logger.info(f"{crop} driver model: {metrics}")

        model = fit_final_model(features_df)
        model.booster_.save_model(str(ARTIFACTS / f"drivers_{crop}.txt"))
        metadata = {
            "crop": crop,
            "data_version": settings["project"]["data_version"],
            "target": drivers_cfg["target"],
            "features": FEATURE_COLUMNS,
            "cv": drivers_cfg["cv"],
            "metrics": metrics,
            "git_hash": _git_hash(),
            "trained_at": datetime.now(UTC).isoformat(),
        }
        with open(ARTIFACTS / f"drivers_{crop}_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        global_shap = compute_global_shap(model, features_df)
        global_shap.insert(0, "crop", crop)
        global_rows.append(global_shap)

        district_shap = compute_district_shap(
            model, features_df, min_plots=drivers_cfg["min_plots"]
        )
        district_shap.insert(0, "crop", crop)
        district_rows.append(district_shap)

    DATA_PUBLIC.mkdir(parents=True, exist_ok=True)
    if global_rows:
        pd.concat(global_rows, ignore_index=True).to_csv(DATA_PUBLIC / "drivers.csv", index=False)
        pd.concat(district_rows, ignore_index=True).to_csv(
            DATA_PUBLIC / "drivers_by_district.csv", index=False
        )
        logger.info("wrote drivers.csv and drivers_by_district.csv")


def run_nowcast() -> None:
    settings = load_settings()
    nowcast_cfg = settings["nowcast"]

    district_yield = pd.read_parquet(DATA_MARTS / "district_yield.parquet")
    lagged = attach_lagged_yield(district_yield)
    yield_lookup = build_yield_lookup(district_yield)

    nowcast_features = pd.read_csv(
        DATA_EXTERNAL / "gee" / "nowcast_features_district_season_year.csv"
    )
    ndvi_climatology = pd.read_csv(DATA_EXTERNAL / "gee" / "ndvi_climatology_district.csv")
    rainfall_climatology = pd.read_csv(
        DATA_EXTERNAL / "gee" / "rainfall_climatology_district.csv"
    )

    backtest_rows = []
    for crop in settings["scope"]["crops"]:
        crop_lagged = lagged[lagged["crop"] == crop]
        for lead_months in nowcast_cfg["lead_months"]:
            features_df = build_nowcast_feature_table(
                crop_lagged,
                yield_lookup,
                nowcast_features,
                ndvi_climatology,
                rainfall_climatology,
                lead_months,
            )
            n_before = len(features_df)
            features_df = exclude_low_reliability(features_df)
            logger.info(
                f"{crop} lead={lead_months}mo: {n_before} rows before reliability "
                f"filter, {len(features_df)} after (suppressed dropped)"
            )
            if len(features_df) < 10 or features_df["year"].nunique() < 2:
                logger.warning(f"{crop} lead={lead_months}mo: too little data, skipped")
                continue

            cv = leave_one_year_out_cv(features_df)
            if cv.empty:
                logger.warning(f"{crop} lead={lead_months}mo: no valid CV folds, skipped")
                continue
            summary = summarize_cv(cv)
            logger.info(f"{crop} lead={lead_months}mo nowcast backtest: {summary}")

            for model_name, mape in summary.items():
                backtest_rows.append(
                    {
                        "crop": crop,
                        "lead_months": lead_months,
                        "model": model_name.removesuffix("_mape"),
                        "mape_pct": mape,
                        "n_years_tested": len(cv),
                    }
                )

    DATA_PUBLIC.mkdir(parents=True, exist_ok=True)
    if backtest_rows:
        pd.DataFrame(backtest_rows).to_csv(DATA_PUBLIC / "nowcast_backtest.csv", index=False)
        logger.info(f"wrote nowcast_backtest.csv ({len(backtest_rows)} rows)")


def main() -> None:
    run()
    run_drivers()
    run_nowcast()


if __name__ == "__main__":
    main()
