Symptom: in the checkout service, carts sometimes contain items that belong to a different customer's request. It only happens under load, and restarting the service clears it for a while.

Function contract: in `cart.py`, `add_item(item, cart)` returns a NEW list that holds the items of `cart` followed by `item`. It never changes the list it was given. If `cart` is not given, the result holds only `item`, and each call without `cart` starts from a fresh, empty list. `item` is a dict with keys `price` and `qty`. `total(cart)` returns the sum of price * qty over all items, and 0 for an empty cart.

There are no tests in this repository. Verify your fix yourself.
