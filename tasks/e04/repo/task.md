Symptom: customers with exactly 10.00 in their account get "insufficient funds" when they withdraw all 10.00. Support also found a deposit of -50 that was accepted and made a balance negative.

Function contract: `account.py` defines `Account(balance=0)` with `deposit(amount)` and `withdraw(amount)`, both returning the new balance, and an exception class `InsufficientFunds`. A withdrawal equal to the balance succeeds and leaves 0. A withdrawal larger than the balance raises `InsufficientFunds` and leaves the balance unchanged. `deposit` and `withdraw` raise ValueError when amount is 0 or less.

There are no tests in this repository. Verify your fix yourself.
