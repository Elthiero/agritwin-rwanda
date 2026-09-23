"""Validates survey/'s national maize estimate against a real, published NISR figure.

Unlike the rest of the test suite, this test reads data/marts/district_yield.parquet (not
data/raw) because there is no synthetic substitute for "does our pipeline reproduce a real
published number": the comparison is only meaningful against the actual output of a real
`make stage clean marts` run on real microdata. data/marts/ is gitignored (per CLAUDE.md
golden rule 1, only data/public/ is committed), so this test is skipped, not failed, when
that file doesn't exist (e.g. a fresh clone before the pipeline has been run), consistent
with docs/AgriTwin_Master_Build_Guide.md's /validate-official being a distinct workflow
from the synthetic-fixture unit tests.

See docs/validation.md for the full write-up, official source, and why production/area
totals are expected to diverge from the official figure while yield_kg_ha is not.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

DISTRICT_YIELD_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "marts" / "district_yield.parquet"
)

# NISR, Seasonal Agricultural Survey Season B 2025 report, Table 6, page 26 (see
# docs/validation.md for the exact source URL and fetch date). National maize yield.
OFFICIAL_MAIZE_YIELD_KG_HA_2025B = 1300.0
TOLERANCE_PCT = 25.0  # see docs/validation.md for why this tolerance is justified

pytestmark = pytest.mark.skipif(
    not DISTRICT_YIELD_PATH.exists(),
    reason="data/marts/district_yield.parquet not built; run `make stage clean marts` first",
)


def test_national_maize_yield_matches_official_report():
    district_yield = pd.read_parquet(DISTRICT_YIELD_PATH)
    row = district_yield[
        (district_yield["geo_level"] == "national")
        & (district_yield["crop"] == "maize")
        & (district_yield["season"] == "B")
        & (district_yield["year"] == "2025")
    ]
    assert len(row) == 1, "expected exactly one national maize Season B 2025 estimate"

    estimated_yield = row.iloc[0]["yield_kg_ha"]
    relative_diff_pct = (
        abs(estimated_yield - OFFICIAL_MAIZE_YIELD_KG_HA_2025B)
        / OFFICIAL_MAIZE_YIELD_KG_HA_2025B
        * 100
    )
    assert relative_diff_pct <= TOLERANCE_PCT, (
        f"estimated yield {estimated_yield:.0f} kg/ha vs official "
        f"{OFFICIAL_MAIZE_YIELD_KG_HA_2025B:.0f} kg/ha: {relative_diff_pct:.1f}% off, "
        f"exceeds the {TOLERANCE_PCT}% tolerance"
    )
