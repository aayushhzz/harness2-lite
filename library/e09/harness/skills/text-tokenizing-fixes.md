# Fixing word-count / tokenizer functions against a contract

1. Read the module, then rewrite it with write_file. Don't patch it with a shell heredoc or a str.replace script: if the old text doesn't match, nothing changes and no error appears, and the edit isn't recorded.
2. Implement the contract literally: `text.split()` (any whitespace), then `tok.strip(PUNCT)` with exactly the listed characters, then `.lower()`, then skip empty tokens. Don't use regex \w splitting, which changes apostrophes and hyphens inside words.
3. For sorting use `sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:n]`.
4. Let open() raise FileNotFoundError. Don't catch it and don't return {}.
5. Before finishing, write a temp file in the scratch dir and run one python3 check (no -I, run from the cwd) that prints PASS/FAIL for each case: 'The the THE' -> {'the':3}; 'cat. cat (cat)' -> {'cat':3}; '... !!' -> {}; a tie such as 'b a' with top_n 2 -> [('a',1),('b',1)]; n smaller than the number of words gets truncated; an internal apostrophe is kept ("don't"); a missing path raises FileNotFoundError.
6. Re-read the edited file before you reply.
