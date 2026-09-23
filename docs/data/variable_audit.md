# SAS variable audit

Filled in by the `/audit-sas` skill, one section per year. Do not hand-edit numbers here without re-running the audit; this file is the evidence trail for `config/sas_variable_map.yaml`.

## 2024

Source: NISR catalog record 113, both Season A and Season B production files (`Rwa_raw_SeasonA2024_Production.dta`, `Rwa_raw_SeasonB2024_Production.dta`), read directly with pyreadstat on 2026-09-23. Season A and Season B share the identical instrument: same column names and same labels for every canonical variable, so the mapping below applies to both seasons at high confidence.

Files present in `data/raw/sas/2024/`: Season A and B production, screening, agricultural practice, and fertilizer/pesticide files (8 files total, all `.dta`, all labeled). Only the production files are needed to build `stg_sas_plot_crop`; every canonical column in the `src/agritwin/CLAUDE.md` schema is sourced from production alone.

| Canonical | Source column | Label | Confidence |
|---|---|---|---|
| segment_id | Segment_ID | IDQUEST | high |
| province_code | s1q1 | 1.1 Province | high |
| district_code | s1q2 | 1.2 District name & code | high |
| stratum | s1q3 | 1.3 Stratum | high |
| segment_no | s1q4 | Q1.4 Segment/LSF Number | high |
| farmer_id | s1q6 | 1.6 Farmer ID/LSF ID | high |
| farmer_type | s1q7 | 1.7 Farmer/LSF type | high |
| plot_id | s2q1 | 2.1 Plot No | high |
| plot_area_sqm | s2q2 | 2.2 Plot area (sqm) | high |
| n_main_crops | s2q3 | Q2.3 Number of main crops surveyed this season | high |
| crop_code_src | s2q4 | Q2.4 Crop name (value-labeled numeric code) | high |
| sowing_date | s2q7 | Q2.7 Sowing date | high |
| improved_seed | s2q9 | Q2.9 Did you use improved seed | high |
| harvest_kg_plot | s2q21 | Q2.21 Total quantity of harvest for this season (Kg) | medium, confirm vs s2q22 |
| harvest_kg_crop | s2q22 | Q2.22 Total quantity of harvest for this crop this season (Kg) | medium, confirm vs s2q21 |
| qty_lost_kg | s2q39 | Q2.39 Qty of this crop lost | high |
| organic_fert | s3q3 | 3.3 Used organic fertilizer on this plot | high |
| inorganic_fert | s3q9 | 3.9 Used inorganic fertilizer on this plot | high |
| pesticide | s3q19 | 3.19 Used pesticide/fungicide on this plot | high |
| erosion_degree | s4q1 | 4.1 Degree of erosion on this plot | high |
| anti_erosion | s4q3 | 4.3 Anti-erosion activity on this plot | high |
| land_consolidation | s4q6 | 4.6 Plot in land consolidated site this season | high |
| mechanized | s4q9 | 4.9 Used mechanical equipment on this plot | high |
| irrigated | s4q15 | 4.15 Plot irrigated this season | high |
| interview_date | s5q12 | Q5.12 Date of interview | high |
| weight | plot_weight | plot_weight | high |

**Resolved 2026-09-23** (was open in this section, checked before harmonize implementation): s2q21 ("total quantity of harvest for this season") and s2q22 ("total quantity produced/to be produced by this crop this season") are **not equivalent on pure-stand plots**. Cross-tab on 2024 Season A pure-stand plots (n=4,869 with both non-null): only 36.6% exactly equal, median relative difference 33%, and a heavy right tail (max diff 257,989,208 kg — data entry outlier). The s2q22/s2q21 ratio is systematically >1 (median 1.5x, mean 12.5x, driven by extreme outliers), consistent with s2q22's wording ("produced/**to be** produced") capturing projected or expected total production rather than harvest actually completed. Same pattern confirmed in 2023 and 2025 (33-34% exact match, similar tail). **Decision: canonical `harvest_kg` sources from s2q21 in every year, not s2q22.** s2q21 is also present in all 7 years (2019-2025), while s2q22 as a distinct crop-level column only exists 2023-2025. See `docs/decisions.md`.

Districts present: 30 of 30 in both seasons. Weight (`plot_weight`) summary: Season A min 1.0, max 42,109.3, sum 35,243,844.1 (n=39,330 rows); Season B min 1.0, max 20,947.2, sum 30,534,218.0 (n=35,584 rows). Farmer type is small-scale (individual or cooperative) for 96% of rows in both seasons.

Pure-stand plot counts (`n_main_crops == 1`) for MVP crops, by `s2q4` code:

| Crop | Code(s) | Season A | Season B |
|---|---|---|---|
| Maize | 101 | 1,016 | 259 |
| Sorghum | 103 | 234 | 878 |
| Irish potato | 110 | 372 | 376 |
| Beans (bush + climbing) | 106, 107 | 988 | 1,123 |
| Rice, not MVP | 102 | 216 | 204 |

MVP crop decision: sorghum, not rice, chosen 2026-09-23. Sorghum's Season B sample (878 pure-stand plots) is over 4x rice's (204), giving more reliable district-level attainable-yield percentiles. See `config/crops.yaml` for the source code mapping and reasoning.

Beans decision: canonical `beans` covers source codes 106 (bush bean) and 107 (climbing bean) only, chosen 2026-09-23. Small red bean (130, 1 plot total) and french bean (135, 7 plots per season) are negligible volume and are not folded in.

Missing share for source columns, Season A / Season B: s2q21 and s2q22 12.7% / 2.5% (not filled for plots still growing at survey time), s3q9 37.8% / 50.9%, s3q19 62.6% / 71.8%, s4q9 99.0% / 99.0%, s4q15 92.9% / 87.9%. All other mapped columns under 11% missing in both seasons. High missingness on mechanized (s4q9) and irrigated (s4q15) reflects that most plots use neither; downstream code should treat missing as "no", not drop rows, per the `clean/` qc_flag rule in `src/agritwin/CLAUDE.md`.

## 2019

Source: NISR catalog record 93, all three files for both Season A and Season B (10 files total, `.sav` format). Data is split across three separate instruments:
1. **Production file** (`rwa-sas-seasonA/B_Crop production.sav`): crop codes, harvest, yields, sowing date
2. **Agricultural practice file** (`rwa-sas-SeasonA/B_PartIV_Agricultural practice.sav`): erosion, anti-erosion, mechanization, irrigation, weight
3. **Fertilizers & pesticides file** (`rwa-sas-SeasonA/B_PartIII_Fertilizers_Pesticides.sav`): organic/inorganic fertilizer, pesticide

All three files must be joined on (Segment_ID, s2q1) at the plot level to build `stg_sas_plot_crop`.

| Canonical | Source column | File | Label | Confidence | Notes |
|---|---|---|---|---|---|
| segment_id | Segment_ID | production | IDQUEST | high | |
| province_code | s1q1 | production | 1.1 Province | high | |
| district_code | s1q2 | production | 1.2 District | high | |
| stratum | s1q3 | production | 1.3 Stratum | high | |
| segment_no | s1q4 | production | 1.4 Segment | high | |
| farmer_id | — | none | N/A | high | Not collected in 2019; use null or generate from segment+plot if needed |
| farmer_type | s2q3_1 | production | 2.3.1 Farmer type | high | |
| plot_id | s2q1 | production | 2.1 Plot No. | high | |
| plot_area_sqm | s2q2 | production | 2.2 Area m2 (A) / Plot size (ha) (B) | high | Label inconsistency (m2 vs ha), but actual unit is square meters (confirmed from data range: 500 to 150,000) |
| n_main_crops | s2q5 | production | 2.5 Number of main crops in plot | high | |
| crop_code_src | s2q6 | production | crop_name (value-labeled numeric) | high | Same code mappings as 2024 (101=maize, 103=sorghum, etc.) |
| sowing_date | s2q8 | production | 2.8 Sowing Date | high | |
| improved_seed | — | none | N/A | low | No direct yes/no flag. Could proxy from s2q14_1/2 (improved seed quantity > 0), but this is indirect; marked low confidence pending model card documentation |
| harvest_kg_plot | s2q21 | production | 2.21 Total quantity of harvest in this plot (Kg) | high | Total for all crops on the plot |
| harvest_kg_crop | — | none | N/A | high | Not separate column; for pure-stand plots, harvest_kg_plot equals harvest_kg_crop by definition; use s2q21 directly downstream for pure-stand rows |
| qty_lost_kg | s2q37 | production | 2.37 Quantity lost after harvest | high | |
| organic_fert | s3q1 | fertilizers | 3.1 Used organic fertilizer in this plot | high | |
| inorganic_fert | s3q5 | fertilizers | 3.5 Used inorganic fertilizer in this plot | high | |
| pesticide | s3q13 | fertilizers | 3.13 Used pesticides in this plot | high | |
| erosion_degree | s4q1 | practice | 4.1 Degree of erosion on this plot | high | |
| anti_erosion | s4q2 | practice | 4.2 Anti-erosion activity on this plot | high | |
| land_consolidation | — | none | N/A | high | Not collected in 2019; use null or zero |
| mechanized | s4q10_1, s4q11_1, s4q12_1 | practice | 4.10.1 (oxen), 4.11.1 (tractor), 4.12.1 (other) | high | Three separate binary columns; harmonize by OR-ing to a single binary flag indicating any mechanization |
| irrigated | s4q13 | practice | 4.13 Irrigated plot this season | high | |
| interview_date | s1q5 | production | 1.5 Date of interview | high | |
| weight | weight | practice | Segment weight | high | **Segment-level, not plot-level** (see decisions.md) |

Districts present: 30 of 30 in both seasons. Weight (`weight`, from practice file, segment-level): Season A min 1.0, max 1537.8, sum 9,258,731 (n_unique_segments ~2,800); Season B: (to be computed).

Pure-stand plot counts (`n_main_crops == 1`) for MVP crops, by `s2q6` code:

| Crop | Code(s) | Season A | Season B |
|---|---|---|---|
| Maize | 101 | 1,029 | 228 |
| Sorghum | 103 | 242 | 1,198 |
| Irish potato | 110 | (not shown, < 5) | (not shown) |
| Beans (bush + climbing) | 106, 107 | 1,063 | 1,407 |
| Rice, not MVP | 102 | 241 | 249 |

## 2020

Source: NISR catalog record 99, both Season A and Season B production, practice, and fertilizers/pesticides files (`.dta` format). Structure is **very similar to 2024**: single production file (with plot_weight) plus separate practice and fertilizer files, all joined on plot level. All canonical variables present except interview_date and harvest_kg_crop.

**Key structural changes from 2019:** 2020 returns to plot-level weighting (like 2024), no longer segment-level. Interview date is missing (not collected in 2020 or lost in the data distribution). Unlike 2024, no separate crop-specific harvest column; only plot-level total.

| Canonical | Source column | File | Label | Confidence | Notes |
|---|---|---|---|---|---|
| segment_id | Segment_ID | production | 1.0 Segment identification | high | |
| province_code | s1q1 | production | 1.1 Province | high | |
| district_code | s1q2 | production | 1.2 District name & code | high | |
| stratum | s1q3 | production | 1.3 Stratum | high | |
| segment_no | s1q4 | production | 1.4 Segment | high | |
| farmer_id | s1q6 | production | 1.6 Farmer ID | high | Returned in 2020 after missing from 2019 |
| farmer_type | s1q7 | production | 1.7 Farmer type | high | |
| plot_id | s2q1 | production | 2.1 Plot No | high | |
| plot_area_sqm | s2q2 | production | 2.2 Plot area sqm | high | |
| n_main_crops | s2q3 | production | 2.3 Number of main crops | high | |
| crop_code_src | s2q4 | production | 2.4 Crop name (value-labeled) | high | Same code mappings as 2024 and 2019 |
| sowing_date | s2q7 | production | 2.7 Sowing date | high | |
| improved_seed | s2q9 | production | 2.9 Did you use improved seed | high | Yes/no flag, like 2024 |
| harvest_kg_plot | s2q21 | production | 2.21 Total quantity of harvest for this season (Kg) | high | Plot-level total |
| harvest_kg_crop | — | none | N/A | high | Not separate column; equals s2q21 for pure-stand plots by definition, same as 2019 |
| qty_lost_kg | s2q38 | production | 2.38 On the total production of this crop what is the quantity lost | high | |
| organic_fert | s3q3 | fertilizers | 3.3 Used organic fertilizer in this plot | high | |
| inorganic_fert | s3q9 | fertilizers | 3.9 Used inorganic fertilizer in this plot | high | |
| pesticide | s3q19 | fertilizers | 3.19 Used pesticide/fungicide in this plot | high | |
| erosion_degree | s4q1 | practice | 4.1 Degree of erosion on this plot | high | |
| anti_erosion | s4q3 | practice | 4.3 Anti-erosion activity on this plot | high | |
| land_consolidation | s3q25 | practice | 3.25 Does this plot belong to consolidated site | high | New question in 2020 (not in 2019); direct binary flag |
| mechanized | s4q8_1, s4q9_1, s4q10_1 | practice | 4.8.1 (oxen), 4.9.1 (tractor), 4.10.1 (other) | high | Three separate binary columns; must OR to single flag |
| irrigated | s4q13 | practice | 4.13 Plot irrigated this season | high | |
| interview_date | — | none | N/A | high | Not collected or not present in distributed data; no interview date column found in any 2020 file |
| weight | Plot_weight | production, practice, fertilizers | Plot weight | high | **Plot-level** (not segment-level like 2019) — min 1.0, max 23,247.8, sum 26,058,302 (Season B) |

Districts present: 30 of 30 in both seasons. Pure-stand plot counts (`n_main_crops == 1`):

| Crop | Code(s) | Season A | Season B |
|---|---|---|---|
| Maize | 101 | 1,054 | 356 |
| Sorghum | 103 | 179 | 1,225 |
| Irish potato | 110 | 383 | 360 |
| Beans (bush + climbing) | 106, 107 | 1,055 | 1,210 |
| Rice, not MVP | 102 | 125 | 191 |

## 2021

Source: NISR catalog record 102, both Season A and Season B production, practice, and fertilizers/pesticides files (`.dta` format). Structure is **identical to 2020**: single production file + practice + fertilizer files, joined on plot level. All canonical variables present except interview_date.

**Differences from 2020:** Minor. Two weight columns present (`plot_weight` with generic label, `finalplot_weight` with explicit label "Plot weight"). Use `finalplot_weight`. s5q13 appears in production file (COVID-19 impacts on agriculture, not interview date). 70 columns in production vs 2020's 66.

| Canonical | Source column | File | Label | Confidence | Notes |
|---|---|---|---|---|---|
| segment_id | Segment_ID | production | Segment Identification | high | |
| province_code | s1q1 | production | 1.1 Province | high | |
| district_code | s1q2 | production | 1.2 District name & code | high | |
| stratum | s1q3 | production | 1.3 Stratum | high | |
| segment_no | s1q4 | production | 1.4 Segment | high | |
| farmer_id | s1q6 | production | 1.6 Farmer ID | high | |
| farmer_type | s1q7 | production | 1.7 Farmer type | high | |
| plot_id | s2q1 | production | 2.1 Plot number | high | |
| plot_area_sqm | s2q2 | production | 2.2 Plot area in sqm | high | |
| n_main_crops | s2q3 | production | 2.3 Number of main crops | high | |
| crop_code_src | s2q4 | production | 2.4 Crop name (value-labeled) | high | Same code mappings as prior years |
| sowing_date | s2q7 | production | 2.7 Sowing date | high | |
| improved_seed | s2q9 | production | 2.9 Did you use improved seed | high | |
| harvest_kg_plot | s2q21 | production | 2.21 Total quantity of harvest for this season (Kg) | high | |
| harvest_kg_crop | — | none | N/A | high | Not separate column; use s2q21 for pure-stand |
| qty_lost_kg | s2q38 | production | 2.38 Quantity lost after harvest | high | |
| organic_fert | s3q3 | fertilizers | 3.3 Used organic fertilizer in this plot | high | |
| inorganic_fert | s3q9 | fertilizers | 3.9 Used inorganic fertilizer in this plot | high | |
| pesticide | s3q19 | fertilizers | 3.19 Used pesticide/fungicide in this plot | high | |
| erosion_degree | s4q1 | practice | 4.1 Degree of erosion on this plot | high | |
| anti_erosion | s4q3 | practice | 4.3 Anti-erosion activity on this plot | high | |
| land_consolidation | s3q25 | practice | 3.25 Does this plot belong to consolidated site | high | |
| mechanized | s4q8_1, s4q9_1, s4q10_1 | practice | 4.8.1 (oxen), 4.9.1 (tractor), 4.10.1 (other) | high | Three separate; OR to binary |
| irrigated | s4q13 | practice | 4.13 Plot irrigated this season | high | |
| interview_date | — | none | N/A | high | Not collected in 2021 (s5q13 is COVID-19 impacts) |
| weight | finalplot_weight | production | Plot weight | high | **Plot-level** (verified: 76.9% of segments show weight variation across plots) — min 1.0, max 24,895.5 (Season B), sum 25,113,833 (Season B). Two weight columns; use finalplot_weight. |

Districts present: 30 of 30 in both seasons. **Design structure: individually verified as plot-level (76.9% segment weight variation, consistent with 2020–2025 block).** Pure-stand plot counts (`n_main_crops == 1`):

| Crop | Code(s) | Season A | Season B |
|---|---|---|---|
| Maize | 101 | 1,013 | 310 |
| Sorghum | 103 | 176 | 1,078 |
| Irish potato | 110 | 308 | 539 |
| Beans (bush + climbing) | 106, 107 | 1,151 | 1,666 |
| Rice, not MVP | 102 | 188 | 201 |

## 2022

Source: NISR catalog record 103, both Season A and Season B production, practice, and fertilizers/pesticides files (`.dta` format). Structure is same as 2020–2021: production + practice + fertilizers joined on plot level. All canonical variables present except interview_date.

**Differences from 2021:**
- Production file expanded to 101 columns (vs 70 in 2021): detailed capture of harvest disposition (ratios for consumed, sold, fed, stored, lost, etc., plus a new "aweight" column with unlabeled purpose).
- Practice file structure changed: land_consolidation moved from `s3q25` (2021) to `s4q6` (2022). Other practice variables remain in same positions.
- Weight is `plot_weight` (not `finalplot_weight` like 2021), but same plot-level design.

| Canonical | Source column | File | Label | Confidence | Notes |
|---|---|---|---|---|---|
| segment_id | Segment_ID | production | Segment Identification | high | |
| province_code | s1q1 | production | 1.1 Province | high | |
| district_code | s1q2 | production | 1.2 District name & code | high | |
| stratum | s1q3 | production | 1.3 Stratum | high | |
| segment_no | s1q4 | production | 1.4 Segment | high | |
| farmer_id | s1q6 | production | 1.6 Farmer ID | high | |
| farmer_type | s1q7 | production | 1.7 Farmer type | high | |
| plot_id | s2q1 | production | 2.1 Plot number | high | |
| plot_area_sqm | s2q2 | production | 2.2 Plot area in sqm | high | |
| n_main_crops | s2q3 | production | 2.3 Number of main crops | high | |
| crop_code_src | s2q4 | production | 2.4 Crop name (value-labeled) | high | Same code mappings as prior years |
| sowing_date | s2q7 | production | 2.7 Sowing date | high | |
| improved_seed | s2q9 | production | 2.9 Did you use improved seed | high | |
| harvest_kg_plot | s2q21 | production | 2.21 Total quantity of harvest for this season (Kg) | high | |
| harvest_kg_crop | — | none | N/A | high | Not separate column; use s2q21 for pure-stand |
| qty_lost_kg | s2q38 | production | 2.38 Quantity lost after harvest | high | |
| organic_fert | s3q3 | fertilizers | 3.3 Used organic fertilizer in this plot | high | |
| inorganic_fert | s3q9 | fertilizers | 3.9 Used inorganic fertilizer in this plot | high | |
| pesticide | s3q19 | fertilizers | 3.19 Used pesticide/fungicide in this plot | high | |
| erosion_degree | s4q1 | practice | 4.1 Degree of erosion on this plot | high | |
| anti_erosion | s4q3 | practice | 4.3 Anti-erosion activity on this plot | high | |
| land_consolidation | s4q6 | practice | 4.6 Is this plot in land consolidated site | high | **Moved from s3q25 (2021) to s4q6 (2022)** |
| mechanized | s4q10_1, s4q11_1, s4q12_1 | practice | 4.10.1 (oxen), 4.11.1 (tractor), 4.12.1 (other) | high | Three separate; OR to binary |
| irrigated | s4q15 | practice | 4.15 Plot irrigated this season | high | |
| interview_date | — | none | N/A | high | Not collected in 2022 |
| weight | plot_weight | production | plot_weight | high | **Plot-level** (verified: 76.0% of segments show weight variation across plots) — min 1.0, max 42,795.4 (Season A), sum 34,993,486 (Season A) |

Districts present: 30 of 30 in both seasons. **Design structure: individually verified as plot-level (76.0% segment weight variation, consistent with 2020–2025 block).** Pure-stand plot counts (`n_main_crops == 1`):

| Crop | Code(s) | Season A | Season B |
|---|---|---|---|
| Maize | 101 | 746 | 264 |
| Sorghum | 103 | 262 | 927 |
| Irish potato | 110 | 374 | 458 |
| Beans (bush + climbing) | 106, 107 | 832 | 1,007 |
| Rice, not MVP | 102 | 150 | 167 |

## 2023

Source: NISR catalog record 106, both Season A and Season B production, practice, and fertilizers/pesticides files (`.dta` format). Structure is **identical to 2022**: production + practice + fertilizers joined on plot level. All canonical variables present except interview_date.

No differences from 2022: land_consolidation remains at `s4q6` (2022 position), weight is `plot_weight` (plot-level), production file same 103 columns.

| Canonical | Source column | File | Label | Confidence | Notes |
|---|---|---|---|---|---|
| segment_id | Segment_ID | production | Segment Identification | high | |
| province_code | s1q1 | production | 1.1 Province | high | |
| district_code | s1q2 | production | 1.2 District name & code | high | |
| stratum | s1q3 | production | 1.3 Stratum | high | |
| segment_no | s1q4 | production | 1.4 Segment | high | |
| farmer_id | s1q6 | production | 1.6 Farmer ID | high | |
| farmer_type | s1q7 | production | 1.7 Farmer type | high | |
| plot_id | s2q1 | production | 2.1 Plot number | high | |
| plot_area_sqm | s2q2 | production | 2.2 Plot area in sqm | high | |
| n_main_crops | s2q3 | production | 2.3 Number of main crops | high | |
| crop_code_src | s2q4 | production | 2.4 Crop name (value-labeled) | high | Same code mappings as prior years |
| sowing_date | s2q7 | production | 2.7 Sowing date | high | |
| improved_seed | s2q9 | production | 2.9 Did you use improved seed | high | |
| harvest_kg_plot | s2q21 | production | 2.21 Total quantity of harvest for this season (Kg) | high | |
| harvest_kg_crop | s2q22 | production | 2.22 Quantity produced by this crop this season (Kg) | high | Separate crop column (new in 2024+); use for pure-stand plots |
| qty_lost_kg | s2q39 | production | 2.39 What was the quantity lost | high | |
| organic_fert | s3q3 | production | 3.3 Used organic fertilizer in this plot | high | |
| inorganic_fert | s3q9 | production | 3.9 Used inorganic fertilizer in this plot | high | |
| pesticide | s3q19 | production | 3.19 Used pesticide/fungicide in this plot | high | |
| erosion_degree | s4q1 | production | 4.1 Degree of erosion on this plot | high | |
| anti_erosion | s4q3 | production | 4.3 Anti-erosion activity on this plot | high | |
| land_consolidation | s4q6 | practice | 4.6 Is this plot in land consolidated site | high | |
| mechanized | s4q10_1, s4q11_1, s4q12_1 | practice | 4.10.1 (oxen), 4.11.1 (tractor), 4.12.1 (other) | high | Three separate; OR to binary |
| irrigated | s4q15 | production | 4.15 Plot irrigated this season | high | |
| interview_date | — | none | N/A | high | Not collected in 2023 |
| weight | plot_weight | production | plot_weight | high | **Plot-level** (verified: 76.4% of segments show weight variation across plots) — min 1.0, max 20,956.5 (Season A), sum 31,499,395 (Season A) |

Districts present: 30 of 30 in both seasons. **Design structure: individually verified as plot-level (76.4% segment weight variation, consistent with 2020–2025 block).** Pure-stand plot counts (`n_main_crops == 1`):

| Crop | Code(s) | Season A | Season B |
|---|---|---|---|
| Maize | 101 | 1,035 | 357 |
| Sorghum | 103 | 227 | 1,062 |
| Irish potato | 110 | 344 | 462 |
| Beans (bush + climbing) | 106, 107 | 960 | 1,367 |
| Rice, not MVP | 102 | 169 | 166 |

## 2025

Source: NISR catalog record 124, both Season A and Season B production, practice, and fertilizers/pesticides files (`.dta` format). Structure is very similar to 2024 with one notable questionnaire change.

**Differences from 2024:** qty_lost_kg questionnaire structure changed. Instead of a single total loss column (s2q39 in 2024), 2025 uses itemized loss tracking across ten categories (s2q41–s2q50: stolen, insects, animals, stalks, harvesting, transport, storage, processing, packaging, sales). All other canonical variables present and in same positions as 2024.

| Canonical | Source column | File | Label | Confidence | Notes |
|---|---|---|---|---|---|
| segment_id | Segment_ID | production | SEGMENT ID/LSF ID | high | |
| province_code | s1q1 | production | 1.1 Province | high | |
| district_code | s1q2 | production | 1.2 District | high | |
| stratum | s1q3 | production | 1.3 Stratum | high | |
| segment_no | s1q4 | production | 1.4 Segment/LSF ID | high | |
| farmer_id | s1q6 | production | 1.6 Farmer ID/LSF ID | high | |
| farmer_type | s1q7 | production | 1.7 Farmer/LSF type | high | |
| plot_id | s2q1 | production | Q2.1. Plot number | high | |
| plot_area_sqm | s2q2 | production | 2.2 Plot area(sqm) | high | |
| n_main_crops | s2q3 | production | 2.3 Number of main crops | high | |
| crop_code_src | s2q4 | production | 2.4 Crop name (value-labeled) | high | Same code mappings as prior years |
| sowing_date | s2q7 | production | 2.7 Sowing date | high | |
| improved_seed | s2q9 | production | 2.9 Did you use improved seed | high | |
| harvest_kg_plot | s2q21 | production | 2.21 Total quantity of harvest for this season (Kg) | high | |
| harvest_kg_crop | s2q22 | production | 2.23 Total quantity produced by this crop this season (Kg) | high | Separate crop column; use for pure-stand plots |
| qty_lost_kg | — | none | N/A | high | **Questionnaire structure changed.** 2025 removed single-column total loss (s2q39 in 2024); now uses itemized losses (s2q41–s2q50). Mapped to null; no downstream consumer. |
| organic_fert | s3q3 | fertilizers | 3.3 Used organic fertilizer in this plot | high | |
| inorganic_fert | s3q9 | fertilizers | 3.9 Used inorganic fertilizer in this plot | high | |
| pesticide | s3q19 | fertilizers | 3.19 Used pesticide/fungicide in this plot | high | |
| erosion_degree | s4q1 | practice | 4.1 Degree of erosion on this plot | high | |
| anti_erosion | s4q3 | practice | 4.3 Anti-erosion activity on this plot | high | |
| land_consolidation | s4q6 | practice | 4.6 Is this plot in land consolidated site | high | |
| mechanized | s4q10_1, s4q11_1, s4q12_1 | practice | 4.10.1 (oxen), 4.11.1 (tractor), 4.12.1 (other) | high | Three separate; OR to binary |
| irrigated | s4q14 | practice | 4.14 Has this plot been irrigated this season | high | |
| interview_date | — | none | N/A | high | Not collected in 2025 |
| weight | plot_weight | production | plot_weight | high | **Plot-level** — min 1.0, max 23,754.1 (Season A), sum 36,857,604 (Season A) |

Districts present: 30 of 30 in both seasons. Pure-stand plot counts (`n_main_crops == 1`):

| Crop | Code(s) | Season A | Season B |
|---|---|---|---|
| Maize | 101 | 1,086 | 307 |
| Sorghum | 103 | 290 | 948 |
| Irish potato | 110 | 384 | 536 |
| Beans (bush + climbing) | 106, 107 | 1,320 | 2,280 |
| Rice, not MVP | 102 | 199 | 197 |

**Derived field (unverified):** `qty_lost_kg_itemized_sum` = sum(s2q41:s2q50) across all ten loss categories (stolen, insects, animals, stalks, harvesting, transport, storage, processing, packaging, sales). **Mutual exclusivity across categories has not been validated.** This field is documented for future reference only; not wired into config/sas_variable_map.yaml or any pipeline step. Before implementing, harmonize module should verify (1) whether the ten categories are truly mutually exclusive or can overlap, and (2) whether this sum equals s2q39 (total loss) in years where both are present (2024, 2023, 2022, etc.) to validate the mapping strategy.
