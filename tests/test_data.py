"""The data tables, checked against the paper.

These are the tables a replica has to get exactly right, and every one of them can
be checked against a number the paper prints independently of the table.
"""
import pytest

from oregon.data import climate, goods, hiscore, illnesses, landmarks, text


def test_the_six_climate_strings_match_table_13():
    """All 144 character codes, against the paper's table rather than the strings."""
    for row in range(6):
        s = climate.WC[row]
        assert len(s) == 24, f"row {row} is {len(s)} characters"
        for month in range(12):
            assert ord(s[month * 2]) == climate.AM_CODES[row][month], (row, month)
            assert ord(s[month * 2 + 1]) == climate.RAIN_CODES[row][month], (row, month)


def test_the_climate_lookup_gives_the_papers_example():
    """Row 0, January: codes 59 and 43, so 9 degrees and 0.039 of rain."""
    assert climate.min_temp(0, 1) == 9
    assert climate.rain_chance(0, 1) == pytest.approx(0.039)


def test_landmarks_and_segments_are_the_shapes_the_paper_gives():
    assert len(landmarks.LM_NAMES) == 18
    assert len(landmarks.SEG_MILES) == 19
    assert len(landmarks.SEG_SPEED) == 19
    assert len(landmarks.SEG_ENDS_AT) == 19
    assert all(t in (0, 1, 2) for t in landmarks.LM_TYPE)
    assert all(s in (20, 12) for s in landmarks.SEG_SPEED)


def test_the_two_cutoffs_are_the_only_second_segments():
    second = [n for n, s in enumerate(landmarks.LM_SEGMENT2) if s]
    assert second == [7, 14], "South Pass and the Blue Mountains, and no others"


def test_every_segment_ends_at_a_landmark_that_leads_somewhere():
    """Every landmark but the last names the segment that leaves it.

    ``LM$(n,2)`` holds a segment *number*, so landmark 0 names segment 0; only the
    Willamette Valley is reached with nothing to choose, and the game ends there
    before line 2200 is ever reached again.
    """
    for dest in range(17):
        assert landmarks.LM_SEGMENT[dest] <= 18
    assert landmarks.SEG_ENDS_AT[-1] == 17


def test_the_route_actually_arrives():
    """Walking the segments out of landmark 0 must reach 17."""
    at = 0
    seen = [at]
    for _ in range(30):
        if at == 17:
            break
        seg = landmarks.LM_SEGMENT[at]
        assert 0 <= seg <= 18, f"landmark {at} names segment {seg}"
        at = landmarks.SEG_ENDS_AT[seg]
        seen.append(at)
    assert seen[-1] == 17, seen


def test_the_speed_base_drops_to_twelve_after_fort_laramie():
    """The base is 20 before Fort Laramie and 12 after, per paper section 4.4."""
    for seg, speed in enumerate(landmarks.SEG_SPEED):
        ends_at = landmarks.SEG_ENDS_AT[seg]
        assert speed == (20 if ends_at <= 5 else 12), (seg, ends_at, speed)


def test_the_climate_zone_has_five_values_and_the_sixth_row_is_unused():
    zones = [landmarks.zone_for(n) for n in range(18)]
    assert min(zones) == 0 and max(zones) == 4
    assert landmarks.ZONE_AT == zones, "the table and the formula must agree"
    # and the Portland row of the climate table is never selected
    assert 5 not in zones


def test_the_goods_table():
    assert len(goods.S) == 7
    assert [r[0] for r in goods.S] == ["Oxen", "Clothing", "Ammunition",
                                       "Wagon wheels", "Wagon axles",
                                       "Wagon tongues", "Food"]
    assert [r[1] for r in goods.S] == [20.0, 10.0, 2.00, 10.0, 10.0, 10.0, 0.20]
    assert goods.BOXES_PER_BULLETS == 20


def test_the_rivers_and_why_they_cannot_be_forded():
    """The Green at 20 feet and the Snake at 6 can never be forded safely."""
    assert len(climate.WC) == 6
    from oregon.data import rivers
    assert len(rivers.RC) == 4
    assert [r[0] for r in rivers.RC] == [1, 1, 20, 6]
    assert rivers.RC[0][5] == 2, "the Kansas has a ferry"
    assert rivers.RC[3][5] == 1, "the Snake has an Indian guide"
    assert rivers.RC[1][5] == 0, "the Big Blue has neither"
    # a wagon clears about 2.5 feet, and 2.5 to 3 only soaks the supplies
    assert all(r[0] > 3 or r[0] < 2.5 for r in rivers.RC)


def test_the_river_index_from_line_50000():
    assert rivers_index(1) == 0 and rivers_index(2) == 1
    assert rivers_index(9) == 2 and rivers_index(12) == 3


def rivers_index(landmark):
    from oregon.data.rivers import RC_RIVER_AT
    return RC_RIVER_AT[landmark]


def test_the_illness_table():
    assert len(illnesses.IL_NAMES) == 9
    assert illnesses.IL_NAMES[0] == "a broken arm"
    assert illnesses.ILLNESS_DAYS[:3] == [30, 30, 10]
    assert all(d == 10 for d in illnesses.ILLNESS_DAYS[2:])
    assert illnesses.DISEASES == [3, 4, 5, 6, 7, 8]


def test_the_original_top_ten_matches_the_papers_table():
    assert hiscore.ORIGINAL[0] == ("Stephen Meek", 7650, "Trail guide")
    assert hiscore.ORIGINAL[-1] == ("Elijah White", 250, "Greenhorn")
    assert len(hiscore.ORIGINAL) == 10
    points = [e[1] for e in hiscore.ORIGINAL]
    assert points == sorted(points, reverse=True)


def test_the_text_arrays_have_the_lengths_the_tables_give():
    assert len(text.MONTHS) == 12
    assert len(text.I_NAMES) == 9
    assert len(text.PACE) == 3 and len(text.RATIONS) == 3
    assert len(text.HEALTH) == 4
    assert len(text.WEATHER) == 10
    assert len(text.ACTIONS) == 10
    assert len(text.DEFAULT_NAMES) == 10
    assert len(text.SCORE_TEXT) == 11
    assert text.MONTHS[0] == "January" and text.MONTHS[11] == "December"
    assert text.WEATHER[6] == "rainy" and text.WEATHER[9] == "very snowy"


def test_the_dialogue_records_load_and_are_the_papers_fifty_one():
    pytest.importorskip("pathlib")
    from oregon.data import dialogue
    if not dialogue.available():
        pytest.skip("the reference document is not in docs/")
    d = dialogue.load()
    assert len(d) == 51
    assert d.landmarks() == list(range(17))
    assert d.speaker(1, 2) == "A ferry operator"
    # the game keeps the original spelling of the dialogue
    assert "Keep'em moving but set them a fair pace" in d.text(2, 2)


def test_the_climate_zone_covers_the_segments_the_code_actually_runs():
    """Table 12 of the paper lists landmark numbers where it means segments.

    The zone is set from the *landmark* on arrival (line 1000) and applies to the
    segment that leaves it, so the segment ranges come out as 0-2, 3-5, 6-11, 12-14
    and 15-18. The paper's column says 0-2, 3-5, 6-10, 11-13, 14-16, which puts
    climate row 2 on the run to Fort Hall and row 3 on the run to the Blue
    Mountains; both are wrong, because Fort Hall is zone 3 and the Blue Mountains
    zone 4. This test pins the mapping the code uses.
    """
    from oregon.trail import climate_zone
    ranges = {}
    # Every landmark but the last has an outgoing segment. Note that
    # LM$(n, 2) holds a segment *number*, so landmark 0 names segment 0 and a
    # zero there is not a "none" marker -- see FINDINGS 6.3.
    for landmark in range(17):
        zone = climate_zone(landmark)
        # the first segment always exists -- and may legitimately be 0 -- while a
        # zero in the second column really does mean "there is none"
        ranges.setdefault(zone, []).append(landmarks.LM_SEGMENT[landmark])
        if landmarks.LM_SEGMENT2[landmark]:
            ranges[zone].append(landmarks.LM_SEGMENT2[landmark])
    covered = {z: sorted(segs) for z, segs in sorted(ranges.items())}
    assert covered == {0: [0, 1, 2], 1: [3, 4, 5], 2: [6, 7, 8, 9, 10, 11],
                       3: [12, 13, 14], 4: [15, 16, 17, 18]}, covered
    assert sum(len(v) for v in covered.values()) == 19, "all nineteen segments"


def test_event_two_has_no_routine_and_cannot_be_reached():
    """Line 3180 names 10200, which the program does not have.

    ``RE(2) = 0`` at line 29001, so the chance is nil; if it were ever reached the
    original raises UNDEF'D STATEMENT, and so does this.
    """
    from oregon import events
    from oregon.state import State
    assert events.EVENT_COUNT == 15
    assert events.unreachable_event == 2
    assert State().RE[2].is_zero(), "RE(2) is 0, so event 2 can never fire"
    with pytest.raises(events.UndefStatementError):
        events.fire(None, 2)
