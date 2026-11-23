# e10: Edit source with the file-edit tool, then check every clause of the contract under a timeout
applies_when: Fixing a small bug in one function from a written contract when the repo has no tests and the agent has to verify the change itself, especially when the bug causes infinite recursion or hangs.
merged_hunks: inv-1, dom-1

## Lessons
- [invariant|mitigated] Make source edits with the write_file/edit tool, not with an ad-hoc shell heredoc running str.replace. In the reference run the heredoc patch exited 1 and the agent kept going, so it reported a fix that never reached the file. If any edit step exits non-zero, re-read the file and confirm the change (evidence: reference:s2, reference:s3, composed:s2, composed:s3)
- [domain|mitigated] If the bug is a recursion or hang, run your self-check under `timeout N` so that a fix that still loops fails quickly. Print expected, actual and PASS for every contract clause: nested lists and tuples flattened in order, str/bytes/dict kept whole, empty and nested-empty lists giving [], and the inp (evidence: reference:s3, reference:s4, composed:s3, composed:s4)
