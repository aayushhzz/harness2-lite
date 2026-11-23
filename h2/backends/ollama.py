import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from h2.backends import Backend, BackendError, Completion
from h2.llmjson import extract_json
from h2.react import run_react


class OllamaBackend(Backend):
    name = "ollama"

    def __init__(self, worker_model: str, editor_model: str, host: str = "http://localhost:11434"):
        self.worker_model = worker_model
        self.editor_model = editor_model
        self.host = host.rstrip("/")

    def _chat(self, model: str, messages: list, schema: Optional[dict] = None):
        body = {"model": model, "messages": messages, "stream": False, "think": False,
                "options": {"temperature": 0, "num_ctx": 8192}}
        if schema is not None:
            body["format"] = schema
        req = urllib.request.Request(self.host + "/api/chat", data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                obj = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise BackendError(f"ollama not reachable: {e}")
        text = (obj.get("message") or {}).get("content", "") or ""
        return text, int(obj.get("prompt_eval_count", 0) or 0), int(obj.get("eval_count", 0) or 0)

    def complete(self, role: str, system: str, prompt: str, schema: Optional[dict] = None) -> Completion:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        text, p, c = self._chat(self.editor_model, messages, schema)
        return Completion(text=text, data=extract_json(text), prompt_tokens=p, completion_tokens=c)

    def run_agent(self, run_name: str, system: str, task_prompt: str, workdir: Path, max_steps: int,
                  timeout_s: int):
        def chat(messages):
            return self._chat(self.worker_model, messages)
        return run_react(run_name, chat, system, task_prompt, workdir, max_steps, timeout_s)
