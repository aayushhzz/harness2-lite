import json
import os
import re
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Iterable, Optional, Tuple

from h2.backends import Backend, BackendError, Completion, RateLimited
from h2.llmjson import extract_json
from h2.tools import child_env  # noqa: F401  (re-exported; same env rules as the shell tool)
from h2.trace import AgentRun, Step, _trunc, make_step

RATE_RE = re.compile(r"rate.?limit|usage limit|limit reached|overloaded", re.I)
AGENT_TOOLS = "Read,Write,Bash"
TOOL_MAP = {"Read": "read_file", "Write": "write_file", "Bash": "run_shell"}
AGENT_SUFFIX = ("\n\nTool names: read_file = Read, write_file = Write, run_shell = Bash. "
                "Use absolute paths under the current working directory for Read and Write.")


def _common_tail() -> list:
    return ["--no-session-persistence", "--setting-sources", "", "--disable-slash-commands", "--strict-mcp-config"]


def build_complete_cmd(system: str, prompt: str, schema: Optional[dict], model: Optional[str]) -> list:
    cmd = ["claude", "-p", prompt, "--system-prompt", system, "--tools", "", "--output-format", "json"]
    if schema is not None:
        cmd += ["--json-schema", json.dumps(schema)]
    cmd += _common_tail()
    if model:
        cmd += ["--model", model]
    return cmd


def build_agent_cmd(system: str, prompt: str, model: Optional[str]) -> list:
    cmd = ["claude", "-p", prompt, "--system-prompt", system,
           "--tools", AGENT_TOOLS, "--allowedTools", AGENT_TOOLS,
           "--permission-mode", "dontAsk", "--output-format", "stream-json", "--verbose"]
    cmd += _common_tail()
    if model:
        cmd += ["--model", model]
    return cmd


def _flatten(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = []
    for b in content:
        if isinstance(b, dict) and b.get("type") == "text":
            parts.append(b.get("text", ""))
        elif isinstance(b, str):
            parts.append(b)
    return "\n".join(parts)


def _tokens(usage: dict) -> Tuple[int, int]:
    usage = usage or {}
    prompt = (usage.get("input_tokens", 0) or 0) + (usage.get("cache_creation_input_tokens", 0) or 0) \
        + (usage.get("cache_read_input_tokens", 0) or 0)
    return prompt, usage.get("output_tokens", 0) or 0


class StreamParser:
    def __init__(self, run_name: str, max_steps: int):
        self.run = run_name
        self.max_steps = max_steps
        self.steps: list = []
        self._pending = {}
        self.final_text = ""
        self.result_event: Optional[dict] = None
        self.assist_usage = {}
        self.capped = False

    def feed(self, line: str) -> bool:
        """Returns True when the run must be killed now (step cap exceeded)."""
        line = line.strip()
        if not line:
            return False
        try:
            ev = json.loads(line)
        except ValueError:
            return False
        t = ev.get("type")
        if t == "assistant":
            msg = ev.get("message", {}) or {}
            if msg.get("id") and msg.get("usage"):
                self.assist_usage[msg["id"]] = msg["usage"]
            for block in msg.get("content", []) or []:
                if block.get("type") == "text" and block.get("text"):
                    self.final_text = block["text"]
                elif block.get("type") == "tool_use":
                    if len(self.steps) >= self.max_steps:
                        self.capped = True
                        return True
                    name = block.get("name", "")
                    raw = block.get("input", {}) or {}
                    if name == "Read":
                        tool, args = "read_file", {"path": raw.get("file_path", "")}
                    elif name == "Write":
                        tool, args = "write_file", {"path": raw.get("file_path", ""), "content": raw.get("content", "")}
                    elif name == "Bash":
                        tool, args = "run_shell", {"cmd": raw.get("command", "")}
                    else:
                        tool, args = name.lower(), dict(raw)
                    self.steps.append(make_step(self.run, len(self.steps) + 1, tool, args, "", False))
                    self._pending[block.get("id")] = len(self.steps) - 1
        elif t == "user":
            msg = ev.get("message", {}) or {}
            for block in msg.get("content", []) or []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                idx = self._pending.pop(block.get("tool_use_id"), None)
                if idx is None:
                    continue
                s = self.steps[idx]
                s.result = _trunc(_flatten(block.get("content")))
                s.is_error = bool(block.get("is_error", False))
        elif t == "rate_limit_event":
            info = ev.get("rate_limit_info", {}) or {}
            if info.get("status") not in ("allowed", "allowed_warning"):
                raise RateLimited(f"rate limited: {info.get('status')}")
        elif t == "result":
            self.result_event = ev
            if ev.get("is_error"):
                text = str(ev.get("result", ""))
                if RATE_RE.search(text):
                    raise RateLimited(text[:300])
        return False

    def finish(self, timed_out: bool, seconds: float) -> AgentRun:
        ev = self.result_event
        error = None
        if ev is not None:
            prompt_tok, comp_tok = _tokens(ev.get("usage"))
            if ev.get("is_error"):
                error = str(ev.get("result", ""))
            final = str(ev.get("result") or self.final_text or "")
        else:
            prompt_tok = comp_tok = 0
            for u in self.assist_usage.values():
                p, c = _tokens(u)
                prompt_tok += p
                comp_tok += c
            final = self.final_text
        steps = list(self.steps)
        n = len(steps) + 1
        if timed_out:
            steps.append(make_step(self.run, n, "timeout", {}, "timed out", True))
        elif self.capped:
            steps.append(make_step(self.run, n, "final", {}, "step cap reached", False))
        else:
            steps.append(make_step(self.run, n, "final", {}, final, False))
        return AgentRun(steps=steps, final_text=final, prompt_tokens=prompt_tok, completion_tokens=comp_tok,
                        timed_out=timed_out, capped=self.capped, seconds=seconds, error=error)


def parse_agent_stream(lines: Iterable[str], run_name: str, max_steps: int, timed_out: bool = False,
                       seconds: float = 0.0) -> AgentRun:
    parser = StreamParser(run_name, max_steps)
    for line in lines:
        if parser.feed(line):
            break
    return parser.finish(timed_out, seconds)


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        pass


class ClaudeCLIBackend(Backend):
    name = "claude"

    def __init__(self, worker_model: Optional[str] = None, editor_model: Optional[str] = None):
        self.worker_model = worker_model
        self.editor_model = editor_model

    def complete(self, role: str, system: str, prompt: str, schema: Optional[dict] = None) -> Completion:
        cmd = build_complete_cmd(system, prompt, schema, self.editor_model)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=child_env(),
                                  cwd=tempfile.gettempdir())
        except subprocess.TimeoutExpired:
            raise BackendError("claude complete timed out after 300s")
        stderr = proc.stderr or ""
        try:
            obj = json.loads(proc.stdout or "")
        except ValueError:
            if RATE_RE.search(stderr):
                raise RateLimited(stderr[-300:])
            raise BackendError(f"claude exit {proc.returncode}: {stderr[-500:]}")
        if not isinstance(obj, dict):
            raise BackendError("claude returned non-object JSON")
        if obj.get("is_error"):
            msg = str(obj.get("result", "")) + stderr
            if RATE_RE.search(msg):
                raise RateLimited(msg[-300:])
            raise BackendError(f"claude error: {msg[-500:]}")
        if proc.returncode != 0:
            raise BackendError(f"claude exit {proc.returncode}: {stderr[-500:]}")
        text = str(obj.get("result") or "")
        if schema is not None:
            data = obj.get("structured_output")
            if not isinstance(data, dict):
                data = extract_json(text)
        else:
            data = extract_json(text)
        p, c = _tokens(obj.get("usage"))
        if not text and data is not None:
            text = json.dumps(data)
        return Completion(text=text, data=data, prompt_tokens=p, completion_tokens=c)

    def run_agent(self, run_name: str, system: str, task_prompt: str, workdir: Path, max_steps: int,
                  timeout_s: int) -> AgentRun:
        cmd = build_agent_cmd(system + AGENT_SUFFIX, task_prompt, self.worker_model)
        err_file = tempfile.TemporaryFile(mode="w+")
        proc = subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.PIPE, stderr=err_file,
                                text=True, cwd=str(workdir), env=child_env())
        state = {"timed_out": False}

        def on_timeout():
            state["timed_out"] = True
            _kill_group(proc.pid)

        timer = threading.Timer(timeout_s, on_timeout)
        parser = StreamParser(run_name, max_steps)
        killed = False
        start = time.monotonic()
        timer.start()
        try:
            for line in proc.stdout:
                if parser.feed(line):
                    killed = True
                    _kill_group(proc.pid)
                    break
        finally:
            timer.cancel()
            _kill_group(proc.pid)
            proc.wait()
            proc.stdout.close()
        rc = proc.returncode
        seconds = time.monotonic() - start
        timed_out = state["timed_out"]
        if rc != 0 and not parser.steps and parser.result_event is None and not killed and not timed_out:
            err_file.seek(0)
            tail = err_file.read()[-500:]
            err_file.close()
            raise BackendError(f"claude agent exit {rc}: {tail}")
        err_file.close()
        return parser.finish(timed_out, seconds)
