import io
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

from h2.backends import BackendError, RateLimited
from h2.backends.claude_cli import (ClaudeCLIBackend, StreamParser, build_agent_cmd, build_complete_cmd,
                                    parse_agent_stream)
from h2.backends.ollama import OllamaBackend
from h2.tools import child_env

FIX = Path(__file__).parent / "fixtures"


def _lines(name):
    return (FIX / name).read_text(encoding="utf-8").splitlines()


def test_stream_ok():
    run = parse_agent_stream(_lines("claude_stream_ok.jsonl"), "candidate_invariant", max_steps=10)
    tools = [s.tool for s in run.steps]
    assert tools == ["read_file", "read_file", "final"]
    assert run.steps[0].args == {"path": "/abs/x.py"}
    assert run.steps[1].is_error is True
    assert sum(1 for s in run.steps if s.is_error and s.tool != "final") == 1
    assert run.tokens == 4 + 37840 + 1060 + 317
    assert run.final_text == "Fixed the bug."
    assert run.steps[-1].tool == "final" and run.steps[-1].id == "candidate_invariant:s3"


def test_stream_cap_kills():
    parser = StreamParser("candidate_domain", max_steps=3)
    fired = [parser.feed(line) for line in _lines("claude_stream_cap.jsonl")]
    assert fired.index(True) == 6  # the 4th tool_use line (index 6 in the file)
    assert parser.capped is True
    run = parser.finish(timed_out=False, seconds=1.0)
    assert len([s for s in run.steps if s.tool != "final"]) == 3
    assert run.capped is True and run.steps[-1].tool == "final"


def test_stream_without_result_event_sums_usage_deduped_by_message_id():
    lines = [
        '{"type":"assistant","message":{"id":"m1","content":[],"usage":{"input_tokens":5,"output_tokens":1}}}',
        '{"type":"assistant","message":{"id":"m1","content":[],"usage":{"input_tokens":7,"output_tokens":2}}}',
        '{"type":"assistant","message":{"id":"m2","content":[],"usage":{"input_tokens":3,"output_tokens":4}}}',
    ]
    run = parse_agent_stream(lines, "reference", max_steps=5, timed_out=True)
    assert run.prompt_tokens == 10 and run.completion_tokens == 6
    assert run.steps[-1].tool == "timeout" and run.timed_out is True


def test_rate_limit_event_raises():
    parser = StreamParser("r", 5)
    with pytest.raises(RateLimited):
        parser.feed('{"type":"rate_limit_event","rate_limit_info":{"status":"rejected"}}')


def test_error_result_rate_limit_text_raises_ratelimited():
    parser = StreamParser("r", 5)
    with pytest.raises(RateLimited):
        parser.feed('{"type":"result","is_error":true,"result":"Claude AI usage limit reached"}')


def test_error_result_other_text_kept_as_error():
    run = parse_agent_stream(['{"type":"result","is_error":true,"result":"bad thing","usage":{}}'], "r", 5)
    assert run.error == "bad thing"
    assert run.steps[-1].tool == "final"


def test_build_agent_cmd():
    cmd = build_agent_cmd("SYS", "PROMPT", None)
    assert cmd[:3] == ["claude", "-p", "PROMPT"]
    i = cmd.index("--setting-sources")
    assert cmd[i + 1] == ""
    assert cmd[cmd.index("--tools") + 1] == "Read,Write,Bash"
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"
    assert cmd[cmd.index("--output-format") + 1] == "stream-json"
    assert "--bare" not in cmd and "--model" not in cmd
    assert build_agent_cmd("S", "P", "haiku")[-2:] == ["--model", "haiku"]


def test_build_complete_cmd_schema_and_tools_empty():
    cmd = build_complete_cmd("SYS", "P", {"type": "object"}, None)
    assert cmd[cmd.index("--tools") + 1] == ""
    assert json.loads(cmd[cmd.index("--json-schema") + 1]) == {"type": "object"}
    assert "--bare" not in cmd and "--model" not in cmd
    assert "--no-session-persistence" in cmd and "--strict-mcp-config" in cmd


def test_child_env_strips_api_keys_and_prefixes_path(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "not-a-real-token")
    env = child_env()
    assert "ANTHROPIC_API_KEY" not in env and "ANTHROPIC_AUTH_TOKEN" not in env
    assert env["PATH"].startswith(os.path.dirname(sys.executable))


def test_complete_parses_structured_output(monkeypatch):
    raw = (FIX / "claude_complete_ok.json").read_text(encoding="utf-8")

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout=raw, stderr="")
    monkeypatch.setattr("h2.backends.claude_cli.subprocess.run", fake_run)
    comp = ClaudeCLIBackend().complete("doctor", "ROLE: doctor\n", "P", {"type": "object"})
    assert comp.data == {"ok": True}
    assert comp.tokens == 2 + 5691 + 1067 + 52


def test_complete_rate_limit_is_ratelimited(monkeypatch):
    raw = json.dumps({"is_error": True, "result": "You have hit your usage limit"})

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 1, stdout=raw, stderr="")
    monkeypatch.setattr("h2.backends.claude_cli.subprocess.run", fake_run)
    with pytest.raises(RateLimited):
        ClaudeCLIBackend().complete("doctor", "ROLE: doctor\n", "P", None)


def test_ollama_complete_tokens(monkeypatch):
    body = json.dumps({"message": {"content": "{}"}, "prompt_eval_count": 7, "eval_count": 3}).encode()
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: io.BytesIO(body))
    comp = OllamaBackend("w", "e").complete("propose_invariant", "ROLE: propose_invariant\n", "P")
    assert comp.tokens == 10
    assert comp.data == {}


def test_ollama_unreachable_is_backend_error(monkeypatch):
    import urllib.error

    def boom(req, timeout=None):
        raise urllib.error.URLError("connection refused")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(BackendError, match="ollama not reachable"):
        OllamaBackend("w", "e").complete("doctor", "ROLE: doctor\n", "P")
