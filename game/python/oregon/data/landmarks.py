"""The two tables that describe the trail: landmarks and segments.

They are indexed differently and it is easy to mix them up. ``LM$`` describes each
of the eighteen landmarks and names the segment, or segments, that leave it.
``LM`` describes each of the nineteen segments, with its length in miles, its speed
base and the landmark it ends at. Paper section 4.1, Tables 7 and 8.
"""

__all__ = ["SCENERY", "LM_NAMES", "LM_TYPE", "LM_SEGMENT", "LM_SEGMENT2", "SEG_MILES",
           "SEG_SPEED", "SEG_ENDS_AT", "ZONE_AT", "TYPE_FORT", "TYPE_RIVER",
           "TYPE_PLAIN", "zone_for", "landmark_name", "short_name"]

TYPE_PLAIN = 0
TYPE_FORT = 1
TYPE_RIVER = 2

# LM$(n, 0) -- the landmark. The paper keeps the leading "the " in the river names
# and strips it again at lines 260 and CROSS.LIB 50000, so it is kept here.
LM_NAMES = [
    "Independence",               # 0
    "the Kansas River crossing",  # 1
    "the Big Blue River crossing",  # 2
    "Fort Kearney",               # 3
    "Chimney Rock",               # 4
    "Fort Laramie",               # 5
    "Independence Rock",          # 6
    "South Pass",                 # 7
    "Fort Bridger",               # 8
    "Green River crossing",  # 9
    "Soda Springs",               # 10
    "Fort Hall",                  # 11
    "the Snake River crossing",  # 12
    "Fort Boise",                 # 13
    "the Blue Mountains",         # 14
    "Fort Walla Walla",           # 15
    "The Dalles",                 # 16
    "the Willamette Valley",      # 17
]

# LM$(n, 1) -- "0" neither, "1" a fort where buying is allowed, "2" a river.
LM_TYPE = [1, 2, 2, 1, 0, 1, 0, 0, 1, 2, 0, 1, 2, 1, 0, 1, 0, 0]

# LM$(n, 2) -- the segment out. The last landmark holds 99, which no segment uses:
# the journey ends there, so nothing reads it.
LM_SEGMENT = [0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 17, 18, 99]

# LM$(n, 3) -- a second segment, or 0. Only South Pass and the Blue Mountains have
# one; the Sublette Cutoff past Fort Bridger and the route past Fort Walla Walla.
LM_SEGMENT2 = [0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0, 0, 0, 0, 16, 0, 0, 0]

# LM(s, 0) -- miles. LM(s, 1) -- the speed base, 20 before Fort Laramie and 12 after.
SEG_MILES = [102, 83, 119, 250, 86, 190, 102, 57, 125, 162,
             144, 57, 182, 114, 160, 55, 125, 120, 100]
SEG_SPEED = [20, 20, 20, 20, 20, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12]

# LM(s, 2) -- the landmark the segment ends at.
SEG_ENDS_AT = [1, 2, 3, 4, 5, 6, 7, 9, 8, 10, 10, 11, 12, 13, 14, 15, 16, 16, 17]

# The climate zone a landmark belongs to, from line 1000:
#     ZO = (LM > 2) + (LM > 5) + (LM > 10) + (LM > 13)
# The code produces five zones; the sixth, Portland, is never selected, which is one
# of the quirks the paper lists in section 13.
ZONE_AT = [0, 0, 0, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 4, 4, 4, 4]


def zone_for(landmark: int) -> int:
    return (landmark > 2) + (landmark > 5) + (landmark > 10) + (landmark > 13)


def landmark_name(n: int) -> str:
    return LM_NAMES[n]


def short_name(n: int) -> str:
    """Line 260: the landmark name without a leading ``the ``.

    ``Z$ = RIGHT$(LM$(LM,0), LEN(LM$(LM,0)) - 4 * (LEFT$(LM$(LM,0),4) = "the "))``
    """
    name = LM_NAMES[n]
    return name[4:] if name[:4].lower() == "the " else name


#: ``L%(NM - 1, 0 to 1)`` (paper Table D5): for the landmark the party is heading for, the
#: number of its picture in the travel scene and the offset that places it. Only the
#: optional graphical mode reads it.
SCENERY = [(8, 78), (8, 78), (5, 50), (6, 36), (7, 50), (6, 36), (7, 56), (8, 56), (14, 78),
           (9, 64), (10, 70), (14, 78), (11, 56), (15, 56), (12, 56), (13, 112), (16, 50)]
