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
