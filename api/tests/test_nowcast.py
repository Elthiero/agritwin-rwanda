"""Tests for /nowcast and /nowcast/{code}/curve, against a small fixture and real
boundaries."""

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


def test_get_nowcast_returns_rows_for_crop_season_year_lead(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/nowcast",
            params={"crop": "maize", "season": "A", "year": 2023, "lead": 3},
        )
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 2
        assert {r["district_code"] for r in rows} == {11, 12}
        assert all(r["is_backtest"] for r in rows)
        assert all(r["actual_yield_kg_ha"] is not None for r in rows)


def test_get_nowcast_defaults_to_lead_3(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/nowcast", params={"crop": "maize", "season": "A", "year": 2023}
        )
        assert len(response.json()) == 2


def test_get_nowcast_unknown_year_returns_empty_list(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/nowcast",
            params={"crop": "maize", "season": "A", "year": 1999, "lead": 3},
        )
        assert response.status_code == 200
        assert response.json() == []


def test_get_nowcast_not_yet_surveyed_row_has_null_actual(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/nowcast",
            params={"crop": "maize", "season": "A", "year": 2024, "lead": 3},
        )
        rows = response.json()
        assert len(rows) == 1
        assert rows[0]["actual_yield_kg_ha"] is None
        assert rows[0]["is_backtest"] is False


def test_get_nowcast_missing_crop_returns_422(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/nowcast", params={"season": "A", "year": 2023})
        assert response.status_code == 422


def test_get_nowcast_curve_returns_one_row_per_lead(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/nowcast/11/curve", params={"season": "A", "year": 2023}
        )
        assert response.status_code == 200
        rows = response.json()
        assert {r["lead_months"] for r in rows} == {2, 3, 4}
        assert all(r["district_code"] == 11 for r in rows)


def test_get_nowcast_curve_unknown_district_returns_404(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/nowcast/999/curve", params={"season": "A", "year": 2023}
        )
        assert response.status_code == 404


def test_get_nowcast_curve_unknown_year_returns_empty_list(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/nowcast/11/curve", params={"season": "A", "year": 1999}
        )
        assert response.status_code == 200
        assert response.json() == []
