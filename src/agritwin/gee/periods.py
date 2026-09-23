"""Season x year date ranges, for filtering time-varying Earth Engine collections."""

from __future__ import annotations


def season_date_range(year: int, season: str, season_windows: dict) -> tuple[str, str]:
    """Start-inclusive, end-exclusive ISO date range for one season x year.

    season_windows comes from config/settings.yaml (scope.season_windows), e.g.
    {"A": {"start_month": 9, "end_month": 2}, "B": {"start_month": 3, "end_month": 6}}.
    Season A runs September to February, so it wraps into year + 1; season B does not.
    """
    window = season_windows[season]
    start_month = window["start_month"]
    end_month = window["end_month"]
    start_date = f"{year}-{start_month:02d}-01"
    end_year = year + 1 if end_month < start_month else year
    end_date = (
        f"{end_year + 1}-01-01" if end_month == 12 else f"{end_year}-{end_month + 1:02d}-01"
    )
    return start_date, end_date
