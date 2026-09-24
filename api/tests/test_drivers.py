"""Tests for the drivers endpoint, against a small fixture (not the real data/public/)."""

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


def test_get_drivers_global_returns_crop_rows(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/drivers", params={"crop": "maize", "season": "A"})
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 3
        assert all(r["crop"] == "maize" for r in rows)
        assert all(r["district_code"] is None for r in rows)


def test_get_drivers_by_district_includes_suppressed_rows(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/drivers", params={"crop": "maize", "season": "A", "district": 11}
        )
        rows = response.json()
        assert len(rows) == 2
        assert all(r["district_code"] == 11 for r in rows)
        assert {r["reliability"] for r in rows} == {"suppressed"}


def test_get_drivers_different_district_is_ok(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/drivers", params={"crop": "maize", "season": "A", "district": 12}
        )
        rows = response.json()
        assert len(rows) == 1
        assert rows[0]["reliability"] == "ok"


def test_get_drivers_invalid_crop_returns_422(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/drivers", params={"crop": "cassava", "season": "A"}
        )
        assert response.status_code == 422


def test_get_drivers_missing_season_returns_422(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/drivers", params={"crop": "maize"})
        assert response.status_code == 422
