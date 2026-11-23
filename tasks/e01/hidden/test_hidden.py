from textutil import slugify


def test_punctuation_collapses_to_one_hyphen():
    assert slugify("Hello, World!") == "hello-world"


def test_whitespace_runs_and_trim():
    assert slugify("  A  B ") == "a-b"


def test_empty_input():
    assert slugify("") == ""


def test_leading_and_trailing_hyphens_removed():
    assert slugify("--x--") == "x"


def test_underscore_is_a_separator():
    assert slugify("a_b") == "a-b"


def test_non_ascii_letters_are_separators():
    assert slugify("Ünï") == "n"
