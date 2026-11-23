import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, List, Optional

from h2.harness import Edit, Harness, apply_edits, diff_harness, hunk_diff, save_harness
from h2.llmjson import call_json
from h2.paths import Config
from h2.prompts import COMPOSE_SCHEMA, COMPOSE_SYSTEM, compose_prompt
from h2.trace import StepIndex, condense, read_steps

DECISIONS = ("merge", "revise", "reject")


@dataclass
class ComposeResult:
    harness: Harness
    decisions: List[dict]
    diff_text: str
    tokens: int = 0


def _validate(data: dict) -> None:
    ds = data.get("decisions")
    if not isinstance(ds, list):
        raise ValueError("decisions must be an array")
    for d in ds:
        if not isinstance(d, dict):
            raise ValueError("each decision must be an object")
        if not isinstance(d.get("hunk_id"), str):
            raise ValueError("decision needs hunk_id")
        if d.get("decision") not in DECISIONS:
            raise ValueError("decision must be merge, revise or reject")
        cs = d.get("cited_steps", [])
        if not isinstance(cs, list) or not all(isinstance(x, str) for x in cs):
            raise ValueError("cited_steps must be an array of strings")


def _one_line(text: str, n: int = 200) -> str:
    return " ".join(str(text).split())[:n]


def compose(task, base_h: Harness, proposals: Dict[str, Optional[object]], contrasts: dict, ref_rec, cand_recs,
            lessons, backend, cfg: Config, run_dir: Path) -> ComposeResult:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    scopes = [s for s in ("invariant", "domain") if proposals.get(s) is not None]
    hunks: List[Edit] = []
    for s in scopes:
        hunks.extend(proposals[s].edits)
    cands = contrasts.get("candidates", {})

    if not hunks:
        (run_dir / "composed.diff").write_text(
            f"# compose log task={task.id} candidates=none\n# end log\n", encoding="utf-8")
        (run_dir / "compose.json").write_text(json.dumps({"task": task.id, "decisions": [],
                                                          "summary": "no hunks to compose"}, indent=2),
                                              encoding="utf-8")
        save_harness(base_h, run_dir / "composed_harness")
        return ComposeResult(harness=dict(base_h), decisions=[], diff_text="", tokens=0)

    index = StepIndex(run_dir)
    ref_steps = read_steps(run_dir / "reference.jsonl")
    cand_steps = {s: cand_recs[s].steps for s in scopes if s in cand_recs}
    hunk_lines = []
    for h in hunks:
        label = cands.get(h.scope, {}).get("label", "unchanged")
        hunk_lines.append(f"HUNK {h.hunk_id} | {h.scope} | {h.path} | {h.op} | label={label}")
        hunk_lines.append(hunk_diff(base_h, h).rstrip("\n"))
    prompt = compose_prompt(task, "\n".join(hunk_lines), json.dumps(contrasts, indent=2, sort_keys=True),
                            ref_steps, cand_steps, lessons)
    data, tokens = call_json(backend, "compose", COMPOSE_SYSTEM, prompt, COMPOSE_SCHEMA, _validate,
                             run_dir / "prompts", retries=1)
    llm = {}
    if data is not None:
        hunk_ids = {h.hunk_id for h in hunks}
        for d in data["decisions"]:
            if d["hunk_id"] in hunk_ids and d["hunk_id"] not in llm:
                llm[d["hunk_id"]] = d
    ref_fallback = [ref_steps[-1].id] if ref_steps else []

    resolved = []
    for h in hunks:
        c = cands.get(h.scope, {})
        label = c.get("label", "unchanged")
        contrast_cites = index.filter_valid(c.get("cited_steps", [])) or ref_fallback
        d = llm.get(h.hunk_id)
        revised = None
        if d is not None:
            decision = d["decision"]
            reason = str(d.get("reason", "")).strip() or "no reason given"
            cites = index.filter_valid(d.get("cited_steps", []))
            source = "llm"
            if not cites:
                cites = contrast_cites
                source = "code_fallback"
            if decision == "revise":
                revised = d.get("revised_new")
        else:
            decision = "merge" if label == "mitigated" else "reject"
            reason = "composer omitted this hunk; followed contrast label"
            cites = contrast_cites
            source = "code_fallback"
        if label == "regressed" and decision in ("merge", "revise"):
            decision = "reject"
            source = "regression_guard"
            reason = "guard: contrast flagged regression; " + reason
        resolved.append({"hunk": h, "decision": decision, "reason": reason, "cites": cites,
                         "source": source, "revised": revised, "label": label})

    cur = dict(base_h)
    decisions = []
    for r in resolved:
        h = r["hunk"]
        applied = False
        reason = r["reason"]
        if r["decision"] in ("merge", "revise"):
            edit = h
            if r["decision"] == "revise" and isinstance(r["revised"], str) and r["revised"] \
                    and len(r["revised"]) <= cfg.max_edit_chars:
                edit = replace(h, new=r["revised"])
            cur, res = apply_edits(cur, [edit], cfg)
            _, ok, why = res[0]
            applied = ok
            if not ok:
                reason = f"{reason} apply_failed:{why}"
        decisions.append({"hunk_id": h.hunk_id, "scope": h.scope, "path": h.path, "decision": r["decision"],
                          "applied": applied, "source": r["source"], "cites": r["cites"],
                          "reason": _one_line(reason), "label": r["label"]})

    lines = [f"# compose log task={task.id} candidates={','.join(scopes)}"]
    for d in decisions:
        lines.append(f"# decision {d['hunk_id']} {d['decision']} applied={str(d['applied']).lower()} "
                     f"source={d['source']} cites={','.join(d['cites'])} reason={d['reason']}")
    lines.append("# end log")
    diff_text = diff_harness(base_h, cur)
    (run_dir / "composed.diff").write_text("\n".join(lines) + "\n" + diff_text, encoding="utf-8")
    summary = str(data.get("summary", "")) if data is not None else "compose call failed; fallback rule used"
    (run_dir / "compose.json").write_text(json.dumps({
        "task": task.id, "decisions": decisions, "summary": summary,
        "call_failed": data is None}, indent=2), encoding="utf-8")
    save_harness(cur, run_dir / "composed_harness")
    return ComposeResult(harness=cur, decisions=decisions, diff_text=diff_text, tokens=tokens)
