import json

from h2.library import LibEntry
from h2.paths import Paths
from h2.prompts import propose_prompt
from h2.propose import propose
from h2.tasks import load_task
from support import REF_STEPS, ScriptBackend, edit, steps_for, write_jsonl
from h2.signals import compute_signals


def _setup(tmp_path, paths):
    task = load_task(paths.with_root(tmp_path).__class__.default(), "e01")
    ref = steps_for("reference", REF_STEPS)
    run_dir = tmp_path / "runs" / "e01"
    write_jsonl(run_dir / "reference.jsonl", ref)
    signals = compute_signals(ref, {}, "")
    return task, ref, signals, run_dir


def _prop(**over):
    base = {"targeted_deficiency": "no test run", "rationale": "x", "cited_steps": ["reference:s3", "reference:s99"],
            "edits": []}
    base.update(over)
    return base


def test_edits_become_hunks_with_ids(tmp_path, paths, base_h, cfg):
    task, ref, sig, run_dir = _setup(tmp_path, paths)
    inv = _prop(edits=[{"path": "guardrails.md", "op": "append", "new": "- verify with a test"},
                       {"path": "tool_guidance.md", "op": "append", "new": "- prefer small reads"}])
    dom = _prop(edits=[{"path": "skills/bugfix.md", "op": "create", "new": "# Bugs\nreproduce first"}])
    be = ScriptBackend({"propose_invariant": [inv], "propose_domain": [dom]})
    out = propose(task, base_h, ref, sig, [], be, cfg, run_dir)
    assert [e.hunk_id for e in out["invariant"].edits] == ["inv-1", "inv-2"]
    assert [e.hunk_id for e in out["domain"].edits] == ["dom-1"]


def test_invariant_rejects_skills_path_and_task_specific_text(tmp_path, paths, base_h, cfg):
    task, ref, sig, run_dir = _setup(tmp_path, paths)
    inv = _prop(edits=[{"path": "skills/x.md", "op": "create", "new": "x"},
                       {"path": "guardrails.md", "op": "append", "new": "- check textutil.py carefully"}])
    dom = _prop(edits=[{"path": "guardrails.md", "op": "append", "new": "- domain rule"}])
    be = ScriptBackend({"propose_invariant": [inv], "propose_domain": [dom]})
    out = propose(task, base_h, ref, sig, [], be, cfg, run_dir)
    assert out["invariant"] is None
    meta = json.loads((run_dir / "candidate_invariant.meta.json").read_text(encoding="utf-8"))
    assert meta["skipped"] == "no_valid_edits"
    reasons = {r for _, r in [(d["edit"], d["reason"]) for d in meta["dropped"]] for r in [r]}
    assert reasons == {"scope_violation", "task_specific"}


def test_invalid_edits_dropped_and_recorded(tmp_path, paths, base_h, cfg):
    task, ref, sig, run_dir = _setup(tmp_path, paths)
    dom = _prop(edits=[{"path": "guardrails.md", "op": "replace", "old": "NOT THERE", "new": "z"},
                       {"path": "guardrails.md", "op": "append", "new": "- ok rule"}])
    be = ScriptBackend({"propose_invariant": [_prop(edits=[{"path": "guardrails.md", "op": "append",
                                                             "new": "- inv rule"}])],
                        "propose_domain": [dom]})
    out = propose(task, base_h, ref, sig, [], be, cfg, run_dir)
    assert [e.new for e in out["domain"].edits] == ["- ok rule"]
    assert [r for _, r in out["domain"].dropped] == ["old_not_found"]
    props = json.loads((run_dir / "proposals.json").read_text(encoding="utf-8"))
    assert props["domain"]["dropped"][0]["reason"] == "old_not_found"


def test_no_valid_edits_skips_scope_and_writes_meta(tmp_path, paths, base_h, cfg):
    task, ref, sig, run_dir = _setup(tmp_path, paths)
    dom = _prop(edits=[{"path": "system.md", "op": "replace", "old": "nothing here", "new": "z"}])
    be = ScriptBackend({"propose_invariant": [_prop(edits=[{"path": "guardrails.md", "op": "append",
                                                             "new": "- inv"}])], "propose_domain": [dom]})
    out = propose(task, base_h, ref, sig, [], be, cfg, run_dir)
    assert out["domain"] is None
    meta = json.loads((run_dir / "candidate_domain.meta.json").read_text(encoding="utf-8"))
    assert meta["skipped"] == "no_valid_edits" and meta["dropped"]


def test_cited_steps_filtered_to_existing(tmp_path, paths, base_h, cfg):
    task, ref, sig, run_dir = _setup(tmp_path, paths)
    inv = _prop(edits=[{"path": "guardrails.md", "op": "append", "new": "- verify"}])
    be = ScriptBackend({"propose_invariant": [inv], "propose_domain": [_prop(edits=[
        {"path": "skills/a.md", "op": "create", "new": "x"}])]})
    out = propose(task, base_h, ref, sig, [], be, cfg, run_dir)
    assert out["invariant"].cited_steps == ["reference:s3"]


def test_prompt_headers_and_library_section(tmp_path, paths, base_h):
    task, ref, sig, run_dir = _setup(tmp_path, paths)
    p = propose_prompt(task, base_h, ref, sig, [], "invariant")
    for header in ("TASK_ID: e01", "## TASK", "## CURRENT HARNESS", "=== FILE: system.md ===",
                   "## REFERENCE TRAJECTORY (run: reference)", "## REFERENCE SIGNALS",
                   "## LIBRARY LESSONS (retrieved: none)", "## OUTPUT FORMAT"):
        assert header in p
    entry = LibEntry(id="e01", title="t", applies_when="a", lessons=1, labels={}, path="", created="",
                     keywords=[], text="LESSON e01: write a test")
    p2 = propose_prompt(task, base_h, ref, sig, [entry], "invariant")
    assert "## LIBRARY LESSONS (retrieved: e01)" in p2
    assert "LESSON e01: write a test" in p2


def test_prompt_logged_to_runs_prompts_dir(tmp_path, paths, base_h, cfg):
    task, ref, sig, run_dir = _setup(tmp_path, paths)
    be = ScriptBackend({"propose_invariant": [_prop(edits=[{"path": "guardrails.md", "op": "append",
                                                             "new": "- v"}])],
                        "propose_domain": [_prop(edits=[{"path": "skills/a.md", "op": "create", "new": "x"}])]})
    propose(task, base_h, ref, sig, [], be, cfg, run_dir)
    assert (run_dir / "prompts" / "propose_invariant.txt").exists()
    assert (run_dir / "prompts" / "propose_domain.response.txt").exists()


def test_proposer_prompt_has_no_hidden_or_test_results(tmp_path, paths, base_h):
    task, ref, sig, run_dir = _setup(tmp_path, paths)
    p = propose_prompt(task, base_h, ref, sig, [], "domain")
    assert "test_hidden" not in p and "hidden" not in p
