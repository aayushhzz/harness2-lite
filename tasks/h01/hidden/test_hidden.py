from titles import title_case


def test_small_words_stay_lower_inside_title():
    assert title_case("the lord of the rings") == "The Lord of the Rings"


def test_small_words_at_edges_are_capitalised():
    assert title_case("war and peace in") == "War and Peace In"


def test_whitespace_collapses():
    assert title_case("  hello    big   world  ") == "Hello Big World"


def test_empty_string():
    assert title_case("") == ""


def test_single_small_word():
    assert title_case("the") == "The"


def test_mixed_case_input_is_normalised():
    assert title_case("tHE cAT in THE hat") == "The Cat in the Hat"
