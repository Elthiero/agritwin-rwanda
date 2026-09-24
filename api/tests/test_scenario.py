"""Tests for the /scenario/{code} endpoint, against a small fixture and real boundaries
(district_code validity is checked against the real district boundary data, which
data_store always loads regardless of DATA_DIR, per test_geo.py's same convention)."""

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


def test_get_scenario_happy_path(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/scenario/11", params={"crop": "maize", "season": "A"}
        )
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 2
        assert {r["improved_seed"] for r in rows} == {True, False}
        off = next(r for r in rows if not r["improved_seed"])
        on = next(r for r in rows if r["improved_seed"])
        assert on["mean_yield_kg_ha"] > off["mean_yield_kg_ha"]
        assert all(r["ci_low"] <= r["ci_high"] for r in rows)


def test_get_scenario_includes_suppressed_rows(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/scenario/12", params={"crop": "maize", "season": "A"}
        )
        rows = response.json()
        assert len(rows) == 1
        assert rows[0]["reliability"] == "suppressed"


def test_get_scenario_unknown_district_returns_404(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/scenario/999", params={"crop": "maize", "season": "A"}
        )
        assert response.status_code == 404


def test_get_scenario_invalid_crop_returns_422(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/scenario/11", params={"crop": "cassava", "season": "A"}
        )
        assert response.status_code == 422
