# Model card: Attainable yield and yield gap

## Purpose
Estimates, for each zone x crop x season, the yield level that the best-performing 10 percent
of pure-stand plots already achieve. This "attainable yield" is compared against the survey's
actual district yield to produce the yield gap shown on the map and district pages: how much
higher yield could plausibly go if a district matched what already happens on the best plots
nearby, not some theoretical agronomic maximum.

This is not a trained machine-learning model in the usual sense. It has two parts: a one-time
k-means grouping of districts into five zones, and a survey-weighted 90th-percentile
calculation per zone x crop x season, pooled across 2019 to 2025.

## Intended users and uses
- District agronomists and NISR/MINAGRI staff using the yield-gap map and district profile
  pages to see which crop x season combinations in their district have the most room to close
  the gap toward already-achieved local performance.
- Feeding the scenario explorer, which shows model-based "what if" adjustments relative to this
  same attainable ceiling.

## Out of scope uses
- Not a recommendation of a specific target yield for an individual farmer or plot; it is a
  district x zone level statistic built from many plots pooled together.
- Not causal. It does not say what practice change would close the gap, only how large the gap
  is. The driver model (`drivers.py`) is the separate, explicitly associative tool for "what is
  associated with higher yield."
- Not an agro-ecological zone map. The "zone" here is a k-means grouping on soil and cropland
  features, a documented fallback (see Method), not an authoritative AEZ boundary.
- Should not be used for crops or seasons outside the MVP list (maize, beans, Irish potato,
  sorghum, rice) or outside 2019 to 2025.

## Data
- Source: harmonized SAS plot-crop records (`stg_sas_plot_crop`), restricted to pure-stand
  plots with `qc_flag == "ok"`, non-null crop, and positive survey weight (same eligibility
  filter as the district actual-yield estimator, so the two sides of the gap are computed from
  the same population).
- Years: 2019 to 2025 (Seasons A and B), pooled together. Attainable yield is not year-specific;
  it represents a stable ceiling for the zone/crop/season, not a per-year figure.
- Zoning inputs: district-level static features from the GEE mart, iSDAsoil (`soil_ph`,
  `soil_nitrogen`, `soil_carbon`, `soil_texture_class`) and ESA WorldCover (`cropland_fraction`),
  covering all 30 districts.
- Current production run (`data/marts/attainable_yield.parquet`): 48 zone x crop x season
  groups, 43 flagged `"ok"` and 5 `"suppressed"`. Per-group weighted plot counts (`n_plots`) and
  PSU counts (`n_segments`) are stored alongside each estimate.

## Target
`attainable_yield_kg_ha`: the survey-weighted 90th percentile of `yield_kg_ha` among eligible
pure-stand plots in a given zone x crop x season group. `yield_gap_kg_ha` and `yield_gap_pct`
(attainable minus the district's actual weighted yield for a given year) are derived from it.

## Features
Zoning uses five district-level static features (soil pH, soil nitrogen, soil carbon, soil
texture class, cropland fraction), standardized before k-means. The percentile itself is
computed only from plot yield and its survey weight; no other covariates enter the percentile
calculation.

## Method
1. **Zoning (k-means fallback):** No agro-ecological zone boundary layer is configured anywhere
   in this repo (checked `config/data_sources.yaml` and `data/external/`). The build guide's
   documented fallback applies: k-means (`k=5`, `random_state=0`) on standardized district-level
   soil and cropland features. See `docs/decisions.md`, 2026-09-23, "Attainable yield zoning
   uses k-means, not an AEZ layer." Deterministic given the fixed random state; zone IDs are
   arbitrary labels, not ranked or meaningful beyond grouping.
2. **Percentile:** `weighted_percentile()` uses the midpoint-interpolation method for a
   survey-weighted quantile (matches, e.g., statsmodels' `DescrStatsW.quantile`), pooled across
   all years present for that zone x crop x season group.
3. **Yield gap:** each district is joined to its zone, then to that zone's attainable yield for
   the matching crop and season. Gap is computed whenever both point estimates exist, regardless
   of reliability tier (a low-reliability cell is flagged and greyed out per CLAUDE.md golden
   rule 6, not hidden). Reliability on the gap row is the worse of the actual-yield and
   attainable-yield reliability tiers.

## Validation scheme
No holdout or cross-validation: this is a descriptive population statistic (a weighted
percentile), not a fitted predictive model, so there is nothing to validate out-of-sample in the
usual ML sense. Correctness is instead checked by unit tests on synthetic data
(`tests/test_attainable.py`): weighted-percentile correctness against `numpy.percentile` under
uniform weights, monotonic response to weight skew, order-independence, deterministic and
complete zone assignment, correct pooling across years, correct suppression below
`min_segments`, and correct gap computation and reliability propagation including the "kept,
not dropped" low-reliability case.

## Metrics (with baselines)
Not applicable in the predictive-accuracy sense (no train/test split, no error metric). The
relevant "metric" is sample adequacy per group, reported directly in the output:
`n_plots`, `n_segments`, `n_years` per zone x crop x season. Current production run: 43 of 48
groups (90 percent) meet the reliability bar; 5 are suppressed for having too few PSUs
(`n_segments < min_segments`).

## Uncertainty method
None of the interval kind. `samplics.estimation.TaylorEstimator` does not expose an
arbitrary-percentile Taylor-linearized variance (only `PopParam.median`), and a PSU bootstrap
for a 90th-percentile confidence interval was deferred, not built, for this pass (see
`docs/decisions.md`, 2026-09-23, "No confidence interval on attainable yield"). Instead, a
`reliability` flag (`ok` / `suppressed`) based on the same `min_segments` PSU-count floor used
elsewhere satisfies CLAUDE.md golden rule 6's requirement that every displayed number carry
either an interval or a reliability flag. A future pass could add a bootstrap CI without
changing the existing output columns.

## Limitations
- The 90th percentile is a "what the best plots already do" ceiling, not an agronomic maximum;
  it can shift if the small number of top-performing plots in a thin group changes.
- Zones are a k-means convenience grouping on two data sources (soil, cropland), not a validated
  agro-ecological classification. Two districts in the same k-means zone may still differ in
  ways relevant to attainable yield that these five features don't capture.
- Pooling across 2019 to 2025 assumes attainable yield is roughly stable over that window; a
  structural shift (new seed variety release, major climate event) partway through would be
  averaged over rather than detected.
- No confidence interval, only a suppression flag; two "ok" attainable-yield figures are not
  guaranteed to be statistically distinguishable from each other.

## Fairness and representativeness notes
- Small farms dominate the pure-stand plot population by construction (pure-stand, small-scale
  farmer plots are the survey's design target), so the attainable ceiling reflects small-farm
  practice, not commercial or large-scale farms.
- 5 of 48 zone x crop x season groups (10 percent) are suppressed for too few PSUs; those cells
  show no attainable yield or gap on the map rather than an unreliable number. Irish potato and
  rice groups, being less widely grown, are more likely to fall into thin-sample zones than
  maize or beans.
- Because zones are built from district-level averages, a district that is genuinely
  heterogeneous internally (mixed soil quality, mixed cropland fraction) is represented by one
  average zone assignment; no district is split across zones.

## Version
- Data version: `data/marts/attainable_yield.parquet`, `data/marts/yield_gap.parquet`, current
  as of the 2019 to 2025 SAS harmonization and the GEE mart used for zoning.
- Config: `config/settings.yaml` `attainable` block (`percentile: 90`, `zone_method: kmeans`,
  `kmeans_k: 5`, `min_segments: 10`).
- Git commit: `68ac497` (2026-09-25).
