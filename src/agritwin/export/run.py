"""Runner for the export step. Invoked by `make export` (python -m agritwin.export.run).

Builds outputs that sit on top of the already-written data/public/ files without
touching them: a simplified, district_code-joined boundaries GeoJSON, and one
one-page PDF brief per district. Deliberately does not move survey/'s and models/'s
existing direct-to-data/public/ writes into this module; see docs/decisions.md
2026-09-24 for why the current pattern was kept.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import loguru
import pandas as pd

from agritwin.config import load_settings
from agritwin.export.briefs import build_brief_context, render_brief_html, write_brief_pdf
from agritwin.export.geo import attach_district_codes, simplify_boundaries
from agritwin.export.static_data import run as run_static_data
from agritwin.gee.boundaries import load_district_crosswalk

DATA_EXTERNAL = Path(__file__).resolve().parents[3] / "data" / "external"
DATA_PUBLIC = Path(__file__).resolve().parents[3] / "data" / "public"

logger = loguru.logger


def run_geo() -> None:
    """Simplify the raw GAUL boundaries and join in the NISR district_code, for
    consumers that want a small, ready-to-serve GeoJSON rather than the
    extraction-grade full-resolution one in data/external/."""
    settings = load_settings()
    raw_path = DATA_EXTERNAL / "boundaries" / "rwanda_districts.geojson"
    gdf = gpd.read_file(raw_path)
    crosswalk = load_district_crosswalk()
    gdf = attach_district_codes(gdf, crosswalk)
    gdf = simplify_boundaries(gdf, settings["export"]["simplify_tolerance_m"])

    output_path = DATA_PUBLIC / "geo" / "rwanda_districts_simplified.geojson"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()  # to_file(driver="GeoJSON") refuses to overwrite in place
    gdf.to_file(output_path, driver="GeoJSON")
    logger.info(f"wrote {len(gdf)} simplified district boundaries to {output_path}")


def run_briefs() -> None:
    """One one-page PDF brief per district, covering every MVP crop's latest yield gap
    and top drivers. Reads only already-written data/public/ files; no new modeling."""
    yield_gap_path = DATA_PUBLIC / "yield_gap.csv"
    drivers_path = DATA_PUBLIC / "drivers_by_district.csv"
    if not yield_gap_path.exists() or not drivers_path.exists():
        logger.warning("yield_gap.csv or drivers_by_district.csv missing, skipping briefs")
        return

    settings = load_settings()
    mvp_crops = settings["scope"]["crops"]

    yield_gap = pd.read_csv(yield_gap_path)
    yield_gap = yield_gap[yield_gap["crop"].isin(mvp_crops)]
    drivers_by_district = pd.read_csv(drivers_path)
    crosswalk = load_district_crosswalk()

    output_dir = DATA_PUBLIC / "briefs"
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = pd.Timestamp.now(tz="UTC").date().isoformat()

    for _, row in crosswalk.iterrows():
        district_code = int(row["nisr_district_code"])
        district_name = row["district_name"]
        context = build_brief_context(
            district_code, district_name, yield_gap, drivers_by_district, generated_at
        )
        html = render_brief_html(context)
        write_brief_pdf(html, output_dir / f"{district_code}.pdf")

    logger.info(f"wrote {len(crosswalk)} district briefs to {output_dir}")


def main() -> None:
    run_geo()
    run_briefs()
    run_static_data()  # after run_geo: reads its simplified districts geojson output


if __name__ == "__main__":
    main()
