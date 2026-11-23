import pytest

from stats2 import median


def test_odd_length_middle_value():
    assert median([3, 1, 2]) == 2


def test_even_length_mean_of_middles():
    assert median([1, 2, 3, 4]) == 2.5


def test_even_length_unsorted():
    assert median([10, 2, 8, 4]) == 6.0


def test_input_not_mutated():
    data = [5, 1, 3]
    median(data)
    assert data == [5, 1, 3]


def test_empty_raises():
    with pytest.raises(ValueError):
        median([])


def test_single_value():
    assert median([7]) == 7
