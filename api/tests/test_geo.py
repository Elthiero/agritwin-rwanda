"""Tests for geographic endpoints."""

from fastapi.testclient import TestClient

from api.app.main import create_app


def test_get_districts():
    """GET /districts returns GeoJSON with 30 district features."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/districts")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 30
        assert all(f["properties"]["district_name"] for f in data["features"])
        assert all(f["properties"]["gaul_district_code"] for f in data["features"])
        assert all(f["geometry"] for f in data["features"])
        valid_types = ["Polygon", "MultiPolygon", "GeometryCollection"]
        assert all(f["geometry"]["type"] in valid_types for f in data["features"])


