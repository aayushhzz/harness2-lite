from datetime import date


def days_between(a, b):
    start, end = sorted([date.fromisoformat(a), date.fromisoformat(b)])
    return (end - start).days + 1
