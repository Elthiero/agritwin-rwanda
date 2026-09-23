"""Runner for feature mart steps. Invoked by `make features`."""

from __future__ import annotations

from pathlib import Path

from agritwin.features.gee_mart import join_gee_features, load_gee_outputs, write_gee_mart

DATA_EXTERNAL = Path(__file__).resolve().parents[3] / "data" / "external"


def run_gee_mart() -> None:
    """Join Earth Engine outputs into a district x season x year feature table."""
    outputs = load_gee_outputs()
    df = join_gee_features(
        outputs["ndvi"], outputs["rainfall"], outputs["cropland"], outputs["soil"]
    )
    write_gee_mart(df, DATA_EXTERNAL / "gee" / "feat_district_season_joined.csv")


def main() -> None:
    run_gee_mart()


if __name__ == "__main__":
    main()
