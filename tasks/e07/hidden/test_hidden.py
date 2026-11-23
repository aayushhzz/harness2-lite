from csvlite import parse_line


def test_quoted_comma_stays_in_field():
    assert parse_line('a,"b,c",d') == ["a", "b,c", "d"]


def test_single_quoted_field():
    assert parse_line('"x"') == ["x"]


def test_empty_line_is_one_empty_field():
    assert parse_line("") == [""]


def test_empty_middle_field():
    assert parse_line("a,,b") == ["a", "", "b"]


def test_doubled_quotes_are_literal_quote():
    assert parse_line('"he said ""hi"""') == ['he said "hi"']


def test_trailing_comma_gives_empty_last_field():
    assert parse_line("a,") == ["a", ""]
