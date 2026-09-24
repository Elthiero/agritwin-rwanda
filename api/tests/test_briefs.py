"""Tests for /briefs/{code}.pdf, against a small fixture and real boundaries."""

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


def test_get_brief_happy_path(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/briefs/57.pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")
        assert response.headers["cache-control"].startswith("public, max-age=")


def test_get_brief_ignores_crop_and_season_query_params(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/briefs/57.pdf", params={"crop": "maize", "season": "A"})
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")


def test_get_brief_unknown_district_returns_404(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/briefs/999.pdf")
        assert response.status_code == 404


def test_get_brief_known_district_without_a_generated_brief_returns_404(monkeypatch):
    with _client(monkeypatch) as client:
        # District 11 (Nyarugenge) is real, but only fixtures/.../briefs/57.pdf exists.
        response = client.get("/api/v1/briefs/11.pdf")
        assert response.status_code == 404
        assert "No brief available" in response.json()["detail"]


def test_get_brief_invalid_crop_returns_422(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/briefs/57.pdf", params={"crop": "cassava"})
        assert response.status_code == 422
