import pytest

from account import Account, InsufficientFunds


def test_withdraw_exact_balance_succeeds():
    a = Account(10)
    assert a.withdraw(10) == 0
    assert a.balance == 0


def test_over_balance_raises_and_keeps_balance():
    a = Account(10)
    with pytest.raises(InsufficientFunds):
        a.withdraw(11)
    assert a.balance == 10


def test_partial_withdraw():
    assert Account(10).withdraw(3) == 7


def test_deposit_adds():
    assert Account(5).deposit(5) == 10


def test_negative_deposit_raises_and_keeps_balance():
    a = Account(5)
    with pytest.raises(ValueError):
        a.deposit(-1)
    assert a.balance == 5


def test_zero_or_negative_withdraw_raises():
    a = Account(5)
    with pytest.raises(ValueError):
        a.withdraw(0)
    with pytest.raises(ValueError):
        a.withdraw(-2)
