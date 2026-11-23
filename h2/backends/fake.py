import json
import re
from pathlib import Path
from typing import Optional

from h2.backends import Backend, BackendError, Completion
from h2.react import run_react


def _section(prompt: str, header: str) -> str:
    out = []
    on = False
    for ln in prompt.splitlines():
        if ln.startswith("## "):
            if on:
                break
            if ln.startswith(header):
                on = True
            continue
        if on:
            out.append(ln)
    return "\n".join(out)


def _first(pattern: str, text: str, default: str) -> str:
    m = re.search(pattern, text)
    return m.group(0) if m else default


class FakeBackend(Backend):
    """Offline, deterministic stand-in for the model. Used by tests and --backend fake."""

    name = "fake"

    def __init__(self, golden_dir: Path, worker_model: Optional[str] = None, editor_model: Optional[str] = None):
        self.golden_dir = Path(golden_dir)
        self.worker_model = worker_model
        self.editor_model = editor_model

    # ---- agent -------------------------------------------------------
    def run_agent(self, run_name: str, system: str, task_prompt: str, workdir: Path, max_steps: int,
                  timeout_s: int):
        m = re.search(r"TASK_ID: (\S+)", task_prompt)
        if not m:
            raise BackendError("fake agent: no TASK_ID line in task prompt")
        task_id = m.group(1)
        gdir = self.golden_dir / task_id
        golden_files = sorted(str(p.relative_to(gdir)) for p in gdir.rglob("*") if p.is_file())
        if not golden_files:
            raise BackendError(f"fake agent: no golden files for {task_id}")
        first = golden_files[0]
        script = [("run_shell", {"cmd": "ls"}), ("read_file", {"path": first})]
        if "FAKE_VERIFY" in system:
            for rel in golden_files:
                script.append(("write_file", {"path": rel, "content": (gdir / rel).read_text(encoding="utf-8")}))
            script.append(("write_file", {"path": "test_mine.py", "content": "def test_ok():\n    assert True\n"}))
            script.append(("run_shell", {"cmd": "python3 -m pytest -q test_mine.py"}))
        else:
            target = Path(workdir) / first
            current = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
            script.append(("write_file", {"path": first, "content": current}))
        script.append(("final", {"text": "done"}))
        it = iter(script)
        sys_len = len(system)

        def chat(messages):
            try:
                tool, args = next(it)
            except StopIteration:
                tool, args = "final", {"text": "done"}
            return json.dumps({"tool": tool, "args": args}), sys_len // 4 + 1, 20

        return run_react(run_name, chat, system, task_prompt, workdir, max_steps, timeout_s)

    # ---- editor / judge roles ---------------------------------------
    def complete(self, role: str, system: str, prompt: str, schema: Optional[dict] = None) -> Completion:
        first = system.splitlines()[0] if system else ""
        m = re.match(r"ROLE:\s*(\S+)", first)
        name = m.group(1) if m else ""
        handlers = {
            "propose_invariant": self._propose_inv,
            "propose_domain": self._propose_dom,
            "contrast": self._contrast,
            "compose": self._compose,
            "reflect": self._reflect,
            "doctor": lambda p: {"ok": True},
        }
        if name not in handlers:
            raise BackendError(f"fake backend has no handler for role {name!r}")
        obj = handlers[name](prompt)
        text = json.dumps(obj)
        return Completion(text=text, data=obj, prompt_tokens=len(system + prompt) // 4 + 1,
                          completion_tokens=len(text) // 4 + 1)

    @staticmethod
    def _task_id(prompt: str) -> str:
        m = re.search(r"TASK_ID: (\S+)", prompt)
        return m.group(1) if m else "unknown"

    def _propose_inv(self, prompt: str) -> dict:
        ids = re.findall(r"reference:s\d+", _section(prompt, "## REFERENCE TRAJECTORY"))
        cite = ids[-1] if ids else "reference:s1"
        return {
            "targeted_deficiency": "agent never writes or runs its own test",
            "rationale": "reference shows no test run",
            "cited_steps": [cite],
            "edits": [{"path": "guardrails.md", "op": "append",
                       "new": "- Before finishing, write and run a small test of your own. FAKE_VERIFY"}],
        }

    def _propose_dom(self, prompt: str) -> dict:
        ids = re.findall(r"reference:s\d+", _section(prompt, "## REFERENCE TRAJECTORY"))
        cite = ids[0] if ids else "reference:s1"
        return {
            "targeted_deficiency": "no reproduction step",
            "rationale": "bug fixing tasks benefit from reproducing the bug first",
            "cited_steps": [cite],
            "edits": [{"path": "skills/bugfix.md", "op": "create",
                       "new": "# Bug fixing\nReproduce the bug before editing. FAKE_DOMAIN_NOTE"}],
        }

    def _contrast(self, prompt: str) -> dict:
        raw = _section(prompt, "## SIGNALS").strip()
        try:
            sig = json.loads(raw)
        except ValueError:
            raise BackendError("fake contrast: SIGNALS section is not json")
        scope = re.search(r"CANDIDATE_SCOPE: (\S+)", prompt).group(1)
        cand_ran = bool(sig["candidate"].get("ran_tests"))
        ref_ran = bool(sig["reference"].get("ran_tests"))
        label = "mitigated" if (cand_ran and not ref_ran) else "unchanged"
        cite = _first(rf"candidate_{scope}:s\d+", prompt, f"candidate_{scope}:s1")
        return {
            "targeted_deficiency": f"fake deficiency for {scope}",
            "observed_change": f"candidate ran_tests={cand_ran} reference ran_tests={ref_ran}",
            "label": label,
            "regression": False,
            "cited_steps": [cite],
        }

    def _compose(self, prompt: str) -> dict:
        decisions = []
        for ln in _section(prompt, "## HUNKS").splitlines():
            hm = re.match(r"^HUNK (\S+) \| (\S+) \| (.*?) \| (\S+) \| label=(\S+)", ln)
            if not hm:
                continue
            hunk_id, scope, label = hm.group(1), hm.group(2), hm.group(5)
            if label == "mitigated":
                decision = "merge"
                cite = _first(rf"candidate_{scope}:s\d+", prompt, f"candidate_{scope}:s1")
            else:
                decision = "reject"
                cite = "reference:s1"
            decisions.append({"hunk_id": hunk_id, "decision": decision,
                              "reason": f"fake compose: label={label}", "cited_steps": [cite]})
        return {"decisions": decisions, "summary": "fake compose"}

    def _reflect(self, prompt: str) -> dict:
        task_id = self._task_id(prompt)
        merged = re.search(r"merged_hunks: (.*)", prompt)
        has_merge = bool(merged) and merged.group(1).strip() not in ("", "none")
        lessons = []
        if has_merge:
            cite = _first(r"candidate_invariant:s\d+", prompt, "candidate_invariant:s1")
            lessons.append({"kind": "invariant", "label": "mitigated",
                            "text": f"LESSON {task_id}: write and run your own test before finishing",
                            "cited_steps": [cite]})
        return {"title": f"fake lesson {task_id}",
                "applies_when": "python bug fix small repository tests",
                "lessons": lessons}
