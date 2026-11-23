import json
import re

from h2.compose import compose
from h2.harness import Edit
from h2.paths import Config, Paths
from h2.tasks import load_task
from h2.trace import StepIndex
from support import REF_STEPS, ScriptBackend, make_prop, make_rec, steps_for, write_jsonl

LOG_RE = re.compile(r"^# decision (\S+) (merge|revise|reject) applied=(true|false) source=(\S+) cites=(\S+) reason=(.*)$")


def _setup(tmp_path, base_h, inv_label="mitigated", dom_label="regressed", inv_old="- Do not delete files.",
           dom_old="- Do not delete files.", inv_new="- inv rule", dom_new="- dom rule", two_scopes=True):
    task = load_task(Paths.default(), "e01")
    run_dir = tmp_path / "runs" / "e01"
    ref = steps_for("reference", REF_STEPS)
    cand_i = steps_for("candidate_invariant", [("write_file", {"path": "guardrails.md", "content": "x"}, "ok", False),
                                               ("final", {}, "d", False)])
    cand_d = steps_for("candidate_domain", [("run_shell", {"cmd": "ls"}, "a", True),
                                            ("final", {}, "d", False)])
    write_jsonl(run_dir / "reference.jsonl", ref)
    write_jsonl(run_dir / "candidate_invariant.jsonl", cand_i)
    write_jsonl(run_dir / "candidate_domain.jsonl", cand_d)
    cand_recs = {"invariant": make_rec("candidate_invariant", cand_i), "domain": make_rec("candidate_domain", cand_d)}
    ref_rec = make_rec("reference", ref)
    proposals = {
        "invariant": make_prop("invariant", [Edit("inv-1", "invariant", "guardrails.md", "replace", inv_old, inv_new)]),
        "domain": make_prop("domain", [Edit("dom-1", "domain", "guardrails.md", "replace", dom_old, dom_new)])
        if two_scopes else None,
    }
    contrasts = {"candidates": {
        "invariant": {"label": inv_label, "cited_steps": ["candidate_invariant:s1"]},
        "domain": {"label": dom_label, "cited_steps": ["candidate_domain:s1"]},
    }}
    return task, run_dir, ref_rec, cand_recs, proposals, contrasts


def _run(task, run_dir, base_h, proposals, contrasts, ref_rec, cand_recs, be):
    return compose(task, base_h, proposals, contrasts, ref_rec, cand_recs, [], be, Config(max_steps=8), run_dir)


def _decisions(run_dir):
    return json.loads((run_dir / "compose.json").read_text(encoding="utf-8"))["decisions"]


def test_all_hunks_get_exactly_one_decision(tmp_path, base_h):
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path, base_h)
    be = ScriptBackend({"compose": [{"decisions": [
        {"hunk_id": "inv-1", "decision": "merge", "reason": "ok", "cited_steps": ["candidate_invariant:s1"]},
        {"hunk_id": "dom-1", "decision": "reject", "reason": "no", "cited_steps": ["reference:s1"]},
    ], "summary": "s"}]})
    _run(task, run_dir, base_h, props, con, ref_rec, cand_recs, be)
    ids = [d["hunk_id"] for d in _decisions(run_dir)]
    assert sorted(ids) == ["dom-1", "inv-1"] and len(ids) == len(set(ids))


def test_missing_decision_follows_contrast_label(tmp_path, base_h):
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path, base_h)
    be = ScriptBackend({"compose": [{"decisions": [
        {"hunk_id": "inv-1", "decision": "merge", "reason": "ok", "cited_steps": ["candidate_invariant:s1"]}],
        "summary": "s"}]})
    _run(task, run_dir, base_h, props, con, ref_rec, cand_recs, be)
    dom = [d for d in _decisions(run_dir) if d["hunk_id"] == "dom-1"][0]
    assert dom["decision"] == "reject" and dom["source"] == "regression_guard" or dom["decision"] == "reject"
    assert dom["applied"] is False


def test_invalid_cites_fall_back_to_contrast_cites(tmp_path, base_h):
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path, base_h)
    be = ScriptBackend({"compose": [{"decisions": [
        {"hunk_id": "inv-1", "decision": "merge", "reason": "ok", "cited_steps": ["reference:s999"]}],
        "summary": "s"}]})
    _run(task, run_dir, base_h, props, con, ref_rec, cand_recs, be)
    inv = [d for d in _decisions(run_dir) if d["hunk_id"] == "inv-1"][0]
    assert inv["source"] == "code_fallback" and inv["cites"] == ["candidate_invariant:s1"]


def test_regression_guard_overrides_merge(tmp_path, base_h):
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path, base_h)
    be = ScriptBackend({"compose": [{"decisions": [
        {"hunk_id": "inv-1", "decision": "merge", "reason": "ok", "cited_steps": ["candidate_invariant:s1"]},
        {"hunk_id": "dom-1", "decision": "merge", "reason": "looks good", "cited_steps": ["candidate_domain:s1"]}],
        "summary": "s"}]})
    _run(task, run_dir, base_h, props, con, ref_rec, cand_recs, be)
    dom = [d for d in _decisions(run_dir) if d["hunk_id"] == "dom-1"][0]
    assert dom["decision"] == "reject" and dom["source"] == "regression_guard"
    assert dom["reason"].startswith("guard: contrast flagged regression;")


def test_revise_uses_revised_new_and_length_limit(tmp_path, base_h):
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path, base_h, two_scopes=False)
    be = ScriptBackend({"compose": [{"decisions": [
        {"hunk_id": "inv-1", "decision": "revise", "reason": "r", "cited_steps": ["candidate_invariant:s1"],
         "revised_new": "- revised rule"}], "summary": "s"}]})
    res = _run(task, run_dir, base_h, props, con, ref_rec, cand_recs, be)
    assert "- revised rule" in res.harness["guardrails.md"]
    # too long -> treated as merge with the original text
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path / "b", base_h, two_scopes=False)
    be = ScriptBackend({"compose": [{"decisions": [
        {"hunk_id": "inv-1", "decision": "revise", "reason": "r", "cited_steps": ["candidate_invariant:s1"],
         "revised_new": "x" * 1300}], "summary": "s"}]})
    res = _run(task, run_dir, base_h, props, con, ref_rec, cand_recs, be)
    assert "- inv rule" in res.harness["guardrails.md"]


def test_unknown_hunk_id_ignored(tmp_path, base_h):
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path, base_h)
    be = ScriptBackend({"compose": [{"decisions": [
        {"hunk_id": "zzz-9", "decision": "merge", "reason": "r", "cited_steps": ["reference:s1"]}],
        "summary": "s"}]})
    _run(task, run_dir, base_h, props, con, ref_rec, cand_recs, be)
    assert {d["hunk_id"] for d in _decisions(run_dir)} == {"inv-1", "dom-1"}


def test_apply_failure_marks_applied_false_but_keeps_citations(tmp_path, base_h):
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path, base_h, inv_label="mitigated",
                                                           dom_label="mitigated")
    be = ScriptBackend({"compose": [{"decisions": [
        {"hunk_id": "inv-1", "decision": "merge", "reason": "r", "cited_steps": ["candidate_invariant:s1"]},
        {"hunk_id": "dom-1", "decision": "merge", "reason": "r", "cited_steps": ["candidate_domain:s1"]}],
        "summary": "s"}]})
    _run(task, run_dir, base_h, props, con, ref_rec, cand_recs, be)
    dom = [d for d in _decisions(run_dir) if d["hunk_id"] == "dom-1"][0]
    assert dom["applied"] is False and dom["cites"] == ["candidate_domain:s1"]
    assert "apply_failed:old_not_found" in dom["reason"]


def test_composed_diff_log_format_regex_every_line_matches(tmp_path, base_h):
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path, base_h)
    be = ScriptBackend({"compose": [{"decisions": [
        {"hunk_id": "inv-1", "decision": "merge", "reason": "two\nlines", "cited_steps": ["candidate_invariant:s1"]},
        {"hunk_id": "dom-1", "decision": "reject", "reason": "no", "cited_steps": ["reference:s1"]}],
        "summary": "s"}]})
    _run(task, run_dir, base_h, props, con, ref_rec, cand_recs, be)
    lines = (run_dir / "composed.diff").read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# compose log task=e01 candidates=invariant,domain")
    idx = StepIndex(run_dir)
    decision_lines = [ln for ln in lines if ln.startswith("# decision")]
    assert len(decision_lines) == 2
    for ln in decision_lines:
        m = LOG_RE.match(ln)
        assert m, ln
        cites = m.group(5).split(",")
        assert cites and all(idx.valid(c) for c in cites)
    assert "# end log" in lines


def test_no_hunks_writes_empty_log_and_base_harness(tmp_path, base_h):
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path, base_h)
    res = compose(task, base_h, {"invariant": None, "domain": None}, con, ref_rec, {}, [],
                  ScriptBackend({}), Config(), run_dir)
    assert (run_dir / "composed.diff").read_text(encoding="utf-8") == \
        "# compose log task=e01 candidates=none\n# end log\n"
    assert res.harness == base_h


def test_compose_call_failure_uses_fallback_rule(tmp_path, base_h):
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path, base_h, inv_label="mitigated",
                                                           dom_label="regressed")
    be = ScriptBackend({"compose": ["junk", "junk again"]})
    res = _run(task, run_dir, base_h, props, con, ref_rec, cand_recs, be)
    by = {d["hunk_id"]: d for d in res.decisions}
    assert by["inv-1"]["decision"] == "merge" and by["inv-1"]["source"] == "code_fallback"
    assert by["dom-1"]["decision"] == "reject" and by["dom-1"]["applied"] is False


def test_composed_harness_dir_written(tmp_path, base_h):
    task, run_dir, ref_rec, cand_recs, props, con = _setup(tmp_path, base_h)
    be = ScriptBackend({"compose": [{"decisions": [], "summary": "s"}]})
    _run(task, run_dir, base_h, props, con, ref_rec, cand_recs, be)
    assert (run_dir / "composed_harness" / "system.md").exists()
    assert (run_dir / "composed_harness" / "skills" / "_placeholder.md").exists()
