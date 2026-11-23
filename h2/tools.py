import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Tuple

READ_LIMIT = 4000
OUT_LIMIT = 2000
API_KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


def child_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in API_KEYS}
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + env.get("PATH", "")
    return env


class Sandbox:
    def __init__(self, workdir):
        self.workdir = Path(workdir).resolve()

    def _resolve(self, path: str):
        p = (self.workdir / path).resolve()
        try:
            p.relative_to(self.workdir)
        except ValueError:
            return None
        return p

    def read_file(self, path: str) -> Tuple[str, bool]:
        p = self._resolve(path)
        if p is None:
            return "path outside working directory", True
        if not p.is_file():
            return f"file not found: {path}", True
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > READ_LIMIT:
            text = text[:READ_LIMIT] + "…[truncated]"
        return text, False

    def write_file(self, path: str, content: str) -> Tuple[str, bool]:
        p = self._resolve(path)
        if p is None:
            return "path outside working directory", True
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"wrote {len(content)} chars", False

    def run_shell(self, cmd: str, timeout: int = 30) -> Tuple[str, bool]:
        proc = subprocess.Popen(
            cmd, shell=True, cwd=str(self.workdir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=child_env(), start_new_session=True, text=True, errors="replace",
        )
        try:
            out, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            proc.communicate()
            return f"command timed out after {timeout}s", True
        if len(out) > OUT_LIMIT:
            out = "…[truncated]" + out[-OUT_LIMIT:]
        return out, proc.returncode != 0

    def dispatch(self, tool, args) -> Tuple[str, bool]:
        if not isinstance(args, dict):
            return "invalid tool call: args must be an object", True
        if tool == "read_file":
            if not isinstance(args.get("path"), str):
                return "invalid tool call: read_file needs string path", True
            return self.read_file(args["path"])
        if tool == "write_file":
            if not isinstance(args.get("path"), str) or not isinstance(args.get("content"), str):
                return "invalid tool call: write_file needs string path and content", True
            return self.write_file(args["path"], args["content"])
        if tool == "run_shell":
            if not isinstance(args.get("cmd"), str):
                return "invalid tool call: run_shell needs string cmd", True
            return self.run_shell(args["cmd"])
        return f"invalid tool call: unknown tool {tool}", True
