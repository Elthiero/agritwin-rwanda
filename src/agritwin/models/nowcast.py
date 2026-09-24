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


def _one_season_back(season: str, year: int) -> tuple[str, int]:
    """The single immediately preceding season: Season A's prior is Season B of the
    previous year; Season B's prior is Season A of the same year."""
    if season == "A":
        return "B", year - 1
    return "A", year


def _n_seasons_back(season: str, year: int, n: int) -> tuple[str, int]:
    for _ in range(n):
        season, year = _one_season_back(season, year)
    return season, year


def _last_year_key(district_code: float, crop: str, season: str, year: int) -> tuple:
    return (district_code, crop, season, year - 1)


def realistic_lookback_seasons(season: str, lead_months: int) -> int:
    """How many seasons back to look for a prior-production feature that would
    realistically be published by this lead time's prediction date. Evidenced in
    docs/nowcast-feature-timing.md: NISR publishes a season's SAS report roughly 3.5 to
    4 months after that season's data collection concludes (confirmed from the actual
    PDF creation dates of the real SAS 2025 Season A and Season B reports, not
    estimated). Season A predictions are safe at every lead time using the immediately
    preceding season (Season B), which already has months of margin by any Season A
    prediction date. Season B predictions are NOT safe using the immediately preceding
    season (Season A of the same year) before lead_months == 4: Season A's own report
    is not published until ~3.5 months after Season A itself concludes, which lands
    inside Season B's own growing period, after the lead=2 and lead=3 prediction dates.
    At those two lead times, Season B falls back two seasons, to the previous year's
    Season B, which is comfortably published (~mid-October) well before Season B's own
    lead=2 prediction date (~May 1).
    """
    if season == "A":
        return 1
    return 1 if lead_months >= 4 else 2


def build_yield_lookup(district_yield: pd.DataFrame) -> pd.Series:
    """(district_code, crop, season, year) -> yield_kg_ha, from survey/'s district-level
    estimates only. Shared by both lagged-yield attachment functions below."""
    district_actual = district_yield[district_yield["geo_level"] == "district"].copy()
    district_actual["district_code"] = district_actual["geo_code"].astype(float)
    district_actual["year"] = district_actual["year"].astype(int)
    return district_actual.set_index(["district_code", "crop", "season", "year"])["yield_kg_ha"]


def attach_lagged_yield(district_yield: pd.DataFrame) -> pd.DataFrame:
    """One row per district x crop x season x year (from survey/'s district-level
    estimates only), with last_year_yield_kg_ha (same season, one year earlier) looked
    up. Used only for the baseline_last_year comparison, never fed to the model as a
    feature, and always safe at every lead time regardless of season (a full year of
    margin is far more than the ~3.5-4 month publication lag needs).
    prior_season_yield_kg_ha is NOT attached here: it depends on lead_months (see
    attach_prior_season_for_lead), unlike last_year_yield_kg_ha.
    """
    district_actual = district_yield[district_yield["geo_level"] == "district"].copy()
    district_actual["district_code"] = district_actual["geo_code"].astype(float)
    district_actual["year"] = district_actual["year"].astype(int)

    lookup = build_yield_lookup(district_yield)

    def _lookup_last_year(row: pd.Series) -> float:
        key = _last_year_key(row["district_code"], row["crop"], row["season"], row["year"])
        return lookup.get(key, np.nan)

    district_actual["last_year_yield_kg_ha"] = district_actual.apply(_lookup_last_year, axis=1)
    return district_actual


def attach_prior_season_for_lead(
    district_yield_lagged: pd.DataFrame, yield_lookup: pd.Series, lead_months: int
) -> pd.DataFrame:
    """Attaches prior_season_yield_kg_ha for one specific lead_months value, using
    however many seasons back would realistically have been published by that lead
    time's prediction date (see realistic_lookback_seasons). Must be called once per
    lead_months, since the same district x crop x season x year row uses a different
    prior-season source depending on which lead time it is being evaluated at.
    """
    out = district_yield_lagged.copy()

    def _lookup_prior(row: pd.Series) -> float:
        n = realistic_lookback_seasons(row["season"], lead_months)
        season, year = _n_seasons_back(row["season"], row["year"], n)
        return yield_lookup.get((row["district_code"], row["crop"], season, year), np.nan)

    out["prior_season_yield_kg_ha"] = out.apply(_lookup_prior, axis=1)
    return out


def build_feature_table(
    district_yield_lagged: pd.DataFrame,
    yield_lookup: pd.Series,
    nowcast_features: pd.DataFrame,
    ndvi_climatology: pd.DataFrame,
    rainfall_climatology: pd.DataFrame,
    lead_months: int,
) -> pd.DataFrame:
    """Attaches this lead time's realistic prior_season_yield_kg_ha, then joins this
    lead time's partial-season NDVI/rainfall (and their climatology anomalies) onto the
    lagged district_yield table. Inner join on the satellite side: a district x season x
    year with no satellite extraction has no usable row here.
    """
    with_prior_season = attach_prior_season_for_lead(
        district_yield_lagged, yield_lookup, lead_months
    )
    feats = nowcast_features[nowcast_features["lead_months"] == lead_months]
    merged = with_prior_season.merge(
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


def exclude_low_reliability(features_df: pd.DataFrame) -> pd.DataFrame:
    """Drops "suppressed" rows (fewer than survey/'s min_segments, see
    src/agritwin/survey/core.py's add_reliability_flag) from both training and
    evaluation: per docs/decisions.md 2026-09-24, a cell resting on too few plots is
    survey noise, not a learnable signal, for either purpose. "use_with_caution" rows
    (elevated CV, but still meeting the minimum segment floor) are kept: a small
    minority per crop, not worth separate handling. prior_season_yield_kg_ha is
    unaffected by this filter: it is computed upstream from the full unfiltered table
    (see build_yield_lookup), since it is an input feature representing the best
    information a real forecaster would have had, not the target being modeled.
    """
    return features_df[features_df["reliability"] != "suppressed"].copy()


def _mape(actual: pd.Series, predicted: pd.Series) -> float:
    """Mean absolute percentage error, excluding rows where actual is 0 (MAPE is
    undefined there, not a large-but-valid number)."""
    valid = actual != 0
    if not valid.any():
        return float("nan")
    return float((np.abs(actual[valid] - predicted[valid]) / np.abs(actual[valid])).mean() * 100)


def _mae(actual: pd.Series, predicted: pd.Series) -> float:
    """Mean absolute error, in the same unit as actual (kg/ha here). Unlike MAPE, well
    defined even where actual is 0, and not misleading when yields are low: per the
    external review, MAPE alone overstates error at low-yield crops/districts relative
    to what the absolute kg/ha miss actually looks like."""
    return float(np.abs(actual - predicted).mean())


MODEL_NAMES = ("baseline_district_mean", "baseline_last_year", "ridge", "lgbm")


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

        predictions = {
            "baseline_district_mean": baseline_district_mean_pred,
            "baseline_last_year": baseline_last_year_pred,
            "ridge": ridge_pred,
            "lgbm": lgbm_pred,
        }
        row = {"held_out_year": held_out_year, "n_test_rows": len(test)}
        for model_name, pred in predictions.items():
            row[f"{model_name}_mape"] = _mape(test_actual, pred)
            row[f"{model_name}_mae_kg_ha"] = _mae(test_actual, pred)
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_cv(cv_results: pd.DataFrame) -> dict:
    """Row-count-weighted average MAPE and MAE per model across all held-out years, so a
    year with more test rows counts more, not every year equally regardless of sample
    size. Also the unweighted standard deviation of each model's per-fold MAPE across
    years, since a mean improvement over baseline is not meaningful on its own if it is
    smaller than the year-to-year spread (see docs/decisions.md 2026-09-24)."""
    weights = cv_results["n_test_rows"]
    summary = {}
    for model_name in MODEL_NAMES:
        mape_col, mae_col = f"{model_name}_mape", f"{model_name}_mae_kg_ha"
        summary[mape_col] = float(np.average(cv_results[mape_col], weights=weights))
        summary[mae_col] = float(np.average(cv_results[mae_col], weights=weights))
        summary[f"{model_name}_mape_std_across_years"] = float(cv_results[mape_col].std(ddof=0))
    return summary
