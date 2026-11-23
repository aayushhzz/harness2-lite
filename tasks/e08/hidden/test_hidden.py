from sorting import sort_people

PEOPLE = [
    {"name": "bob", "age": 30},
    {"name": "Alice", "age": 30},
    {"name": "carol", "age": 41},
    {"name": "dave", "age": 19},
]


def test_age_desc_then_name_asc_ignoring_case():
    out = sort_people(PEOPLE)
    assert [p["name"] for p in out] == ["carol", "Alice", "bob", "dave"]


def test_empty_list():
    assert sort_people([]) == []


def test_input_not_mutated():
    data = [{"name": "b", "age": 1}, {"name": "a", "age": 2}]
    before = [dict(p) for p in data]
    sort_people(data)
    assert data == before


def test_returns_new_list():
    data = [{"name": "b", "age": 1}]
    assert sort_people(data) is not data


def test_same_name_different_case_both_kept():
    data = [{"name": "Zed", "age": 5}, {"name": "zed", "age": 5}]
    assert len(sort_people(data)) == 2


def test_older_first():
    out = sort_people([{"name": "x", "age": 1}, {"name": "y", "age": 9}])
    assert out[0]["name"] == "y"
