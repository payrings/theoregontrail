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