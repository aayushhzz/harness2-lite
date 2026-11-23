import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from h2.backends.fake import FakeBackend  # noqa: E402
from h2.harness import load_harness  # noqa: E402
from h2.paths import Config, Paths  # noqa: E402


@pytest.fixture
def paths(tmp_path):
    return Paths.with_root(tmp_path)


@pytest.fixture
def fake():
    return FakeBackend(ROOT / "tests" / "golden")


@pytest.fixture
def cfg():
    return Config(max_steps=8, timeout_s=30)


@pytest.fixture
def base_h():
    return load_harness(ROOT / "harness" / "base")
