"""Plausibility check on the committed rainfall extraction output.

Guards against the bug where a spatial Reducer.sum() (instead of mean())
scaled seasonal rainfall totals by district pixel count: observed values up
to ~43,000 mm, when a season's total rainfall for Rwanda is roughly
300 to 900 mm. RAINFALL_CEILING_MM is a generous upper bound, not a tight
climatological check.
"""

from pathlib import Path

import pandas as pd
import pytest

DATA_EXTERNAL = Path(__file__).resolve().parents[1] / "data" / "external"
CSV_PATH = DATA_EXTERNAL / "gee" / "rainfall_district_season.csv"
RAINFALL_CEILING_MM = 1500


@pytest.mark.skipif(not CSV_PATH.exists(), reason="run `make gee` first to generate this output")
def test_rainfall_seasonal_totals_are_physically_plausible():
    df = pd.read_csv(CSV_PATH)
    assert df["rainfall_mm"].max() < RAINFALL_CEILING_MM
    assert df["rainfall_mm"].min() > 0
