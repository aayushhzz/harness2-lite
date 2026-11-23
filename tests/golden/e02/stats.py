def moving_average(xs, window):
    if window < 1:
        raise ValueError("window must be >= 1")
    out = []
    for i in range(len(xs) - window + 1):
        out.append(sum(xs[i:i + window]) / window)
    return out
