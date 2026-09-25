# Model card: Scenario explorer (precomputed lever grid)

## Purpose
Lets a user ask "what would the driver model's own predicted yield be for this district
and crop, if a given combination of farming practices were used instead of what was
actually observed?" It is a lookup into a precomputed table, not a live model call, and
its answer is the driver model's own association re-evaluated under a hypothetical
input, never a causal estimate of what would actually happen if a real farmer or
district changed practices.

This is not a separately trained model. It reuses `drivers.py`'s already-fitted
LightGBM model per crop and evaluates it under 16 fixed lever combinations, so this
card describes that evaluation procedure, not a new fit.

## Intended users and uses
- The scenario explorer page and each district page's scenario card, showing a
  district x crop's predicted mean yield under a chosen combination of improved seed,
  inorganic fertilizer, organic fertilizer, and irrigation.
- Comparing the 16 combinations for one district x crop to see which the driver model
  associates with the highest predicted yield, always read as "the model's association
  under this input," not a ranked list of interventions guaranteed to work.

## Out of scope uses
- **Never causal**, per CLAUDE.md rule 5 and the module's own docstring. A higher
  predicted yield under "improved seed = true" does not mean giving a farmer improved
  seed would produce that yield; the same confounding caveats as the driver model apply
  (see `docs/models/src/agritwin/models/drivers.py.md`), since this is that same
  model's own fitted associations, just queried at a different input point.
- Not a real-time simulation: every number is precomputed at `make train` time from
  `data/public/scenario.csv`, not recalculated per request.
- Not valid for a crop whose own driver model does not beat its naive baseline
  (sorghum, see the drivers model card): a scenario built on an association-ranking
  model that is itself no better than guessing carries even less evidentiary weight.
- Not a per-farmer or per-plot recommendation. Every row is a district x crop average
  over that district's real, observed plots with the lever values overridden; it holds
  every other feature (soil, rainfall, plot conditions) at its observed value, not at
  some "typical" value, so it describes this district's existing plot mix, not a
  generic farmer.

## Data
- Source: the same eligible pure-stand, small-scale-farmer plot features `drivers.py`
  builds per crop (`build_feature_table`), one row per plot with its observed soil,
  rainfall, plot, and practice features.
- Years, crops: identical scope to the driver model (2019 to 2025, the 4 MVP crops).
- Current production run (`data/public/scenario.csv`): 1,904 rows = 4 crops x 16 lever
  combinations x (30 districts for maize/beans/irish_potato, 29 for sorghum). 1,616
  rows (85%) flagged `"ok"`, 288 (15%) `"suppressed"` for too few plots.

## Target
`mean_yield_kg_ha`: the mean of `exp(model.predict(X))` across a district's eligible
plots for one crop, where `X` is each plot's own observed feature row with the four
lever columns (`improved_seed`, `inorganic_fert`, `organic_fert`, `irrigated`)
overridden to the combination's fixed True/False values. The model's own target is
`log_yield` (see the drivers model card), so predictions are exponentiated back to
kg/ha here.

## Features
The same `FEATURE_COLUMNS` as `drivers.py`: the 8 boolean practice flags (4 of which
are the levers being swept, the other 4 left at their observed values),
`erosion_degree`, `plot_area_ha`, `sowing_month`, 4 iSDAsoil features, and CHIRPS
`rainfall_mm`. No new features; this module contributes only the lever-sweep and
bootstrap logic on top of `drivers.py`'s fitted model and feature table.

## Method
1. `lever_grid()`: every one of the 2^4 = 16 True/False combinations of
   `config/settings.yaml`'s `drivers.levers`.
2. `predict_yield_kg_ha()`: for one lever combination, copies each plot's real feature
   row, overwrites the 4 lever columns, predicts with the already-fitted driver model,
   and exponentiates.
3. `bootstrap_district_scenario()`: per district x crop, the point estimate is the mean
   prediction across that district's real plots (not resampled). The interval is a
   percentile bootstrap: plots are resampled with replacement `n_reps` times
   (`scenario.bootstrap_reps` in `config/settings.yaml`, 100, smaller than
   `survey.bootstrap_reps`'s 200 since this runs 16x per district x crop rather than
   once), the mean prediction is taken within each resample, and the 2.5th/97.5th
   percentiles of those `n_reps` means form the interval. Not survey-weighted, for the
   same reason the driver model isn't (see its card): this is a per-plot association
   re-evaluation, not a population total or mean.
4. Districts with fewer than `drivers.min_plots` (30) eligible plots for that crop are
   flagged `"suppressed"`, same convention and same floor as the driver model's
   per-district SHAP summary, kept in the output but marked.

## Validation scheme
No holdout or cross-validation of its own: this module does not fit anything, it
evaluates `drivers.py`'s already-validated model at different inputs, so `drivers.py`'s
own GroupKFold-by-district validation is the relevant accuracy evidence (see that
card). This module's own correctness is checked by unit tests on synthetic data
(`tests/test_scenario.py`): `lever_grid()` produces exactly `2**len(levers)` distinct
combinations, including the all-levers-on case; `predict_yield_kg_ha()` returns
positive predictions and, on synthetic data with a known strong `improved_seed` effect,
correctly shows a higher mean prediction with that lever on than off; the bootstrap
output has the right shape (one row per district x lever combination), a valid
`ci_low <= ci_high` interval, and positive predicted yields; the reliability flag
correctly flips to `"suppressed"` when every district falls below `min_plots`.

## Metrics (with baselines)
Not applicable in the predictive-accuracy sense; see `drivers.py`'s model card for the
underlying model's real out-of-fold accuracy per crop (3 of 4 crops beat a naive
baseline, sorghum does not). The relevant "metric" here is sample adequacy per row,
reported directly: `n_plots` and `reliability` per district x crop, independent of
which lever combination is being evaluated (all 16 combinations for a given district x
crop share the same plot set and therefore the same `n_plots`/`reliability`).

## Uncertainty method
A percentile bootstrap interval (`ci_low`, `ci_high`), resampling plots with
replacement within a district x crop, `scenario.bootstrap_reps` (100) times. This
captures sampling variability in which plots happen to be in a given district's
eligible set, not the driver model's own fitting uncertainty (a single already-fitted
model is used throughout; refitting the model per bootstrap resample was not done, so
this interval is narrower than a full model-refit bootstrap would be, a known
simplification, not a correctness issue for what it does capture).

## Limitations
- Inherits every limitation of `drivers.py`'s underlying model: not causal, not
  season-specific, untuned hyperparameters, and specifically weak for sorghum (see that
  card). A scenario for sorghum is built on a model that does not itself beat a naive
  baseline.
- The bootstrap interval only reflects plot-resampling variance, not model-refitting
  variance; the true uncertainty in "what would this district's mean look like under
  this lever combination" is understated to that extent.
- Holding every non-lever feature at its observed value means the scenario describes
  "this district's existing plots, with these levers swapped," not a synthetic average
  farmer; two districts with different soil or rainfall profiles are not directly
  comparable at the same lever combination for that reason.
- Precomputed at `make train` time, not recalculated live: a config change (a new
  lever, a different bootstrap rep count) requires rerunning the pipeline, not just a
  new API request.

## Fairness and representativeness notes
- Same population as the driver model: pure-stand, small-scale-farmer plots only: the
  scenario describes this population's practice-outcome associations, not commercial or
  large-scale farms.
- 288 of 1,904 rows (15%) are `"suppressed"` for too few plots in that district x crop;
  suppression is concentrated wherever the driver model's own per-district SHAP summary
  is already thin (see that card's fairness notes), since both use the same
  `min_plots` floor over the same eligible-plot population.
- Sorghum has one fewer district than the other three crops (29, not 30), the same gap
  documented in the driver model's card, so no Rwandan district's sorghum scenario can
  be shown for that one missing district.

## Version
- Data version: `data/public/scenario.csv`, built from the same driver-model artifacts
  as `artifacts/drivers_*_metadata.json` (data version `2026.10.0`).
- Config: `config/settings.yaml` `scenario.bootstrap_reps: 100`, `drivers.levers`
  (`improved_seed`, `inorganic_fert`, `organic_fert`, `irrigated`), `drivers.min_plots: 30`.
- Git commit: `68ac497` (2026-09-25) for the underlying driver-model artifacts this
  reuses; this card current as of the 2026-09-25 full-repo-review session.
