Symptom: the config loader hangs for a while and then fails with RecursionError whenever a settings value is a plain string such as "ab". Lists of numbers flatten fine.

Function contract: `flatten(x)` in `nested.py` returns a new flat list. It descends into lists and tuples at any depth and keeps their leaves in order. Strings, bytes and dicts are kept whole as single elements, never split into characters or keys. An empty list, or a list containing only empty lists, returns [].

There are no tests in this repository. Verify your fix yourself.
