import json

from h2.contrast import contrast
from h2.harness import Edit
from h2.paths import Paths
from h2.tasks import load_task
from support import REF_STEPS, ScriptBackend, make_prop, make_rec, steps_for, write_jsonl
from h2.trace import make_step

CONTRAST_OK = {"targeted_deficiency": "no test", "observed_change": "candidate ran tests",
               "label": "mitigated", "regression": False, "cited_steps": ["candidate_invariant:s1"]}


def _setup(tmp_path, with_domain=True):
    task = load_task(Paths.default(), "e01")
    run_dir = tmp_path / "runs" / "e01"
    ref = steps_for("reference", REF_STEPS)
    cand = steps_for("candidate_invariant", [("run_shell", {"cmd": "python3 -m pytest -q t.py"}, "ok", False),
                                             ("final", {}, "done", False)])
    write_jsonl(run_dir / "reference.jsonl", ref)
    write_jsonl(run_dir / "candidate_invariant.jsonl", cand)
    ref_rec = make_rec("reference", ref, diff="")
    cand_rec = make_rec("candidate_invariant", cand, diff="")
    prop = make_prop("invariant", [Edit("inv-1", "invariant", "guardrails.md", "append", "", "- x")],
                     deficiency="never tests")
    return task, run_dir, ref, ref_rec, cand_rec, prop


def test_label_enum_enforced_via_retry(tmp_path):
    task, run_dir, ref, ref_rec, cand_rec, prop = _setup(tmp_path)
    be = ScriptBackend({"contrast": [dict(CONTRAST_OK, label="great"), CONTRAST_OK]})
    res = contrast(task, {"invariant": prop, "domain": None}, ref_rec, {"invariant": cand_rec}, be, None, run_dir)
    assert res["candidates"]["invariant"]["label"] == "mitigated"
    assert len(be.calls) == 2


def test_regression_coerced_from_label(tmp_path):
    task, run_dir, ref, ref_rec, cand_rec, prop = _setup(tmp_path)
    be = ScriptBackend({"contrast": [dict(CONTRAST_OK, label="regressed", regression=False)]})
    res = contrast(task, {"invariant": prop, "domain": None}, ref_rec, {"invariant": cand_rec}, be, None, run_dir)
    c = res["candidates"]["invariant"]
    assert c["label"] == "regressed" and c["regression"] is True


def test_invalid_cites_replaced_by_code_fallback_and_flagged(tmp_path):
    task, run_dir, ref, ref_rec, cand_rec, prop = _setup(tmp_path)
    be = ScriptBackend({"contrast": [dict(CONTRAST_OK, cited_steps=["candidate_invariant:s77"])]})
    res = contrast(task, {"invariant": prop, "domain": None}, ref_rec, {"invariant": cand_rec}, be, None, run_dir)
    c = res["candidates"]["invariant"]
    assert c["cites_source"] == "code_fallback" and c["cited_steps"]
    assert all(cid in ("reference:s1", "reference:s2", "reference:s3", "candidate_invariant:s1",
                       "candidate_invariant:s2") for cid in c["cited_steps"])


def test_llm_failure_defaults_unchanged_with_cites(tmp_path):
    task, run_dir, ref, ref_rec, cand_rec, prop = _setup(tmp_path)
    be = ScriptBackend({"contrast": ["not json", "still not json"]})
    res = contrast(task, {"invariant": prop, "domain": None}, ref_rec, {"invariant": cand_rec}, be, None, run_dir)
    c = res["candidates"]["invariant"]
    assert c["label"] == "unchanged" and c["regression"] is False and c["llm_failed"] is True
    assert c["observed_change"] == "contrast call failed" and c["cites_source"] == "code_fallback"
    assert c["cited_steps"]


def test_skipped_candidate_recorded(tmp_path):
    task, run_dir, ref, ref_rec, cand_rec, prop = _setup(tmp_path)
    be = ScriptBackend({"contrast": [CONTRAST_OK]})
    res = contrast(task, {"invariant": prop, "domain": None}, ref_rec, {"invariant": cand_rec}, be, None, run_dir)
    assert "skipped" in res["candidates"]["domain"]


def test_contrast_json_schema_keys(tmp_path):
    task, run_dir, ref, ref_rec, cand_rec, prop = _setup(tmp_path)
    be = ScriptBackend({"contrast": [CONTRAST_OK]})
    contrast(task, {"invariant": prop, "domain": None}, ref_rec, {"invariant": cand_rec}, be, None, run_dir)
    data = json.loads((run_dir / "contrast.json").read_text(encoding="utf-8"))
    assert data["task"] == "e01"
    keys = {"scope", "targeted_deficiency", "observed_change", "label", "regression", "cited_steps",
            "cites_source", "signals_reference", "signals_candidate", "signal_deltas"}
    assert keys <= set(data["candidates"]["invariant"])
