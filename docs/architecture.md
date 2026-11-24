# Architecture & Pipeline Internals

This document details the Propose–Probe–Compose pipeline, strict oracle isolation, and backend contract in `harness2-lite`.

## Pipeline Flow (`h2/ppc.py`)

For each task, `run_ppc` executes a single `k = 1` harness improvement step on a frozen model:

1. **Reference Run (`h2/probe.py`):** Copies `tasks/<id>/repo/` into an isolated temporary workspace and executes the agent under `harness/base/` (`system.md`, `guardrails.md`, `tool_guidance.md`, `skills/`). Logs trajectory (`reference.jsonl`), metadata (`reference.meta.json`), and repo diff (`reference.diff`).
2. **Propose (`h2/propose.py`):** Retrieves relevant prior lessons from `library/index.json` (keyword overlap over `EXPERIENCE.md`) and asks the editor model for two structured edit proposals (`{path, op, old, new}`):
   - **Invariant candidate:** General workflow/discipline improvements.
   - **Domain candidate:** Task-family-specific guidance.
3. **Probe (`h2/probe.py`):** Applies each valid proposal to a copy of the base harness and runs the agent in fresh temporary workspaces under matched conditions (`candidate_invariant.*`, `candidate_domain.*`).
4. **Label-Free Behavioral Contrast (`h2/signals.py`, `h2/contrast.py`):** Extracts deterministic trajectory signals (step counts, tool errors, repeated calls, whether self-verification commands ran, diff size) and contrasts each candidate against the reference without seeing any grader score.
5. **Evidence-Cited Compose (`h2/compose.py`):** Merges surviving hunks into `composed_harness/` and writes `composed.diff` with a structured decision header. Any step citation invented by the model is discarded and replaced with code-derived step IDs (`source=code_fallback`).
6. **Final Run & Reflect (`h2/reflect.py`, `h2/library.py`):** Runs the composed harness, then writes evidence-backed lessons into `library/<task>/EXPERIENCE.md` and `library/index.json`.

## Oracle Isolation

No module in the evolution path (`propose`, `probe`, `signals`, `contrast`, `compose`, `reflect`) imports or accesses hidden tests:

- Hidden pytest suites live under `tasks/<id>/hidden/test_hidden.py`.
- Only `h2/oracle.py` and `h2/evalrun.py` (lazily imported by `h2/cli.py` for `h2 eval`) execute hidden tests.
- `tests/test_isolation.py` enforces this boundary statically.
- During `h2 eval`, `library/` is opened read-only and any agent step referencing `tasks/` or `hidden` is flagged via `oracle_peek` in `meta.json`.

## Backend Interface (`h2/backends/__init__.py`)

Backends implement two methods on `Backend`:

- `complete(role, system, prompt, schema) -> Completion`: Single structured JSON call for editor/judge roles.
- `run_agent(run_name, system, task_prompt, workdir, max_steps, timeout_s) -> AgentRun`: Runs the worker agent on a temporary workspace and returns parsed steps, token counts, and terminal status.

Built-in backends: `claude` (`h2/backends/claude_cli.py`, local Claude Pro CLI with isolated flags and stripped API key env vars), `ollama` (`h2/backends/ollama.py`), and `fake` (`h2/backends/fake.py`, deterministic offline backend backed by `tests/golden/`).
