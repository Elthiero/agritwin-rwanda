"""Tests for the yield-gap endpoint, against a small fixture (not the real data/public/)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.app.main import create_app
from api.app.settings import get_settings

FIXTURE_DATA_DIR = Path(__file__).resolve().parent / "fixtures" / "data"
MAIZE_A_2024 = {"crop": "maize", "season": "A", "year": 2024}


def _client(monkeypatch) -> TestClient:
    monkeypatch.setenv("DATA_DIR", str(FIXTURE_DATA_DIR))
    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)


def test_get_yield_gap_happy_path(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/yield-gap", params=MAIZE_A_2024)
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 2
        assert {r["district_code"] for r in rows} == {11, 12}
        assert response.headers["cache-control"].startswith("public, max-age=")


def test_get_yield_gap_returns_every_reliability_tier(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/yield-gap", params=MAIZE_A_2024)
        rows = response.json()
        reliabilities = {r["reliability"] for r in rows}
        assert reliabilities == {"ok", "suppressed"}
        suppressed_row = next(r for r in rows if r["reliability"] == "suppressed")
        assert suppressed_row["actual_yield_kg_ha"] == 700.2  # the number is not hidden


def test_get_yield_gap_filters_by_crop_season_year(monkeypatch):
    with _client(monkeypatch) as client:
        beans = client.get(
            "/api/v1/yield-gap", params={"crop": "beans", "season": "A", "year": 2024}
        )
        assert len(beans.json()) == 1
        assert beans.json()[0]["district_code"] == 13

        season_b = client.get(
            "/api/v1/yield-gap", params={"crop": "maize", "season": "B", "year": 2024}
        )
        assert len(season_b.json()) == 1
        assert season_b.json()[0]["district_code"] == 11


def test_get_yield_gap_unknown_year_returns_empty_list(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/yield-gap", params={"crop": "maize", "season": "A", "year": 1999}
        )
        assert response.status_code == 200
        assert response.json() == []


def test_get_yield_gap_invalid_crop_returns_422(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/yield-gap", params={"crop": "cassava", "season": "A", "year": 2024}
        )
        assert response.status_code == 422


def test_get_yield_gap_missing_required_param_returns_422(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/yield-gap", params={"crop": "maize", "season": "A"})
        assert response.status_code == 422


def test_get_yield_gap_every_row_carries_ci_and_reliability(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/yield-gap", params=MAIZE_A_2024)
        for row in response.json():
            assert "reliability" in row
            assert "actual_yield_kg_ha_ci_low" in row
            assert "actual_yield_kg_ha_ci_high" in row
            assert "n_plots" in row
