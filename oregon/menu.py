"""MENU (side 1) and MANAGEMENT: the title screen, the profession, the names and
the top ten.

``MENU`` 100-1020 is the menu itself, 2000-2235 the top-ten list and the "how points
are earned" screens, 2300 the sound switch, 4000-4110 the choice of profession,
6000-6045 the party names, 7000-7500 the text screens and 9000 the start of a game.
``MANAGEMENT`` 100-1015 and its option handlers are the teacher menu reached with
Control-A.
"""

from __future__ import annotations

from . import common, num
from .data import hiscore as HIS
from .data import text as T
from .ui import ALLOWED

__all__ = ["main_menu", "profession", "party_names", "top_ten", "how_points",
           "learn", "management", "shuffle_names"]

VERSION = "Version 1.4"


# --------------------------------------------------------------------- MENU
def main_menu(c) -> str:
    """Lines 1000-1020: the four choices, and the reseed that follows each.

    Line 1015 is the only reseeding in the game: the argument is the 16-bit counter
    the keyboard routine keeps while it waits for a key, so the seed is fixed by how
    long the player took to press it. ``--seed`` on the command line supplies the
    same number directly.
    """
    while True:
        c.set_program("MENU")
        c.ui.clear()
        c.ui.print("The Oregon Trail")
        c.ui.print(VERSION)
        c.ui.print()
        c.ui.print("You may:")
        c.ui.print()
        c.ui.print("  1. Travel the trail")
        c.ui.print("  2. Learn about the trail")
        c.ui.print("  3. See the Oregon Top Ten")
        c.ui.print("  4. Turn sound " + T.SOUND_WORDS[0 if c.mem.peek(975) else 1])
        c.ui.print()
        c.ui.print("What is your choice? ")
        a = c.ui.key(ALLOWED["CHOICE"], 1)
        if not a:
            continue
        digit = ord(a[0]) - 48
        # Z = RND(-(PEEK(78) + PEEK(79) * 256))
        c.rng.seed_from_keyboard(c.mem.keyboard_counter)
        if digit == 1:
            c.set_program("MANAGEMENT")
            c.ui.print("Getting Management Options...")
            management(c)
            continue
        if digit == 2:
            learn(c)
        elif digit == 3:
            top_ten(c)
        elif digit == 4:
            toggle_sound(c)
        elif digit == 0:                      # chr$(1), the Control-A route
            c.set_program("MANAGEMENT")
            c.ui.print("Getting Management Options...")
            management(c)
            continue
        else:
            start(c)
            return "BUY SUPPLIES"


def toggle_sound(c):
    """Line 2300: ``POKE 975, NOT PEEK(975)``."""
    on = 0 if c.mem.peek(975) else 1
    c.mem.poke(975, on)
    c.ui.clear()
    c.ui.print("The sound is now turned " + T.SOUND_WORDS[on] + ".")
    c.ui.print()
    c.ui.print("You may turn the sound on or off during the program by pressing "
               "Control-S.")
    common.wait_key(c)


# ---------------------------------------------------------------- profession
def profession(c) -> int:
    """Lines 4000-4030: be a banker, a carpenter or a farmer.

    Line 4030 stores the choice at 915 and the starting money, times ten, at 913
    and 914: ``Z = ((Z = 1) * 1600 + (Z = 2) * 800 + (Z = 3) * 400) * 10``. The three
    professions differ only in that money, and the multiplier in the score at the end
    is what makes the harder ones worth choosing.
    """
    while True:
        c.ui.clear()
        c.ui.print("Many kinds of people made the trip to Oregon.")
        c.ui.print()
        c.ui.print("You may:")
        c.ui.print("1. Be a " + T.PROFESSIONS[0])
        c.ui.print("2. Be a " + T.PROFESSIONS[1])
        c.ui.print("3. Be a " + T.PROFESSIONS[2])
        c.ui.print("4. Find out the differences between these choices")
        c.ui.print()
        c.ui.print("What is your choice? ")
        a = c.ui.key(ALLOWED["PROFESSION"], 1)
        z = int(a) if a and a.isdigit() else 0
        if z == 4:
            difficulty_text(c)
            continue
        if z in (1, 2, 3):
            c.mem.poke(915, z, 4030)
            dollars = (1600, 800, 400)[z - 1]
            c.mem.poke_word(913, dollars * 10, 4030)
            return z
        c.ui.print("What is your choice? ")
        c.ui.key(ALLOWED["PROFESSION"], 1)


def difficulty_text(c):
    """Lines 4100-4110."""
    c.ui.clear()
    c.ui.print("Traveling to Oregon isn't easy!  But if you're a banker, you'll "
               "have more money for supplies and services than a carpenter or a "
               "farmer.")
    c.ui.print()
    c.ui.print("However, the harder you have to try, the more points you deserve!  "
               "Therefore, the farmer earns the greatest number of points and the "
               "banker earns the least.")
    common.wait_key(c)


# --------------------------------------------------------------------- names
def shuffle_names(c) -> list:
    """Lines 6000-6015: the ten default names into random order.

    Ten draws, one per name, always: ``Z = INT (RND (1) * 10)`` and if that slot is
    taken the code steps forward, wrapping from 9 to 0. So the number of draws does
    not depend on the values, which is what Appendix G.1 records.
    """
    names = [""] * 10
    for _ in range(10):
        z = c.rng.int_range("MENU 6000 name slot", 10)
        while names[z]:
            z = z + 1
            z = z * (z < 10)                  # 10 wraps back to 0
        names[z] = T.DEFAULT_NAMES[_]
    return names


def party_names(c, defaults=None) -> list:
    """Lines 6015-6045: the five names, confirmed and written to memory.

    The player types the leader's name and then up to four others; a blank keeps the
    shuffled default. Line 6045 writes the five names from address 1920, each ended
    by a zero byte, and ``OREGON TRAIL`` 29010 reads them back.
    """
    pool = list(defaults or shuffle_names(c))
    n = list(pool[:5])
    c.ui.clear()
    c.ui.print("What is the first name of the wagon leader? ")
    typed = c.ui.key(ALLOWED["NAMES"], 9)
    n[0] = typed or n[0]
    c.ui.print()
    c.ui.print("What are the first names of the four other members in your party? ")
    c.ui.print()
    c.ui.print("(Enter names or press Return)")
    # Line 6030 reads a name for each of the other four in turn; a blank keeps the
    # default *and stops the asking*, which is what the BASIC does with its FOR L =
    # L TO 4 that prints the rest of the defaults and jumps to the confirmation.
    for i in range(1, 5):
        typed = c.ui.key(ALLOWED["NAMES"], 9, default="")
        if not typed:
            break
        n[i] = typed
    while True:
        c.ui.print()
        for i in range(5):
            c.ui.print(f"{i + 1}. {n[i]}")
        c.ui.print()
        c.ui.print("Are these names correct? ")
        if common.yes_no(c) == "Y":
            break
        c.ui.print("Change which name? ")
        a = c.ui.key(ALLOWED["MANAGE"], 1)
        which = (int(a) - 1) if a and a.isdigit() else 0
        if 0 <= which <= 4:
            c.ui.print(" ")
            typed = c.ui.key(ALLOWED["NAMES"], 9)
            if typed:
                n[which] = typed
    c.mem.put_names(n, 6045)
    return n


# ------------------------------------------------------------------ top ten
def read_top_ten(c):
    if not getattr(c, "_hiscore", None):
        entries = c.files.read_hiscore()
        if not entries:
            entries = HIS.original()
            c.files.write_hiscore(entries)
        c._hiscore = entries
    return c._hiscore


def top_ten(c, entries=None, rating_only: bool = False):
    """Line 2005: the list, then the offer to explain the points.

    Line 2010 pads the points to four columns with ``RIGHT$("  " + Z$, 4)``, which
    is why the numbers line up under the heading.
    """
    entries = entries if entries is not None else read_top_ten(c)
    c.ui.clear()
    c.ui.print("Name".ljust(16) + "Points".rjust(8) + "Rating")
    c.ui.print()
    for name, points, rating in entries[:10]:
        c.ui.print(str(name)[:16].ljust(16) + str(points).rjust(8) + "  " + str(rating))
    c.ui.print()
    if not rating_only:
        c.ui.print("Would you like to see how points are earned? ")
        if common.yes_no(c) == "Y":
            how_points(c)


def how_points(c):
    """Lines 2200-2235: the three explanation screens, from DATA 29010."""
    c.ui.clear()
    c.ui.print("Your most important resource is the people you have with you.  You "
               "receive points for each member of your party who arrives safely; "
               "you receive more points if they arrive in good health!")
    c.ui.print()
    c.ui.print("Health of        Points per")
    c.ui.print("  Party             Person")
    for word, points in T.SCORE_TEXT[:4]:
        c.ui.print(f"  {word:<18}{points}")
    common.wait_key(c)
    c.ui.clear()
    c.ui.print("The resources you arrive with will help you get started in the new "
               "land.  You receive points for each item you bring safely to Oregon.")
    c.ui.print()
    c.ui.print("Resources of        Points per")
    c.ui.print("   Party               Item")
    for word, points in T.SCORE_TEXT[4:]:
        unit, _, count = word.partition(" (each ")
        c.ui.print(f"   {unit:<20}{points}")
    common.wait_key(c)
    c.ui.clear()
    c.ui.print("You receive points for your occupation in the new land.  Because "
               "more farmers and carpenters were needed than bankers, you receive "
               "double points upon arriving in Oregon as a carpenter, and triple "
               "points for arriving as a farmer.")
    common.wait_key(c)


# --------------------------------------------------------------------- learn
LEARN = [
    ("Try taking a journey by covered wagon across 2000 miles of plains, rivers, "
     "and mountains.  Try!  On the plains, will you slosh your oxen through mud "
     "and water-filled ruts or will you plod through dust six inches deep?"),
    ("How will you cross the rivers?  If you have money, you might take a ferry "
     "(if there is a ferry).  Or, you can ford the river and hope you and your "
     "wagon aren't swallowed alive!"),
    ("What about supplies?  Well, if you're low on food you can hunt.  You might "
     "get a buffalo...you might.  And there are bear in the mountains."),
    ("At the Dalles, you can try navigating the Columbia River, but if running the "
     "rapids with a makeshift raft makes you queasy, better take the Barlow Road."),
]


def learn(c):
    """Lines 7000-7041: the four screens that explain the journey."""
    for text in LEARN:
        c.ui.clear()
        c.ui.print(text)
        common.wait_key(c)
    c.ui.print("If for some reason you don't survive "
               "-- your wagon burns, or thieves steal your oxen, or you run out of "
               "provisions, or you die of cholera -- don't give up!  Try again...and "
               "again...until your name is up with the others on The Oregon Top Ten.")
    common.wait_key(c)


# ---------------------------------------------------------------- start game
def start(c):
    """Line 9000: fix the year, take the profession and the names, hand over.

    ``POKE 901,48`` makes the year 1848, the only year the game ever uses. The
    names and the money are left in memory for ``BUY SUPPLIES`` to read.
    """
    c.set_program("MENU")
    c.mem.poke(901, 48, 9000)
    profession(c)
    n = party_names(c)
    for i in range(5):
        c.st.N[i] = n[i]
    c.st.NP = 5
    c.ui.print()
    c.ui.print(f"Going back to 18{c.mem.peek(901)}...")
    common.wait_key(c)


# ----------------------------------------------------------------- MANAGEMENT
def management(c):
    """Lines 1000-1015: the teacher menu.

    Choice 1 and 2 show the current and the original top ten, 3 erases the current
    list and restores the original ten, 4 erases the tombstone messages, 5 returns
    to the main menu.
    """
    from .menu import top_ten as show
    while True:
        c.set_program("MANAGEMENT")
        c.ui.clear()
        c.ui.print("The Oregon Trail")
        c.ui.print(VERSION)
        c.ui.print()
        c.ui.print("Management Options")
        c.ui.print("You may:")
        c.ui.print()
        for i, opt in enumerate(T.MANAGE_OPTIONS, 1):
            c.ui.print(f"{i}. {opt}")
        c.ui.print()
        c.ui.print("What is your choice? ")
        a = c.ui.key(ALLOWED["MANAGE"], 1)
        z = int(a) if a and a.isdigit() else 0
        if z == 1:
            top_ten(c, read_top_ten(c))
        elif z == 2:
            top_ten(c, HIS.original())
        elif z == 3:
            erase_top_ten(c)
        elif z == 4:
            erase_tombs(c)
        elif z == 5:
            return


def erase_top_ten(c):
    """Line 700: the list is replaced by the original ten, which are on DATA."""
    c.ui.print("If you erase the current Top Ten list, the names and scores will be "
               "replaced by those on the original list.")
    c.ui.print("Do you want to do this? ")
    if common.yes_no(c) == "N":
        return
    c._hiscore = c.files.reset_hiscore()


def erase_tombs(c):
    """Line 200: an empty record on each side, in turn.

    The confirmation names the side as it goes, and an empty record has a segment
    code of 0, which is how the reader at line 29004 tells it from a grave.
    """
    c.ui.print("There may be a tombstone message on each side of the diskette.  If "
               "you erase these messages, they will not be replaced until team "
               "leaders die along the trail.")
    c.ui.print("Do you want to do this? ")
    if common.yes_no(c) == "N":
        return
    for side in (0, 1):
        c.ui.clear()
        c.ui.print(f"Removing tombstones from side {'one' if side == 0 else 'two'}...")
        common.check_side(c, side + 1)
        c.files.erase_tombs(side)
