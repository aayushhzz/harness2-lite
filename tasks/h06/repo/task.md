Symptom: the email preview cuts text too long, with lines running one character past the column limit, and the last line of every message disappears from the preview.

Function contract: `wrap(text, width)` in `wrap.py` returns a list of lines. Words are the pieces of text separated by whitespace. Fill each line greedily: add the next word while the line, including a single space between words, stays at most `width` characters. A single word longer than width goes alone on its own line. Empty text returns []. A width below 1 raises ValueError.

There are no tests in this repository. Verify your fix yourself.
