# Fixing recursive flatten / tree-walk bugs
- An infinite recursion on strings happens because a 1-char str iterates to itself. Recurse only into the container types the contract names, e.g. `isinstance(item, (list, tuple))`. Do not use `hasattr(item, '__iter__')` or `Iterable` checks, because str, bytes and dict would then be split.
- Read the whole function. Also check the base case, whether the result is built in a new list (not a shared default or the input), and whether order is kept (extend vs. insert).
- Verify every contract clause with a timeout so a hang can't stall you: `timeout 10 python3 -c 'import sys; sys.path.insert(0,"."); from nested import flatten; ...'`. Minimum cases, each printed as expected/actual/PASS:
  flatten([1,[2,(3,[4])]])==[1,2,3,4]; flatten(['ab',[b'cd']])==['ab',b'cd']; flatten([{'k':1}])==[{'k':1}]; flatten([])==[]; flatten([[],[[]]])==[]; also check that the input is unchanged (deepcopy compare) and that the result is a new object.
- In the final sentence, say which types are now handled, not just the one in the symptom.
