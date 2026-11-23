# Verifying a stateful-class fix against a written contract (no tests in repo)

Use together with the general check-script rules (import path under -I, one PASS/FAIL line per clause).

1. Make the source edit with write_file, not a shell heredoc, so the change is recorded as an edited file. Then run the checks in the next step.
2. For a class like Account with deposit/withdraw, cover:
   - the return value of each method (the new balance)
   - the boundary: withdrawing exactly the balance (e.g. 10.00 from 10.00) leaves 0
   - an over-limit withdrawal raises the custom exception (InsufficientFunds) AND leaves the balance unchanged
   - amount 0 and a negative amount raise ValueError for EVERY method named in the contract, and leave the balance unchanged
3. Exit nonzero if any case fails. Finish only after every case prints PASS.
