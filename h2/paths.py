from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class Paths:
    root: Path
    tasks_dir: Path
    harness_dir: Path
    runs_dir: Path
    library_dir: Path
    results_path: Path

    @staticmethod
    def default() -> "Paths":
        root = Path(__file__).resolve().parents[1]
        return Paths(
            root=root,
            tasks_dir=root / "tasks",
            harness_dir=root / "harness" / "base",
            runs_dir=root / "runs",
            library_dir=root / "library",
            results_path=root / "results.md",
        )

    @staticmethod
    def with_root(root: Path) -> "Paths":
        base = Paths.default()
        root = Path(root)
        return Paths(
            root=base.root,
            tasks_dir=base.tasks_dir,
            harness_dir=base.harness_dir,
            runs_dir=root / "runs",
            library_dir=root / "library",
            results_path=root / "results.md",
        )


@dataclass
class Config:
    max_steps: int = 20
    timeout_s: int = 240
    max_edits: int = 2
    max_edit_chars: int = 1200
    lib_top_k: int = 2

    @staticmethod
    def from_env() -> "Config":
        return Config(
            max_steps=int(os.environ.get("H2_MAX_STEPS", "20")),
            timeout_s=int(os.environ.get("H2_TIMEOUT", "240")),
        )
