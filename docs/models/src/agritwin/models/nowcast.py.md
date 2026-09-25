# Model card: Early yield estimate (nowcast)

## Purpose
Tries to predict a district's yield for the current growing season before the official survey
(SAS) report is published, using satellite signals (NDVI greenness, CHIRPS rainfall) measured
partway through the season plus the district's own recent production history. The honest
headline result of this model is that, at the current sample size, it mostly does not beat the
simplest possible guess: this district's own historical average yield for that crop and season.
That finding is reported directly rather than hidden, per the project's own standard for
negative results.

## Intended users and uses
- District agronomists and NISR/MINAGRI staff wanting an early read on how a season is shaping
  up before SAS data is available, for crops and lead times where the backtest shows a real,
  if modest, edge over the naive guess: **sorghum and beans only** (see Metrics).
- The backtest page itself, which exists specifically to show these numbers honestly rather than
  present the nowcast as more reliable than it is.

## Out of scope uses
- **Do not present as "the nowcast beats the naive estimate" for maize or Irish potato at any
  lead time.** The evidence does not support that claim; `baseline_district_mean` (predict this
  year equals the historical average) is the best or tied-best model for these two crops in
  every tested lead time.
- Not causal, and not a substitute for the actual SAS survey once published; it is a
  best-available early guess for the gap period only.
- Not validated at the plot level; this is a district x crop x season model.
- Should not be used at a lead time or crop combination not in `config/settings.yaml`'s
  `nowcast.lead_months` ([2, 3, 4] months into the season) and MVP crop list.

## Data
- Target population: same district-level weighted yield estimates used elsewhere
  (`data/marts/district_yield.parquet`), restricted (per a 2026-09-24 fix) to rows where
  `reliability != "suppressed"` (fewer than the survey's `min_segments` PSUs). Rows flagged
  `"use_with_caution"` are kept.
- Predictors: partial-season MODIS NDVI (mean and peak) and CHIRPS rainfall at 2, 3, and 4
  months into each season, each compared against a real climatology (MODIS NDVI 2001 to 2018,
  CHIRPS rainfall 1991 to 2020) to produce an anomaly, plus the most recent prior-season district
  yield that would realistically have been published by that lead time's prediction date (not
  simply "last season," since NISR's own publication lag can put the immediately-preceding
  season's report inside the current season's growing period; see
  `docs/nowcast-feature-timing.md`).
- Years: 2019 to 2025, evaluated with leave-one-year-out cross-validation, so each crop has
  6 to 7 held-out years total (beans 7, maize 7, sorghum 7, Irish potato 6).
- Suppressed-cell exclusion (2026-09-24) removed 56% of all district-level rows overall before
  this fix, with wide variation by crop (maize 66%, Irish potato 73%, sorghum 48%, beans 25%
  suppressed); after exclusion, every crop still retains at least 58 rows per training fold.

## Target
`district_yield_anomaly`: this year's actual district x crop x season yield minus that same
group's historical mean yield, where the historical mean is always computed from the current
fold's training years only (never including the held-out year), per CLAUDE.md's no-target-leakage
rule. Evaluated on the reconstructed actual yield (historical mean plus predicted anomaly), not
on the anomaly directly, since a percentage error on a near-zero anomaly is not meaningful.

## Features
`ndvi_mean`, `ndvi_peak`, `ndvi_anomaly`, `rainfall_mm`, `rainfall_anomaly` (all specific to the
lead time being evaluated), and `prior_season_yield_kg_ha` (the most recent season's yield that
would have realistically been published by that lead time, per
`realistic_lookback_seasons()`).

## Method
Four models compared side by side at every crop x lead-time combination, per
`config/settings.yaml`'s `nowcast.models`:
- `baseline_district_mean`: predicts this district x crop x season's own historical mean
  (zero anomaly).
- `baseline_last_year`: predicts last year's same-season anomaly for this district x crop.
- `ridge`: a linear ridge regression on the anomaly, using the feature list above.
- `lgbm`: a small LightGBM (`n_estimators=50, num_leaves=7, min_child_samples=5`) on the same
  features.

Validated with leave-one-year-out cross-validation (never random K-fold on panel data), one
model refit per held-out year. `best_model_per_lead()` picks whichever of the four models
actually has the lowest MAPE for a given crop x lead time when serving the live nowcast, rather
than always preferring a "fancier" model regardless of whether it earns that choice.

## Validation scheme
Leave-one-year-out cross-validation, weighted summary: `summarize_cv()` averages MAPE and MAE
across held-out years, weighted by that year's test-row count, and also reports the unweighted
standard deviation of each model's per-fold MAPE across years, since a mean improvement that is
smaller than the year-to-year spread is not a meaningful improvement.

## Metrics (with baselines)
Row-count-weighted MAPE by crop and lead time, after all fixes (suppressed-cell exclusion, Season
A date-alignment correction, prior-season publication-lag correction), from
`data/public/nowcast_backtest.csv`:

| Crop | Lead (months) | baseline_district_mean | ridge | Better than baseline? |
|---|---|---|---|---|
| maize | 2 | 28.4% | 28.7% | No |
| maize | 3 | 28.4% | 28.9% | No |
| maize | 4 | 28.4% | 29.1% | No |
| beans | 2 | 20.6% | 20.5% | Marginal |
| beans | 3 | 20.6% | 20.0% | Marginal, consistent direction |
| beans | 4 | 20.6% | 20.2% | Marginal |
| Irish potato | 2 | 14.4% | 14.7% | No |
| Irish potato | 3 | 14.4% | 14.6% | No |
| Irish potato | 4 | 14.4% | 14.3% | Roughly tied |
| sorghum | 2 | 21.0% | 20.5% | Marginal (LightGBM does better here, see below) |
| sorghum | 3 | 21.0% | 20.1% | Marginal (LightGBM does better here, see below) |
| sorghum | 4 | 21.0% | 21.1% | No |

Checked year-by-year, not just on the point estimate (`docs/decisions.md`, 2026-09-24):

| Crop | Best lead/model | Mean improvement over baseline | Std across years | Wins in how many of 7 years |
|---|---|---|---|---|
| maize | none beats baseline | best case -0.30 percentage points (worse) | n/a | 2/7 |
| beans | ridge, lead 4 | +0.46pp | 0.63pp | 5/7 |
| Irish potato | ridge, lead 4 | +0.17pp | 1.02pp | 3/6 |
| sorghum | LightGBM, lead 2 | +3.16pp | 4.40pp | 6/7 |

**Plain conclusion: no crop, at any lead time, beats the naive district-mean baseline by a margin
that is large relative to the year-to-year spread.** Sorghum's LightGBM shows the largest mean
improvement, but its own variability (4.40pp) is bigger than the improvement itself (3.16pp).
That said, sorghum wins in 6 of 7 held-out years and beans' ridge wins in 5 of 7, both a
directionally consistent pattern even though the size of the win varies. Maize never beats
baseline at any lead time by any measure; Irish potato is close to a coin flip.

## Uncertainty method
A normal-approximation prediction interval (predicted plus or minus 1.96 times the
out-of-fold residual standard deviation, computed per model across every held-out year and
district in `residual_std_by_model()`). This is not a bootstrap, but it is an honest, already-
computed source for an interval, satisfying CLAUDE.md's requirement that every displayed number
carry one.

## Limitations
- **The core, honest finding is a null result for two of the four MVP crops** (maize, Irish
  potato): satellite NDVI/rainfall signal at these lead times does not currently explain enough
  district x crop x season yield variance to beat a simple historical average, at this sample
  size. This was investigated across four documented fix passes (Season A date alignment,
  prior-season publication-lag leakage, suppressed-cell exclusion, MAE reporting), each of which
  moved the numbers but did not change this fundamental conclusion.
- **Small n.** Only 6 to 7 held-out years per crop in leave-one-year-out CV, which sharply limits
  how confidently any "this model wins" claim can be trusted, even where sorghum and beans show a
  directionally consistent edge.
- **Not season-specific in a fully independent sense**: like the driver model, `season` enters
  as part of the grouping key but the API's `season` query parameter currently has no effect on
  which model or metrics are served (documented, not silently ignored).
- **MODIS 250m district-mean aggregation** may smooth out real within-district variation that a
  finer-resolution or plot-level signal could capture; not investigated further in this pass.
- Candidate structural reasons the signal is weak (genuinely weak relationship at this scale,
  insufficient training years, spatial aggregation, climatology season-boundary approximation)
  are logged but not all individually tested; what remains is considered a structural limitation
  of the available years of data, not a quick fix.

## Fairness and representativeness notes
- Suppressed low-reliability district x crop x season x year cells are excluded from both
  training and evaluation, which disproportionately removed maize (66%) and Irish potato (73%)
  rows relative to beans (25%) and sorghum (48%); this is why those two crops' backtests are
  based on a comparatively thinner, though now more honest, population.
- Small-scale, pure-stand farmers are the underlying survey population throughout, same as every
  other model in this pipeline; results describe that population, not commercial farms.
- No district is individually flagged unreliable at the nowcast-model level (reliability
  filtering happens at the input-row level, not as a separate per-district flag on the model's
  output); a district with mostly suppressed input rows for a given crop will simply have less
  influence on that crop's fitted model and fewer of its own predictions served.

## Version
- Data version: current `data/marts/district_yield.parquet` and GEE mart extractions
  (post Season-A date-alignment fix).
- Config: `config/settings.yaml` `nowcast` block (`lead_months: [2, 3, 4]`,
  `target: district_yield_anomaly`, `cv: leave_one_year_out`,
  `models: [baseline_last_year, baseline_district_mean, ridge, lgbm_small]`,
  `ndvi_climatology: [2001, 2018]`, `rainfall_climatology: [1991, 2020]`).
- Fix history (see `docs/decisions.md`, 2026-09-24): Season A date-alignment correction,
  prior-season publication-lag correction, suppressed-cell exclusion, MAE and per-year-std
  reporting added. Investigation of the underlying null result closed 2026-09-25 alongside the
  driver model's sorghum investigation, concluding the remaining gap is structural (limited
  held-out years), not a quick fix.
- Git commit: `68ac497` (2026-09-25).
