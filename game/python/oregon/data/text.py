"""The text arrays held in the saved variable table, and the DATA statements.

Everything here is a string the game prints or compares. Appendix D.2 lists the
arrays that ``VAR.BIN`` restores; the rest come from DATA lines in the source:
``MENU`` 29000 for the default names and the scoring text, ``MENU`` 20060 for the
management options, ``OREGON TRAIL`` 22000 for the travel-screen labels, and
``WIN`` 29005 for the rating and health words. The spelling is the game's own.
"""

__all__ = ["MONTHS", "I_NAMES", "PACE", "RATIONS", "HEALTH", "WEATHER",
           "ACTIONS", "TRAVEL_LABELS", "DEFAULT_NAMES", "SCORE_TEXT",
           "RATINGS", "PROFESSIONS", "MANAGE_OPTIONS", "MONTH_CHOICES",
           "SOUND_WORDS", "STORE_PART_NAMES", "GOOD_ADVICE", "TUTOR_TEXT",
           "DIFFICULTY_TEXT", "health_word"]

# M$(0 to 11). The store offers choices 1 to 5 for March to July, so M$(0) and
# M$(1) are never offered but WIN reads M$(PEEK(902)) with the month, 3 to 7.
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

# I$(0 to 8). I$(0) is empty and I$(1) is "Wagon"; neither is used in play: the
# wagon is a flag at address 904 and the wagon's points are scored separately.
I_NAMES = ["", "Wagon", "oxen", "sets of clothing", "bullets",
           "wagon wheels", "wagon axles", "wagon tongues", "pounds of food"]

PACE = ["steady", "strenuous", "grueling"]
RATIONS = ["filling", "meager", "bare bones"]
HEALTH = ["good", "fair", "poor", "very poor"]
WEATHER = ["very cold", "cold", "cool", "warm", "hot", "very hot",
           "rainy", "snowy", "very rainy", "very snowy"]

# AQ$(0 to 9), the action menu.
ACTIONS = ["Continue on trail", "Check supplies", "Look at map", "Change pace",
           "Change food rations", "Stop to rest", "Attempt to trade",
           "Talk to people", "Buy supplies", "Hunt for food"]

# OREGON TRAIL 22000. Line 400 reads the first and line 320 the rest.
TRAVEL_LABELS = ["Press RETURN to size up the situation", "Date", "Weather",
                 "Health", "Food", "Next landmark", "Miles traveled"]

# MENU 29000: the ten names shuffled into the party at line 6000.
DEFAULT_NAMES = ["Zeke", "Jed", "Anna", "Mary", "Joey", "Beth", "John", "Sara",
                 "Henry", "Emily"]

# MENU 29010: how the points are earned, read by the "how points are earned" screen.
SCORE_TEXT = [
    ("good", 500), ("fair", 400), ("poor", 300), ("very poor", 200),
    ("wagon", 50), ("ox", 4), ("spare wagon part", 2), ("set of clothing", 2),
    ("bullets (each 50)", 1), ("food (each 25 pounds)", 1),
    ("cash (each 5 dollars)", 1),
]

# WIN 29005: the rating words, and the multiplier sentence.
RATINGS = ["Trail guide", "Adventurer", "Greenhorn"]

# MENU 4006 and 4010: the three professions and where each came from.
PROFESSIONS = ["banker from Boston", "carpenter from Ohio", "farmer from Illinois"]

# MENU 20060: the five management options.
MANAGE_OPTIONS = [
    "See the current Top Ten list",
    "See the original Top Ten list",
    "Erase the current Top Ten list",
    "Erase the tombstone messages",
    "Return to main menu",
]

# BUY SUPPLIES 29000: the store's month list, choice 1 to 5, plus the advice option.
MONTH_CHOICES = ["March", "April", "May", "June", "July"]

# MENU 130: SB$(0) and SB$(1).
SOUND_WORDS = ["off", "on"]

# BUY SUPPLIES 29000, read at line 120 as READ W$(L,L1), SP$(L,L1): SP$(L,0) is the
# name of a spare part and SP$(L,1) its price, "10", which line 800 prints. The
# numbers 200, 300 and 400 in the same DATA go to W$(L,1) and are not shown.
STORE_PART_NAMES = [("wagon wheel", 10), ("wagon axle", 10),
                    ("wagon tongue", 10)]

# BUY SUPPLIES 6010 and the shop windows.
COVERED_WAGON = "Covered wagon"

# BUY SUPPLIES 6105: the advice the player gets by choosing option 6.
GOOD_ADVICE = [
    ("You attend a public meeting held for \"folks with the California - "
     "Oregon fever.\""),
    ("You're told:"),
]


def health_word(band: int) -> str:
    """``H$(INT (H / 35))``. The array is not dimensioned, so Applesoft allows eleven
    elements and the ones past ``H$(3)`` are empty: a party at 140 or more shows no word."""
    return HEALTH[band] if 0 <= band < len(HEALTH) else ""
