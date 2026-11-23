import ast
import dataclasses
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from h2.library import Library
from h2.ppc import run_ppc
from h2.tasks import Task, load_task
from h2.paths import Paths

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "h2"
ALLOWED_FORBIDDEN = {"oracle.py", "evalrun.py", "cli.py"}


def _py_files():
    return sorted(PKG.rglob("*.py"))


def test_forbidden_words_absent():
    pattern = re.compile(r"(?i)hidden|oracle|evalrun")
    for p in _py_files():
        if p.name in ALLOWED_FORBIDDEN:
            continue
        assert not pattern.search(p.read_text(encoding="utf-8")), str(p)


def _imported(tree):
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            for alias in node.names:
                found.add(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
    return found


def test_import_graph():
    for p in _py_files():
        mods = _imported(ast.parse(p.read_text(encoding="utf-8")))
        if "h2.oracle" in mods or "h2.oracle.score_hidden" in mods:
            assert p.name == "evalrun.py", str(p)
        if any(m.startswith("h2.evalrun") for m in mods):
            assert p.name == "cli.py", str(p)


def test_cli_imports_evalrun_lazily():
    code = ("import sys, h2.cli\n"
            "assert 'h2.evalrun' not in sys.modules\n"
            "assert 'h2.oracle' not in sys.modules\n"
            "print('lazy-ok')\n")
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=str(ROOT))
    assert out.returncode == 0, out.stderr
    assert "lazy-ok" in out.stdout


def test_task_loader_does_not_expose_hidden_dir():
    task = load_task(Paths.default(), "e01")
    for f in dataclasses.fields(Task):
        value = getattr(task, f.name)
        assert "hidden" not in str(value), f.name


def test_workspaces_and_prompts_clean(paths, fake, cfg, base_h):
    run_ppc(load_task(paths, "e01"), base_h, fake, cfg, paths.runs_dir / "e01", library=Library(paths.library_dir),
            reflect_enabled=True, execute_final=True)
    for p in (paths.runs_dir / "e01").rglob("*"):
        if not p.is_file() or "_ws" in p.relative_to(paths.runs_dir / "e01").parts[0]:
            continue
        assert "test_hidden" not in p.read_text(encoding="utf-8", errors="replace"), str(p)
