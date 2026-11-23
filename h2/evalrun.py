"""Held-out evaluation. Only this module and oracle.py may refer to the hidden tests.

Writes hidden-test results only to runs/eval/<task>/summary.json and results.md. The library is opened
read-only and never written.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from h2.harness import load_harness
from h2.library import Library
from h2.oracle import score_hidden
from h2.paths import Config, Paths
from h2.ppc import run_ppc
from h2.probe import probe_candidate
from h2.tasks import list_tasks

ARMS = ("base", "pppc", "pppc_lib")


def _scan_peek(run_dir: Path, name: str) -> bool:
    """Agent bash cannot be sandboxed: flag a run whose steps touched the tasks tree or a hidden path."""
    path = run_dir / f"{name}.jsonl"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    peek = "tasks/" in text or "hidden" in text
    meta_path = run_dir / f"{name}.meta.json"
    if peek and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["oracle_peek"] = True
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return peek


def _arm_stats(meta_path: Path) -> dict:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return {"steps": int(meta.get("steps", 0)), "tool_errors": int(meta.get("tool_errors", 0)),
            "tokens": int(meta.get("tokens", 0))}


def _run_task(paths: Paths, task, backend, cfg: Config, library: Library, base_h: dict) -> dict:
    tdir = paths.runs_dir / "eval" / task.id
    if tdir.exists() and (tdir / "reference_ws").exists():
        shutil.rmtree(tdir / "reference_ws")
    tdir.mkdir(parents=True, exist_ok=True)
    arms: Dict[str, dict] = {}

    # base arm: the reference run itself, scored by the held-out tests
    rec = probe_candidate(task, base_h, backend, cfg, tdir, "reference", keep_workspace=True)
    try:
        res = score_hidden(paths, task.id, rec.workspace)
        shutil.copytree(rec.workspace, tdir / "reference_ws", dirs_exist_ok=True)
    finally:
        if rec.workspace is not None:
            shutil.rmtree(rec.workspace, ignore_errors=True)
    stats = _arm_stats(tdir / "reference.meta.json")
    ref_tokens = stats["tokens"]
    arms["base"] = {"passed": res.passed, "steps": stats["steps"], "tool_errors": stats["tool_errors"],
                    "tokens_run": ref_tokens, "tokens_total": ref_tokens, "oracle_tail": res.tail,
                    "oracle_peek": _scan_peek(tdir, "reference")}

    for arm, lib in (("pppc", None), ("pppc_lib", library)):
        run_dir = tdir / arm
        ppc = run_ppc(task, base_h, backend, cfg, run_dir, library=lib, reflect_enabled=False,
                      execute_final=True, reference=tdir)
        res = score_hidden(paths, task.id, ppc.final_ws)
        stats = _arm_stats(run_dir / "composed.meta.json")
        arms[arm] = {"passed": res.passed, "steps": stats["steps"], "tool_errors": stats["tool_errors"],
                     "tokens_run": stats["tokens"],
                     "tokens_total": ref_tokens + ppc.tokens_improve + ppc.tokens_final,
                     "oracle_tail": res.tail,
                     "oracle_peek": any(_scan_peek(run_dir, n) for n in ("reference", "candidate_invariant",
                                                                          "candidate_domain", "composed"))}
    summary = {"task": task.id, **arms}
    (tdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _pct(k: int, n: int) -> str:
    return f"{k}/{n} ({round(100 * k / n) if n else 0}%)"


def _render(rows: List[dict], backend, cfg: Config, selector: str) -> str:
    n = len(rows)
    worker = getattr(backend, "worker_model", None) or "default"
    editor = getattr(backend, "editor_model", None) or "default"
    lines = [
        "# Harness2-lite results",
        f"backend={backend.name} worker_model={worker} editor_model={editor} tasks={n} "
        f"date={datetime.now().isoformat(timespec='seconds')}",
        "",
        "| Arm | Hidden-test pass | Mean steps | Mean tool errors | Mean tokens (run) | Mean tokens (total) |",
        "|---|---|---|---|---|---|",
    ]
    for arm in ARMS:
        vals = [r[arm] for r in rows if arm in r]
        m = len(vals)
        passed = sum(1 for v in vals if v["passed"])
        mean = (lambda key, fmt: format(sum(v[key] for v in vals) / m, fmt) if m else "0")
        lines.append(f"| {arm} | {_pct(passed, m)} | {mean('steps', '.1f')} | {mean('tool_errors', '.1f')} "
                     f"| {mean('tokens_run', ',.0f')} | {mean('tokens_total', ',.0f')} |")
    lines += ["", "| Task | base | pppc | pppc_lib |", "|---|---|---|---|"]
    for r in rows:
        cells = []
        for arm in ARMS:
            v = r.get(arm)
            cells.append("-" if v is None else f"{'PASS' if v['passed'] else 'FAIL'} ({v['steps']})")
        lines.append(f"| {r['task']} | " + " | ".join(cells) + " |")
    lines += ["", f"Notes: single sample per cell, n={n}; one task of difference is within noise. "
                  "tokens = input + cache_creation + cache_read + output (claude) or prompt_eval_count + eval_count "
                  "(ollama). \"total\" includes reference, propose, probe, contrast, compose and the final run. "
                  "The library is frozen during eval. Cells show steps of the measured run."]
    return "\n".join(lines) + "\n"


def run_eval(paths: Paths, backend, cfg: Config, selector: str = "heldout", limit: Optional[int] = None,
             force: bool = False) -> str:
    tasks = list_tasks(paths, selector)
    if limit:
        tasks = tasks[:limit]
    base_h = load_harness(paths.harness_dir)
    library = Library(paths.library_dir, readonly=True)
    rows = []
    for task in tasks:
        summary_path = paths.runs_dir / "eval" / task.id / "summary.json"
        if summary_path.exists() and not force:
            print(f"skip {task.id} (summary exists)")
            rows.append(json.loads(summary_path.read_text(encoding="utf-8")))
            continue
        summary = _run_task(paths, task, backend, cfg, library, base_h)
        print(f"{task.id} base:{'PASS' if summary['base']['passed'] else 'FAIL'} "
              f"pppc:{'PASS' if summary['pppc']['passed'] else 'FAIL'} "
              f"pppc_lib:{'PASS' if summary['pppc_lib']['passed'] else 'FAIL'}")
        rows.append(summary)
    text = _render(rows, backend, cfg, selector)
    paths.results_path.parent.mkdir(parents=True, exist_ok=True)
    paths.results_path.write_text(text, encoding="utf-8")
    flagged = [r["task"] for r in rows for a in ARMS if a in r and r[a].get("oracle_peek")]
    for t in sorted(set(flagged)):
        print(f"warning: agent bash touched the tasks tree or a hidden path in task {t} (score unchanged)")
    return text
