import pytest

from ringbuffer import RingBuffer


def test_fill_without_wrap():
    rb = RingBuffer(3)
    rb.push(1)
    rb.push(2)
    assert rb.to_list() == [1, 2]
    assert len(rb) == 2


def test_exactly_full():
    rb = RingBuffer(3)
    for x in (1, 2, 3):
        rb.push(x)
    assert rb.to_list() == [1, 2, 3]


def test_wrap_once_overwrites_oldest():
    rb = RingBuffer(3)
    for x in (1, 2, 3, 4):
        rb.push(x)
    assert rb.to_list() == [2, 3, 4]


def test_wrap_twice():
    rb = RingBuffer(3)
    for x in range(1, 8):
        rb.push(x)
    assert rb.to_list() == [5, 6, 7]
    assert len(rb) == 3


def test_capacity_one():
    rb = RingBuffer(1)
    rb.push("a")
    rb.push("b")
    assert rb.to_list() == ["b"]


def test_capacity_must_be_positive():
    with pytest.raises(ValueError):
        RingBuffer(0)
