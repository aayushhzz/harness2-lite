Symptom: the leaderboard page lists people in reverse alphabetical order (Z first) instead of showing the oldest members first.

Function contract: `sort_people(people)` in `sorting.py` takes a list of dicts with keys `name` and `age`. It returns a NEW list ordered by age from highest to lowest, and for people of the same age by name in ascending order, ignoring case. The input list and its dicts are not changed. An empty list returns an empty list.

There are no tests in this repository. Verify your fix yourself.
