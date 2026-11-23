import difflib
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


ID_RE = re.compile(r"^(reference|candidate_invariant|candidate_domain|composed):s[1-9][0-9]*$")
TRUNC = 400


def _trunc(s: str, n: int = TRUNC) -> str:
    if len(s) <= n:
        return s
    return s[:n] + f"…[+{len(s) - n} chars]"


@dataclass
class Step:
    id: str
    tool: str
    args: dict
    result: str
    is_error: bool
    sig: str

    def to_json(self) -> dict:
        return {"id": self.id, "tool": self.tool, "args": self.args, "result": self.result,
                "is_error": self.is_error, "sig": self.sig}

    @staticmethod
    def from_json(d: dict) -> "Step":
        return Step(id=d["id"], tool=d["tool"], args=d.get("args", {}), result=d.get("result", ""),
                    is_error=bool(d.get("is_error", False)), sig=d.get("sig", ""))


def make_step(run: str, n: int, tool: str, args: dict, result: str, is_error: bool) -> Step:
    digest = hashlib.sha1((tool + json.dumps(args, sort_keys=True)).encode("utf-8")).hexdigest()[:10]
    short_args = {}
    for k, v in args.items():
        short_args[k] = _trunc(v) if isinstance(v, str) else v
    return Step(id=f"{run}:s{n}", tool=tool, args=short_args, result=_trunc(result),
                is_error=bool(is_error), sig=digest)


@dataclass
class AgentRun:
    steps: List[Step]
    final_text: str
    prompt_tokens: int
    completion_tokens: int
    timed_out: bool
    capped: bool
    seconds: float
    error: Optional[str]

    @property
    def tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def write_run(run_dir: Path, name: str, agent_run: AgentRun, diff_text: str, extra: dict,
              diff_name: Optional[str] = None) -> None:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    with open(run_dir / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for s in agent_run.steps:
            f.write(json.dumps(s.to_json()) + "\n")
    tool_errors = sum(1 for s in agent_run.steps if s.is_error and s.tool not in ("final", "timeout"))
    meta = {
        "steps": len([s for s in agent_run.steps if s.tool not in ("final", "timeout")]),
        "tool_errors": tool_errors,
        "tokens": agent_run.tokens,
        "prompt_tokens": agent_run.prompt_tokens,
        "completion_tokens": agent_run.completion_tokens,
        "timed_out": agent_run.timed_out,
        "capped": agent_run.capped,
        "final_text": agent_run.final_text,
        "seconds": round(agent_run.seconds, 2),
        "error": agent_run.error,
    }
    meta.update(extra)
    (run_dir / f"{name}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    # composed.diff is the compose log, so the composed run keeps its deliverable diff under another name
    (run_dir / (diff_name or f"{name}.diff")).write_text(diff_text, encoding="utf-8")


def read_steps(path: Path) -> List[Step]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(Step.from_json(json.loads(line)))
    return out


class StepIndex:
    RUNS = ("reference", "candidate_invariant", "candidate_domain", "composed")

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self._steps: Dict[str, Step] = {}
        self._order: List[str] = []
        for name in self.RUNS:
            p = self.run_dir / f"{name}.jsonl"
            if not p.exists():
                continue
            for s in read_steps(p):
                if ID_RE.match(s.id) and s.id not in self._steps:
                    self._steps[s.id] = s
                    self._order.append(s.id)

    def valid(self, sid: str) -> bool:
        return sid in self._steps

    def get(self, sid: str) -> Step:
        return self._steps[sid]

    def ids(self) -> List[str]:
        return list(self._order)

    def filter_valid(self, ids) -> List[str]:
        out: List[str] = []
        seen = set()
        for i in ids or []:
            if isinstance(i, str) and i in self._steps and i not in seen:
                seen.add(i)
                out.append(i)
        return out


def text_lines(text: str) -> List[str]:
    """Split text into lines, treating a missing final newline as present (keeps diffs one line per entry)."""
    if text and not text.endswith("\n"):
        text += "\n"
    return text.splitlines(True)


def _one_line_value(v) -> str:
    return str(v).replace("\n", "\\n")


def condense(steps: List[Step], max_args: int = 100, max_result: int = 120, max_lines: int = 40) -> str:
    def line(s: Step) -> str:
        args = " ".join(f"{k}={_one_line_value(v)}" for k, v in s.args.items()) if s.args else ""
        args = args if len(args) <= max_args else args[:max_args] + "…"
        first = (s.result.splitlines() or [""])[0]
        first = first if len(first) <= max_result else first[:max_result] + "…"
        out = f"{s.id} | {s.tool} | {args} | -> {first}"
        if s.is_error:
            out += " | ERR"
        return out

    lines = [line(s) for s in steps]
    if len(lines) > max_lines:
        head, tail = lines[:20], lines[-20:]
        omitted = len(lines) - 40
        lines = head + [f"... {omitted} steps omitted ..."] + tail
    return "\n".join(lines)


def workspace_diff(orig_dir: Path, ws_dir: Path) -> str:
    orig_dir, ws_dir = Path(orig_dir), Path(ws_dir)
    exts = (".py", ".md", ".txt", ".csv", ".json")
    skip = {"__pycache__", ".pytest_cache"}

    def collect(root: Path) -> Dict[str, str]:
        files = {}
        if not root.exists():
            return files
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix not in exts:
                continue
            rel = p.relative_to(root)
            if any(part in skip for part in rel.parts):
                continue
            files[str(rel)] = p.read_text(encoding="utf-8", errors="replace")
        return files

    a = collect(orig_dir)
    b = collect(ws_dir)
    chunks = []
    for rel in sorted(set(a) | set(b)):
        old = a.get(rel)
        new = b.get(rel)
        if old == new:
            continue
        diff = difflib.unified_diff(
            text_lines(old or ""), text_lines(new or ""),
            fromfile="a/" + rel if old is not None else "/dev/null",
            tofile="b/" + rel if new is not None else "/dev/null",
        )
        text = "".join(diff)
        if text and not text.endswith("\n"):
            text += "\n"
        chunks.append(text)
    return "".join(chunks)
