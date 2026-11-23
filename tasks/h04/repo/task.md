Symptom: customers are charged less than expected. A 19.99 item with a 10 percent discount is charged 17.00, and a basket with two of the same item only counts one of them.

Function contract: `apply_discount(price, pct)` in `pricing.py` returns the price after removing pct percent, rounded to 2 decimals with round-half-up, computed from the decimal text of the price (use decimal.Decimal on str(price)). pct must be between 0 and 100 inclusive, otherwise raise ValueError. `total(items)` in `checkout.py` takes a list of dicts with keys `price`, `qty` and `discount_pct`. Each line is apply_discount(price, discount_pct) multiplied by qty; the sum is rounded to 2 decimals with round-half-up and returned as a float. An empty list returns 0.0.

There are no tests in this repository. Verify your fix yourself.
