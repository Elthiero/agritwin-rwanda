from agritwin.gee.periods import partial_season_date_range, season_date_range

SEASON_WINDOWS = {
    "A": {"start_month": 9, "end_month": 2},
    "B": {"start_month": 3, "end_month": 6},
}


def test_season_b_stays_within_one_year():
    start, end = season_date_range(2024, "B", SEASON_WINDOWS)
    assert start == "2024-03-01"
    assert end == "2024-07-01"


def test_season_b_start_year_unaffected_by_the_season_a_fix():
    # Regression guard for the Season A year-alignment fix below: Season B does not
    # cross a calendar-year boundary, so its start year must stay equal to its label
    # year, not shift by one like Season A's does.
    start, end = season_date_range(2024, "B", SEASON_WINDOWS)
    assert start == "2024-03-01"
    assert end == "2024-07-01"


def test_season_a_year_label_starts_in_the_previous_calendar_year():
    # "SAS 2025 Season A" was sown around September 2024 and collected December 2024
    # to February 2025 (confirmed against the NISR SAS 2025 Season A report, section
    # 2.1: data collection ran December 1, 2024 to February 15, 2025). NISR labels a
    # season by the calendar year it concludes in, not the one it starts in, so
    # season_date_range(2025, "A", ...) must start in 2024, not 2025.
    start, end = season_date_range(2025, "A", SEASON_WINDOWS)
    assert start == "2024-09-01"
    assert end == "2025-03-01"


def test_end_month_december_rolls_into_january():
    windows = {"C": {"start_month": 11, "end_month": 12}}
    start, end = season_date_range(2024, "C", windows)
    assert start == "2024-11-01"
    assert end == "2025-01-01"


def test_partial_season_a_two_months_starts_in_the_previous_calendar_year():
    start, cutoff = partial_season_date_range(2025, "A", SEASON_WINDOWS, lead_months=2)
    assert start == "2024-09-01"
    assert cutoff == "2024-11-01"


def test_partial_season_a_four_months_wraps_into_the_label_year():
    start, cutoff = partial_season_date_range(2025, "A", SEASON_WINDOWS, lead_months=4)
    assert start == "2024-09-01"
    assert cutoff == "2025-01-01"


def test_partial_season_b_full_length_matches_season_date_range():
    partial_start, partial_cutoff = partial_season_date_range(
        2024, "B", SEASON_WINDOWS, lead_months=4
    )
    full_start, full_end = season_date_range(2024, "B", SEASON_WINDOWS)
    assert (partial_start, partial_cutoff) == (full_start, full_end)
