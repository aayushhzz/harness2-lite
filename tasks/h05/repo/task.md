Symptom: the update checker thinks version "1.10.0" is older than "1.9.0", so users are never offered the newest releases once the minor number reaches 10.

Function contract: `compare(a, b)` in `semver.py` compares two dotted numeric version strings. It returns -1 if a is lower than b, 0 if they are equal, and 1 if a is higher. Parts are compared as integers, left to right. Missing parts count as 0, so "1.0" equals "1.0.0". Any part that is not a plain non-negative integer raises ValueError.

There are no tests in this repository. Verify your fix yourself.
