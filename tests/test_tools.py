import sys

from h2.tools import Sandbox


def test_read_write_inside_sandbox(tmp_path):
    sb = Sandbox(tmp_path)
    assert sb.write_file("sub/a.txt", "hello") == ("wrote 5 chars", False)
    assert sb.read_file("sub/a.txt") == ("hello", False)


def test_path_escape_blocked(tmp_path):
    sb = Sandbox(tmp_path)
    for p in ("../x", "/etc/hosts"):
        assert sb.read_file(p)[1] is True
        assert sb.write_file(p, "x")[1] is True


def test_symlink_escape_blocked(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("s", encoding="utf-8")
    (root / "link").symlink_to(secret)
    sb = Sandbox(root)
    assert sb.read_file("link")[1] is True
    assert sb.write_file("link", "x")[1] is True


def test_missing_file_is_error(tmp_path):
    assert Sandbox(tmp_path).read_file("nope") == ("file not found: nope", True)


def test_run_shell_exit_code_error_flag(tmp_path):
    sb = Sandbox(tmp_path)
    assert sb.run_shell("echo hi") == ("hi\n", False)
    assert sb.run_shell("exit 3")[1] is True


def test_run_shell_timeout(tmp_path):
    assert Sandbox(tmp_path).run_shell("sleep 5", timeout=1) == ("command timed out after 1s", True)


def test_output_truncation(tmp_path):
    out, err = Sandbox(tmp_path).run_shell("head -c 5000 /dev/zero | tr '\\0' 'x'")
    assert err is False
    assert out.startswith("…[truncated]")
    assert len(out) <= 2020


def test_bad_args_invalid_call(tmp_path):
    sb = Sandbox(tmp_path)
    out, err = sb.dispatch("read_file", {})
    assert err and out.startswith("invalid tool call")
    assert sb.dispatch("nope", {})[1] is True
    assert sb.dispatch("write_file", {"path": 1, "content": "x"})[1] is True
    assert sb.dispatch("run_shell", "ls")[1] is True
