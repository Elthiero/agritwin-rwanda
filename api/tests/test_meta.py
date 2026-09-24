"""Tests for the /meta endpoint, against a small fixture (not the real data/public/)."""

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


def test_get_meta_returns_scope_from_real_data(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/meta")
        assert response.status_code == 200
        body = response.json()
        assert set(body["crops"]) == {"maize", "beans", "irish_potato", "sorghum"}
        assert set(body["seasons"]) == {"A", "B"}
        # years come from the fixture district_yield.csv, not a hardcoded list
        assert body["years"] == [2023, 2024]
        assert len(body["districts"]) == 30  # real boundary data, always loaded
        assert body["data_version"]


def test_get_meta_districts_have_code_and_name(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/meta")
        districts = response.json()["districts"]
        bugesera = next(d for d in districts if d["district_name"] == "Bugesera")
        assert bugesera["district_code"] == 57
