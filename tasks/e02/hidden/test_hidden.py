import pytest

from stats import moving_average


def test_two_point_windows_include_last():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_window_larger_than_list_is_empty():
    assert moving_average([1, 2], 3) == []


def test_single_item_window_one():
    assert moving_average([5], 1) == [5.0]


def test_empty_list_is_empty():
    assert moving_average([], 1) == []


def test_window_zero_raises():
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], 0)


def test_negative_window_raises():
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], -1)
