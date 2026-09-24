"""Pydantic settings for the API."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # The repo's data/ root (matches .env.example's DATA_DIR=./data), not data/public/
    # directly: consumers append the subfolder they need (public/, external/, ...).
    DATA_DIR: Path = Path(__file__).resolve().parents[2] / "data"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    CACHE_SECONDS: int = 3600


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
