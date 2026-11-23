import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from h2.harness import Harness, save_harness


@dataclass
class LibEntry:
    id: str
    title: str
    applies_when: str
    lessons: int
    labels: Dict[str, int]
    path: str
    created: str
    keywords: List[str]
    text: str = field(default="", repr=False)


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z]{4,}", text.lower()))


class Library:
    def __init__(self, dir, readonly: bool = False):
        self.dir = Path(dir)
        self.readonly = readonly

    @property
    def index_path(self) -> Path:
        return self.dir / "index.json"

    def entries(self) -> List[LibEntry]:
        p = self.index_path
        if not p.exists():
            return []
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            raw = data.get("entries", [])
            if not isinstance(raw, list):
                raise ValueError("entries must be a list")
        except (ValueError, AttributeError):
            if not self.readonly:
                os.replace(p, p.with_name("index.json.corrupt"))
            return []
        out = []
        for d in raw:
            try:
                e = LibEntry(
                    id=str(d["id"]), title=str(d.get("title", "")), applies_when=str(d.get("applies_when", "")),
                    lessons=int(d.get("lessons", 0)), labels=dict(d.get("labels", {})),
                    path=str(d.get("path", "")), created=str(d.get("created", "")),
                    keywords=list(d.get("keywords", [])),
                )
            except (KeyError, TypeError, ValueError):
                continue
            out.append(e)
        return out

    def _load_text(self, e: LibEntry) -> str:
        try:
            return (self.dir / e.path).read_text(encoding="utf-8")
        except OSError:
            return ""

    def retrieve(self, query: str, k: int) -> List[LibEntry]:
        entries = self.entries()
        if not entries or k <= 0:
            return []
        q = _tokens(query)
        ordered = sorted(entries, key=lambda e: e.created, reverse=True)  # newest first
        ordered = sorted(ordered, key=lambda e: -len(q & set(e.keywords)))  # stable: overlap wins
        top = ordered[:k]
        for e in top:
            e.text = self._load_text(e)
        return top

    def add_entry(self, task_id: str, title: str, applies_when: str, lessons: List[dict],
                  adopted: Harness, merged_hunks: List[str]) -> LibEntry:
        if self.readonly:
            raise PermissionError("library is read-only")
        tdir = self.dir / task_id
        tdir.mkdir(parents=True, exist_ok=True)
        merged_txt = ", ".join(merged_hunks) if merged_hunks else "none"
        lines = [f"# {task_id}: {title}", f"applies_when: {applies_when}", f"merged_hunks: {merged_txt}", "",
                 "## Lessons"]
        labels: Dict[str, int] = {}
        texts = [title, applies_when]
        for les in lessons:
            text = " ".join(str(les["text"]).split())
            ev = ", ".join(les.get("cited_steps", []))
            lines.append(f"- [{les['kind']}|{les['label']}] {text} (evidence: {ev})")
            labels[les["label"]] = labels.get(les["label"], 0) + 1
            texts.append(text)
        (tdir / "EXPERIENCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        save_harness(adopted, tdir / "harness")
        keywords = sorted(_tokens(" ".join(texts)))[:60]
        entry = LibEntry(id=task_id, title=title, applies_when=applies_when, lessons=len(lessons), labels=labels,
                         path=f"{task_id}/EXPERIENCE.md",
                         created=datetime.now(timezone.utc).isoformat(),
                         keywords=keywords)
        kept = [e for e in self.entries() if e.id != task_id]
        records = [{"id": e.id, "title": e.title, "applies_when": e.applies_when, "lessons": e.lessons,
                    "labels": e.labels, "path": e.path, "created": e.created, "keywords": e.keywords}
                   for e in kept + [entry]]
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.index_path.with_name("index.json.tmp")
        tmp.write_text(json.dumps({"entries": records}, indent=2), encoding="utf-8")
        os.replace(tmp, self.index_path)
        entry.text = "\n".join(lines) + "\n"
        return entry
