import json

from h2.react import run_react


def script(actions):
    it = iter(actions)

    def chat(messages):
        return next(it), 10, 5
    return chat


def test_step_ids_sequential_and_terminal_final(tmp_path):
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    chat = script([json.dumps({"tool": "read_file", "args": {"path": "a.txt"}}),
                   json.dumps({"tool": "final", "args": {"text": "done"}})])
    run = run_react("r", chat, "sys", "task", tmp_path, 5, 30)
    assert [s.id for s in run.steps] == ["r:s1", "r:s2"]
    assert run.steps[-1].tool == "final" and run.final_text == "done"


def test_invalid_json_recorded_as_invalid_step_with_error(tmp_path):
    chat = script(["not json at all", json.dumps({"tool": "final", "args": {"text": "ok"}})])
    run = run_react("r", chat, "sys", "task", tmp_path, 5, 30)
    assert run.steps[0].tool == "invalid" and run.steps[0].is_error
    assert run.steps[0].result == "could not parse action"
    assert run.steps[-1].tool == "final"


def test_step_cap_sets_capped_and_stops(tmp_path):
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    calls = []

    def chat(messages):
        calls.append(1)
        return json.dumps({"tool": "read_file", "args": {"path": "a.txt"}}), 1, 1
    run = run_react("r", chat, "sys", "task", tmp_path, 3, 30)
    assert run.capped is True and run.timed_out is False
    assert len([s for s in run.steps if s.tool != "final"]) == 3
    assert run.steps[-1].tool == "final" and run.steps[-1].result == "step cap reached"
    assert len(calls) == 4


def test_timeout_sets_timed_out_and_terminal_timeout_step(tmp_path):
    run = run_react("r", script([]), "sys", "task", tmp_path, 5, 0)
    assert run.timed_out is True
    assert len(run.steps) == 1 and run.steps[0].tool == "timeout"


def test_tokens_accumulate(tmp_path):
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    chat = script([json.dumps({"tool": "read_file", "args": {"path": "a.txt"}}),
                   json.dumps({"tool": "final", "args": {"text": "x"}})])
    run = run_react("r", chat, "sys", "task", tmp_path, 5, 30)
    assert run.prompt_tokens == 20 and run.completion_tokens == 10 and run.tokens == 30
