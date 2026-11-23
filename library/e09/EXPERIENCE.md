# e09: Edit with write_file, then check every contract clause yourself when the repo has no tests
applies_when: Small single-file bug fixes that come with an explicit function contract and no test suite, where the task asks the agent to verify the fix itself.
merged_hunks: inv-1, inv-2, dom-1

## Lessons
- [invariant|mitigated] Change source files with the dedicated write/edit tool, not a shell heredoc running str.replace. A heredoc edit leaves edited_files empty, so the change can't be tracked, and a replace pattern that doesn't match fails without any error. Read the file first, then write the full corrected content. (evidence: reference:s2, composed:s1, composed:s3)
- [invariant|mitigated] If the repo has no tests and the task says to verify the fix, write a small check script in the scratch dir before the final reply. Give it one assertion per contract clause (here: case folding, punctuation stripping, dropping empty tokens, top_n ordering and tie-breaks, the n limit, FileNotFoundErr (evidence: reference:s3, composed:s4, composed:s6)
- [invariant|regressed] Don't re-read a file you just wrote in full with write_file when a check script has already exercised it. The re-read adds nothing new and shows up as a repeated call. Re-read only when the write was partial or the check failed. (evidence: composed:s1, composed:s5)
- [domain|mitigated] For word-frequency contracts, keep the normalization in one helper, in this order: split on whitespace, strip the listed PUNCT set from both ends, lowercase, drop empty tokens. Have top_n sort by (-count, word) and slice to n. Test it with inputs like 'The the cat. cat' and with a missing path. (evidence: composed:s3, composed:s4)
