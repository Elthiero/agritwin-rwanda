# AgriTwin Rwanda

**Yield gap and early harvest estimator for Rwanda.**

Built for the [NISR 2026 Big Data Hackathon](https://statistics.gov.rw/about/hackathon/2026-hackathon-competition), Track 1 (Agricultural Productivity).

- Live app: `<deployed web URL>`
- API docs: `<deployed API URL>/docs`
- Demo video: `<YouTube unlisted link>`
- Documentation site: `<MkDocs GitHub Pages URL>`

---

## Background

Rwanda's agriculture sector is dominated by smallholder farmers, and productivity varies widely between districts and even between farmers in the same district. The National Institute of Statistics of Rwanda (NISR) runs the Seasonal Agricultural Survey (SAS) every year to measure land use, crop area, inputs, and production, but the results are published only after each season ends, once the survey has been fully processed.

That timing gap matters. Planners at MINAGRI, RAB, and district agriculture offices need to know where yields are underperforming and what this season's harvest is likely to look like *before* the official numbers arrive, not months after, when the window for a mid-season response has already closed.

This project is our entry for NISR's 2026 hackathon, aligned with Rwanda's NST2 priorities and Vision 2050 goals around agricultural productivity, commercialization, and climate resilience.

## Problem

Three related gaps show up in how agricultural data currently gets used in Rwanda:

1. **No systematic view of the yield gap.** National and district averages exist, but there is no tool that shows, per crop and district, how far actual yields fall below what similar farmers under similar conditions are already achieving.
2. **No explanation of what drives the gap.** Even where a gap is visible, it is not clear which factors, improved seed, fertilizer use, irrigation, erosion control, extension access, are most strongly associated with it in a given district.
3. **No early signal before the survey is published.** SAS results are only available after the season ends. Between rounds, there is no data-driven way to anticipate how a season is unfolding.

## Solution

AgriTwin combines NISR's Seasonal Agricultural Survey microdata with satellite and climate data to give planners, agronomists, and extension workers a single tool with three linked capabilities:

1. **Yield gap engine.** Estimates attainable yield (the top-performing farmers under comparable agro-ecological conditions) and shows the gap for each crop, district, and season, with a confidence interval.
2. **Driver engine.** Uses an explainable model (LightGBM + SHAP) to show which factors, improved seed, fertilizer, irrigation, erosion control, plot size, rainfall, soil, are most associated with higher yield in each district. Presented as association, never as a causal claim.
3. **Early estimate engine (nowcast).** Combines satellite vegetation signals (NDVI) and rainfall data during the growing season to produce a district-level yield estimate before the official SAS results are published, validated against a historical backtest.
4. **Scenario explorer.** Lets a user ask "what would happen to the model's yield estimate if improved seed adoption in this district rose from X% to Y%", clearly labeled as a model-based estimate rather than a policy guarantee.

Every number shown in the app carries a confidence interval or an explicit reliability flag. Nothing below district level is ever shown, and no individual farmer or plot data leaves the pipeline.

## Tech stack

| Layer | Technology |
|---|---|
| Data processing | Python 3.12, polars/pandas, pyreadstat, DuckDB, GeoPandas |
| Satellite and climate data | Google Earth Engine (MODIS NDVI, Sentinel-2, CHIRPS, ESA WorldCover, iSDAsoil, SRTM) |
| Modelling | scikit-learn, LightGBM, SHAP, samplics (survey-weighted estimation) |
| API | FastAPI, Pydantic, serving precomputed Parquet/JSON, no live database |
| Web app | React 18, Vite, TypeScript, MapLibre GL JS, ECharts, Tailwind CSS, react-i18next (English, French, Kinyarwanda) |
| Documentation | MkDocs Material, deployed to GitHub Pages |
| Containerization | Docker, Docker Compose |

## Data sources

- **NISR microdata:** Seasonal Agricultural Survey (SAS) 2019 to 2025, Agriculture Household Survey (AHS) 2024. Raw microdata is never included in this repository; see [`docs/data/README.md`](docs/data/README.md) for how to request it from NISR and reproduce the processed outputs.
- **Open satellite and climate data:** MODIS NDVI, Sentinel-2 surface reflectance, CHIRPS rainfall, ESA WorldCover, iSDAsoil, and SRTM elevation, all accessed through Google Earth Engine at no cost for noncommercial academic use.

Full source list, dataset IDs, and licensing notes are in [`docs/data/README.md`](docs/data/README.md).

## Installation

### Prerequisites

- Python 3.12 or later
- Node.js 20 or later (for the web app, from Week 2 onward)
- A Google Earth Engine account with a registered noncommercial project ([register here](https://code.earthengine.google.com/register))
- A NISR microdata account ([register here](https://microdata.statistics.gov.rw)), if you plan to run the data pipeline yourself
- Docker and Docker Compose (optional, for containerized deployment)

### Get the code

```bash
git clone https://github.com/Elthiero/agritwin-rwanda.git
cd agritwin-rwanda
```

### Set up the Python environment

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt -r requirements-dev.txt
pip install -e .                  # makes the agritwin package importable
```

### Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set `GEE_PROJECT_ID` to your own Earth Engine project ID. Then authenticate once per machine:

```bash
earthengine authenticate
```

Confirm everything is working:

```bash
python scripts/test_gee.py
```

### Get the data

Raw NISR microdata is not included in this repository and cannot be redistributed. Follow [`docs/data/README.md`](docs/data/README.md) to request access and download the files, then place them at:

```
data/raw/sas/{year}/
data/raw/ahs/2024/
```

### Run the pipeline

```bash
make ingest stage marts    # process NISR microdata
make gee                   # pull satellite and climate features
make features train        # build model features and train models
make export                # produce the aggregated, public-safe outputs
```

### Run the app locally

```bash
make api     # FastAPI on http://localhost:8000, docs at /docs
```

For the web app, once it has been scaffolded (see `web/` after Week 2 of development):

```bash
cd web
npm install
npm run dev  # http://localhost:5173
```

### Or run everything with Docker

```bash
docker compose up --build
```

This starts the API and web app together, reading from `data/public/`.

## Methodology and validation

Every population-level estimate uses the SAS survey weights and design (strata and primary sampling units), never a simple average. Model outputs are always shown as associations or predictions, never as causal claims. Yield gap and driver models are validated with district-grouped cross-validation; the seasonal nowcast is validated with a leave-one-year-out backtest against naive baselines. Full methodology, validation results, and known limitations are documented on the project's methodology page and in `docs/`.

## Data privacy

No individual farmer, plot, or household-level data is ever published, committed to this repository, or served by the API. All outputs are aggregated to district level or coarser, and any estimate based on fewer than the minimum sample size is flagged as low-reliability rather than suppressed silently. See `docs/data/README.md` for details.

## AI use disclosure

AI assistants were used during development, as permitted under the NISR hackathon rules. Full disclosure is in [`AI_DISCLOSURE.md`](AI_DISCLOSURE.md).

## Originality

This is original work produced for the NISR 2026 Big Data Hackathon and has not been submitted to any other competition. See [`ORIGINALITY.md`](ORIGINALITY.md).

## License and intellectual property

Per the NISR 2026 Big Data Hackathon rules, all intellectual property in this submission, including copyright and any patent rights, transfers to NISR, who may use, modify, publish, and distribute the work for any purpose. See `LICENSE` and `NOTICE` for details.

## Team

- **Ahourdet Donambi Thierry**: data engineering, modelling, API, deployment (thierrydonambi@gmail.com)
- **Ishimwe Aime Cesar**: survey methodology, validation, Kinyarwanda translation, domain research (ishimweaimecesar5@gmail.com)

## Contact

Questions about this project: `thierrydonambi@gmail.com`
Questions about the hackathon: Prosper Ayinebyona, prosper.ayinebyona@statistics.gov.rw
