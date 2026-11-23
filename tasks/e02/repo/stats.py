def moving_average(xs, window):
    out = []
    for i in range(len(xs) - window):
        chunk = xs[i:i + window]
        out.append(sum(chunk) / window)
    return out
