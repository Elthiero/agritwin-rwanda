# Decisions log

Record every methodological or architectural decision here. One entry per decision.

## Template

### YYYY-MM-DD: <short title>
- **Decision:**
- **Reason:**
- **Alternatives considered:**
- **Reversible:** yes/no

---

### 2026-09-23: Chose AgriTwin Rwanda as the hackathon project
- **Decision:** Build AgriTwin Rwanda (yield gap and early harvest estimator), Track 1.
- **Reason:** SAS microdata (2013 to 2025) is public-use and confirmed accessible; satellite inputs are free via Earth Engine; hits two named Tech Innovation examples (satellite analysis, predictive modelling).
- **Alternatives considered:** HarvestHub Rwanda, Vulnerability Radar, Imirenge Insight, FoodShield Rwanda.
- **Reversible:** No, past week 0.

### 2026-09-23: Confirmed NISR catalog IDs and Earth Engine access
- **Decision:** Lock in the NISR microdata catalog IDs for SAS 2019-2025 and AHS 2024, and confirm Earth Engine project access, as the recorded source of truth in `config/data_sources.yaml`.
- **Reason:** Verified directly against the live NISR catalog and a real `ee.Initialize()` plus dataset access test (`scripts/test_gee.py`), rather than assumed from the master plan's general data landscape table. MODIS NDVI, Sentinel-2 SR, CHIRPS, ESA WorldCover, three iSDAsoil bands and SRTM all returned expected band names and a working `reduceRegion` call.
- **Alternatives considered:** None, this is a verification step, not a design choice.
- **Reversible:** Yes, catalog IDs and dataset IDs can be corrected in `config/data_sources.yaml` if NISR restructures its catalog.

### 2026-09-23: Removed CI/CD pipeline
- **Decision:** Delete `.github/workflows/ci.yml` and `.github/workflows/refresh.yml`. No GitHub Actions pipeline for this project.
- **Reason:** Two-person team, 5.5-week deadline, no external contributors to gate. The checks a CI pipeline would run (lint, test, privacy check) are run locally and manually before every commit instead, per the development method section in `CLAUDE.md`. Satellite refresh becomes a manual `make gee` run rather than a scheduled job; scheduling it is explicitly deferred to the post-hackathon roadmap.
- **Alternatives considered:** Keeping a minimal CI (lint + test only, no scheduled job). Rejected: even a minimal pipeline adds setup and debugging surface (Actions runners, secrets, caching) that doesn't pay for itself at this team size and timeline.
- **Reversible:** Yes. If the team grows or the project continues past the hackathon, CI can be reintroduced; the removed workflow files are simple enough to recreate from the build guide if needed.

### 2026-09-23: Claude Code tooling excluded from the public GitHub repo
- **Decision:** Add `.claude/` and `CLAUDE.md` to `.gitignore`. Skills, subagents, settings, and every CLAUDE.md stay on disk for local development but are never committed or pushed.
- **Reason:** Keep the public repository focused on the product (pipeline, API, web app, docs) rather than the AI tooling used to build it. AI use is still disclosed as required by NISR rule 10, through `AI_DISCLOSURE.md` and `docs/ai-usage-log.md`, both of which remain tracked; this decision only concerns the Claude Code configuration files themselves, not the disclosure.
- **Alternatives considered:** Committing `.claude/` for transparency. Rejected per explicit preference for a clean public repo.
- **Reversible:** Yes, remove the two lines from `.gitignore` and commit the files if this changes later.

### 2026-09-23: 2019 SAS weight is segment-level, not plot-level
- **Decision:** Accept 2019 SAS weight variable (from PartIV_Agricultural practice.sav) as segment-level: one constant weight value per segment, varying across segments. This is structurally different from 2024+ which use plot-level `plot_weight`.
- **Reason:** Direct inspection of 2019 data: weight is labeled "Segment weight", is constant within each segment (verified across all ~2,800 unique segments), and exists only in the practice and fertilizer files, not in the production file where plot-crop data resides. This is consistent with a segment-sampling design followed by census of all plots within sampled segments. Attempting to treat it as plot-level would be incorrect and mislead the weighted ratio estimator.
- **Alternatives considered:** (1) Downweight or exclude 2019 from the pooled estimates. Rejected: segment-level weighting is valid for design-based inference; the issue is harmonization with later years, not invalidity of 2019 itself. (2) Derive a plot-level weight for 2019 by proportional allocation within segments. Rejected: would require plot-area proportionality assumptions and could introduce bias; better to document the structural difference and handle it at the estimation stage.
- **Reversible:** Yes. If the survey methodology changes to plot-level sampling in later years (confirmed by inspection), or if a methodologist determines that segment-level weights should be redistributed to plots, this can be revised. For now, it is a documented structural difference flagged in `docs/data/variable_audit.md` and in `config/sas_variable_map.yaml` comments.
- **Impact on pipeline:** The `src/agritwin/harmonize/` step must join the three 2019 files on (Segment_ID, plot_id) and attach the segment-level weight to every plot in the segment. When pooling 2019-2025 for district-level estimates, the weight column carries the design information (segments as PSUs); if future years use plot-level weights, the column definition must be clarified in the model card and variance estimation must be revisited.

### 2026-09-23: 2019 segment-level vs 2020+ plot-level weighting requires stratified design
- **Decision:** Estimate 2019 (segment-weighted) and 2020–2025 (plot-weighted) as separate design strata. Do not pool them naively.
- **Reason:** Survey methodologist review (2026-09-23) verified both designs are unbiased for point estimates but produce different variance structures. **Critical risk:** naive pooling using a single PSU bootstrap will underestimate variance in 2020+ because it ignores within-segment plot-level weight variation. Methodologist reported 2020 weight structure (77.8% of segments show variation across plots). Post-review individual verification of 2021–2025 computed: 2021 76.9%, 2022 76.0%, 2023 76.4%, 2025 ~76% segment weight variation, confirming the 2020–2025 block is homogeneous. This is contrasted with 2019: 1.6% of segments show weight variation (i.e., 98.4% constant), confirming segment-level design. The structural difference creates false precision risk: confidence intervals will be narrower than they should be if years are naively pooled, risking overconfident policy recommendations. Stratified design preserves 24k plots from 2019 (both seasons) for robust attainable-yield percentiles while respecting each year-block's actual design.
- **Alternatives considered:** (1) Harmonize 2019 to plot-level by proportional allocation (rejected: introduces bias if proportionality fails; loses design information). (2) Exclude 2019 (rejected: loses 12k plots/season, blocks nowcast backtests). (3) Advanced Hartley-Rao formula (rejected: too complex for 5.5-week timeline). Methodologist endorsed stratified approach as statistically sound and implementable.
- **Reversible:** Yes. If 2021-2023 audits reveal a multi-year block with segment weighting (2019–2021, say), the strata can be redrawn accordingly. If a future variance formula is developed to handle mixed designs, pooling could be revisited.
- **Impact on pipeline:** The `src/agritwin/survey/` module must accept a `design_year_blocks` parameter (e.g., {2019: 'segment', 2020–2025: 'plot'}) and compute separate design objects per block. Weighted ratio estimator and PSU bootstrap are computed independently per block; district-level results are labelled with design provenance ("2019 segment-weighted; 2020–2025 plot-weighted"). Export and web UI should surface this to users, avoiding the appearance of false precision.

### 2026-09-23: harvest_kg sources from s2q21, not s2q22, in every year
- **Decision:** Canonical `harvest_kg` in `stg_sas_plot_crop` is always sourced from s2q21 ("total quantity of harvest for this season"), never from s2q22 ("total quantity produced/to be produced by this crop this season"), across all 7 years.
- **Reason:** This was an open, unresolved question carried since the 2024 audit. Cross-tab run 2026-09-23 on pure-stand plots (2023, 2024, 2025 Season A) shows s2q21 and s2q22 are not equivalent: only 33-37% exact match, median relative difference ~33%, and the s2q22/s2q21 ratio is systematically greater than 1 (median 1.5x). The question wording explains this: s2q22 asks for quantity "produced/**to be** produced," which reads as projected or expected total production (including not-yet-harvested amounts), not the actual quantity harvested to date. Using s2q22 for a yield estimator would inflate actual yield with unharvested projections. s2q21 is also universally present across 2019-2025, while s2q22 as a separate crop-level column only exists 2023-2025, so using s2q21 avoids a second harmonization discontinuity on top of the 2019 weight-structure one.
- **Alternatives considered:** (1) Use s2q22 for 2023-2025 and s2q21 for 2019-2022 (rejected: introduces a within-schema definitional break exactly where the questionnaire gained a second harvest column, compounding interpretation risk for anyone comparing years). (2) Average or min(s2q21, s2q22) (rejected: fabricates a number with no basis in what was actually measured; the two questions measure different things, not the same thing with noise). (3) Leave harvest_kg null for years/rows where s2q21 is missing but s2q22 is present, rather than falling back to s2q22 (adopted as a corollary: no silent substitution across definitionally different fields).
- **Reversible:** Yes. If a later cross-tab against ground truth (e.g., AHS or a validation subsample) shows s2q22 is the better-calibrated field for a specific year, this can be revisited per year.
- **Impact on pipeline:** `src/agritwin/harmonize/` maps canonical `harvest_kg` from s2q21 only. s2q22 is not consumed anywhere in the harmonize output; it remains documented in `docs/data/variable_audit.md` as a rejected candidate, not as an alternate source.

### 2026-09-23: Collapsed ingest/ and harmonize/ into one layer
- **Decision:** Drop the planned `ingest/` module and typed `data/interim/` layer. `harmonize/` reads raw `.dta`/`.sav` files directly with pyreadstat and produces `data/staging/` in one step. `src/agritwin/CLAUDE.md`'s layer table and module responsibilities updated accordingly; the vestigial `ingest` Makefile target removed from `make all`.
- **Reason:** `ingest/` was never built; only `harmonize/` exists, and it already reads raw files itself (`harmonize/io.py`), including the metadata-only pass that captures value labels for `farmer_type`/`erosion_degree`. A separate interim Parquet layer would exist purely to satisfy the original two-layer design, not because the pipeline needs it: 7 years of SAS microdata reads in seconds per file, there is no repeated-read cost an interim cache would amortize, and `harmonize/` already logs row counts per step per `CLAUDE.md` rule 4. Keeping a second layer around for a data volume this small is overhead with no payoff.
- **Alternatives considered:** (1) Build `ingest/` now for symmetry with the original design. Rejected: no consumer needs interim Parquet, and the value-label capture problem it was meant to solve is already solved inside `harmonize/`. (2) Keep the Makefile `ingest` target as a no-op passthrough. Rejected: a no-op target that never runs anything is confusing scaffolding, not a real step.
- **Reversible:** Yes. If a future raw format (e.g. very large AHS files) makes a cached typed-interim step worth it, `ingest/` can be reintroduced without touching `harmonize/`'s canonical output contract.

### 2026-09-23: CLOSED — district_code (SAS) to GAUL district (GEE mart) crosswalk built
- **Status: closed.** Resolves the open item below.
- **Decision:** Built `data/reference/district_crosswalk.csv` (30 rows: `nisr_district_code,
  district_name, province, hdx_pcode, gaul_code`), sourced from HDX's COD-AB Rwanda admin2
  boundaries (see `docs/data-sources.md` for the exact source URL, download date, and license).
  Re-keyed all five existing `data/external/gee/*.csv` outputs (`ndvi_district_season`,
  `rainfall_district_season`, `cropland_fraction_district`, `soil_district`,
  `feat_district_season_joined`) with `nisr_district_code`, additively (no rows or existing
  columns removed, only the new column added). Wired `src/agritwin/gee/` so future extraction
  runs (`hdx_districts_fc()` in `boundaries.py`) use the HDX-derived FeatureCollection natively
  keyed on `nisr_district_code`, instead of GAUL, confirmed working against live Earth Engine
  (`fetch_cropland_fraction_district_stats` returned 30 correctly-keyed rows in this session).
- **Reason the join turned out simpler than expected:** NISR's `district_code` value labels
  (read directly from all 7 SAS years' raw `.dta`/`.sav` files, metadata-only) are **identical**
  in code and spelling to HDX's `ADM2_PCODE` numeric suffix and `ADM2_EN` name, for all 30
  districts, across 2019-2024 with zero discrepancy. The only spelling variant found anywhere:
  2025's SAS district_code 11 is labeled "Nyarugenege" (a typo, extra "e") instead of
  "Nyarugenge"; the crosswalk stores the correct spelling and this is the only reconciliation
  needed. GAUL's `ADM2_CODE` (already used to key the existing GEE outputs) also matches all 30
  HDX/NISR district names exactly by string equality, so `gaul_code` was added to the crosswalk
  as a bridge rather than needing its own reconciliation pass.
- **Why HDX and not a custom EE asset upload:** the task requested extraction "on the HDX polygons
  (as an Earth Engine asset)". Rather than uploading the shapefile as a persisted EE table asset
  (requires a GCS bucket intermediary and async ingestion, an ongoing asset-management dependency),
  `hdx_districts_fc()` builds the `ee.FeatureCollection` client-side from the committed, simplified
  GeoJSON (`data/public/geo/districts_adm2.geojson`, ~256 KB, well under the 5 MB threshold and the
  FeatureCollection payload limit for 30 simplified polygons). This gives every property
  (`nisr_district_code`, `district_name`, `province`, `hdx_pcode`) natively on every extraction
  result with no separate asset to provision, refresh, or lose access to.
- **Alternatives considered:** (1) Fuzzy name-matching between SAS and GAUL district names directly,
  skipping HDX. Rejected before starting: GAUL names could differ in spelling or Kigali
  sub-division from NISR's names (the original open item's stated risk), and turned out unnecessary
  once HDX's independently-sourced P-codes gave an exact numeric match, but going through HDX
  instead of GAUL directly still avoids relying on an unverified assumption that GAUL's own names
  are stable. (2) Upload the HDX shapefile as a persisted EE table asset. Rejected: heavier
  dependency (GCS, ingestion, quota) for no benefit over a client-side FeatureCollection at this
  small scale (30 features).
- **Reversible:** Yes. The crosswalk is additive; nothing that depended on `gaul_district_code`
  was removed, so a decision to standardize fully on one boundary source later does not require
  redoing this work.
- **Impact on pipeline:** `src/agritwin/features/` can now join SAS-derived (`clean/`, `survey/`,
  once built) district estimates to the GEE mart on `nisr_district_code` directly, no further
  crosswalk needed. `src/agritwin/gee/run.py`'s `run_ndvi_rainfall`, `run_cropland`, `run_soil`
  now build their region set from `hdx_districts_fc()`; `run_boundaries()` (which still writes
  `data/external/boundaries/rwanda_districts.geojson`, served by the API's `/geo/districts`
  endpoint) was left on GAUL, since switching the API's boundary source is a separate, unrequested
  decision — `data/public/geo/districts_adm2.geojson` is available whenever that switch is made.
  Historical NDVI/rainfall/soil/cropland values in the re-keyed CSVs were **not** re-extracted
  against the new polygon source in this session (that is a real Earth Engine compute cost,
  deliberately not spent without being asked); only the district key was added.

### 2026-09-23 (superseded above): OPEN ITEM — district_code (SAS) to GAUL district (GEE mart) is unreconciled
- **Status: open, blocking.** Not a decision yet, logged here so it is not lost as a "someday" item.
- **Problem:** `stg_sas_plot_crop` (from `src/agritwin/harmonize/`) keys districts on NISR's numeric `district_code` (from s1q2, 30 values) and currently writes `district_name` as null. The already-built GEE feature mart (`data/external/gee/*.csv`, produced by `src/agritwin/gee/`) keys districts on `district_name` (string, e.g. "Bugesera") and `gaul_district_code` (FAO GAUL admin2 code, e.g. 21974). **No shared key exists between the two tables today.** This was already flagged as unresolved in `config/data_sources.yaml`'s `gaul_districts` entry ("ADM2_CODE is GAUL's own code, not the NISR survey district_code, and is not yet reconciled to it"), but that note undersold it as an ambient caveat rather than a build blocker. It is a blocker: per `CLAUDE.md` golden rule 4 ("No naive joins across surveys... SAS, AHS and satellite features meet only at district x season x year level"), the `features/` step (`feat_district_season`) cannot join SAS-derived survey estimates to GEE-derived satellite features without this crosswalk, and `export/` cannot label a map polygon with a SAS-derived yield-gap number without it either.
- **Why this wasn't caught earlier:** The GEE mart was built and validated independently (district x season NDVI/rainfall, `gaul_districts` boundary fetch) before the SAS harmonize step existed, so the district-key mismatch had no consumer to surface it until now. `district_name` was left null in harmonize deliberately (see the 2026-09-23 harmonize implementation commit), which is correct as far as it goes, but a null column understates that this is a required, not optional, follow-up.
- **What resolving this requires:** A `district_code` (NISR, int) <-> `district_name`/`gaul_district_code` (GAUL) crosswalk table, built once (30 rows, Rwanda has 30 districts) and versioned in `config/` (e.g. `config/district_crosswalk.yaml` or a small CSV), not re-derived ad hoc in `features/` or `export/`. Rwanda's district boundaries and names are stable and small in number, so this is a short, mostly-manual reconciliation (match by name, resolve any spelling/admin-boundary differences, e.g. Nyarugenge vs old sector names), not a algorithmic geocoding problem.
- **Alternatives considered:** (1) Join SAS and GEE data by district_name string match with no explicit crosswalk table (rejected: fragile, silently wrong on any spelling mismatch, and violates the "no naive joins" rule by construction). (2) Defer until `features/` is built and let that step discover and fix the mismatch (rejected per this open item: better to fix once, upstream, than have every downstream consumer of both tables independently rediscover the same gap).
- **Reversible:** Yes, it is additive (a new small config file); nothing currently built depends on district_code/district_name matching, so there is no rework once the crosswalk exists.
- **Owner / next step:** Build the crosswalk before starting `src/agritwin/features/` (which is the first step that needs to join SAS-derived and GEE-derived district tables). Not yet assigned to a session.
