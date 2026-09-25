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

# Hand-picked regularization sweep from docs/decisions.md 2026-09-25's sorghum
# investigation: heavier regularization recovered over half of sorghum's gap to baseline
# and also improved maize's already-positive result, the signature of an untuned,
# overfitting LightGBM default. Config 0 is that default. Selected per-fold by
# select_hyperparams() via an inner CV, never by looking at the outer/reported fold, so
# choosing among these does not leak into the honest metric it's chosen within.
HYPERPARAM_CANDIDATES: list[dict] = [
    {},  # LightGBM defaults
    {
        "num_leaves": 7,
        "min_child_samples": 30,
        "max_depth": 4,
        "reg_alpha": 1.0,
        "reg_lambda": 1.0,
        "learning_rate": 0.05,
        "n_estimators": 200,
    },
    {
        "num_leaves": 4,
        "min_child_samples": 50,
        "max_depth": 3,
        "reg_alpha": 1.0,
        "reg_lambda": 1.0,
        "learning_rate": 0.03,
        "n_estimators": 150,
    },
    {
        "num_leaves": 15,
        "min_child_samples": 20,
        "learning_rate": 0.02,
        "n_estimators": 500,
    },
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


def select_hyperparams(
    X: pd.DataFrame, y: pd.Series, groups: pd.Series, n_splits: int, random_state: int = 0
) -> dict:
    """Picks the HYPERPARAM_CANDIDATES config with the lowest inner GroupKFold-by-district
    MAE on (X, y, groups) alone. Callers pass only an outer-fold's training rows (for
    cross_validate_nested) or the whole dataset (for the final production model), so this
    selection never sees whatever rows it will later be scored against."""
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error
    from sklearn.model_selection import GroupKFold

    n_inner = min(n_splits, groups.nunique())
    if n_inner < 2:
        return HYPERPARAM_CANDIDATES[0]

    best_config, best_mae = HYPERPARAM_CANDIDATES[0], float("inf")
    for config in HYPERPARAM_CANDIDATES:
        fold_errors = []
        for train_idx, val_idx in GroupKFold(n_splits=n_inner).split(X, y, groups):
            model = lgb.LGBMRegressor(random_state=random_state, verbosity=-1, **config)
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            fold_errors.append(
                mean_absolute_error(y.iloc[val_idx], model.predict(X.iloc[val_idx]))
            )
        mae = float(np.mean(fold_errors))
        if mae < best_mae:
            best_config, best_mae = config, mae
    return best_config


def cross_validate_nested(
    features_df: pd.DataFrame,
    n_splits: int,
    n_inner_splits: int = 3,
    random_state: int = 0,
) -> dict:
    """Same outer GroupKFold-by-district honest metric as cross_validate(), except the
    LightGBM hyperparameters used within each outer fold are chosen by an inner
    GroupKFold over that fold's training rows only (select_hyperparams), never by looking
    at the outer validation fold. This is the leakage-safe version of the hand-picked
    sweep in docs/decisions.md 2026-09-25: same HYPERPARAM_CANDIDATES, but the config is
    now selected inside the training data of each fold instead of by eyeballing the
    reported metric.
    """
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error
    from sklearn.model_selection import GroupKFold

    X = features_df[FEATURE_COLUMNS]
    y = features_df["log_yield"]
    groups = features_df["district_code"]

    model_errors, baseline_errors, chosen_configs = [], [], []
    for train_idx, val_idx in GroupKFold(n_splits=n_splits).split(X, y, groups):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        config = select_hyperparams(
            X_train, y_train, groups.iloc[train_idx], n_inner_splits, random_state
        )
        chosen_configs.append(config)

        model = lgb.LGBMRegressor(random_state=random_state, verbosity=-1, **config)
        model.fit(X_train, y_train)
        model_errors.append(mean_absolute_error(y_val, model.predict(X_val)))

        baseline_pred = y_train.mean()
        baseline_errors.append(mean_absolute_error(y_val, [baseline_pred] * len(y_val)))

    model_mae = float(np.mean(model_errors))
    baseline_mae = float(np.mean(baseline_errors))
    return {
        "n_splits": n_splits,
        "n_inner_splits": n_inner_splits,
        "n_rows": len(features_df),
        "n_districts": int(groups.nunique()),
        "model_mae_log": model_mae,
        "baseline_mae_log": baseline_mae,
        "improvement_over_baseline_pct": (baseline_mae - model_mae) / baseline_mae * 100,
        "chosen_configs_per_fold": chosen_configs,
    }


def fit_final_model(features_df: pd.DataFrame, random_state: int = 0, params: dict | None = None):
    """Fit on every eligible row for this crop (after cross_validate_nested already
    reported honest out-of-fold performance); this final model is what SHAP explanations
    use. `params` defaults to LightGBM's own defaults; pass the output of
    select_hyperparams(..., over the full dataset) to use the same tuned config the
    nested CV validated, rather than an untuned default."""
    import lightgbm as lgb

    X = features_df[FEATURE_COLUMNS]
    y = features_df["log_yield"]
    model = lgb.LGBMRegressor(random_state=random_state, verbosity=-1, **(params or {}))
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
