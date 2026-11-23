# Fixing multi-key sort functions

For 'X descending, then Y ascending ignoring case', use:
`return sorted(items, key=lambda d: (-d['age'], d['name'].casefold()))`
Use `sorted` (it returns a new list), not `list.sort()`. Don't use `reverse=True` for mixed directions, because it flips the tie-break too.

REQUIRED: after editing, run a SEPARATE run_shell check and read its output before you finish. Writing the file is not verification, and a claimed self-check you didn't run doesn't count. Start it with `import sys; sys.path.insert(0, '.')`. Cases:
- Case tie-break: 'bob', 'Carl', 'alice' at the same age, expecting alice, bob, Carl. ('Alice' vs 'bob' proves nothing.)
- Direction: distinct ages, highest first.
- No mutation: `copy.deepcopy` the input, call the function, assert input == copy and `result is not input`.
- Empty: `sort_people([]) == []`.
Print label, expected, actual and PASS/FAIL for each case. Finish only when the output shows every case PASS.
