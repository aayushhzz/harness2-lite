Symptom: book titles in the catalogue look wrong. "war and peace" comes out as "War And Peace", and "the lord of the rings" becomes "The Lord Of The Rings". Extra spaces in the input also leak into the output.

Function contract: `title_case(s)` in `titles.py` returns the title with each word capitalised: first letter upper case, the rest lower case. The small words a, an, the, of, and, in, on and to stay lower case when they are not the first or last word. Runs of whitespace collapse to one space and there is no leading or trailing space. Empty input returns an empty string.

There are no tests in this repository. Verify your fix yourself.
