Symptom: blog post URLs come out like `hello--world-` when the title has punctuation, and a title with extra spaces such as `  My  Post ` gives `-my--post-`. Someone said the regex in the old code was fine, so the bug must be elsewhere.

Function contract: `slugify(s)` in `textutil.py` returns a URL slug. Lowercase the text. Only ASCII letters a-z and digits 0-9 are kept; every run of any other characters (including accented letters) becomes exactly one hyphen. Leading and trailing hyphens are removed. Empty input returns an empty string.

There are no tests in this repository. Verify your fix yourself.
