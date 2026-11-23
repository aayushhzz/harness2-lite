def apply_discount(price, pct):
    if not 0 <= pct <= 100:
        raise ValueError("pct must be between 0 and 100")
    return int(price * (100 - pct) / 100)
