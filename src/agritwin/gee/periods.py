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


def partial_season_date_range(
    year: int, season: str, season_windows: dict, lead_months: int
) -> tuple[str, str]:
    """Start-inclusive, end-exclusive ISO date range for the first `lead_months` months
    of one season x year (a "lead time" cutoff for the nowcast: how much of the season
    has happened by the time this estimate would actually be made). lead_months == the
    season's full length reduces to the same end date as season_date_range.
    """
    window = season_windows[season]
    start_month = window["start_month"]
    start_date = f"{year}-{start_month:02d}-01"
    month_index = (start_month - 1) + lead_months
    cutoff_year = year + month_index // 12
    cutoff_month = month_index % 12 + 1
    cutoff_date = f"{cutoff_year}-{cutoff_month:02d}-01"
    return start_date, cutoff_date
