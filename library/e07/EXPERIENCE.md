# e07: Reconcile self-check failures with the contract, and make local imports work on the first run
applies_when: You are fixing a small parsing function from a written contract in a repo with no tests, and checking the fix with ad-hoc python one-liners.
merged_hunks: inv-1, inv-2, dom-1

## Lessons
- [invariant|mitigated] If your own check prints FAIL, don't finish. First decide whether the code or the expected value is wrong by checking the case against the contract. Then fix whichever one is wrong and re-run until the output shows PASS. In the reference run the agent finished right after a FAIL for 'Smith, John'. T (evidence: reference:s4, reference:s5, candidate_invariant:s3, candidate_invariant:s4, candidate_invariant:s5)
- [invariant|mitigated] `python3 -I` leaves the current directory off sys.path, so `from localmodule import ...` fails. When you check a module in the working directory, put `import sys; sys.path.insert(0, '.')` in the very first verification command. That avoids losing a step to an import error and a retry. (evidence: reference:s3, reference:s4, candidate_invariant:s3, candidate_domain:s3, composed:s4)
- [domain|mitigated] For CSV-like parsers, take each test expectation straight from a contract clause. Unquoted 'a, b' gives ['a', ' b']. Quoted '"Smith, John"' gives ['Smith, John']. '"say ""hi"""' gives ['say "hi"']. An empty line gives ['']. A trailing comma adds a final ''. Print input, expected, actual and PASS/FAI (evidence: candidate_domain:s3, candidate_domain:s4, composed:s4, reference:s4)
