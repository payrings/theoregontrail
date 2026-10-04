"""WIN: the end of the journey.

Lines 100 to 1030. The score is built from what the party arrives with -- paper
section 10.3 and Table 21:

============================  ==========================
each person alive             500, 400, 300 or 200 by the health band
the wagon                     50
each ox                       4
each spare wagon part         2
each set of clothing          2
bullets                       1 per 50
food                         1 per 25 pounds
cash                         1 per 5 dollars
============================  ==========================

The total is then multiplied by the profession: once for a banker, twice for a
carpenter, three for a farmer. The rating is ``(SC < 6000) + (SC < 3000)`` -- Trail
guide at six thousand or more, Adventurer from three thousand, Greenhorn below. A
score better than the tenth entry goes on the list and the list is rewritten.

The final screen prints the date as the month, the day and ``"18"`` followed by the
stored year byte, so a party arriving after 1899 sees the wrong century. The paper
lists that in section 13 and it is reproduced.
"""

from __future__ import annotations

from . import num
from .data import hiscore as HIS
from .data import text as T

__all__ = ["run", "score"]

MULTIPLIER_TEXT = {1: "", 2: "double", 3: "tripled"}
PROFESSION_NAME = {1: "banker", 2: "carpenter", 3: "farmer"}


def read_items(c):
    """Lines 130-140: the eight scoring items, read from the hand-over memory."""
    pt = [[0, 0] for _ in range(8)]
    people = c.mem.peek(900)
    pt[0][0] = people
    pt[0][1] = people * (500 - 100 * c.mem.peek(916))
    pt[1][0] = 1
    pt[1][1] = 50
    pt[1 + 1][0] = c.mem.peek(909)
    pt[2][1] = pt[2][0] * 4
    pt[3][0] = c.mem.peek(910) + c.mem.peek(911) + c.mem.peek(912)
    pt[3][1] = pt[3][0] * 2
    pt[4][0] = c.mem.peek(908)
    pt[4][1] = pt[4][0] * 2
    pt[5][0] = c.mem.peek_word(904)
    pt[5][1] = pt[5][0] // 50
    pt[6][0] = c.mem.peek_word(906)
    pt[6][1] = pt[6][0] // 25
    cash = c.mem.peek_word(913) + c.mem.peek(917) / 100.0
    pt[7][0] = int(cash)
    pt[7][1] = pt[7][0] // 5
    return pt


def total(pt) -> int:
    """Line 305: the sum of the eight."""
    return sum(row[1] for row in pt)


def rating(score: int) -> int:
    """Line 630: ``R = (SC < 6000) + (SC < 3000)``."""
    return (1 if score < 6000 else 0) + (1 if score < 3000 else 0)


def run(c):
    """Lines 1000-1030: the congratulations, the score, the list and the menu."""
    from . import common
    c.set_program("WIN")
    entries = c.files.read_hiscore() or HIS.original()
    pt = read_items(c)
    score = total(pt)
    c.ui.clear()
    # line 601: "18" then the stored year byte
    c.ui.print("The Willamette Valley, Oregon")
    c.ui.print(f"{T.MONTHS[c.mem.peek(902) - 1]} {c.mem.peek(903)}, 18"
               f"{c.mem.peek(901)}")
    common.wait_key(c)
    c.ui.clear()
    c.ui.print("Congratulations!  You have made it to Oregon!  Let's see how many "
               "points you have received.")
    common.wait_key(c)
    shown = False
    while True:
        c.ui.clear()
        c.ui.print("Points for arriving in Oregon")
        c.ui.print()
        c.ui.print("   " + str(pt[0][0]) + (" people" if pt[0][0] != 1 else " person")
                   + " in " + T.HEALTH[c.mem.peek(916)] + " health".ljust(24)
                   + str(pt[0][1]).rjust(8))
        c.ui.print("   " + str(pt[1][0]) + " wagon".ljust(28) + str(pt[1][1]).rjust(8))
        c.ui.print("   " + str(pt[2][0]) + (" oxen" if pt[2][0] != 1 else " ox")
                   .ljust(28) + str(pt[2][1]).rjust(8))
        c.ui.print("   " + str(pt[3][0]) + " spare wagon part"
                   + ("s" if pt[3][0] != 1 else "").ljust(28)
                   + str(pt[3][1]).rjust(8))
        c.ui.print("   " + str(pt[4][0]) + " set" + ("s" if pt[4][0] != 1 else "")
                   + " of clothing".ljust(28) + str(pt[4][1]).rjust(8))
        c.ui.print("   " + str(pt[5][0]) + " bullet" + ("s" if pt[5][0] != 1 else "")
                   .ljust(28) + str(pt[5][1]).rjust(8))
        c.ui.print("   " + str(pt[6][0]) + " pounds of food".ljust(28)
                   + str(pt[6][1]).rjust(8))
        c.ui.print("     $ cash".ljust(28) + str(pt[7][1]).rjust(8))
        c.ui.print("   Total:".ljust(28) + str(score).rjust(8))
        c.ui.print()
        profession = c.mem.peek(915)
        if not shown and profession > 1:
            shown = True
            c.ui.print(f"For going as a {PROFESSION_NAME[profession]}, your points are "
                       f"{MULTIPLIER_TEXT[profession]}.")
            common.wait_key(c)
            for row in pt:
                row[1] *= profession
            score *= profession
            continue
        break
    rate = rating(score)
    c.outcome = f"ARRIVED {score} {T.RATINGS[rate]}"
    if score > (entries[9][1] if len(entries) > 9 else -1):
        entries = insert(c, entries, score, T.RATINGS[rate])
        c.files.write_hiscore(entries)
        c.ui.clear()
        c.ui.print("Congratulations!  Type your name as you would like to see it on "
                   "the Oregon Top Ten list.")
        c.ui.print()
        common.wait_key(c)
    else:
        c.ui.clear()
        c.ui.print(f"You have accumulated {score} points.  This is not enough to "
                   f"qualify for the Oregon Top Ten.")
        common.wait_key(c)
    from . import menu
    menu.top_ten(c, entries)
    return "MENU"


def insert(c, entries, score: int, rate: str):
    """Lines 510-530: the entry goes into the list in order, and the name is typed."""
    from . import common
    entries = [list(e) for e in entries]
    while len(entries) < 10:
        entries.append(["", 0, ""])
    place = 9
    for i in range(9, -1, -1):
        if score > entries[i][1]:
            if i < 9:
                entries[i + 1] = list(entries[i])
            place = i
        else:
            place = i
            break
    entries[place][1] = score
    entries[place][2] = rate
    name = ""
    while True:
        name = c.ui.key("-AZ-az .'-", 15, default="")
        if name:
            break
        if common.yes_no(c) != "Y":
            break
    entries[place][0] = name
    c.ui.print("Would you like to make any changes? ")
    if common.yes_no(c) == "Y":
        return insert(c, entries, score, rate)
    return entries
