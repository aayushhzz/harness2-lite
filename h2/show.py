import json
import re
from pathlib import Path
from typing import List, Optional

from h2.paths import Paths
from h2.trace import StepIndex, condense

DECISION_RE = re.compile(r"^# decision (\S+) (merge|revise|reject) applied=(true|false) source=(\S+) cites=(\S+) reason=(.*)$")


class ShowError(Exception):
    pass


def resolve_run_dir(paths: Paths, task_id: str, arm: Optional[str]) -> Path:
    if arm:
        return paths.runs_dir / "eval" / task_id / arm
    direct = paths.runs_dir / task_id
    if direct.exists():
        return direct
    return paths.runs_dir / "eval" / task_id / "pppc_lib"


def render_show(paths: Paths, task_id: str, arm: Optional[str] = None) -> str:
    run_dir = resolve_run_dir(paths, task_id, arm)
    diff_path = run_dir / "composed.diff"
    if not diff_path.exists():
        raise ShowError(f"no composed.diff in {run_dir}; run `h2 run --tasks {task_id}` or pick --arm")
    text = diff_path.read_text(encoding="utf-8")
    log, _, diff = text.partition("# end log\n")
    try:
        shown_dir = run_dir.relative_to(paths.root)
    except ValueError:
        shown_dir = run_dir
    out = [f"TASK {task_id}  ({shown_dir})"]

    contrast = {}
    cpath = run_dir / "contrast.json"
    if cpath.exists():
        contrast = json.loads(cpath.read_text(encoding="utf-8")).get("candidates", {})
    for scope in ("invariant", "domain"):
        c = contrast.get(scope)
        if c is None or "skipped" in c:
            reason = c.get("skipped", "not proposed") if c else "not proposed"
            out.append(f"{scope:<9} [skipped]: {reason}")
        else:
            out.append(f"{scope:<9} [{c.get('label')}]: {c.get('targeted_deficiency', '')}")

    index = StepIndex(run_dir)
    for ln in log.splitlines():
        m = DECISION_RE.match(ln)
        if not m:
            continue
        hunk, decision, applied, source, cites, reason = m.groups()
        status = "applied" if applied == "true" else "not applied"
        out.append(f"--- decision {hunk}: {decision.upper()} ({status}, source={source})")
        out.append(f"  reason: {reason}")
        for sid in cites.split(","):
            if index.valid(sid):
                out.append(f"  evidence: {condense([index.get(sid)])}")
            else:
                out.append(f"  evidence: {sid} (not found in logs)")
    out.append("--- diff")
    out.append(diff.rstrip("\n") if diff.strip() else "(no changes applied)")
    return "\n".join(out) + "\n"
