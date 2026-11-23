import pytest

from h2.harness import (Edit, apply_edits, diff_harness, load_harness, mentions_task_specifics,
                        render_system_prompt, save_harness)
from h2.paths import Config, Paths
from h2.tasks import load_task


def E(path, op, old="", new="", scope="invariant", hunk="x"):
    return Edit(hunk_id=hunk, scope=scope, path=path, op=op, old=old, new=new)


def test_load_render_roundtrip(base_h, tmp_path):
    text = render_system_prompt(base_h)
    assert text.index("# System") < text.index("# Guardrails") < text.index("# Tool guidance")
    assert "ignored by the agent" not in text
    h = dict(base_h)
    h["skills/x.md"] = "do x"
    assert "\n## x\ndo x" in render_system_prompt(h)
    save_harness(h, tmp_path / "h")
    assert load_harness(tmp_path / "h") == h


def test_apply_edits_each_op(base_h):
    edits = [
        E("guardrails.md", "append", new="- new rule"),
        E("system.md", "replace", old="coding agent", new="careful coding agent"),
        E("skills/bugfix.md", "create", new="# Bugs\nreproduce", scope="domain"),
    ]
    out, res = apply_edits(base_h, edits, Config())
    assert [r[2] for r in res] == ["ok", "ok", "ok"]
    assert out["guardrails.md"].endswith("- new rule\n")
    assert "careful coding agent" in out["system.md"]
    assert out["skills/bugfix.md"] == "# Bugs\nreproduce\n"


@pytest.mark.parametrize("edit, reason", [
    (E("../x.md", "append", new="a"), "path_not_allowed"),
    (E("skills/_placeholder.md", "replace", old="Skills", new="Y", scope="domain"), "path_not_allowed"),
    (E("skills/Bad Name.md", "create", new="z", scope="domain"), "path_not_allowed"),
    (E("guardrails.md", "append", new="a" * 1201), "too_long"),
    (E("system.md", "replace", old="NOT THERE", new="z"), "old_not_found"),
    (E("guardrails.md", "replace", old="- ", new="z"), "old_ambiguous"),
    (E("system.md", "replace", old="", new="z"), "old_empty"),
    (E("guardrails.md", "create", new="z", scope="domain"), "exists"),
    (E("skills/new.md", "replace", old="b", new="a", scope="domain"), "file_missing"),
    (E("system.md", "replace", old="bug report", new="bug report"), "noop"),
])
def test_apply_edits_failures(base_h, edit, reason):
    out, res = apply_edits(base_h, [edit], Config())
    assert res[0][1] is False and res[0][2] == reason
    assert out == base_h


def test_failed_edit_does_not_block_later_edits(base_h):
    bad = E("system.md", "replace", old="NOT THERE", new="z")
    good = E("guardrails.md", "append", new="- extra")
    out, res = apply_edits(base_h, [bad, good], Config())
    assert [r[2] for r in res] == ["old_not_found", "ok"]
    assert "- extra" in out["guardrails.md"]


def test_diff_harness_is_valid_unified_diff(base_h):
    h = dict(base_h)
    h["system.md"] = h["system.md"] + " more"
    d = diff_harness(base_h, h)
    assert d.startswith("--- a/system.md")
    assert "+++ b/system.md" in d
    h2 = dict(base_h)
    h2["skills/new.md"] = "x\n"
    assert "--- /dev/null" in diff_harness(base_h, h2)
    assert diff_harness(base_h, dict(base_h)) == ""


def test_mentions_task_specifics():
    task = load_task(Paths.default(), "e01")
    assert mentions_task_specifics("fix textutil.py now", task)
    assert mentions_task_specifics("this concerns e01", task)
    assert not mentions_task_specifics("write and run a small test before finishing", task)


def test_diff_keeps_lines_apart_when_file_lacks_final_newline():
    d = diff_harness({"a.md": "one"}, {"a.md": "two"})
    assert "-one\n+two\n" in d
    assert "-one+two" not in d


def test_condense_is_one_line_per_step_even_with_multiline_args():
    from h2.trace import condense, make_step
    s = make_step("r", 1, "write_file", {"path": "x.py", "content": "a\nb"}, "wrote 3 chars", False)
    out = condense([s])
    assert out.count("\n") == 0 and "content=a\\nb" in out
