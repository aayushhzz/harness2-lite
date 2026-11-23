from pricing import apply_discount


def total(items):
    subtotal = 0.0
    for it in items:
        subtotal += apply_discount(it["price"], it["discount_pct"])
    return round(subtotal, 2)
