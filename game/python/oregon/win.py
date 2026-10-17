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

from .data import hiscore as HIS
from .data import text as T

__all__ = ["run", "score"]

MULTIPLIER_TEXT = {1: "", 2: "doubled", 3: "tripled"}      # DATA at line 29000
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
    # PT(7,0) = PEEK (913) + PEEK (914) * 256 + PEEK (917) / 100, PT(7,1) = INT (PT(7,0) / 5)
    from . import num
    cash = num.add(num.parse(str(c.mem.peek_word(913))),
                   num.div(num.parse(str(c.mem.peek(917))), num.parse("100")))
    pt[7][0] = num.store(cash)                # PT(7,0) is an array element: stored
    pt[7][1] = num.trunc(num.div(cash, num.parse("5")))
    return pt


def win_rows(c, pt):
    """Lines 610-621: the eight lines of the table as the program words them."""
    from . import common
    pl = ["", "s", "s", "en"]                           # PL$(0 to 3), DATA 29000

    def n4(n):
        return str(n).rjust(4)

    return [
        ("   " + str(pt[0][0]) + (" people" if pt[0][0] > 1 else " person") + " in "
         + T.HEALTH[c.mem.peek(916)] + " health", pt[0][1]),
        ("   " + str(pt[1][0]) + " wagon", pt[1][1]),
        (n4(pt[2][0]) + " ox" + pl[3 * (pt[2][0] != 1)], pt[2][1]),
        (n4(pt[3][0]) + " spare wagon part" + pl[pt[3][0] != 1], pt[3][1]),
        (n4(pt[4][0]) + " set" + pl[pt[4][0] != 1] + " of clothing", pt[4][1]),
        (n4(pt[5][0]) + " bullet" + pl[2 * (pt[5][0] != 1)], pt[5][1]),
        (n4(pt[6][0]) + " pounds of food", pt[6][1]),
        ("     $" + common.money(c, pt[7][0]) + " cash", pt[7][1]),
    ]


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
    if hasattr(c.ui, "sound"):
        c.ui.sound.select("ms17")                # WIN 100: & RFL, "MS17.BIN" AT 51944
    entries = c.files.read_hiscore() or HIS.original()
    pt = read_items(c)
    score = total(pt)
    gfx = c.ui.pictures
    # line 601: "18" then the stored year byte
    date = f"{T.MONTHS[c.mem.peek(902) - 1]} {c.mem.peek(903)}, 18{c.mem.peek(901)}"
    congrats = ("Congratulations!  You have made it to Oregon!  Let's see how many "
                "points you have received.")
    if gfx:
        from .graphics import screens
        screens.win_arrival(c.ui, date)
        c.ui.wait_key(y=182, tune=True)                      # 601: GOSUB 950
        screens.box41000(c.ui, congrats, 14, 60, 253, 108)
    else:
        c.ui.clear()
        c.ui.print("The Willamette Valley, Oregon")
        c.ui.print(date)
        common.wait_key(c)
        c.ui.clear()
        c.ui.print(congrats)
    common.wait_key(c)
    shown = False
    while True:
        if gfx:
            ny = screens.win_points(c.ui, win_rows(c, pt), score, redraw=not shown)
            profession = c.mem.peek(915)
            if not shown and profession > 1:
                shown = True
                c.ui.dfw(20, ny, 239, 191 - ny)
                c.ui.para(f"For going as a {PROFESSION_NAME[profession]}, your points are "
                          f"{MULTIPLIER_TEXT[profession]}.")
                common.wait_key(c)
                for row in pt:
                    row[1] *= profession
                score *= profession
                continue
            common.wait_key(c)                    # 630: GOSUB 30000
            break
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
        # 621: V = PT(7,0): GOSUB 250: PRINT "     $"K$" cash"
        c.ui.print(("     $" + common.money(c, pt[7][0]) + " cash").ljust(28)
                   + str(pt[7][1]).rjust(8))
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
    from . import menu
    if score > (entries[9][1] if len(entries) > 9 else -1):
        # WIN 2000-2020: the top-ten screen and the "Type your name" line are shown
        # *before* the name entry (WIN 530), so the prompt the player is answering
        # is explained while it is on screen.
        menu.top_ten(c, entries, rating_only=True)
        if gfx:
            c.ui.dfw(20, 140, 230, 51)                # 2015: & DFW,7 AT 20,140,230,51
        c.ui.print("Congratulations!  Type your name as you would like to see it on "
                   "the Oregon Top Ten list.")
        entries = insert(c, entries, score, T.RATINGS[rate])
        c.files.write_hiscore(entries)
    else:
        if gfx:
            menu.top_ten(c, entries, rating_only=True)
            c.ui.dfw(20, 140, 230, 51)
        else:
            c.ui.clear()
        c.ui.print(f"You have accumulated {score} points.  This is not enough to "
                   f"qualify for the Oregon Top Ten.")
        common.wait_key(c)
    menu.top_ten(c, entries)
    return "MENU"


def place_in_list(entries, score: int):
    """Lines 510 and 515: where the new score goes, and the list with room made.

    ``FOR L = 9 TO 1 STEP -1: IF SC > VAL (HI$(L,1)) THEN`` copy entry ``L - 1`` down
    to ``L``; ``IF SC <= VAL (HI$(L,1)) THEN G = L: L = 0``. The test at 515 reads
    the entry that has just been copied in, so the new score lands **below** the
    first entry that is not smaller than it: ``G`` is the number of entries that are
    at least as high, and a tie goes below the old entry. Returns ``(list, G)``.
    """
    hi = [list(e) for e in entries]
    while len(hi) < 10:
        hi.append(["", 0, ""])
    g = 0
    for l in range(9, 0, -1):
        if score > int(hi[l][1]):
            hi[l] = list(hi[l - 1])
        if score <= int(hi[l][1]):
            g = l
            break
    return hi, g


def insert(c, entries, score: int, rate: str):
    """Lines 510-530: the entry goes into the list in order, and the name is typed.

    The name is asked for again only through the "Would you like to make any
    changes?" question (``GOTO 530``); the list is not rearranged a second time, and
    an empty name is accepted without a question.
    """
    from . import common
    entries, g = place_in_list(entries, score)
    entries[g] = ["", score, rate]               # HI$(G,1) = STR$(SC), HI$(G,2) = R$(R)
    gfx = c.ui.pictures
    if gfx:
        from .graphics import screens
        screens.top_ten(c.ui, entries[:g] + [["", "", ""]] + entries[g + 1:])    # 520: GOSUB 700
    while True:
        if gfx:
            y = 38 + 9 * g
            c.ui.dfw(0, 0, 280, 192)
            c.ui.cv.clear_text(0, y, 279, y + 8)
            c.ui.co(0, y)                        # 530: & CO,,ZZ + G * 9: & CEL
        entries[g][0] = c.ui.key("-AZ-az .'-", 15, default="")
        if gfx:
            c.ui.co(139, y)
            c.ui.put(str(entries[g][1]).rjust(4))
            c.ui.co(189, y)
            c.ui.put(str(entries[g][2]))
            c.ui.cv.box(20, 140, 249, 190)       # & WIND,7: & BOX
            c.ui.dfw(20, 140, 230, 51)
        c.ui.print("Would you like to make any changes? ")
        if common.yes_no(c) != "Y":
            break
    return entries
