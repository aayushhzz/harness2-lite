# Harness2-lite results
backend=claude worker_model=haiku editor_model=default tasks=6 date=2026-11-20T14:04:58

| Arm | Hidden-test pass | Mean steps | Mean tool errors | Mean tokens (run) | Mean tokens (total) |
|---|---|---|---|---|---|
| base | 6/6 (100%) | 4.0 | 0.8 | 22,922 | 22,922 |
| pppc | 6/6 (100%) | 3.5 | 0.0 | 21,356 | 123,447 |
| pppc_lib | 6/6 (100%) | 3.2 | 0.0 | 22,580 | 123,247 |

| Task | base | pppc | pppc_lib |
|---|---|---|---|
| h01 | PASS (5) | PASS (4) | PASS (3) |
| h02 | PASS (2) | PASS (3) | PASS (2) |
| h03 | PASS (4) | PASS (2) | PASS (2) |
| h04 | PASS (5) | PASS (6) | PASS (4) |
| h05 | PASS (4) | PASS (3) | PASS (4) |
| h06 | PASS (4) | PASS (3) | PASS (4) |

Notes: single sample per cell, n=6; one task of difference is within noise. tokens = input + cache_creation + cache_read + output (claude) or prompt_eval_count + eval_count (ollama). "total" includes reference, propose, probe, contrast, compose and the final run. The library is frozen during eval. Cells show steps of the measured run.
