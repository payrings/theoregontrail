"""``python -m oregon`` -- play the game.

Fish-syntax examples are in ``README.md``. The options are:

``--seed N``
    seed the random generator with the 16-bit value ``N``, which is what the keyboard
    counter at 78 and 79 holds at ``MENU`` 1015. Any game can be replayed from a seed,
    so this is what a reference trace would be recorded against.

``--num rom|pure``
    which arithmetic backend. The default is the emulated Apple IIe ROM.

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
    p.add_argument("--num", choices=applesoft.choices(), default="rom",
                   help="the arithmetic backend (default: the emulated Apple IIe ROM)")
    p.add_argument("--trace", default=None, metavar="FILE",
                   help="write one line per game day")
    p.add_argument("--inputs", default=None, metavar="FILE",
                   help="play from a list of answers, one per line")
    p.add_argument("--data", default="data", metavar="DIR",
                   help="where HISCORE.SEQ and TOMB.SEQ are kept")
    p.add_argument("--no-interrupt", action="store_true",
                   help="never break out of the daily cycle")
    p.add_argument("--demo", action="store_true",
                   help="watch the game play itself, quietly, to the end")
    p.add_argument("--verbose-demo", action="store_true",
                   help="like --demo, but show the screens as well")
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


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    backend = applesoft.use(args.num)
    if args.list:
        print(f"arithmetic backend : {backend.name}")
        print(f"Apple IIe ROM      : {applesoft.rom_status()}")
        return 0
    if args.demo or args.verbose_demo:
        ui = AutoUI(quiet=not args.verbose_demo)
    elif args.inputs:
        ui = ScriptedUI(answers_from(args.inputs))
    else:
        ui = TerminalUI(interrupt=not args.no_interrupt)
    rng = SeededRnd()
    tracer = Tracer(args.trace)
    c = Context(ui=ui, rng=rng, files=Files(args.data), trace=tracer)
    if args.seed is not None:
        rng.seed_from_keyboard(args.seed)
    from . import buysupplies, menu, trail, win
    try:
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
    except KeyboardInterrupt:
        print()
        print("Broken.")
    finally:
        tracer.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
