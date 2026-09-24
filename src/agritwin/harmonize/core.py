"""Pure functions: join season files, rename to canonical schema, derive computed columns.

No file I/O here (see io.py) and no yield/QC computation (that is clean/'s job, per
src/agritwin/CLAUDE.md module responsibilities). This module only renames and stacks.
"""

from __future__ import annotations

import pandas as pd

# canonical_variable -> default raw file role it is sourced from, when not "production".
# Confirmed by /audit-sas across all 7 years: fertilizer questions live in the
# fertilizer/pesticide file, practice questions live in the agricultural practice file,
# everything else lives in the production (crop-level) file.
FILE_LOCATION: dict[str, str] = {
    "organic_fert": "fertilizer",
    "inorganic_fert": "fertilizer",
    "pesticide": "fertilizer",
    "erosion_degree": "practice",
    "anti_erosion": "practice",
    "land_consolidation": "practice",
    "mechanized": "practice",
    "irrigated": "practice",
}

# (year, canonical_variable) -> file role override, for the documented exceptions to
# FILE_LOCATION. Only one exists: 2019 weight is segment-level and only present in the
# agricultural practice file, not production. See docs/decisions.md 2026-09-23.
FILE_LOCATION_OVERRIDES: dict[tuple[int, str], str] = {
    (2019, "weight"): "practice",
}

# year -> survey design level of the weight column. See docs/decisions.md 2026-09-23:
# 2019 is segment-level (weight is constant per segment); 2020-2025 are plot-level
# (weight varies within a segment). This is a property of the survey design, not of
# which file the column happens to live in, so it is tracked separately from
# FILE_LOCATION_OVERRIDES even though the two currently coincide for 2019.
WEIGHT_LEVEL_BY_YEAR: dict[int, str] = {
    2019: "segment",
    2020: "plot",
    2021: "plot",
    2022: "plot",
    2023: "plot",
    2024: "plot",
    2025: "plot",
}

# Canonical variables that are Yes/No survey flags, encoded 1=Yes, 2=No. Confirmed by
# direct inspection of value labels in 2019 and 2023 (both consistent). Any other coded
# value (including missing) becomes null, not False, so "unknown" is never conflated
# with "no".
BOOLEAN_FLAG_VARS = frozenset(
    {
        "improved_seed",
        "organic_fert",
        "inorganic_fert",
        "pesticide",
        "anti_erosion",
        "land_consolidation",
        "irrigated",
    }
)

# Canonical variables kept as raw source codes in the output schema (not decoded to
# booleans, and not remapped to a small fixed vocabulary like `crop`). Confirmed by
# /audit-sas: the code -> label mapping for these is NOT stable across years. farmer_type
# code 2 means "large scale farmer" in 2019 but "small scale farmer as cooperative" in
# 2020+ (2019 has 2 codes, 2020+ has 4); erosion_degree has 3 levels in 2019 vs 4 in
# 2024+. A consumer must decode using the correct year's labels (see
# stg_sas_value_labels.parquet, written by run.py), never assume a fixed meaning per
# code across years. See docs/decisions.md 2026-09-23.
CODED_VARIABLES = ("farmer_type", "erosion_degree")


def value_label_rows(year: int, variable: str, labels: dict) -> list[dict]:
    """Turn a {code: label} dict (as read by io.read_value_labels) into rows for the
    stg_sas_value_labels sidecar table."""
    return [
        {"year": year, "variable": variable, "code": code, "label": label}
        for code, label in labels.items()
    ]


# canonical staging schema columns produced by this module, per src/agritwin/CLAUDE.md,
# minus yield_kg_ha and qc_flag (owned by clean/, not harmonize/). district_name starts
# null here (rename_to_canonical has no crosswalk) and is filled in by run()'s call to
# attach_district_name() once all years/seasons are stacked.
OUTPUT_COLUMNS = [
    "year",
    "season",
    "district_code",
    "district_name",
    "province_code",
    "stratum",
    "segment_id",
    "farmer_id",
    "farmer_type",
    "plot_id",
    "plot_area_sqm",
    "plot_area_ha",
    "n_main_crops",
    "pure_stand",
    "crop_code_src",
    "crop",
    "harvest_kg",
    "improved_seed",
    "organic_fert",
    "inorganic_fert",
    "pesticide",
    "erosion_degree",
    "anti_erosion",
    "land_consolidation",
    "mechanized",
    "irrigated",
    "sowing_month",
    "weight",
    "weight_level",
]


def file_for(year: int, variable: str) -> str:
    """Which raw file role (production/practice/fertilizer) a canonical variable is sourced
    from in a given year."""
    override = FILE_LOCATION_OVERRIDES.get((year, variable))
    if override is not None:
        return override
    return FILE_LOCATION.get(variable, "production")


def _source_columns(entry: dict) -> list[str]:
    source = entry["source"]
    if source is None:
        return []
    if isinstance(source, list):
        return list(source)
    return [source]


def columns_needed_from(year: int, role: str, year_map: dict) -> list[str]:
    """All raw source column names sourced from one file role this year, across every
    canonical variable (deduplicated, order preserved)."""
    cols: list[str] = []
    for variable, entry in year_map.items():
        if file_for(year, variable) != role:
            continue
        for col in _source_columns(entry):
            if col not in cols:
                cols.append(col)
    return cols


def _qualified_name(role: str, source_col: str) -> str:
    return f"{role}__{source_col}"


def resolved_column(year: int, variable: str, year_map: dict) -> str | None:
    """The actual scalar column name to read from the *joined* DataFrame for a canonical
    variable (all canonical variables except `mechanized`, whose source is a list; see
    resolved_column_list). Columns pulled from practice/fertilizer are always renamed to
    "{role}__{source}" during join_season_files, regardless of whether production happens
    to have a same-named column, so there is never ambiguity about which file's value a
    canonical variable resolves to."""
    entry = year_map[variable]
    source = entry["source"]
    if source is None or isinstance(source, list):
        return None
    role = file_for(year, variable)
    return source if role == "production" else _qualified_name(role, source)


def resolved_column_list(year: int, variable: str, year_map: dict) -> list[str]:
    """Like resolved_column, but for a canonical variable whose source is a list of raw
    columns (currently only `mechanized`, OR'd across oxen/tractor/other flags)."""
    entry = year_map[variable]
    source = entry["source"]
    if source is None:
        return []
    cols = source if isinstance(source, list) else [source]
    role = file_for(year, variable)
    if role == "production":
        return cols
    return [_qualified_name(role, c) for c in cols]


def join_season_files(year: int, files: dict[str, pd.DataFrame], year_map: dict) -> pd.DataFrame:
    """Left-join production (crop-level, base table) with practice and fertilizer
    (plot-level) on (segment_id_src, plot_id_src). Only the raw columns actually needed
    for this year's canonical mapping are pulled from practice/fertilizer, and each is
    renamed to "{role}__{column}" before merging, so a column name shared by coincidence
    with production (e.g. both files carry an "s1q1" or, in principle, a "weight" column)
    can never be silently shadowed or picked from the wrong file.

    Row count of the result always equals row count of `production`: production is the
    base, practice/fertilizer are deduplicated to one row per plot before merging, so the
    left join can neither drop nor duplicate rows.
    """
    segment_id_src = year_map["segment_id"]["source"]
    plot_id_src = year_map["plot_id"]["source"]
    join_keys = [segment_id_src, plot_id_src]

    result = files["production"].copy()

    for role in ("practice", "fertilizer"):
        if role not in files:
            continue
        needed = columns_needed_from(year, role, year_map)
        present = [c for c in needed if c in files[role].columns]
        subset = files[role][join_keys + present].drop_duplicates(subset=join_keys)
        subset = subset.rename(columns={c: _qualified_name(role, c) for c in present})
        result = result.merge(subset, on=join_keys, how="left")

    return result


def _to_bool(series: pd.Series) -> pd.Series:
    """1 -> True, 2 -> No, anything else (including missing) -> null."""
    return series.map({1: True, 2: False})


def _or_flags(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    """OR across several Yes/No flag columns. True if any is Yes; False if none is Yes but
    at least one is a known No; null only if every column is missing/unknown."""
    bools = pd.concat([_to_bool(df[c]) for c in cols if c in df.columns], axis=1)
    any_true = bools.any(axis=1, skipna=True)
    all_null = bools.isna().all(axis=1)
    return any_true.astype("boolean").mask(all_null, pd.NA)


def rename_to_canonical(
    joined: pd.DataFrame, year: int, season: str, year_map: dict
) -> pd.DataFrame:
    """Select and rename source columns to canonical names for one year x season. Does not
    join files (see join_season_files) and does not compute yield or QC flags (see clean/).
    """
    out = pd.DataFrame(index=joined.index)
    out["year"] = year
    out["season"] = season

    for variable in (
        "district_code",
        "province_code",
        "stratum",
        "segment_id",
        "farmer_id",
        "farmer_type",
        "plot_id",
        "plot_area_sqm",
        "n_main_crops",
        "crop_code_src",
        "sowing_date",
        "erosion_degree",
        "weight",
    ):
        col = resolved_column(year, variable, year_map)
        out[variable] = joined[col] if col is not None and col in joined.columns else pd.NA

    for variable in BOOLEAN_FLAG_VARS:
        col = resolved_column(year, variable, year_map)
        if col is not None and col in joined.columns:
            out[variable] = _to_bool(joined[col])
        else:
            out[variable] = pd.NA

    mechanized_cols = resolved_column_list(year, "mechanized", year_map)
    present = [c for c in mechanized_cols if c in joined.columns]
    out["mechanized"] = _or_flags(joined, present) if present else pd.NA

    # canonical harvest_kg always sources from s2q21 (harvest_kg_plot), never s2q22
    # (harvest_kg_crop). See docs/decisions.md 2026-09-23: s2q22 captures projected/
    # expected production, not actual harvest, and is not equivalent to s2q21.
    harvest_col = resolved_column(year, "harvest_kg_plot", year_map)
    if harvest_col is not None and harvest_col in joined.columns:
        out["harvest_kg"] = joined[harvest_col]
    else:
        out["harvest_kg"] = pd.NA

    out["district_name"] = pd.NA
    out["plot_area_ha"] = out["plot_area_sqm"] / 10000
    out["pure_stand"] = out["n_main_crops"] == 1
    out["weight_level"] = WEIGHT_LEVEL_BY_YEAR[year]
    out["sowing_month"] = pd.to_datetime(out["sowing_date"], errors="coerce").dt.month
    out = out.drop(columns=["sowing_date"])

    return out


def apply_crop_codes(df: pd.DataFrame, code_map: dict[int, str]) -> pd.DataFrame:
    """Map crop_code_src to canonical crop name. Unmapped codes become null crop, the row
    is kept (never dropped silently)."""
    df = df.copy()
    df["crop"] = df["crop_code_src"].map(code_map)
    return df


def attach_district_name(df: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    """Fill district_name from the NISR district_code -> name crosswalk (see
    data/reference/district_crosswalk.csv, loaded by the caller). A district_code with no
    match keeps district_name null rather than dropping the row."""
    lookup = crosswalk.set_index("nisr_district_code")["district_name"]
    df = df.copy()
    df["district_name"] = df["district_code"].map(lookup)
    return df


def build_confidence_table(variable_map: dict) -> pd.DataFrame:
    """Flatten config/sas_variable_map.yaml into (year, variable, confidence, note, file)
    rows, one per (year, canonical_variable) as tracked in the audit. This documents the
    provenance of every mapped variable, including ones (e.g. qty_lost_kg, interview_date)
    that are not part of the final stg_sas_plot_crop schema."""
    rows = []
    for year, block in variable_map.items():
        for variable, entry in block["production"].items():
            rows.append(
                {
                    "year": year,
                    "variable": variable,
                    "confidence": entry["confidence"],
                    "note": entry.get("note"),
                    "file": file_for(year, variable),
                }
            )
    return pd.DataFrame(rows)
