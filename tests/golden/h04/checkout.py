from decimal import Decimal, ROUND_HALF_UP

from pricing import apply_discount


def total(items):
    if not items:
        return 0.0
    acc = Decimal("0")
    for it in items:
        line = Decimal(str(apply_discount(it["price"], it["discount_pct"])))
        acc += line * it["qty"]
    return float(acc.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
