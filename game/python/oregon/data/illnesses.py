"""Illnesses and injuries: ``IL$(0 to 8)``, and the days each lasts.

Two of the nine are injuries rather than disease, and the first of them does not
work: the injury number 0 is stored as the member's illness, and 0 means healthy,
so a broken arm has no effect at all -- and the same line overwrites whatever
illness that member already had. Line 10830. The paper lists this in section 13 and
it is reproduced, not fixed.
"""

__all__ = ["IL_NAMES", "ILLNESS_DAYS", "BROKEN_ARM", "BROKEN_LEG", "SNAKEBITE",
           "DISEASES", "DEATH_SENTENCE"]

IL_NAMES = [
    "a broken arm", "a broken leg", "a snakebite", "exhaustion", "typhoid",
    "cholera", "measles", "dysentery", "a fever",
]

# Line 3200 counts an illness down and clears it below 1. Event 3 gives a disease
# for ten days; the injuries at line 10830 give thirty.
ILLNESS_DAYS = [30, 30, 10, 10, 10, 10, 10, 10, 10]

BROKEN_ARM = 0
BROKEN_LEG = 1
SNAKEBITE = 2

# The six diseases event 3 draws from: INT(RND(1) * 6) + 3, so 3 to 8, equally
# likely. A person dies on catching a second one, and the second is never named.
DISEASES = [3, 4, 5, 6, 7, 8]

DEATH_SENTENCE = "died"
