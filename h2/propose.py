import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from h2.harness import Edit, Harness, apply_edits, diff_harness, mentions_task_specifics
from h2.llmjson import call_json
from h2.paths import Config
from h2.prompts import PROPOSAL_SCHEMA, propose_prompt, propose_system
from h2.trace import Step, StepIndex

OPS = ("append", "replace", "create")


@dataclass
class Proposal:
    scope: str
    targeted_deficiency: str
    rationale: str
    cited_steps: List[str]
    edits: List[Edit]
    dropped: List[Tuple[dict, str]] = field(default_factory=list)
    diff_text: str = ""


def _validate(data: dict) -> None:
    if not isinstance(data.get("targeted_deficiency"), str) or not data["targeted_deficiency"].strip():
        raise ValueError("targeted_deficiency must be a non-empty string")
    cs = data.get("cited_steps")
    if not isinstance(cs, list) or not all(isinstance(x, str) for x in cs):
        raise ValueError("cited_steps must be an array of strings")
    edits = data.get("edits")
    if not isinstance(edits, list) or not edits:
        raise ValueError("edits must be a non-empty array")
    for e in edits:
        if not isinstance(e, dict):
            raise ValueError("each edit must be an object")
        if e.get("op") not in OPS:
            raise ValueError("edit op must be append, replace or create")
        if not isinstance(e.get("path"), str) or not isinstance(e.get("new"), str):
            raise ValueError("edit needs string path and new")
        if "old" in e and e["old"] is not None and not isinstance(e["old"], str):
            raise ValueError("edit old must be a string")


def _edit_dict(e: Edit) -> dict:
    return {"hunk_id": e.hunk_id, "path": e.path, "op": e.op, "new": e.new, "old": e.old}


def propose(task, harness: Harness, ref_steps: List[Step], ref_signals: dict, lessons, backend, cfg: Config,
            run_dir: Path, tokens_out: Optional[dict] = None) -> Dict[str, Optional[Proposal]]:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    index = StepIndex(run_dir)
    out: Dict[str, Optional[Proposal]] = {}
    report: Dict[str, dict] = {}
    for scope in ("invariant", "domain"):
        prefix = "inv" if scope == "invariant" else "dom"
        prompt = propose_prompt(task, harness, ref_steps, ref_signals, lessons, scope)
        data, tokens = call_json(backend, f"propose_{scope}", propose_system(scope), prompt, PROPOSAL_SCHEMA,
                                 _validate, run_dir / "prompts", retries=1)
        if tokens_out is not None:
            tokens_out[scope] = tokens_out.get(scope, 0) + tokens
        dropped: List[Tuple[dict, str]] = []
        if data is None:
            out[scope] = None
            _write_skip(run_dir, scope, "proposal_invalid", dropped)
            report[scope] = {"skipped": "proposal_invalid", "dropped": []}
            continue
        raw_edits = data["edits"][:cfg.max_edits]
        candidates: List[Edit] = []
        for i, e in enumerate(raw_edits, 1):
            edit = Edit(hunk_id=f"{prefix}-{i}", scope=scope, path=e["path"], op=e["op"],
                        old=e.get("old") or "", new=e["new"])
            if scope == "invariant":
                if edit.path.startswith("skills/"):
                    dropped.append((_edit_dict(edit), "scope_violation"))
                    continue
                if mentions_task_specifics(edit.new + "\n" + edit.old, task):
                    dropped.append((_edit_dict(edit), "task_specific"))
                    continue
            candidates.append(edit)
        valid: List[Edit] = []
        cur = dict(harness)
        for edit in candidates:
            nxt, results = apply_edits(cur, [edit], cfg)
            _, ok, reason = results[0]
            if ok:
                valid.append(edit)
                cur = nxt
            else:
                dropped.append((_edit_dict(edit), reason))
        cites = index.filter_valid(data.get("cited_steps", []))
        if not valid:
            out[scope] = None
            _write_skip(run_dir, scope, "no_valid_edits", dropped)
            report[scope] = {"skipped": "no_valid_edits", "dropped": [d for d in dropped]}
            continue
        diff_text = diff_harness(harness, cur)
        prop = Proposal(scope=scope, targeted_deficiency=data["targeted_deficiency"].strip(),
                        rationale=str(data.get("rationale", "")), cited_steps=cites, edits=valid,
                        dropped=dropped, diff_text=diff_text)
        out[scope] = prop
        report[scope] = {"targeted_deficiency": prop.targeted_deficiency, "rationale": prop.rationale,
                         "cited_steps": cites, "edits": [_edit_dict(e) for e in valid],
                         "dropped": [{"edit": d, "reason": r} for d, r in dropped], "diff": diff_text}
    (run_dir / "proposals.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out


def _write_skip(run_dir: Path, scope: str, reason: str, dropped) -> None:
    meta = {"skipped": reason, "dropped": [{"edit": d, "reason": r} for d, r in dropped]}
    (run_dir / f"candidate_{scope}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
