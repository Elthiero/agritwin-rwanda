from agritwin.gee.periods import partial_season_date_range, season_date_range

SEASON_WINDOWS = {
    "A": {"start_month": 9, "end_month": 2},
    "B": {"start_month": 3, "end_month": 6},
}


def test_season_b_stays_within_one_year():
    start, end = season_date_range(2024, "B", SEASON_WINDOWS)
    assert start == "2024-03-01"
    assert end == "2024-07-01"


def test_season_a_wraps_into_next_year():
    start, end = season_date_range(2024, "A", SEASON_WINDOWS)
    assert start == "2024-09-01"
    assert end == "2025-03-01"


def test_end_month_december_rolls_into_january():
    windows = {"C": {"start_month": 11, "end_month": 12}}
    start, end = season_date_range(2024, "C", windows)
    assert start == "2024-11-01"
    assert end == "2025-01-01"


def test_partial_season_a_two_months_stays_within_the_start_year():
    start, cutoff = partial_season_date_range(2024, "A", SEASON_WINDOWS, lead_months=2)
    assert start == "2024-09-01"
    assert cutoff == "2024-11-01"


def test_partial_season_a_four_months_wraps_into_next_year():
    start, cutoff = partial_season_date_range(2024, "A", SEASON_WINDOWS, lead_months=4)
    assert start == "2024-09-01"
    assert cutoff == "2025-01-01"


def test_partial_season_b_full_length_matches_season_date_range():
    partial_start, partial_cutoff = partial_season_date_range(
        2024, "B", SEASON_WINDOWS, lead_months=4
    )
    full_start, full_end = season_date_range(2024, "B", SEASON_WINDOWS)
    assert (partial_start, partial_cutoff) == (full_start, full_end)
