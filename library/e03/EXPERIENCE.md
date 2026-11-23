# e03: Verifying a local-module fix: import cleanly the first time and check each contract clause
applies_when: You have fixed a module in the working directory (for example a mutable-default-argument bug) and the repo has no tests, so you check the fix yourself with an ad-hoc Python snippet.
merged_hunks: inv-1, inv-2

## Lessons
- [invariant|mitigated] When an ad-hoc check imports a module from the cwd, don't run it as `python3 -I` with a plain import. `-I` removes the cwd from sys.path, so the import fails and costs you an error and a retry. Either run plain `python3` with `sys.path.insert(0, '.')` or keep the sys.path insert if you need `-I`. Ge (evidence: reference:s3, reference:s4, composed:s3)
- [invariant|mitigated] Build the self-check from the function contract one clause at a time. For each clause, give the case a label and print expected, actual and PASS/FAIL. Here the clauses were: no cart gives only the item, each call starts fresh, the input list is not mutated, and the total of an empty cart is 0. A bar (evidence: composed:s3, reference:s4)
