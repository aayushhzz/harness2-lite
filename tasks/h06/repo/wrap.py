def wrap(text, width):
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width + 1:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    return lines
