from agritwin.gee.periods import season_date_range

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
