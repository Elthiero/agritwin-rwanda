# AgriTwin Rwanda — Project Status

Audit date: 2026-09-23. Read-only audit, no code changed in this session.

**Note on scope:** the task brief for this audit referenced `docs/NISR_2026_Hackathon_Master_Plan.md` (Sections 8 and 9) as the target to measure against. That file does not exist in this repository (checked with `find . -iname "*master_plan*" -o -iname "*NISR_2026*"`, no match). The only planning document that exists is `docs/AgriTwin_Master_Build_Guide.md`, which is what `CLAUDE.md` actually tells contributors to read, and what all 28 commits to date were built against. This report measures against that document instead, and flags every point where the task brief's assumptions (crops, stack, endpoints) diverge from what's actually specified in this repo, rather than silently substituting one for the other.

## Summary

All 28 commits are dated 2026-09-23 (today) — this is week 0, a single day of compressed development, not week 5 of a 5.5-week build. The harmonization layer for SAS microdata is solid and well-tested (38 passing pytest tests, `ruff`/`mypy` clean). The GEE satellite pipeline runs end-to-end and produces a district-level feature CSV. Everything downstream of that — yield computation (`clean/`), survey-weighted estimation (`survey/`), the SAS↔GEE district join, model training (`models/`), and public export (`export/`) — does not exist yet as code. The API has 2 of ~9 planned endpoints (health + district boundaries only), and the web app is a single unrouted page rendering a MapLibre basemap with no real product pages, and it currently fails `tsc`, `eslint`, and `vitest`. No compliance red flags: no raw microdata, secrets, or committed credentials found anywhere in git history. Rough MVP completion: **~20–25%** — the hard data-harmonization foundation is genuinely done and correct, but the yield/model/UI layers that the judging criteria mostly score are not started.

## What is built and working

- **`src/agritwin/harmonize/`** (`core.py` 311 lines, `io.py`, `run.py`): joins SAS production/practice/fertilizer files for all 7 years (2019–2025, Seasons A/B) into `stg_sas_plot_crop`, plus two sidecars (`stg_sas_variable_confidence`, `stg_sas_value_labels`). 17 dedicated tests in `tests/test_harmonize.py`, all passing. Real output verified present at `data/staging/stg_sas_plot_crop.parquet`.
- **`src/agritwin/gee/`** (`boundaries.py`, `extract.py`, `periods.py`, `scaling.py`, `run.py`): pulls MODIS NDVI, CHIRPS rainfall, ESA WorldCover cropland fraction, and iSDAsoil bands via Earth Engine, and Rwanda's 30 district boundaries with GAUL codes. Outputs exist and are populated: `data/external/gee/ndvi_district_season.csv` (421 rows), `rainfall_district_season.csv` (421), `cropland_fraction_district.csv` (31), `soil_district.csv` (31), `data/external/boundaries/rwanda_districts.geojson`. 6 test files covering scaling, periods, boundaries, extract, mart join, and rainfall plausibility, all passing.
- **`src/agritwin/features/gee_mart.py`**: joins the four GEE CSVs into one district×season×year table (`feat_district_season_joined.csv`, 421 rows). This is GEE-side only; no SAS join.
- **API** (`api/app/`): FastAPI app starts cleanly (verified with `uvicorn api.app.main:app`), serves real data, not mocks — `GET /health` returns `{"status":"ok","data_version":"2026.10.0"}`, `GET /api/v1/districts` returns the actual 30-district GeoJSON loaded from `data/external/boundaries/`. 1 passing test (`api/tests/test_geo.py`).
- **Compliance structure**: `.gitignore` correctly excludes `data/raw/`, `data/interim/`, `data/staging/`, `data/marts/`, `artifacts/`, `*.dta`, `*.sav`, and `.env*`; no CI pipeline (intentionally removed, logged in `docs/decisions.md`).
- **Docs**: `docs/decisions.md` (11 dated entries with reasons/alternatives), `docs/data/variable_audit.md` (per-year SAS column audits), `AI_DISCLOSURE.md`, `ORIGINALITY.md` all exist and are substantive, not stubs.

## What is partial or broken

- **`src/agritwin/features/`**: only joins GEE outputs to each other (`gee_mart.py`). Does not join to SAS/survey data at all — blocked on the district crosswalk gap below.
- **API**: only 2 of the ~9 endpoints `api/CLAUDE.md` specifies (`/health`, `/geo/districts`). `/kpis`, `/yield-gap`, `/districts/{code}/profile`, `/drivers`, `/nowcast`, `/nowcast/{code}/curve`, `/backtest`, `/scenario/{code}`, `/briefs/{code}.pdf` are all unimplemented — there is no data for them to serve yet regardless (no `data/public/`).
- **Web app** (`web/src/App.tsx`, 95 lines): a single component rendering a MapLibre basemap and a district-count label. No routing (`react-router-dom` is not even in `web/package.json`), no `TanStack Query` (also not in `package.json`, despite being named in `web/CLAUDE.md`'s stack and root `CLAUDE.md`'s stack table), no ECharts, no i18n (`react-i18next`/`i18next` are listed as dependencies but unused in code — `grep` for `useTranslation`/`i18next` in `web/src` returns nothing), none of the 8 pages listed in `web/CLAUDE.md` (`Home, MapPage, DistrictPage, EarlyEstimatePage, ScenarioPage, MethodologyPage, DataPage, AboutPage`).
  - `npm run typecheck` (`tsc --noEmit`) fails with 3 errors: `src/App.tsx:6` (`ImportMeta.env` not typed — missing Vite client types), `src/App.tsx:48` (GeoJSON type mismatch on the `District` interface), `src/main.tsx:3` (TS5097, `.tsx` extension import not allowed under current `tsconfig`).
  - `npm run build` fails with the same 3 errors (build runs `tsc && vite build`, so it never reaches the Vite build step).
  - `npm run lint` fails outright: `ESLint couldn't find a configuration file` — no `.eslintrc*` exists anywhere in `web/`.
  - `npm run test` (`vitest --run`) exits 1: `No test files found` — zero test files exist under `web/src`.
  - `npm install` succeeds (added 376 packages) but reports 12 vulnerabilities (2 moderate, 7 high, 3 critical) — not yet triaged.
- **`docs/ai-usage-log.md`**: exists but contains only the header row, no actual log entries, despite 28 substantive AI-assisted commits to date and `CLAUDE.md` rule 9 requiring one line per session via `/log-ai-use`. This is a real disclosure-process gap, not just an empty template.
- **`docs/data/questionnaires/`**: exists as a directory but is empty. `audit-sas`'s own workflow (step 3) says to consult questionnaires there for matching unlabeled columns by position; there is nothing to consult. The 2025 audit's low/medium-confidence columns were therefore resolved without this input.

## What is missing vs. the plan (`docs/AgriTwin_Master_Build_Guide.md`)

All of the following have **no corresponding directory under `src/agritwin/`** — confirmed with `ls src/agritwin` (only `config.py`, `features/`, `gee/`, `harmonize/`, `__init__.py` exist):

| Module | Status | Build guide reference |
|---|---|---|
| `clean/` — yield computation, QC flags | **Missing** | §4.1 steps 2–3, `CLAUDE.md` module table |
| `survey/` — weighted ratio estimator, PSU bootstrap | **Missing** | §4.1 step 4, decisions.md 2026-09-23 stratified-design entry |
| `models/` (`attainable.py`, `drivers.py`, `nowcast.py`, `scenario.py`, `evaluation.py`) | **Missing** | `CLAUDE.md` module table |
| `export/` — public aggregated outputs, GeoJSON, PDF briefs | **Missing** | `CLAUDE.md` module table |

Consequently `data/marts/`, `artifacts/`, and `data/public/` do not exist on disk at all (`ls` confirms), and `make marts`, `make train`, `make export` all reference modules that were never built (same situation the recent `chore: collapse ingest/ into harmonize/` commit fixed for `ingest`, not yet fixed for these). No survey weight is ever applied to any output shown to a user — because no output is shown to a user yet — so there is no *misuse* of weights to flag, only their complete absence downstream of `stg_sas_plot_crop`.

**District crosswalk gap** (already self-identified and logged as an open blocking item in `docs/decisions.md`, dated 2026-09-23): SAS data keys districts on NISR's numeric `district_code`; the GEE mart keys on `district_name`/`gaul_district_code`. No crosswalk table exists. This blocks `features/`'s SAS-side join and therefore blocks `clean/`, `survey/`, `models/`, and `export/` from ever reaching a shared district key — it is the single highest-leverage missing piece, a 30-row table, not yet built.

**Crop scope discrepancy**: this audit's task brief states the MVP crops as "maize, beans, Irish potato, cassava." The repo's actual, already-decided scope (`config/settings.yaml`, `config/crops.yaml`, decisions log) is maize, beans, Irish potato, **sorghum** — chosen over rice on 2026-09-23 specifically because 2024 Season B has 878 sorghum pure-stand plots vs. 204–216 for rice, a real sample-size decision with cited numbers. Cassava is explicitly *excluded* from the nowcast per root `CLAUDE.md` ("Cassava is excluded from the nowcast because its growth cycle spans several seasons"). This looks like the task brief's crop list came from a plan document not present in this repo; flagging rather than reconciling silently.

**FAOSTAT**: the task brief lists FAOSTAT as an expected data source (§9.4). No reference to FAOSTAT exists anywhere in `docs/AgriTwin_Master_Build_Guide.md` or `config/data_sources.yaml` — same likely cause as the crop-list mismatch above.

## Compliance and security findings (highest priority first)

1. **No raw microdata in git history.** Checked `git log --all --diff-filter=A --name-only` across all 28 commits for `.dta`, `.sav`, `.sas7bdat`, and any path under `data/raw|interim|staging|marts` — zero matches. `.gitignore` covers all of these plus a belt-and-suspenders `!tests/fixtures/**` re-include. **Clean.**
2. **No secrets in git history.** `.env` was never committed (only `.env.example`, which contains placeholder values like `GEE_PROJECT_ID=your-earth-engine-project-id`, no real key). `git grep` for key/secret/password/AKIA/PEM-header patterns across all tracked files found nothing beyond the word "secrets" in `.gitignore` comments. **Clean.**
3. **`moving_nisr_files.py`** exists at repo root but is explicitly gitignored (a "some files" entry added to `.gitignore`) and confirmed untracked via `git ls-files`. Contents not reviewed here since it's out of git and the audit brief asked for git-tracked compliance, but worth the team's own awareness that a local file handling NISR data sits at repo root.
4. **AI disclosure process gap**: `AI_DISCLOSURE.md` and `ORIGINALITY.md` both exist and are substantive (team names, emails, tool list, scope of use). But `docs/ai-usage-log.md` is required by `CLAUDE.md` rule 9 to get one row per AI-assisted session and currently has zero rows despite 28 AI-assisted commits. This is a disclosure-completeness risk if judges check that specific file, not a disclosure-existence risk.
5. **No LICENSE or NOTICE file.** `find . -maxdepth 1 -iname "LICENSE*" -o -iname "NOTICE*"` returns nothing. The task brief asks specifically about "LICENSE/NOTICE about IP transfer to NISR" — if the hackathon rules require an explicit IP-transfer notice, it is not present anywhere in the repo.
6. **No code that looks copied from elsewhere.** Every file reviewed (harmonize, gee, api, web) reads as originally written for this project's specific schema and decisions (e.g., the SAS variable map's per-year confidence tags, the GAUL/district_name rename fix in an early commit) rather than generic boilerplate. `ORIGINALITY.md`'s declaration is consistent with what's in the tree.
7. **npm audit**: 12 vulnerabilities (3 critical, 7 high, 2 moderate) in `web/`'s dependency tree post-install, not yet triaged (`npm audit` for detail).

## Technical debt and quick wins

- `make marts`, `make train`, `make export` in the `Makefile` still reference `agritwin.survey.run`, `agritwin.models.run`, `agritwin.export.run` — none of which exist yet. Harmless until `make all` is run, but will fail loudly the moment someone does. (S)
- `web/tsconfig.json` and Vite client types need fixing before *any* further frontend work can build — currently blocks `npm run build` entirely. (S)
- No ESLint config in `web/` at all — `npm run lint` cannot run. (S)
- No test files in `web/src` — `npm run test` exits 1 immediately. (S, but only meaningful once there's something to test)
- `docs/data/questionnaires/` is empty; if 2025's low-confidence column matches ever need re-verification, there's no source document on hand to check against. (M — depends on NISR providing the questionnaire PDF)
- `docs/ai-usage-log.md` backfill: 28 commits' worth of AI-assisted sessions need at least a summarized retroactive entry to satisfy rule 9 literally, even if going forward `/log-ai-use` is run each session. (S)
- `api/app/data_store.py` loads `data/external/boundaries/rwanda_districts.geojson` directly rather than from `data/public/`, which is fine functionally (boundaries aren't sensitive) but is a precedent worth deciding on explicitly before more endpoints are added reading from `data/external/` instead of `data/public/`. (S, one decisions.md entry)

## Recommended next 10 tasks, ordered by judging-impact

Judging: Problem relevance, Data and methodology, Tech innovation, Usability, Tangible impact (20 pts each).

1. **Build the district_code↔GAUL crosswalk** (`config/district_crosswalk.yaml`, 30 rows). *Data and methodology.* Unblocks everything downstream; already scoped in `docs/decisions.md`. — **S**
2. **Build `src/agritwin/clean/`**: `yield_kg_ha` + `qc_flag` on `stg_sas_plot_crop` (plan for this was already proposed and awaiting approval as of this audit). *Data and methodology.* — **M**
3. **Build `src/agritwin/survey/`**: weighted ratio estimator + PSU bootstrap, respecting the 2019-segment vs 2020+-plot stratified design already decided in `docs/decisions.md`. *Data and methodology, Tech innovation.* — **M**
4. **Join SAS-derived district estimates to the GEE mart** via the crosswalk from #1, completing `feat_district_season`. *Data and methodology.* — **S** once #1–3 exist
5. **Fix the web app's build/lint/test toolchain** (tsconfig, ESLint config, Vite env types) so further frontend work is on solid ground. *Usability (unblocks everything visual).* — **S**
6. **Ship one real end-to-end page**: district picker + yield-gap map, backed by a real (even if minimal) `/api/v1/yield-gap` endpoint reading from a real `data/public/` mart. This is the first thing a judge will actually click. *Usability, Tangible impact.* — **M**
7. **`src/agritwin/models/attainable.py`**: weighted 90th-percentile attainable yield per zone×crop×season, the simplest model in the plan and a prerequisite for the yield-gap page above. *Data and methodology.* — **M**
8. **Driver model** (`models/drivers.py`, LightGBM + SHAP, GroupKFold by district) plus a naive baseline for comparison (none currently exists anywhere in `src/`). *Tech innovation.* — **L**
9. **Nowcast model** (`models/nowcast.py`, leave-one-year-out backtest against naive baselines) — the most technically distinctive piece of the pitch (satellite-based early estimate) and currently 0% built. *Tech innovation, Problem relevance.* — **L**
10. **`src/agritwin/export/` + `check_public.py` real run**: produce the first actual `data/public/` artifacts and confirm the privacy check catches something real, not just passing trivially because the directory doesn't exist yet (verified in this audit: `python scripts/check_public.py` currently just says "Privacy check passed" with nothing to check). *Tangible impact, compliance.* — **M**
