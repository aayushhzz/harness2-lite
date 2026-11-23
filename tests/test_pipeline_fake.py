import json
import re
import sys
import tempfile
from pathlib import Path

import pytest

from h2.backends import BackendError
from h2.cli import main
from h2.library import Library
from h2.paths import Paths
from h2.ppc import run_ppc
from h2.tasks import load_task
from h2.trace import StepIndex

LOG_RE = re.compile(r"^# decision (\S+) (merge|revise|reject) applied=(true|false) source=(\S+) cites=(\S+) reason=(.*)$")


class CountingBackend:
    name = "counting"

    def __init__(self, inner):
        self.inner = inner
        self.agent_calls = []

    def complete(self, *a, **k):
        return self.inner.complete(*a, **k)

    def run_agent(self, run_name, *a, **k):
        self.agent_calls.append(run_name)
        return self.inner.run_agent(run_name, *a, **k)


def _run(paths, fake, cfg, tid, base_h, library=None, reflect=False, reference=None):
    task = load_task(paths, tid)
    run_dir = paths.runs_dir / tid
    return run_ppc(task, base_h, fake, cfg, run_dir, library=library, reflect_enabled=reflect,
                   execute_final=True, reference=reference)


def test_ppc_single_task_artifacts(paths, fake, cfg, base_h):
    res = _run(paths, fake, cfg, "e01", base_h)
    d = paths.runs_dir / "e01"
    for name in ("reference.jsonl", "candidate_invariant.jsonl", "candidate_domain.jsonl", "contrast.json",
                 "composed.diff", "compose.json", "composed.jsonl", "prompts/propose_invariant.txt", "DONE"):
        assert (d / name).exists(), name
    assert "FAKE_VERIFY" in (d / "composed.diff").read_text(encoding="utf-8")
    contrast = json.loads((d / "contrast.json").read_text(encoding="utf-8"))["candidates"]
    assert contrast["invariant"]["label"] == "mitigated"
    assert contrast["domain"]["label"] == "unchanged"
    assert res.labels == {"invariant": "mitigated", "domain": "unchanged"}
    assert res.merged == ["inv-1"] and res.tokens_improve > 0 and res.tokens_final > 0


def test_every_compose_decision_cites_existing_step(paths, fake, cfg, base_h):
    _run(paths, fake, cfg, "e01", base_h)
    d = paths.runs_dir / "e01"
    idx = StepIndex(d)
    decisions = [ln for ln in (d / "composed.diff").read_text(encoding="utf-8").splitlines()
                 if ln.startswith("# decision")]
    assert decisions
    for ln in decisions:
        m = LOG_RE.match(ln)
        assert m, ln
        cites = m.group(5).split(",")
        assert cites and all(idx.valid(c) for c in cites)


def test_library_lessons_retrieved_for_later_task(paths, fake, cfg, base_h):
    lib = Library(paths.library_dir)
    _run(paths, fake, cfg, "e01", base_h, library=lib, reflect=True)
    _run(paths, fake, cfg, "e02", base_h, library=lib, reflect=True)
    prompt = (paths.runs_dir / "e02" / "prompts" / "propose_invariant.txt").read_text(encoding="utf-8")
    assert "## LIBRARY LESSONS (retrieved: e01" in prompt
    assert "LESSON e01" in prompt
    assert (paths.library_dir / "e01" / "EXPERIENCE.md").exists()
    assert (paths.library_dir / "index.json").exists()


def test_pipeline_never_imports_oracle(paths, fake, cfg, base_h, monkeypatch):
    monkeypatch.setitem(sys.modules, "h2.oracle", None)
    monkeypatch.setitem(sys.modules, "h2.evalrun", None)
    lib = Library(paths.library_dir)
    for tid in ("e01", "e02"):
        _run(paths, fake, cfg, tid, base_h, library=lib, reflect=True)
    assert (paths.runs_dir / "e02" / "DONE").exists()


def test_resume_skips_done_tasks(paths, capsys):
    root = str(paths.root if False else paths.runs_dir.parent)
    assert main(["--backend", "fake", "--root", root, "run", "--tasks", "e01"]) == 0
    capsys.readouterr()
    assert main(["--backend", "fake", "--root", root, "run", "--tasks", "e01"]) == 0
    assert "skip e01 (done)" in capsys.readouterr().out


def test_probe_temp_workspaces_cleaned(paths, fake, cfg, base_h, monkeypatch, tmp_path):
    tmp = tmp_path / "tmpdir"
    tmp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    _run(paths, fake, cfg, "e01", base_h)
    assert list(tmp.glob("h2-ws-*")) == []

    class Boom(CountingBackend):
        def run_agent(self, *a, **k):
            raise BackendError("boom")
    with pytest.raises(BackendError):
        _run(paths.__class__(**{**paths.__dict__, "runs_dir": paths.runs_dir / "boom"}), Boom(fake), cfg, "e02",
             base_h)
    assert list(tmp.glob("h2-ws-*")) == []


def test_reference_reuse_copies_files_and_does_not_rerun_agent(paths, fake, cfg, base_h):
    first = _run(paths, fake, cfg, "e01", base_h)
    ref_dir = paths.runs_dir / "e01"
    counting = CountingBackend(fake)
    task = load_task(paths, "e01")
    run_ppc(task, base_h, counting, cfg, paths.runs_dir / "e01_reuse", library=None, reflect_enabled=False,
            execute_final=True, reference=ref_dir)
    assert counting.agent_calls == ["candidate_invariant", "candidate_domain", "composed"]
    assert (paths.runs_dir / "e01_reuse" / "reference.jsonl").exists()
    assert first.labels == {"invariant": "mitigated", "domain": "unchanged"}
