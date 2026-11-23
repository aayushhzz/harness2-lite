import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from h2.paths import Config
from h2.trace import text_lines

Harness = Dict[str, str]

FIXED = ("system.md", "guardrails.md", "tool_guidance.md")
SKILL_RE = re.compile(r"^skills/[a-z0-9][a-z0-9_-]*\.md$")
PLACEHOLDER = "skills/_placeholder.md"
SECTIONS = "# System\n{system}\n\n# Guardrails\n{guardrails}\n\n# Tool guidance\n{tool}"


def _editable(rel: str) -> bool:
    return rel in FIXED or bool(SKILL_RE.match(rel))


def load_harness(d: Path) -> Harness:
    d = Path(d)
    h: Harness = {}
    for name in FIXED:
        p = d / name
        if p.exists():
            h[name] = p.read_text(encoding="utf-8")
    sk = d / "skills"
    if sk.exists():
        for p in sorted(sk.glob("*.md")):
            h["skills/" + p.name] = p.read_text(encoding="utf-8")
    return h


def save_harness(h: Harness, d: Path) -> None:
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    for rel, content in h.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def render_system_prompt(h: Harness) -> str:
    text = SECTIONS.format(
        system=h.get("system.md", "").strip(),
        guardrails=h.get("guardrails.md", "").strip(),
        tool=h.get("tool_guidance.md", "").strip(),
    )
    skills = [rel for rel in sorted(h) if rel.startswith("skills/") and not rel.split("/")[-1].startswith("_")]
    if skills:
        text += "\n\n# Skills"
        for rel in skills:
            name = rel.split("/")[-1][:-3]
            text += "\n## " + name + "\n" + h[rel].strip()
    return text.strip()


@dataclass
class Edit:
    hunk_id: str
    scope: str
    path: str
    op: str
    old: str
    new: str


def _apply_one(h: Harness, e: Edit, cfg: Config) -> Tuple[Harness, str]:
    if e.op not in ("append", "replace", "create"):
        return h, "path_not_allowed"
    if e.op == "create" and not e.path.startswith("skills/"):
        return h, "exists"
    if not _editable(e.path):
        return h, "path_not_allowed"
    if len(e.new) > cfg.max_edit_chars:
        return h, "too_long"
    out = dict(h)
    if e.op == "append":
        cur = h.get(e.path)
        if cur is None:
            out[e.path] = e.new.rstrip("\n") + "\n"
        else:
            out[e.path] = cur.rstrip("\n") + "\n" + e.new.rstrip("\n") + "\n"
    elif e.op == "replace":
        cur = h.get(e.path)
        if cur is None:
            return h, "file_missing"
        if not e.old:
            return h, "old_empty"
        n = cur.count(e.old)
        if n == 0:
            return h, "old_not_found"
        if n > 1:
            return h, "old_ambiguous"
        out[e.path] = cur.replace(e.old, e.new, 1)
    else:
        if e.path in h:
            return h, "exists"
        out[e.path] = e.new.rstrip("\n") + "\n"
    if out == h:
        return h, "noop"
    return out, "ok"


def apply_edits(h: Harness, edits: List[Edit], cfg: Optional[Config] = None) -> Tuple[Harness, List[Tuple[Edit, bool, str]]]:
    cfg = cfg or Config()
    cur = dict(h)
    results = []
    for e in edits:
        cur, reason = _apply_one(cur, e, cfg)
        results.append((e, reason == "ok", reason))
    return cur, results


def diff_harness(old: Harness, new: Harness) -> str:
    chunks = []
    for p in sorted(set(old) | set(new)):
        a = old.get(p)
        b = new.get(p)
        if a == b:
            continue
        diff = difflib.unified_diff(
            text_lines(a or ""), text_lines(b or ""),
            fromfile="/dev/null" if a is None else "a/" + p,
            tofile="/dev/null" if b is None else "b/" + p,
        )
        text = "".join(diff)
        if text and not text.endswith("\n"):
            text += "\n"
        if text:
            chunks.append(text)
    return "".join(chunks)


def hunk_diff(base: Harness, edit: Edit, cfg: Optional[Config] = None) -> str:
    new, results = apply_edits(base, [edit], cfg)
    if not results[0][1]:
        return ""
    return diff_harness(base, new)


def mentions_task_specifics(text: str, task) -> bool:
    if not text:
        return False
    if task.id and task.id in text:
        return True
    for p in Path(task.repo_dir).rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts:
            continue
        if len(p.name) >= 4 and p.name in text:
            return True
        if len(p.stem) >= 4 and p.stem in text:
            return True
    return False
