"""Unit tests for the harmonize module. Synthetic fixtures only, no data/raw reads."""

from __future__ import annotations

import pandas as pd

from agritwin.harmonize.core import (
    OUTPUT_COLUMNS,
    apply_crop_codes,
    build_confidence_table,
    join_season_files,
    rename_to_canonical,
)
from tests.fixtures.synthetic_sas import (
    YEAR_MAP,
    YEAR_MAP_2019_STYLE,
    production_df,
    season_files,
)

CROP_MAP = {101: "maize", 103: "sorghum"}


def _harmonized(year: int = 2024, season: str = "A", year_map: dict = YEAR_MAP) -> pd.DataFrame:
    files = season_files()
    joined = join_season_files(year, files, year_map)
    renamed = rename_to_canonical(joined, year, season, year_map)
    return apply_crop_codes(renamed, CROP_MAP)


def test_join_preserves_production_row_count():
    files = season_files()
    joined = join_season_files(2024, files, YEAR_MAP)
    assert len(joined) == len(production_df())


def test_join_does_not_collide_on_shared_column_names():
    # production and practice/fertilizer all carry s1q1/s1q2/... but harmonize only pulls
    # the columns each canonical variable actually needs, and role-qualifies each pulled
    # column ("practice__s4q1"), so no pandas _x/_y suffix ever appears and no column from
    # practice/fertilizer can be shadowed by a same-named production column.
    files = season_files()
    joined = join_season_files(2024, files, YEAR_MAP)
    assert not any(c.endswith(("_x", "_y")) for c in joined.columns)
    assert "practice__s4q1" in joined.columns  # pulled in from practice, role-qualified
    assert "fertilizer__s3q3" in joined.columns  # pulled in from fertilizer, role-qualified


def test_output_has_exactly_the_canonical_columns():
    df = _harmonized()
    assert set(df.columns) == set(OUTPUT_COLUMNS)


def test_missing_weight_is_null_not_dropped():
    df = _harmonized()
    assert len(df) == 3
    segment2_row = df[(df["segment_id"] == 2)].iloc[0]
    assert pd.isna(segment2_row["weight"])


def test_zero_plot_area_becomes_zero_hectares_not_error():
    df = _harmonized()
    segment2_row = df[df["segment_id"] == 2].iloc[0]
    assert segment2_row["plot_area_sqm"] == 0.0
    assert segment2_row["plot_area_ha"] == 0.0


def test_unknown_crop_code_becomes_null_crop_row_kept():
    df = _harmonized()
    unknown_rows = df[df["crop_code_src"] == 999]
    assert len(unknown_rows) == 1
    assert pd.isna(unknown_rows.iloc[0]["crop"])


def test_known_crop_code_maps_to_canonical_name():
    df = _harmonized()
    known_rows = df[df["crop_code_src"] == 101]
    assert (known_rows["crop"] == "maize").all()


def test_mechanized_or_across_flags():
    df = _harmonized()
    # segment 1: s4q10_1=Yes, s4q11_1=No, s4q12_1=missing -> OR is True
    seg1_rows = df[df["segment_id"] == 1]
    assert (seg1_rows["mechanized"] == True).all()  # noqa: E712
    # segment 2: all three flags missing -> null, not False
    seg2_row = df[df["segment_id"] == 2].iloc[0]
    assert pd.isna(seg2_row["mechanized"])


def test_pure_stand_flag_derived_from_n_main_crops():
    df = _harmonized()
    seg1_rows = df[df["segment_id"] == 1]
    assert (~seg1_rows["pure_stand"]).all()  # n_main_crops == 2
    seg2_row = df[df["segment_id"] == 2].iloc[0]
    assert seg2_row["pure_stand"]  # n_main_crops == 1


def test_harvest_kg_sources_from_s2q21_not_s2q22():
    # s2q21 (harvest_kg_plot) = 500, s2q22 (harvest_kg_crop) = 400 for the first row.
    # harvest_kg must equal s2q21's value, not s2q22's (see docs/decisions.md 2026-09-23).
    df = _harmonized()
    first_row = df.iloc[0]
    assert first_row["harvest_kg"] == 500.0


def test_weight_level_plot_for_2024_style_year():
    df = _harmonized(year=2024, year_map=YEAR_MAP)
    assert (df["weight_level"] == "plot").all()


def test_weight_level_segment_for_2019_style_year():
    df = _harmonized(year=2019, year_map=YEAR_MAP_2019_STYLE)
    assert (df["weight_level"] == "segment").all()
    # weight for 2019-style year must come from the practice file's "weight" column
    # (999.0 for segment 2), not the production file's identically-named column (which
    # would give a different, wrong value if the join collided).
    seg2_row = df[df["segment_id"] == 2].iloc[0]
    assert seg2_row["weight"] == 999.0


def test_confidence_table_flags_low_confidence_entry():
    variable_map = {2019: {"production": YEAR_MAP_2019_STYLE}, 2024: {"production": YEAR_MAP}}
    table = build_confidence_table(variable_map)
    low = table[(table["year"] == 2019) & (table["variable"] == "improved_seed")]
    assert len(low) == 1
    assert low.iloc[0]["confidence"] == "low"
    high = table[(table["year"] == 2024) & (table["variable"] == "improved_seed")]
    assert high.iloc[0]["confidence"] == "high"
