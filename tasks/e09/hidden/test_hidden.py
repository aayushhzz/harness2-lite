import pytest

from wordcount import count_words, top_n


def test_case_and_punctuation_normalised(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text('The cat. The "cat" (sat)! the end', encoding="utf-8")
    assert count_words(str(p)) == {"the": 3, "cat": 2, "sat": 1, "end": 1}


def test_top_n_order_and_limit(tmp_path):
    p = tmp_path / "b.txt"
    p.write_text("b a b c a b", encoding="utf-8")
    assert top_n(str(p), 2) == [("b", 3), ("a", 2)]
    assert top_n(str(p), 1) == [("b", 3)]


def test_top_n_ties_alphabetical(tmp_path):
    p = tmp_path / "c.txt"
    p.write_text("zeta alpha", encoding="utf-8")
    assert top_n(str(p), 5) == [("alpha", 1), ("zeta", 1)]


def test_punctuation_only_tokens_ignored(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("  ...  !!  word  ", encoding="utf-8")
    assert count_words(str(p)) == {"word": 1}


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        count_words("/nonexistent/none.txt")
