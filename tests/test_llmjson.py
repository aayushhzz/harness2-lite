import pytest

from h2.backends import BackendError, Completion
from h2.llmjson import call_json, extract_json


class Stub:
    name = "stub"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, role, system, prompt, schema=None):
        self.calls.append(prompt)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return Completion(text=r, data=None, prompt_tokens=3, completion_tokens=2)


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json('Sure! {"a": 3} hope it helps') == {"a": 3}
    assert extract_json("garbage") is None


def test_call_json_retries_once_then_none(tmp_path):
    stub = Stub(["garbage", "more garbage"])
    data, tokens = call_json(stub, "propose_invariant", "ROLE: propose_invariant\n", "P", None,
                             lambda d: None, tmp_path)
    assert data is None
    assert tokens == 10
    assert len(stub.calls) == 2


def test_call_json_logs_prompt_before_call(tmp_path):
    stub = Stub([BackendError("boom")])
    with pytest.raises(BackendError):
        call_json(stub, "role_x", "ROLE: role_x\n", "P", None, lambda d: None, tmp_path / "prompts")
    assert (tmp_path / "prompts" / "role_x.txt").exists()


def test_validate_error_message_appended_on_retry(tmp_path):
    stub = Stub(['{"a": 1}', '{"a": 2}'])

    def validate(d):
        if d["a"] == 1:
            raise ValueError("bad key")
    data, _ = call_json(stub, "r", "ROLE: r\n", "P", None, validate, tmp_path)
    assert data == {"a": 2}
    assert "Your previous reply was invalid: bad key" in stub.calls[1]
    assert (tmp_path / "r.retry.txt").exists()
