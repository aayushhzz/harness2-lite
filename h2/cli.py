import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from h2.backends import BackendError, RateLimited, get_backend
from h2.harness import load_harness
from h2.library import Library
from h2.paths import Config, Paths
from h2.ppc import run_ppc
from h2.show import ShowError, render_show
from h2.tasks import list_tasks

DOCTOR_SCHEMA = {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}


def _paths(args) -> Paths:
    return Paths.with_root(Path(args.root)) if args.root else Paths.default()


def cmd_list(args, paths: Paths) -> int:
    for t in list_tasks(paths, "all"):
        print(f"{t.id} {t.group} {t.title}")
    return 0


def cmd_doctor(args, paths: Paths) -> int:
    ok = True
    print(f"python {sys.version.split()[0]}")
    if sys.version_info < (3, 9):
        print("FAIL: python 3.9 or newer is required")
        return 1
    try:
        backend = get_backend(args.backend, args.worker_model, args.editor_model)
    except BackendError as e:
        print(f"FAIL: {e}")
        return 1
    print(f"backend {backend.name}")
    if backend.name == "claude":
        try:
            proc = subprocess.run(["claude", "auth", "status"], capture_output=True, text=True, timeout=60)
            info = json.loads(proc.stdout or "{}")
            method = info.get("authMethod")
            print(f"claude auth: authMethod={method}")
            if method != "claude.ai":
                print("warning: expected authMethod claude.ai (local Claude Pro login)")
        except (OSError, ValueError, subprocess.TimeoutExpired) as e:
            print(f"warning: could not read claude auth status: {e}")
        print("note: API key environment variables are stripped from claude subprocesses")
    try:
        comp = backend.complete("doctor", "ROLE: doctor\nReply with JSON only, matching the schema.",
                                'Reply with {"ok": true}.', DOCTOR_SCHEMA)
        print(f"OK tokens={comp.tokens}")
    except BackendError as e:
        print(f"FAIL: {e}")
        ok = False
    return 0 if ok else 1


def cmd_run(args, paths: Paths, cfg: Config) -> int:
    tasks = list_tasks(paths, args.tasks or "evolve")
    if args.limit:
        tasks = tasks[:args.limit]
    backend = get_backend(args.backend, args.worker_model, args.editor_model)
    base_h = load_harness(paths.harness_dir)
    library = Library(paths.library_dir)
    n = len(tasks)
    print(f"about {10 * n} model calls (4 agent runs + 6 editor calls per task); Ctrl-C to stop; rerun resumes")
    done = 0
    for task in tasks:
        run_dir = paths.runs_dir / task.id
        if (run_dir / "DONE").exists() and not args.force:
            print(f"skip {task.id} (done)")
            done += 1
            continue
        res = run_ppc(task, base_h, backend, cfg, run_dir, library=library, reflect_enabled=True,
                      execute_final=True, reference=None)
        ref_meta = json.loads((run_dir / "reference.meta.json").read_text(encoding="utf-8"))
        comp = json.loads((run_dir / "compose.json").read_text(encoding="utf-8"))
        hunks = len(comp.get("decisions", []))
        total = int(ref_meta.get("tokens", 0)) + res.tokens_improve + res.tokens_final
        inv = res.labels.get("invariant", "skipped")
        dom = res.labels.get("domain", "skipped")
        print(f"{task.id} ref:{ref_meta.get('steps', 0)} steps | inv:{inv} | dom:{dom} | "
              f"merged {len(res.merged)}/{hunks} | lessons {res.lessons_written} | tokens {total:,}")
        done += 1
    print(f"done {done}, library entries: {len(library.entries())}")
    return 0


def cmd_eval(args, paths: Paths, cfg: Config) -> int:
    from h2.evalrun import run_eval  # lazy: keeps hidden-test code out of the worker path
    backend = get_backend(args.backend, args.worker_model, args.editor_model)
    if not Library(paths.library_dir, readonly=True).entries():
        print("warning: library is empty: run `h2 run --tasks evolve` first")
    text = run_eval(paths, backend, cfg, selector=args.tasks or "heldout", limit=args.limit, force=args.force)
    print(text, end="")
    return 0


def cmd_show(args, paths: Paths, cfg: Config) -> int:
    try:
        list_tasks(paths, args.task)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    try:
        print(render_show(paths, args.task, args.arm), end="")
    except ShowError as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="h2", description="Harness^2-lite: Propose-Probe-Compose on a frozen model.")
    p.add_argument("--backend", default=None, help="claude (default), ollama, fake")
    p.add_argument("--worker-model", default=None)
    p.add_argument("--editor-model", default=None)
    p.add_argument("--root", default=None, help="write runs/, library/ and results.md under DIR")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="list tasks")
    sub.add_parser("doctor", help="check python, backend login and one tiny model call")
    r = sub.add_parser("run", help="run Propose-Probe-Compose on evolve tasks (reflections go to library)")
    r.add_argument("--tasks", default="evolve")
    r.add_argument("--limit", type=int, default=None)
    r.add_argument("--force", action="store_true")
    e = sub.add_parser("eval", help="held-out evaluation: base, pppc, pppc_lib")
    e.add_argument("--tasks", default="heldout")
    e.add_argument("--limit", type=int, default=None)
    e.add_argument("--force", action="store_true")
    s = sub.add_parser("show", help="render the composed diff with cited evidence")
    s.add_argument("task")
    s.add_argument("--arm", default=None, choices=["base", "pppc", "pppc_lib"])
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = _paths(args)
        cfg = Config.from_env()
        handlers = {"list": cmd_list, "doctor": cmd_doctor, "run": cmd_run, "eval": cmd_eval, "show": cmd_show}
        if args.command in ("list", "doctor"):
            return handlers[args.command](args, paths)
        return handlers[args.command](args, paths, cfg)
    except RateLimited:
        print("Claude usage limit reached; rerun the same command later to resume", file=sys.stderr)
        return 3
    except BackendError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
