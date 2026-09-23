# Survey design variables

Documents the weight, stratum, and PSU/segment variables for all 7 SAS years (2019-2025),
Seasons A and B, as inputs to `src/agritwin/survey/`. Everything below was confirmed by
reading value labels and row-level frequencies directly from the raw `.dta`/`.sav` files
(metadata-only where possible) and from `data/staging/stg_sas_plot_crop.parquet`, not
assumed from prior years' pattern. See `docs/decisions.md` for the two structural design
decisions already logged (2019 segment-level weighting; harvest_kg source).

## Weight

| Year | Source column | Level | Notes |
|---|---|---|---|
| 2019 | `weight` (practice file) | segment | Constant per segment (1.6% of segments vary, see `docs/decisions.md` 2026-09-23). |
| 2020 | `Plot_weight` (production) | plot | First plot-level weighting year. |
| 2021 | `finalplot_weight` (production) | plot | **2021 has two weight columns** (`plot_weight` and `finalplot_weight`); `config/sas_variable_map.yaml` already documents the decision to use `finalplot_weight`. Not re-litigated here; carried forward as-is. `weight` is null for 163/77,503 rows (0.2%) in 2021, higher than other years — noted, not yet explained. |
| 2022 | `plot_weight` (production) | plot | Back to `plot_weight` after 2021's `finalplot_weight`. |
| 2023 | `plot_weight` (production) | plot | |
| 2024 | `plot_weight` (production) | plot | |
| 2025 | `plot_weight` (production) | plot | |

## PSU (primary sampling unit)

`segment_id` (`Segment_ID`), combined with `year`: segment numbering is not a stable
identifier of the same physical location across years (segment counts grow from 955 in
2019 to ~1,500-1,580 in 2020-2025, i.e. the frame was redrawn, most likely at the
2020 transition to plot-level weighting). Within a year, a segment never spans more than
one district (checked all 7 years, 0 exceptions), and roughly 95% of segments appear in
both Season A and Season B of the same year (checked 2024: 1,474/1,545 A-segments also in
B), consistent with a segment being sampled once per year and visited both seasons. PSU key
for the design object: `(year, segment_id)`.

## Strata

`stratum` (`s1q3`), 4-6 categories per year. **This variable's codes are not stable across
years** — more than a simple relabeling in one case (see Open questions below). Categories
actually present in the data (frequencies from `stg_sas_plot_crop`, not just the label
dictionary, since several years carry unused label entries with zero rows):

| Year | Codes present (row counts) |
|---|---|
| 2019 | 11=hillside (50,017), 20=marshland (7,090), 30=rangeland (4,055), 50=LSF (2,237). **No code 40** despite later years using 40 for a general/mixed stratum — 2019 appears to use a 4-category scheme, not 5. |
| 2020 | 0=LSF (2,571), 10=hillside (64,337), 20=marshland (2,890), 30=rangeland (678), 40=mixed (6,610) |
| 2021 | 0=LSF (2,778), 10=hillside (34,641, **Season A only**), 11=unlabeled (29,912, **Season B only**), 20=marshland (2,858), 30=rangeland (714), 40=mixed (6,600) |
| 2022 | 0=LSF (2,748), 10=hillside (64,824), 20=marshland (2,834), 30=rangeland (742), 40=mixed (6,446) |
| 2023 | 0=LSF (2,437), 10=hillside (63,195), 20=marshland (2,814), 30=rangeland (837), 40=mixed (6,301) |
| 2024 | 10=hillside (61,706), 20=marshland (2,766), 30=rangeland (596), 40=mixed (6,862), 90=LSF (2,984). Code 0's "LSF" label exists in the file's metadata but **has zero rows** in 2024 — vestigial, not a live ambiguity. |
| 2025 | 10=hillside (55,085), 20=marshland (2,285), 30=rangeland (644), 40=mixed (6,284), 90=LSF (2,991). Code 50's "Site" label exists in metadata but **has zero rows** — same vestigial pattern as 2024's code 0. |

### Open question, resolved with evidence (not left blocking)

**2021 stratum code 11 is unlabeled in the raw file's metadata.** Checked whether it is a
genuinely new stratum category or a mid-year recoding of "hillside" (already code 10 in
every other year): code 10 appears in 2021 **only** in Season A (34,641 rows, 0 in Season
B) and code 11 appears **only** in Season B (29,912 rows, 0 in Season A), with near-identical
relative shares across all 30 districts (checked full cross-tab). Their combined total
(64,553) matches the single-code totals other years show for hillside alone (61,706-64,824).
This is strong circumstantial evidence that 2021 recoded "hillside" from 10 to 11 partway
through the year, not that a new physical stratum was introduced. **Treated as equivalent to
code 10 for stratification purposes**, but flagged here explicitly since the raw file's own
metadata never labels code 11 and no questionnaire PDF is available in this repo
(`docs/data/questionnaires/` is empty) to independently confirm it.

**2019's missing code 40** and the general year-to-year code churn (LSF stratum moves
50 -> 0 -> 0/90 -> 90) means the *codes* are not a safe join key across years; only a
canonical stratum label (`hillside`, `marshland`, `rangeland`, `mixed`, `lsf`) is. This is
handled in `src/agritwin/survey/core.py` by mapping each year's codes to a fixed 5-category
canonical stratum before any design object is built, never joining on raw codes across years.

## Design blocks for estimation

Per `docs/decisions.md` 2026-09-23 ("2019 segment-level vs 2020+ plot-level weighting
requires stratified design"): **2019 is one design block (segment-level weight), 2020-2025
is a second design block (plot-level weight)**. `src/agritwin/survey/` computes each block's
weighted estimates and PSU-based variance independently; it does not pool 2019 with
2020-2025 into a single variance calculation.

## Scope restriction forced by harmonize's own output, not a preference

`stg_sas_plot_crop.harvest_kg` is **plot-level total harvest** (sourced from s2q21, per
`docs/decisions.md` 2026-09-23), not a per-crop figure. For an intercropped plot
(`pure_stand == False`), there is no valid way to attribute a share of `harvest_kg` to one
specific crop using data currently in `stg_sas_plot_crop` — s2q22 (`harvest_kg_crop`, the
only per-crop production question that exists in some years) was explicitly rejected as a
harvest_kg source because it captures projected/expected production, not actual harvest
(same decisions.md entry). **`src/agritwin/survey/`'s crop x district x season x year
production and yield estimates are therefore restricted to pure-stand, small-scale-farmer
plots**, consistent with the canonical yield definition already in `src/agritwin/CLAUDE.md`.
This is a hard data constraint inherited from harmonize's design, not a new methodological
choice made in survey/.
