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
