def add_item(item, cart=[]):
    cart.append(item)
    return cart


def total(cart):
    return sum(i["price"] * i["qty"] for i in cart)
