import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from h2.compose import compose
from h2.contrast import contrast
from h2.harness import Harness, apply_edits
from h2.library import Library
from h2.paths import Config
from h2.probe import RunRecord, probe_candidate
from h2.propose import propose
from h2.reflect import reflect
from h2.signals import compute_signals
from h2.tasks import Task
from h2.trace import read_steps


@dataclass
class PPCResult:
    composed_harness: Harness
    tokens_improve: int
    tokens_final: int
    final_rec: Optional[RunRecord]
    final_ws: Optional[Path]
    labels: Dict[str, str]
    merged: List[str]
    lessons_written: int


def _persist_ws(rec: RunRecord, run_dir: Path, name: str) -> Path:
    dest = run_dir / f"{name}_ws"
    if rec.workspace is not None and rec.workspace.exists():
        shutil.copytree(rec.workspace, dest, dirs_exist_ok=True)
        shutil.rmtree(rec.workspace, ignore_errors=True)
        rec.workspace = None
    return dest


def run_ppc(task: Task, base_h: Harness, backend, cfg: Config, run_dir, library: Optional[Library],
            reflect_enabled: bool, execute_final: bool = True, reference: Optional[Path] = None) -> PPCResult:
    run_dir = Path(run_dir)
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    temp_ws: List[RunRecord] = []
    try:
        # 1. reference: reuse a previous run's files, or run it once
        if reference is not None:
            ref_dir = Path(reference)
            for name in ("reference.jsonl", "reference.meta.json", "reference.diff"):
                shutil.copy(ref_dir / name, run_dir / name)
            if (ref_dir / "reference_ws").exists():
                shutil.copytree(ref_dir / "reference_ws", run_dir / "reference_ws", dirs_exist_ok=True)
            ref_steps = read_steps(run_dir / "reference.jsonl")
            ref_meta = json.loads((run_dir / "reference.meta.json").read_text(encoding="utf-8"))
            ref_diff = (run_dir / "reference.diff").read_text(encoding="utf-8")
            ref_signals = compute_signals(ref_steps, ref_meta, ref_diff)
            ref_rec = RunRecord(name="reference", steps=ref_steps, meta=ref_meta, diff=ref_diff,
                                signals=ref_signals, workspace=None)
        else:
            ref_rec = probe_candidate(task, base_h, backend, cfg, run_dir, "reference", keep_workspace=True)
            temp_ws.append(ref_rec)
            _persist_ws(ref_rec, run_dir, "reference")
            temp_ws.remove(ref_rec)

        # 2. library lessons
        lessons = []
        if library is not None:
            query = task.prompt + "\n" + json.dumps(ref_rec.signals, sort_keys=True)
            lessons = library.retrieve(query, cfg.lib_top_k)

        tokens_improve = 0
        # 3. propose
        tok_prop: Dict[str, int] = {}
        proposals = propose(task, base_h, ref_rec.steps, ref_rec.signals, lessons, backend, cfg, run_dir,
                            tokens_out=tok_prop)
        tokens_improve += sum(tok_prop.values())

        # 4. probe candidates
        cand_recs: Dict[str, RunRecord] = {}
        for scope in ("invariant", "domain"):
            prop = proposals.get(scope)
            if prop is None:
                continue
            cand_h, _ = apply_edits(base_h, prop.edits, cfg)
            rec = probe_candidate(task, cand_h, backend, cfg, run_dir, f"candidate_{scope}")
            cand_recs[scope] = rec
            tokens_improve += rec.tokens

        # 5. contrast
        tok_con: Dict[str, int] = {}
        contrasts = contrast(task, proposals, ref_rec, cand_recs, backend, cfg, run_dir, tokens_out=tok_con)
        tokens_improve += sum(tok_con.values())

        # 6. compose
        comp = compose(task, base_h, proposals, contrasts, ref_rec, cand_recs, lessons, backend, cfg, run_dir)
        tokens_improve += comp.tokens

        # 7. execute the composed harness
        final_rec = None
        final_ws = None
        tokens_final = 0
        if execute_final:
            final_rec = probe_candidate(task, comp.harness, backend, cfg, run_dir, "composed", keep_workspace=True)
            temp_ws.append(final_rec)
            final_ws = _persist_ws(final_rec, run_dir, "composed")
            temp_ws.remove(final_rec)
            tokens_final = final_rec.tokens

        # 8. reflect (library only; never on eval runs)
        lessons_written = 0
        if reflect_enabled and library is not None and not library.readonly:
            tok_ref: Dict[str, int] = {}
            entry = reflect(task, contrasts, comp, ref_rec, final_rec, backend, cfg, run_dir, library,
                            tokens_out=tok_ref)
            tokens_improve += sum(tok_ref.values())
            if entry is not None:
                lessons_written = entry.lessons

        labels = {s: c.get("label", "skipped") for s, c in contrasts.get("candidates", {}).items()}
        merged = [d["hunk_id"] for d in comp.decisions if d["applied"] and d["decision"] in ("merge", "revise")]
        (run_dir / "DONE").write_text(json.dumps({
            "task": task.id, "labels": labels, "merged": merged, "tokens_improve": tokens_improve,
            "tokens_final": tokens_final, "lessons_written": lessons_written,
        }, indent=2), encoding="utf-8")
        return PPCResult(composed_harness=comp.harness, tokens_improve=tokens_improve, tokens_final=tokens_final,
                         final_rec=final_rec, final_ws=final_ws, labels=labels, merged=merged,
                         lessons_written=lessons_written)
    finally:
        for rec in temp_ws:
            if rec.workspace is not None:
                shutil.rmtree(rec.workspace, ignore_errors=True)
