import pytest

from daterange import days_between


def test_inclusive_count():
    assert days_between("2024-01-01", "2024-01-03") == 3


def test_same_day_is_one():
    assert days_between("2024-05-05", "2024-05-05") == 1


def test_reversed_order_same_result():
    assert days_between("2024-01-03", "2024-01-01") == 3


def test_across_leap_day():
    assert days_between("2024-02-28", "2024-03-01") == 3


def test_invalid_format_raises():
    with pytest.raises(ValueError):
        days_between("2024/01/01", "2024-01-02")


def test_invalid_date_raises():
    with pytest.raises(ValueError):
        days_between("2024-02-30", "2024-03-01")
