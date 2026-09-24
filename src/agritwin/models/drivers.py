"""Driver model: LightGBM regression of log(yield_kg_ha) on practices, plot conditions,
soil, and in-season rainfall, per district x crop.

Per docs/AgriTwin_Master_Build_Guide.md section 4.2 and config/settings.yaml's `drivers`
block: one model per crop (not pooled with crop as a feature, so SHAP explanations are
crop-specific rather than dominated by cross-crop yield-level differences), validated with
GroupKFold by district (never random K-fold: plots within a district are correlated, and a
random split would leak district-level information into the validation fold). SHAP values
give a global driver ranking and a per-district explanation. Presented strictly as
association, never causation, per CLAUDE.md rule 5: nothing here is a causal estimate.

Training population is the same qc_flag == "ok" (pure-stand, small-scale-farmer,
non-outlier) rows survey/ and models/attainable.py use, for consistency; see
agritwin.survey.core.prepare_for_estimation. Rows are not survey-weighted for training:
survey weights correct for unequal selection probability when estimating a *population*
total or mean, which is not what a driver model's per-plot association ranking is doing
(see docs/decisions.md).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from agritwin.survey.core import prepare_for_estimation

BOOLEAN_FEATURES = [
    "improved_seed",
    "organic_fert",
    "inorganic_fert",
    "pesticide",
    "anti_erosion",
    "land_consolidation",
    "mechanized",
    "irrigated",
]

# erosion_degree is used as-is (not remapped): confirmed across all 7 years (see
# docs/data/variable_audit.md / stg_sas_value_labels) that code 1 = "Severe" and code 2 =
# "Moderate" mean the same thing in every year, and every year's codes increase with
# decreasing severity. The one caveat: 2019 has only 3 levels (its code 3, "Weak", merges
# what 2020+ split into code 3 "Low" and code 4 "Very Low"), so 2019's code 3 is ordinally
# comparable but not identical to other years' code 3. Documented, not silently ignored.
SOIL_FEATURES = ["soil_ph", "soil_nitrogen", "soil_carbon", "soil_texture_class"]

FEATURE_COLUMNS = [
    *BOOLEAN_FEATURES,
    "erosion_degree",
    "plot_area_ha",
    "sowing_month",
    *SOIL_FEATURES,
    "rainfall_mm",
]


def build_feature_table(
    plot_crop: pd.DataFrame, soil_df: pd.DataFrame, rainfall_df: pd.DataFrame, crop: str
) -> pd.DataFrame:
    """One row per eligible plot growing `crop`, with FEATURE_COLUMNS and log_yield.
    yield_kg_ha == 0 rows (total crop failure) are excluded: log(0) is undefined, and
    there is no principled non-zero value to substitute without distorting the target.
    """
    eligible = prepare_for_estimation(plot_crop)
    eligible = eligible[(eligible["crop"] == crop) & (eligible["yield_kg_ha"] > 0)].copy()
    eligible["log_yield"] = np.log(eligible["yield_kg_ha"])

    for col in BOOLEAN_FEATURES:
        eligible[col] = eligible[col].astype("float64")

    merged = eligible.merge(
        soil_df[["nisr_district_code", *SOIL_FEATURES]],
        left_on="district_code",
        right_on="nisr_district_code",
        how="left",
    ).drop(columns="nisr_district_code")

    merged = merged.merge(
        rainfall_df[["nisr_district_code", "season", "year", "rainfall_mm"]],
        left_on=["district_code", "season", "year"],
        right_on=["nisr_district_code", "season", "year"],
        how="left",
    ).drop(columns="nisr_district_code")

    return merged


def cross_validate(features_df: pd.DataFrame, n_splits: int, random_state: int = 0) -> dict:
    """GroupKFold-by-district out-of-fold MAE (in log space) for the LightGBM model
    against a naive baseline (each fold's training-set mean log_yield, computed only from
    that fold's training rows, never leaking validation-fold information into the
    baseline any more than into the model).
    """
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error
    from sklearn.model_selection import GroupKFold

    X = features_df[FEATURE_COLUMNS]
    y = features_df["log_yield"]
    groups = features_df["district_code"]

    model_errors, baseline_errors = [], []
    for train_idx, val_idx in GroupKFold(n_splits=n_splits).split(X, y, groups):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model = lgb.LGBMRegressor(random_state=random_state, verbosity=-1)
        model.fit(X_train, y_train)
        model_errors.append(mean_absolute_error(y_val, model.predict(X_val)))

        baseline_pred = y_train.mean()
        baseline_errors.append(mean_absolute_error(y_val, [baseline_pred] * len(y_val)))

    model_mae = float(np.mean(model_errors))
    baseline_mae = float(np.mean(baseline_errors))
    return {
        "n_splits": n_splits,
        "n_rows": len(features_df),
        "n_districts": int(groups.nunique()),
        "model_mae_log": model_mae,
        "baseline_mae_log": baseline_mae,
        "improvement_over_baseline_pct": (baseline_mae - model_mae) / baseline_mae * 100,
    }


def fit_final_model(features_df: pd.DataFrame, random_state: int = 0):
    """Fit on every eligible row for this crop (after cross_validate already reported
    honest out-of-fold performance); this final model is what SHAP explanations use."""
    import lightgbm as lgb

    X = features_df[FEATURE_COLUMNS]
    y = features_df["log_yield"]
    model = lgb.LGBMRegressor(random_state=random_state, verbosity=-1)
    model.fit(X, y)
    return model


def _shap_values(model, X: pd.DataFrame) -> pd.DataFrame:
    import shap

    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(X)
    return pd.DataFrame(values, columns=X.columns, index=X.index)


def compute_global_shap(model, features_df: pd.DataFrame) -> pd.DataFrame:
    """Global driver ranking: feature, mean_abs_shap, direction (sign of the mean SHAP
    value, i.e. whether the feature is associated with higher or lower log_yield on
    average). Association only, per CLAUDE.md rule 5 -- never presented as causal.
    """
    shap_df = _shap_values(model, features_df[FEATURE_COLUMNS])
    rows = [
        {
            "feature": col,
            "mean_abs_shap": float(shap_df[col].abs().mean()),
            "direction": "positive" if shap_df[col].mean() >= 0 else "negative",
        }
        for col in FEATURE_COLUMNS
    ]
    return pd.DataFrame(rows).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)


def compute_district_shap(model, features_df: pd.DataFrame, min_plots: int) -> pd.DataFrame:
    """Per-district driver ranking. Districts with fewer than min_plots eligible plots
    for this crop are flagged "suppressed" (same convention as survey/ and
    models/attainable.py), not silently omitted -- the row stays, just flagged.
    """
    shap_df = _shap_values(model, features_df[FEATURE_COLUMNS])
    shap_df["district_code"] = features_df["district_code"].to_numpy()

    rows = []
    for district_code, group in shap_df.groupby("district_code"):
        n_plots = len(group)
        reliability = "suppressed" if n_plots < min_plots else "ok"
        for col in FEATURE_COLUMNS:
            rows.append(
                {
                    "district_code": district_code,
                    "feature": col,
                    "mean_abs_shap": float(group[col].abs().mean()),
                    "direction": "positive" if group[col].mean() >= 0 else "negative",
                    "n_plots": n_plots,
                    "reliability": reliability,
                }
            )
    return pd.DataFrame(rows)
