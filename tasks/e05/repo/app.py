from config import parse_bool


def is_enabled(settings, key, default=False):
    if key not in settings:
        return default
    value = settings[key]
    if isinstance(value, str):
        return parse_bool(value)
    return bool(value)
