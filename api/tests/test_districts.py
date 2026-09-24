"""Tests for /districts/{code}/profile, against a small fixture and real boundaries."""

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


def test_get_district_profile_happy_path(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/districts/11/profile", params={"crop": "maize", "season": "A"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["district_code"] == 11
        assert body["district_name"] == "Nyarugenge"
        assert [r["year"] for r in body["yield_trend"]] == [2023, 2024]
        assert len(body["gap_trend"]) == 1
        assert body["gap_trend"][0]["yield_gap_pct"] == 39.97
        assert len(body["top_drivers"]) == 2
        assert {d["district_code"] for d in body["peer_districts"]} == {12}


def test_get_district_profile_peer_districts_exclude_self(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/districts/12/profile", params={"crop": "maize", "season": "A"}
        )
        peers = response.json()["peer_districts"]
        assert 12 not in {p["district_code"] for p in peers}
        assert 11 in {p["district_code"] for p in peers}


def test_get_district_profile_unknown_district_returns_404(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/districts/999/profile", params={"crop": "maize", "season": "A"}
        )
        assert response.status_code == 404


def test_get_district_profile_no_data_for_crop_returns_empty_lists(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get(
            "/api/v1/districts/11/profile", params={"crop": "sorghum", "season": "A"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["yield_trend"] == []
        assert body["gap_trend"] == []
        assert body["top_drivers"] == []
