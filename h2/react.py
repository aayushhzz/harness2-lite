import time

from typing import Callable, List, Tuple

from h2.llmjson import extract_json
from h2.tools import Sandbox
from h2.trace import AgentRun, Step, make_step

REACT_PROTOCOL = (
    "\n\n# Protocol\n"
    "Reply with exactly one JSON object and nothing else: "
    '{"tool":"read_file|write_file|run_shell|final","args":{...}}. '
    'Use the final tool with args {"text": "..."} when you are done.'
)
TOOLS = ("read_file", "write_file", "run_shell", "final")

def run_react(run_name: str, chat: Callable[[List[dict]], Tuple[str, int, int]], system: str, task_prompt: str,
              workdir, max_steps: int, timeout_s: float) -> AgentRun:
    sandbox = Sandbox(workdir)
    messages = [
        {"role": "system", "content": system + REACT_PROTOCOL},
        {"role": "user", "content": task_prompt},
    ]
    steps: List[Step] = []
    n = 0
    pt = ct = 0
    timed_out = capped = False
    final_text = ""
    start = time.monotonic()

    def terminal(tool: str, result: str, is_error: bool) -> None:
        steps.append(make_step(run_name, len(steps) + 1, tool, {}, result, is_error))

    while True:
        if time.monotonic() - start >= timeout_s:
            timed_out = True
            terminal("timeout", "timed out", True)
            break
        text, p, c = chat(messages)
        pt += p
        ct += c
        obj = extract_json(text)
        valid = isinstance(obj, dict) and obj.get("tool") in TOOLS
        if valid and obj["tool"] == "final":
            args = obj.get("args") if isinstance(obj.get("args"), dict) else {}
            final_text = str(args.get("text", ""))
            terminal("final", final_text, False)
            break
        if n >= max_steps:
            capped = True
            terminal("final", "step cap reached", False)
            break
        messages.append({"role": "assistant", "content": text or ""})
        if not valid:
            n += 1
            steps.append(make_step(run_name, len(steps) + 1, "invalid", {}, "could not parse action", True))
            messages.append({"role": "user", "content": "Invalid action. Reply with one JSON object."})
            continue
        args = obj.get("args") if isinstance(obj.get("args"), dict) else {}
        result, is_err = sandbox.dispatch(obj["tool"], args)
        n += 1
        steps.append(make_step(run_name, len(steps) + 1, obj["tool"], args, result, is_err))
        messages.append({"role": "user", "content": "RESULT: " + result})

    return AgentRun(
        steps=steps, final_text=final_text, prompt_tokens=pt, completion_tokens=ct,
        timed_out=timed_out, capped=capped, seconds=time.monotonic() - start, error=None,
    )
