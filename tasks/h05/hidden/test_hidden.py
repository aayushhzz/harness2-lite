import pytest

from semver import compare


def test_numeric_not_lexicographic():
    assert compare("1.10.0", "1.9.0") == 1
    assert compare("2", "10") == -1


def test_missing_parts_count_as_zero():
    assert compare("1.0", "1.0.0") == 0
    assert compare("1.0.0", "1.0") == 0
    assert compare("1.2", "1.2.1") == -1


def test_equal_versions():
    assert compare("3.4.5", "3.4.5") == 0


def test_less_and_greater():
    assert compare("0.9.9", "1.0.0") == -1
    assert compare("1.0.1", "1.0.0") == 1


def test_non_numeric_part_raises():
    with pytest.raises(ValueError):
        compare("1.x.0", "1.0.0")


def test_empty_part_raises():
    with pytest.raises(ValueError):
        compare("1..0", "1.0.0")
