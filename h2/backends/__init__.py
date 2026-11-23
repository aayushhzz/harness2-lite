import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class BackendError(Exception):
    pass


class RateLimited(BackendError):
    pass


@dataclass
class Completion:
    text: str
    data: Optional[dict]
    prompt_tokens: int
    completion_tokens: int

    @property
    def tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class Backend(ABC):
    name: str

    @abstractmethod
    def complete(self, role: str, system: str, prompt: str, schema: Optional[dict] = None) -> Completion:
        ...

    @abstractmethod
    def run_agent(self, run_name: str, system: str, task_prompt: str, workdir: Path, max_steps: int,
                  timeout_s: int):
        ...


def get_backend(name: Optional[str], worker_model: Optional[str], editor_model: Optional[str]) -> Backend:
    from h2.paths import Paths  # local import keeps package import light

    name = name or os.environ.get("HARNESS_BACKEND") or "claude"
    if name == "anthropic":
        raise BackendError("HARNESS_BACKEND=anthropic is not implemented: this project uses the local claude login, not an API key")
    if name == "claude":
        from h2.backends.claude_cli import ClaudeCLIBackend
        return ClaudeCLIBackend(
            worker_model or os.environ.get("H2_WORKER_MODEL") or None,
            editor_model or os.environ.get("H2_EDITOR_MODEL") or None,
        )
    if name == "ollama":
        from h2.backends.ollama import OllamaBackend
        return OllamaBackend(
            worker_model or os.environ.get("OLLAMA_WORKER_MODEL") or "qwen3:4b-instruct",
            editor_model or os.environ.get("OLLAMA_EDITOR_MODEL") or "qwen3:8b",
            host=os.environ.get("OLLAMA_HOST") or "http://localhost:11434",
        )
    if name == "fake":
        from h2.backends.fake import FakeBackend
        golden = os.environ.get("H2_FAKE_GOLDEN") or str(Paths.default().root / "tests" / "golden")
        return FakeBackend(Path(golden), worker_model, editor_model)
    raise BackendError(f"unknown backend: {name}")
