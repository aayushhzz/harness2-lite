# harness2-lite

Harness^2-lite is one Propose-Probe-Compose step plus an experience library, run on a frozen model. It is a small, local reimplementation of the idea in Xu et al., "Harness^2" (arXiv 2610.14224): instead of changing the model, the agent's *harness* (system prompt, guardrails, tool guidance, skills) is treated as a set of plain files that can be edited, diffed and reviewed.

The project ships 16 synthetic Python repositories (10 `evolve` tasks used to improve the harness, 6 `heldout` tasks used only to score it). Each repository has one subtle bug and a hidden pytest file that the agent never sees. For each evolve task, the pipeline runs the agent once with the current harness (the reference), asks an editor model for an invariant and a domain-specific harness edit, probes the agent under each candidate, labels each edit by observed behaviour contrast, composes the surviving edits, and reruns the agent on the composed harness. Reflections backed by evidence go into a library that later tasks read.

## Terms notice

This is for personal local use. It drives the locally logged-in `claude` CLI on a Claude Pro subscription (`claude auth status` must show `authMethod: claude.ai`). Sharing or deploying it for other people requires switching to API-key authentication under Anthropic's Agent SDK terms. `HARNESS_BACKEND=anthropic` is deliberately not implemented, and no `ANTHROPIC_API_KEY` is read or set anywhere in this project.

## Install

Python 3.9 or newer. There are no runtime dependencies beyond the standard library and pytest. There is no `pyproject.toml`; packaging uses `setup.py` and `setup.cfg`, which works with the pip that ships in a fresh venv.

```
python3 -m venv .venv && . .venv/bin/activate && pip install -e .
h2 doctor
```

`h2 doctor` checks the Python version, the backend, the `claude auth status` login (warns if it is not `claude.ai`) and makes one tiny structured model call.

## Quick start

Offline smoke test (no model calls, deterministic fake backend, writes into a temporary root):

```
h2 --backend fake --root /tmp/h2-demo run --tasks e01,e02
h2 --backend fake --root /tmp/h2-demo eval --limit 2
pytest
```

Small live demo on the Claude login:

```
H2_WORKER_MODEL=haiku h2 run --tasks e01
h2 show e01
```

Full run and held-out evaluation:

```
H2_WORKER_MODEL=haiku h2 run --tasks evolve
h2 eval
```

Quota advice: each task costs about 4 agent runs plus 6 editor calls. Every agent run reads roughly 40k tokens of Claude Code context, most of it cache reads. Set `H2_WORKER_MODEL=haiku` to spend less quota on the worker. `--limit N` runs only the first N tasks. If the usage limit is reached, the command exits with code 3; rerun the same command later and it resumes at the first task without a `DONE` marker.

## Commands reference

| Command | What it does |
|---|---|
| `h2 list` | Prints `<id> <group> <title>` for all 16 tasks. |
| `h2 doctor` | Python version, backend, claude login, one tiny model call. Exit 0 or 1. |
| `h2 run --tasks <evolve\|heldout\|all\|id,id> [--limit N] [--force]` | Runs the pipeline per task and writes `runs/<id>/`. Default `evolve`. Tasks with `runs/<id>/DONE` are skipped unless `--force`. Reflections are written to `library/`. |
| `h2 eval [--tasks heldout] [--limit N] [--force]` | Runs the three arms (base, pppc, pppc_lib) on held-out tasks, scores them with the hidden tests, and writes `runs/eval/<id>/summary.json` and `results.md`. The library is opened read-only. |
| `h2 show <task> [--arm base\|pppc\|pppc_lib]` | Renders the composed diff with the cited evidence (real step lines from the logs). |

Global options go before the subcommand: `--backend {claude,ollama,fake}`, `--worker-model M`, `--editor-model M`, `--root DIR` (writes `runs/`, `library/` and `results.md` under DIR instead of the project).

Environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `HARNESS_BACKEND` | `claude` | `claude`, `ollama`, `fake`. `anthropic` exits with an error. |
| `H2_WORKER_MODEL` | CLI default | Model for agent runs (`haiku` saves quota). |
| `H2_EDITOR_MODEL` | CLI default | Model for propose, contrast, compose, reflect. |
| `H2_MAX_STEPS` | `20` | Tool-call cap per agent run. |
| `H2_TIMEOUT` | `240` | Wall-clock seconds per agent run. |
| `OLLAMA_WORKER_MODEL` | `qwen3:4b-instruct` | Ollama worker model. |
| `OLLAMA_EDITOR_MODEL` | `qwen3:8b` | Ollama editor model. |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint. |
| `H2_FAKE_GOLDEN` | `tests/golden` | Golden fixes used by the fake backend. |

Exit codes: 0 success, 2 bad input or backend error, 3 Claude usage limit reached (rerun later), 130 interrupted.

## How it maps to the paper

| Paper concept | Where it lives |
|---|---|
| Harness H = editable component files | `harness/base/` loaded by `h2/harness.py` |
| Frozen model and agent | `h2/backends/*`, `run_agent` |
| Execution record (trajectory and deliverable) | `h2/trace.py`: `runs/<task>/<name>.jsonl`, `.meta.json`, `.diff` |
| Reference execution | `h2/probe.py`, run name `reference` |
| Propose invariant and domain candidates | `h2/propose.py`, prompts in `h2/prompts.py` |
| Probe under matched conditions in a throwaway copy | `h2/probe.py` (temporary workspace from the task repo) |
| Behavioural contrast, label-free | `h2/signals.py`, `h2/contrast.py` (`contrast.json`) |
| Compose with evidence-cited decisions | `h2/compose.py` (`composed.diff`, `compose.json`) |
| Reflect only when evidence supports it | `h2/reflect.py` |
| Improvement library (EXPERIENCE.md and index) | `h2/library.py`, `library/` |
| Library read before proposing | `propose()` receives retrieved lessons, logged in `runs/<task>/prompts/` |
| No grader verdict reaches editors | hidden tests only in `h2/oracle.py`, used only by `h2/evalrun.py` |
| Ablation arms | `h2 eval`: base (no edit), pppc (no library), pppc_lib (read-only library) |

## Output layout

```
runs/<task>/
  reference.jsonl  reference.meta.json  reference.diff  reference_ws/
  candidate_invariant.jsonl  candidate_invariant.meta.json  candidate_invariant.diff
  candidate_domain.jsonl     candidate_domain.meta.json     candidate_domain.diff
        (candidate_<scope>.meta.json alone, with "skipped", when the proposal was invalid)
  proposals.json        proposed edits, diffs and dropped edits with reasons
  contrast.json         labels, regression flags, cited steps, signal deltas per candidate
  composed.diff         compose log block, then the unified diff of base -> composed harness
  compose.json          decisions with source, cites and reasons
  composed_harness/     the composed harness files
  composed.jsonl  composed.meta.json  composed.run.diff  composed_ws/
  reflect.json          reflection outcome (entry written or skipped reason)
  reflect_lessons.json  kept and dropped lessons with reasons
  prompts/              every editor and judge prompt and raw reply (propose_*, contrast_*, compose, reflect)
  DONE                  marker written last; labels, merged hunks, tokens
library/
  index.json            entries: id, title, applies_when, labels, keywords, created
  <task>/EXPERIENCE.md  lessons with evidence ids
  <task>/harness/       the adopted harness for that task
runs/eval/<task>/
  reference*, pppc/, pppc_lib/, summary.json (hidden-test results live only here)
results.md              the three-arm table
```

`composed.diff` log format, one line per hunk:

```
# compose log task=e01 candidates=invariant,domain
# decision inv-1 merge applied=true source=llm cites=candidate_invariant:s2,reference:s3 reason=...
# decision dom-1 reject applied=false source=code_fallback cites=reference:s1 reason=...
# end log
<unified diff of base -> composed>
```

Every `cites` id exists in the run logs. Ids the model invents are discarded and replaced by code-derived ids, flagged `source=code_fallback`.

## Why selection never sees a metric

This differs from an autoresearch loop, which keeps an edit only when a metric improves. Here no step of the pipeline sees test results. Propose, probe, contrast, compose and reflect read only the trajectories, the diffs and the signals (step counts, tool errors, repeated calls, whether tests were run, diff size). The hidden pytest files are reachable only through `h2 eval`, after each harness is fixed.

How to verify:

```
grep -rliE "hidden|oracle" h2 --include=*.py   # lists only oracle.py, evalrun.py, cli.py (cli.py dispatches; evalrun is imported lazily)
pytest tests/test_isolation.py
```

Caveat: the agent's own shell can, in principle, read the `tasks/` tree. The eval flags any run whose steps mention `tasks/` or `hidden` (`oracle_peek` in `meta.json`) and prints a warning. The score is not changed by the flag.

## Backends

A backend implements two methods (`h2/backends/__init__.py`):

- `complete(role, system, prompt, schema) -> Completion` for single JSON replies (editor and judge roles). The system prompt's first line is `ROLE: <role>`.
- `run_agent(run_name, system, task_prompt, workdir, max_steps, timeout_s) -> AgentRun` runs one agent on a workspace and returns steps, tokens and a terminal step.

To add a backend, subclass `Backend`, implement both methods and register the name in `get_backend`.

Claude CLI specifics (`h2/backends/claude_cli.py`):

- Never passes `--bare`, which ignores the OAuth login and demands an API key.
- Always passes `--setting-sources ""`, so the user's Stop hooks (for example the Obsidian capture hook) do not run on every call.
- Always passes `--disable-slash-commands --strict-mcp-config --no-session-persistence`.
- Strips `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` from child processes and prefixes `PATH` with the venv bin directory.
- Agent runs use `--tools Read,Write,Bash --permission-mode dontAsk --output-format stream-json`, inside a temporary copy of the task repo. Each `tool_use` becomes one step. The step cap is enforced by killing the process group.

Ollama fallback: `HARNESS_BACKEND=ollama h2 run --tasks e01` (needs `qwen3:4b-instruct` and `qwen3:8b` pulled). Not exercised by the default tests except for one mocked call.

Fake backend: deterministic and offline, used by the tests and `--backend fake`. Its base harness never runs tests and fails the hidden tests. A harness that contains the marker `FAKE_VERIFY` runs its own test and passes. This exercises the whole pipeline without a model.

## Reading results honestly

- Single sample per cell, six held-out tasks. Agents are stochastic, so one task of difference is within noise.
- Tokens include cache reads, which dominate the Claude numbers. They are not a cost estimate.
- There may be a ceiling effect: if the base harness already passes everything, there is nothing to improve.
- The library is frozen during `h2 eval`, and reflections come only from evolve tasks. The held-out results therefore show what one composition step plus the library achieved on unseen tasks, not a converged harness.

## Simplifications vs the paper

- k = 1 only, no parallel or sequential recursion. Budget scaling is the paper's main lever; here it would multiply quota use.
- 4 of the 8 components: system prompt, guardrails, tool guidance and skills. No memory, scripts, subagents or plugins.
- Edits are structured `{path, op, old, new}` objects, and the diff is generated by `difflib`, not written by the editor.
- Retrieval is keyword overlap over EXPERIENCE.md text, not an agent browsing the index. Skills are inlined into the system prompt.
- One probe per candidate and one reference sample, not the paper's repeated samples.
- Deterministic fallbacks replace citations the model invents, and an edit that fails to apply is logged, not retried.
- The `anthropic` backend is not implemented (no API key by design). Parallel recursion, the other components, and harness reuse beyond EXPERIENCE text are also skipped on purpose.

## Development

```
. .venv/bin/activate
pytest                 # offline, uses the fake backend; about 25 seconds
pytest tests/test_tasks.py   # every buggy repo must fail its hidden test, every golden fix must pass
```

Adding a task: create `tasks/<id>/meta.json` (`{"group": "evolve|heldout", "title": "..."}`), `tasks/<id>/repo/` (buggy source files plus `task.md`, which must not contain the words `assert` or `hidden`, and must end with the line "There are no tests in this repository. Verify your fix yourself."), `tasks/<id>/hidden/test_hidden.py` (at least six asserts, flat imports), and `tests/golden/<id>/` (the fixed versions of the changed files). Then run `pytest tests/test_tasks.py -k <id>`. Do not tune a task after seeing live results.

Layout: `h2/` (package; `cli.py` dispatches, `oracle.py` and `evalrun.py` are the only modules that know the hidden tests), `harness/base/` (starting harness), `tasks/`, `tests/` (offline tests, `tests/golden/`, `tests/fixtures/`), `runs/` and `.venv/` (git-ignored), `library/` and `results.md` (generated outputs).
