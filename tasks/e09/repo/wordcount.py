def _words(text):
    return text.split()


def count_words(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    counts = {}
    for w in _words(text):
        counts[w] = counts.get(w, 0) + 1
    return counts


def top_n(path, n):
    counts = count_words(path)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:n]
