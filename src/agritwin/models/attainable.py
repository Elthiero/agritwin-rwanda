"""Attainable yield and yield gap.

Per docs/AgriTwin_Master_Build_Guide.md section 4.1 and src/agritwin/CLAUDE.md: attainable
yield is the weighted 90th percentile of pure-stand plot yields within an agro-ecological
zone x crop x season group, pooled across the core years. No AEZ boundary layer is
configured anywhere in this repo (checked config/data_sources.yaml and data/external/): the
build guide's own documented fallback applies, k-means zoning on district-level static
features, per config/settings.yaml's attainable.zone_method (see docs/decisions.md
2026-09-23 for why this was changed from its placeholder "aez" value to "kmeans").

Yield gap = attainable minus actual (survey/'s district-level weighted yield estimate),
in kg/ha and as a percent of attainable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from agritwin.survey.core import prepare_for_estimation

ZONE_FEATURES = [
    "soil_ph",
    "soil_nitrogen",
    "soil_carbon",
    "soil_texture_class",
    "cropland_fraction",
]


def assign_zones(
    soil_df: pd.DataFrame, cropland_df: pd.DataFrame, k: int, random_state: int = 0
) -> pd.DataFrame:
    """K-means zones from district-level static soil and cropland features. Standardized
    before clustering since the features are on very different scales (pH ~4-7, nitrogen/
    carbon in g/kg, cropland_fraction in [0,1]); an unscaled clustering would be dominated
    by whichever feature has the largest raw magnitude. Deterministic given random_state,
    so re-running with the same inputs reproduces the same zone_id assignment (zone_id
    labels themselves are arbitrary, not ordered or meaningful beyond grouping).
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    merged = soil_df.merge(
        cropland_df[["nisr_district_code", "cropland_fraction"]], on="nisr_district_code"
    )
    features = StandardScaler().fit_transform(merged[ZONE_FEATURES])
    labels = KMeans(n_clusters=k, random_state=random_state, n_init=10).fit_predict(features)
    return pd.DataFrame({"nisr_district_code": merged["nisr_district_code"], "zone_id": labels})


def weighted_percentile(values: pd.Series, weights: pd.Series, percentile: float) -> float:
    """Survey-weighted percentile via the midpoint-interpolation method (each observation's
    cumulative-weight position is its own weight's midpoint, then linearly interpolated at
    the target percentile), the standard approach for a weighted quantile of a finite
    population (matches, e.g., statsmodels' DescrStatsW.quantile). Reduces to the ordinary
    (unweighted) percentile when every weight is equal.
    """
    order = np.argsort(values.to_numpy())
    sorted_values = values.to_numpy()[order]
    sorted_weights = weights.to_numpy()[order]
    cum_weights = np.cumsum(sorted_weights) - 0.5 * sorted_weights
    cum_weights = cum_weights / sorted_weights.sum()
    return float(np.interp(percentile / 100, cum_weights, sorted_values))


def attach_zone(plot_crop: pd.DataFrame, zones: pd.DataFrame) -> pd.DataFrame:
    """Join zone_id onto each plot by its district. Plots in a district with no zone
    assignment (should not happen, all 30 districts are zoned, but not assumed) keep a
    null zone_id rather than being silently dropped."""
    return plot_crop.merge(
        zones, left_on="district_code", right_on="nisr_district_code", how="left"
    ).drop(columns="nisr_district_code")


def compute_attainable_yield(
    eligible: pd.DataFrame, percentile: float, min_segments: int
) -> pd.DataFrame:
    """Weighted percentile of yield_kg_ha per (zone_id, crop, season), pooled across every
    year present in `eligible` (attainable yield is not year-specific: it represents a
    stable ceiling for the zone/crop/season, not a per-year figure). `eligible` must
    already be restricted to qc_flag == "ok" rows with zone_id attached (see attach_zone
    and agritwin.survey.core.prepare_for_estimation).

    Unlike survey/'s Taylor-linearized estimates, no confidence interval is computed for
    this percentile: samplics does not expose an arbitrary-percentile Taylor variance
    (only PopParam.median), and a PSU bootstrap for a 90th-percentile CI is out of scope
    for this pass (see docs/decisions.md 2026-09-23). A segment-count-based reliability
    flag is used instead, the same suppression logic as survey/.
    """
    rows = []
    groups = eligible.groupby(["zone_id", "crop", "season"], dropna=False)
    for (zone_id, crop, season), group in groups:
        rows.append(
            {
                "zone_id": zone_id,
                "crop": crop,
                "season": season,
                "attainable_yield_kg_ha": weighted_percentile(
                    group["yield_kg_ha"], group["weight"], percentile
                ),
                "n_plots": len(group),
                "n_segments": group["segment_id"].nunique(),
                "n_years": group["year"].nunique(),
            }
        )
    result = pd.DataFrame(rows)
    result["reliability"] = np.where(result["n_segments"] < min_segments, "suppressed", "ok")
    return result


def compute_yield_gap(
    district_yield: pd.DataFrame, attainable_yield: pd.DataFrame, zones: pd.DataFrame
) -> pd.DataFrame:
    """Yield gap per district x crop x season x year: attainable (that district's zone,
    same crop/season, pooled across years) minus actual (survey/'s district-level weighted
    yield estimate for that specific year). The gap number itself is computed whenever
    both point estimates exist, regardless of reliability tier: per CLAUDE.md golden rule
    6, a low-reliability cell is "flagged... and greyed out in the UI", not hidden, so the
    number stays and the combined reliability (the worse of the actual and attainable
    reliability) travels with it instead. Gap is null only when there is genuinely no
    matching attainable-yield group for that district's zone x crop x season (a left-merge
    miss, not a reliability judgment).
    """
    district_actual = district_yield[district_yield["geo_level"] == "district"].copy()
    district_actual["district_code"] = district_actual["geo_code"].astype(float)
    district_actual = district_actual.merge(
        zones, left_on="district_code", right_on="nisr_district_code", how="left"
    )

    merged = district_actual.merge(
        attainable_yield,
        on=["zone_id", "crop", "season"],
        how="left",
        suffixes=("_actual", "_attainable"),
    )

    merged["yield_gap_kg_ha"] = merged["attainable_yield_kg_ha"] - merged["yield_kg_ha"]
    merged["yield_gap_pct"] = merged["yield_gap_kg_ha"] / merged["attainable_yield_kg_ha"] * 100

    reliability_rank = {"ok": 0, "use_with_caution": 1, "suppressed": 2}
    actual_rank = merged["reliability_actual"].map(reliability_rank)
    attainable_rank = merged["reliability_attainable"].map(reliability_rank).fillna(
        reliability_rank["suppressed"]
    )
    worse_rank = pd.Series(np.maximum(actual_rank, attainable_rank), index=merged.index)
    rank_to_label = {v: k for k, v in reliability_rank.items()}
    merged["reliability"] = worse_rank.map(rank_to_label)

    # n_plots/n_segments/reliability exist on both sides of the merge (district_yield and
    # attainable_yield each carry their own), so pandas suffixes them; the "actual" side's
    # sample size is what a district x crop x season x year figure's own n_plots means.
    return merged[
        [
            "district_code",
            "zone_id",
            "crop",
            "season",
            "year",
            "yield_kg_ha",
            "yield_kg_ha_ci_low",
            "yield_kg_ha_ci_high",
            "attainable_yield_kg_ha",
            "yield_gap_kg_ha",
            "yield_gap_pct",
            "n_plots_actual",
            "n_segments_actual",
            "reliability",
        ]
    ].rename(
        columns={
            "yield_kg_ha": "actual_yield_kg_ha",
            "yield_kg_ha_ci_low": "actual_yield_kg_ha_ci_low",
            "yield_kg_ha_ci_high": "actual_yield_kg_ha_ci_high",
            "n_plots_actual": "n_plots",
            "n_segments_actual": "n_segments",
        }
    )


def prepare_eligible_plots(plot_crop: pd.DataFrame, zones: pd.DataFrame) -> pd.DataFrame:
    """Same eligibility filter as survey/'s district estimates (qc_flag == "ok", non-null
    crop, positive weight), plus zone_id attached. Kept as one function so attainable
    yield's plot population is guaranteed identical to the population survey/'s actual
    yield is estimated from; a gap between two differently-filtered populations would be
    meaningless."""
    eligible = prepare_for_estimation(plot_crop)
    return attach_zone(eligible, zones)
