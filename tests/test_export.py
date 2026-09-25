"""Unit tests for export/. Synthetic fixtures only; one smoke test renders a real PDF
via the actually-installed weasyprint, since a template typo would otherwise only
surface at real pipeline-run time."""

from __future__ import annotations

import json

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from agritwin.export.briefs import build_brief_context, render_brief_html, write_brief_pdf
from agritwin.export.geo import attach_district_codes, simplify_boundaries
from agritwin.export.static_data import CSV_MIRRORS, build_meta
from agritwin.export.static_data import run as run_static_data


def _yield_gap_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "district_code": 11.0, "crop": "maize", "season": "A", "year": 2023,
                "actual_yield_kg_ha": 900.0, "attainable_yield_kg_ha": 1500.0,
                "yield_gap_pct": 40.0, "reliability": "ok",
            },
            {
                "district_code": 11.0, "crop": "maize", "season": "B", "year": 2024,
                "actual_yield_kg_ha": 950.0, "attainable_yield_kg_ha": 1500.0,
                "yield_gap_pct": 36.7, "reliability": "ok",
            },
            {
                "district_code": 11.0, "crop": "beans", "season": "A", "year": 2024,
                "actual_yield_kg_ha": 400.0, "attainable_yield_kg_ha": 1000.0,
                "yield_gap_pct": 60.0, "reliability": "suppressed",
            },
            {
                "district_code": 12.0, "crop": "maize", "season": "A", "year": 2024,
                "actual_yield_kg_ha": 700.0, "attainable_yield_kg_ha": 1400.0,
                "yield_gap_pct": 50.0, "reliability": "ok",
            },
        ]
    )


def _drivers_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "district_code": 11.0, "crop": "maize", "feature": "improved_seed",
                "mean_abs_shap": 0.2, "direction": "positive",
            },
            {
                "district_code": 11.0, "crop": "maize", "feature": "soil_ph",
                "mean_abs_shap": 0.1, "direction": "negative",
            },
        ]
    )


def test_build_brief_context_picks_most_recent_year_per_crop():
    context = build_brief_context(11, "Nyarugenge", _yield_gap_df(), _drivers_df(), "2026-09-24")
    crops = {c["crop"]: c for c in context["crops"]}
    assert crops["maize"]["year"] == 2024
    assert crops["maize"]["season"] == "B"
    assert context["district_code"] == 11
    assert context["district_name"] == "Nyarugenge"


def test_build_brief_context_includes_top_drivers_for_matched_crop():
    context = build_brief_context(11, "Nyarugenge", _yield_gap_df(), _drivers_df(), "2026-09-24")
    maize = next(c for c in context["crops"] if c["crop"] == "maize")
    assert [d["feature"] for d in maize["top_drivers"]] == ["improved_seed", "soil_ph"]


def test_build_brief_context_only_includes_this_district():
    context = build_brief_context(11, "Nyarugenge", _yield_gap_df(), _drivers_df(), "2026-09-24")
    crops = {c["crop"] for c in context["crops"]}
    assert crops == {"maize", "beans"}


def test_render_brief_html_marks_suppressed_rows():
    context = build_brief_context(11, "Nyarugenge", _yield_gap_df(), _drivers_df(), "2026-09-24")
    html = render_brief_html(context)
    assert "Nyarugenge" in html
    assert "Too few surveyed plots" in html


def test_write_brief_pdf_produces_a_real_pdf(tmp_path):
    context = build_brief_context(11, "Nyarugenge", _yield_gap_df(), _drivers_df(), "2026-09-24")
    html = render_brief_html(context)
    output_path = tmp_path / "11.pdf"
    write_brief_pdf(html, output_path)
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF")


def _square(x: float, y: float, size: float = 0.01) -> Polygon:
    return Polygon([(x, y), (x + size, y), (x + size, y + size), (x, y + size)])


def test_simplify_boundaries_preserves_row_count_and_crs():
    gdf = gpd.GeoDataFrame(
        {"district_name": ["Kigali"], "gaul_district_code": [1]},
        geometry=[_square(30.0, -2.0)],
        crs="EPSG:4326",
    )
    simplified = simplify_boundaries(gdf, tolerance_m=1000)
    assert len(simplified) == 1
    assert simplified.crs.to_epsg() == 4326


def test_attach_district_codes_joins_on_gaul_code():
    gdf = gpd.GeoDataFrame(
        {"district_name": ["Kigali"], "gaul_district_code": [21996]},
        geometry=[_square(30.0, -2.0)],
        crs="EPSG:4326",
    )
    crosswalk = pd.DataFrame(
        {"gaul_code": [21996], "nisr_district_code": [11], "district_name": ["Nyarugenge"]}
    )
    result = attach_district_codes(gdf, crosswalk)
    assert result.loc[0, "district_code"] == 11


def test_build_meta_matches_years_and_sorts_districts():
    district_yield = pd.DataFrame({"year": [2024, 2019, 2024]})
    districts_geojson = {
        "features": [
            {"properties": {"district_code": 21, "district_name": "Nyanza"}},
            {"properties": {"district_code": 11, "district_name": "Nyarugenge"}},
        ]
    }
    meta = build_meta(district_yield, districts_geojson)
    assert meta["years"] == [2019, 2024]
    assert [d["district_code"] for d in meta["districts"]] == [11, 21]
    assert meta["crops"] == ["maize", "beans", "irish_potato", "sorghum"]


def test_build_meta_handles_missing_sources():
    meta = build_meta(None, None)
    assert meta["years"] == []
    assert meta["districts"] == []


def test_run_static_data_mirrors_every_public_csv_and_writes_meta(tmp_path):
    public_dir = tmp_path / "public"
    (public_dir / "geo").mkdir(parents=True)
    for csv_name in CSV_MIRRORS:
        pd.DataFrame([{"crop": "maize", "year": 2024}]).to_csv(public_dir / csv_name, index=False)
    (public_dir / "geo" / "rwanda_districts_simplified.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": []})
    )

    out_dir = tmp_path / "static-data"
    run_static_data(public_dir=public_dir, out_dir=out_dir)

    for json_name in CSV_MIRRORS.values():
        assert (out_dir / json_name).exists()
    assert (out_dir / "districts.geojson").exists()
    assert (out_dir / "meta.json").exists()
    meta = json.loads((out_dir / "meta.json").read_text())
    assert meta["years"] == [2024]


def test_run_static_data_skips_missing_files_without_raising(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    out_dir = tmp_path / "static-data"
    run_static_data(public_dir=public_dir, out_dir=out_dir)  # no CSVs, no geojson at all
    assert (out_dir / "meta.json").exists()
    for json_name in CSV_MIRRORS.values():
        assert not (out_dir / json_name).exists()
