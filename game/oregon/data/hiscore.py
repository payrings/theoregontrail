"""The original top ten list, from MANAGEMENT's DATA lines 20000 and 20010.

The management program can erase the current list, which restores these ten. Kept
here so the reset option has something to restore and so the scoring screen has the
words it prints.
"""

__all__ = ["ORIGINAL", "n", "original"]

# name, points, rating
ORIGINAL = [
    ("Stephen Meek", 7650, "Trail guide"),
    ("David Hastings", 5694, "Adventurer"),
    ("Andrew Sublette", 4138, "Adventurer"),
    ("Celinda Hines", 2945, "Greenhorn"),
    ("Ezra Meeker", 2052, "Greenhorn"),
    ("William Vaughn", 1401, "Greenhorn"),
    ("Mary Bartlett", 937, "Greenhorn"),
    ("William Wiggins", 615, "Greenhorn"),
    ("Charles Hopper", 396, "Greenhorn"),
    ("Elijah White", 250, "Greenhorn"),
]


def n(count: int = 10):
    return [list(e) for e in ORIGINAL[:count]]


def original():
    return n(10)
