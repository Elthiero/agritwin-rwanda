"""Block commits of microdata and validate aggregated public outputs.

Usage:
    python scripts/check_public.py            # check data/public contents
    python scripts/check_public.py --staged   # also check files staged for commit
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import polars as pl

FORBIDDEN_EXT = {".dta", ".sav", ".sas7bdat"}
DATA_EXT = {".parquet", ".csv", ".dta", ".sav", ".sas7bdat", ".xlsx"}
ALLOWED_DATA_DIRS = (
    "data/public/",
    "data/external/official/",
    "data/external/boundaries/",
    "data/external/gee/",
    "tests/fixtures/",
    "api/tests/fixtures/",
)
FORBIDDEN_COLS = {
    "farmer_id", "segment_id", "plot_id", "segment_no",
    "s1q4", "s1q6", "s2q1", "segment_id_src", "Segment_ID",
}


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True
    )
    return [f for f in out.stdout.splitlines() if f]


def check_staged(errors: list[str]) -> None:
    for f in staged_files():
        p = Path(f)
        if p.suffix.lower() in FORBIDDEN_EXT and not f.startswith(("tests/fixtures/", "api/tests/fixtures/")):
            errors.append(f"microdata file staged: {f}")
        elif p.suffix.lower() in DATA_EXT and not f.startswith(ALLOWED_DATA_DIRS):
            errors.append(f"data file outside allowed folders: {f}")


def check_public(errors: list[str]) -> None:
    root = Path("data/public")
    if not root.exists():
        return
    for p in root.rglob("*.parquet"):
        df = pl.read_parquet(p)
        bad = FORBIDDEN_COLS.intersection(df.columns)
        if bad:
            errors.append(f"{p}: identifier columns present {sorted(bad)}")
        if "n_plots" in df.columns and "reliability" not in df.columns:
            errors.append(f"{p}: has n_plots but no reliability column")


def main() -> int:
    errors: list[str] = []
    if "--staged" in sys.argv:
        check_staged(errors)
    check_public(errors)
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        print("Privacy check failed. See CLAUDE.md golden rule 1.")
        return 1
    print("Privacy check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
