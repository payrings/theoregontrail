"""BUY SUPPLIES: the departure month and Matt's General Store.

Lines 100 to 5020. The store is the first place the party's resources come from, and
it is where the hand-over layout of paper section 2.3 is written: the yokes of oxen
at 905, the pounds of food split across 906 and 907, the sets of clothing at 908, the
boxes of bullets at 909 and the three spare parts at 910 to 912.
"""

from __future__ import annotations

from . import common, num
from .data import text as T
from .ui import ALLOWED

__all__ = ["departure_month", "store", "init_state", "item_prices"]

MAX_FOOD = 2000
MAX_PART = 3
MAX_YOKE = 9


def init_state(c):
    """Line 120: read the hand-over and clear 904 to 912.

    ``MY = (PEEK (913) + PEEK (914) * 256) / 10`` -- the money was stored times ten,
    because the hand-over is whole numbers. Everything from 904 to 912 is then
    cleared, so a party that buys nothing leaves with nothing.
    """
    st = c.st
    st.MY = num.div(num.parse(str(c.mem.peek_word(913))), num.parse("10"))
    for addr in range(904, 913):
        c.mem.poke(addr, 0, 120)
    for item in range(2, 9):
        st.I[item] = num.ZERO
    st.I[1] = num.ONE
    return st.MY


def item_prices():
    """Lines 910-950: what the store charges, at the store's own prices.

    Oxen $40 a yoke, food 20 cents a pound, clothing $10 a set, ammunition $2 a box,
    spare parts $10 each. The bill at line 4000 is the sum of the five.
    """
    return (40.0, 0.20, 10.0, 2.0, 10.0)


def departure_month(c):
    """Lines 6000-6110: March to July, or a word of advice.

    Line 6030 stores the choice plus two at 902 and the day is one, so a party that
    leaves in March has three units of snow on the ground at the start (line 29000).
    """
    c.mem.poke(903, 1, 6000)          # the day is the first of the month
    while True:
        c.set_program("BUY SUPPLIES")
        c.ui.clear()
        c.ui.print(f"It is 18{c.mem.peek(901)}.  Your jumping off place for Oregon "
                   f"is Independence, Missouri.  You must decide which month to "
                   f"leave Independence.")
        c.ui.print()
        for i, name in enumerate(T.MONTH_CHOICES, 1):
            c.ui.print(f"   {i}. {name}")
        c.ui.print("   6. Ask for advice")
        c.ui.print()
        c.ui.print("What is your choice? ")
        a = c.ui.key(ALLOWED["MONTH"], 1)
        if a and a.isdigit():
            z = int(a)
            if z == 6:
                advice(c)
                continue
            if 1 <= z <= 5:
                c.mem.poke(902, z + 2, 6030)     # February..July in DATA, but the
                return z + 2                     # table stores March..July
        c.ui.print("What is your choice? ")
        c.ui.key(ALLOWED["MONTH"], 1)


def advice(c):
    """Lines 6105-6110."""
    c.ui.clear()
    c.ui.print('You attend a public meeting held for "folks with the California - '
               'Oregon fever."  You\'re told:')
    c.ui.print()
    c.ui.print("If you leave too early, there won't be any grass for your oxen to "
               "eat.  ")
    c.ui.print("If you leave too late, you may not get to Oregon before winter "
               "comes.  If you leave at just the right time, there will be green "
               "grass and the weather will still be cool.")
    common.wait_key(c)


# ------------------------------------------------------------------- the store
def store(c) -> dict:
    """Lines 1000-5020: buy until the player leaves.

    The loop at 1015 is ``Z = (Z = 0) * 6 + Z: ON Z GOSUB 400, 500, 600, 700, 800,
    5000``, so choice 0 -- what the store's own prompt returns when nothing is typed
    -- is the sixth option, leaving the store. The bill at line 4000 is the sum of
    the five lines, and line 5000 refuses to let the party leave if it exceeds the
    money held or if there are no oxen.
    """
    st = c.st
    prices = item_prices()
    intro(c)
    while True:
        show_bill(c)
        # Line 3030 prints this on a box at the foot of the panel and then does
        # "Z = USR (1)", which **waits for a key** -- the same routine line 950 uses
        # for "Press SPACE BAR to continue", and WIN 956 shows what it does:
        # "Z = USR (2): IF Z < 128 THEN 955", so it loops until a key arrives with the
        # high bit set, which is any ordinary key, space included.
        #
        # This used to print the prompt and flush instead, on the reading that USR(1)
        # clears the keyboard. That was wrong, and it was reported from play: the
        # prompt said "Press SPACE BAR to leave store", pressing space did nothing at
        # all, and only Return worked -- because Return was answering the *next*
        # question, "Which item would you like to buy?". FINDINGS.md 22.
        c.ui.wait_key("Press SPACE BAR to leave store")
        c.ui.print()
        c.ui.print("Which item would you like to buy? ")
        # Line 250's reader accepts 1 to 5 and nothing else -- "ON (Z < 49 OR Z > 53)
        # AND Z <> 32 GOTO 252" -- and a bare Return gives Z$ = "", so VAL(Z$) = 0,
        # which line 1015 turns into the sixth choice: leaving the store.
        a = c.ui.key(ALLOWED["STORE_ITEM"], 1, default="")
        z = int(a) if a and a.isdigit() else 0
        if z == 0:
            z = 6
        if z == 6:
            if leave(c):
                return {"yokes": c.mem.peek(905),
                        "food": c.mem.peek(906) + c.mem.peek(907) * 256}
            continue
        buy_item(c, z, prices)


def intro(c):
    """Lines 2000-2030: Matt's introduction and the bill so far."""
    st = c.st
    c.ui.clear()
    c.ui.print("Before leaving Independence, you should buy equipment and "
               "supplies.  You have "
               f"${common.money(c, st.MY)} in cash, but you don't have to spend it "
               "all now.")
    common.wait_key(c)
    c.ui.print("You can buy whatever you need at Matt's General Store.")
    common.wait_key(c)
    c.ui.print()
    c.ui.print("Hello, I'm Matt.  So you're going to Oregon!  I can fix you up with "
               "what you need:")
    c.ui.print()
    c.ui.print("- a team of oxen to pull your wagon")
    c.ui.print("- clothing for both summer and winter")
    common.wait_key(c)
    c.ui.print("- plenty of food for the trip")
    c.ui.print("- ammunition for your rifles")
    c.ui.print("- spare parts for your wagon")
    common.wait_key(c)


def bill(c) -> float:
    """Line 4000: the sum of the five lines at 900 to 950."""
    p = item_prices()
    food = c.mem.peek(906) + c.mem.peek(907) * 256
    total = (p[0] * c.mem.peek(905) + p[1] * food + p[2] * c.mem.peek(908)
             + p[3] * c.mem.peek(909)
             + p[4] * (c.mem.peek(910) + c.mem.peek(911) + c.mem.peek(912)))
    return total


def show_bill(c):
    """Line 3015-3020: the five lines, the total and the money held."""
    st = c.st
    p = item_prices()
    food = c.mem.peek(906) + c.mem.peek(907) * 256
    c.ui.print("  Matt's General Store")
    c.ui.print("  Independence, Missouri")
    # Line 3015 is "PRINT L". "I$(L)", so the five lines carry their number -- and
    # that number is what the player types, since the reader at line 250 accepts 1
    # to 5.
    rows = [
        (T.I_NAMES[2], p[0] * c.mem.peek(905)),
        (T.I_NAMES[8], p[1] * food),
        (T.I_NAMES[3], p[2] * c.mem.peek(908)),
        (T.I_NAMES[4], p[3] * c.mem.peek(909)),
        ("spare wagon parts",
         p[4] * (c.mem.peek(910) + c.mem.peek(911) + c.mem.peek(912))),
    ]
    for n, (name, line_total) in enumerate(rows, 1):
        c.ui.print(f"{n}. {name}".ljust(24)
                   + common.dollar_text(c, num.parse(str(line_total))))
    c.ui.print("Total bill: " + common.dollar_text(c, num.parse(str(bill(c)))))
    c.ui.print("Amount you have: " + common.dollar_text(c, st.MY))


def buy_item(c, z: int, prices):
    """Lines 400, 500, 600, 700 and 800: the five prompts.

    The limits are the ones the paper lists in Table 5: 1 to 9 yoke, 2000 pounds of
    food, 99 sets of clothing, 99 boxes of ammunition and 3 of each spare part. The
    oxen prompt at line 405 allows 1 to 9 in one digit, and nothing rejects a 0 --
    so a party can leave with no oxen and find out at line 5006.
    """
    st = c.st
    if z == 1:                                       # oxen, line 400
        c.ui.clear()
        c.ui.print("There are 2 oxen in a yoke; I recommend at least 3 yoke.  I "
                   "charge $40 a yoke.")
        c.ui.print()
        c.ui.print("How many yoke do you")
        c.ui.print("want? ")
        a = c.ui.key(ALLOWED["STORE_YOKE"], 1)
        c.mem.poke(905, int(a) if a and a.isdigit() else 0, 405)
    elif z == 2:                                     # food, line 500
        while True:
            c.ui.clear()
            c.ui.print("I recommend you take at least 200 pounds of food for each "
                       "person in your family.  I see that you have 5 people in "
                       "all.  You'll need flour, sugar, bacon, and coffee.  My price "
                       "is 20 cents a pound.")
            c.ui.print()
            c.ui.print("How many pounds of food do you want? ")
            a = c.ui.key(ALLOWED["STORE_FOOD"], 4)
            want = int(a) if a and a.isdigit() else 0
            if want > MAX_FOOD:
                c.ui.print()
                c.ui.print("Your wagon may only carry 2000 pounds of food.")
                common.wait_key(c)
                continue
            c.mem.poke_word(906, want, 530)
            break
    elif z == 3:                                     # clothing, line 600
        c.ui.clear()
        c.ui.print("You'll need warm clothing in the mountains.  I recommend taking "
                   "at least 2 sets of clothes per person.  Each set is $10.00.")
        c.ui.print()
        c.ui.print("How many sets of clothes do you want? ")
        a = c.ui.key(ALLOWED["STORE_CLOTHES"], 2)
        c.mem.poke(908, int(a) if a and a.isdigit() else 0, 610)
    elif z == 4:                                     # ammunition, line 700
        c.ui.clear()
        c.ui.print("I sell ammunition in boxes of 20 bullets.  Each box costs "
                   "$2.00.")
        c.ui.print()
        c.ui.print("How many boxes do")
        c.ui.print("you want? ")
        a = c.ui.key(ALLOWED["STORE_AMMO"], 2)
        c.mem.poke(909, int(a) if a and a.isdigit() else 0, 700)
    elif z == 5:                                     # spare parts, line 800
        c.ui.clear()
        c.ui.print("It's a good idea to have a few spare parts for your wagon.  "
                   "Here are the prices:")
        for name, price in T.STORE_PART_NAMES:
            c.ui.print(f"   {name:<14}- ${price} each")
        for i, (name, _price) in enumerate(T.STORE_PART_NAMES):
            c.ui.print()
            c.ui.print(f"How many {name}s? ")
            a = c.ui.key(ALLOWED["STORE_PART"], 1)
            want = int(a) if a and a.isdigit() else 0
            if want > MAX_PART:
                c.ui.print(f"Your wagon may only carry 3 {name}s.")
                common.wait_key(c)
                continue
            c.mem.poke(910 + i, want, 811)
    show_bill(c)


def leave(c):
    """Lines 5000-5020: leave the store, or be told why not.

    Line 5000 refuses if the bill exceeds the money; line 5006 refuses if there are
    no oxen; line 5010 writes what is left, times ten, to 913 and 914.
    """
    st = c.st
    total = bill(c)
    if num.lt(st.MY, num.parse(str(total))):
        c.ui.print()
        c.ui.print("Okay, that comes to a total of "
                   + common.dollar_text(c, num.parse(str(total)))
                   + ".  But I see that you only have $"
                   + common.money(c, st.MY)
                   + ".  We'd better go over the list again.")
        common.wait_key(c)
        return False
    if not c.mem.peek(905):
        c.ui.print()
        c.ui.print("Don't forget, you'll need oxen to pull your wagon.")
        common.wait_key(c)
        return False
    left = num.sub(st.MY, num.parse(str(total)))
    c.mem.poke_word(913, num.trunc(num.mul(left, num.parse("10"))), 5010)
    st.MY = left
    c.ui.print()
    c.ui.print("Well then, you're ready to start.  Good luck!  You have a long and "
               "difficult journey ahead of you.")
    common.wait_key(c)
    c.ui.print()
    c.ui.print("Now loading the wagon...")
    # line 5020 chains to OREGON TRAIL with & RNH, so the store never comes back
    return True
