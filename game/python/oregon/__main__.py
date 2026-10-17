"""``python -m oregon`` -- play the game.

Fish-syntax examples are in ``README.md``. The options are:

``--seed N``
    seed the random generator with the 16-bit value ``N``, which is what the keyboard
    counter at 78 and 79 holds at ``MENU`` 1015. Any game can be replayed from a seed,
    so this is what a reference trace would be recorded against.

``--num rom|exact|float|rounded``
    which arithmetic backend. The default is the emulated Apple IIe ROM; ``exact``
    is the Python transcription of its routines and gives the same games; the
    other three are the approximate arithmetics of paper sections 12.7 and 12.8.

``--trace FILE``
    write one line per game day in the form Appendix H describes.

``--inputs FILE``
    play from a script: one answer per line, for a whole game.

``--data DIR``
    where to keep ``HISCORE.SEQ`` and ``TOMB.SEQ``.

``--list``
    show the arithmetic backend and the ROM, then stop.
"""

from __future__ import annotations

import argparse
import sys

from . import applesoft
from .context import Context
from .files import Files
from .rng import SeededRnd
from .trace import Tracer
from .ui import AutoUI, ScriptedUI, TerminalUI


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m oregon",
                                description="The Oregon Trail (MECC, 1985)")
    p.add_argument("--seed", type=int, default=None,
                   help="the 16-bit keyboard counter that seeds RND")
    p.add_argument("--num", choices=applesoft.choices(), default=None,
                   help="the arithmetic backend (default: the emulated Apple IIe ROM when it and "
                        "py65 are present, otherwise the Python transcription of its routines)")
    p.add_argument("--trace", default=None, metavar="FILE",
                   help="write one line per game day")
    p.add_argument("--inputs", default=None, metavar="FILE",
                   help="play from a list of answers, one per line")
    p.add_argument("--data", default="data", metavar="DIR",
                   help="where HISCORE.SEQ and TOMB.SEQ are kept")
    p.add_argument("--no-interrupt", action="store_true",
                   help="never break out of the daily cycle")
    p.add_argument("--daily-screen", action="store_true",
                   help="show travel screen each day (press Enter to interrupt)")
    p.add_argument("--preset", action="store_true",
                   help="skip setup with carpenter, April departure, full supplies, $50 left")
    p.add_argument("--demo", action="store_true",
                   help="watch the game play itself, quietly, to the end")
    p.add_argument("--verbose-demo", action="store_true",
                   help="like --demo, but show the screens as well")
    p.add_argument("--wander", action="store_true",
                   help="with --demo: also use the pace and rations screens, rest, trade, talk, "
                        "hunt, shop at forts and raft, so a check reaches code the plain demo never runs")
    p.add_argument("--graphics", action="store_true",
                   help="play in a window drawn like the Apple II screen (needs Pillow "
                        "and the pictures in the assets folder)")
    p.add_argument("--assets", default=None, metavar="DIR",
                   help="the folder of PNG pictures for --graphics (default: assets)")
    p.add_argument("--scale", type=int, default=4,
                   help="size of the --graphics window as a multiple of 280 x 192")
    p.add_argument("--list", action="store_true",
                   help="show the numeric backend and the ROM, then stop")
    return p


def answers_from(path):
    if path is None:
        return None
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        out.append(line if line != "" else "")
    return out


def apply_preset(c):
    """Apply the carpenter preset: skip all menus, set up game state directly.

    It ends by loading the trail state, and ``main`` loads it again, so the opening
    draws of lines 29000 and 29004 are made twice and the journey starts two draws
    further along the sequence than the original would after the same reseeding.
    Every result in the paper was recorded this way (paper 12.7, Appendix H), so it
    is kept; a trace from the original must make the same two extra draws.
    """
    from . import num
    st = c.st

    # Set year to 1848
    c.mem.poke(901, 48, 9000)

    # Profession: carpenter (2) = $800
    c.mem.poke(915, 2, 4030)
    c.mem.poke_word(913, 800 * 10, 4030)
    st.MY = num.parse("800")
    for i in range(5):
        st.N[i] = ["Zeke", "Jed", "Anna", "Mary", "Joey"][i]
    st.NP = 5
    # MENU 6045 hands the names over in memory; load_state reads them back from there
    c.mem.put_names(["Zeke", "Jed", "Anna", "Mary", "Joey"])

    # Departure month: April (4)
    c.mem.poke(902, 4, 6030)
    c.mem.poke(903, 1, 6000)
    st.AM = num.parse("4")
    st.AD = num.parse("1")
    st.AY = num.parse("1848")

    # Supplies - write directly to hand-over memory (addresses 905-912)
    # 905: yokes of oxen
    c.mem.poke(905, 9, 405)
    # 906,907: food (low/high byte)
    c.mem.poke_word(906, 2000, 530)   # the store limit; 500 starves by mid-May
    # 908: sets of clothing
    c.mem.poke(908, 10, 610)
    # 909: boxes of bullets
    c.mem.poke(909, 50, 700)
    # 910: wagon wheels
    c.mem.poke(910, 3, 811)
    # 911: wagon axles
    c.mem.poke(911, 3, 811)
    # 912: wagon tongues
    c.mem.poke(912, 3, 811)

    # The preset is one fixed starting position, not a purchase the store allows: at
    # Independence prices these goods cost $360 (18 oxen) + $400 (food) + $100
    # (clothing) + $100 (ammunition) + $90 (spare parts) = $1,050, against a
    # carpenter's $800. The party starts with $50 in hand.
    c.mem.poke_word(913, 50 * 10, 5010)

    # Now load the journey state from hand-over (skip store entirely)
    from . import trail
    trail.load_state(c)

    print("Well then, you're ready to start.  Good luck!  You have a long and "
          "difficult journey ahead of you.")


def summary(c, ui, where) -> str:
    """The state at the end of a self-played game, as one line of JSON.

    For the scripts that play many games and compare them. Nothing in the game
    reads it.
    """
    import json
    from . import num
    from .data import illnesses as ILL, landmarks as L, text as T
    st = c.st
    alive = max(0, num.as_int(st.NP))
    said = ui.out
    members = []
    for i in range(5):
        if i >= alive:
            members.append("dead")
        else:
            h1 = num.as_int(st.H1[i])
            members.append(ILL.IL_NAMES[h1] if 0 < h1 < len(ILL.IL_NAMES) else "healthy")
    outcome = (c.outcome or "").split()
    arrived = bool(outcome) and outcome[0] == "ARRIVED"
    health = num.as_float(st.H)
    lm = int(st.LM)
    return json.dumps({
        "ending": "ARRIVED" if arrived else ("DIED" if alive <= 0 else "UNFINISHED"),
        "route_end": where,
        "score": int(outcome[1]) if arrived else 0,
        "rating": " ".join(outcome[2:]) if arrived else "",
        "days": c.trace.days,
        "end_day": num.as_int(st.AD), "end_month": num.as_int(st.AM),
        "end_year": num.as_int(st.AY),
        "miles": round(num.as_float(st.M), 4),
        "last_landmark": lm,
        "last_landmark_name": L.LM_NAMES[lm] if 0 <= lm < len(L.LM_NAMES) else "",
        "survivors": alive,
        "health": round(health, 6),
        "health_class": T.HEALTH[min(3, max(0, int(health // 35)))] if alive else "",
        "members": members,
        "sick_at_end": sum(1 for m in members if m not in ("dead", "healthy")),
        "illnesses_during_game": sum(
            1 for line in said
            if any(line.rstrip().endswith(" has " + n + ".") for n in ILL.IL_NAMES)),
        "oxen": round(num.as_float(st.I[2]), 4),
        "clothing": round(num.as_float(st.I[3]), 4),
        "bullets": round(num.as_float(st.I[4]), 4),
        "wheels": num.as_int(st.I[5]), "axles": num.as_int(st.I[6]),
        "tongues": num.as_int(st.I[7]),
        "food": round(num.as_float(st.I[8]), 4),
        "money": round(num.as_float(st.MY), 4),
    })


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    # no --num: keep what importing the package chose (the ROM if it can run, else `exact`)
    backend = applesoft.use(args.num) if args.num else applesoft.current()
    if args.list:
        print(f"arithmetic backend : {backend.name}")
        print(f"Apple IIe ROM      : {applesoft.rom_status()}")
        return 0
    if args.demo or args.verbose_demo:
        ui = AutoUI(quiet=not args.verbose_demo, wander=args.wander)
    elif args.inputs:
        ui = ScriptedUI(answers_from(args.inputs))
    elif args.graphics:
        from .graphics import AssetError, make_ui
        try:
            ui = make_ui(args.assets, args.scale, show_daily=True)
        except (AssetError, ImportError) as e:
            print(f"--graphics: {e}", file=sys.stderr)
            return 2
    else:
        ui = TerminalUI(interrupt=not args.no_interrupt, show_daily=args.daily_screen)
    rng = SeededRnd()
    tracer = Tracer(args.trace)
    # a person at the keyboard goes back to the menu when a journey ends (MENU SIDE 2, line
    # 31000); a script, a demo or a preset plays one game and stops, as the tests expect
    again = not (args.demo or args.verbose_demo or args.inputs or args.preset)
    first = True
    sound_flag = 1
    try:
        while True:
            c = None
            c = Context(ui=ui, rng=rng, files=Files(args.data), trace=tracer)
            if args.seed is not None and first:
                rng.seed_from_keyboard(args.seed)
                # the menu reseeds from the keyboard counter (MENU 1015), which a script
                # never advances; holding it at the seed makes that reseed the same seed
                c.mem.keyboard_counter = args.seed
            from . import buysupplies, menu, trail, win
            if hasattr(ui, "sound"):               # memory byte 975 is the sound switch (MENU 130)
                c.mem.poke(975, sound_flag)        # on the first time, then as the player left it
                ui.sound.enabled = lambda c=c: bool(c.mem.peek(975))
                ui.sound.toggle = lambda c=c: c.mem.poke(975, 0 if c.mem.peek(975) else 1)
            try:
                if args.preset:
                    apply_preset(c)
                else:
                    # the order is the original's: MENU fixes the year and takes the
                    # profession and the names, then BUY SUPPLIES asks the month and sells,
                    # then OREGON TRAIL reads the hand-over back out of memory and travels
                    menu.main_menu(c)
                    buysupplies.departure_month(c)
                    buysupplies.init_state(c)
                    buysupplies.store(c)
                trail.load_state(c)
                where = trail.run(c)
                if where in ("WIN", "FLOAT"):
                    # END.LIB 50050 has already written the hand-over, whichever way the
                    # party arrived -- by the Barlow Road or down the Columbia
                    win.run(c)
                if args.demo or args.verbose_demo:
                    # one line a script can read: how the game ended, and the last return
                    print(f"ENDING {c.outcome or 'NONE'} [{where}]", file=sys.stderr)
                    print("SUMMARY " + summary(c, ui, where), file=sys.stderr)
            except KeyboardInterrupt:
                print()
                print("Broken.")
                again = False
            except Exception as err:                   # noqa: BLE001
                # ONERR GOTO 32000 in every program: an Applesoft error is a defined
                # outcome -- the message, a key, and back to the menu (COMMON.LIB 32120)
                from .applesoft.rom import RomError
                from .errors import ApplesoftError, handle
                if isinstance(err, RomError):
                    # the rebuild does not track BASIC line numbers, so an error raised by
                    # the arithmetic is reported with line 0 (game/NOTES.md, section 2)
                    code = getattr(err, "code", 69)         # 69: OVERFLOW
                    err = ApplesoftError(code, 0, getattr(c, "program", "") or "", str(err))
                if not isinstance(err, ApplesoftError):
                    raise
                handle(ui, err, getattr(c, "program", None))
                c.outcome = f"ERROR {err.code}"
                if args.demo or args.verbose_demo:
                    print(f"ENDING {c.outcome} [MENU]", file=sys.stderr)
                    print("SUMMARY " + summary(c, ui, "MENU"), file=sys.stderr)
            if hasattr(ui, "sound"):
                sound_flag = c.mem.peek(975)
            if again:
                from . import flip
                flip.back_to_menu(c)               # 31000: side 1 again if side 2 is in, then the menu
            first = False
            if not again:
                break
    finally:
        tracer.close()
        if hasattr(ui, "sound"):
            ui.sound.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
