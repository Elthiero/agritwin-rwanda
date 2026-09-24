"""One-page PDF district brief: this district's latest yield gap and top drivers for
every MVP crop, per docs/AgriTwin_Master_Build_Guide.md section 8 ("one-page PDF
district brief, generated ahead of time and served as a static file").

Reads only already-written data/public/ files (yield_gap.csv, drivers_by_district.csv);
no new modeling happens here, only presentation. Per CLAUDE.md rule 5, driver
associations are always phrased as associations, never causes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2
import pandas as pd

# ruff: noqa: E501 (HTML template markup below reads better on one line per row)

TOP_N_DRIVERS = 3

BRIEF_TEMPLATE = jinja2.Template(
    """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 2cm; }
  body { font-family: sans-serif; color: #1a1a1a; }
  h1 { font-size: 20px; margin-bottom: 0; }
  .subtitle { color: #555; font-size: 11px; margin-top: 2px; }
  .badge { display: inline-block; background: #eef; color: #224; padding: 2px 8px;
           border-radius: 4px; font-size: 10px; margin-top: 6px; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; }
  th, td { text-align: left; padding: 4px 6px; border-bottom: 1px solid #ddd; font-size: 11px; }
  th { background: #f4f4f4; width: 40%; }
  .crop-block { margin-top: 18px; }
  .reliability-suppressed { color: #999; font-style: italic; }
  .drivers { font-size: 10px; color: #444; margin-top: 4px; }
  .footer { margin-top: 24px; font-size: 9px; color: #888; }
</style>
</head>
<body>
  <h1>{{ district_name }} district brief</h1>
  <div class="subtitle">Generated {{ generated_at }}</div>
  <div class="badge">Model-based estimates. Not official NISR statistics.</div>

  {% for crop in crops %}
  <div class="crop-block">
    <h3>{{ crop.crop | replace("_", " ") | title }} ({{ crop.season }} {{ crop.year }})</h3>
    {% if crop.reliability == "suppressed" %}
      <p class="reliability-suppressed">Too few surveyed plots this season to report reliably.</p>
    {% else %}
      <table>
        <tr><th>Actual yield</th><td>{{ "%.0f"|format(crop.actual_yield_kg_ha) }} kg/ha</td></tr>
        {% if crop.attainable_yield_kg_ha %}
        <tr><th>Attainable yield</th><td>{{ "%.0f"|format(crop.attainable_yield_kg_ha) }} kg/ha</td></tr>
        <tr><th>Yield gap</th><td>{{ "%.0f"|format(crop.yield_gap_pct) }} percent of attainable</td></tr>
        {% endif %}
        <tr><th>Reliability</th><td>{{ crop.reliability }}</td></tr>
      </table>
      {% if crop.top_drivers %}
      <div class="drivers">
        Associated with higher or lower yield (model-based, not causal):
        {% for d in crop.top_drivers %}{{ d.feature | replace("_", " ") }} ({{ d.direction }}){{ ", " if not loop.last }}{% endfor %}
      </div>
      {% endif %}
    {% endif %}
  </div>
  {% endfor %}

  <div class="footer">
    AgriTwin Rwanda. NISR 2026 Big Data Hackathon. Yield and yield-gap figures are
    survey-weighted model-based estimates, not official NISR statistics. Driver
    associations are not causal.
  </div>
</body>
</html>
"""
)


def latest_crop_rows(yield_gap_df: pd.DataFrame, district_code: int) -> list[dict[str, Any]]:
    """One row per MVP crop present for `district_code`: the most recent year, breaking
    a same-year tie by preferring season B (the later calendar season within a year
    label). A crop never surveyed for this district is simply absent, not zero-filled.
    """
    df = yield_gap_df[yield_gap_df["district_code"] == float(district_code)]
    rows: list[dict[str, Any]] = []
    for _, group in df.groupby("crop"):
        group = group.sort_values(["year", "season"], ascending=[False, False])
        row: dict[str, Any] = group.iloc[0].to_dict()  # type: ignore[assignment]
        rows.append(row)
    return rows


def top_driver_rows(
    drivers_by_district_df: pd.DataFrame, district_code: int, crop: str, top_n: int = TOP_N_DRIVERS
) -> list[dict[str, Any]]:
    """The top_n features by mean_abs_shap for one district x crop."""
    df = drivers_by_district_df[
        (drivers_by_district_df["district_code"] == float(district_code))
        & (drivers_by_district_df["crop"] == crop)
    ]
    rows: list[dict[str, Any]] = df.sort_values(  # type: ignore[assignment]
        "mean_abs_shap", ascending=False
    ).head(top_n).to_dict("records")
    return rows


def build_brief_context(
    district_code: int,
    district_name: str,
    yield_gap_df: pd.DataFrame,
    drivers_by_district_df: pd.DataFrame,
    generated_at: str,
) -> dict[str, Any]:
    """Assemble the template context for one district's brief: its latest yield-gap row
    per MVP crop, each with that crop's top drivers attached."""
    crops = []
    for row in latest_crop_rows(yield_gap_df, district_code):
        crops.append(
            {
                "crop": row["crop"],
                "season": row["season"],
                "year": int(row["year"]),
                "actual_yield_kg_ha": row["actual_yield_kg_ha"],
                "attainable_yield_kg_ha": row.get("attainable_yield_kg_ha"),
                "yield_gap_pct": row.get("yield_gap_pct"),
                "reliability": row["reliability"],
                "top_drivers": top_driver_rows(drivers_by_district_df, district_code, row["crop"]),
            }
        )
    crops.sort(key=lambda c: c["crop"])
    return {
        "district_code": district_code,
        "district_name": district_name,
        "generated_at": generated_at,
        "crops": crops,
    }


def render_brief_html(context: dict[str, Any]) -> str:
    return BRIEF_TEMPLATE.render(**context)


def write_brief_pdf(html: str, output_path: Path) -> None:
    from weasyprint import HTML

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html).write_pdf(str(output_path))
