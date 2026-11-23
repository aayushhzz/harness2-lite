import pytest

from checkout import total
from pricing import apply_discount


def test_discount_rounds_half_up_from_decimal_text():
    assert apply_discount(19.99, 10) == 17.99
    assert apply_discount(0.05, 50) == 0.03


def test_zero_and_full_discount():
    assert apply_discount(10, 0) == 10.0
    assert apply_discount(10, 100) == 0.0


def test_invalid_pct_raises():
    with pytest.raises(ValueError):
        apply_discount(10, 101)
    with pytest.raises(ValueError):
        apply_discount(10, -1)


def test_total_respects_quantity():
    items = [{"price": 2.0, "qty": 3, "discount_pct": 0}]
    assert total(items) == 6.0


def test_total_mixed_items():
    items = [
        {"price": 19.99, "qty": 2, "discount_pct": 10},
        {"price": 0.05, "qty": 1, "discount_pct": 50},
    ]
    assert total(items) == 36.01


def test_total_empty_is_zero():
    assert total([]) == 0.0
