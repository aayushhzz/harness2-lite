"""Shared test helpers: a scripted backend and small builders for steps, runs and proposals."""
import json
from pathlib import Path

from h2.backends import Backend, BackendError, Completion
from h2.harness import Edit
from h2.probe import RunRecord
from h2.propose import Proposal
from h2.signals import compute_signals
from h2.trace import make_step


class ScriptBackend(Backend):
    """Answers editor roles from a per-role queue of replies (dicts are dumped to JSON)."""
    name = "script"

    def __init__(self, replies=None):
        self.replies = {k: list(v) for k, v in (replies or {}).items()}
        self.calls = []

    def complete(self, role, system, prompt, schema=None):
        name = system.splitlines()[0].split("ROLE:", 1)[1].strip()
        self.calls.append((name, prompt))
        queue = self.replies.get(name) or []
        if not queue:
            raise BackendError(f"no scripted reply for {name}")
        r = queue.pop(0)
        if isinstance(r, BaseException):
            raise r
        text = r if isinstance(r, str) else json.dumps(r)
        return Completion(text=text, data=None, prompt_tokens=3, completion_tokens=2)

    def run_agent(self, run_name, system, task_prompt, workdir, max_steps, timeout_s):
        raise BackendError("script backend has no agent")


def steps_for(run, specs):
    return [make_step(run, i, tool, args, res, err) for i, (tool, args, res, err) in enumerate(specs, 1)]


def write_jsonl(path, steps):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(s.to_json()) + "\n" for s in steps), encoding="utf-8")


def make_rec(name, steps, diff="", tokens=10):
    meta = {"tokens": tokens, "capped": False, "timed_out": False}
    return RunRecord(name=name, steps=steps, meta=meta, diff=diff,
                     signals=compute_signals(steps, meta, diff))


def make_prop(scope, edits, deficiency="weak point", cites=None):
    return Proposal(scope=scope, targeted_deficiency=deficiency, rationale="r",
                    cited_steps=cites or [], edits=edits, dropped=[], diff_text="")


def edit(hunk_id, scope, path, op, new, old=""):
    return Edit(hunk_id=hunk_id, scope=scope, path=path, op=op, old=old, new=new)


REF_STEPS = [
    ("run_shell", {"cmd": "ls"}, "textutil.py task.md", False),
    ("read_file", {"path": "textutil.py"}, "def slugify(s): ...", False),
    ("final", {}, "done", False),
]
