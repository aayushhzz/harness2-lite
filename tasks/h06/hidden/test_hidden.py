import pytest

from wrap import wrap


def test_greedy_fill():
    assert wrap("the quick brown fox jumps over the lazy dog", 10) == [
        "the quick", "brown fox", "jumps over", "the lazy", "dog",
    ]


def test_exact_width_fits():
    assert wrap("a b c", 3) == ["a b", "c"]


def test_long_word_alone_on_its_line():
    assert wrap("supercalifragilistic is long", 5) == ["supercalifragilistic", "is", "long"]


def test_last_line_is_kept():
    assert wrap("abc", 3) == ["abc"]


def test_whitespace_runs_collapse():
    assert wrap("  spaced   out  ", 20) == ["spaced out"]


def test_empty_text():
    assert wrap("", 5) == []


def test_width_below_one_raises():
    with pytest.raises(ValueError):
        wrap("x", 0)
