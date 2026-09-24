# AgriTwin Rwanda: Master Build Guide

> NISR 2026 Big Data Hackathon, Track 1 (Agricultural Productivity)
> Team: Ahourdet Donambi Thierry (thierrydonambi@gmail.com) and Ishimwe Aime Cesar (ishimweaimecesar5@gmail.com)
> Prepared: 23 September 2026
> Submission deadline: 30 October 2026, 23:59. Internal target: 28 October 2026.
> This file is the single reference for the project: problem, data, methodology, architecture, execution plan, and a complete Claude Code project kit (CLAUDE.md files, skills, subagents, config, CI) ready to drop into a new repository.

---

## Contents

1. [One-liner and scope](#1-one-liner-and-scope)
2. [Data confirmed available](#2-data-confirmed-available)
3. [Known data risks and how we handle them](#3-known-data-risks-and-how-we-handle-them)
4. [Methodology](#4-methodology)
5. [Architecture](#5-architecture)
6. [Repository structure](#6-repository-structure)
7. [Computational resources](#7-computational-resources)
7a. [Development method](#7a-development-method)
8. [Execution plan, week by week](#8-execution-plan-week-by-week)
9. [MVP scope and pages](#9-mvp-scope-and-pages)
10. [Submission checklist](#10-submission-checklist)
11. [Sources](#11-sources)
12. [Claude Code project kit](#12-claude-code-project-kit)

---

## 1. One-liner and scope

AgriTwin Rwanda shows, per crop and district, how far below attainable yield farmers are, which factors are associated with the gap, and what this season's harvest is likely to be before the official SAS results are published.

**MVP crops:** maize, beans, Irish potato, and a fourth crop (sorghum or rice, confirmed after the variable audit in week 0).
**MVP geography:** all 30 districts.
**MVP seasons:** A and B (Season C excluded: it is marshland and irrigated agriculture on a much smaller sample, not comparable to the main rain-fed seasons).
**Core years:** 2019 to 2025, narrowed from the original 2013 to 2025 range in the master plan, to keep harmonization effort inside the 5.5-week budget. Earlier years can be added later if their crop codes and structure line up cheaply with the audit.

Everything shown to a user is a **district x season x crop x year** figure with a confidence interval or a reliability flag. No plot-level or farmer-level data is ever surfaced.

---

## 2. Data confirmed available

This section reflects an actual check of the NISR microdata catalog and the Earth Engine noncommercial terms on 23 September 2026, not just the plan's data landscape table.

### 2.1 SAS microdata, year by year, catalog IDs confirmed

The NISR Central Data Catalog (browsable at `https://www.microdata.statistics.gov.rw/index.php/catalog/{id}`) lists a Seasonal Agricultural Survey (SAS) entry for every year from 2013 to 2025. Every catalog ID needed for the core 2019 to 2025 scope, plus AHS 2024, has been individually verified against the live catalog and is recorded in `config/data_sources.yaml`:

| Study | Catalog ID | Study | Catalog ID |
|---|---|---|---|
| SAS 2019 | 93 | SAS 2023 | 111 |
| SAS 2020 | 99 | SAS 2024 | 113 |
| SAS 2021 | 102 | SAS 2025 | 124 |
| SAS 2022 | 103 | AHS 2024 | 123 |

Optional earlier years, confirmed but outside the core scope: SAS 2013 (ID 66), 2014 (ID 78), 2015 (ID 77), 2017 (ID 88). 2016 and 2018 were not looked up, since core scope starts at 2019.

The 2025 round (catalog record 124) went live on 2 April 2026 and its overview describes it as an edited, anonymized dataset for public use, covering the 2024/2025 agricultural year across Seasons A, B and C, with national coverage that allows district-level estimation. The 2025 dictionary lists twelve files: fertilizer/pesticide, agricultural practice, production and screening, for each of Seasons A, B and C, with production files at roughly 33,000 to 34,000 plot-crop rows per season.

The 2024 round (catalog record 113) has the same file structure and, importantly, its Season B production file (F6, 35,584 rows, 97 variables) is fully labeled. It includes, per plot-crop row: province, district code, stratum, segment ID, farmer ID and type, plot ID, plot area in square metres, number of main crops on the plot, crop name, sowing date, improved seed use and source, quantity harvested in kg (both a plot-level and a crop-level total), what happened to that harvest (sold, consumed, stored, lost, and losses broken down by cause: pests, theft, birds, transport, storage, processing, packaging, sales), organic and inorganic fertilizer use, micronutrients, pesticide use, erosion degree and anti-erosion activity, land consolidation, mechanization, irrigation, interview date, and a `plot_weight` survey weight. This one file alone carries the yield target, the input and practice features for the driver model, and the weights needed for design-based estimation.

**Practical implication:** the 2024 file is our reference for column meaning. The 2025 production file has the same 101-variable shape but its variables are unlabeled (V1 to V100 in the public dictionary). Treat 2025 as needing a manual crosswalk against 2024 and the field questionnaire before it can be used; do not guess.

### 2.2 Earth Engine access and compute, confirmed working

Sentinel-2, MODIS NDVI, CHIRPS, ESA WorldCover, iSDAsoil and SRTM are all available through Google Earth Engine at no cost for noncommercial academic use. Since 27 April 2026, Earth Engine enforces noncommercial quota tiers: the default **Community Tier** gives 150 EECU-hours per month, aimed at undergraduate-level usage; the **Contributor Tier** gives 1,000 EECU-hours per month, aimed at graduate students and researchers, and requires linking a billing account for identity verification only (Earth Engine compute itself is never charged under noncommercial status). Running out of quota does not cut access off; it drops the project into a slower "restricted mode" until the monthly reset. For a workload this size (district-level zonal statistics on monthly composites over one small country, computed a handful of times and then cached), 150 EECU-hours is very likely sufficient.

**This has since been verified end to end, not just researched.** On 23 September 2026, `scripts/test_gee.py` (in the kit below) confirmed: project registration, API enablement, and live access to all eight datasets the pipeline needs, plus a real `reduceRegion` compute call (mean NDVI over Rwanda, January 2024). The exact dataset IDs and scale factors are now locked in `config/data_sources.yaml` and implemented once in `src/agritwin/gee/scaling.py`, so they never need to be re-derived while building the pipeline:

| Dataset | Earth Engine ID | Scale factor |
|---|---|---|
| MODIS NDVI/EVI | `MODIS/061/MOD13Q1` | multiply by 0.0001 |
| Sentinel-2 SR | `COPERNICUS/S2_SR_HARMONIZED` | multiply by 0.0001 |
| CHIRPS Daily | `UCSB-CHG/CHIRPS/DAILY` | none, already mm/day |
| ESA WorldCover | `ESA/WorldCover/v200` | none, categorical |
| iSDAsoil pH | `ISDASOIL/Africa/v1/ph` | x / 10 |
| iSDAsoil Nitrogen | `ISDASOIL/Africa/v1/nitrogen_total` | exp(x / 100) - 1 |
| iSDAsoil Carbon | `ISDASOIL/Africa/v1/carbon_organic` | exp(x / 10) - 1 |
| SRTM elevation | `USGS/SRTMGL1_003` | none |

A subtlety caught by the confirmation run: MOD13Q1 stores NDVI as a scaled `int16`, so an unscaled read (raw values in the thousands) looks superficially plausible but is wrong by a factor of 10000. Always import the scale factor from `scaling.py` rather than trusting a value that "looks like a number".

Sentinel-2 surface reflectance has good, consistent coverage over Rwanda from around 2019 onward; for the full 2019 to 2025 history use MODIS NDVI (available from 2000) as the primary nowcast signal, and use Sentinel-2 only for the higher-resolution current-season map shown in the app.

### 2.3 What this means for feasibility

Doable within 5.5 weeks. The microdata volume is small (tens of thousands of rows per file, not millions), so DuckDB and polars on a laptop handle it comfortably; no cluster or paid cloud compute is required for the modelling. The only external dependency with a quota is Earth Engine, and the quota is unlikely to bind at this scale. The two real risks are not data availability but harmonization effort (mapping the unlabeled 2025 file, and reconciling file structure differences year to year) and the intercropping problem described next.

---

## 3. Known data risks and how we handle them

| Risk | Detail | Mitigation |
|---|---|---|
| Intercropped plots | The production file records one plot area and a count of main crops per plot, but no per-crop area share. Dividing total harvest by plot area is wrong when more than one crop shares the plot. | Restrict yield-gap and driver models to **pure-stand plots** (`n_main_crops == 1`). Report the resulting sample size per crop and season; if beans fall too low, note this explicitly as a limitation rather than including biased intercropped yields. |
| 2025 file unlabeled | Season A/B/C production files for 2025 list only V1 to V100 with no labels in the public dictionary. | Run `/audit-sas 2025` (see kit below): match columns by position and value pattern against the labeled 2024 file and the field questionnaire, tag confidence per column, and never use a low-confidence column without a human check. |
| Inconsistent file sets across years | 2024 has no Season B agricultural-practice file (practice questions are folded into the production file that year); other years may differ. | Treat the production file as the primary source per year, and use the audit to confirm which practice variables are or are not present each year before harmonizing. |
| Small nowcast sample | 30 districts x 2 seasons x 7 years gives roughly 400 crop-season-district observations, further thinned by cloud cover and missing years. | Set expectations low and explicit: the nowcast is framed as an early vigour signal with a documented backtest against naive baselines, not a guaranteed improvement. Leave-one-year-out validation only, never random splits. |
| Confidentiality | Plot and farmer identifiers must never reach the public repo or the deployed app. | Enforced structurally: raw/interim/staging data are gitignored, only `data/public/` (district-level, aggregated) is committed or deployed, and a `check_public.py` script plus a `privacy-guard` subagent both check for identifier columns and small, unflagged cells before every release. |
| SAS access mechanics unverified | The Data Access page for the 2025 catalog record did not render readable text at time of writing, so the exact request/approval flow (immediate download vs approval queue) is unconfirmed. | Log in and attempt the actual download for SAS 2019 to 2025 and AHS 2024 in week 0, day 1. If any year needs an approval request, submit it immediately and build the pipeline against whichever years are available first, backfilling later years as access clears. |

---

## 4. Methodology

### 4.1 Yield and yield gap

1. Restrict to small-scale farmer, pure-stand plots (`n_main_crops == 1`) for the four MVP crops.
2. Compute plot yield in kg/ha: `harvest_kg / (plot_area_sqm / 10000)`.
3. QC: drop implausible plot areas (below 20 sqm), trim at the 0.5th and 99.5th percentile per crop, season and year, and flag any yield above an agronomic plausibility cap (see `config/settings.yaml`) rather than silently dropping it.
4. District-season-year yield is a **weighted ratio estimator**: `sum(weight * harvest_kg) / sum(weight * plot_area_ha)`, not a mean of plot yields, with a design-based confidence interval from a PSU bootstrap (resample segments within strata) or samplics' Taylor linearisation as a cross-check.
5. Attainable yield: the weighted 90th percentile of pure-stand plot yields within an agro-ecological zone x crop x season group (or a k-means zoning if an AEZ layer isn't readily available), pooled across the core years.
6. Yield gap = attainable minus actual, reported in kg/ha and as a percent of attainable, with its own interval propagated from both quantities.

### 4.2 Driver model

LightGBM regression of log-yield on improved seed, organic and inorganic fertilizer, pesticide, erosion degree and anti-erosion activity, land consolidation, mechanization, irrigation, plot area, sowing month, soil (pH, nitrogen, carbon, texture from iSDAsoil) and in-season rainfall (CHIRPS). Validation is **GroupKFold by district** (never random K-fold, since plots within a district are correlated and a random split would leak district-level information into the test fold). SHAP values give both a global driver ranking and a district-specific explanation ("in Nyaruguru, the top three factors associated with the gap are..."). This is presented strictly as association, never as a causal claim, both in the model card and in the UI copy.

### 4.3 Early estimate (nowcast)

A district x season x crop x year panel built from 2019 to 2025 (roughly 400 rows per crop after restricting to core years). Features: cumulative and peak NDVI, NDVI anomaly against a 2001 to 2018 climatology, rainfall anomaly against a 1991 to 2020 CHIRPS climatology, and prior-season production, all computed at a chosen lead time (2, 3 or 4 months into the season). Two candidate lead-time strategies are evaluated so the product can offer an early, less accurate estimate and a later, more accurate one. Models: a naive baseline (last year's yield, and separately, the district's historical mean), ridge regression, and a small LightGBM. Validation is **leave-one-year-out**, and every result is reported against both baselines with MAPE, never presented as a bare number. Given the sample size, do not overclaim: state the achieved improvement over baseline honestly, and if a lead time shows no improvement, say so on the backtest page rather than hiding it.

### 4.4 Scenario explorer

Not a live re-run of the model. Precompute, per district and crop, the model's predicted yield under a small grid of lever configurations (for example, improved seed adoption at four levels crossed with fertilizer at two levels), with bootstrap intervals, and let the frontend interpolate or select among the precomputed points. This keeps the API stateless and fast, and avoids needing a job queue for the hackathon deadline. Every scenario output carries the label "model-based, not causal" both in the API response and in the UI.

### 4.5 Validation against official figures

In week 1, reproduce one or more published SAS figures (for example, national maize yield for a given year and season, or an adoption rate) using the weighted pipeline, and compare against the NISR annual report tables. This is the single highest-value credibility check for a jury of statisticians, and it is scripted as the repeatable `/validate-official` skill so it can be re-run whenever the pipeline changes.

---

## 5. Architecture

```text
┌───────────────────────────── DATA SOURCES ─────────────────────────────┐
│  NISR SAS microdata 2019-2025 (Seasons A, B), NISR AHS 2024            │
│  Earth Engine: MODIS NDVI, Sentinel-2, CHIRPS, WorldCover, iSDAsoil    │
│  HDX Rwanda admin boundaries, NISR SAS/CPI published tables (validation)│
└───────────────┬───────────────────────────────┬────────────────────────┘
                │ manual download (registered)   │ Earth Engine API
                ▼                                ▼
┌──────────────────────────── INGESTION LAYER ───────────────────────────┐
│  src/agritwin/ingest  (pyreadstat -> data/interim, typed Parquet)      │
│  src/agritwin/gee     (zonal stats -> data/external/gee)               │
└───────────────┬────────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────── STAGING / MARTS ───────────────────────────┐
│  src/agritwin/harmonize  -> data/staging (canonical schema, all years) │
│  src/agritwin/clean      -> yield computation, QC flags                │
│  src/agritwin/survey     -> weighted estimates + bootstrap CIs -> marts│
│  Engine: DuckDB + polars locally, no database server needed            │
└───────────────┬────────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────── MODELLING LAYER ───────────────────────────┐
│  src/agritwin/features  -> district-season feature table               │
│  src/agritwin/models    -> attainable, drivers (LightGBM+SHAP),        │
│                             nowcast (leave-one-year-out), scenario grid │
│  Artifacts saved to artifacts/ with metadata.json (never committed)    │
└───────────────┬────────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────── EXPORT LAYER ──────────────────────────────┐
│  src/agritwin/export -> data/public/ (Parquet + JSON + GeoJSON + PDFs) │
│  This is the ONLY data folder committed to git and shipped in Docker  │
└───────────────┬────────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────── SERVING LAYER ─────────────────────────────┐
│  FastAPI reading data/public/ only, no live DB, cached responses       │
└───────────────┬────────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────── PRESENTATION LAYER ────────────────────────┐
│  React + Vite + TS, MapLibre GL, ECharts, Tailwind, i18n (en/fr/rw)    │
└────────────────────────────────────────────────────────────────────────┘
```

Deliberate simplifications versus the original master plan, to fit 5.5 weeks: no PostgreSQL/PostGIS server (static Parquet/GeoJSON files served by FastAPI are enough for precomputed, read-only results); no Prefect orchestration (`make` targets cover the pipeline, run manually); no Celery/Redis job queue (the scenario explorer is precomputed, not live); no CI/CD pipeline (see Section 7a).

---

## 6. Repository structure

```text
agritwin-rwanda/
├── CLAUDE.md                    # root project instructions for Claude Code
├── README.md
├── AI_DISCLOSURE.md
├── ORIGINALITY.md
├── LICENSE
├── Makefile
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml           # editable install only; dependencies live in requirements*.txt
├── docker-compose.yml
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── .claude/
│   ├── settings.json
│   ├── skills/
│   │   ├── audit-sas/SKILL.md
│   │   ├── pipeline-step/SKILL.md
│   │   ├── validate-official/SKILL.md
│   │   ├── add-endpoint/SKILL.md
│   │   ├── add-page/SKILL.md
│   │   ├── model-card/SKILL.md
│   │   ├── privacy-check/SKILL.md
│   │   ├── release-check/SKILL.md
│   │   └── log-ai-use/SKILL.md
│   └── agents/
│       ├── survey-methodologist.md
│       ├── privacy-guard.md
│       └── ux-reviewer.md
├── config/
│   ├── settings.yaml
│   ├── sas_variable_map.yaml
│   └── crops.yaml
├── data/
│   ├── raw/            (gitignored)      SAS, AHS as downloaded
│   ├── interim/         (gitignored)      typed Parquet, one per source file
│   ├── staging/         (gitignored)      harmonized, canonical schema, all years
│   ├── marts/           (gitignored)      district x season x crop x year estimates
│   ├── external/
│   │   ├── gee/                           Earth Engine extractions (CSV)
│   │   ├── official/                      transcribed NISR published tables
│   │   └── boundaries/                    HDX admin boundaries
│   └── public/                            ONLY folder committed and deployed
├── artifacts/            (gitignored)     trained models + metadata.json
├── src/agritwin/
│   ├── CLAUDE.md
│   ├── ingest/  harmonize/  clean/  survey/  gee/  features/  models/  export/
├── api/
│   ├── CLAUDE.md
│   ├── app/ (main.py, settings.py, data_store.py, schemas.py, routers/)
│   └── tests/
├── web/
│   ├── CLAUDE.md
│   └── src/ (api/, components/, pages/, lib/, i18n/, styles/)
├── notebooks/            numbered EDA, cleared outputs, never imported by code
├── tests/
├── docs/
│   ├── AgriTwin_Master_Build_Guide.md   (this file)
│   ├── decisions.md
│   ├── ai-usage-log.md
│   ├── data/ (README.md, variable_audit.md, questionnaires/)
│   └── models/ (_template.md, attainable.md, drivers.md, nowcast.md)
├── infra/
│   ├── Dockerfile.api
│   └── Dockerfile.web
└── scripts/
    └── check_public.py
```

`.claude/` and every `CLAUDE.md` are gitignored: they stay on disk for Claude Code to read locally but are never committed or pushed, so the public GitHub repository shows the product, not the tooling used to build it. AI use is still disclosed as required, through `AI_DISCLOSURE.md` and `docs/ai-usage-log.md`, both of which remain tracked.

---

## 7. Computational resources

- **Local machine:** any laptop with 8 GB+ RAM is enough. All SAS files together across 7 years are a few hundred thousand rows; DuckDB and polars handle this in seconds.
- **Model training:** LightGBM with SHAP on this data trains in seconds to low minutes per model. No GPU needed.
- **Earth Engine:** the only external compute dependency; register the project as noncommercial this week (`ee.Authenticate()` then select a tier at the Earth Engine Configuration page). Use 20 to 30 m reduction scale for zonal statistics rather than native 10 m Sentinel-2 resolution to keep compute light. Export results to CSV once per refresh rather than recomputing on every pipeline run.
- **Hosting:** API and web are stateless once `data/public/` is built, so a small always-on instance (Render, Railway, Fly.io free/hobby tier, or a small VM) is enough; avoid a host that sleeps, since the evaluation window (1 to 5 November) requires uptime. Set up an uptime monitor (UptimeRobot free tier). Deploy through the host's own git-triggered deploy on push; that is the platform's feature, not a pipeline the team builds.
- **No CI.** See Section 7a for why, and for the local-checks routine that replaces it.

---

## 7a. Development method

No CI/CD pipeline. This is a deliberate choice, not a shortcut taken under time pressure: with a two-person team and 5.5 weeks, an automated pipeline is overhead that doesn't pay for itself. Nobody else is merging code either of you hasn't already seen, and minutes spent waiting on a remote runner are minutes not spent on the model or the app. Every check a CI pipeline would run happens locally instead, by hand, every time:

1. **Trunk-based, small commits.** Work directly on `main` unless a change is large enough to risk breaking something the other person depends on that day; then use a short-lived branch merged within the day. No long-lived feature branches, no PR queue waiting on a check to go green.
2. **Local gates before every commit, not after a push.** Run `make lint && make test` before committing. Before any commit touching `data/public/`, also run `/privacy-check`. Treat a red `make test` the way you'd treat a red CI badge: don't commit past it.
3. **Vertical slices, not horizontal layers.** Each week ships one thin end-to-end slice (a bit of data, a model output, an API endpoint, a UI view) rather than finishing the whole pipeline before touching the frontend, matching the week-by-week plan in Section 8. This also means there's always something runnable to sanity-check by hand.
4. **Skills are the process.** `/pipeline-step`, `/validate-official`, `/add-endpoint`, `/add-page`, `/model-card`, `/privacy-check`, `/release-check` are invoked manually at the point in the work where they matter, replacing the automated triggers a CI pipeline would use.
5. **Decisions log instead of PR review.** There's no second reviewer gating a merge, so anything worth a reviewer's sanity check, a methodology choice, a scope cut, an architecture call, goes in `docs/decisions.md` instead, dated, with the reason and the alternatives considered.
6. **Deploy by hand, early and often.** Push to the hosting platform's own git-triggered deploy from week 3 onward; that's the platform's own feature (Render, Railway, and Fly.io all offer it), not a pipeline the team builds or maintains. Manually smoke-test the deployed URL after each deploy: open the map, switch crop and season, check a district profile loads. `/release-check` formalizes this before submission; do a lighter version after every deploy.
7. **Satellite refresh is a manual `make gee` run during the hackathon**, not a scheduled job. Automating it is explicitly a post-hackathon task (Section 9.9 style "going live" work for each idea), not something to build now.

## 8. Execution plan, week by week

| Week | Dates | Goals | Deliverables |
|---|---|---|---|
| 0 | 21 to 27 Sep | Log in to microdata portal using the confirmed catalog links in `config/data_sources.yaml`, attempt real downloads for SAS 2019-2025 and AHS 2024; run `/audit-sas` for each year; confirm the fourth crop (sorghum vs rice) by checking sample sizes; scaffold the repo from Section 12 below; confirm teammate roles. Earth Engine access is already confirmed (`scripts/test_gee.py` passed 23 Sep), so this is no longer a week 0 risk item | Variable audit doc, decision memo, repo skeleton, CI green on an empty pipeline |
| 1 | 28 Sep to 4 Oct | `make ingest stage marts` for at least 2024 and 2025; run `/validate-official` against one published figure; Earth Engine pull for MODIS NDVI and CHIRPS 2019-2025 | Staging + marts for at least 2 years, validation report, GEE extraction cached to `data/external/gee` |
| 2 | 5 to 11 Oct | Finish harmonizing all core years; attainable yield and driver model v1 with SHAP; API v1 (kpis, yield-gap, districts, drivers); frontend skeleton with map; **freeze MVP scope 11 Oct** | Model v1 + metrics, API v1 live locally, UI wireframe |
| 3 | 12 to 18 Oct | Nowcast model + backtest; scenario grid precomputation; scenario and early-estimate pages; deploy to a staging URL | Working end-to-end app online |
| 4 | 19 to 25 Oct | User testing with 3 to 5 people; run `/release-check`; fix UX per `ux-reviewer` findings; Kinyarwanda translations; docs site (MkDocs) published | Test notes, docs site live, EN/FR/RW complete |
| 5 | 26 to 30 Oct | Final polish, performance, `/privacy-check`, demo video, pitch deck; **submit 28 Oct** | GitHub repo public, live app, docs, video, deck |

---

## 9. MVP scope and pages

1. **Home / national overview:** KPI cards (area, production, input adoption) with intervals, trend charts 2019 to 2025.
2. **Map:** choropleth of yield gap by district for the selected crop and season, with reliability shading.
3. **District profile:** gap, top 5 SHAP drivers, comparison with similar districts.
4. **Early estimate:** current-season NDVI and rainfall curve vs climatology, predicted yield with interval, badge stating it is model-based.
5. **Scenario explorer:** sliders for the precomputed lever grid (seed adoption, fertilizer, irrigation, erosion control).
6. **Backtest page:** leave-one-year-out nowcast results vs baselines, shown honestly even where the model does not beat baseline.
7. **Methodology and data page:** sources, validation results, limitations, in plain language.
8. **Export:** one-page PDF district brief, generated ahead of time and served as a static file.

---

## 10. Submission checklist

- [ ] Public GitHub repository link
- [ ] Deployed app link, tested on desktop and mobile from a different network
- [ ] Documentation (MkDocs site + README)
- [ ] `ORIGINALITY.md`
- [ ] `AI_DISCLOSURE.md`, kept current from `docs/ai-usage-log.md`
- [ ] Proof of student status for both members
- [ ] Architecture diagram and demo GIF in README
- [ ] `docker compose up` works on a clean machine
- [ ] 3-minute demo video (YouTube unlisted), linked in README
- [ ] 8 to 10 slide pitch deck
- [ ] Uptime monitor active for 1 to 5 November
- [ ] Every data source and licence cited on the Data page

---

## 11. Sources

- NISR 2026 Hackathon Competition: https://statistics.gov.rw/about/hackathon/2026-hackathon-competition
- NISR Microdata Central Catalog: https://microdata.statistics.gov.rw/index.php/catalog
- SAS 2025 (catalog 124), data dictionary and overview: https://www.microdata.statistics.gov.rw/index.php/catalog/124
- SAS 2024 (catalog 113), data dictionary, production file F6: https://www.microdata.statistics.gov.rw/index.php/catalog/113
- Google Earth Engine noncommercial tiers: https://developers.google.com/earth-engine/guides/noncommercial_tiers
- Google Earth Engine noncommercial use terms: https://earthengine.google.com/noncommercial/
- CHIRPS: https://www.chc.ucsb.edu/data/chirps
- iSDAsoil: https://www.isda-africa.com/isdasoil
- Humanitarian Data Exchange (Rwanda boundaries): https://data.humdata.org/group/rwa
- NISR PxWeb: https://pxweb.statistics.gov.rw

*Re-check licence terms and current availability for all external data before use, since they can change.*

---

## 12. Claude Code project kit

Everything below is a complete, working starting point for the repository, written for Claude Code. Create the folders shown in Section 6, then create each file below at its shown path with its shown content. All of it follows the project's writing-style rule: no em dashes or en dashes anywhere.

**How to use this with Claude Code, in order:**

1. `git init agritwin-rwanda && cd agritwin-rwanda`, then create every file below at its path.
2. Fill in the team members in `ORIGINALITY.md`, the repository URL in `README.md`, and your real Earth Engine project ID in `.env` (copy from `.env.example`).
3. Run `claude` in the repo root. Claude Code will read `CLAUDE.md` automatically. Run `/init` if you want it to also append its own repo notes, then review the diff.
4. Run `make setup` (creates the venv, installs `requirements.txt` and `requirements-dev.txt`, installs the `agritwin` package in editable mode, and runs `npm ci`), then `source venv/bin/activate` and `python scripts/test_gee.py` to reconfirm Earth Engine works in this environment (already confirmed once on 23 Sep 2026; re-run after any new machine or venv).
5. Start with `/pipeline-step ingest SAS production files for one year` and build up module by module, following the week-by-week plan in Section 8.
6. Use `/audit-sas 2025` before writing any harmonization code for 2025.
7. Use `/validate-official 2024 A` once staging and marts exist for 2024.
8. Use `/add-endpoint` and `/add-page` once models are producing outputs.
9. Use `/model-card` for each trained model before the docs site is built.
10. Use `/privacy-check` before every commit that touches `data/public/`, and `/release-check` before submission.
11. Use `/log-ai-use` at the end of each work session, for the AI disclosure requirement.

The three subagents (`survey-methodologist`, `privacy-guard`, `ux-reviewer`) are invoked automatically by the skills above where relevant, or directly by name, for example: "ask the survey-methodologist subagent to review src/agritwin/survey/estimator.py".

#### `.env.example`

```bash
DATA_DIR=./data
GEE_PROJECT_ID=your-earth-engine-project-id
# GEE_PROJECT_ID confirmed working via scripts/test_gee.py on 23 Sep 2026 setup.
# Do not commit your real project ID's associated service account key; see GEE_SERVICE_ACCOUNT_JSON below.
GEE_SERVICE_ACCOUNT_JSON=./secrets/gee-service-account.json
API_ALLOWED_ORIGINS=http://localhost:5173
VITE_API_BASE=http://localhost:8000/api/v1
```

#### `.gitignore`

```text
# Claude Code project files: kept on disk for local development, never pushed
# to GitHub. Claude Code still reads these locally; git just never tracks
# them, so the public repo shows only the product, not the tooling used to
# build it. If any of these were committed before this rule was added, run
# `git rm -r --cached .claude CLAUDE.md` once to untrack them.
.claude/
CLAUDE.md

# data: never commit microdata
data/raw/
data/interim/
data/staging/
data/marts/
artifacts/
*.dta
*.sav
*.sas7bdat
!tests/fixtures/**

# secrets
.env
.env.*
!.env.example
secrets/
*.json.key

# python
.venv/
venv/
env/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# node
web/node_modules/
web/dist/

# misc
.DS_Store
site/
mlruns/
```

#### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/kynan/nbstripout
    rev: 0.7.1
    hooks:
      - id: nbstripout
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: check-added-large-files
        args: [--maxkb=5000]
      - id: detect-private-key
  - repo: local
    hooks:
      - id: block-microdata
        name: block microdata and non-public data
        entry: python scripts/check_public.py --staged
        language: system
        pass_filenames: false
```

#### `AI_DISCLOSURE.md`

```markdown
# AI disclosure

This project used AI assistants during development, as permitted by the NISR 2026 Big Data Hackathon rules (requirement 10), with all use disclosed here and in `docs/ai-usage-log.md`. The team is fully responsible for all submitted work.

## Tools used
- Claude (Anthropic), via Claude Code and claude.ai: pipeline code, API code, frontend code, documentation drafting, and this build plan.
- <add any other tool used: ChatGPT, GitHub Copilot, etc., and what for>

## What AI was used for
- Scaffolding and boilerplate for the data pipeline, API and frontend.
- Drafting documentation, model cards and this disclosure.
- Code review suggestions.

## What AI was not used for
- Survey methodology decisions (weighting, variance estimation, validation design): reviewed and approved by the team.
- Final model selection and interpretation of results.
- No microdata was pasted into any AI tool. Only aggregated summaries, schemas and synthetic examples were shared.

## Human oversight
Every AI-assisted change was reviewed, run and tested by a team member before merging. See `docs/ai-usage-log.md` for the session-by-session record.
```

#### `CLAUDE.md`

```markdown
# AgriTwin Rwanda

Early-season crop yield intelligence and yield-gap analysis for Rwanda. Built for the NISR 2026 Big Data Hackathon, Track 1 (Agricultural Productivity).
Submission deadline: 30 October 2026, 23:59. Internal target: 28 October 2026.
Team of two: Ahourdet Donambi Thierry (data engineering, API, frontend, deployment) and Ishimwe Aime Cesar (survey methodology, validation, Kinyarwanda, domain research).

The full build guide lives in `docs/AgriTwin_Master_Build_Guide.md`. Read the relevant section before starting any new module.

## What the product does

1. **Yield gap engine**: district-level actual yield vs attainable yield, per crop and season, with confidence intervals.
2. **Driver engine**: explainable model (LightGBM + SHAP) showing which practices and conditions are associated with higher yield.
3. **Early estimate engine (nowcast)**: MODIS NDVI + CHIRPS rainfall during the season predict district yield before SAS is published.
4. **Scenario explorer**: "if improved seed adoption rose to X%", computed from precomputed model outputs. Always labelled as model-based, not causal.

Unit of analysis for everything shown to users: **district x season x crop x year**. Plot-level data never leaves the pipeline.

## Golden rules (non negotiable)

1. **Never commit raw or plot-level NISR microdata.** `data/raw/`, `data/interim/`, `data/staging/`, `data/marts/` and `artifacts/` are gitignored. Only aggregated, district-level outputs in `data/public/` may be committed or deployed. Run `make check-public` before every commit that touches `data/public/`.
2. **Do not dump microdata into the conversation.** When you need to understand a file, print its schema, dtypes, value counts of categorical columns and summary statistics. Never print more than 5 raw rows.
3. **Survey design everywhere.** Every population estimate uses `weight` (from SAS `plot_weight`) and the design: strata = `stratum`, PSU = `segment_id`. Unweighted means are only allowed in QC notebooks and must be labelled as such.
4. **No naive joins across surveys.** SAS, AHS and satellite features meet only at district x season x year level.
5. **Associations, not causation.** Never write "causes", "increases yield by", "impact of" in UI copy or docs for model outputs. Use "is associated with" and "model-based estimate".
6. **Uncertainty is mandatory.** Every number displayed has a confidence or prediction interval, or a reliability flag. Cells with fewer than `n_min` unweighted plots (see `config/settings.yaml`) are flagged `low_reliability` and greyed out in the UI.
7. **Do not invent variable names.** Source column names come only from `config/sas_variable_map.yaml` and `docs/data/variable_audit.md`. If a variable is missing, stop and ask.
8. **Original work only.** Do not paste code from other projects of the team. Standard library usage and documented examples are fine.
9. **AI disclosure.** After any session that produced significant code or text, append one line to `docs/ai-usage-log.md` (date, tool, task, what a human reviewed). Use the `/log-ai-use` skill.
10. **Writing style.** No em dashes or en dashes in docs, UI copy, commit messages or comments. Use commas, colons, or separate sentences. Ranges are written with "to" (for example "2019 to 2025").

## Stack

- Python 3.12, managed with a plain venv and `requirements.txt` / `requirements-dev.txt` (pip). Data: polars (preferred) or pandas, pyreadstat, DuckDB, GeoPandas.
- Earth Engine Python API for all satellite features (MODIS NDVI, Sentinel-2, CHIRPS, WorldCover, iSDAsoil, SRTM).
- Models: scikit-learn, LightGBM, SHAP. Survey statistics: samplics plus our own PSU bootstrap in `src/agritwin/survey/`.
- API: FastAPI + Pydantic v2, serving precomputed Parquet/JSON from `data/public/`. No database server.
- Web: React 18 + Vite + TypeScript, MapLibre GL JS, ECharts, Tailwind CSS, react-i18next (en, fr, rw), TanStack Query, React Router.
- Docs: MkDocs Material, deployed to GitHub Pages.
- No CI/CD pipeline. `make lint` and `make test` are run manually before every commit; see the development method note below.

## Commands

```bash
make setup          # venv + pip install -r requirements.txt -r requirements-dev.txt + npm ci + pre-commit install
make ingest         # data/raw -> data/interim (typed Parquet)
make stage          # harmonize SAS years -> data/staging
make marts          # survey estimates -> data/marts
make gee            # Earth Engine extractions -> data/external/gee
make features       # district x season feature table
make train          # attainable yield, driver model, nowcast backtests
make export         # data/marts + artifacts -> data/public (aggregated only)
make check-public   # privacy and schema checks on data/public
make all            # everything above in order
make api            # uvicorn on :8000
make web            # vite dev server on :5173
make test           # pytest + vitest
make lint           # ruff, mypy, eslint, tsc
make docs           # mkdocs serve
```

## Repository map

- `config/` settings, SAS variable map per year, crop codes, district crosswalk
- `src/agritwin/` pipeline package (ingest, harmonize, clean, survey, gee, features, models, export). See its CLAUDE.md.
- `api/` FastAPI app. See its CLAUDE.md.
- `web/` React app. See its CLAUDE.md.
- `docs/` MkDocs site, decisions log, variable audit, model cards, AI usage log
- `notebooks/` numbered exploration notebooks, never imported by code
- `tests/` pytest for the pipeline; `api/tests/`; `web/src/**/*.test.ts(x)`
- `scripts/` utility scripts (privacy check, keepalive, release checks)

## How to work in this repo

1. For any task larger than one file, start in plan mode and write the plan first. Wait for approval.
2. Write or update tests in the same change. Data functions get a unit test with a tiny synthetic DataFrame, never real microdata.
3. Keep functions pure where possible: take a DataFrame, return a DataFrame. I/O lives in thin wrappers.
4. All tunable numbers (thresholds, years, crops, n_min, bootstrap B) live in `config/settings.yaml`. No magic numbers in code.
5. Small commits with Conventional Commit messages (`feat:`, `fix:`, `data:`, `docs:`, `test:`, `chore:`).
6. Record any methodological or architectural decision in `docs/decisions.md` (date, decision, reason, alternatives).
7. When unsure about survey methodology, delegate a review to the `survey-methodologist` subagent.
8. Before release, run the `/privacy-check` and `/release-check` skills.

## Development method

No CI/CD pipeline. With a two-person team and a 5.5-week deadline, an automated pipeline is overhead that doesn't pay for itself: nobody else is merging code you haven't seen, and Actions minutes spent waiting are minutes not spent on the model or the app. The checks a CI pipeline would run happen locally, by hand, every time, instead:

1. **Trunk-based, small commits.** Work directly on `main` unless a change is large enough to risk breaking something the other person depends on that day; then use a short-lived branch merged within the day. No long-lived feature branches, no PR queue waiting on a check to go green.
2. **Local gates before every commit, not after a push.** Run `make lint && make test` before committing. Before any commit that touches `data/public/`, also run `/privacy-check`. This is a habit, not a script that runs itself; treat a red `make test` the same way you'd treat a red CI badge, don't commit past it.
3. **Vertical slices, not horizontal layers.** Each week ships one thin end-to-end slice (a bit of data, a model output, an API endpoint, a UI view) rather than finishing the whole pipeline before touching the frontend. This is what the week-by-week plan in the build guide already assumes; it also means there's always something runnable to sanity-check by hand.
4. **Skills are the process.** `/pipeline-step`, `/validate-official`, `/add-endpoint`, `/add-page`, `/model-card`, `/privacy-check`, `/release-check` are invoked manually at the point in the work where they matter, replacing the automated triggers a CI pipeline would use. Run them, don't skip them because "it's just a small change".
5. **Decisions log instead of PR review.** There's no second reviewer gating a merge, so anything worth a reviewer's sanity check (a methodology choice, a scope cut, an architecture call) goes in `docs/decisions.md` instead, dated, with the reason and the alternatives considered. Read it before reversing an earlier choice.
6. **Deploy by hand, early and often.** Push to the hosting platform's own git-triggered deploy (Render, Railway, Fly.io all offer this natively; that's the platform's feature, not a pipeline we build or maintain) from week 3 onward, and manually smoke-test the deployed URL after each deploy: open the map, switch crop and season, check a district profile loads. `/release-check` formalizes this before submission, but do a lighter version of it after every deploy, not just at the end.
7. **Satellite refresh is a manual `make gee` run during the hackathon**, not a scheduled job. Automating it with a cron workflow is explicitly a post-hackathon, "going live" task (see the build guide), not something to build now.

## Confirmed environment status

- NISR catalog IDs for every SAS year in scope (2019 to 2025) and AHS 2024 are confirmed and recorded in `config/data_sources.yaml`. Use that file, not memory, when writing download instructions or docs.
- Earth Engine project registration, API enablement, and access to all eight datasets used by the pipeline (MODIS NDVI, Sentinel-2 SR, CHIRPS, ESA WorldCover, four iSDAsoil bands, SRTM) were confirmed working with `scripts/test_gee.py` on 23 September 2026. Scale factors for every dataset are implemented in `src/agritwin/gee/scaling.py`; always import from there, never re-derive a scale factor inline.
- `GEE_PROJECT_ID` must be set in `.env` before running `make gee` or `scripts/test_gee.py`.

## Domain definitions

- Seasons: A (September to February), B (March to June), C (July to September, marshland and irrigated; excluded from MVP).
- MVP crops: maize, beans, Irish potato, plus one of sorghum or rice (decided after the variable audit). Cassava is excluded from the nowcast because its growth cycle spans several seasons.
- Core years: 2019 to 2025 (Seasons A and B). Earlier years only if harmonization is cheap.
- Yield: kg per hectare = harvest_kg / (plot_area_sqm / 10000), computed on **pure-stand plots** (one main crop on the plot) of small-scale farmers.
- District yield estimate: weighted ratio estimator sum(w * harvest_kg) / sum(w * area_ha).
- Attainable yield: weighted 90th percentile of pure-stand plot yields within zone x crop x season, pooled across core years.
- Yield gap: attainable minus actual, also shown as percent of attainable.
```

#### `Makefile`

```makefile
.PHONY: setup ingest stage marts gee features train export check-public all api web test lint docs

# Assumes an activated venv (python3 -m venv venv && source venv/bin/activate).
PY = python -m

setup:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt -r requirements-dev.txt
	./venv/bin/pip install -e .
	if [ -f web/package.json ]; then cd web && npm install; else echo "web/ not scaffolded yet, skipping (see web/CLAUDE.md, Week 2 task)"; fi
	./venv/bin/pre-commit install

ingest:
	$(PY) agritwin.ingest.run

stage:
	$(PY) agritwin.harmonize.run

marts:
	$(PY) agritwin.survey.run

gee:
	$(PY) agritwin.gee.run

features:
	$(PY) agritwin.features.run

train:
	$(PY) agritwin.models.run

export:
	$(PY) agritwin.export.run

check-public:
	python scripts/check_public.py

all: ingest stage marts gee features train export check-public

api:
	uvicorn api.app.main:app --reload --port 8000

web:
	cd web && npm run dev

test:
	pytest -q
	cd web && npm run test -- --run

lint:
	ruff check .
	mypy src api
	cd web && npm run lint && npm run typecheck

docs:
	mkdocs serve
```

#### `ORIGINALITY.md`

```markdown
# Declaration of originality

We declare that this submission to the NISR 2026 Big Data Hackathon is original work produced by our team for this competition, has not been submitted to any other competition or entity, and is not derived from either team member's other coursework, theses, or client projects. All third-party data, libraries and references are cited in `docs/AgriTwin_Master_Build_Guide.md` and in code comments where used. AI assistance is disclosed in `AI_DISCLOSURE.md`.

Team members: Ahourdet Donambi Thierry (thierrydonambi@gmail.com), Ishimwe Aime Cesar (ishimweaimecesar5@gmail.com).
```

#### `README.md`

```markdown
# AgriTwin Rwanda

Early-season crop yield intelligence and yield-gap analysis for Rwanda. Built for the NISR 2026 Big Data Hackathon (Track 1, Agricultural Productivity).

- Problem, users and methodology: see `docs/AgriTwin_Master_Build_Guide.md` and the deployed docs site.
- Live app: <deployed web URL>
- API docs: <deployed API URL>/docs
- Demo video: <YouTube unlisted link>
- Data access: raw NISR microdata is not in this repository. See `docs/data/README.md` for how to request it from NISR and reproduce `data/public/`.
- AI disclosure: `AI_DISCLOSURE.md`
- Originality declaration: `ORIGINALITY.md`

## Quick start

```bash
git clone <repo-url> && cd agritwin-rwanda
cp .env.example .env
make setup
# with data/raw populated per docs/data/README.md:
make all
make api    # http://localhost:8000
make web    # http://localhost:5173
```

Or with Docker:

```bash
docker compose up --build
```

## Team
Ahourdet Donambi Thierry, data engineering, models, API, deployment. Ishimwe Aime Cesar, survey methodology, validation, Kinyarwanda, domain research.
```

#### `docker-compose.yml`

```yaml
services:
  api:
    build:
      context: .
      dockerfile: infra/Dockerfile.api
    ports: ["8000:8000"]
    volumes:
      - ./data/public:/app/data/public:ro
    environment:
      - DATA_DIR=/app/data
      - API_ALLOWED_ORIGINS=http://localhost:5173
  web:
    build:
      context: .
      dockerfile: infra/Dockerfile.web
      args:
        VITE_API_BASE: http://localhost:8000/api/v1
    ports: ["5173:80"]
    depends_on: [api]
```

#### `pyproject.toml`

```toml
[project]
name = "agritwin"
version = "0.1.0"
description = "AgriTwin Rwanda: early-season crop yield intelligence and yield-gap analysis (NISR 2026 Big Data Hackathon)"
requires-python = ">=3.12"
# Runtime and dev dependencies live in requirements.txt / requirements-dev.txt,
# not here. This file exists so `pip install -e .` makes the `agritwin`
# package (under src/) importable everywhere, including in scripts/test_gee.py
# and the test suite.
dependencies = []

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "PD"]

[tool.pytest.ini_options]
testpaths = ["tests", "api/tests"]
```

#### `requirements-dev.txt`

```text
# AgriTwin Rwanda -- development-only dependencies (tests, linting, notebooks, docs).
# Install alongside requirements.txt:
#   pip install -r requirements.txt -r requirements-dev.txt

-r requirements.txt

pytest
pytest-cov
hypothesis
ruff
mypy
pre-commit
nbstripout
jupyterlab
httpx
mkdocs-material
mkdocstrings[python]
```

#### `requirements.txt`

```text
# AgriTwin Rwanda -- runtime dependencies (pipeline + API).
# Create a venv and install with:
#   python3 -m venv venv
#   source venv/bin/activate        # Windows: venv\Scripts\activate
#   pip install -r requirements.txt
# For linting, tests, notebooks and docs, also install requirements-dev.txt.

# data handling
polars
pandas
pyarrow
pyreadstat
duckdb

# geospatial
geopandas
shapely
pyogrio

# satellite data
earthengine-api

# modelling
scikit-learn
lightgbm
shap
samplics

# utilities
pyyaml
loguru
typer
python-dotenv

# reporting / PDF briefs
matplotlib
weasyprint
jinja2

# API
fastapi
uvicorn[standard]
pydantic>=2
pydantic-settings
```

#### `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(python -m venv:*)",
      "Bash(python3 -m venv:*)",
      "Bash(pip install:*)",
      "Bash(./venv/bin/pip:*)",
      "Bash(python -m pytest:*)",
      "Bash(pytest:*)",
      "Bash(python -m agritwin.*:*)",
      "Bash(ruff:*)",
      "Bash(mypy:*)",
      "Bash(pre-commit:*)",
      "Bash(make:*)",
      "Bash(npm run:*)",
      "Bash(npm ci)",
      "Bash(npm install:*)",
      "Bash(npx:*)",
      "Bash(git status)",
      "Bash(git diff:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git log:*)",
      "Bash(git ls-files:*)",
      "Bash(ls:*)",
      "Bash(cat:*)",
      "Bash(docker compose:*)"
    ],
    "ask": [
      "Bash(git push:*)",
      "Bash(rm:*)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Bash(git push --force:*)",
      "Bash(git push -f:*)",
      "Bash(rm -rf data:*)"
    ]
  }
}
```

#### `.claude/agents/privacy-guard.md`

```markdown
---
name: privacy-guard
description: Scans the repository, public outputs and notebooks for any leakage of NISR microdata or identifying information. Use before commits touching data/public and before release.
tools: Read, Grep, Glob, Bash
---

You protect the confidentiality of NISR microdata.

Check:
1. Tracked files: no raw, interim, staging or mart data; no microdata formats outside allowed folders.
2. `data/public/`: finest geography is district; no identifier columns (farmer_id, segment_id, plot_id, s1q4, s1q6, Segment_ID); no rows with fewer than the minimum cell size unless flagged low_reliability and the value is suppressed or clearly flagged per settings.
3. Notebooks: outputs stripped; no printed raw rows.
4. Logs, fixtures and docs: no copied real rows. Test fixtures must be synthetic.
5. Deployed artefacts: Dockerfiles copy only `data/public/`.

Report must-fix items with file paths and the exact remediation. Do not edit files yourself.
```

#### `.claude/agents/survey-methodologist.md`

```markdown
---
name: survey-methodologist
description: Reviews survey estimation, weighting, variance estimation, yield computation and model validation for statistical correctness. Use proactively after changes in src/agritwin/survey, clean, features or models.
tools: Read, Grep, Glob, Bash
---

You are a survey statistician familiar with area-frame agricultural surveys like the Rwanda Seasonal Agricultural Survey (SAS) and with small-sample predictive modelling.

When invoked, review the changed code and outputs for:

1. Correct use of weights, strata and PSUs. Ratio estimators for yield (sum of weighted harvest over sum of weighted area), not means of plot yields, unless explicitly justified.
2. Variance estimation: PSU bootstrap resamples segments within strata with the right number of draws; single-PSU strata handled; CIs reported.
3. Yield QC: units (sqm to ha, kg), pure-stand filter, outlier trimming rules applied per crop and season, no silent row drops.
4. Leakage: GroupKFold by district for plot models, leave-one-year-out for the nowcast, target-derived features computed within folds only, no future satellite data used for an earlier lead month.
5. Baselines: every reported metric compared with naive baselines (previous year same season, district mean).
6. Language: outputs described as associations and model-based estimates, not causal effects.

Report findings as: must-fix, should-fix, note. Quote file and line. Propose the concrete fix. Do not edit files yourself.
```

#### `.claude/agents/ux-reviewer.md`

```markdown
---
name: ux-reviewer
description: Reviews React pages and components for usability, clarity of statistics, accessibility, mobile layout and translation completeness. Use after building or changing a page.
tools: Read, Grep, Glob, Bash
---

You are a product designer who builds decision tools for government planners with limited time and mixed data literacy.

Review against `web/CLAUDE.md` UX rules and check:
1. Can a district agronomist answer "where is the biggest maize gap and why" in under 2 minutes and 3 clicks?
2. Is every number paired with its interval and plain-language caption? Are model outputs badged?
3. Mobile at 360 px: stacking, readable text (at least 14 px), touch targets at least 44 px.
4. Accessibility: keyboard reachability, focus order, aria labels, colour contrast, colour-blind safe scales.
5. i18n: no hardcoded strings, keys present in en, fr, rw.
6. Loading, error and empty states exist and help the user.
7. Visual hierarchy: one primary action per view, consistent spacing, no clutter.

Report must-fix, should-fix and nice-to-have, each with file and a concrete change. Do not edit files yourself.
```

#### `.claude/skills/add-endpoint/SKILL.md`

```markdown
---
name: add-endpoint
description: Add a FastAPI endpoint serving precomputed data, with Pydantic schema, tests and regenerated frontend types.
disable-model-invocation: true
argument-hint: "[METHOD /path and purpose]"
---

Add this API endpoint: $ARGUMENTS

1. Read `api/CLAUDE.md`. Confirm the data it needs already exists in `data/public/`. If not, stop and tell me which export step is missing.
2. Add the Pydantic response model to `api/app/schemas.py`, the route to the right router, and data access in `data_store.py`.
3. Validate query params with enums, return 404 for unknown entities, include interval and reliability fields.
4. Add tests in `api/tests/` (happy path, invalid param, unknown district).
5. Run the API, then run `npm run gen:types` in `web/` to refresh TypeScript types.
6. Run `make lint` and `make test`.
```

#### `.claude/skills/add-page/SKILL.md`

```markdown
---
name: add-page
description: Add or rework a page in the React app following the UX rules, with translations and tests.
disable-model-invocation: true
argument-hint: "[page name and purpose]"
---

Build this page: $ARGUMENTS

1. Read `web/CLAUDE.md` and the page spec in `docs/AgriTwin_Master_Build_Guide.md` (section on pages).
2. Propose the layout (desktop and 360 px mobile), components, data hooks and user flow. Wait for approval.
3. Implement with existing components where possible. All strings via `t()` with keys added to en.json, fr.json and rw.json (rw may be marked TODO for the teammate to translate).
4. Include loading, error and empty states, the model-based badge where relevant, and interval display for every number.
5. Add vitest tests for any logic and a render test for the page.
6. Run `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`.
7. Then ask the `ux-reviewer` subagent to review the page and apply its must-fix items.
```

#### `.claude/skills/audit-sas/SKILL.md`

```markdown
---
name: audit-sas
description: Profile the SAS microdata files for one year and update the variable audit and the SAS variable map. Use when a new SAS year is added or when harmonization fails.
disable-model-invocation: true
argument-hint: "[year] e.g. 2024"
---

Audit the Seasonal Agricultural Survey files for year $ARGUMENTS.

1. List every file in `data/raw/sas/$ARGUMENTS/` with size and format.
2. For each file, read it with pyreadstat (metadata only first, then data) and print: number of rows, number of columns, and for each column its name, label, dtype, share missing, and number of distinct values. Do not print raw rows beyond 5.
3. Identify, for Seasons A and B production files, the source columns for each canonical variable listed in `src/agritwin/CLAUDE.md` (staging schema). Use variable labels and the questionnaire in `docs/data/questionnaires/` when names are generic like V1 to V100.
4. For unlabeled files, match columns by position and value patterns against the closest labeled year, and mark each match with a confidence level (high, medium, low).
5. Update `config/sas_variable_map.yaml` for this year and add a section to `docs/data/variable_audit.md` with a table: canonical name, source column, label, confidence, notes.
6. Report: missing canonical variables, crop code list with counts of pure-stand plots per MVP crop and season, number of districts present, weight variable summary (min, max, sum).
7. Stop and ask me before guessing any variable marked low confidence.
```

#### `.claude/skills/log-ai-use/SKILL.md`

```markdown
---
name: log-ai-use
description: Append an entry to the AI usage log required for the NISR AI disclosure.
disable-model-invocation: true
argument-hint: "[what was done in this session]"
---

Append one row to the table in `docs/ai-usage-log.md` for this session: $ARGUMENTS

Columns: date (YYYY-MM-DD), tool (Claude Code, model name if known), area (pipeline, model, api, web, docs), task summary in one sentence, files touched, human review done (what the team checked or changed).
Keep it factual and short. Do not remove earlier rows.
```

#### `.claude/skills/model-card/SKILL.md`

```markdown
---
name: model-card
description: Generate or update a model card for one trained model from its artifact metadata and evaluation outputs.
disable-model-invocation: true
argument-hint: "[attainable | drivers | nowcast]"
---

Write the model card for: $ARGUMENTS

1. Read `artifacts/$ARGUMENTS/metadata.json` and the evaluation outputs in `data/marts/`.
2. Fill `docs/models/_template.md` into `docs/models/$ARGUMENTS.md`: purpose, intended users and uses, out-of-scope uses, data (sources, years, filters, n), target, features, method, validation scheme, metrics with baselines, uncertainty method, known limitations, fairness and representativeness notes (small vs large farms, districts with few plots), versioning.
3. Use plain language a district agronomist can follow, with a short technical subsection for statisticians.
4. No em dashes or en dashes.
```

#### `.claude/skills/pipeline-step/SKILL.md`

```markdown
---
name: pipeline-step
description: Add or change one pipeline step in src/agritwin with tests and a Makefile target.
disable-model-invocation: true
argument-hint: "[short description of the step]"
---

Implement this pipeline step: $ARGUMENTS

1. Read `src/agritwin/CLAUDE.md` and the relevant section of `docs/AgriTwin_Master_Build_Guide.md`.
2. Propose a plan: inputs (files, schemas), outputs (files, schemas), functions, tests, settings keys. Wait for my approval.
3. Implement pure functions plus a thin runner. Read tunable values from `config/settings.yaml`.
4. Add unit tests in `tests/` using synthetic fixtures. Include one test for row-count preservation and one for an edge case (missing weight, zero area, unknown crop code).
5. Wire the step into the Makefile and `make all` in the right order.
6. Run `make lint` and `make test`. Fix failures.
7. Summarize what changed and suggest a Conventional Commit message.
```

#### `.claude/skills/privacy-check/SKILL.md`

```markdown
---
name: privacy-check
description: Check that nothing in the repository or deployable outputs contains plot-level or identifying NISR microdata.
disable-model-invocation: true
---

Run a privacy and confidentiality check.

1. Run `make check-public` and report its output.
2. Run `git ls-files` and flag any .dta, .sav, .sas7bdat, .parquet or .csv file outside `data/public/`, `data/external/official/`, `data/external/boundaries/`, `data/external/gee/` and test fixtures.
3. Inspect every file in `data/public/`: confirm the finest geography is district, no column holds farmer, segment or plot identifiers, and every row with an estimate reports n_plots and reliability.
4. Search the git history for raw data paths: `git log --all --stat -- 'data/raw/*' 'data/interim/*' 'data/staging/*'`.
5. Check notebooks for saved outputs that show raw rows; outputs must be cleared (`nbstripout`).
6. Delegate a second pass to the `privacy-guard` subagent.
7. Report findings as must-fix and ok.
```

#### `.claude/skills/release-check/SKILL.md`

```markdown
---
name: release-check
description: Run the NISR submission checklist against the repository and deployed URLs.
disable-model-invocation: true
argument-hint: "[web URL] [api URL]"
---

Run the release checklist. Deployed URLs: $ARGUMENTS

1. Repository: README complete (problem, users, screenshots, demo video link, architecture, quick start, data access instructions), AI_DISCLOSURE.md present and up to date with `docs/ai-usage-log.md`, ORIGINALITY.md present, LICENSE and NOTICE mention the IP transfer to NISR, `docker compose up` instructions tested.
2. Run `make lint`, `make test`, and a clean `docker compose build`.
3. Hit every API endpoint on the deployed API URL and report status codes and latency.
4. Check the deployed web URL: all pages load, language switch works, no console errors (describe what to check manually if you cannot open a browser).
5. Docs site builds with `mkdocs build --strict`.
6. Run `/privacy-check`.
7. Output a checklist with pass or fail and the fix for each failure.
```

#### `.claude/skills/validate-official/SKILL.md`

```markdown
---
name: validate-official
description: Compare our weighted SAS estimates with the official NISR published figures and write a validation report.
disable-model-invocation: true
argument-hint: "[year] [season] e.g. 2024 A"
---

Validate our estimates for $ARGUMENTS against official NISR figures.

1. Load official figures from `data/external/official/sas_official_{year}.csv` (transcribed from the SAS annual report tables). If the file is missing, tell me which tables to transcribe and stop.
2. Compute with our pipeline: national and district cultivated area, production and yield for each MVP crop, and adoption rates (improved seed, inorganic fertilizer, irrigation, anti-erosion) at farmer level.
3. Produce a comparison table: indicator, official, ours, absolute difference, relative difference, our 95 percent CI, and whether the official value falls inside our CI.
4. Flag any relative difference above the tolerance in `config/settings.yaml` (validation.tolerance_pct).
5. Explain likely causes of differences (pure-stand restriction, large-scale farms, crop-cut vs farmer-reported, outlier trimming).
6. Write the report to `docs/methodology/validation_{year}{season}.md` and a CSV to `data/public/validation/`.
```

#### `api/CLAUDE.md`

```markdown
# API conventions (api/)

FastAPI app that serves **precomputed, aggregated** results from `data/public/`. It never touches microdata and never trains models.

## Structure

```
api/
  app/
    main.py            # app factory, CORS, gzip, routers, lifespan loads data store
    settings.py        # pydantic-settings: DATA_DIR, ALLOWED_ORIGINS, CACHE_SECONDS
    data_store.py      # loads Parquet/JSON into memory once (DuckDB in-memory or polars)
    schemas.py         # Pydantic response models, shared enums (Crop, Season)
    routers/
      meta.py  kpis.py  yield_gap.py  districts.py  drivers.py  nowcast.py  scenario.py  geo.py  briefs.py
  tests/
  Dockerfile
```

## Endpoints (v1, prefix /api/v1)

| Method | Path | Returns |
|---|---|---|
| GET | /health | status, data_version |
| GET | /meta | crops, seasons, years, districts, data_version, last_updated |
| GET | /kpis?year&season | national KPI cards with CIs |
| GET | /yield-gap?crop&season&year | 30 rows: district, actual, attainable, gap, gap_pct, CIs, n_plots, reliability |
| GET | /districts/{code}/profile?crop&season | trend, gap, top drivers, peer districts |
| GET | /drivers?crop&season[&district] | SHAP summaries: feature, mean_abs_shap, direction |
| GET | /nowcast?crop&season&year[&lead] | 30 rows: prediction, interval, lead_month, is_backtest, actual if known |
| GET | /nowcast/{code}/curve?season&year | NDVI and rainfall curve vs climatology |
| GET | /backtest?crop&season | metrics per model and lead month vs baselines |
| GET | /scenario/{code}?crop&season | the 16 lever-configuration means + bootstrap draws for client-side scenario |
| GET | /geo/districts | simplified district GeoJSON |
| GET | /briefs/{code}.pdf?crop&season | precomputed PDF brief |

## Rules

- All responses are typed Pydantic models, so OpenAPI docs at /docs are complete and judges can read them.
- Query parameters validated with enums; unknown crop or district returns 404 with a clear message.
- Every numeric estimate field comes with `ci_low`, `ci_high` (or `pi_low`, `pi_high`) and `reliability`.
- Set `Cache-Control: public, max-age=3600` on data endpoints.
- CORS restricted to the deployed web origin and localhost.
- Tests with `fastapi.testclient` against a small fixture `data/public` built in `api/tests/fixtures/`.
- Keep cold start fast: data loading under 2 seconds, image under 400 MB.
```

#### `config/crops.yaml`

```yaml
# Map source crop codes or labels (per year) to canonical crops. Filled by /audit-sas.
canonical:
  maize: {label_en: Maize, label_fr: "Maïs", label_rw: Ibigori}
  beans: {label_en: Beans, label_fr: Haricots, label_rw: Ibishyimbo}
  irish_potato: {label_en: Irish potato, label_fr: "Pomme de terre", label_rw: Ibirayi}
  sorghum: {label_en: Sorghum, label_fr: Sorgho, label_rw: Amasaka}
  rice: {label_en: Rice, label_fr: Riz, label_rw: Umuceri}
source_codes: {}
```

#### `config/data_sources.yaml`

```yaml
# Confirmed data sources for AgriTwin Rwanda.
# NISR catalog IDs verified against the live catalog on 23 September 2026.
# GEE dataset IDs and scale factors verified by an actual ee.Initialize() +
# dataset access test on the same date (see scripts/test_gee.py).

nisr:
  base_url: "https://www.microdata.statistics.gov.rw/index.php/catalog"
  # pattern per study: {base_url}/{catalog_id}
  #   overview:        {base_url}/{catalog_id}
  #   data dictionary:  {base_url}/{catalog_id}/data-dictionary
  #   download:         {base_url}/{catalog_id}/get-microdata   (login required)
  sas:
    2013: {catalog_id: 66,  confirmed: true, note: "core scope starts 2019; earlier years optional"}
    2014: {catalog_id: 78,  confirmed: true, note: "optional, not in core scope"}
    2015: {catalog_id: 77,  confirmed: true, note: "optional, not in core scope"}
    2017: {catalog_id: 88,  confirmed: true, note: "optional, not in core scope"}
    2019: {catalog_id: 93,  confirmed: true, note: "core scope start"}
    2020: {catalog_id: 99,  confirmed: true}
    2021: {catalog_id: 102, confirmed: true}
    2022: {catalog_id: 103, confirmed: true}
    2023: {catalog_id: 111, confirmed: true}
    2024: {catalog_id: 113, confirmed: true, note: "reference year, fully labeled dictionary"}
    2025: {catalog_id: 124, confirmed: true, note: "production files unlabeled (V1-V100); run /audit-sas 2025 before use"}
    # 2016 and 2018 not confirmed; look up the same way if the core scope is extended.
  ahs:
    2024: {catalog_id: 123, confirmed: true}

gee:
  # ee.Initialize(project=<your project id>) then use these snippets directly.
  # Verified reachable and returning expected bands on 23 September 2026.
  datasets:
    modis_ndvi:
      id: "MODIS/061/MOD13Q1"
      type: ImageCollection
      resolution_m: 250
      cadence: "16-day composite"
      bands_used: [NDVI, EVI]
      scale_factor: 0.0001          # stored as int16 x10000; multiply by 0.0001 for real NDVI/EVI in [-1, 1]
      use: "primary nowcast signal, full 2019-2025 history"
    sentinel2_sr:
      id: "COPERNICUS/S2_SR_HARMONIZED"
      type: ImageCollection
      resolution_m: 10
      cadence: "~5 day"
      bands_used: [B4, B8]          # red, NIR, for computing NDVI at 10m
      scale_factor: 0.0001          # surface reflectance bands are int, x10000
      use: "current-season high-resolution map; reliable coverage only from ~2019 onward"
      cloud_mask_band: SCL          # use Scene Classification Layer to mask cloud/shadow before compositing
    chirps_daily:
      id: "UCSB-CHG/CHIRPS/DAILY"
      type: ImageCollection
      resolution_m: 5566
      cadence: daily
      bands_used: [precipitation]
      scale_factor: 1.0             # already in mm/day, no rescale needed
      use: "rainfall totals and anomalies, driver + nowcast features"
    esa_worldcover:
      id: "ESA/WorldCover/v200"
      type: ImageCollection
      resolution_m: 10
      cadence: "single map, 2021"
      bands_used: [Map]
      scale_factor: null            # categorical class codes, no rescale; class 40 = cropland
      use: "cropland mask so NDVI/rainfall are averaged over cropland pixels only"
    isda_ph:
      id: "ISDASOIL/Africa/v1/ph"
      type: Image
      resolution_m: 30
      bands_used: [mean_0_20]
      scale_factor_formula: "x / 10"
      use: "soil pH feature for the driver model"
    isda_nitrogen:
      id: "ISDASOIL/Africa/v1/nitrogen_total"
      type: Image
      resolution_m: 30
      bands_used: [mean_0_20]
      scale_factor_formula: "exp(x / 100) - 1"
      use: "soil nitrogen feature"
    isda_carbon:
      id: "ISDASOIL/Africa/v1/carbon_organic"
      type: Image
      resolution_m: 30
      bands_used: [mean_0_20]
      scale_factor_formula: "exp(x / 10) - 1"
      use: "soil organic carbon feature"
    isda_texture:
      id: "ISDASOIL/Africa/v1/texture_class"
      type: Image
      resolution_m: 30
      bands_used: [texture_0_20]
      scale_factor: null             # categorical, no rescale
      use: "soil texture class feature"
    srtm:
      id: "USGS/SRTMGL1_003"
      type: Image
      resolution_m: 30
      bands_used: [elevation]
      scale_factor: 1.0
      use: "terrain, slope for zoning; not required for MVP but cheap to pull alongside soil"
```

#### `config/sas_variable_map.yaml`

```yaml
# canonical_name: source column per year and file type.
# 2024 Season B production names come from the NISR data dictionary (catalog 113, file F6).
# All other years must be filled by the /audit-sas skill. Do not guess.
2024:
  production:
    segment_id: Segment_ID
    province_code: s1q1
    district_code: s1q2
    stratum: s1q3
    segment_no: s1q4
    farmer_id: s1q6
    farmer_type: s1q7
    plot_id: s2q1
    plot_area_sqm: s2q2
    n_main_crops: s2q3
    crop_code_src: s2q4
    sowing_date: s2q7
    improved_seed: s2q9
    harvest_kg_plot: s2q21      # verify: total harvest this season (kg)
    harvest_kg_crop: s2q22      # verify: total for this crop this season (kg)
    qty_lost_kg: s2q39
    organic_fert: s3q3
    inorganic_fert: s3q9
    pesticide: s3q19
    erosion_degree: s4q1
    anti_erosion: s4q3
    land_consolidation: s4q6
    mechanized: s4q9
    irrigated: s4q15
    interview_date: s5q12
    weight: plot_weight
2025:
  production: {}   # V1 to V100 unlabeled in the dictionary; map by position with /audit-sas
```

#### `config/settings.yaml`

```yaml
project:
  name: AgriTwin Rwanda
  data_version: "2026.10.0"

scope:
  years: [2019, 2020, 2021, 2022, 2023, 2024, 2025]
  seasons: [A, B]
  crops: [maize, beans, irish_potato, sorghum]   # 4th crop confirmed after audit (sorghum or rice)
  farmer_types: [SSF]                             # small-scale farmers; LSF reported separately if at all

season_windows:        # calendar months, used for satellite features
  A: {start_month: 9, end_month: 2}
  B: {start_month: 3, end_month: 6}

survey:
  weight_col: weight
  strata_col: stratum
  psu_col: segment_id
  bootstrap_reps: 200
  ci_level: 0.95
  n_min: 30             # unweighted plots per cell below which reliability = low
  cv_max: 0.30          # coefficient of variation above which reliability = low

yield_qc:
  min_plot_area_sqm: 20
  trim_lower_pct: 0.5   # per crop x season x year
  trim_upper_pct: 99.5
  max_yield_kg_ha:      # agronomic plausibility caps, flag above
    maize: 12000
    beans: 5000
    irish_potato: 50000
    sorghum: 8000
    rice: 12000

attainable:
  percentile: 90
  zone_method: aez      # aez if an agro-ecological zone layer is available, else kmeans
  kmeans_k: 5

drivers:
  target: log_yield
  cv: group_kfold_district
  n_splits: 5
  levers: [improved_seed, inorganic_fert, organic_fert, irrigated]

nowcast:
  lead_months: [2, 3, 4]
  target: district_yield_anomaly
  cv: leave_one_year_out
  models: [baseline_last_year, baseline_district_mean, ridge, lgbm_small]
  ndvi_source: modis     # MODIS for history; Sentinel-2 used for recent maps only
  rainfall_climatology: [1991, 2020]
  ndvi_climatology: [2001, 2018]

validation:
  tolerance_pct: 10

export:
  public_dir: data/public
  simplify_tolerance_m: 150
```

#### `docs/ai-usage-log.md`

```markdown
# AI usage log

Required by NISR hackathon rule 10 (AI use must be disclosed). Append one row per work session using `/log-ai-use`. Never delete rows.

| Date | Tool | Area | Task | Files touched | Human review |
|---|---|---|---|---|---|
```

#### `docs/decisions.md`

```markdown
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
```

#### `docs/data/README.md`

```markdown
# Data access

Raw NISR microdata is never committed to this repository (see `CLAUDE.md` golden rule 1). Full machine-readable source of truth: `config/data_sources.yaml`.

## NISR microdata

Browse a study at `https://www.microdata.statistics.gov.rw/index.php/catalog/{catalog_id}`. Its data dictionary is at `.../catalog/{catalog_id}/data-dictionary` and the actual download is at `.../catalog/{catalog_id}/get-microdata` (registration and login required).

Confirmed catalog IDs, core scope (2019 to 2025):

| Study | Catalog ID | Link |
|---|---|---|
| SAS 2019 | 93 | https://www.microdata.statistics.gov.rw/index.php/catalog/93 |
| SAS 2020 | 99 | https://www.microdata.statistics.gov.rw/index.php/catalog/99 |
| SAS 2021 | 102 | https://www.microdata.statistics.gov.rw/index.php/catalog/102 |
| SAS 2022 | 103 | https://www.microdata.statistics.gov.rw/index.php/catalog/103 |
| SAS 2023 | 111 | https://www.microdata.statistics.gov.rw/index.php/catalog/111 |
| SAS 2024 | 113 | https://www.microdata.statistics.gov.rw/index.php/catalog/113 |
| SAS 2025 | 124 | https://www.microdata.statistics.gov.rw/index.php/catalog/124 |
| AHS 2024 | 123 | https://www.microdata.statistics.gov.rw/index.php/catalog/123 |

Optional, earlier years, only if the core scope is extended: SAS 2013 (ID 66), 2014 (ID 78), 2015 (ID 77), 2017 (ID 88). 2016 and 2018 IDs are not yet confirmed.

Steps:

1. Register at https://microdata.statistics.gov.rw and request access to each study above.
2. Place downloaded files under `data/raw/sas/{year}/` and `data/raw/ahs/2024/` exactly as downloaded.
3. Run `make ingest stage marts`.

## Earth Engine (satellite and soil data)

Confirmed working end to end (project registration, API enablement, dataset access, and a real `reduceRegion` compute call) on 23 September 2026 with `scripts/test_gee.py`. Run that script first in any new environment before trusting `make gee`.

| Dataset | Earth Engine ID | Use | Scale factor |
|---|---|---|---|
| MODIS NDVI/EVI | `MODIS/061/MOD13Q1` | Nowcast history, 2019-2025 | multiply by 0.0001 |
| Sentinel-2 SR | `COPERNICUS/S2_SR_HARMONIZED` | Current-season high-res map | multiply by 0.0001 |
| CHIRPS Daily | `UCSB-CHG/CHIRPS/DAILY` | Rainfall totals and anomalies | none, already mm/day |
| ESA WorldCover | `ESA/WorldCover/v200` | Cropland mask | none, categorical |
| iSDAsoil pH | `ISDASOIL/Africa/v1/ph` | Soil driver feature | x / 10 |
| iSDAsoil Nitrogen | `ISDASOIL/Africa/v1/nitrogen_total` | Soil driver feature | exp(x / 100) - 1 |
| iSDAsoil Carbon | `ISDASOIL/Africa/v1/carbon_organic` | Soil driver feature | exp(x / 10) - 1 |
| SRTM elevation | `USGS/SRTMGL1_003` | Terrain, zoning | none |

All scale factors are implemented once in `src/agritwin/gee/scaling.py`; every extraction function imports from there rather than re-deriving them.

Setup:

1. Register your project at https://code.earthengine.google.com/register (Community tier, 150 EECU-hours/month, is enough for this workload).
2. Enable the API directly if prompted: `https://console.developers.google.com/apis/api/earthengine.googleapis.com/overview?project={your-project-id}` (can take a few minutes to propagate after enabling).
3. `earthengine authenticate` once per machine.
4. Set `GEE_PROJECT_ID` in `.env`.
5. Run `python scripts/test_gee.py` to confirm before running `make gee`.
```

#### `docs/data/variable_audit.md`

```markdown
# SAS variable audit

Filled in by the `/audit-sas` skill, one section per year. Do not hand-edit numbers here without re-running the audit; this file is the evidence trail for `config/sas_variable_map.yaml`.

## 2024

Source: NISR catalog record 113, Season B production file (F6), confirmed from the published data dictionary.

| Canonical | Source column | Label | Confidence |
|---|---|---|---|
| district_code | s1q2 | 1.2 District name and code | high |
| plot_area_sqm | s2q2 | 2.2 Plot area (sqm) | high |
| improved_seed | s2q9 | 2.9 Did you use improved seed | high |
| harvest_kg_crop | s2q22 | 2.22 Total quantity of harvest for this crop this season (Kg) | medium, confirm vs s2q21 |
| weight | plot_weight | plot_weight | high |

Open question: s2q21 ("total quantity of harvest for this season") vs s2q22 ("for this crop this season") on a pure-stand plot should be equal; confirm with a cross-tab before using either as the yield numerator.

## 2025

Not yet audited. Data dictionary lists 101 unlabeled variables (V1 to V100 plus one more) for the Season B production file. Run `/audit-sas 2025` after downloading the file.

## 2019 to 2023

Not yet audited. Run `/audit-sas <year>` for each.
```

#### `docs/models/_template.md`

```markdown
# Model card: <name>

## Purpose
## Intended users and uses
## Out of scope uses
## Data
- Sources, years, seasons, crops, filters, n plots (weighted and unweighted)
## Target
## Features
## Method
## Validation scheme
## Metrics (with baselines)
## Uncertainty method
## Limitations
## Fairness and representativeness notes
## Version
- Data version, git commit, date
```

#### `infra/Dockerfile.api`

```text
FROM python:3.12-slim AS base
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY pyproject.toml ./
COPY api ./api
COPY src ./src
RUN pip install --no-cache-dir -e .
COPY data/public ./data/public
EXPOSE 8000
CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `infra/Dockerfile.web`

```text
FROM node:20-slim AS build
WORKDIR /app
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE
COPY web/package*.json ./
RUN npm ci
COPY web .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

#### `scripts/check_public.py`

```python
"""Block commits of microdata and validate aggregated public outputs.

Usage:
    python scripts/check_public.py            # check data/public contents
    python scripts/check_public.py --staged   # also check files staged for commit
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import polars as pl

FORBIDDEN_EXT = {".dta", ".sav", ".sas7bdat"}
DATA_EXT = {".parquet", ".csv", ".dta", ".sav", ".sas7bdat", ".xlsx"}
ALLOWED_DATA_DIRS = (
    "data/public/",
    "data/external/official/",
    "data/external/boundaries/",
    "data/external/gee/",
    "tests/fixtures/",
    "api/tests/fixtures/",
)
FORBIDDEN_COLS = {
    "farmer_id", "segment_id", "plot_id", "segment_no",
    "s1q4", "s1q6", "s2q1", "segment_id_src", "Segment_ID",
}


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True
    )
    return [f for f in out.stdout.splitlines() if f]


def check_staged(errors: list[str]) -> None:
    for f in staged_files():
        p = Path(f)
        if p.suffix.lower() in FORBIDDEN_EXT and not f.startswith(("tests/fixtures/", "api/tests/fixtures/")):
            errors.append(f"microdata file staged: {f}")
        elif p.suffix.lower() in DATA_EXT and not f.startswith(ALLOWED_DATA_DIRS):
            errors.append(f"data file outside allowed folders: {f}")


def check_public(errors: list[str]) -> None:
    root = Path("data/public")
    if not root.exists():
        return
    for p in root.rglob("*.parquet"):
        df = pl.read_parquet(p)
        bad = FORBIDDEN_COLS.intersection(df.columns)
        if bad:
            errors.append(f"{p}: identifier columns present {sorted(bad)}")
        if "n_plots" in df.columns and "reliability" not in df.columns:
            errors.append(f"{p}: has n_plots but no reliability column")


def main() -> int:
    errors: list[str] = []
    if "--staged" in sys.argv:
        check_staged(errors)
    check_public(errors)
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        print("Privacy check failed. See CLAUDE.md golden rule 1.")
        return 1
    print("Privacy check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

#### `scripts/test_gee.py`

```python
"""
test_gee.py -- confirms Earth Engine works for AgriTwin before the pipeline is built.

First time only:
    pip install earthengine-api python-dotenv
    earthengine authenticate      # opens a browser, log in with the account tied to your project

Set GEE_PROJECT_ID in .env (copy .env.example if you haven't), then:
    python scripts/test_gee.py

Confirmed working against all six datasets on 23 September 2026. If any dataset
check fails, see docs/data/README.md for the registration and API-enable steps.
"""

import os
import sys

import ee
from dotenv import load_dotenv

from agritwin.gee.scaling import (
    CHIRPS_SCALE,
    MODIS_NDVI_SCALE,
    isda_ph,
)

load_dotenv()
PROJECT_ID = os.environ.get("GEE_PROJECT_ID")

if not PROJECT_ID or PROJECT_ID == "your-earth-engine-project-id":
    print(
        "GEE_PROJECT_ID is not set. Copy .env.example to .env and set GEE_PROJECT_ID "
        "to your real Earth Engine project ID, then run this script again.",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> None:
    print(f"Initializing Earth Engine with project: {PROJECT_ID}")
    ee.Initialize(project=PROJECT_ID)
    print("Initialized OK.\n")

    rwanda = ee.Geometry.Rectangle([28.85, -2.85, 30.90, -1.05])

    checks = [
        ("MODIS NDVI (MOD13Q1)", lambda: ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate("2024-01-01", "2024-02-01").filterBounds(rwanda).first()),
        ("Sentinel-2 SR", lambda: ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterDate("2024-01-01", "2024-02-01").filterBounds(rwanda).first()),
        ("CHIRPS Daily rainfall", lambda: ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filterDate("2024-01-01", "2024-01-05").filterBounds(rwanda).first()),
        ("ESA WorldCover", lambda: ee.ImageCollection("ESA/WorldCover/v200").first()),
        ("iSDAsoil pH", lambda: ee.Image("ISDASOIL/Africa/v1/ph")),
        ("iSDAsoil Total Nitrogen", lambda: ee.Image("ISDASOIL/Africa/v1/nitrogen_total")),
        ("iSDAsoil Organic Carbon", lambda: ee.Image("ISDASOIL/Africa/v1/carbon_organic")),
        ("SRTM elevation", lambda: ee.Image("USGS/SRTMGL1_003")),
    ]

    print("Checking dataset access:")
    for name, get_image in checks:
        try:
            img = get_image()
            band_names = img.bandNames().getInfo()
            print(f"  OK   {name:<28} bands: {band_names}")
        except Exception as e:
            print(f"  FAIL {name:<28} {e}")

    print("\nRunning a real reduceRegion (this is what costs EECU-hours):")
    ndvi_img = (
        ee.ImageCollection("MODIS/061/MOD13Q1")
        .filterDate("2024-01-01", "2024-02-01")
        .filterBounds(rwanda)
        .select("NDVI")
        .mean()
        .multiply(MODIS_NDVI_SCALE)
    )
    result = ndvi_img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=rwanda, scale=250, maxPixels=1e9,
    ).getInfo()
    print(f"  Mean NDVI over Rwanda, Jan 2024 (scaled): {result}")

    print("\nRunning a real iSDAsoil pH reduceRegion, back-transformed:")
    ph_img = ee.Image("ISDASOIL/Africa/v1/ph").select("mean_0_20")
    ph_raw = ph_img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=rwanda, scale=30, maxPixels=1e9,
    ).getInfo()
    raw_val = ph_raw.get("mean_0_20")
    if raw_val is not None:
        print(f"  Mean pH over Rwanda (0-20cm), raw={raw_val:.1f}, real={isda_ph(raw_val):.2f}")

    print("\nAll checks complete. If everything above says OK and you got numbers, you're good to build the pipeline.")


if __name__ == "__main__":
    main()
```

#### `src/agritwin/CLAUDE.md`

```markdown
# Pipeline package conventions (src/agritwin)

## Layers and folders

| Layer | Folder | Format | Committed? |
|---|---|---|---|
| raw | `data/raw/sas/{year}/`, `data/raw/ahs/2024/` | .dta / .sav / .csv exactly as downloaded | Never |
| interim | `data/interim/` | Parquet, typed, one file per source file, original column names | Never |
| staging | `data/staging/` | Parquet, harmonized canonical names across years | Never |
| marts | `data/marts/` | Parquet, district x season x crop x year tables | Never |
| external | `data/external/` | GEE CSVs, boundaries, official tables | Boundaries and official tables yes, GEE CSVs yes |
| public | `data/public/` | Parquet + JSON + GeoJSON served by API and web | Yes, after `make check-public` |

## Module responsibilities

- `ingest/`: read raw files with pyreadstat, keep value labels in a sidecar JSON, write interim Parquet. No transformations beyond dtype fixes.
- `harmonize/`: rename source columns to canonical names using `config/sas_variable_map.yaml`, map crop codes with `config/crops.yaml`, convert units, stack years into `stg_sas_plot_crop`.
- `clean/`: yield computation and QC flags. Never drop rows silently. Add a `qc_flag` column and filter explicitly downstream.
- `survey/`: design object, weighted ratio estimator, PSU bootstrap (resample segments within strata, B from settings), Taylor SE via samplics for cross-checks.
- `gee/`: Earth Engine extraction scripts. Each function returns a pandas DataFrame at district x period level and the runner writes CSV to `data/external/gee/`. Never pull pixels locally. Every dataset ID and scale factor comes from `config/data_sources.yaml` and `gee/scaling.py`, confirmed working by `scripts/test_gee.py`; never hardcode a dataset ID or scale factor elsewhere.
- `features/`: build `feat_district_season` (NDVI and rainfall by lead month, soil, terrain) and plot-level driver features.
- `models/`: `attainable.py`, `drivers.py`, `nowcast.py`, `scenario.py`, `evaluation.py`. Every trained artifact is saved to `artifacts/` with a JSON metadata file (data version, features, params, metrics, git hash).
- `export/`: build the aggregated public outputs, simplified GeoJSON and district PDF briefs.

## Canonical staging schema: stg_sas_plot_crop

year, season, district_code, district_name, province_code, stratum, segment_id, farmer_id, farmer_type, plot_id, plot_area_sqm, plot_area_ha, n_main_crops, pure_stand, crop_code_src, crop, harvest_kg, yield_kg_ha, improved_seed, organic_fert, inorganic_fert, pesticide, erosion_degree, anti_erosion, land_consolidation, mechanized, irrigated, sowing_month, weight, qc_flag

Types: codes are Int16 or strings, flags are boolean (null allowed), quantities are Float64.

## Rules

- Every function that estimates a population quantity takes `weight_col`, `strata_col`, `psu_col` arguments with defaults from settings.
- Model validation must be grouped: GroupKFold by district for the driver model, leave-one-year-out for the nowcast. Never random KFold on panel data.
- Any feature derived from the target (for example district historical mean yield) must be computed inside the CV fold from training years only.
- Log row counts at every step (`loguru`). A step that loses more than 2 percent of rows without a qc_flag must raise.
- Tests use synthetic data from `tests/fixtures/synthetic_sas.py`. Never read `data/raw` in tests.
```

#### `src/agritwin/gee/scaling.py`

```python
"""Scale factors and band choices for every Earth Engine dataset AgriTwin uses.

Confirmed by an actual ee.Initialize() + dataset access test on 23 September 2026
(see scripts/test_gee.py). Do not hand-roll these numbers elsewhere; import from
here so a correction only has to happen in one place.

The single most common bug in a pipeline like this is forgetting a scale factor
and silently working with, e.g., MODIS NDVI values in the 0 to 10000 range
instead of -1 to 1. Every extraction function in this module must apply the
matching factor below before returning a DataFrame.
"""

from __future__ import annotations

import math

import ee

# MODIS MOD13Q1: NDVI and EVI stored as int16, scaled by 10000.
MODIS_NDVI_SCALE = 0.0001

# Sentinel-2 SR (harmonized): reflectance bands stored as int, scaled by 10000.
SENTINEL2_SR_SCALE = 0.0001

# CHIRPS daily: already mm/day, no rescale needed.
CHIRPS_SCALE = 1.0

# iSDAsoil back-transforms. Each returns the real-world value from the raw band.
def isda_ph(raw: float) -> float:
    """pH: raw / 10."""
    return raw / 10.0


def isda_nitrogen_total(raw: float) -> float:
    """Total nitrogen, g/kg: exp(raw / 100) - 1."""
    return math.exp(raw / 100.0) - 1.0


def isda_carbon_organic(raw: float) -> float:
    """Organic carbon, g/kg: exp(raw / 10) - 1."""
    return math.exp(raw / 10.0) - 1.0


def scale_modis_ndvi(img: ee.Image) -> ee.Image:
    """Apply the MOD13Q1 scale factor to an NDVI/EVI image."""
    return img.multiply(MODIS_NDVI_SCALE)


def scale_sentinel2_sr(img: ee.Image) -> ee.Image:
    """Apply the Sentinel-2 SR scale factor to reflectance bands."""
    return img.multiply(SENTINEL2_SR_SCALE)


def scale_isda_image_ee(img: ee.Image, formula: str) -> ee.Image:
    """Apply an iSDAsoil back-transform to an ee.Image server-side.

    formula: one of "ph", "nitrogen_total", "carbon_organic".
    """
    if formula == "ph":
        return img.divide(10.0)
    if formula == "nitrogen_total":
        return img.divide(100.0).exp().subtract(1.0)
    if formula == "carbon_organic":
        return img.divide(10.0).exp().subtract(1.0)
    raise ValueError(f"unknown iSDAsoil formula: {formula}")
```

#### `tests/test_gee_scaling.py`

```python
"""Unit tests for confirmed Earth Engine scale factors. No network access, no real ee calls."""

import math

from agritwin.gee.scaling import (
    CHIRPS_SCALE,
    MODIS_NDVI_SCALE,
    SENTINEL2_SR_SCALE,
    isda_carbon_organic,
    isda_nitrogen_total,
    isda_ph,
)


def test_modis_ndvi_scale_brings_raw_into_valid_range():
    raw = 6067.79  # observed raw value, Rwanda cropland, Jan 2024
    scaled = raw * MODIS_NDVI_SCALE
    assert -1.0 <= scaled <= 1.0
    assert round(scaled, 3) == 0.607


def test_sentinel2_sr_scale_is_ten_thousandth():
    assert SENTINEL2_SR_SCALE == 0.0001


def test_chirps_scale_is_identity():
    assert CHIRPS_SCALE == 1.0


def test_isda_ph_back_transform():
    # raw 65 -> pH 6.5, a plausible Rwanda topsoil value
    assert isda_ph(65) == 6.5


def test_isda_nitrogen_back_transform_matches_formula():
    raw = 150.0
    expected = math.exp(raw / 100.0) - 1.0
    assert isda_nitrogen_total(raw) == expected


def test_isda_carbon_back_transform_matches_formula():
    raw = 40.0
    expected = math.exp(raw / 10.0) - 1.0
    assert isda_carbon_organic(raw) == expected
```

#### `web/CLAUDE.md`

```markdown
# Web app conventions (web/)

React 18 + Vite + TypeScript (strict). MapLibre GL JS for maps, ECharts (echarts-for-react) for charts, Tailwind for styling, react-i18next for en/fr/rw, TanStack Query for data, React Router for pages.

## Structure

```
web/
  src/
    main.tsx  App.tsx  routes.tsx
    api/          client.ts (fetch wrapper, API base from VITE_API_BASE, falls back to /static-data), hooks.ts (TanStack Query hooks), types.ts (generated from OpenAPI)
    components/   layout/ map/ charts/ cards/ controls/ common/
    pages/        Home, MapPage, DistrictPage, EarlyEstimatePage, ScenarioPage, MethodologyPage, DataPage, AboutPage
    lib/          format.ts (numbers, kg/ha, percent), scenario.ts (client-side scenario math), colors.ts
    i18n/         index.ts, locales/en.json, fr.json, rw.json
    styles/
  public/static-data/   JSON mirror of the API for offline fallback (generated by make export)
```

## UX rules (Usability and Design is 20 points)

1. Map first. Any question answerable in 3 clicks or fewer: pick crop, pick season, click district.
2. Global filter bar (crop, season, year, language) persists in the URL query string so every view is shareable.
3. Every number shows its interval. Low reliability cells are hatched grey with a tooltip explaining why.
4. Colour: cividis or viridis for sequential scales, a diverging palette for gaps. Never red/green alone.
5. Every chart has a one-sentence "What this shows" caption and a "How to read" tooltip in all three languages.
6. Model outputs carry a visible badge: "Model-based estimate, not official statistics".
7. Mobile first: works at 360 px width, map and panel stack vertically, touch targets at least 44 px.
8. Accessibility: keyboard navigation for all controls, focus rings, aria labels, alt text, contrast AA.
9. Loading states with skeletons, error states with retry, empty states that explain.
10. No text hardcoded in components; everything goes through `t()`.

## Rules

- Types for API responses are generated with `openapi-typescript` from the running API (`npm run gen:types`). Do not hand-write them.
- Scenario math lives in `lib/scenario.ts`, is pure and unit tested with vitest.
- Keep the bundle lean: lazy-load pages, import ECharts modules selectively.
- District geometries are simplified (mapshaper, under 300 KB).
- No external map tiles are required. Default basemap is a plain background with district polygons; an optional light basemap can be toggled.
```
