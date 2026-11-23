import json
from pathlib import Path
from typing import Callable, Optional, Tuple


def _fenced(t: str) -> Optional[str]:
    if "```" not in t:
        return None
    parts = t.split("```")
    if len(parts) < 3:
        return None
    body = parts[1]
    if body.startswith("json"):
        body = body[4:]
    return body.strip()


def _sliced(t: str) -> Optional[str]:
    a, b = t.find("{"), t.rfind("}")
    if a == -1 or b <= a:
        return None
    return t[a:b + 1]


def extract_json(text: Optional[str]) -> Optional[dict]:
    if not text:
        return None
    t = text.strip()
    for cand in (t, _fenced(t), _sliced(t)):
        if not cand:
            continue
        try:
            v = json.loads(cand)
        except ValueError:
            continue
        if isinstance(v, dict):
            return v
    return None


def call_json(backend, role: str, system: str, prompt: str, schema, validate: Callable[[dict], None],
              log_dir, retries: int = 1, log_name: Optional[str] = None) -> Tuple[Optional[dict], int]:
    """Returns (validated data or None, total tokens). Never raises on invalid content."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    name = log_name or role
    (log_dir / f"{name}.txt").write_text(system + "\n\n----\n\n" + prompt, encoding="utf-8")
    total = 0
    last_msg = ""
    for attempt in range(retries + 1):
        p = prompt
        if attempt > 0:
            suffix = f"\n\nYour previous reply was invalid: {last_msg}. Reply again with valid JSON only."
            p = prompt + suffix
            (log_dir / f"{name}.retry.txt").write_text(suffix, encoding="utf-8")
        comp = backend.complete(role, system, p, schema)
        total += comp.prompt_tokens + comp.completion_tokens
        (log_dir / f"{name}.response.txt").write_text(comp.text or "", encoding="utf-8")
        data = comp.data if isinstance(comp.data, dict) else extract_json(comp.text)
        if data is None:
            last_msg = "reply was not a JSON object"
            continue
        try:
            validate(data)
        except ValueError as e:
            last_msg = str(e) or "invalid content"
            continue
        return data, total
    return None, total
