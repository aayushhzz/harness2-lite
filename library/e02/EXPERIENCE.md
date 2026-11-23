# e02: Verifying a local module fix: import it correctly, edit with the file tool, and check every contract clause
applies_when: You fix a small function in a module in the working directory, there are no tests, and you check the fix with an inline python3 script.
merged_hunks: none

## Lessons
- [invariant|regressed] Don't run a check script with `python3 -I` and then import a module from the working directory with a plain import (`from stats import ...`). Isolated mode takes the current directory off sys.path, so the import fails and you lose a step and add a tool error (composed:s3 and candidate_invariant:s3/s (evidence: reference:s3, composed:s3, composed:s4, candidate_invariant:s3, candidate_invariant:s4, candidate_invariant:s5)
- [invariant|regressed] Use the write_file/edit tool to write source changes, not a shell heredoc. The heredoc write in candidate_domain:s2 failed with exit 1, cost extra tokens, and the change no longer counted as an edited file. The reference made the same change with write_file without any error (reference:s2). (evidence: reference:s2, candidate_domain:s2)
- [domain|mitigated] For moving_average, use one check script that prints PASS/FAIL for each case and covers every contract clause, not just the reported symptom: [1,2,3,4] with window 2 gives [1.5,2.5,3.5]; window == len gives one mean; window > len gives []; [] with window 1 gives []; window 0 and a negative window ra (evidence: reference:s3, candidate_domain:s3)
