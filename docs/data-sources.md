# External (non-NISR-microdata) data sources

This file logs sources for reference/crosswalk data that are not part of the NISR SAS/AHS
microdata catalog (that list lives in `config/data_sources.yaml`) and not part of the GEE
satellite catalog (also in `config/data_sources.yaml`). Right now it covers one thing: the
admin-2 (district) boundary and P-code source used to build `data/reference/district_crosswalk.csv`.

## Rwanda admin boundaries (COD-AB) — HDX

- **Source:** UN OCHA Common Operational Datasets - Administrative Boundaries (COD-AB), Rwanda.
- **Dataset page:** `https://data.humdata.org/dataset/cod-ab-rwa`
- **Resource downloaded:** `rwa_adm_2006_NISR_WGS1984_20181002_SHP.zip`
  (direct URL: `https://data.humdata.org/dataset/2768bdfd-6486-4963-8e3d-e63149478eb4/resource/176eaace-708c-46b3-94e9-d5ba91cca08c/download/rwa_adm_2006_nisr_wgs1984_20181002_shp.zip`)
- **Download date:** 2026-09-23
- **Original source per HDX metadata:** National Institute of Statistics of Rwanda (NISR), vetted by
  ITOS (USAID-funded), last modified 2022-06-09.
- **License:** Creative Commons Attribution for Intergovernmental Organisations (CC BY-IGO).
- **Contents used:** admin level 2 (district) layer only, `rwa_adm2_2006_NISR_WGS1984_20181002.shp`,
  30 features. Fields used: `ADM1_EN` (province), `ADM2_EN` (district name), `ADM2_PCODE`
  (P-code, e.g. `RW11`).
- **Not committed to git:** the downloaded shapefile bundle (15.5 MB) is kept out of the repo per
  `CLAUDE.md` golden rule 1's general policy of not committing bulky external geodata by default.
  A simplified GeoJSON derived from it is committed at `data/public/geo/districts_adm2.geojson`
  (see below) since it is well under the 5 MB threshold.
- **How it was used:** joined against NISR SAS `district_code` value labels (from the raw `.dta`/
  `.sav` files, read via `pyreadstat` metadata-only mode, never against any committed microdata) to
  build `data/reference/district_crosswalk.csv`. See `docs/decisions.md` 2026-09-23 for the join
  method and the one spelling variant found (2025 SAS district_code 11 is labeled "Nyarugenege",
  a typo for "Nyarugenge").

### Simplified public GeoJSON

`data/public/geo/districts_adm2.geojson` is the HDX ADM2 layer, simplified (Douglas-Peucker,
tolerance matching `config/settings.yaml`'s `export.simplify_tolerance_m: 150`) and reprojected to
WGS84 (already WGS84 in the source), with only `nisr_district_code`, `district_name`, `province`,
`hdx_pcode` kept as properties (no other HDX metadata fields). File size: see the file itself; it
was only committed because it measured under 5 MB.

## FAO GAUL districts (existing, for comparison)

`config/data_sources.yaml`'s `gee.datasets.gaul_districts` entry (`FAO/GAUL/2015/level2`, accessed
via Earth Engine) remains the boundary source `src/agritwin/gee/boundaries.py`'s original
`rwanda_districts_fc()` function uses, and its `gaul_district_code` values are what the existing
`data/external/gee/*.csv` outputs are keyed on. The crosswalk above includes GAUL's `ADM2_CODE` as
`gaul_code`, matched by exact `district_name` string equality (verified: all 30 GAUL district names
match the HDX/NISR names exactly, no reconciliation needed on that side). GAUL and HDX are two
different boundary products for the same 30 districts; both are retained rather than one replacing
the other, since existing GEE outputs are keyed to GAUL and re-extracting historical satellite data
against a new polygon source is out of scope for this change (see `docs/decisions.md`).
