import json
from pathlib import Path
from typing import Dict, List, Optional

from h2.library import Library, LibEntry
from h2.llmjson import call_json
from h2.paths import Config
from h2.prompts import REFLECT_SCHEMA, REFLECT_SYSTEM, reflect_prompt
from h2.signals import signal_deltas
from h2.trace import StepIndex, read_steps

LESSON_CHARS = 300
MAX_LESSONS = 4


def _validate(data: dict) -> None:
    for key in ("title", "applies_when"):
        if not isinstance(data.get(key), str):
            raise ValueError(f"{key} must be a string")
    ls = data.get("lessons")
    if not isinstance(ls, list):
        raise ValueError("lessons must be an array")
    for les in ls:
        if not isinstance(les, dict):
            raise ValueError("each lesson must be an object")
        if les.get("kind") not in ("invariant", "domain"):
            raise ValueError("lesson kind must be invariant or domain")
        if les.get("label") not in ("mitigated", "unchanged", "regressed"):
            raise ValueError("lesson label must be mitigated, unchanged or regressed")
        if not isinstance(les.get("text"), str):
            raise ValueError("lesson text must be a string")
        cs = les.get("cited_steps", [])
        if not isinstance(cs, list) or not all(isinstance(x, str) for x in cs):
            raise ValueError("cited_steps must be an array of strings")


def _skip(run_dir: Path, reason: str) -> None:
    (run_dir / "reflect.json").write_text(json.dumps({"skipped": reason}, indent=2), encoding="utf-8")
    return None


def reflect(task, contrasts: dict, compose_result, ref_rec, composed_rec, backend, cfg: Config, run_dir: Path,
            library: Library, tokens_out: Optional[dict] = None) -> Optional[LibEntry]:
    run_dir = Path(run_dir)
    if library.readonly:
        return _skip(run_dir, "library_readonly")
    cands = contrasts.get("candidates", {})
    merged = [d for d in compose_result.decisions if d["applied"] and d["decision"] in ("merge", "revise")]
    no_evidence = all(c.get("skipped") or c.get("label") == "unchanged" for c in cands.values())
    if not merged and no_evidence:
        return _skip(run_dir, "no_supported_evidence")

    ref_steps = read_steps(run_dir / "reference.jsonl")
    comp_steps = read_steps(run_dir / "composed.jsonl") if (run_dir / "composed.jsonl").exists() else None
    deltas = signal_deltas(ref_rec.signals, composed_rec.signals) if composed_rec is not None else None
    merged_ids = [d["hunk_id"] for d in merged]
    log_lines = (run_dir / "composed.diff").read_text(encoding="utf-8").splitlines()
    log = "\n".join(ln for ln in log_lines if ln.startswith("# "))
    prompt = reflect_prompt(task, json.dumps(contrasts, indent=2, sort_keys=True), log, merged_ids, deltas,
                            ref_steps, comp_steps)
    data, tokens = call_json(backend, "reflect", REFLECT_SYSTEM, prompt, REFLECT_SCHEMA, _validate,
                             run_dir / "prompts", retries=1)
    if tokens_out is not None:
        tokens_out["reflect"] = tokens_out.get("reflect", 0) + tokens
    if data is None:
        return _skip(run_dir, "reflect_call_failed")

    index = StepIndex(run_dir)
    kept: List[dict] = []
    dropped: List[dict] = []
    for les in data["lessons"]:
        text = " ".join(les["text"].split())[:LESSON_CHARS]
        cites = index.filter_valid(les.get("cited_steps", []))
        if not text or not cites:
            dropped.append({"text": text, "reason": "no_cited_text" if not text else "no_valid_cites"})
            continue
        kept.append({"kind": les["kind"], "label": les["label"], "text": text, "cited_steps": cites})
    kept = kept[:MAX_LESSONS]
    (run_dir / "reflect_lessons.json").write_text(json.dumps({"kept": kept, "dropped": dropped}, indent=2),
                                                 encoding="utf-8")
    if not kept:
        return _skip(run_dir, "no_cited_lessons")
    entry = library.add_entry(task.id, title=data["title"].strip() or f"{task.id} lessons",
                              applies_when=data["applies_when"].strip() or task.title,
                              lessons=kept, adopted=compose_result.harness, merged_hunks=merged_ids)
    (run_dir / "reflect.json").write_text(json.dumps({"entry": entry.id, "lessons": len(kept),
                                                      "merged_hunks": merged_ids}, indent=2), encoding="utf-8")
    return entry
