# e06: Make source edits with write_file and check them against each contract clause, not with heredocs and ad-hoc asserts
applies_when: Fixing a small function against a written contract when the repo has no tests and the agent has to verify the fix itself.
merged_hunks: inv-1, inv-2

## Lessons
- [invariant|mitigated] Edit source files with write_file, not a run_shell `cat > file <<EOF` heredoc, then read the file back once to confirm the content. The heredoc edit exited with code 1 and was never tracked as an edit. The write_file edit succeeded, was tracked, and the read-back confirmed it. (evidence: reference:s2, composed:s2, composed:s3)
- [invariant|mitigated] When there are no tests, turn each contract clause into one check case: normal range, reversed order, equal inputs, month/year/leap boundaries, and invalid input raising the expected exception. Print input, expected, actual and PASS/FAIL for each case, and run the script before giving the final answ (evidence: reference:s3, composed:s4, composed:s5)
- [domain|unchanged] Advisory domain guidance alone (a skill listing date edge cases) didn't change behaviour. The agent still used a heredoc and skipped every listed check, so it went straight from the edit to the final answer. Avoid relying on a domain checklist without a process rule that forces running the checks be (evidence: candidate_domain:s2, candidate_domain:s3)
