from decimal import Decimal, ROUND_HALF_UP


def apply_discount(price, pct):
    if not 0 <= pct <= 100:
        raise ValueError("pct must be between 0 and 100")
    p = Decimal(str(price))
    result = p * (Decimal(100) - Decimal(str(pct))) / Decimal(100)
    return float(result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
