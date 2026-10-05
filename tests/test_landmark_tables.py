"""Tables 7 and 8 of the paper, checked against the data this package uses.

The two tables live in ``VAR.BIN``: ``LM$(0 to 17, 0 to 3)`` describes the eighteen
landmarks and ``LM(0 to 18, 0 to 2)`` the nineteen segments. They were originally
read from the data file, so they are transcribed here from the paper rather than
reconstructed from the code, and every field is compared. Two fields were wrong
before this test existed -- the type of landmark 0 and the name of landmark 9 --
and neither was visible from the code alone.
"""

from __future__ import annotations

from oregon.data import landmarks as L

#: Table 7: name, type, segment out, second segment. Type 1 is a fort where buying
#: is allowed, 2 a river crossing, 0 neither.
TABLE_7 = [
    ("Independence", 1, 0, None),
    ("the Kansas River crossing", 2, 1, None),
    ("the Big Blue River crossing", 2, 2, None),
    ("Fort Kearney", 1, 3, None),
    ("Chimney Rock", 0, 4, None),
    ("Fort Laramie", 1, 5, None),
    ("Independence Rock", 0, 6, None),
    ("South Pass", 0, 7, 8),
    ("Fort Bridger", 1, 9, None),
    ("Green River crossing", 2, 10, None),
    ("Soda Springs", 0, 11, None),
    ("Fort Hall", 1, 12, None),
    ("the Snake River crossing", 2, 13, None),
    ("Fort Boise", 1, 14, None),
    ("the Blue Mountains", 0, 15, 16),
    ("Fort Walla Walla", 1, 17, None),
    ("The Dalles", 0, 18, None),
    ("the Willamette Valley", 0, None, None),
]

#: Table 8: miles, speed base, and the landmark the segment ends at.
TABLE_8 = [
    (102, 20, 1),    # 0  Independence to Kansas River
    (83, 20, 2),     # 1  Kansas River to Big Blue River
    (119, 20, 3),    # 2  Big Blue River to Fort Kearney
    (250, 20, 4),    # 3  Fort Kearney to Chimney Rock
    (86, 20, 5),     # 4  Chimney Rock to Fort Laramie
    (190, 12, 6),    # 5  Fort Laramie to Independence Rock
    (102, 12, 7),    # 6  Independence Rock to South Pass
    (57, 12, 9),     # 7  South Pass to Green River
    (125, 12, 8),    # 8  South Pass to Fort Bridger
    (162, 12, 10),   # 9  Fort Bridger to Soda Springs
    (144, 12, 10),   # 10 Green River to Soda Springs
    (57, 12, 11),    # 11 Soda Springs to Fort Hall
    (182, 12, 12),   # 12 Fort Hall to Snake River
    (114, 12, 13),   # 13 Snake River to Fort Boise
    (160, 12, 14),   # 14 Fort Boise to Blue Mountains
    (55, 12, 15),    # 15 Blue Mountains to Fort Walla Walla
    (125, 12, 16),   # 16 Blue Mountains to The Dalles
    (120, 12, 16),   # 17 Fort Walla Walla to The Dalles
    (100, 12, 17),   # 18 The Dalles to Willamette Valley (Barlow Road)
]


def test_table_7_the_landmarks():
    assert len(TABLE_7) == 18
    assert len(L.LM_NAMES) == len(TABLE_7)
    for n, (name, typ, seg, seg2) in enumerate(TABLE_7):
        assert L.LM_NAMES[n] == name, f"landmark {n}"
        assert L.LM_TYPE[n] == typ, f"landmark {n} type"
        assert L.LM_SEGMENT[n] == (0 if seg is None else seg), f"landmark {n} segment"
        assert L.LM_SEGMENT2[n] == (0 if seg2 is None else seg2), f"landmark {n} second"


def test_table_8_the_segments():
    assert len(TABLE_8) == 19
    assert len(L.SEG_MILES) == len(TABLE_8)
    for s, (miles, speed, ends) in enumerate(TABLE_8):
        assert L.SEG_MILES[s] == miles, f"segment {s} miles"
        assert L.SEG_SPEED[s] == speed, f"segment {s} speed"
        assert L.SEG_ENDS_AT[s] == ends, f"segment {s} ends at"


def test_only_three_landmarks_divide():
    """South Pass and the Blue Mountains branch; The Dalles is where ``END.LIB``
    takes over, and it is reached either direct or by Fort Walla Walla."""
    branching = [n for n in range(len(TABLE_7)) if TABLE_7[n][3] is not None]
    assert branching == [7, 14]


def test_the_four_distances_to_the_end():
    """Both ways into The Dalles can be followed by segment 18, so the crossing is
    1,771 or 1,821 to The Dalles and 1,871 or 1,921 to the Willamette Valley."""
    by_green_river = [0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14]
    to_the_dalles = [16]
    via_walla_walla = [15, 17]
    barlow = 18

    def miles(segments):
        return sum(L.SEG_MILES[s] for s in segments)

    common = miles(by_green_river)
    assert common + miles(to_the_dalles) == 1771
    assert common + miles(to_the_dalles) + L.SEG_MILES[barlow] == 1871
    assert common + miles(via_walla_walla) == 1821
    assert common + miles(via_walla_walla) + L.SEG_MILES[barlow] == 1921


def test_both_ways_into_the_dalles_lead_on_to_the_barlow_road():
    """``LM$(16, 2)`` is 18 whichever way the party arrived, so all four totals are
    reachable and none of them is a special case in the code."""
    direct = L.LM_SEGMENT2[14]                        # the Blue Mountains' second
    assert direct == 16 and L.SEG_ENDS_AT[direct] == 16
    assert L.SEG_ENDS_AT[15] == 15                  # to Fort Walla Walla
    assert L.SEG_ENDS_AT[L.LM_SEGMENT[15]] == 16      # and on to The Dalles
    assert L.LM_SEGMENT[16] == 18
    assert L.SEG_ENDS_AT[18] == 17


def test_independence_is_a_fort():
    """Table 7 gives landmark 0 type 1, so the action menu at Independence offers
    "Buy supplies" as well as "Talk to people"."""
    assert L.LM_TYPE[0] == 1
    assert L.LM_TYPE[3] == 1
