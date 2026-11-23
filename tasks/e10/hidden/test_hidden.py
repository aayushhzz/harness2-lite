from nested import flatten


def test_mixed_nesting_keeps_strings_whole():
    assert flatten([1, [2, [3, "ab"]]]) == [1, 2, 3, "ab"]


def test_empty_list():
    assert flatten([]) == []


def test_tuples_are_flattened():
    assert flatten((1, (2, 3))) == [1, 2, 3]


def test_dicts_kept_whole():
    assert flatten([{"a": [1]}]) == [{"a": [1]}]


def test_deep_nesting():
    x = 7
    for _ in range(50):
        x = [x]
    assert flatten(x) == [7]


def test_only_empty_lists():
    assert flatten([[], [[]]]) == []


def test_bytes_kept_whole():
    assert flatten([b"xy"]) == [b"xy"]
