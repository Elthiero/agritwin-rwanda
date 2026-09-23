"""Unit tests for the harmonize module. Synthetic fixtures only, no data/raw reads."""

from __future__ import annotations

import pandas as pd

from agritwin.harmonize.core import (
    OUTPUT_COLUMNS,
    apply_crop_codes,
    build_confidence_table,
    join_season_files,
    rename_to_canonical,
    resolved_column,
    value_label_rows,
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


def test_2019_weight_resolves_to_practice_file_column():
    # Documented exception in core.FILE_LOCATION_OVERRIDES: 2019 weight is segment-level
    # and only exists in the practice file, unlike every other year (2020-2025) where it
    # comes from production. resolved_column must reflect that exception explicitly,
    # not just happen to produce the right value by coincidence.
    col = resolved_column(2019, "weight", YEAR_MAP_2019_STYLE)
    assert col == "practice__weight"

    col_2024 = resolved_column(2024, "weight", YEAR_MAP)
    assert col_2024 == "plot_weight"  # unqualified: sourced from production, not practice


def test_2019_weight_values_come_from_practice_not_production():
    # production_df() and practice_df() both define a "weight" column with different
    # values on purpose (see tests/fixtures/synthetic_sas.py), specifically so a harmonize
    # bug that silently preferred production's value would be caught here. Practice's
    # weight is [50.0, 999.0] for segment 1 / segment 2; production's is [50.0, 50.0, None].
    # If harmonize used production's value for segment 2, this would read None, not 999.0.
    df = _harmonized(year=2019, year_map=YEAR_MAP_2019_STYLE)
    seg1_rows = df[df["segment_id"] == 1]
    seg2_row = df[df["segment_id"] == 2].iloc[0]
    assert (seg1_rows["weight"] == 50.0).all()  # coincides with production's value here
    assert seg2_row["weight"] == 999.0  # diverges from production's None -- proves the source
    assert seg2_row["weight"] != 50.0  # production's segment-2 value, must not leak through


def test_season_c_excluded_from_run_output_even_if_present_in_raw_input(monkeypatch):
    # Season C (marshland/irrigated) is out of MVP scope per src/agritwin/CLAUDE.md domain
    # definitions, even though raw SAS releases sometimes include a Season C file set.
    # run() must only process the seasons listed in settings.scope.seasons, and must not
    # be fooled into processing Season C just because the file registry or raw files
    # happen to define one.
    import agritwin.harmonize.run as run_module

    fake_settings = {"scope": {"years": [2024], "seasons": ["A", "B"]}}
    fake_file_registry = {
        2024: {
            "A": {"production": "prod_a.dta", "practice": "prac_a.dta", "fertilizer": "fert_a.dta"},
            "B": {"production": "prod_b.dta", "practice": "prac_b.dta", "fertilizer": "fert_b.dta"},
            "C": {"production": "prod_c.dta", "practice": "prac_c.dta", "fertilizer": "fert_c.dta"},
        }
    }
    fake_variable_map = {2024: {"production": YEAR_MAP}}
    fake_crops_cfg = {"source_codes": {2024: CROP_MAP}}

    seasons_processed: list[str] = []

    def fake_read_season_files(year, season, file_registry):
        seasons_processed.append(season)
        return season_files()

    monkeypatch.setattr(run_module, "load_settings", lambda: fake_settings)
    monkeypatch.setattr(run_module, "load_file_registry", lambda: fake_file_registry)
    monkeypatch.setattr(run_module, "load_variable_map", lambda: fake_variable_map)
    monkeypatch.setattr(run_module, "load_crops", lambda: fake_crops_cfg)
    monkeypatch.setattr(run_module, "read_season_files", fake_read_season_files)
    monkeypatch.setattr(run_module, "read_value_labels", lambda path, columns: {})
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda self, *a, **k: None)

    result = run_module.run()

    assert set(seasons_processed) == {"A", "B"}
    assert "C" not in seasons_processed
    assert set(result["season"].unique()) == {"A", "B"}


def test_value_label_rows_preserves_year_specific_codes():
    # farmer_type code 2 means different things in different years (large scale farmer
    # in 2019 vs small scale cooperative in 2020+); the sidecar table must keep these
    # separate by year, not collapse them into one global code -> label dictionary.
    labels_2019 = {1: "small scale farmer", 2: "large scale farmer"}
    labels_2020 = {
        1: "Small scale farmer as individual",
        2: "Small Scale farmer as Coperative",
        3: "Large scale farmer",
    }
    rows_2019 = value_label_rows(2019, "farmer_type", labels_2019)
    rows_2020 = value_label_rows(2020, "farmer_type", labels_2020)
    assert {r["code"]: r["label"] for r in rows_2019}[2] == "large scale farmer"
    assert {r["code"]: r["label"] for r in rows_2020}[2] == "Small Scale farmer as Coperative"
    assert all(r["year"] == 2019 for r in rows_2019)
    assert all(r["variable"] == "farmer_type" for r in rows_2019)


def test_confidence_table_flags_low_confidence_entry():
    variable_map = {2019: {"production": YEAR_MAP_2019_STYLE}, 2024: {"production": YEAR_MAP}}
    table = build_confidence_table(variable_map)
    low = table[(table["year"] == 2019) & (table["variable"] == "improved_seed")]
    assert len(low) == 1
    assert low.iloc[0]["confidence"] == "low"
    high = table[(table["year"] == 2024) & (table["variable"] == "improved_seed")]
    assert high.iloc[0]["confidence"] == "high"
