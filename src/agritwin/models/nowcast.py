"""Early yield estimate (nowcast): district x crop x season x year yield anomaly,
predicted from partial-season NDVI/rainfall (at a chosen lead time into the season) plus
prior-season production. Per docs/AgriTwin_Master_Build_Guide.md section 4.3 and
config/settings.yaml's `nowcast` block.

Target is `district_yield_anomaly` (settings.nowcast.target): this year's actual district
x crop x season yield minus that district x crop x season's historical mean, where the
historical mean is always computed from training years only under leave-one-year-out CV
(CLAUDE.md rule: "Any feature derived from the target... must be computed inside the CV
fold from training years only"). Reported against two naive baselines
(settings.nowcast.models: baseline_district_mean predicts zero anomaly; baseline_last_year
predicts last year's same-season anomaly) plus ridge and a small LightGBM, all compared by
MAPE on the reconstructed actual yield (MAPE on the anomaly itself is not meaningful: an
anomaly can be near zero for a genuinely average year, blowing up a percentage error that
has nothing to do with the model being wrong).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "ndvi_mean",
    "ndvi_peak",
    "ndvi_anomaly",
    "rainfall_mm",
    "rainfall_anomaly",
    "prior_season_yield_kg_ha",
]

GROUP_COLS = ["district_code", "crop", "season"]


def _prior_season_key(district_code: float, crop: str, season: str, year: int) -> tuple:
    if season == "A":
        return (district_code, crop, "B", year - 1)
    return (district_code, crop, "A", year)


def _last_year_key(district_code: float, crop: str, season: str, year: int) -> tuple:
    return (district_code, crop, season, year - 1)


def attach_lagged_yield(district_yield: pd.DataFrame) -> pd.DataFrame:
    """One row per district x crop x season x year (from survey/'s district-level
    estimates only), with two lagged yield columns looked up from the same table:
    prior_season_yield_kg_ha (the immediately preceding season, a model feature) and
    last_year_yield_kg_ha (same season, one year earlier, used only for the
    baseline_last_year comparison, never fed to the model as a feature).
    """
    district_actual = district_yield[district_yield["geo_level"] == "district"].copy()
    district_actual["district_code"] = district_actual["geo_code"].astype(float)
    district_actual["year"] = district_actual["year"].astype(int)

    lookup = district_actual.set_index(["district_code", "crop", "season", "year"])[
        "yield_kg_ha"
    ]

    def _lookup(row: pd.Series, key_fn) -> float:
        key = key_fn(row["district_code"], row["crop"], row["season"], row["year"])
        return lookup.get(key, np.nan)

    district_actual["prior_season_yield_kg_ha"] = district_actual.apply(
        _lookup, axis=1, key_fn=_prior_season_key
    )
    district_actual["last_year_yield_kg_ha"] = district_actual.apply(
        _lookup, axis=1, key_fn=_last_year_key
    )
    return district_actual


def build_feature_table(
    district_yield_lagged: pd.DataFrame,
    nowcast_features: pd.DataFrame,
    ndvi_climatology: pd.DataFrame,
    rainfall_climatology: pd.DataFrame,
    lead_months: int,
) -> pd.DataFrame:
    """Joins one lead time's partial-season NDVI/rainfall (and their climatology
    anomalies) onto the lagged district_yield table. Inner join on the satellite side:
    a district x season x year with no satellite extraction has no usable row here.
    """
    feats = nowcast_features[nowcast_features["lead_months"] == lead_months]
    merged = district_yield_lagged.merge(
        feats,
        left_on=["district_code", "season", "year"],
        right_on=["nisr_district_code", "season", "year"],
        how="inner",
    ).drop(columns="nisr_district_code")

    merged = merged.merge(
        ndvi_climatology[["nisr_district_code", "season", "ndvi_climatology_mean"]],
        left_on=["district_code", "season"],
        right_on=["nisr_district_code", "season"],
        how="left",
    ).drop(columns="nisr_district_code")
    merged = merged.merge(
        rainfall_climatology[["nisr_district_code", "season", "rainfall_climatology_mm"]],
        left_on=["district_code", "season"],
        right_on=["nisr_district_code", "season"],
        how="left",
    ).drop(columns="nisr_district_code")

    merged["ndvi_anomaly"] = merged["ndvi_mean"] - merged["ndvi_climatology_mean"]
    merged["rainfall_anomaly"] = merged["rainfall_mm"] - merged["rainfall_climatology_mm"]
    return merged


def _mape(actual: pd.Series, predicted: pd.Series) -> float:
    """Mean absolute percentage error, excluding rows where actual is 0 (MAPE is
    undefined there, not a large-but-valid number)."""
    valid = actual != 0
    if not valid.any():
        return float("nan")
    return float((np.abs(actual[valid] - predicted[valid]) / np.abs(actual[valid])).mean() * 100)


def leave_one_year_out_cv(features_df: pd.DataFrame, min_train_rows: int = 20) -> pd.DataFrame:
    """One row of metrics per held-out year: MAPE (on reconstructed actual yield) for
    both naive baselines, ridge, and a small LightGBM. The historical mean used to build
    target_anomaly and to reconstruct predicted actual yield is computed from the
    training years only, every fold, per CLAUDE.md's no-target-leakage rule.
    """
    from lightgbm import LGBMRegressor
    from sklearn.linear_model import Ridge

    rows = []
    for held_out_year in sorted(features_df["year"].unique()):
        train = features_df[features_df["year"] != held_out_year].copy()
        test = features_df[features_df["year"] == held_out_year].copy()
        if len(train) < min_train_rows or len(test) == 0:
            continue

        historical_mean = train.groupby(GROUP_COLS)["yield_kg_ha"].mean()
        train["historical_mean"] = train.set_index(GROUP_COLS).index.map(historical_mean)
        test["historical_mean"] = test.set_index(GROUP_COLS).index.map(historical_mean)
        test = test.dropna(subset=["historical_mean"])
        if len(test) == 0:
            continue

        train["target_anomaly"] = train["yield_kg_ha"] - train["historical_mean"]
        test_actual = test["yield_kg_ha"]

        baseline_district_mean_pred = test["historical_mean"]
        last_year_anomaly = test["last_year_yield_kg_ha"] - test["historical_mean"]
        baseline_last_year_pred = test["historical_mean"] + last_year_anomaly.fillna(0)

        # median() skips NaN, but is itself NaN for a column that's 100% missing in this
        # fold's training rows; fillna(NaN) would be a no-op and crash Ridge.fit on the
        # first such fold, so a genuinely all-missing column falls back to 0 (Ridge has
        # no NaN-native handling, unlike LightGBM below, which uses the raw columns).
        median_fill = train[FEATURE_COLUMNS].median().fillna(0.0)
        X_train_ridge = train[FEATURE_COLUMNS].fillna(median_fill)
        X_test_ridge = test[FEATURE_COLUMNS].fillna(median_fill)
        ridge = Ridge(random_state=0)
        ridge.fit(X_train_ridge, train["target_anomaly"])
        ridge_pred = test["historical_mean"] + ridge.predict(X_test_ridge)

        lgbm = LGBMRegressor(
            random_state=0, verbosity=-1, n_estimators=50, num_leaves=7, min_child_samples=5
        )
        lgbm.fit(train[FEATURE_COLUMNS], train["target_anomaly"])
        lgbm_pred = test["historical_mean"] + lgbm.predict(test[FEATURE_COLUMNS])

        rows.append(
            {
                "held_out_year": held_out_year,
                "n_test_rows": len(test),
                "baseline_district_mean_mape": _mape(test_actual, baseline_district_mean_pred),
                "baseline_last_year_mape": _mape(test_actual, baseline_last_year_pred),
                "ridge_mape": _mape(test_actual, ridge_pred),
                "lgbm_mape": _mape(test_actual, lgbm_pred),
            }
        )
    return pd.DataFrame(rows)


def summarize_cv(cv_results: pd.DataFrame) -> dict:
    """Row-count-weighted average MAPE per model across all held-out years, so a year
    with more test rows counts more, not every year equally regardless of sample size."""
    weights = cv_results["n_test_rows"]
    mape_cols = [
        "baseline_district_mean_mape",
        "baseline_last_year_mape",
        "ridge_mape",
        "lgbm_mape",
    ]
    return {col: float(np.average(cv_results[col], weights=weights)) for col in mape_cols}
