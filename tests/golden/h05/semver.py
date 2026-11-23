def _parts(v):
    out = []
    for p in v.split("."):
        if not p.isdigit():
            raise ValueError(f"invalid version: {v!r}")
        out.append(int(p))
    return out


def compare(a, b):
    pa, pb = _parts(a), _parts(b)
    n = max(len(pa), len(pb))
    pa += [0] * (n - len(pa))
    pb += [0] * (n - len(pb))
    if pa == pb:
        return 0
    return -1 if pa < pb else 1
