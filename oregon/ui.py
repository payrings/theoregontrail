"""Screen output and keyboard input, behind one interface.

This module plays the part of the ``&`` command package (Appendix F): the game asks
for text, a position, a clear or a line of input, and never touches the terminal
itself. Game logic must not call ``print`` or ``input``.

Two implementations are provided. :class:`TerminalUI` is the one a player sees.
:class:`ScriptedUI` replays a list of answers, so a whole game can be played from a
script -- which is how the tests reach each ending without a human.

The methods correspond to the ``&`` commands the BASIC calls:

===============================  ==========================================
method                           the ``&`` command it stands in for
===============================  ==========================================
``print``                        ``PRINT``
``clear``                        ``PRINT CL$`` (chr$(12))
``at``                           ``& CO,x,y``
``line_to``                      ``& CEL``
``space``                        ``& SPACE,n``
``window``, ``wind``, ``box``    ``& DFW``, ``& WIND``, ``& BOX``
``indent``                       ``& IN,n``
``key``                          ``& INP,1,"-AZ-az '.-",1,Z$``
``wait_key``                     ``& INP,1,allowed,0,Z$`` -- waits for Return
``poll_key``                     ``USR (3)`` -- a key with no wait (line 800)
``putc``                         the five control characters ``D$``..``CF$``
===============================  ==========================================

Graphics-only commands (``& IMAGE``, ``& PUT``, ``& TAKE``, ``& UIM``, ``& DUN``)
have no meaning in a terminal and are recorded in ``GAPS.md`` as deliberately
replaced; the map and the travel screen are drawn as text instead.
"""

from __future__ import annotations

import copy
import sys

__all__ = ["UI", "TerminalUI", "ScriptedUI", "RETURN"]

RETURN = "\r"
END = "\n"

# The five control characters COMMON.LIB 40005 puts in variables.
CTRL = {"D$": "\x04", "CC$": "\x03", "CL$": "\x0c", "CM$": "\x0d",
        "CE$": "\x05", "CF$": "\x06"}

# The allowed-character sets the BASIC passes to ``& INP``.
ALLOWED = {
    "YN": "YESNOyesno",
    "NAMES": "-AZ-az '.-",
    "TOPTEN": "-AZ-az .'-",
    "EPITAPH": "-09-AZ-az ,.'-",
    "DIGITS09": "-09",
    "DIGITS19": "-19",
    "CHOICE": "-14",
    "PROFESSION": "-14",
    "MONTH": "-16",
    "MANAGE": "-15",
    "FORT": "-18",
    "SEGMENT": "-13",
    "RATION": "-13",
    "PACE": "-14",
    "REST": "-09",
    "STORE_FOOD": "-09",
    "STORE_CLOTHES": "-09",
    "STORE_AMMO": "-09",
    "STORE_PART": "-09",
    "STORE_YOKE": "-19",
    "DALLES": "-12",
    "RIVER_KC": "-14",       # the river menus are five long
    "RIVER_SNAKE": "-15",
    "RIVER_BB": "-14",
}


class UI:
    """What the game is allowed to ask of the screen and the keyboard."""

    def __init__(self):
        self.typing = False          # set while reading a line, for the arrow keys
        self.out = []                # everything printed, for the tests

    # ------------------------------------------------------------- output
    def print(self, text: str = ""):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def at(self, x: int, y: int):
        """``& CO,x,y``. In a terminal this is a no-op; the column is advisory."""

    def line_to(self):
        """``& CEL``: clear from the cursor to the end of the line."""

    def space(self, n: int):
        self.print(" " * n)

    def window(self, *args):
        """``& DFW``: a graphics window. Nothing to do in a terminal."""

    def wind(self, n: int = 0):
        """``& WIND``: select an output window. Nothing to do in a terminal."""

    def box(self, *args):
        """``& BOX``: draw a rectangle. Drawn in text by the screens that use it."""

    def indent(self, n: int):
        """``& IN,n``: the left margin for wrapped text."""

    def wait_key(self, allowed: str = "", prompt: str = "Press SPACE BAR to continue"):
        """Line 950: wait for a key, allowing Control-S to toggle the sound."""
        raise NotImplementedError

    # -------------------------------------------------------------- input
    def key(self, allowed: str = "", maxlen: int = 1, default: str = "") -> str:
        """``& INP,length,allowed,flag,Z$``: a line of at most *maxlen* characters,
        keeping only those in *allowed*. Return is always accepted."""
        raise NotImplementedError

    def yes_no(self, prompt: str = "") -> str:
        """COMMON.LIB 30120: ``& INP,3,"YESNOyesno",1,Z$``; returns ``"Y"``/``"N"``."""
        if prompt:
            self.print(prompt)
        for _ in range(64):
            z = self.key(ALLOWED["YN"], 3)
            if z:
                return z[0].upper()
        return "N"

    def poll_key(self) -> str | None:
        """``USR (3)`` at line 800: a key if one is waiting, else None.

        This is the travel interrupt: the player presses Return to stop and open
        the action menu. No wait, so the daily cycle is never held up.
        """
        return None

    def flip_disk(self, side: int, title: str = "OREGON TRAIL") -> str:
        """``& SET`` / the prompts at COMMON.LIB 33015 and FLIP.LIB 50005.

        The original checks the disk volume name before reading or writing a data
        file. There is no disk here, so this asks for the side and returns it.
        """
        raise NotImplementedError


class TerminalUI(UI):
    """The plain terminal implementation.

    The interesting part is :meth:`poll_key`, which has to be genuinely
    non-blocking for the travel interrupt to work as it does in the original: the
    cycle runs on and a keypress stops it. On a POSIX terminal the line is put into
    cbreak mode so a single keypress is available without Return. When the input
    is not a terminal -- a pipe, a test run -- ``poll_key`` always returns None,
    which means travel is never interrupted, and that is the sensible reading.
    """

    def __init__(self, echo: bool = True, interrupt: bool = True):
        super().__init__()
        self.echo = echo
        self.interrupt = interrupt
        self._saved = None
        self._pending = []

    # ---------------------------------------------------------- raw input
    def _enter_raw(self):
        if self._saved is not None or not sys.stdin.isatty():
            return
        try:
            import termios
            import tty
        except ImportError:                       # pragma: no cover - not POSIX
            return
        self._saved = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())

    def _leave_raw(self):
        if self._saved is None:
            return
        try:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._saved)
        except Exception:                          # noqa: BLE001
            pass
        self._saved = None

    def _at_eof(self) -> bool:
        """Whether stdin has run out, so a prompt cannot loop for ever."""
        import sys as _sys
        try:
            return not _sys.stdin.isatty() and _sys.stdin.read() == ""
        except Exception:                          # noqa: BLE001
            return False

    def _read_char(self):
        """One character, without waiting for a newline, or None."""
        self._enter_raw()
        try:
            ch = sys.stdin.read(1)
        finally:
            self._leave_raw()
        return ch or None

    def poll_key(self):
        if not self.interrupt:
            return None
        if self._pending:
            return self._pending.pop(0)
        try:
            import select
            if not select.select([sys.stdin], [], [], 0)[0]:
                return None
        except Exception:                          # noqa: BLE001
            return None
        ch = self._read_char()
        return ch

    def wait_key(self, allowed: str = "", prompt: str = "Press SPACE BAR to continue"):
        self.print(prompt)
        while True:
            ch = self._read_char()
            if ch is None:
                if self._at_eof():
                    return ""
                continue
            if ch in ("\x1b",):
                self._read_char()                  # swallow the rest of an escape
                continue
            return ch

    def key(self, allowed: str = "", maxlen: int = 1, default: str = "") -> str:
        got = []
        allowed_set = set(allowed) | {"\r", "\n"}
        while len(got) < maxlen:
            ch = self._read_char()
            if ch is None:
                if self._at_eof():
                    # stdin is exhausted: a prompt with no answer would spin for
                    # ever, so stop the game cleanly instead
                    raise SystemExit("input ended while waiting for an answer")
                continue
            if ch in ("\x1b",):
                self._read_char()
                continue
            if ch in ("\x7f", "\b"):
                if got:
                    got.pop()
                    self._echo_line(got)
                continue
            if ch in ("\r", "\n"):
                break
            if ch in allowed_set or not allowed:
                got.append(ch)
                self._echo_line(got)
        return "".join(got)

    def _echo_line(self, got):
        if self.echo:
            sys.stdout.write("\r" + " " * 40 + "\r")
            sys.stdout.write("".join(got))
            sys.stdout.flush()

    # ------------------------------------------------------------- output
    def print(self, text: str = ""):
        self.out.append(text)
        sys.stdout.write(text + END)
        sys.stdout.flush()

    def clear(self):
        self.out.append("<clear>")
        sys.stdout.write("\x0c")
        sys.stdout.flush()

    def flip_disk(self, side: int, title: str = "OREGON TRAIL") -> str:
        other = 2 if side == 1 else 1
        self.print(f"Please insert side {other} of the {title} diskette.")
        self.print("Press SPACE BAR to continue")
        self.wait_key()
        return str(other)


class ScriptedUI(UI):
    """Replays a list of answers, so a whole game can be played from a script.

    Answers are taken in order. An answer may be a string, or an integer for a
    numeric prompt. When the list runs out the UI keeps returning the last
    answer's default rather than raising, because a game that asks one question
    more than expected should still be visible -- the test asserts the position in
    the list instead, and :attr:`position` records how far it got.
    """

    def __init__(self, answers=None, record=None, allow_repeat: bool = False,
                 max_prompts: int = 20000):
        super().__init__()
        self.max_prompts = max_prompts
        self.prompts = 0
        self.answers = list(answers or [])
        self.i = 0
        self.record = record if record is not None else []
        self.position = 0
        self.exhausted = False
        self.allow_repeat = allow_repeat
        self.keys = []                    # key presses waiting, for the interrupt

    def _next(self, default=""):
        """The next answer.


        Running off the end is an **error**, not a repeat: a game that asks one
        question more than its script expected is a bug in the transcription or in
        the script, and hanging or silently repeating would hide it. Pass
        ``allow_repeat=True`` for a script that deliberately loops.
        """
        self.prompts += 1
        if self.prompts > self.max_prompts:
            raise AssertionError(
                f"ScriptedUI asked for {self.prompts} answers, more than the "
                f"max_prompts of {self.max_prompts}: the game is looping")
        if self.i < len(self.answers):
            a = self.answers[self.i]
            self.i += 1
            self.position = self.i
            return default if a is None else a
        self.exhausted = True
        self.position = self.i
        if self.allow_repeat:
            # repeat the last answer, so a prompt that is asked more than the
            # script expected gets a sensible reply instead of nothing
            if not default and self.answers:
                return self.answers[-1]
            return default
        raise AssertionError(
            f"ScriptedUI ran out of answers after {self.i}; the game asked for "
            f"more input than the script supplies")

    # ------------------------------------------------------------- output
    def print(self, text: str = ""):
        self.out.append(text)

    def clear(self):
        self.out.append("<clear>")

    def line_to(self):
        pass

    # -------------------------------------------------------------- input
    def key(self, allowed: str = "", maxlen: int = 1, default: str = "") -> str:
        a = self._next(default)
        self.record.append(("key", a))
        return str(a)[:maxlen] if maxlen else str(a)

    def wait_key(self, allowed: str = "", prompt: str = "Press SPACE BAR to continue"):
        """A keypress the script does not have to supply.

        A bare ``& SPACE``-style key press is not an answer the game reads back, so
        a scripted run does not have to list one for every "Press SPACE BAR". Push a
        character onto :attr:`keys` when a test *does* want to control one, as the
        travel interrupt does.
        """
        if self.keys:
            return self.keys.pop(0)
        self.record.append(("wait_key", " "))
        return " "

    def poll_key(self):
        if self.keys:
            return self.keys.pop(0)
        return None

    def flip_disk(self, side: int, title: str = "OREGON TRAIL") -> str:
        self.record.append(("flip", side))
        return str(2 - side) if side in (1, 2) else str(side)

class AutoUI(UI):
    """Plays the game by itself, so it can be watched rather than played.

    Not a game feature -- the original has nothing like it. It answers each prompt
    with a sensible default, which is enough to watch a whole crossing from
    Independence to the Willamette Valley: it takes the shops, fords what can be
    forded, takes the ferry and the guide where it cannot, continues from the
    action menu, and pays the Barlow toll. ``--demo`` uses it.

    A prompt it does not recognise is answered with a bare Return, which the game
    treats as "no" or as choice 1, so it cannot spin.
    """

    #: The first rule that matches wins, and each is the text that was printed
    #: plus the answer. Sequences are consumed one entry per time that prompt is
    #: asked, so the store's item and quantity questions can be interleaved
    #: correctly: the item menu is 1 to 5 then Return to leave, and the quantity
    #: prompts are yoke, food, clothing, ammunition, then the three spare parts.
    RULES = (
        ("first name of the wagon leader", "Zeke"),
        ("Are these names correct", "Y"),
        ("Ask for advice", "3"),                 # leave in April
        ("Which item would you like to buy?", ["1", "2", "3", "4", "5", ""]),
        ("want?", ["4", "1000", "6", "6"]),      # yoke, food, clothes, ammo
        ("How many wagon", ["1", "1", "1"]),      # wheel, axle, tongue
        ("Would you like to look around?", "N"),
        ("River depth:", ["1", "1", "3", "3"]),
        ("Are you willing to do this?", "Y"),
        ("Will you accept this offer?", "Y"),
        ("The trail divides here", ["1", "1"]),
        ("float down the Columbia River", "2"),
        ("to travel the Barlow road", "Y"),
        # These three come before "Continue on trail", which is on every action
        # menu and would otherwise take the answer before they can.
        #   * "You must trade for ..." is what line 4070 says when the wagon
        #     cannot move. Line 4070 refuses choice 1 outright, and line 4090
        #     consumes a spare part only when some *other* option is taken, so the
        #     answer is "check supplies" -- which is how the original gets unstuck.
        ("You must trade for", "2"),
        ("another emigrant", ["Y"] * 40),
        ("Broken wagon", "Y"),
        ("Continue on trail", "1"),
        ("What is your choice?", "1"),
    )

    def __init__(self, quiet: bool = True, max_prompts: int = 4000, **kw):
        super().__init__()
        self.quiet = quiet
        self.max_prompts = max_prompts
        self.rules = copy.deepcopy(list(self.RULES))
        self._since = 0
        self.prompts = 0
        self.log = []

    #: how many printed lines back to look for a rule. Wide, because the action
    #: menu redraws the whole screen around a message, which pushes the message
    #: itself out of range.
    LOOKBACK = 24

    def _ask(self) -> str:
        recent = "\n".join(self.out[self._since:])
        for needle, answer in self.rules:
            if needle in recent:
                if isinstance(answer, (list, tuple)):
                    if answer:
                        return str(answer.pop(0))
                    continue
                return str(answer)
        return ""

    def print(self, text: str = ""):
        self.out.append(text)
        if not self.quiet:
            import sys
            sys.stdout.write(text + "\n")
            sys.stdout.flush()

    def clear(self):
        self.out.append("<clear>")
        if not self.quiet:
            import sys
            sys.stdout.write("\x0c")
            sys.stdout.flush()

    def line_to(self):
        pass

    def key(self, allowed: str = "", maxlen: int = 1, default: str = "") -> str:
        ask = self.out[-1].strip()[-60:] if self.out else ""
        a = self._ask()
        self._since = len(self.out)
        self.prompts += 1
        if self.prompts > self.max_prompts:
            raise SystemExit(
                f"the demo asked {self.prompts} questions and gave up; the last "
                f"was {ask!r} answered {a!r}. The party is probably stuck.")
        self.log.append((ask, a))
        return a[:maxlen] if maxlen else a

    def wait_key(self, allowed: str = "", prompt: str = "Press SPACE BAR to continue"):
        return " "

    def poll_key(self):
        return None

    def flip_disk(self, side: int, title: str = "OREGON TRAIL") -> str:
        return str(2 - side) if side in (1, 2) else str(side)

    def progress(self):
        """A one-line report of how the crossing is going."""
        st = self.out
        return len(self.log), len(st)
