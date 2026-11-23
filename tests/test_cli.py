import re

import pytest

from h2 import cli
from h2.backends import RateLimited
from h2.backends.fake import FakeBackend
from support import ScriptBackend

LINE_RE = re.compile(r"^e01 ref:\d+ steps \| inv:\w+ \| dom:\w+ \| merged \d+/\d+ \| lessons \d+ \| tokens [\d,]+$")


def test_help_lists_commands(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--help"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    for cmd in ("list", "doctor", "run", "eval", "show"):
        assert cmd in out


def test_unknown_task_exit_2(paths, capsys):
    assert cli.main(["--backend", "fake", "--root", str(paths.runs_dir.parent), "show", "zzz"]) == 2
    assert cli.main(["--backend", "fake", "--root", str(paths.runs_dir.parent), "run", "--tasks", "zzz"]) == 2


def test_list_prints_16(capsys):
    assert cli.main(["list"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 16 and lines[0].startswith("e01 evolve ")


def test_doctor_fake_ok(capsys):
    assert cli.main(["--backend", "fake", "doctor"]) == 0
    assert "OK" in capsys.readouterr().out


def test_run_limit_and_summary_line_shape(paths, capsys):
    root = str(paths.runs_dir.parent)
    assert cli.main(["--backend", "fake", "--root", root, "run", "--tasks", "e01,e02", "--limit", "1"]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert LINE_RE.match(out[1]), out
    assert out[-1] == "done 1, library entries: 1"


def test_show_prints_evidence_lines_from_real_steps(paths, capsys):
    root = str(paths.runs_dir.parent)
    assert cli.main(["--backend", "fake", "--root", root, "run", "--tasks", "e01"]) == 0
    capsys.readouterr()
    assert cli.main(["--backend", "fake", "--root", root, "show", "e01"]) == 0
    out = capsys.readouterr().out
    assert "--- decision inv-1: MERGE (applied, source=llm)" in out
    assert "  evidence: candidate_invariant:s1 | " in out


def test_anthropic_backend_not_implemented_exit_2(paths, capsys, monkeypatch):
    monkeypatch.delenv("HARNESS_BACKEND", raising=False)
    assert cli.main(["--backend", "anthropic", "--root", str(paths.runs_dir.parent), "run", "--tasks", "e01"]) == 2
    assert "not implemented" in capsys.readouterr().err


def test_rate_limited_exit_3(paths, capsys, monkeypatch):
    class Limited(ScriptBackend):
        def run_agent(self, *a, **k):
            raise RateLimited("usage limit reached")
    monkeypatch.setattr(cli, "get_backend", lambda *a, **k: Limited({}))
    assert cli.main(["--root", str(paths.runs_dir.parent), "run", "--tasks", "e01"]) == 3
    assert "rerun the same command later" in capsys.readouterr().err
    assert not (paths.runs_dir / "e01" / "DONE").exists()
