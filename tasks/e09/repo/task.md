Symptom: the word frequency report lists "The" and "the" as two different words, and "cat." and "cat" are counted separately. The top-words list is full of entries that look like the same word.

Function contract: `wordcount.py` has `count_words(path)`, which reads a UTF-8 text file and returns a dict mapping each word to how often it occurs. Words are compared in lowercase. Split the text on whitespace, then strip the characters . , ! ? ; : " ' ( ) from both ends of every token. Tokens that are empty after stripping are ignored. `top_n(path, n)` returns a list of (word, count) tuples, highest count first, ties broken by word in ascending order, at most n items. A missing file raises FileNotFoundError.

There are no tests in this repository. Verify your fix yourself.
