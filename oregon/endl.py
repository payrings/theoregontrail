"""END.LIB: The Dalles, and the hand-over to ``WIN``.

Lines 50000 to 50080. At The Dalles the party chooses between floating the Columbia
and paying the Barlow toll, which is ``5 + INT(I(2) + .5) * .5`` -- $5 and fifty
cents an ox. **A party holding exactly the toll cannot pay it**, because the test is
``MY > V`` and not ``>=``; the paper lists that in section 13 and it is reproduced.

Whichever way is taken, line 50050 writes the end-of-journey layout: the party size
at 900, the year at 901, the month and day at 902 and 903, the oxen at 909, the food
across 906 and 907, the clothing at 908, the bullets across 904 and 905, the health
band at 916 and the cents at 917, with the dollars at 913 and 914. Then the raft runs
or ``WIN`` does.

``POKE 901, AY - 1800`` is where a party that arrives more than 255 years after 1800
stops the program with error 53, which is what the paper's long-wait study found.
"""

from __future__ import annotations

from . import num
from .ui import ALLOWED

__all__ = ["the_dalles", "arrive_willamette", "write_handover", "TOLL_BASE"]

TOLL_BASE = 5


def the_dalles(c):
    """Lines 50000-50040: the choice, and the toll."""
    st = c.st
    from . import common
    while True:
        c.ui.clear()
        c.ui.print("The trail divides here.")
        c.ui.print("You may:")
        c.ui.print()
        c.ui.print("1. float down the Columbia River")
        c.ui.print()
        c.ui.print("2. take the Barlow Toll Road")
        c.ui.print()
        c.ui.print("What is your choice? ")
        a = c.ui.key(ALLOWED["DALLES"], 1, default="2")
        if a == "1":
            write_handover(c)
            from . import floatraft
            floatraft.run(c)
            return "FLOAT"
        # line 50015: the money is rounded to cents before the toll is worked out
        st.MY = num.store(num.div(num.mul(st.MY, num.parse("100")), num.parse("100")))
        toll = num.add(num.parse(str(TOLL_BASE)),
                       num.mul(num.int_(num.add(st.I[2], num.HALF)), num.HALF))
        c.ui.clear()
        c.ui.print("You must pay $" + common.money(c, toll)
                   + " to travel the Barlow road.  Are you willing to do this? ")
        if common.yes_no(c) == "Y" and num.gt(st.MY, toll):
            st.MY = num.sub(st.MY, toll)
            # the toll road is segment 18: a hundred miles to the Willamette Valley,
            # travelled exactly as any other segment is
            from . import trail
            st.LM = 16
            st.LL = 1
            trail.load_segment(c, 18)
            trail.start_segment(c)
            trail.travel_screen(c)
            trail.daily_cycle(c)
            st.LM = 17
            # arriving at the Willamette Valley by road is line 1020 reaching
            # END.LIB 50050, exactly as the river route is
            write_handover(c)
            return "WIN"
        c.ui.print()
        c.ui.print("You do not have enough cash.")
        common.wait_key(c)


def arrive_willamette(c):
    """Line 1020 of OREGON TRAIL reaches here when ``LM`` is 17."""
    write_handover(c)
    return "WIN"


def write_handover(c):
    """Lines 50050-50070: the end-of-journey memory layout.

    Note that the oxen go to **909** here, where the store put the boxes of bullets,
    and the bullets to 904 and 905, where the store put the yokes. The two layouts
    are genuinely different and must not be mixed up; ``FLOAT`` reads the oxen from
    909 and the bullets from 904 and 905.
    """
    st = c.st
    from . import common
    c.mem.poke(900, num.as_int(st.NP), 50050)
    c.mem.poke(901, num.as_int(st.AY) - 1800, 50050)
    c.mem.poke(902, num.as_int(st.AM), 50050)
    c.mem.poke(903, num.as_int(st.AD), 50050)
    c.mem.poke(909, num.trunc(num.add(st.I[2], num.HALF)), 50050)
    food = num.trunc(st.I[8])
    c.mem.poke_word(906, food, 50050)
    c.mem.poke(908, num.trunc(st.I[3]), 50050)
    bullets = num.trunc(st.I[4])
    c.mem.poke_word(904, bullets, 50050)
    c.mem.poke(916, st.health_band(), 50050)
    c.mem.put_names([st.N[i] for i in range(num.as_int(st.NP))], 50060)
    st.MY = num.store(num.div(num.mul(st.MY, num.parse("100")), num.parse("100")))
    for item in (5, 6, 7):
        c.mem.poke(905 + item, num.trunc(st.I[item]), 50070)
    c.mem.poke_word(913, num.trunc(st.MY), 50070)
    cents = num.add(num.sub(st.MY, num.int_(st.MY)), num.parse("0.5"))
    c.mem.poke(917, num.trunc(cents), 50070)
    return st
