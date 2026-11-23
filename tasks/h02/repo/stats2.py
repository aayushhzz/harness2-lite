def median(xs):
    if not xs:
        raise ValueError("median of empty sequence")
    xs.sort()
    return xs[len(xs) // 2]
