# Nowcast feature timing: when would `prior_season_yield_kg_ha` actually be available?

Written as part of the external-review Step 2 fix (see `docs/decisions.md` 2026-09-24).
`src/agritwin/models/nowcast.py` uses the prior season's actual district yield as a
model feature. This document checks, per lead time, whether that figure would
realistically have been published by NISR before the nowcast's own prediction date, using
real evidence rather than an assumption.

## Evidence: NISR's publication lag

Pulled directly from the two real SAS reports already fetched for `docs/validation.md`,
using each PDF's own creation timestamp (`pdfinfo`), not a guess:

| Report | Season covered | Data collection ends | Report created |
|---|---|---|---|
| SAS 2025 Season A | Sept 2024 to Feb 2025 | Feb 15, 2025 | **May 30, 2025** |
| SAS 2025 Season B | Mar to Jun 2025 | ~Jun 30, 2025 | **Oct 21, 2025** |

Both independently show roughly the same lag: **NISR publishes a season's SAS report
about 3.5 to 4 months after that season's data collection concludes.**

## Per-lead-time table

**Season A target** (starts September 1; prior season = Season B of the previous year,
which ends ~June 30 and publishes ~mid-October):

| lead_months | prediction date | feature cutoff date | prior season (this fix) | realistically published? |
|---|---|---|---|---|
| 2 | Nov 1 | Nov 1 | Season B, year - 1 | Yes, ~2 weeks margin |
| 3 | Dec 1 | Dec 1 | Season B, year - 1 | Yes, comfortable |
| 4 | Jan 1 | Jan 1 | Season B, year - 1 | Yes, comfortable |

**Season B target** (starts March 1; the immediately preceding season is Season A of the
same year, which ends ~Feb 15 and publishes ~May 30, the exact real date above):

| lead_months | prediction date | feature cutoff date | prior season (this fix) | realistically published? |
|---|---|---|---|---|
| 2 | May 1 | May 1 | Season B, year - 1 (two seasons back) | Yes, ~mid-October, comfortable |
| 3 | Jun 1 | Jun 1 | Season B, year - 1 (two seasons back) | Yes, comfortable |
| 4 | Jul 1 | Jul 1 | Season A, year (one season back) | Yes, ~1 month margin |

Before this fix, Season B at lead=2 and lead=3 used Season A of the same year (one
season back), which would not actually have been published yet: at lead=2 (prediction
date May 1), Season A's report is not out until May 30, a full month later; at lead=3
(prediction date June 1), the margin is 1 to 2 days, not a safe assumption. Both are
fixed now by falling back to the previous year's Season B instead.

## Implementation

`src/agritwin/models/nowcast.py`'s `realistic_lookback_seasons(season, lead_months)`
returns how many seasons back to look; `attach_prior_season_for_lead()` applies it per
lead time (the same district x crop x season x year row uses a different prior-season
source depending on which lead time it is being evaluated at, so this can no longer be
computed once for the whole table the way `last_year_yield_kg_ha` still is).
