"""System prompts, JSON schemas and user-prompt builders for the editor and judge roles.

Every system prompt starts with a `ROLE: <role>` line and ends with the JSON-only reminder.
"""
import json
from typing import Dict, List, Optional

from h2.harness import Harness
from h2.trace import Step, condense

JSON_ONLY = "Reply with JSON only, matching the schema."
MAX_DIFF = 1500
MAX_FILE = 4000

PROPOSE_INSTR = {
    "invariant": (
        "Find a general agentic weakness (planning, tool use, context handling, delegation, verification) "
        "visible in the reference trajectory and propose at most 2 edits to system.md, guardrails.md or "
        "tool_guidance.md that fix it. The edit must be domain-neutral: never mention this task, its files "
        "or its functions."
    ),
    "domain": (
        "Propose at most 2 edits that add knowledge or procedure specific to this kind of task (Python bug "
        "fixing in small repos): you may append to the three base files or create one new skills/<slug>.md. "
        "You do not know whether the reference result is correct; do not claim to."
    ),
}
PROPOSE_COMMON = (
    "Cite at least one step id from the reference trajectory that shows the weakness. If the trajectory "
    "looks clean, propose a low-risk reinforcement of verifying work before finishing. Use op append (add "
    "text), replace (old must occur exactly once), or create (new skills/ file). Keep each edit under 1200 "
    "characters."
)

CONTRAST_SYSTEM = (
    "ROLE: contrast\n"
    "You compare a reference agent run with a candidate run that used a harness edit. Judge only the "
    "behaviour change against the targeted deficiency. You cannot know whether either solution is correct.\n"
    "label mitigated = the targeted weakness observably improved and nothing got worse; regressed = new tool "
    "errors, more repeated calls, cap/timeout, or a much larger unexplained diff; unchanged otherwise. "
    "regression must be true iff label is regressed. Cite step ids that appear in the trajectories.\n"
    + JSON_ONLY
)

COMPOSE_SYSTEM = (
    "ROLE: compose\n"
    "You decide what happens to each edit (hunk) of a proposed harness change. For EVERY hunk give a decision "
    "merge/revise/reject. Each decision must cite at least one step id that exists in the trajectories above "
    "and say what you observed there. Do not use presumed score gains. revise: give revised_new (replacement "
    "text for that hunk, <=1200 chars).\n"
    + JSON_ONLY
)

REFLECT_SYSTEM = (
    "ROLE: reflect\n"
    "Write 1-4 lessons, each backed by a contrast and citing step ids that exist. kind invariant (transfers "
    "across tasks) or domain. A lesson about a regressed or unchanged edit is allowed and should say what to "
    "avoid. If the evidence does not support any lesson return lessons: []. Do not mention test results; you "
    "have none.\n"
    + JSON_ONLY
)

PROPOSAL_SCHEMA = {
    "type": "object",
    "required": ["targeted_deficiency", "rationale", "cited_steps", "edits"],
    "properties": {
        "targeted_deficiency": {"type": "string"},
        "rationale": {"type": "string"},
        "cited_steps": {"type": "array", "items": {"type": "string"}},
        "edits": {
            "type": "array",
            "maxItems": 2,
            "items": {
                "type": "object",
                "required": ["path", "op", "new"],
                "properties": {
                    "path": {"type": "string"},
                    "op": {"type": "string", "enum": ["append", "replace", "create"]},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
            },
        },
    },
}

CONTRAST_SCHEMA = {
    "type": "object",
    "required": ["targeted_deficiency", "observed_change", "label", "regression", "cited_steps"],
    "properties": {
        "targeted_deficiency": {"type": "string"},
        "observed_change": {"type": "string"},
        "label": {"type": "string", "enum": ["mitigated", "unchanged", "regressed"]},
        "regression": {"type": "boolean"},
        "cited_steps": {"type": "array", "items": {"type": "string"}},
    },
}

COMPOSE_SCHEMA = {
    "type": "object",
    "required": ["decisions", "summary"],
    "properties": {
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["hunk_id", "decision", "reason", "cited_steps"],
                "properties": {
                    "hunk_id": {"type": "string"},
                    "decision": {"type": "string", "enum": ["merge", "revise", "reject"]},
                    "reason": {"type": "string"},
                    "cited_steps": {"type": "array", "items": {"type": "string"}},
                    "revised_new": {"type": "string"},
                },
            },
        },
        "summary": {"type": "string"},
    },
}

REFLECT_SCHEMA = {
    "type": "object",
    "required": ["title", "applies_when", "lessons"],
    "properties": {
        "title": {"type": "string"},
        "applies_when": {"type": "string"},
        "lessons": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["kind", "label", "text", "cited_steps"],
                "properties": {
                    "kind": {"type": "string", "enum": ["invariant", "domain"]},
                    "label": {"type": "string", "enum": ["mitigated", "unchanged", "regressed"]},
                    "text": {"type": "string"},
                    "cited_steps": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


def propose_system(scope: str) -> str:
    return (f"ROLE: propose_{scope}\n" + PROPOSE_INSTR[scope] + "\n" + PROPOSE_COMMON + "\n" + JSON_ONLY)


def _cut(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n] + "…[truncated]"


def _trajectory(steps: List[Step]) -> str:
    return condense(steps)


def _lessons_block(lessons) -> str:
    if not lessons:
        return "## LIBRARY LESSONS (retrieved: none)\n(none)"
    ids = ", ".join(e.id for e in lessons)
    body = "\n\n".join(e.text.strip() for e in lessons if e.text.strip()) or "(none)"
    return f"## LIBRARY LESSONS (retrieved: {ids})\n{body}"


def propose_prompt(task, harness: Harness, ref_steps: List[Step], ref_signals: dict, lessons, scope: str) -> str:
    files = []
    for rel in sorted(harness):
        files.append(f"=== FILE: {rel} ===\n{_cut(harness[rel], MAX_FILE)}")
    parts = [
        f"TASK_ID: {task.id}",
        "## TASK\n" + task.prompt,
        "## CURRENT HARNESS\n" + "\n".join(files),
        "## REFERENCE TRAJECTORY (run: reference)\n" + _trajectory(ref_steps),
        "## REFERENCE SIGNALS\n" + json.dumps(ref_signals, indent=2, sort_keys=True),
        _lessons_block(lessons),
        "## OUTPUT FORMAT\n"
        "Return an object with: targeted_deficiency (string), rationale (string), cited_steps (array of step ids "
        "from the reference trajectory), edits (array of at most 2 objects with path, op, old (for replace), "
        f"new). Scope: {scope}.",
    ]
    return "\n\n".join(parts)


def contrast_prompt(task, scope: str, proposal, ref_steps: List[Step], cand_steps: List[Step],
                    signals: dict, ref_diff: str, cand_diff: str) -> str:
    edit_text = "\n".join(
        f"[{e.hunk_id}] {e.op} {e.path}: {_cut(e.new, 600)}" for e in proposal.edits
    )
    parts = [
        f"TASK_ID: {task.id}",
        f"CANDIDATE_SCOPE: {scope}",
        "## TARGETED DEFICIENCY\n" + proposal.targeted_deficiency,
        "## EDIT (unified diff)\n" + _cut(proposal.diff_text, MAX_DIFF) + "\n" + edit_text,
        "## REFERENCE TRAJECTORY (run: reference)\n" + _trajectory(ref_steps),
        f"## CANDIDATE TRAJECTORY (run: candidate_{scope})\n" + _trajectory(cand_steps),
        "## SIGNALS\n" + json.dumps(signals, indent=2, sort_keys=True),
        "## DELIVERABLE DIFFS\n--- reference\n" + _cut(ref_diff, MAX_DIFF) + "\n--- candidate\n" + _cut(cand_diff, MAX_DIFF),
        "## OUTPUT FORMAT\n"
        "Return targeted_deficiency, observed_change, label (mitigated|unchanged|regressed), regression (boolean, "
        "true iff label is regressed), cited_steps (ids from the trajectories above).",
    ]
    return "\n\n".join(parts)


def compose_prompt(task, hunk_text: str, contrasts_json: str, ref_steps: List[Step],
                   cand_steps_by_scope: Dict[str, List[Step]], lessons) -> str:
    parts = [
        f"TASK_ID: {task.id}",
        "## TASK\n" + task.prompt,
        "## HUNKS\n" + hunk_text,
        "## CONTRASTS\n" + contrasts_json,
        "## REFERENCE TRAJECTORY (run: reference)\n" + _trajectory(ref_steps),
    ]
    for scope, steps in cand_steps_by_scope.items():
        parts.append(f"## CANDIDATE TRAJECTORY (run: candidate_{scope})\n" + _trajectory(steps))
    parts.append(_lessons_block(lessons))
    parts.append("## OUTPUT FORMAT\n"
                 "Return decisions (one per hunk: hunk_id, decision merge|revise|reject, reason, cited_steps, and "
                 "revised_new when revise) and a short summary.")
    return "\n\n".join(parts)


def reflect_prompt(task, contrasts_json: str, compose_log: str, merged: List[str], composed_deltas: Optional[dict],
                   ref_steps: List[Step], composed_steps: Optional[List[Step]]) -> str:
    parts = [
        f"TASK_ID: {task.id}",
        "## TASK\n" + task.prompt,
        "## CONTRASTS\n" + contrasts_json,
        "## COMPOSE DECISIONS\n" + compose_log,
        "merged_hunks: " + (", ".join(merged) if merged else "none"),
        "## COMPOSED RUN SIGNALS vs REFERENCE\n" + json.dumps(composed_deltas or {}, indent=2, sort_keys=True),
        "## REFERENCE TRAJECTORY\n" + _trajectory(ref_steps),
    ]
    if composed_steps is not None:
        parts.append("## COMPOSED TRAJECTORY (run: composed)\n" + _trajectory(composed_steps))
    parts.append("## OUTPUT FORMAT\nReturn title, applies_when, and lessons (kind, label, text, cited_steps).")
    return "\n\n".join(parts)
