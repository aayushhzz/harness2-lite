"""Scores a finished workspace against the held-out tests. Only evalrun.py may import this module."""
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from h2.paths import Paths
from h2.tools import child_env


@dataclass
class OracleResult:
    passed: bool
    n_passed: int
    n_failed: int
    tail: str


def score_hidden(paths: Paths, task_id: str, workspace: Path) -> OracleResult:
    test_file = paths.tasks_dir / task_id / "hidden" / "test_hidden.py"
    tmp = Path(tempfile.mkdtemp(prefix="h2-score-"))
    try:
        dst = tmp / "ws"
        shutil.copytree(workspace, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        shutil.copy(test_file, dst / "test_hidden.py")
        try:
            proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_hidden.py"],
                                  cwd=str(dst), capture_output=True, text=True, timeout=60, env=child_env())
        except subprocess.TimeoutExpired:
            return OracleResult(passed=False, n_passed=0, n_failed=0, tail="timeout")
        out = (proc.stdout or "") + (proc.stderr or "")
        lines = [ln for ln in out.splitlines() if ln.strip()]
        last = lines[-1] if lines else ""
        mp = re.search(r"(\d+) passed", last)
        mf = re.search(r"(\d+) failed", last)
        return OracleResult(passed=proc.returncode == 0,
                            n_passed=int(mp.group(1)) if mp else 0,
                            n_failed=int(mf.group(1)) if mf else 0,
                            tail=last[-300:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
