"""Synthetic SAS-shaped fixtures for pipeline tests. Never read data/raw here (see
src/agritwin/CLAUDE.md testing rule); these are small hand-built DataFrames that mimic
the real column names and 1=Yes/2=No encoding confirmed by /audit-sas, without any real
microdata.
"""

from __future__ import annotations

import pandas as pd

# A minimal, structurally realistic year_map (matches the shape of one year's
# "production" block in config/sas_variable_map.yaml). Two crop rows share segment 1 /
# plot 1 (multi-crop plot); segment 2 / plot 1 is a separate, pure-stand plot used to
# exercise edge cases (zero area, missing weight, unknown crop code).
YEAR_MAP = {
    "segment_id": {"source": "Segment_ID", "confidence": "high"},
    "province_code": {"source": "s1q1", "confidence": "high"},
    "district_code": {"source": "s1q2", "confidence": "high"},
    "stratum": {"source": "s1q3", "confidence": "high"},
    "segment_no": {"source": "s1q4", "confidence": "high"},
    "farmer_id": {"source": "s1q6", "confidence": "high"},
    "farmer_type": {"source": "s1q7", "confidence": "high"},
    "plot_id": {"source": "s2q1", "confidence": "high"},
    "plot_area_sqm": {"source": "s2q2", "confidence": "high"},
    "n_main_crops": {"source": "s2q3", "confidence": "high"},
    "crop_code_src": {"source": "s2q4", "confidence": "high"},
    "sowing_date": {"source": "s2q7", "confidence": "high"},
    "improved_seed": {"source": "s2q9", "confidence": "high"},
    "harvest_kg_plot": {"source": "s2q21", "confidence": "high"},
    "harvest_kg_crop": {"source": "s2q22", "confidence": "high"},
    "qty_lost_kg": {"source": "s2q39", "confidence": "high"},
    "organic_fert": {"source": "s3q3", "confidence": "high"},
    "inorganic_fert": {"source": "s3q9", "confidence": "high"},
    "pesticide": {"source": "s3q19", "confidence": "high"},
    "erosion_degree": {"source": "s4q1", "confidence": "high"},
    "anti_erosion": {"source": "s4q3", "confidence": "high"},
    "land_consolidation": {"source": "s4q6", "confidence": "high"},
    "mechanized": {"source": ["s4q10_1", "s4q11_1", "s4q12_1"], "confidence": "high"},
    "irrigated": {"source": "s4q15", "confidence": "high"},
    "interview_date": {"source": None, "confidence": "high"},
    "weight": {"source": "plot_weight", "confidence": "high"},
}

# Same shape as YEAR_MAP but with weight sourced from the practice file and
# improved_seed unmapped, mimicking 2019 (segment-level weight, no improved_seed flag).
YEAR_MAP_2019_STYLE = {
    **YEAR_MAP,
    "improved_seed": {"source": None, "confidence": "low", "note": "no direct yes/no flag"},
    "weight": {"source": "weight", "confidence": "high", "note": "segment-level"},
}


def production_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Segment_ID": [1, 1, 2],
            "s1q1": [1, 1, 2],
            "s1q2": [10, 10, 20],
            "s1q3": [1, 1, 2],
            "s1q4": ["01", "01", "02"],
            "s1q6": [100, 100, 200],
            "s1q7": [1, 1, 2],
            "s2q1": [1, 1, 1],
            "s2q2": [5000.0, 5000.0, 0.0],  # edge case: zero plot area (segment 2)
            "s2q3": [2, 2, 1],  # multi-crop plot vs pure-stand plot
            "s2q4": [101, 999, 101],  # edge case: 999 is an unknown crop code
            "s2q7": ["2024-09-15", "2024-09-15", "2024-03-01"],
            "s2q9": [1, 2, None],
            "s2q21": [500.0, 500.0, None],
            "s2q22": [400.0, 100.0, None],
            "plot_weight": [50.0, 50.0, None],  # edge case: missing weight (segment 2)
            "weight": [50.0, 50.0, None],  # present in production too, for 2019-style tests
        }
    )


def practice_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Segment_ID": [1, 2],
            "s2q1": [1, 1],
            "s4q1": [2, 3],
            "s4q3": [1, 2],
            "s4q6": [2, 1],
            "s4q10_1": [1, None],
            "s4q11_1": [2, None],
            "s4q12_1": [None, None],  # edge case: segment 2 has all-null mechanized flags
            "s4q15": [2, 1],
            "weight": [50.0, 999.0],  # 2019-style: segment-level weight lives here
        }
    )


def fertilizer_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Segment_ID": [1, 2],
            "s2q1": [1, 1],
            "s3q3": [1, 2],
            "s3q9": [2, 1],
            "s3q19": [1, None],
        }
    )


def season_files() -> dict[str, pd.DataFrame]:
    return {"production": production_df(), "practice": practice_df(), "fertilizer": fertilizer_df()}
