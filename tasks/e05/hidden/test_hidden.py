import pytest

from app import is_enabled
from config import parse_bool


def test_true_spellings():
    assert parse_bool("true") is True
    assert parse_bool(" YES ") is True
    assert parse_bool("1") is True
    assert parse_bool("On") is True


def test_false_spellings():
    assert parse_bool("false") is False
    assert parse_bool("0") is False
    assert parse_bool("") is False
    assert parse_bool("  off ") is False


def test_unknown_text_raises():
    with pytest.raises(ValueError):
        parse_bool("maybe")


def test_missing_key_uses_default():
    assert is_enabled({}, "x") is False
    assert is_enabled({}, "x", True) is True


def test_string_values_are_parsed():
    assert is_enabled({"flag": "false"}, "flag", True) is False
    assert is_enabled({"flag": "yes"}, "flag") is True


def test_real_bools_are_used_directly():
    assert is_enabled({"flag": True}, "flag") is True
    assert is_enabled({"flag": False}, "flag", True) is False
