# AgriTwin Rwanda — Project Status

Updated 2026-09-24. Supersedes the 2026-09-23 version of this file, which described `clean/`, `survey/`, and `models/` as missing and estimated MVP completion at 20-25%. That is stale; this version reflects the real, current state, pulled from the actual repo (file listings, `git log`, `pytest`, real pipeline runs), not from memory.

## Summary

66 commits, all still on a single compressed development arc. The full data pipeline now runs end to end on real data: SAS microdata harmonization, yield/QC cleaning, survey-weighted district estimates (validated against a real published NISR report), satellite feature extraction including climatology and lead-time cutoffs, attainable yield and yield gap, a driver model (LightGBM + SHAP) per crop, and a nowcast model with a leave-one-year-out backtest. A round of external review this session found and fixed four real correctness bugs in the nowcast (a satellite date-alignment error, feature leakage, and survey-noise contamination of the training target) and reported the results honestly, including where the models do not beat a naive baseline. 133 tests pass, `ruff`/`mypy` clean. The API has grown from 2 to 5 of the ~9 planned endpoints (`/drivers` and `/backtest` added; both found and documented, rather than papered over, a real gap: neither the driver model nor the nowcast ever split by season). `make lint && make test` is fully green across the whole repo for the first time this session: the web app's `tsc`, `eslint`, and `vitest` all pass now (a missing `vite-env.d.ts`, `noEmit` in `tsconfig.json`, a real GeoJSON type instead of a hand-rolled one, an ESLint config, and one real test file). It is still a single unrouted page with no real product pages yet. `models/scenario.py` and `export/` do not exist yet. Rough MVP completion: **~60-65%** — the entire data-to-model pipeline is real, tested, and honestly validated; what's missing is mostly the presentation layer (API surface, web app) and the scenario/export modules.

## What is built and working

- **`src/agritwin/harmonize/`**: joins all 7 SAS years (2019-2025, Seasons A/B) into `stg_sas_plot_crop`, plus confidence and value-label sidecars.
- **`src/agritwin/clean/`**: adds `yield_kg_ha` and a priority-ordered `qc_flag` (missing data, zero/too-small area, not pure-stand, not SSF, above plausibility cap, outlier, ok).
- **`src/agritwin/survey/`**: Taylor-linearized (`samplics`), design-based weighted estimates at district/province/national x crop x season x year, with a three-tier reliability flag (`ok`/`use_with_caution`/`suppressed`). **Validated against the real NISR SAS 2025B report**: national maize yield 1,400 kg/ha (ours) vs 1,300 kg/ha (official), 7.7% off, inside our own 95% CI (`docs/validation.md`).
- **`src/agritwin/gee/`**: MODIS NDVI, CHIRPS rainfall, ESA WorldCover cropland, iSDAsoil, Rwanda district boundaries, a real NISR district_code <-> HDX/GAUL crosswalk, long-run climatology (MODIS 2001-2018, CHIRPS 1991-2020), and lead-time (partial-season) extraction for the nowcast. A real Season A date-alignment bug (satellite data was reading a full season ahead of the actual survey period, confirmed against NISR's own SAS 2025 Season A report) was found and fixed this session; see `docs/decisions.md` 2026-09-24.
- **`src/agritwin/models/attainable.py`**: k-means zoning (no AEZ layer is configured anywhere in this repo, the build guide's own documented fallback) and weighted-90th-percentile attainable yield, plus yield gap.
- **`src/agritwin/models/drivers.py`**: one LightGBM + SHAP model per MVP crop, GroupKFold by district, against a fold-safe naive baseline. 3 of 4 crops beat baseline (irish_potato +20.0%, beans +5.4%, maize +5.0%); **sorghum does not (-4.4%)**, reported plainly rather than tuned away.
- **`src/agritwin/models/nowcast.py`**: NDVI/rainfall anomaly + realistic prior-season-yield feature (which season is used depends on lead time and whether NISR would actually have published it by then, per `docs/nowcast-feature-timing.md`), leave-one-year-out CV, MAPE and MAE reported for two naive baselines plus ridge and LightGBM. **Honest verdict**: no crop beats the naive district-mean baseline by a margin large relative to the year-to-year spread; sorghum (LightGBM) and beans (ridge) show a real but modest, noisy directional edge, maize and irish potato do not (`docs/decisions.md` 2026-09-24).
- **`data/public/`**: 7 real files now exist — `district_yield.csv`, `yield_gap.csv`, `district_zones.csv`, `drivers.csv`, `drivers_by_district.csv`, `nowcast_backtest.csv`, and `geo/districts_adm2.geojson`. All pass `scripts/check_public.py`.
- **API** (`api/app/`): `GET /health`, `GET /api/v1/districts` (now also carries the NISR `district_code` alongside `gaul_district_code`, joined server-side from `data/reference/district_crosswalk.csv`, see `docs/decisions.md` 2026-09-24), `GET /api/v1/yield-gap`, `GET /api/v1/drivers`, `GET /api/v1/backtest` (crop/season/year filtered, every row including `"suppressed"` ones returned with a reliability flag rather than silently dropped, per `CLAUDE.md` golden rule 6). Live-verified with a real `uvicorn` run, not just unit tests. A real `DATA_DIR` semantics bug (the real `.env` config pointed at the wrong subfolder) was found and fixed via this live check.
- **Compliance**: no raw microdata, secrets, or credentials anywhere in git history (checked across all commits, not just recent ones). `docs/ai-usage-log.md` now has real entries for every session, not just a header row. `NOTICE` (IP transfer + third-party licenses) exists. `CONTRIBUTING.md` exists.
- **Docs**: `docs/decisions.md` (23 dated entries), `docs/survey-design.md`, `docs/data-sources.md`, `docs/validation.md`, `docs/nowcast-feature-timing.md`, `docs/data/variable_audit.md`, `AI_DISCLOSURE.md`, `ORIGINALITY.md`.

## What is partial or broken

- **`src/agritwin/features/gee_mart.py`**: still only joins GEE outputs to each other. Investigated this session (see `docs/decisions.md` 2026-09-24): its output, `feat_district_season_joined.csv`, has no consumer anywhere in the repo — `models/run.py` reads GEE features and district_yield separately and joins them itself. Building the SAS-side join here would be speculative; either wire a real consumer to it or consider the file dead output.
- ~~`stg_sas_plot_crop.district_name`: still null~~ — fixed this session. `harmonize/run.py` now joins `data/reference/district_crosswalk.csv` onto the stacked table; re-ran `make stage` on real 2019-2025 data, all 513,369 rows across 30 districts got a non-null name, zero unmatched. `survey/`'s public `geo_code` is still a raw numeric code, not a label — a separate, smaller follow-up if the API/web layer ever wants district names straight from `survey/` output rather than joining `/districts`' `district_code` client-side.
- **API**: 5 of ~9 endpoints (`/health`, `/districts`, `/yield-gap`, `/drivers`, `/backtest`). `/kpis`, `/districts/{code}/profile`, `/nowcast`, `/nowcast/{code}/curve`, `/scenario/{code}`, `/briefs/{code}.pdf` are unimplemented. `/nowcast` is genuinely blocked on new modeling work (a per-district-per-year prediction endpoint, not just a backtest summary); the rest are mechanical once their underlying data/model exists.
- **Web app**: `tsc`, `eslint`, and `vitest` all pass. First real product page shipped this session: `pages/MapPage.tsx`, a district yield-gap choropleth (crop/season/year filter bar, hover tooltip, low-reliability cells shown grey, "Model-based estimate" badge), routed via `react-router-dom` and backed by TanStack Query hooks in `api/hooks.ts` calling the live `/districts` and `/yield-gap` endpoints. Live-verified in a real browser, not just unit tests. Still only one route; no i18n wired up despite the dependencies being installed, no other pages (`DistrictPage`, `EarlyEstimatePage`, etc. from `web/CLAUDE.md`'s planned structure) exist yet. `npm install` succeeds locally, with 12 unaddressed vulnerabilities (unchanged).
- **`docs/data/questionnaires/`**: still empty.

## What is missing vs. the plan

| Module | Status |
|---|---|
| `models/scenario.py` — precomputed lever grid | **Missing** |
| `export/` — PDF briefs, per-crop simplified GeoJSON | **Missing** |

`models/run.py` currently writes directly to `data/public/`, standing in for a formal `export/` step. Whether to build `export/` as originally scoped or keep this pattern is an open decision, not yet made.

## Compliance and security findings

1. **No raw microdata in git history.** Re-confirmed across all 66 commits, not just the ones since the last audit. **Clean.**
2. **No secrets in git history.** Re-confirmed. **Clean.**
3. **AI disclosure**: `docs/ai-usage-log.md` now has a real entry per session (previously flagged as empty). `AI_DISCLOSURE.md` and `ORIGINALITY.md` remain substantive.
4. **`NOTICE` now exists** (IP transfer to NISR + third-party data licenses), resolving the previous audit's finding.
5. **`LICENSE` now exists** (MIT, confirmed with the team; the hackathon's own IP-transfer rule was independently checked live against the actual NISR hackathon page and imposes no constraint on which license the repo displays before submission), resolving the previous finding.
6. **No code that looks copied from elsewhere**, same finding as before, re-confirmed against everything built since.
7. **`web/` npm audit**: 12 vulnerabilities (3 critical, 7 high, 2 moderate), still not triaged.

## Technical debt and quick wins

- ~~`web/tsconfig.json`, Vite client types, ESLint config, and test files~~ — fixed this session.
- `stg_sas_plot_crop.district_name` should be wired from the crosswalk now that it exists, rather than left null. (S)
- `features/gee_mart.py` should join the SAS-side district estimates now that the crosswalk exists. (M)
- `docs/data/questionnaires/` is still empty; depends on NISR providing the questionnaire PDF. (M, external dependency)
- `api/app/data_store.py` still loads district boundaries from `data/external/` directly rather than `data/public/`, an inconsistency flagged in the previous audit and still unresolved (harmless, since boundaries aren't sensitive, but worth a deliberate decision).
- The driver model's `sorghum` underperformance and the nowcast's largely-null-result verdict are not technical debt to "fix" by tuning; they are honest findings that should be carried into any model card or UI copy rather than glossed over.

## Recommended next tasks, ordered by judging-impact

Judging: Problem relevance, Data and methodology, Tech innovation, Usability, Tangible impact (20 pts each).

1. **Wire `/drivers` and `/nowcast` API endpoints** off the data that already exists in `data/public/`. *Usability, Tangible impact.* — **S**, no longer blocked on missing data.
2. ~~Fix the web app's build/lint/test toolchain~~ — done this session.
3. ~~Ship one real end-to-end page~~ — done this session (yield-gap map). The `/districts` vs `/yield-gap` district-code join is now done server-side too (see `docs/decisions.md` 2026-09-24).
4. ~~Wire `district_name` into `stg_sas_plot_crop`~~ — done this session. `features/gee_mart.py`'s SAS-side join turned out to have no consumer (see `docs/decisions.md` 2026-09-24); not built, flagged as a separate open question instead.
5. **`models/scenario.py`**: precomputed lever grid for the scenario explorer. *Tech innovation.* — **M**
6. **`export/`**: formalize the public-output step (PDF briefs, per-crop GeoJSON), or make an explicit decision to keep the current `models/run.py`-writes-directly-to-`data/public/` pattern instead. *Tangible impact.* — **M**
7. **Investigate why sorghum's driver model and the nowcast overall don't beat baseline**, rather than treating the current honest-but-null result as final. Candidates already logged in `docs/decisions.md`: sample size, spatial aggregation smoothing, insufficient hyperparameter tuning. *Data and methodology.* — **L**
8. ~~LICENSE file~~ — done this session (MIT).
9. **Deploy and smoke-test** the API and web app somewhere real, per the project's own "deploy by hand, early and often" development method, not yet done at all. *Tangible impact.* — **M**
10. **`docs/data/questionnaires/`**: request the SAS questionnaire PDFs from NISR to independently confirm the 2025 low-confidence column matches and the 2021 stratum-code resolution. *Data and methodology.* — **M**, external dependency
