"""Pure functions: yield_kg_ha computation and qc_flag assignment on stg_sas_plot_crop.

harmonize/ already produced every other canonical column (see its core.py); this module
only adds the two columns CLAUDE.md's canonical schema reserves for clean/: yield_kg_ha
and qc_flag. Never drops or reorders rows.
"""

from __future__ import annotations

import pandas as pd

# qc_flag values, in the priority order applied below. A row gets the first flag whose
# condition is true; "ok" means none of the earlier conditions applied.
FLAG_MISSING_DATA = "missing_data"
FLAG_ZERO_AREA = "zero_area"
FLAG_AREA_TOO_SMALL = "area_too_small"
FLAG_NOT_PURE_STAND = "not_pure_stand"
FLAG_NOT_SSF = "not_ssf"
FLAG_ABOVE_CAP = "above_plausibility_cap"
FLAG_OUTLIER_LOW = "outlier_low"
FLAG_OUTLIER_HIGH = "outlier_high"
FLAG_OK = "ok"


def resolve_ssf(value_labels: pd.DataFrame) -> dict[tuple[int, int], bool]:
    """(year, farmer_type code) -> is this code a "small scale" farmer type this year.

    Reads label text from stg_sas_value_labels (built by harmonize/) rather than a
    hardcoded code table, since farmer_type's code->meaning mapping is not stable across
    years (see src/agritwin/CLAUDE.md and docs/decisions.md 2026-09-23). A code with no
    label at all, or a label not starting with "small scale", is not SSF.
    """
    farmer_type_labels = value_labels[value_labels["variable"] == "farmer_type"]
    return {
        (int(year), int(code)): str(label).strip().lower().startswith("small scale")
        for year, code, label in zip(
            farmer_type_labels["year"],
            farmer_type_labels["code"],
            farmer_type_labels["label"],
            strict=True,
        )
    }


def compute_yield_kg_ha(df: pd.DataFrame) -> pd.Series:
    """harvest_kg / plot_area_ha, null when either input is missing or area is zero.

    Computed for every row regardless of qc_flag (kept visible for QC notebooks per
    CLAUDE.md golden rule 3), not just rows that pass the eligibility checks below.
    """
    has_inputs = df["harvest_kg"].notna() & df["plot_area_ha"].notna() & (df["plot_area_ha"] > 0)
    return (df["harvest_kg"] / df["plot_area_ha"]).where(has_inputs)


def _is_ssf(df: pd.DataFrame, ssf_lookup: dict[tuple[int, int], bool]) -> pd.Series:
    def lookup(row: pd.Series) -> bool:
        if pd.isna(row["farmer_type"]):
            return False
        return ssf_lookup.get((int(row["year"]), int(row["farmer_type"])), False)

    return df.apply(lookup, axis=1)


def compute_qc_flag(
    df: pd.DataFrame,
    yield_kg_ha: pd.Series,
    ssf_lookup: dict[tuple[int, int], bool],
    settings: dict,
) -> pd.Series:
    """Priority-ordered qc_flag. See module docstring for the full order and rationale
    in docs/AgriTwin_Master_Build_Guide.md section 4.1 and src/agritwin/CLAUDE.md.
    """
    qc_cfg = settings["yield_qc"]
    min_area = qc_cfg["min_plot_area_sqm"]
    max_yield = qc_cfg["max_yield_kg_ha"]

    missing_data = df["harvest_kg"].isna() | df["plot_area_sqm"].isna()
    zero_area = ~missing_data & (df["plot_area_sqm"] == 0)
    area_too_small = ~missing_data & ~zero_area & (df["plot_area_sqm"] < min_area)
    not_pure_stand = df["pure_stand"] != True  # noqa: E712 (nullable boolean: catches False and NA)
    is_ssf = _is_ssf(df, ssf_lookup)
    not_ssf = ~is_ssf

    max_cap = df["crop"].map(max_yield)
    above_cap = yield_kg_ha.notna() & max_cap.notna() & (yield_kg_ha > max_cap)

    eligible = (
        ~missing_data
        & ~zero_area
        & ~area_too_small
        & (df["pure_stand"] == True)  # noqa: E712
        & is_ssf
        & ~above_cap
    )
    outlier_low, outlier_high = _outlier_flags(df, yield_kg_ha, eligible, qc_cfg)

    flag = pd.Series(FLAG_OK, index=df.index, dtype="object")
    for condition, value in [
        (outlier_high, FLAG_OUTLIER_HIGH),
        (outlier_low, FLAG_OUTLIER_LOW),
        (above_cap, FLAG_ABOVE_CAP),
        (not_ssf, FLAG_NOT_SSF),
        (not_pure_stand, FLAG_NOT_PURE_STAND),
        (area_too_small, FLAG_AREA_TOO_SMALL),
        (zero_area, FLAG_ZERO_AREA),
        (missing_data, FLAG_MISSING_DATA),
    ]:
        flag = flag.mask(condition, value)
    return flag


def _outlier_flags(
    df: pd.DataFrame, yield_kg_ha: pd.Series, eligible: pd.Series, qc_cfg: dict
) -> tuple[pd.Series, pd.Series]:
    """Below/above the configured percentile within (crop, season, year), computed only
    over the eligible subset so ineligible rows never widen or shift the trim bounds."""
    lower_pct = qc_cfg["trim_lower_pct"] / 100
    upper_pct = qc_cfg["trim_upper_pct"] / 100

    low = pd.Series(False, index=df.index)
    high = pd.Series(False, index=df.index)
    groups = df.loc[eligible].groupby(["crop", "season", "year"], dropna=False).groups
    for idx in groups.values():
        group_yield = yield_kg_ha.loc[idx]
        lower_bound = group_yield.quantile(lower_pct)
        upper_bound = group_yield.quantile(upper_pct)
        low.loc[idx] = group_yield < lower_bound
        high.loc[idx] = group_yield > upper_bound
    return low, high


def clean_plot_crop(df: pd.DataFrame, value_labels: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Add yield_kg_ha and qc_flag to harmonize's stg_sas_plot_crop output. Row count,
    row order, and every existing column are preserved exactly."""
    ssf_lookup = resolve_ssf(value_labels)
    yield_kg_ha = compute_yield_kg_ha(df)
    qc_flag = compute_qc_flag(df, yield_kg_ha, ssf_lookup, settings)
    out = df.copy()
    out["yield_kg_ha"] = yield_kg_ha
    out["qc_flag"] = qc_flag
    return out
