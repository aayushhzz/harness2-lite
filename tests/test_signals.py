import pytest

from h2.signals import compute_signals, default_cites, signal_deltas
from h2.trace import make_step


def mk(run, n, tool, args, result="", err=False):
    return make_step(run, n, tool, args, result, err)


def test_counts_errors_repeats_ran_tests_edited_files():
    steps = [
        mk("candidate_invariant", 1, "run_shell", {"cmd": "ls"}, "a"),
        mk("candidate_invariant", 2, "run_shell", {"cmd": "ls"}, "a"),
        mk("candidate_invariant", 3, "read_file", {"path": "x"}, "nope", True),
        mk("candidate_invariant", 4, "write_file", {"path": "x.py", "content": "c"}, "wrote 1 chars"),
        mk("candidate_invariant", 5, "run_shell", {"cmd": "python3 -m pytest -q test_mine.py"}, "ok"),
        mk("candidate_invariant", 6, "final", {}, "done"),
    ]
    s = compute_signals(steps, {"tokens": 7}, "")
    assert s["n_steps"] == 5 and s["tool_errors"] == 1 and s["repeated_calls"] == 1
    assert s["ran_tests"] is True and s["edited_files"] == ["x.py"]
    assert s["finished"] is True and s["tokens"] == 7


@pytest.mark.parametrize("cmd, expected", [
    ("pytest -q", True), ("python3 -m unittest", True), ("python test_x.py", True), ("ls", False),
])
def test_ran_tests_regex_variants(cmd, expected):
    steps = [mk("reference", 1, "run_shell", {"cmd": cmd}, ""), mk("reference", 2, "final", {}, "d")]
    assert compute_signals(steps, {}, "")["ran_tests"] is expected


def test_diff_lines_counts_only_changes():
    diff = "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new\n+\n \n"
    steps = [mk("reference", 1, "final", {}, "d")]
    assert compute_signals(steps, {}, diff)["diff_lines"] == 2


def test_default_cites_never_empty_even_for_single_step_runs():
    single = [mk("reference", 1, "final", {}, "done")]
    cites = default_cites(single, single)
    assert len(cites) >= 1 and cites[0] == "reference:s1"


def test_signal_deltas():
    ref = {"n_steps": 3, "tool_errors": 0, "repeated_calls": 1, "diff_lines": 2, "ran_tests": False,
           "edited_files": ["a.py"]}
    cand = {"n_steps": 5, "tool_errors": 1, "repeated_calls": 0, "diff_lines": 4, "ran_tests": True,
            "edited_files": ["b.py"]}
    d = signal_deltas(ref, cand)
    assert d["n_steps"] == 2 and d["tool_errors"] == 1 and d["repeated_calls"] == -1 and d["diff_lines"] == 2
    assert d["ran_tests_changed"] is True
    assert d["files_changed"] == {"only_candidate": ["b.py"], "only_reference": ["a.py"]}
