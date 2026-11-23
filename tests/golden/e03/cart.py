def add_item(item, cart=None):
    if cart is None:
        cart = []
    return list(cart) + [item]


def total(cart):
    return sum(i["price"] * i["qty"] for i in cart)
