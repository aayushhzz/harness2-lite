# e04: Self-verification of small Python fixes: avoid -I import trap, print per-case expected/actual
applies_when: A repo has no tests, and the agent writes its own check script to confirm a fix to a Python module in the working directory.
merged_hunks: inv-1, inv-2, dom-1

## Lessons
- [invariant|mitigated] If you run a self-check with `python3 -I`, a plain `from module import X` fails for project code because isolated mode drops the cwd from sys.path. Either add `sys.path.insert(0, '<project dir>')` before the import or write the check as a script file that sets the path explicitly. Do not do a plain (evidence: reference:s3, reference:s4, composed:s3)
- [invariant|mitigated] Have the check print one line per contract case in the form 'case: expected=X actual=Y PASS/FAIL'. A single bare 'ok' after a chain of asserts gives less evidence. One run then shows which clauses were covered, and nothing needs to be rerun. (evidence: reference:s4, composed:s3)
- [domain|mitigated] For balance and amount-validation contracts, test every clause, not only the reported symptom. That means: withdrawing exactly the balance leaves 0; overdrawing raises InsufficientFunds and leaves the balance unchanged; deposit and withdraw each raise ValueError for 0 and for negative amounts; both (evidence: reference:s5, composed:s2, composed:s3, composed:s4)
