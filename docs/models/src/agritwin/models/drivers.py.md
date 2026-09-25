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
- Default LightGBM hyperparameters, untuned (see Limitations).

## Validation scheme
GroupKFold by district (5 splits), never a random K-fold: plots within a district are
correlated (shared soil, shared local conditions), and a random split would leak
district-level information into the validation fold. Compared against a fold-safe naive
baseline: each fold's own training-set mean log-yield (never averaging in validation-fold
values), so the baseline sees exactly the same information split as the model.

## Metrics (with baselines)
Out-of-fold MAE in log space, model versus the fold-safe naive baseline
(`artifacts/drivers_*_metadata.json`, current production run):

| Crop | Model MAE (log) | Baseline MAE (log) | Improvement over baseline |
|---|---|---|---|
| maize | 0.693 | 0.727 | +4.6% |
| beans | 0.532 | 0.561 | +5.2% |
| Irish potato | 0.605 | 0.750 | +19.4% |
| sorghum | 0.531 | 0.506 | **-5.0% (worse than baseline)** |

Sorghum's driver model does not beat the naive baseline. This is reported honestly rather than
hidden or tuned away (see `docs/decisions.md`, 2026-09-24 and 2026-09-25). A follow-up
investigation (2026-09-25) found this is a real, structural result, not a bug: sorghum's
`log_yield` has the lowest variance of the four crops (0.656 vs. 0.926 for maize, 0.892 for
Irish potato, 0.711 for beans), so the naive per-district mean already explains more of the
variation before any model is applied, and four of sorghum's eight boolean practice features are
close to constant for this crop (`improved_seed` adoption 0.2%, `mechanized` 3.1%, `irrigated`
0.5%, `land_consolidation` 1.9%, versus, e.g., 81.4% improved-seed adoption for maize), leaving
structurally less signal for a model to find. A controlled hyperparameter sweep against the same
CV showed heavier regularization recovers roughly half the gap (-5.0% to -1.35%) and also
improves maize's already-positive result, indicating an untuned-defaults issue rather than
something sorghum-specific. This was deliberately not applied to production, because selecting a
configuration using the same CV metric that is then reported as the honest result would itself
be a form of leakage; a defensible fix needs a proper nested CV or held-out tuning set, flagged
as a next step, not done here.

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
- **Untuned hyperparameters.** LightGBM defaults are used as-is; the 2026-09-25 investigation
  confirmed a real accuracy gain is available from regularization tuning across all four crops,
  not implemented here to avoid leakage from tuning against the reported evaluation metric.
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
- Trained: 2026-09-24 (per-crop timestamps in `artifacts/drivers_*_metadata.json`).
- Config: `config/settings.yaml` `drivers` block (`target: log_yield`, `cv: group_kfold_district`,
  `n_splits: 5`, `min_plots: 30`).
- Git commit: `766290df98860eb2d55c3eac76e812722e28fef0` (training run); current repo HEAD `68ac497`
  (2026-09-25) for this card.
