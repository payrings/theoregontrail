"""The optional graphical mode, tested with a small made-up set of pictures.

Most of what is here needs no pictures of its own: the font is a plain block
alphabet and the pictures are coloured squares, so the checks are about where
things are drawn, how text wraps and whether the game can be played through the
graphical interface from a script. Two tests at the end use the pictures in the
repository, to check that a clean checkout can start the graphical mode.
"""

import json
import os

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from oregon.graphics import Assets, screens  # noqa: E402
from oregon.graphics.backends import ScriptBackend  # noqa: E402
from oregon.graphics.gui import GraphicalUI  # noqa: E402


@pytest.fixture(autouse=True)
def _keep_arithmetic_backend():
    """Some tests here choose the exact backend; put the session's one back afterwards."""
    from oregon import applesoft
    yield
    applesoft.use("rom" if applesoft.rom_available() else "exact")


@pytest.fixture()
def folder(tmp_path):
    """A font of solid 5 x 7 blocks (width 5, so a letter advances 7 dots) and a few squares."""
    (tmp_path / "font").mkdir()
    (tmp_path / "images").mkdir()
    (tmp_path / "screens").mkdir()
    cell = 10
    chars = list(range(32, 128))
    sheet = Image.new("RGBA", (16 * cell, 6 * cell), (0, 0, 0, 0))
    glyphs = {}
    for i, c in enumerate(chars):
        x, y = (i % 16) * cell, (i // 16) * cell
        if c != 32:
            for dx in range(5):
                for dy in range(7):
                    sheet.putpixel((x + dx, y + dy), (255, 255, 254, 255))
        glyphs[str(c)] = {"width": 5, "yoff": 0, "rows": 7, "x": x, "y": y}
    sheet.save(tmp_path / "font" / "font.png")
    (tmp_path / "font" / "font.json").write_text(json.dumps({"cell": cell, "hsp": 2, "glyphs": glyphs}))
    Image.new("RGBA", (14, 10), (255, 0, 0, 255)).save(tmp_path / "images" / "first_02.png")
    return str(tmp_path)


def make(folder, keys=""):
    backend = ScriptBackend(list(keys))
    return GraphicalUI(Assets(folder), backend), backend


def lit_rows(ui):
    return sorted({y for (_, y) in ui.cv.dots})


def test_letters_advance_by_width_plus_two(folder):
    ui, _ = make(folder)
    ui.put("ab")
    assert ui.cx == 14
    assert ui.width("ab") == 14


def test_lines_are_nine_dots_apart(folder):
    ui, _ = make(folder)
    ui.print("a")
    ui.print("b")
    assert ui.cy == 18


def test_wrap_rule_is_width_minus_one(folder):
    """A word goes to the next line when cx + width > window width - 1 (width counts the
    two dots after each letter). Each letter is 7 dots here."""
    ui, _ = make(folder)
    ui.dfw(0, 0, 36, 100)                  # 36 - 1 = 35 = five letters
    ui.para("aaaaa bbbbb")
    assert ui.cy == 18 and ui.cx == 0       # two lines, then the newline
    ui2, _ = make(folder)
    ui2.dfw(0, 0, 35, 100)                 # 34 allows four letters only
    ui2.para("aaaaa")
    assert ui2.cy == 9                     # a single long word is never split


def test_prompt_keeps_the_cursor_and_key_reads_it(folder):
    ui, b = make(folder, "7")
    ui.print("Which? ")
    y = ui.cy
    assert ui.key("-19", 1) == "7"
    assert ui.cy == y + 9                  # the answer is echoed, then a new line


def test_key_filters_and_ends_on_return(folder):
    ui, _ = make(folder, "ab1\r")
    assert ui.key("-09", 3) == "1"


def test_yes_no_answers_at_once(folder):
    ui, _ = make(folder, "x n")
    assert ui.yes_no("Sure? ") == "N"


def test_missing_pictures_are_skipped(folder):
    ui, _ = make(folder)
    screens.title(ui, "on")                # first_03 does not exist: no error
    assert ui.cv.dots


def test_box_clears_letters(folder):
    ui, _ = make(folder)
    ui.put("abc")
    ui.cv.box(0, 0, 100, 20)
    assert not ui.cv.dots


def test_coloured_box_runs_from_first_to_last_lit_column(folder):
    ui, _ = make(folder)
    ui.cv.box(20, 0, 70, 3, 5)             # orange: odd columns, so 21 to 69
    px = ui.cv.render().load()
    assert px[20, 0] == (0, 0, 0) and px[21, 0] == (242, 94, 0)
    assert px[69, 0] == (242, 94, 0) and px[70, 0] == (0, 0, 0)


def test_lone_dots_take_the_column_colour(folder):
    ui, _ = make(folder)
    ui.cv.dots.update({(10, 5), (13, 5), (14, 5), (15, 5)})
    px = ui.cv.render().load()
    assert px[10, 5] == (199, 52, 255)     # even column, alone: violet
    assert px[14, 5] == (255, 255, 254)    # beside another: white


def test_store_plays_through_the_graphical_interface(folder):
    """The shop, driven by keys: buy 6 yoke, leave."""
    from oregon import applesoft, buysupplies
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import SeededRnd
    from oregon.trace import Tracer
    try:
        applesoft.use("exact")
    except Exception:                       # noqa: BLE001
        pytest.skip("no arithmetic backend")
    keys = [" "] * 4 + ["1", "6", "8", " "] + [" ", " "]
    ui, b = make(folder, keys)
    c = Context(ui=ui, rng=SeededRnd(), files=Files(os.path.join(folder, "data")),
                trace=Tracer(None))
    c.mem.poke(901, 48)
    c.mem.poke(902, 5)
    c.mem.poke(903, 1)
    c.mem.poke_word(913, 8000)
    buysupplies.init_state(c)
    r = buysupplies.store(c)
    assert r["yokes"] == 6
    assert c.mem.peek(905) == 6


def test_store_leaves_on_the_space_bar_and_ignores_return(folder):
    """Line 252 takes 1 to 5 or the space bar: Return does not leave the store."""
    from oregon import buysupplies
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import SeededRnd
    from oregon.trace import Tracer
    # the intro's four waits, 1 and 6 yoke, then two Returns at the item prompt (ignored),
    # the space bar (leave), and the wait that follows
    keys = [" "] * 4 + ["1", "6"] + ["\r", "\r", " "] + [" "]
    ui, b = make(folder, keys)
    c = Context(ui=ui, rng=SeededRnd(), files=Files(os.path.join(folder, "data")),
                trace=Tracer(None))
    c.mem.poke(901, 48)
    c.mem.poke(902, 5)
    c.mem.poke(903, 1)
    c.mem.poke_word(913, 8000)
    buysupplies.init_state(c)
    assert buysupplies.store(c)["yokes"] == 6
    assert b.keys == []                      # both Returns were read and ignored


def test_each_travelling_day_is_shown_step_by_step(folder):
    """With a pause set, the day's scene is put on the screen at each four-dot step."""
    from oregon import trail
    from oregon.__main__ import apply_preset
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import SeededRnd
    from oregon.trace import Tracer

    class Counting(ScriptBackend):
        shown = 0

        def show(self, img):
            self.shown += 1
            super().show(img)

    b = Counting()
    ui = GraphicalUI(Assets(folder), b)
    ui.daily_pause = 0.001
    c = Context(ui=ui, rng=SeededRnd(), files=Files(os.path.join(folder, "data")),
                trace=Tracer(None))
    apply_preset(c)
    trail.load_state(c)
    c.st.LM, c.st.NM = 0, 1
    trail.scene_start(c)
    c.scene["ix"] -= 12                      # three steps behind where the miles put it
    trail.scene(c, daily=True)
    assert b.shown == 4                      # three steps and the finished day
    assert c.scene["wg"] == 1                # the wheels turned 1 -> 2 -> 3 -> 1


def test_travel_screen_layout(folder):
    """Ground, white facts panel, the line above it, and the bottom line at 182 for line 950."""
    ui, _ = make(folder)
    screens.travel(ui, "prairie", 8, -22, 2, 1, ["Date", "Weather", "Health", "Food",
                                                 "Next landmark", "Miles traveled"],
                   ["April 3, 1848", "warm", "good", "470 pounds", "82 miles", "20 miles"],
                   prompt="Press RETURN to size up the situation")
    im = ui.cv.render()
    assert im.getpixel((101, 80)) == (56, 203, 0)           # grass on the odd columns
    assert im.getpixel((100, 123)) == (255, 255, 254)       # the panel is white...
    assert im.getpixel((100, 179)) == (255, 255, 254)       # ...down to row 179
    assert im.getpixel((100, 180)) == (0, 0, 0)
    assert im.getpixel((100, 100)) == (56, 203, 0) or im.getpixel((100, 100)) == (0, 0, 0)
    ui.wait_key(y=182)
    assert min(y for (_, y) in ui.cv.dots if y >= 180) == 182
    ui.wait_key()
    assert min(y for (_, y) in ui.cv.dots if y >= 180) == 184


def test_trail_screens_play_through_the_graphical_interface(folder):
    """The action menu and the screens it opens, from the keyboard, on the trail."""
    from oregon import action, applesoft
    from oregon.__main__ import apply_preset
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import SeededRnd
    from oregon.trace import Tracer
    try:
        applesoft.use("exact")
    except Exception:                       # noqa: BLE001
        pytest.skip("no arithmetic backend")
    # supplies, map, pace (and its explanation), rations, talk, the fort store, continue
    # Every typed answer ends with Return, as & INP's does; only a "press the space bar" key is a bare key.
    keys = ["2", "\r", " ", "3", "\r", " ", "4", "\r", "4", "\r", " ", "2", "\r", "5", "\r", "2", "\r",
            "8", "\r", " ", "9", "\r", "8", "\r", "1", "\r"]

    class Limited(ScriptBackend):             # a wrong key list must fail, not wait for ever
        reads = 0

        def read(self):
            self.reads += 1
            assert self.reads < 100, "the script ran out of keys"
            return super().read()

    b = Limited(keys)
    ui = GraphicalUI(Assets(folder), b)
    c = Context(ui=ui, rng=SeededRnd(), files=Files(os.path.join(folder, "data")),
                trace=Tracer(None))
    apply_preset(c)
    c.st.LL = 0                              # at Independence, so there is someone to talk to
    c.st.A = 0
    assert action.action_menu(c) in (None, "CONTINUE")
    assert b.keys == []                      # every key was used
    from oregon import num
    assert num.as_int(c.st.P) == 2 and num.as_int(c.st.R) == 2


def test_graphics_without_pictures_falls_back_to_the_text_mode(tmp_path, capsys):
    """No pictures: say so, and play in the terminal rather than stopping."""
    from oregon.__main__ import build_parser, build_ui
    args = build_parser().parse_args(["--graphics", "--assets", str(tmp_path / "nowhere")])
    ui = build_ui(args)
    err = capsys.readouterr().err
    assert "assets folder not found" in err
    assert "falling back to the text mode" in err
    assert type(ui).__name__ == "TerminalUI"


def test_the_pictures_in_the_repository_are_the_default_ones():
    """The graphical mode finds its pictures in a clean checkout."""
    from oregon.graphics import default_folder
    folder = default_folder()
    assert os.path.isdir(folder), folder
    assert os.path.isfile(os.path.join(folder, "font", "font.png"))
    assert os.path.isfile(os.path.join(folder, "font", "font.json"))
    assert os.path.isfile(os.path.join(folder, "screens", "l0.png"))
    assert os.path.isfile(os.path.join(folder, "screens", "m0.png"))


def test_the_graphical_ui_starts_from_the_pictures_in_the_repository():
    """The window's interface builds from the tracked folder, with no display."""
    from oregon.graphics import Assets
    from oregon.graphics.backends import ScriptBackend
    from oregon.graphics.gui import GraphicalUI
    ui = GraphicalUI(Assets(), ScriptBackend())
    assert ui.cv is not None
    assert ui.assets.glyphs                       # the font loaded
    assert ui.assets.screen("l0") is not None      # a landmark picture loaded


# ----------------------------------------------------------------- lines, map, boxes
def test_line_steps_across_or_down_never_both(folder):
    """The ROM's line routine (HLIN) draws dx + dy + 1 dots and moves one way each step."""
    ui, _ = make(folder)
    ui.cv.line(10, 10, 20, 14, 4)
    ui2, _ = make(folder)
    ui2.cv.line(10, 10, 20, 14, 3)
    im = ui2.cv.render()
    lit = [(x, y) for y in range(8, 17) for x in range(8, 23) if im.getpixel((x, y)) != (0, 0, 0)]
    assert len(lit) == 10 + 4 + 1
    lit.sort()
    for (x1, y1), (x2, y2) in zip(lit, lit[1:]):
        assert abs(x2 - x1) + abs(y2 - y1) == 1 or (y2 < y1 and x2 - x1 == 1)


def test_map_route_is_drawn_between_the_landmarks(folder):
    ui, _ = make(folder)
    screens.map_screen(ui, [0, 1, 2], (2, 3, 5.0, 10.0))
    im = ui.cv.render()
    # the first leg runs from (245, 139) to (235, 136); its end points are black
    assert im.getpixel((245, 139)) == (0, 0, 0) and im.getpixel((235, 136)) == (0, 0, 0)


def test_broken_part_box_is_an_unframed_black_rectangle(folder):
    ui, _ = make(folder)
    ui.cv.box(0, 60, 278, 110, 5)
    screens.part_box(ui, "Broken wagon axle.  Would you like to try to repair it? ")
    im = ui.cv.render()
    assert im.getpixel((7, 66)) == (0, 0, 0) and im.getpixel((272, 97)) == (0, 0, 0)
    assert im.getpixel((275, 66)) != (0, 0, 0)                  # the orange ground outside it
    assert any(d[1] >= 68 for d in ui.cv.dots)                  # the text is inside


def test_tombstone_cuts_black_letters_in_the_stone(folder):
    ui, _ = make(folder)
    ui.cv.base.paste((255, 255, 255), (0, 0, 280, 192))          # a white "stone"
    screens.tombstone(ui, "John", "Poor bastard")
    ui.cv.base.paste((255, 255, 255), (0, 0, 280, 192))
    ui.inverse = True
    ui.dfw(56, 62, 150, 45)
    ui.put("Hi")
    im = ui.cv.render()
    assert im.getpixel((57, 63)) == (0, 0, 0)                    # a letter is black on the stone


def test_management_screen_has_the_blue_line(folder):
    ui, _ = make(folder)
    from oregon.data import text as T
    screens.management(ui, T.MANAGE_OPTIONS)
    im = ui.cv.render()
    assert im.getpixel((100, 20)) == (13, 161, 255) or im.getpixel((101, 20)) == (13, 161, 255)


def test_flip_to_side_2_keeps_the_scene_and_puts_it_back(folder):
    ui, _ = make(folder)
    ui.cv.box(0, 121, 279, 180, 5)
    saved = screens.flip_to_side_2(ui)
    assert ui.cv.render().getpixel((100, 150)) == (0, 0, 0)       # strip and panel cleared
    ui.cv.put(saved)
    assert ui.cv.render().getpixel((100, 150)) == (242, 94, 0)


def test_top_ten_and_score_screens_draw(folder):
    ui, _ = make(folder)
    y = screens.top_ten(ui, [("Stephen Meek", 7650, "Trail guide")] * 10)
    assert y == 38 + 90 + 9
    for page in range(3):
        screens.how_points(ui, page, [("good", 500)] * 4 + [("wagon", 50)] * 7)
    ny = screens.win_points(ui, [("   5 people in good health", 2500)] * 8, 2678)
    assert ny > 100


def test_river_crossing_plays_through_the_graphical_interface(folder):
    from oregon import river
    from oregon.__main__ import apply_preset
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import SeededRnd
    from oregon.trace import Tracer

    class Limited(ScriptBackend):
        reads = 0

        def read(self):
            self.reads += 1
            assert self.reads < 60, "the script ran out of keys"
            return super().read()

    # intro, "get more information" (a typed answer ends with Return) and its three pages, then ford
    # (typed, Return) and the result
    b = Limited([" ", "4", "\r", " ", " ", " ", "1", "\r", " "])
    ui = GraphicalUI(Assets(folder), b)
    c = Context(ui=ui, rng=SeededRnd(), files=Files(os.path.join(folder, "data")),
                trace=Tracer(None))
    apply_preset(c)
    c.st.LM = 2
    c.st.NM = 3
    assert river.crossing(c) is True
    assert b.keys == []


def test_hunting_field_is_played_with_the_keys(folder):
    """Return walks, space fires, and the meat comes from the paper's weights."""
    from oregon.graphics import hunt_field
    from oregon.hunt import ANIMALS, HuntRng, allowed_types
    h = HuntRng(bytes([1, 2, 3, 4, 5]))
    ui, _ = make(folder)
    keys = iter(["\r", " ", " ", " ", " ", " ", " "] + [None] * 400000)
    r = hunt_field.play(ui, 5, h.below, h.below, allowed_types(10), ANIMALS, 2500,
                        getkey=lambda: next(keys), pause=0)
    assert 0 <= r["bullets"] <= 5 and r["shots"] <= 4
    if r["shots"] == 0:
        assert r["meat"] == 0


def test_a_day_waits_longer_at_a_steady_pace_than_at_a_grueling_one(folder):
    from oregon import num, trail
    from oregon.__main__ import apply_preset
    from oregon.context import Context
    from oregon.files import Files
    from oregon.rng import SeededRnd
    from oregon.trace import Tracer
    ui, _ = make(folder)
    ui.by_pace = True
    ui.daily_pause = 1.0
    c = Context(ui=ui, rng=SeededRnd(), files=Files(os.path.join(folder, "data")),
                trace=Tracer(None))
    apply_preset(c)
    got = {}
    for p in (1, 2, 3):
        c.st.P = num.parse(str(p))
        got[p] = trail.day_seconds(c)
    assert got == {1: 1.0, 2: 0.5, 3: 0.3}


def test_hunting_scene_runs_from_sprite_data(folder):
    """The sprite-based field needs only the sprite table; shooting never exceeds the bullets."""
    from oregon.graphics import hunt_scene
    from oregon.hunt import ANIMALS, HuntRng, allowed_types
    box = ["##", "##"]
    poses = {p: {"dx": 0, "dy": 0, "rows": box} for p in hunt_scene.POSES}
    data = {"hunter": poses,
            "scenery": [{"kind": "tree", "image": "sq1", "k": 12, "w": 2, "h": 2},
                        {"kind": "grass", "image": "sq1", "k": 13, "w": 2, "h": 2}],
            "animals": {k: {"L": [box], "R": [box]} for k in ("bison", "deer", "squirrel", "rabbit")},
            "lying": {}, "speed": {"bison": 38, "deer": 100, "squirrel": 170, "rabbit": 110}}
    h = HuntRng(bytes([9, 8, 7, 6, 5]))
    ui, _ = make(folder)
    keys = iter([None] * 60 + ["\r"] + [" "] * 5 + [None] * 10 ** 6)
    r = hunt_scene.play(ui, data, 3, h.below, allowed_types(10), ANIMALS, 600,
                        getkey=lambda: next(keys), live=False)
    assert 0 <= r["bullets"] <= 3 and r["shots"] <= 4
    assert all(0 <= x < 280 and 0 <= y < 192 for x, y in ui.cv.dots)


def test_the_raft_is_drawn_and_steered_with_the_arrow_keys(folder):
    from oregon import floatraft
    from oregon.__main__ import apply_preset
    from oregon.context import Context
    from oregon.files import Files
    from oregon.graphics import raft_scene
    from oregon.rng import SeededRnd
    from oregon.trace import Tracer
    for name, size in (("float_raft", (39, 28)), ("float_rock", (29, 10)), ("float_sign", (30, 22))):
        Image.new("RGBA", size, (255, 255, 255, 255)).save(os.path.join(folder, "images", name + ".png"))
    Image.new("RGB", (280, 192), (13, 161, 255)).save(os.path.join(folder, "screens", "b_river.png"))
    ui, b = make(folder)
    assert raft_scene.available(ui)
    seen = []
    keys = iter(["\x1d"] * 3 + [None] * 10 ** 6)
    b.poll = lambda: next(keys)
    b.show = lambda img: seen.append(img)
    c = Context(ui=ui, rng=SeededRnd(), files=Files(os.path.join(folder, "data")), trace=Tracer(None))
    apply_preset(c)
    floatraft.run(c)
    assert len(seen) >= 20                        # a picture a pass
    assert floatraft.LEFT_KEYS and "\x1c" in floatraft.LEFT_KEYS and "\x1d" in floatraft.RIGHT_KEYS


# ------------------------------------------------------------------ a themed assets folder
@pytest.fixture()
def themed(folder):
    """The same small folder with a theme.json: plain text and the theme's own colours."""
    (open(os.path.join(folder, "theme.json"), "w")).write(json.dumps(
        {"plain_text": True, "text_colour": [246, 234, 218],
         "colours": {"3": [250, 240, 220], "1": [10, 120, 10], "4": [20, 10, 30]}}))
    Image.new("RGB", (280, 192), (30, 20, 60)).save(os.path.join(folder, "screens", "backdrop_default.png"))
    Image.new("RGB", (280, 20), (200, 100, 50)).save(os.path.join(folder, "screens", "backdrop_ground_1.png"))
    return folder


def test_a_theme_turns_the_apple_colour_rules_off(themed):
    ui, _ = make(themed)
    cv = ui.cv
    cv.dots.update({(10, 10), (11, 10), (40, 10), (80, 10), (82, 10)})     # beside, lone even, lone, gap of one
    im = cv.render()
    for p in ((10, 10), (11, 10), (40, 10), (80, 10), (82, 10)):
        assert im.getpixel(p) == (246, 234, 218)             # one plain colour: no violet, green or white
    assert im.getpixel((81, 10)) != (246, 234, 218)           # and no filling between two lit dots


def test_a_theme_paints_boxes_and_lines_as_they_are(themed):
    ui, _ = make(themed)
    cv = ui.cv
    cv.box(100, 50, 109, 59, 1)                               # odd columns only in the Apple, all of them here
    assert {cv.base.getpixel((x, 55)) for x in range(100, 110)} == {(10, 120, 10)}
    assert not cv.filled
    cv.line(10, 100, 30, 100, 3)
    assert cv.base.getpixel((20, 100)) == (250, 240, 220)


def test_a_theme_has_a_backdrop_and_ink_that_shows_through_a_panel(themed):
    ui, _ = make(themed)
    cv = ui.cv
    assert cv.base.getpixel((5, 5)) == (30, 20, 60)           # the empty screen is the backdrop
    assert cv.backdrop("ground_1", 0, 60) and cv.base.getpixel((5, 65)) == (200, 100, 50)
    cv.base.paste((9, 9, 9), (0, 120, 100, 140))              # a picture under a white panel
    cv.panel(0, 120, 100, 140)
    cv.glyph("A", 10, 125, inverse=True)
    inked = {cv.base.getpixel(p) for p in ((x, y) for x in range(10, 16) for y in range(125, 134))}
    assert cv.palette[0] in inked                             # the letter is ink, not the picture


def test_a_folder_without_a_theme_keeps_the_apple_colours(folder):
    ui, _ = make(folder)
    ui.cv.dots.update({(10, 10), (40, 10)})
    im = ui.cv.render()
    assert im.getpixel((10, 10)) == (199, 52, 255) and im.getpixel((40, 10)) == (199, 52, 255)
    assert not ui.cv.backdrop("ground_1")


def test_a_theme_paints_coloured_sprites(themed):
    ui, _ = make(themed)
    cv = ui.cv
    cv.paint_rows(["ab.", ".ba"], 20, 30, {"a": (1, 2, 3), "b": (4, 5, 6)})
    assert cv.base.getpixel((20, 30)) == (1, 2, 3) and cv.base.getpixel((21, 30)) == (4, 5, 6)
    assert cv.base.getpixel((22, 30)) != (1, 2, 3)            # '.' stays transparent


def test_the_cursor_blinks_and_is_a_block(folder):
    class Blinker:
        """Gives one blink interval with no key, then the letter, then Return."""
        def __init__(self):
            self.script = ["", "a", "\r"]
            self.frames = []
        def show(self, img):
            self.frames.append(img.copy())
        def read_timeout(self, seconds):
            return self.script.pop(0)
        read = read_timeout
        def flush(self): pass
        def pump(self): pass
        def poll(self): return None
    b = Blinker()
    ui = GraphicalUI(Assets(folder), b)
    ui.dfw(0, 0, 280, 192)
    assert ui.key("", 1) == "a"
    assert len(b.frames) >= 2                                 # drawn again after the blink
    on = [im for im in b.frames if im.getpixel((2, 2)) != (0, 0, 0)]
    off = [im for im in b.frames if im.getpixel((2, 2)) == (0, 0, 0)]
    assert on and off                                         # lit once, dark once


def test_arrival_point_path():
    from oregon.graphics import raft_scene
    assert raft_scene.landing_position(-1) is None
    assert raft_scene.landing_position(0) == (-8, 218)
    assert raft_scene.landing_position(40) == (232, 98)
    assert raft_scene.landing_position(60) is None


def test_sound_tunes_and_switch(tmp_path):
    from oregon.graphics import sound
    assert abs(sound.duration(sound.wait_tune()) - 16.4) < 0.3      # as long as the original's MS0
    assert 0.4 < sound.duration(sound.collision_tune()) < 0.6        # a half-second sound, as in FLOAT
    p = tmp_path / "t.wav"
    sound.write_wav(str(p), sound.collision_tune(1))
    import wave
    with wave.open(str(p)) as w:
        assert (w.getnchannels(), w.getsampwidth()) == (1, 1)
    s = sound.Sound(enabled=lambda: False)
    s.waiting()
    assert s.collision() == 0.0 and s._proc is None            # off means silent
    s.close()


def test_every_tune_file_has_a_tune():
    from oregon.graphics import sound, tunes
    assert set(sound.TUNES) == {f"ms{i}" for i in range(18)} | {"ts"}
    for name, secs in tunes.SECONDS.items():
        melody, bass = tunes.melody_and_bass(name)
        assert sum(n for _, n in melody) == sum(n for _, n in bass)
        assert abs(sound.duration(sound.wait_tune(name=name)) - secs) < 0.3, name
    assert len({str(tunes.melody_and_bass(n)[0]) for n in tunes.names()}) == 19    # all different


def _proportional_space(folder):
    """The same blocks, but a space only 2 wide (as in the themed font), so space padding would drift."""
    p = os.path.join(folder, "font", "font.json")
    j = json.load(open(p))
    j["glyphs"]["32"]["width"] = 2
    json.dump(j, open(p, "w"))


def test_padded_numbers_end_on_the_same_edge_whatever_the_space_width(folder):
    _proportional_space(folder)
    ui, _ = make(folder)
    ui.dfw(0, 0, 280, 192)
    for text in ("5", "50", "500", "5000"):
        ui.cx = 0
        ui.padded(text, 4)
        assert ui.cx == 4 * ui.cell()


def test_trail_colons_line_up_in_one_column(folder):
    _proportional_space(folder)
    ui, _ = make(folder)
    seen = []
    orig = ui.put

    def spy(s):
        if s.endswith(":"):
            seen.append(ui.win[0] + ui.cx + ui.width(s))
        orig(s)
    ui.put = spy
    screens.travel(ui, "prairie", 8, -22, 2, 1, ["Date", "Weather", "Health", "Food",
                                                 "Next landmark", "Miles traveled"],
                   ["a", "b", "c", "d", "e", "f"])
    assert len(seen) == 6 and set(seen) == {screens.COLON_X}
