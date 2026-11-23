import re
from typing import List, Optional

from h2.trace import Step

TERMINAL = ("final", "timeout")
TEST_RE = re.compile(r"\b(pytest|unittest)\b|python3?\s+\S*test\S*\.py")


def _body(steps: List[Step]) -> List[Step]:
    return [s for s in steps if s.tool not in TERMINAL]


def compute_signals(steps: List[Step], meta: dict, diff_text: str) -> dict:
    body = _body(steps)
    seen = set()
    repeated = 0
    for s in body:
        if s.sig in seen:
            repeated += 1
        seen.add(s.sig)
    ran_tests = any(s.tool == "run_shell" and TEST_RE.search(str(s.args.get("cmd", ""))) for s in body)
    edited = sorted({str(s.args.get("path")) for s in body if s.tool == "write_file" and s.args.get("path")})
    diff_lines = 0
    for ln in (diff_text or "").splitlines():
        if ln.startswith("+++") or ln.startswith("---"):
            continue
        if (ln.startswith("+") or ln.startswith("-")) and ln[1:].strip():
            diff_lines += 1
    return {
        "n_steps": len(body),
        "tool_errors": sum(1 for s in body if s.is_error),
        "repeated_calls": repeated,
        "ran_tests": ran_tests,
        "edited_files": edited,
        "diff_lines": diff_lines,
        "capped": bool(meta.get("capped", False)),
        "timed_out": bool(meta.get("timed_out", False)),
        "finished": bool(steps) and steps[-1].tool == "final",
        "tokens": int(meta.get("tokens", 0) or 0),
    }


def signal_deltas(ref: dict, cand: dict) -> dict:
    ref_files = set(ref.get("edited_files", []))
    cand_files = set(cand.get("edited_files", []))
    return {
        "n_steps": cand["n_steps"] - ref["n_steps"],
        "tool_errors": cand["tool_errors"] - ref["tool_errors"],
        "repeated_calls": cand["repeated_calls"] - ref["repeated_calls"],
        "diff_lines": cand["diff_lines"] - ref["diff_lines"],
        "ran_tests_changed": bool(cand["ran_tests"]) != bool(ref["ran_tests"]),
        "files_changed": {
            "only_candidate": sorted(cand_files - ref_files),
            "only_reference": sorted(ref_files - cand_files),
        },
    }


def default_cites(ref_steps: List[Step], cand_steps: List[Step]) -> List[str]:
    """Code-derived evidence ids, first 3 in priority order. Never empty for a non-empty run."""
    out: List[str] = []

    def add(step: Optional[Step]) -> None:
        if step is not None and step.id not in out:
            out.append(step.id)

    cand_body = _body(cand_steps)
    add(next((s for s in cand_body if s.is_error), None))
    rep = None
    seen_sigs = set()
    for s in cand_body:
        if s.sig in seen_sigs:
            rep = s
            break
        seen_sigs.add(s.sig)
    add(rep)
    add(next((s for s in _body(ref_steps) if s.is_error), None))
    if cand_steps:
        add(cand_steps[-1])
    if ref_steps:
        add(ref_steps[-1])
    return out[:3]
