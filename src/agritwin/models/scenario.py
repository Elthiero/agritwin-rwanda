"""Scenario explorer: precomputed lever grid, per docs/AgriTwin_Master_Build_Guide.md
section 4.4. Not a live re-run of the model. For each district x crop, predicts mean
yield under every combination of the boolean levers in config/settings.yaml's
`drivers.levers` (4 levers -> 16 configurations), holding every other feature (soil,
rainfall, plot conditions) at its observed value, using the already-fitted driver model
from models/drivers.py. Bootstrap over plots gives a percentile interval per
configuration. Always "model-based, not causal" (CLAUDE.md rule 5): this is the driver
model's association, evaluated under a hypothetical input, not a causal simulation.
"""

from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

from agritwin.models.drivers import FEATURE_COLUMNS


def lever_grid(levers: list[str]) -> list[dict[str, bool]]:
    """All 2**len(levers) True/False combinations, as a list of {lever: value} dicts."""
    combos = product([False, True], repeat=len(levers))
    return [dict(zip(levers, combo, strict=True)) for combo in combos]


def predict_yield_kg_ha(
    model, features_df: pd.DataFrame, lever_config: dict[str, bool]
) -> np.ndarray:
    """Predicted yield_kg_ha per row under `lever_config`, holding every other feature at
    its observed value. log_yield -> kg/ha via exp (the model's target is log_yield, see
    models/drivers.py FEATURE_COLUMNS docstring)."""
    X = features_df[FEATURE_COLUMNS].copy()
    for lever, value in lever_config.items():
        X[lever] = float(value)
    return np.exp(model.predict(X))


def bootstrap_district_scenario(
    model,
    features_df: pd.DataFrame,
    levers: list[str],
    n_reps: int,
    min_plots: int,
    random_state: int = 0,
) -> pd.DataFrame:
    """One row per (district_code, lever configuration): mean predicted yield_kg_ha,
    a bootstrap 95 percent interval (resampling plots with replacement, same
    unweighted-bootstrap approach as models/drivers.py's SHAP; the driver model is not
    survey-weighted, see its docstring), n_plots, and a reliability flag (same min_plots
    floor as models/drivers.py's district SHAP)."""
    rng = np.random.default_rng(random_state)
    configs = lever_grid(levers)
    rows = []

    for district_code, group in features_df.groupby("district_code"):
        n_plots = len(group)
        reliability = "suppressed" if n_plots < min_plots else "ok"
        group = group.reset_index(drop=True)

        # All n_reps resamples stacked into one table, predicted in a single call per
        # config rather than one call per rep: same bootstrap statistics, far fewer
        # LightGBM predict() calls (that per-call overhead, not row count, dominated
        # runtime here).
        boot_positions = rng.integers(0, n_plots, size=n_reps * n_plots)
        boot_rows = group.iloc[boot_positions].reset_index(drop=True)
        rep_id = np.repeat(np.arange(n_reps), n_plots)

        for config in configs:
            point = float(predict_yield_kg_ha(model, group, config).mean())
            preds = predict_yield_kg_ha(model, boot_rows, config)
            draws = pd.Series(preds).groupby(rep_id).mean().to_numpy()

            row = {"district_code": district_code, **config}
            row["mean_yield_kg_ha"] = point
            row["ci_low"] = float(np.percentile(draws, 2.5))
            row["ci_high"] = float(np.percentile(draws, 97.5))
            row["n_plots"] = n_plots
            row["reliability"] = reliability
            rows.append(row)

    return pd.DataFrame(rows)
