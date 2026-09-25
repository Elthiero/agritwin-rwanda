# Model card: Driver model (LightGBM + SHAP)

## Purpose
Shows, for each crop, which farming practices and plot conditions tend to go together with
higher or lower yield, both nationally and per district. This is the "why might yield differ"
explanation shown alongside the yield-gap map: not a prediction of next season's yield, but a
ranked list of what is associated with better or worse outcomes in the plots already surveyed.

One LightGBM regression model is trained per crop (maize, beans, Irish potato, sorghum), on
log(yield per hectare), and explained with SHAP.

## Intended users and uses
- District agronomists and NISR/MINAGRI staff looking at the district profile page, to see
  which practices (improved seed, fertilizer, irrigation, erosion control, and so on) are
  associated with higher yield for a given crop in their district specifically.
- Feeding the scenario explorer's lever choices (improved seed adoption, fertilizer use,
  irrigation, land consolidation), which are drawn from this model's global ranking.

## Out of scope uses
- **Never causal.** Per CLAUDE.md rule 5, this model must never be described with words like
  "causes," "increases yield by," or "impact of." A plot with irrigation and higher yield does
  not mean irrigation caused the higher yield: better-resourced farmers may adopt several good
  practices together, or better land may attract both irrigation investment and naturally higher
  yield. Always describe results as "associated with," never as an effect.
- Not a per-plot or per-farmer prediction tool. It is trained and explained at the crop x
  district level; a single farmer's plot may look nothing like the SHAP summary for their
  district.
- Sorghum's model specifically should be treated with more skepticism than the other three
  crops (see Metrics and Limitations): it does not beat a naive baseline, so its SHAP rankings
  carry a weaker evidentiary basis.
- Not validated for crops or seasons outside the MVP set (maize, beans, Irish potato, sorghum)
  or outside the 2019 to 2025 SAS years pooled together. The model is not season-specific: a
  known limitation, not a design choice (see Limitations).

## Data
- Source: harmonized SAS plot-crop records (`stg_sas_plot_crop`), restricted to pure-stand
  plots with `qc_flag == "ok"` (the same eligibility filter used everywhere else in the
  pipeline), further restricted to `yield_kg_ha > 0` (total crop failures are excluded because
  log(0) is undefined, not because they are uninteresting).
- Years: 2019 to 2025, both seasons pooled together (see Limitations for what this means).
- Per-crop row counts, all pooled across seasons and years, all 2019-2025 (`artifacts/drivers_*_metadata.json`):

  | Crop | Rows (n_plots) | Districts |
  |---|---|---|
  | maize | 7,238 | 30 |
  | beans | 15,088 | 30 |
  | Irish potato | 4,559 | 30 |
  | sorghum | 7,466 | 29 |

- Rows are **not survey-weighted** for training: survey weights correct for unequal selection
  probability when estimating a population total or mean, which is not what a per-plot
  association-ranking model is doing (see `docs/decisions.md`, 2026-09-24).

## Target
`log_yield` = natural log of `yield_kg_ha`, per plot. Log scale because yield is right-skewed
and practice effects are more plausibly multiplicative than additive on the raw kg/ha scale.

## Features
Eight boolean practice flags (`improved_seed`, `organic_fert`, `inorganic_fert`, `pesticide`,
`anti_erosion`, `land_consolidation`, `mechanized`, `irrigated`), `erosion_degree` (an ordinal
severity code, used as-is; stable in ranking across all 7 years with one documented 2019
level-merging caveat), `plot_area_ha`, `sowing_month`, four iSDAsoil features (`soil_ph`,
`soil_nitrogen`, `soil_carbon`, `soil_texture_class`), and CHIRPS `rainfall_mm` for that
district x season x year (joined from the GEE mart).

## Method
- One LightGBM regressor per crop (not one pooled model with crop as a feature), so SHAP
  explanations reflect within-crop associations rather than being dominated by cross-crop
  yield-level differences.
- SHAP (`shap.TreeExplainer`) gives:
  - a global ranking (`compute_global_shap`): feature, mean absolute SHAP value, and direction
    (whether the feature associates with higher or lower log-yield on average).
  - a per-district ranking (`compute_district_shap`): the same, computed separately within
    each district's plots for that crop. Districts with fewer than `min_plots` (30, same floor
    as the survey's `n_min`) eligible plots for that crop are flagged `"suppressed"`, kept in
    the output but marked, not silently dropped.
- Hyperparameters are chosen by a nested CV, not left at LightGBM's defaults (see Method and
  Metrics below; this replaces the untuned-defaults version documented before 2026-09-25).

## Validation scheme
GroupKFold by district (5 outer splits), never a random K-fold: plots within a district are
correlated (shared soil, shared local conditions), and a random split would leak
district-level information into the validation fold. Compared against a fold-safe naive
baseline: each fold's own training-set mean log-yield (never averaging in validation-fold
values), so the baseline sees exactly the same information split as the model.

**Hyperparameters are selected by a nested inner CV**, not hand-picked against the reported
metric. Within each outer fold's *training* rows only, `select_hyperparams()` runs a further
GroupKFold-by-district search (3 inner splits) over a small fixed candidate grid (LightGBM
defaults, plus three progressively more regularized configs identified in the 2026-09-24/25
sorghum investigation: shallower trees, larger `min_child_samples`, L1/L2 regularization,
slower learning rate), and the winning config for that outer fold is then fit on the full
outer-training set and scored on the untouched outer-validation fold. The outer fold never
influences which config is chosen, so the reported metric below carries no tuning leakage. The
production model (`fit_final_model`) uses the same selection procedure run once more over the
entire dataset, and the chosen config is recorded per crop in
`artifacts/drivers_*_metadata.json`'s `final_hyperparams`.

## Metrics (with baselines)
Out-of-fold MAE in log space from the nested CV above, model versus the fold-safe naive
baseline (`artifacts/drivers_*_metadata.json`, current production run):

| Crop | Model MAE (log) | Baseline MAE (log) | Improvement over baseline | Chosen final config |
|---|---|---|---|---|
| maize | 0.669 | 0.727 | +7.96% | `num_leaves=4, min_child_samples=50, max_depth=3, reg_alpha/lambda=1.0, lr=0.03, n_estimators=150` |
| beans | 0.534 | 0.561 | +4.76% | same as maize |
| Irish potato | 0.584 | 0.750 | +22.23% | `num_leaves=7, min_child_samples=30, max_depth=4, reg_alpha/lambda=1.0, lr=0.05, n_estimators=200` |
| sorghum | 0.513 | 0.506 | **-1.35% (still worse than baseline)** | same as maize |

Nested CV improved three of four crops over the earlier untuned-defaults numbers (maize +4.6%
to +7.96%, Irish potato +19.4% to +22.23%, beans essentially flat at +4.76%) and closed most of
sorghum's gap (-5.0% to -1.35%), matching what the 2026-09-25 hand-picked sweep predicted, this
time without the leakage risk of picking a config by eye against the reported number. **Sorghum
still does not beat the naive baseline.** This is reported honestly rather than hidden (see
`docs/decisions.md`, 2026-09-24 and 2026-09-25). The underlying reason, confirmed in the
2026-09-25 investigation, is structural, not a tuning gap: sorghum's `log_yield` has the lowest
variance of the four crops (0.656 vs. 0.926 for maize, 0.892 for Irish potato, 0.711 for beans),
so the naive per-district mean already explains more of the variation before any model is
applied, and four of sorghum's eight boolean practice features are close to constant for this
crop (`improved_seed` adoption 0.2%, `mechanized` 3.1%, `irrigated` 0.5%, `land_consolidation`
1.9%, versus, e.g., 81.4% improved-seed adoption for maize), leaving structurally less signal for
any model, tuned or not, to find.

## Uncertainty method
SHAP values themselves are point estimates of feature contribution to a single model fit; no
confidence interval is placed on an individual SHAP value or ranking position. The reliability
signal in the driver model's output is the `"ok"`/`"suppressed"` flag per district (based on
`min_plots`, the same convention used across the pipeline for "trust this or not"), not an
interval. Global cross-crop comparability is bounded by the honest MAE-vs-baseline numbers above:
a crop whose model does not beat baseline (sorghum) should have its SHAP rankings treated with
correspondingly less confidence, even though SHAP itself does not carry a built-in uncertainty
figure.

## Limitations
- **Sorghum does not beat its own naive baseline.** Its driver rankings are real associations in
  the fitted model, but the model's overall out-of-fold accuracy is no better than guessing each
  district's average, so treat sorghum's SHAP story with more skepticism than the other three
  crops.
- **Not causal**, ever (CLAUDE.md rule 5). Confounding is expected: farmers who adopt one good
  practice often adopt several, and better land may draw more investment in the first place.
- **Not season-specific.** Both seasons are pooled into one model per crop; `season` is not a
  training feature, so the model cannot distinguish a Season A association from a Season B one,
  even though the API's `/drivers` endpoint accepts a `season` parameter (documented as currently
  having no effect; see `docs/decisions.md`, 2026-09-24, "found neither driver nor nowcast
  models split by season").
- **Hyperparameter search is limited to 4 hand-picked candidates**, not a broad search: the
  nested CV (see Method) chooses among LightGBM defaults and 3 regularized configs identified in
  the earlier hand-picked sweep, not an open hyperparameter space. A wider search might find a
  better config still, at the cost of more compute per training run.
- **erosion_degree** has one documented year-comparability caveat: 2019 has only 3 severity
  levels where 2020 onward has 4 (2019's level 3 "Weak" merges what later years split into
  "Low" and "Very Low"), so it is ordinally comparable but not identical across years.

## Fairness and representativeness notes
- Training rows are restricted to pure-stand, small-scale-farmer plots by the survey's own
  design; the model's associations describe that population, not commercial or large-scale
  farms.
- Districts with fewer than 30 eligible plots for a given crop get a `"suppressed"` per-district
  SHAP summary rather than a shown-but-unreliable one; Irish potato (4,559 rows total across 30
  districts, the smallest of the four crops) is the most likely to have thin districts.
- Sorghum has data from only 29 of 30 districts (one district has no eligible sorghum plots in
  the study period), so its per-district driver summary cannot cover all of Rwanda for this crop.
- Rare-practice features (e.g. sorghum's near-zero improved-seed and irrigation adoption) mean
  the model has very little evidence to learn an association for that feature-crop combination,
  even where the feature exists in the data; a near-constant feature cannot show a meaningful
  SHAP contribution regardless of its true effect.

## Version
- Data version: `2026.10.0` (from `artifacts/drivers_*_metadata.json`).
- Trained: 2026-09-25 (nested-CV retrain; per-crop timestamps in
  `artifacts/drivers_*_metadata.json`).
- Config: `config/settings.yaml` `drivers` block (`target: log_yield`, `cv: group_kfold_district`,
  `n_splits: 5`, `min_plots: 30`); inner CV `n_inner_splits: 3` (passed by
  `models/run.py`, not yet its own settings key); `HYPERPARAM_CANDIDATES` in
  `models/drivers.py`.
- Git commit: `e59e68d` (training run); current repo HEAD as of this card's last edit,
  2026-09-25 (nested CV / npm audit session).
