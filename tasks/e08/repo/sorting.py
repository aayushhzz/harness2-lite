def sort_people(people):
    return sorted(people, key=lambda p: p["name"], reverse=True)
