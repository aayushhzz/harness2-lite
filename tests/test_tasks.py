import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from h2.paths import Paths
from h2.tasks import all_task_ids, list_tasks, load_task, make_workspace

PATHS = Paths.default()
IDS = ["e01", "e02", "e03", "e04", "e05", "e06", "e07", "e08", "e09", "e10",
       "h01", "h02", "h03", "h04", "h05", "h06"]


def _run_hidden(repo: Path, tid: str, tmp_path: Path) -> int:
    ws = tmp_path / "ws"
    shutil.copytree(repo, ws)
    shutil.copy(PATHS.tasks_dir / tid / "hidden" / "test_hidden.py", ws / "test_hidden.py")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_hidden.py"],
                       cwd=ws, capture_output=True, text=True, timeout=120)
    return r.returncode


def test_counts():
    ids = all_task_ids(PATHS)
    assert sorted(ids) == sorted(IDS)
    assert [t.id for t in list_tasks(PATHS, "evolve")] == [f"e{n:02d}" for n in range(1, 11)]
    assert [t.id for t in list_tasks(PATHS, "heldout")] == [f"h{n:02d}" for n in range(1, 7)]


def test_unknown_selector_raises():
    with pytest.raises(ValueError, match="unknown task: zz"):
        list_tasks(PATHS, "e01,zz")


@pytest.mark.parametrize("tid", IDS)
def test_task_md_hygiene(tid):
    text = (PATHS.tasks_dir / tid / "repo" / "task.md").read_text(encoding="utf-8")
    for bad in ("assert", "hidden", "test_hidden"):
        assert bad not in text
    assert "There are no tests in this repository." in text


@pytest.mark.parametrize("tid", IDS)
def test_buggy_repo_fails_hidden(tid, tmp_path):
    assert _run_hidden(PATHS.tasks_dir / tid / "repo", tid, tmp_path) != 0


@pytest.mark.parametrize("tid", IDS)
def test_golden_passes_hidden(tid, tmp_path):
    ws = tmp_path / "repo"
    shutil.copytree(PATHS.tasks_dir / tid / "repo", ws)
    golden = PATHS.root / "tests" / "golden" / tid
    for p in golden.rglob("*"):
        if p.is_file():
            shutil.copy(p, ws / p.relative_to(golden))
    assert _run_hidden(ws, tid, tmp_path / "run") == 0


@pytest.mark.parametrize("tid", IDS)
def test_hidden_has_at_least_six_asserts(tid):
    tree = ast.parse((PATHS.tasks_dir / tid / "hidden" / "test_hidden.py").read_text(encoding="utf-8"))
    asserts = sum(isinstance(n, ast.Assert) for n in ast.walk(tree))
    raises = sum(isinstance(n, ast.With) for n in ast.walk(tree))
    assert asserts + raises >= 6


@pytest.mark.parametrize("tid", IDS)
def test_workspace_copy_contains_no_hidden_path(tid):
    ws = make_workspace(load_task(PATHS, tid))
    try:
        names = [str(p.relative_to(ws)) for p in ws.rglob("*")]
        assert not any("hidden" in n for n in names)
    finally:
        shutil.rmtree(ws, ignore_errors=True)
