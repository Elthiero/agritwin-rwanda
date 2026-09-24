"""Tests for the /kpis endpoint, against a small fixture (not the real data/public/)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.app.main import create_app
from api.app.settings import get_settings

FIXTURE_DATA_DIR = Path(__file__).resolve().parent / "fixtures" / "data"


def _client(monkeypatch) -> TestClient:
    monkeypatch.setenv("DATA_DIR", str(FIXTURE_DATA_DIR))
    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)


def test_get_kpis_returns_one_row_per_crop_at_national_level(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/kpis", params={"year": 2024, "season": "A"})
        assert response.status_code == 200
        rows = response.json()
        assert {r["crop"] for r in rows} == {"maize", "beans"}
        maize = next(r for r in rows if r["crop"] == "maize")
        assert maize["yield_kg_ha"] == 1400.0
        assert maize["yield_kg_ha_ci_low"] == 1300.0
        assert maize["reliability"] == "ok"


def test_get_kpis_does_not_return_district_level_rows(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/kpis", params={"year": 2024, "season": "A"})
        rows = response.json()
        assert all("district_code" not in r for r in rows)


def test_get_kpis_unknown_year_returns_empty_list(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/kpis", params={"year": 1999, "season": "A"})
        assert response.status_code == 200
        assert response.json() == []


def test_get_kpis_missing_required_param_returns_422(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/kpis", params={"year": 2024})
        assert response.status_code == 422
