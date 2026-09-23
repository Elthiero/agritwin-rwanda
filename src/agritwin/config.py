"""Small YAML config loaders shared across the pipeline.

Never re-read config/*.yaml by hand elsewhere; import these so every module
agrees on where settings and data source definitions live.
"""

from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def load_settings() -> dict:
    with open(CONFIG_DIR / "settings.yaml") as f:
        return yaml.safe_load(f)


def load_data_sources() -> dict:
    with open(CONFIG_DIR / "data_sources.yaml") as f:
        return yaml.safe_load(f)


def gee_dataset_config(name: str) -> dict:
    """Config for one entry under gee.datasets in config/data_sources.yaml."""
    return load_data_sources()["gee"]["datasets"][name]


def load_variable_map() -> dict:
    with open(CONFIG_DIR / "sas_variable_map.yaml") as f:
        return yaml.safe_load(f)


def load_file_registry() -> dict:
    with open(CONFIG_DIR / "sas_file_registry.yaml") as f:
        return yaml.safe_load(f)


def load_crops() -> dict:
    with open(CONFIG_DIR / "crops.yaml") as f:
        return yaml.safe_load(f)
