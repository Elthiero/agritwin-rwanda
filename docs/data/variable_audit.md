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

Open question (unresolved): s2q21 ("total quantity of harvest for this season") vs s2q22 ("for this crop this season") on a pure-stand plot should be equal; confirm with a cross-tab before using either as the yield numerator.

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

## 2025

Not yet audited. Data dictionary lists 101 unlabeled variables (V1 to V100 plus one more) for the Season B production file. Run `/audit-sas 2025` after downloading the file.

## 2021-2023

Not yet audited. Run `/audit-sas <year>` for each.
