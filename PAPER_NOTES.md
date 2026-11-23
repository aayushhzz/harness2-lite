# Paper notes: Harness^2 (arXiv 2610.14224, Xu et al., Google Cloud AI Research, Oct 2026)

PDF is at `paper/harness2.pdf` (37 pages). Read via text extraction (pypdf in a scratch venv; the Read tool's PDF mode needs poppler, which is not installed). Sections used: 1 (intro), 2.1-2.3 (method), 3 (setup, Tables 1-2), 4 (ablation, Table 3), Appendix D.2/D.3 (library, 8 components).

## The mechanism in my own words

The model is frozen. Everything that can change is a set of plain files (the "harness"): system prompt, guardrails, memory, skills, tool guidance, scripts, subagents, a middleware plugin. Because they are files, an edit is a diff.

The hard part is the open world: a new task arrives and there is no verifier, so you cannot simply try edits and keep the one with the higher score. Harness^2 replaces "score" with *behavioural contrast* under matched conditions:

1. **Reference.** Run the current harness once. The trajectory shows how the harness behaves, not whether the answer is right.
2. **Propose.** An editor LLM reads the task, harness, reference trajectory (and library lessons) and writes two candidate harnesses. One is *invariant* (planning, tool use, context, delegation weaknesses that recur across domains). One is *domain-specific* (knowledge and procedure for this kind of task).
3. **Probe.** Re-run the *same task* under each candidate. Compare trajectory and deliverable to the reference and label each edit mitigated / unchanged / regressed for the deficiency it targeted. These labels guide composition; they are explicitly not a correctness check, because stochasticity and shared model bias make the evidence weak.
4. **Compose.** A composer reads everything and builds the successor harness: merge supported hunks, revise conflicting ones, adopt one candidate, or keep the original. Each decision must point at a concrete observation in the trajectories, not a presumed score gain. The successor is then executed.

Task-level recursion scales this with a budget k (k candidates per scope composed in parallel, or k chained steps in sequence); k=1 is the plain step. Gains grow with k.

**Harnessing-level recursion.** After the task, a reflector reads the whole improvement record and writes only lessons backed by execution contrasts into a library: per adopted harness an `EXPERIENCE.md` (situation, lessons, evidence) plus an index. If evidence is thin it writes nothing. Later tasks still start from the common base harness H0 (not the previous task's harness), but the proposer (and composer) consult the library, reusing or adapting entries rather than inheriting them.

Evidence in the paper: one step beats base on all benchmarks (up to +11.5 on WorkBuddy-Bench). Ablation (Table 3): removing the library costs 3.1 / 1.8 points, removing scoped invariant/domain editors costs 2.9 / 3.7, removing composition costs 1.6 / 1.9. Appendix D.2: editor sessions get evidence as files; a guard refuses to hand over any directory containing a grader verdict; invalid edit trees are retried once then fall back to the input tree.

## Concept to planned code

| Paper concept | Planned file / function |
|---|---|
| Harness H = editable component files | `h2/harness.py`: `load_harness`, `apply_edits`, `diff_harness`, `render_system_prompt`; files `harness/base/{system.md,guardrails.md,tool_guidance.md,skills/*.md}` |
| Frozen model M, agent A(q; M, H) | `h2/backends/*`: `Backend.run_agent(...)` (worker) |
| Execution record e = (trajectory, deliverable) | `h2/trace.py`: `Step`, `RunRecord`; `<run>.jsonl`, `<run>.meta.json`, `<run>.diff` |
| Reference execution e0 | `h2/ppc.py::run_reference` |
| Propose: invariant + domain candidates | `h2/propose.py::propose` (roles `propose_invariant`, `propose_domain`) |
| Probe in matched conditions, throwaway workspace | `h2/probe.py::probe_candidate` (temp copy of the task repo) |
| Behavioural contrast (label-free) | `h2/signals.py::compute_signals`, `h2/contrast.py::contrast` writing `contrast.json` |
| Compose with evidence-cited decisions | `h2/compose.py::compose` writing `composed.diff` + `compose.json` |
| Step record xi | the `runs/<task>/` directory as a whole |
| Reflect, lessons only if evidence-backed | `h2/reflect.py::reflect` |
| Improvement library, EXPERIENCE.md + index | `h2/library.py`: `add_entry`, `retrieve`; `library/index.json`, `library/<task>/EXPERIENCE.md` |
| Reuse: library read before Propose | `propose()` receives retrieved lessons; prompt logged to `runs/<task>/prompts/` |
| Guard: no grader verdict reaches editors | Hidden pytest only reachable through `h2/oracle.py`, imported only by `h2/evalrun.py`; enforced by `tests/test_isolation.py` |
| Ablation arms (w/o library, single step) | `h2 eval` arms: base, pppc (no library), pppc_lib |
| Table 1 style results | `h2/evalrun.py` writing `results.md` |

## What I simplify and why

- **k = 1 only, no parallel/sequential recursion.** The brief asks for one Propose-Probe-Compose step; budget scaling is the paper's headline, but it multiplies Claude Pro quota use by k. Left as a documented extension point.
- **Two components out of eight.** Only system prompt, guardrails, tool guidance and skills are editable. No memory, scripts, subagents or plugins: a 3-tool agent on tiny repos has nothing for them to do.
- **Edits are structured, the diff is generated by code.** The paper has the editor edit files in a sandbox. Here the LLM returns `{path, op, old, new}` edits and `difflib` builds the unified diff. LLM-written hunk headers are unreliable, and this makes "hunk" a well-defined unit for compose decisions.
- **One probe per candidate, one reference sample.** Stochasticity is high; the paper averages 3 runs. We cannot afford it, so results are noisy and the README says so.
- **Deterministic fallbacks for evidence.** Where the paper relies on the editor to cite, we validate every cited step ID against the logs and fall back to code-derived citations (flagged `code_fallback`) instead of trusting the LLM.
- **Retrieval is keyword overlap over EXPERIENCE.md text**, not an agent browsing the index. Skills are inlined into the system prompt rather than loaded on invoke.
- **Library frozen during `h2 eval`.** The paper updates after every task; we keep the held-out evaluation clean and order-independent.
- **Models.** Paper: Gemini/GLM executors, Opus editor. Here: Claude via the locally logged-in `claude` CLI (Pro subscription), Ollama qwen3 as optional fallback. Worker and editor are separate model settings (default CLI model for both; override with env vars).
- **Selection never sees a metric.** Same as the paper; this is what separates it from an autoresearch loop, which keeps an edit only if a metric improves. The hidden pytest files are touched only by `h2 eval` after the harness is fixed.
