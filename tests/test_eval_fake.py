import hashlib
import json
from pathlib import Path

from h2.evalrun import run_eval
from h2.library import Library
from h2.ppc import run_ppc
from h2.tasks import load_task


def _tree_hash(root: Path) -> dict:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_eval_three_arms_table(paths, fake, cfg, capsys):
    text = run_eval(paths, fake, cfg, selector="heldout", limit=2)
    assert "| Arm | Hidden-test pass | Mean steps | Mean tool errors | Mean tokens (run) | Mean tokens (total) |" in text
    assert "| base | 0/2 (0%) |" in text
    assert "| pppc | 2/2 (100%) |" in text
    assert "| pppc_lib | 2/2 (100%) |" in text
    assert "| Task | base | pppc | pppc_lib |" in text
    assert paths.results_path.read_text(encoding="utf-8") == text
    for tid in ("h01", "h02"):
        summary = json.loads((paths.runs_dir / "eval" / tid / "summary.json").read_text(encoding="utf-8"))
        assert set(summary) >= {"base", "pppc", "pppc_lib"}
        assert set(summary["pppc"]) >= {"passed", "steps", "tool_errors", "tokens_run", "tokens_total", "oracle_tail"}


def test_eval_does_not_modify_library(paths, fake, cfg, base_h):
    lib = Library(paths.library_dir)
    run_ppc(load_task(paths, "e01"), base_h, fake, cfg, paths.runs_dir / "e01", library=lib,
            reflect_enabled=True, execute_final=True)
    before = _tree_hash(paths.library_dir)
    assert before
    run_eval(paths, fake, cfg, selector="heldout", limit=2)
    assert _tree_hash(paths.library_dir) == before


def test_eval_resume_skips_existing_summary_unless_force(paths, fake, cfg, capsys):
    run_eval(paths, fake, cfg, selector="heldout", limit=1)
    capsys.readouterr()
    run_eval(paths, fake, cfg, selector="heldout", limit=1)
    assert "skip h01 (summary exists)" in capsys.readouterr().out
    run_eval(paths, fake, cfg, selector="heldout", limit=1, force=True)
    assert "skip h01" not in capsys.readouterr().out


def test_hidden_results_only_in_summary_and_results(paths, fake, cfg):
    run_eval(paths, fake, cfg, selector="heldout", limit=2)
    tails = []
    for tid in ("h01", "h02"):
        summary = json.loads((paths.runs_dir / "eval" / tid / "summary.json").read_text(encoding="utf-8"))
        tails += [summary[arm]["oracle_tail"] for arm in ("base", "pppc", "pppc_lib")]
    for p in paths.runs_dir.rglob("*"):
        if not p.is_file() or p.name == "summary.json":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        assert "test_hidden" not in text, str(p)
        for tail in tails:
            assert tail not in text, str(p)
    assert paths.results_path.exists()


def test_tokens_total_includes_improvement(paths, fake, cfg):
    run_eval(paths, fake, cfg, selector="heldout", limit=1)
    summary = json.loads((paths.runs_dir / "eval" / "h01" / "summary.json").read_text(encoding="utf-8"))
    assert summary["pppc"]["tokens_total"] > summary["pppc"]["tokens_run"]
    assert summary["base"]["tokens_total"] == summary["base"]["tokens_run"]
