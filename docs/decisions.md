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
