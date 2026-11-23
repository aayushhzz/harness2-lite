from cart import add_item, total


def test_calls_without_cart_are_independent():
    a = add_item({"price": 1, "qty": 1})
    b = add_item({"price": 2, "qty": 1})
    assert a == [{"price": 1, "qty": 1}]
    assert b == [{"price": 2, "qty": 1}]


def test_input_cart_is_not_mutated():
    cart = [{"price": 1, "qty": 1}]
    add_item({"price": 5, "qty": 2}, cart)
    assert cart == [{"price": 1, "qty": 1}]


def test_result_is_a_new_list_with_item_appended():
    cart = [{"price": 1, "qty": 1}]
    new = add_item({"price": 5, "qty": 2}, cart)
    assert new is not cart
    assert new == [{"price": 1, "qty": 1}, {"price": 5, "qty": 2}]


def test_total_sums_price_times_qty():
    cart = [{"price": 2.5, "qty": 4}, {"price": 1, "qty": 3}]
    assert total(cart) == 13.0


def test_total_of_empty_cart_is_zero():
    assert total([]) == 0


def test_default_then_explicit_cart_totals():
    c = add_item({"price": 1, "qty": 1})
    d = add_item({"price": 2, "qty": 2}, c)
    assert total(d) == 5
