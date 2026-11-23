# e08: Verify sort-contract fixes with data that can tell correct behavior from wrong behavior
applies_when: You are fixing a sort or ordering function in a repo with no tests, where the contract has several clauses (sort key direction, a case-insensitive tie-break, returning a new list, not mutating the input, handling empty input) and you have to verify the fix yourself.
merged_hunks: dom-1

## Lessons
- [domain|mitigated] To check a case-insensitive tie-break, build same-age data where case-sensitive and case-insensitive ordering give different results, such as ['bob','Carl','alice']. A case-sensitive sort puts 'Carl' before 'alice'. The reference self-check used 'Alice' and 'bob', which sort the same way either way, (evidence: reference:s3, composed:s3)
- [invariant|mitigated] When a contract says 'returns a NEW list and does not change the input', check both parts on purpose. Take a deepcopy of the input before the call and compare it afterwards, and assert `result is not input`. Print expected and actual values, not only the output. The reference only printed the sorted (evidence: reference:s3, composed:s4, composed:s5)
- [invariant|unchanged] Rewriting a file with a shell heredoc (`cat > file <<EOF`) leaves the edit out of the edited-files signal, so tracking only sees diff size. It also makes it easy to skip the edit tool's confirmation step. If you still use a heredoc, follow it with an observable check that runs the code. Don't treat (evidence: composed:s2, reference:s2)
