def slugify(s):
    result = ""
    for ch in s.lower():
        if ch.isalnum():
            result += ch
        else:
            result += "-"
    return result
