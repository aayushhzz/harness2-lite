# Verifying a fix in a small Python repo with no tests

1. Importing cwd modules: plain `python3 -c` finds modules in the cwd. If you use `python3 -I`, cwd is not on sys.path, so start the snippet with `import sys; sys.path.insert(0, '.')`. Get this right the first time; a failed import costs an error and a retry.
2. Edit with write_file, not shell heredocs.
3. Write one check script that takes the contract one clause at a time. For each case print the label, expected, actual and PASS/FAIL, and end with a count of failures.
4. String-to-bool or other parsers: test every listed token in mixed case (`'TRUE'`, `'On'`) and with padding (`'  no '`). Test the empty string and whitespace-only input. Unknown text such as `'maybe'` must raise the stated exception (catch it and report PASS). Check that results are real bools (`is True`/`is False`).
5. Also check the caller named in the symptom (e.g. `is_enabled`): missing key returns default (both True and False defaults), string values go through the parser, and non-strings (0, 1, None, True) go through bool().
6. Finish only after every case shows PASS. Then grep for other callers of the old buggy behaviour.
