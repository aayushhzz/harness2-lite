SMALL_WORDS = {"a", "an", "the", "of", "and", "in", "on", "to"}


def title_case(s):
    words = s.split()
    last = len(words) - 1
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if 0 < i < last and lw in SMALL_WORDS:
            out.append(lw)
        else:
            out.append(lw[:1].upper() + lw[1:])
    return " ".join(out)
