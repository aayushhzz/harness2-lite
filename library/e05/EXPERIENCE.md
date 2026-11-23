# e05: Self-verify a cwd-module fix without import failures under python -I
applies_when: The repo has no tests and you check a fix with an ad-hoc Python script that imports modules from the working directory, especially when you run it with `python3 -I`.
merged_hunks: inv-1, inv-2, dom-1

## Lessons
- [invariant|mitigated] `python3 -I` (isolated mode) leaves the cwd off sys.path, so `from config import ...` fails. If you need -I, start the check script with `sys.path.insert(0, '<workspace dir>')`, or run a script saved outside the workspace that adds the path explicitly. Do this before you run it, not after the first (evidence: reference:s3, reference:s4, composed:s5)
- [invariant|mitigated] Write the verification as one case per contract clause. Each line should print the input, expected value, actual value and PASS/FAIL, e.g. `parse_bool('true'): expected=True actual=True PASS`. Include the ValueError cases and the caller (is_enabled) too. This makes the check self-evident in one run. (evidence: reference:s4, composed:s5)
- [domain|mitigated] Make the deliverable edit with write_file, not a shell heredoc, so the change is recorded as an edited file. Keep the check script in the scratchpad, outside the workspace. The composed run edited config.py with write_file and put its check script under /private/tmp/claude-501. (evidence: composed:s4, composed:s5)
