# e01: Verify a small text-function fix in the same step as the edit, with checks planned from the contract
applies_when: You are fixing a pure function against a written contract in a repo that has no tests, and you have to write and run your own checks.
merged_hunks: inv-1, inv-2

## Lessons
- [invariant|mitigated] Run a self-written check from the working directory without `python3 -I`, or add the cwd to sys.path explicitly. `-I` removes the cwd from the import path, so `from textutil import slugify` fails, and you lose a step finding out why. The candidate ran its check right after writing the file in the sa (evidence: reference:s3, reference:s4, candidate_invariant:s2)
- [invariant|mitigated] Before running anything, write one check script with a case for each contract clause: lowercasing, collapsing runs of non-alphanumerics, accented letters, trimming leading and trailing hyphens, and empty input. Have it print input, expected, actual and PASS/FAIL. Then apply the fix and run the scrip (evidence: candidate_invariant:s2, candidate_invariant:s3, reference:s4)
