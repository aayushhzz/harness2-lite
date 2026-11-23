import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from h2.paths import Paths

IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache")


@dataclass
class Task:
    id: str
    group: str
    title: str
    repo_dir: Path
    prompt: str


def _meta(paths: Paths, tid: str) -> dict:
    p = paths.tasks_dir / tid / "meta.json"
    return json.loads(p.read_text(encoding="utf-8"))


def all_task_ids(paths: Paths) -> List[str]:
    return sorted(p.name for p in paths.tasks_dir.iterdir() if (p / "meta.json").exists())


def load_task(paths: Paths, tid: str) -> Task:
    if tid not in all_task_ids(paths):
        raise ValueError(f"unknown task: {tid}")
    meta = _meta(paths, tid)
    repo = paths.tasks_dir / tid / "repo"
    task_md = (repo / "task.md").read_text(encoding="utf-8")
    prompt = (f"TASK_ID: {tid}\n\n" + task_md +
              "\n\nWork inside the current directory. When finished, reply with one sentence.")
    return Task(id=tid, group=meta["group"], title=meta["title"], repo_dir=repo, prompt=prompt)


def list_tasks(paths: Paths, selector: str) -> List[Task]:
    ids = all_task_ids(paths)
    sel = (selector or "evolve").strip()
    if sel == "all":
        chosen = ids
    elif sel in ("evolve", "heldout"):
        chosen = [t for t in ids if _meta(paths, t)["group"] == sel]
    else:
        chosen = []
        for x in [s.strip() for s in sel.split(",") if s.strip()]:
            if x not in ids:
                raise ValueError(f"unknown task: {x}")
            chosen.append(x)
    return [load_task(paths, t) for t in sorted(set(chosen))]


def make_workspace(task: Task, dest: Optional[Path] = None) -> Path:
    if dest is None:
        target = Path(tempfile.mkdtemp(prefix="h2-ws-"))
    else:
        target = Path(dest)
    shutil.copytree(task.repo_dir, target, ignore=IGNORE, dirs_exist_ok=True)
    return target
