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

## 2025

Not yet audited. Data dictionary lists 101 unlabeled variables (V1 to V100 plus one more) for the Season B production file. Run `/audit-sas 2025` after downloading the file.

## 2019 to 2023

Not yet audited. Run `/audit-sas <year>` for each.
