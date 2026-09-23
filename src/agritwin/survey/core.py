"""Pure functions: design-based, survey-weighted estimates from clean/'s qc-flagged panel.

Consumes stg_sas_plot_crop (harmonize/ + clean/'s completed canonical schema), restricted
to qc_flag == "ok" rows (pure-stand, small-scale-farmer, non-outlier plots; see
docs/survey-design.md for why this restriction is forced by harvest_kg's own definition,
not a preference). Estimates weighted total production, weighted total cultivated area,
and yield as a ratio estimator, with Taylor-linearized variance via samplics, at
crop x district x season x year (and coarser province/national) granularity.

2019 (segment-level weight) and 2020-2025 (plot-level weight) are estimated as two
independent design blocks and never pooled into one variance calculation, per
docs/decisions.md 2026-09-23.
"""

from __future__ import annotations

import warnings

import pandas as pd

from agritwin.harmonize.core import WEIGHT_LEVEL_BY_YEAR

DOMAIN_SEP = "\x1f"

# year -> {raw stratum code -> canonical stratum label}. Codes are not stable across years
# (see docs/survey-design.md); only the canonical label is a safe cross-year key. 2021's
# code 11 is mapped to "hillside" based on the season-partition evidence documented there
# (confirmed with the team, not an unverified guess).
STRATUM_CODE_MAP: dict[int, dict[int, str]] = {
    2019: {11: "hillside", 20: "marshland", 30: "rangeland", 50: "lsf"},
    2020: {0: "lsf", 10: "hillside", 20: "marshland", 30: "rangeland", 40: "mixed"},
    2021: {0: "lsf", 10: "hillside", 11: "hillside", 20: "marshland", 30: "rangeland", 40: "mixed"},
    2022: {0: "lsf", 10: "hillside", 20: "marshland", 30: "rangeland", 40: "mixed"},
    2023: {0: "lsf", 10: "hillside", 20: "marshland", 30: "rangeland", 40: "mixed"},
    2024: {10: "hillside", 20: "marshland", 30: "rangeland", 40: "mixed", 90: "lsf"},
    2025: {10: "hillside", 20: "marshland", 30: "rangeland", 40: "mixed", 90: "lsf"},
}


def canonicalize_stratum(df: pd.DataFrame) -> pd.Series:
    """Map each row's (year, stratum) to a canonical stratum label. A code with no entry
    in STRATUM_CODE_MAP for that year (unexpected, not yet seen in any audited year) maps
    to null rather than being silently grouped under a wrong label."""

    def _map_row(year: int, code: float) -> str | None:
        if pd.isna(code):
            return None
        return STRATUM_CODE_MAP.get(int(year), {}).get(int(code))

    return pd.Series(
        [_map_row(y, c) for y, c in zip(df["year"], df["stratum"], strict=True)], index=df.index
    )


def build_psu_key(df: pd.DataFrame) -> pd.Series:
    """(year, segment_id) as a single string key: segment_id is not a stable identifier
    of the same physical location across years (segment counts differ year to year, see
    docs/survey-design.md), so the PSU key must carry year too."""
    return df["year"].astype(str) + "_" + df["segment_id"].astype("Int64").astype(str)


def design_block(year: int) -> str:
    """'segment' (2019) or 'plot' (2020-2025): which weighting design a year belongs to."""
    return WEIGHT_LEVEL_BY_YEAR[year]


def prepare_for_estimation(df: pd.DataFrame) -> pd.DataFrame:
    """Restrict to eligible rows (qc_flag == "ok") and attach the columns the estimator
    needs: stratum_canonical, psu_key, design_block. Never used on the full unfiltered
    panel: production/area totals over non-"ok" rows would double-count intercropped
    plots' harvest and include outliers clean/ already flagged."""
    # crop must be non-null: an unmapped crop code (see harmonize/) has no meaningful
    # crop x district x season x year domain to estimate against. weight must be present
    # and positive: samplics' TaylorEstimator cannot weight a row with no weight, and a
    # handful of rows (e.g. 2021, see docs/survey-design.md) have a null weight.
    eligible = df[
        (df["qc_flag"] == "ok") & df["crop"].notna() & df["weight"].notna() & (df["weight"] > 0)
    ].copy()
    eligible["stratum_canonical"] = canonicalize_stratum(eligible)
    eligible["psu_key"] = build_psu_key(eligible)
    eligible["design_block"] = eligible["year"].map(design_block)
    return eligible


def _build_domain(df: pd.DataFrame, group_cols: list[str]) -> pd.Series:
    domain = df[group_cols[0]].astype(str)
    for col in group_cols[1:]:
        domain = domain.str.cat(df[col].astype(str), sep=DOMAIN_SEP, na_rep="NA")
    return domain


def _split_domain(domain: pd.Series, group_cols: list[str]) -> pd.DataFrame:
    parts = domain.str.split(DOMAIN_SEP, expand=True)
    parts.columns = group_cols
    return parts


def _zero_yield_domains(df: pd.DataFrame, domain: pd.Series) -> set[str]:
    """Domains where every row's harvest_kg is exactly 0 (total crop failure for every
    sampled plot in that crop x geography x season x year cell). Every retained row has a
    positive weight (see prepare_for_estimation), so the weighted total is exactly zero
    in these domains too, not just the unweighted one. samplics' TaylorEstimator computes
    CV as stderror / point_est unconditionally and raises ZeroDivisionError on 0.0/0.0 for
    these; handled here by estimating them separately rather than working around the
    library internals."""
    totals = df.groupby(domain)["harvest_kg"].sum()
    return set(totals[totals == 0].index)


def _patch_single_domain(result: pd.DataFrame, domain: pd.Series) -> pd.DataFrame:
    """samplics' TaylorEstimator.to_dataframe() returns a null "_domain" column when
    exactly one domain value is present in the input (it collapses to a "no domain"
    scalar result internally instead of tagging the single domain), which breaks a
    merge-on-"_domain" join against the other estimates. Filled in here from the input,
    since there is exactly one possible value it could be."""
    if result["_domain"].isna().any():
        unique_domains = domain.unique()
        if len(unique_domains) == 1:
            result = result.copy()
            result["_domain"] = unique_domains[0]
    return result


def _taylor_total(y: pd.Series, common: dict, value_col: str, se_col: str) -> pd.DataFrame:
    from samplics.estimation import TaylorEstimator
    from samplics.utils.types import PopParam

    est = TaylorEstimator(PopParam.total)
    est.estimate(y=y, **common)
    result = _patch_single_domain(est.to_dataframe(), common["domain"])
    return result.rename(columns={"_estimate": value_col, "_stderror": se_col})[
        ["_domain", value_col, se_col]
    ]


def _taylor_ratio(y: pd.Series, x: pd.Series, common: dict) -> pd.DataFrame:
    from samplics.estimation import TaylorEstimator
    from samplics.utils.types import PopParam

    est = TaylorEstimator(PopParam.ratio)
    est.estimate(y=y, x=x, **common)
    return _patch_single_domain(est.to_dataframe(), common["domain"]).rename(
        columns={
            "_estimate": "yield_kg_ha",
            "_stderror": "yield_kg_ha_se",
            "_lci": "yield_kg_ha_ci_low",
            "_uci": "yield_kg_ha_ci_high",
            "_cv": "yield_kg_ha_cv",
        }
    )[
        [
            "_domain",
            "yield_kg_ha",
            "yield_kg_ha_se",
            "yield_kg_ha_ci_low",
            "yield_kg_ha_ci_high",
            "yield_kg_ha_cv",
        ]
    ]


def _zero_yield_rows(domains: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Manually constructed production/yield rows for domains with zero total harvest.
    Variance is genuinely zero (every unit reports the same value, 0, so there is no
    sampling variance to estimate), and CV is genuinely undefined (0/0), not approximated
    as 0 or infinity."""
    production = pd.DataFrame(
        {
            "_domain": list(domains),
            "total_production_kg": 0.0,
            "total_production_kg_se": 0.0,
        }
    )
    yield_rows = pd.DataFrame(
        {
            "_domain": list(domains),
            "yield_kg_ha": 0.0,
            "yield_kg_ha_se": 0.0,
            "yield_kg_ha_ci_low": 0.0,
            "yield_kg_ha_ci_high": 0.0,
            "yield_kg_ha_cv": float("nan"),
        }
    )
    return production, yield_rows


def _estimate_one_block(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Taylor-linearized weighted total production, total area, and yield ratio for one
    design block (a single weight/PSU/stratum structure), across every domain present."""
    domain = _build_domain(df, group_cols)
    zero_domains = _zero_yield_domains(df, domain)
    nonzero = ~domain.isin(zero_domains)

    from samplics.utils.types import SinglePSUEst

    common: dict[str, object] = {
        "samp_weight": df["weight"][nonzero],
        "stratum": df["stratum_canonical"][nonzero],
        "psu": df["psu_key"][nonzero],
        "domain": domain[nonzero],
        "single_psu": SinglePSUEst.skip,
    }

    production_parts = []
    yield_parts = []
    if nonzero.any():
        production_parts.append(
            _taylor_total(
                df["harvest_kg"][nonzero], common, "total_production_kg", "total_production_kg_se"
            )
        )
        yield_parts.append(
            _taylor_ratio(df["harvest_kg"][nonzero], df["plot_area_ha"][nonzero], common)
        )
    if zero_domains:
        zero_production, zero_yield = _zero_yield_rows(zero_domains)
        production_parts.append(zero_production)
        yield_parts.append(zero_yield)
    production = pd.concat(production_parts, ignore_index=True)
    yield_df = pd.concat(yield_parts, ignore_index=True)

    area_common = {
        "samp_weight": df["weight"],
        "stratum": df["stratum_canonical"],
        "psu": df["psu_key"],
        "domain": domain,
        "single_psu": SinglePSUEst.skip,
    }
    area = _taylor_total(df["plot_area_ha"], area_common, "total_area_ha", "total_area_ha_se")

    sample_sizes = (
        df.assign(_domain=domain)
        .groupby("_domain")
        .agg(n_plots=("plot_id", "size"), n_segments=("segment_id", "nunique"))
        .reset_index()
    )

    result = production.merge(area, on="_domain").merge(yield_df, on="_domain").merge(
        sample_sizes, on="_domain"
    )
    domain_cols = _split_domain(result["_domain"], group_cols)
    result = pd.concat([domain_cols, result.drop(columns="_domain")], axis=1)
    return result


def estimate_ratio(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Weighted total production, total area, and yield ratio per group_cols domain,
    with Taylor-linearized SE/CI/CV and unweighted n_plots/n_segments. df must already be
    prepare_for_estimation()'s output (eligible rows only, design_block attached).
    Estimates each design block (2019 vs 2020-2025) independently, never pooling their
    variance, then concatenates the results.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)  # samplics: archived-package notice
        blocks = [
            _estimate_one_block(block_df, group_cols)
            for _, block_df in df.groupby("design_block")
            if len(block_df) > 0
        ]
    return pd.concat(blocks, ignore_index=True)


def add_reliability_flag(df: pd.DataFrame, cv_max: float, min_segments: int) -> pd.DataFrame:
    """"suppressed" if n_segments < min_segments (not enough PSUs to trust any variance
    estimate); else "use_with_caution" if yield_kg_ha_cv > cv_max; else "ok"."""
    out = df.copy()
    reliability = pd.Series("ok", index=out.index, dtype="object")
    reliability = reliability.mask(out["yield_kg_ha_cv"] > cv_max, "use_with_caution")
    reliability = reliability.mask(out["n_segments"] < min_segments, "suppressed")
    out["reliability"] = reliability
    return out
