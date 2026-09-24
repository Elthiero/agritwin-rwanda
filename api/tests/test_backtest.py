"""Tests for the backtest endpoint, against a small fixture (not the real data/public/)."""

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


def test_get_backtest_returns_rows_for_crop(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/backtest", params={"crop": "maize", "season": "A"})
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 2
        assert {r["model"] for r in rows} == {"baseline_district_mean", "ridge"}


def test_get_backtest_filters_by_crop(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/backtest", params={"crop": "beans", "season": "B"})
        rows = response.json()
        assert len(rows) == 1
        assert rows[0]["model"] == "ridge"
        assert rows[0]["lead_months"] == 4


def test_get_backtest_unknown_combination_returns_empty_list(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/backtest", params={"crop": "sorghum", "season": "A"})
        assert response.status_code == 200
        assert response.json() == []


def test_get_backtest_missing_crop_returns_422(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/backtest", params={"season": "A"})
        assert response.status_code == 422


def test_get_backtest_every_row_carries_mae_and_spread(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/backtest", params={"crop": "maize", "season": "A"})
        for row in response.json():
            assert "mae_kg_ha" in row
            assert "mape_std_across_years" in row
