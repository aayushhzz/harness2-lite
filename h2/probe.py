import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from h2.harness import Harness, render_system_prompt
from h2.paths import Config
from h2.signals import compute_signals
from h2.tasks import Task, make_workspace
from h2.trace import AgentRun, Step, workspace_diff, write_run


@dataclass
class RunRecord:
    name: str
    steps: List[Step]
    meta: dict
    diff: str
    signals: dict
    workspace: Optional[Path] = None
    agent_run: Optional[AgentRun] = field(default=None, repr=False)

    @property
    def tokens(self) -> int:
        return int(self.meta.get("tokens", 0))


def probe_candidate(task: Task, harness_files: Harness, backend, cfg: Config, run_dir: Path, run_name: str,
                    keep_workspace: bool = False) -> RunRecord:
    """Run the agent once on a throwaway copy of the task repo. Caller removes a kept workspace."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    ws = make_workspace(task)
    keep = False
    try:
        system = render_system_prompt(harness_files)
        agent_run = backend.run_agent(run_name, system, task.prompt, ws, cfg.max_steps, cfg.timeout_s)
        diff = workspace_diff(task.repo_dir, ws)
        diff_name = "composed.run.diff" if run_name == "composed" else None
        write_run(run_dir, run_name, agent_run, diff, {"harness_files": sorted(harness_files)}, diff_name)
        meta = _meta_for(agent_run)
        signals = compute_signals(agent_run.steps, meta, diff)
        keep = keep_workspace
        return RunRecord(name=run_name, steps=agent_run.steps, meta=meta,
                         diff=diff, signals=signals, workspace=ws if keep else None, agent_run=agent_run)
    finally:
        if not keep:
            shutil.rmtree(ws, ignore_errors=True)


def _meta_for(agent_run: AgentRun) -> dict:
    tool_errors = sum(1 for s in agent_run.steps if s.is_error and s.tool not in ("final", "timeout"))
    return {
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
