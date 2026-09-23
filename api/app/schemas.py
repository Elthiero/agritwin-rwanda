"""Pydantic response schemas for API endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class GeoJSONResponse(BaseModel):
    """GeoJSON FeatureCollection response."""

    type: str = "FeatureCollection"
    features: list[dict[str, Any]]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"district_name": "Kigali", "gaul_district_code": 1},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[29.0, -2.0], [29.1, -2.0]]],
                        },
                    }
                ],
            }
        }
    )
