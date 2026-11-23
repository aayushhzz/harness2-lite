TRUE_VALUES = {"true", "1", "yes", "on"}
FALSE_VALUES = {"false", "0", "no", "off", ""}


def parse_bool(s):
    v = s.strip().lower()
    if v in TRUE_VALUES:
        return True
    if v in FALSE_VALUES:
        return False
    raise ValueError(f"not a boolean: {s!r}")
