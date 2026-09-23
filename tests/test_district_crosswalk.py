"""Validates data/reference/district_crosswalk.csv, the SAS district_code <-> HDX/GAUL
crosswalk that closes the open item logged in docs/decisions.md. Reads the crosswalk
CSV directly (it is a small, committed reference table under data/reference, not raw
microdata under data/raw, so this does not violate the "never read data/raw in tests"
rule in src/agritwin/CLAUDE.md).

The expected (code, name) sets below are not re-derived from data/raw here; they are the
literal values independently confirmed in this session by reading value labels straight
from the raw SAS files (metadata-only, all 7 years) and from the existing GEE mart CSVs,
recorded as a fixed reference so this test never needs raw data access to run.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CROSSWALK_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "reference" / "district_crosswalk.csv"
)

# Confirmed 2026-09-23 by reading district_code value labels from all 7 SAS years
# (2019-2025) directly; identical across every year except one 2025 spelling typo
# ("Nyarugenege" for code 11), which is documented in docs/decisions.md and not
# reflected here since the crosswalk stores the correct spelling.
EXPECTED_NISR_DISTRICT_CODES = {
    11, 12, 13, 21, 22, 23, 24, 25, 26, 27, 28, 31, 32, 33, 34, 35, 36, 37,
    41, 42, 43, 44, 45, 51, 52, 53, 54, 55, 56, 57,
}

# Confirmed 2026-09-23 against data/external/gee/ndvi_district_season.csv's district_name
# column (30 unique values, exact string match against the SAS-side names above).
EXPECTED_GEE_DISTRICT_NAMES = {
    "Bugesera", "Burera", "Gakenke", "Gasabo", "Gatsibo", "Gicumbi", "Gisagara", "Huye",
    "Kamonyi", "Karongi", "Kayonza", "Kicukiro", "Kirehe", "Muhanga", "Musanze", "Ngoma",
    "Ngororero", "Nyabihu", "Nyagatare", "Nyamagabe", "Nyamasheke", "Nyanza", "Nyarugenge",
    "Nyaruguru", "Rubavu", "Ruhango", "Rulindo", "Rusizi", "Rutsiro", "Rwamagana",
}


def _load() -> pd.DataFrame:
    return pd.read_csv(CROSSWALK_PATH)


def test_file_exists_and_has_expected_columns():
    df = _load()
    assert set(df.columns) == {
        "nisr_district_code",
        "district_name",
        "province",
        "hdx_pcode",
        "gaul_code",
    }


def test_exactly_thirty_rows():
    df = _load()
    assert len(df) == 30


def test_no_duplicate_nisr_district_code():
    df = _load()
    assert df["nisr_district_code"].duplicated().sum() == 0


def test_no_duplicate_district_name():
    df = _load()
    assert df["district_name"].duplicated().sum() == 0


def test_no_duplicate_hdx_pcode():
    df = _load()
    assert df["hdx_pcode"].duplicated().sum() == 0


def test_no_nulls_in_any_column():
    df = _load()
    assert df.isna().sum().sum() == 0


def test_every_sas_district_code_maps_exactly_once():
    df = _load()
    codes = df["nisr_district_code"].tolist()
    assert set(codes) == EXPECTED_NISR_DISTRICT_CODES
    assert len(codes) == len(EXPECTED_NISR_DISTRICT_CODES)


def test_every_gee_district_name_maps_exactly_once():
    df = _load()
    names = df["district_name"].tolist()
    assert set(names) == EXPECTED_GEE_DISTRICT_NAMES
    assert len(names) == len(EXPECTED_GEE_DISTRICT_NAMES)


def test_hdx_pcode_matches_nisr_district_code_numeric_suffix():
    # RW11 -> 11, RW57 -> 57: confirms the two codes are the same underlying admin
    # code, not independently assigned identifiers that happen to overlap in range.
    df = _load()
    suffix = df["hdx_pcode"].str[2:].astype(int)
    assert (suffix == df["nisr_district_code"]).all()


def test_gaul_code_is_five_digit_gaul_range():
    # FAO GAUL admin2 codes for Rwanda fall in 21974-22003 (confirmed against the
    # existing data/external/gee/*.csv outputs); a code outside this range would
    # indicate a bad join, not a legitimate GAUL code.
    df = _load()
    assert df["gaul_code"].between(21974, 22003).all()
