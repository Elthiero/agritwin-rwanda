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
