import json

import pytest

from h2.compose import ComposeResult
from h2.library import Library
from h2.paths import Paths
from h2.reflect import reflect
from h2.tasks import load_task
from support import REF_STEPS, ScriptBackend, make_rec, steps_for, write_jsonl


def _lesson(text="do the thing", cites=("reference:s1",), label="mitigated", kind="invariant"):
    return {"kind": kind, "label": label, "text": text, "cited_steps": list(cites)}


def test_add_entry_writes_experience_and_index(tmp_path, base_h):
    lib = Library(tmp_path / "lib")
    e = lib.add_entry("e01", "Slug fix", "python bug fix", [_lesson()], base_h, ["inv-1"])
    exp = (tmp_path / "lib" / "e01" / "EXPERIENCE.md").read_text(encoding="utf-8")
    assert exp.startswith("# e01: Slug fix\napplies_when: python bug fix\nmerged_hunks: inv-1\n")
    assert "## Lessons" in exp and "- [invariant|mitigated] do the thing (evidence: reference:s1)" in exp
    index = json.loads((tmp_path / "lib" / "index.json").read_text(encoding="utf-8"))
    assert [x["id"] for x in index["entries"]] == ["e01"]
    assert (tmp_path / "lib" / "e01" / "harness" / "system.md").exists()
    assert e.lessons == 1 and e.labels == {"mitigated": 1}


def test_index_atomic_replace_and_same_task_overwrites(tmp_path, base_h):
    lib = Library(tmp_path / "lib")
    lib.add_entry("e01", "one", "x", [_lesson("first")], base_h, [])
    lib.add_entry("e01", "two", "x", [_lesson("second")], base_h, [])
    assert len(lib.entries()) == 1
    assert "second" in (tmp_path / "lib" / "e01" / "EXPERIENCE.md").read_text(encoding="utf-8")
    assert not (tmp_path / "lib" / "index.json.tmp").exists()


def test_retrieve_ranks_by_overlap_then_recency_and_returns_k(tmp_path, base_h):
    lib = Library(tmp_path / "lib")
    lib.add_entry("e01", "slugify text", "string normalisation", [_lesson("slug lesson")], base_h, [])
    lib.add_entry("e02", "moving average window", "list statistics", [_lesson("window lesson")], base_h, [])
    lib.add_entry("e03", "ring buffer order", "queues", [_lesson("queue lesson")], base_h, [])
    top = lib.retrieve("compute a moving average over a window", 2)
    assert top[0].id == "e02"
    assert len(top) == 2 and top[0].id == "e02"
    assert "window lesson" in top[0].text
    no_overlap = lib.retrieve("zzzzzz", 2)
    assert len(no_overlap) == 2 and no_overlap[0].id == "e03"


def test_retrieve_empty_library(tmp_path):
    assert Library(tmp_path / "none").retrieve("anything at all", 2) == []


def test_corrupt_index_backed_up_and_treated_empty(tmp_path):
    d = tmp_path / "lib"
    d.mkdir()
    (d / "index.json").write_text("{not json", encoding="utf-8")
    lib = Library(d)
    assert lib.entries() == []
    assert (d / "index.json.corrupt").exists() and not (d / "index.json").exists()


def test_readonly_add_raises(tmp_path, base_h):
    with pytest.raises(PermissionError):
        Library(tmp_path / "lib", readonly=True).add_entry("e01", "t", "a", [_lesson()], base_h, [])


def _reflect_setup(tmp_path, base_h, decisions=None, unchanged=False):
    task = load_task(Paths.default(), "e01")
    run_dir = tmp_path / "runs" / "e01"
    ref = steps_for("reference", REF_STEPS)
    cand = steps_for("candidate_invariant", [("final", {}, "d", False)])
    write_jsonl(run_dir / "reference.jsonl", ref)
    write_jsonl(run_dir / "candidate_invariant.jsonl", cand)
    (run_dir / "composed.diff").write_text("# compose log task=e01 candidates=invariant\n"
                                           "# decision inv-1 merge applied=true source=llm cites=candidate_invariant:s1 "
                                           "reason=ok\n# end log\n", encoding="utf-8")
    label = "unchanged" if unchanged else "mitigated"
    contrasts = {"candidates": {"invariant": {"label": label, "cited_steps": ["candidate_invariant:s1"]},
                                "domain": {"skipped": "no_valid_proposal"}}}
    merged = [] if unchanged else [{"hunk_id": "inv-1", "decision": "merge", "applied": True}]
    comp = ComposeResult(harness=base_h, decisions=merged, diff_text="")
    ref_rec = make_rec("reference", ref)
    lib = Library(tmp_path / "lib")
    return task, run_dir, contrasts, comp, ref_rec, lib


def _reflect_reply(lessons):
    return {"title": "T", "applies_when": "python bug fix", "lessons": lessons}


def test_reflect_drops_uncited_lessons(tmp_path, base_h, cfg):
    task, run_dir, contrasts, comp, ref_rec, lib = _reflect_setup(tmp_path, base_h)
    be = ScriptBackend({"reflect": [_reflect_reply([
        {"kind": "invariant", "label": "mitigated", "text": "uncited", "cited_steps": ["reference:s999"]},
        {"kind": "invariant", "label": "mitigated", "text": "cited ok", "cited_steps": ["candidate_invariant:s1"]},
    ])]})
    entry = reflect(task, contrasts, comp, ref_rec, None, be, cfg, run_dir, lib)
    assert entry is not None and entry.lessons == 1
    kept = json.loads((run_dir / "reflect_lessons.json").read_text(encoding="utf-8"))
    assert [k["text"] for k in kept["kept"]] == ["cited ok"]
    assert "uncited" not in (tmp_path / "lib" / "e01" / "EXPERIENCE.md").read_text(encoding="utf-8")


def test_reflect_skips_when_no_supported_evidence(tmp_path, base_h, cfg):
    task, run_dir, contrasts, comp, ref_rec, lib = _reflect_setup(tmp_path, base_h, unchanged=True)
    be = ScriptBackend({})
    assert reflect(task, contrasts, comp, ref_rec, None, be, cfg, run_dir, lib) is None
    assert json.loads((run_dir / "reflect.json").read_text(encoding="utf-8")) == \
        {"skipped": "no_supported_evidence"}
    assert be.calls == []


def test_reflect_skips_when_all_lessons_dropped(tmp_path, base_h, cfg):
    task, run_dir, contrasts, comp, ref_rec, lib = _reflect_setup(tmp_path, base_h)
    be = ScriptBackend({"reflect": [_reflect_reply([
        {"kind": "invariant", "label": "mitigated", "text": "a", "cited_steps": ["reference:s88"]}])]})
    assert reflect(task, contrasts, comp, ref_rec, None, be, cfg, run_dir, lib) is None
    assert json.loads((run_dir / "reflect.json").read_text(encoding="utf-8")) == {"skipped": "no_cited_lessons"}


def test_reflect_readonly_library_skips(tmp_path, base_h, cfg):
    task, run_dir, contrasts, comp, ref_rec, lib = _reflect_setup(tmp_path, base_h)
    ro = Library(tmp_path / "lib", readonly=True)
    assert reflect(task, contrasts, comp, ref_rec, None, ScriptBackend({}), cfg, run_dir, ro) is None


def test_lesson_single_line_and_300_char_cap(tmp_path, base_h, cfg):
    task, run_dir, contrasts, comp, ref_rec, lib = _reflect_setup(tmp_path, base_h)
    long_text = "line one\nline two " + "x" * 500
    be = ScriptBackend({"reflect": [_reflect_reply([
        {"kind": "invariant", "label": "mitigated", "text": long_text, "cited_steps": ["candidate_invariant:s1"]}])]})
    reflect(task, contrasts, comp, ref_rec, None, be, cfg, run_dir, lib)
    lines = (tmp_path / "lib" / "e01" / "EXPERIENCE.md").read_text(encoding="utf-8").splitlines()
    bullet = [ln for ln in lines if ln.startswith("- [")][0]
    text = bullet[len("- [invariant|mitigated] "):].split(" (evidence:")[0]
    assert len(text) <= 300 and "\n" not in text
    assert text.startswith("line one line two")
