"""Season x year date ranges, for filtering time-varying Earth Engine collections."""

from __future__ import annotations


def season_date_range(year: int, season: str, season_windows: dict) -> tuple[str, str]:
    """Start-inclusive, end-exclusive ISO date range for one season x year.

    season_windows comes from config/settings.yaml (scope.season_windows), e.g.
    {"A": {"start_month": 9, "end_month": 2}, "B": {"start_month": 3, "end_month": 6}}.

    NISR labels a season by the calendar year it concludes in, not the one it starts in:
    "SAS 2025 Season A" was sown around September 2024 and collected December 2024 to
    February 2025 (confirmed directly against the NISR SAS 2025 Season A report, section
    2.1, not assumed). A season whose start_month is after its end_month (it wraps across
    a year boundary, e.g. Season A) therefore starts in year - 1, not year. Season B does
    not wrap, so its start year already equals its label year.
    """
    window = season_windows[season]
    start_month = window["start_month"]
    end_month = window["end_month"]
    start_year = year - 1 if start_month > end_month else year
    start_date = f"{start_year}-{start_month:02d}-01"
    end_year = start_year + 1 if end_month < start_month else start_year
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

    Same year-alignment rule as season_date_range: a wrapping season starts in year - 1.
    """
    window = season_windows[season]
    start_month = window["start_month"]
    end_month = window["end_month"]
    start_year = year - 1 if start_month > end_month else year
    start_date = f"{start_year}-{start_month:02d}-01"
    month_index = (start_month - 1) + lead_months
    cutoff_year = start_year + month_index // 12
    cutoff_month = month_index % 12 + 1
    cutoff_date = f"{cutoff_year}-{cutoff_month:02d}-01"
    return start_date, cutoff_date
