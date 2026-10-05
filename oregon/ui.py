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

import atexit
import copy
import os
import sys

__all__ = ["UI", "TerminalUI", "ScriptedUI", "AutoUI", "RETURN",
           "ALLOWED", "allowed_chars"]

RETURN = "\r"
END = "\n"

# The five control characters COMMON.LIB 40005 puts in variables.
CTRL = {"D$": "\x04", "CC$": "\x03", "CL$": "\x0c", "CM$": "\x0d",
        "CE$": "\x05", "CF$": "\x06"}

# The allowed-character sets the BASIC passes to ``& INP``. A prompt filters on
# them: a character outside the set is ignored and the prompt waits for another,
# as the original's routine does. For a menu the set is ``-`` plus the digits of
# the choices on offer, so a prompt offering four choices must allow 1 to 4.
# Getting that wrong makes a choice unreachable and is invisible until someone
# tries it, so tests/test_ui.py checks every set against the choices its screen
# prints. PACE is the one genuinely non-consecutive set: 1 to 3 change the pace
# and 4 explains them, so "-14" is right.
# The allowed-character sets the BASIC passes to ``& INP``, exactly as the
# listings print them.
#
# A set is **characters and inclusive ranges**: ``-`` pairs the characters either
# side of it. So ``"-AZ-az '.-"``, which MENU 500 passes for a name, is A to Z, a to
# z, a space, an apostrophe and a period -- every letter, not the four letters it
# looks like if you read it as a literal list. Reading it literally is what made
# the name prompt accept ``a`` and nothing else worth typing.
#
# The same reading fixes every menu. ``"-14"`` -- the main menu and the profession
# screen -- is 1 to 4, so all four choices are reachable; ``"-16"`` is the six
# month options; ``"-18"`` is the fort shop's eight. That is why they are written
# the way they are, and it is why Appendix X's ``CHR$(1) + "-14"`` needs no
# correction at all.
ALLOWED = {
    # answers that are words rather than menu choices
    "YN": "YESNOyesno",                 # COMMON.LIB 30120
    "NAMES": "-AZ-az '.-",               # MENU 500: a name, at most nine of them
    "TOPTEN": "-AZ-az .'-",              # WIN 530: the name that goes on the list
    "EPITAPH": "-09-AZ-az ,.'-",        # TOMB.LIB 50020: up to twenty-nine
    # numbers
    "DIGITS09": "-09",
    "DIGITS19": "-19",
    # menus
    "CHOICE": "\x011234",               # main menu 1015: Control-A, then 1 to 4
    "PROFESSION": "-1234",               # MENU 4025
    "MANAGE": "-15",                     # MANAGEMENT 1015, five options
    "MONTH": "-16",                      # BUY SUPPLIES 6020, six options
    "PACE": "-14",                       # PACE.LIB: 1 to 3 set a pace, 4 explains
    "RATION": "-13",                     # RATION.LIB: three settings
    "SEGMENT": "-13",                    # OREGON TRAIL 2120: two ways on, plus map
    "DALLES": "-12",                     # END.LIB 50010
    # line 50015 builds this one at run time: Z$ = "-1" + STR$(Z), so a
    # five-choice menu asks for "-15"
    "RIVER": "-15",                      # RIVER.LIB: five choices
    "FORT": "-18",                       # BUY.LIB: the seven goods, then leave
    "REST": "-09",                       # one digit: how many days to rest
    # the store asks quantities
    # line 250 accepts 1 to 5 and nothing else: "ON (Z < 49 OR Z > 53) AND
    # Z <> 32 GOTO 252". Spelled as the game spells a range.
    "STORE_ITEM": "-15",
    "STORE_YOKE": "-19",                 # 1 to 9 yoke
    "STORE_FOOD": "-09",                 # up to four digits
    "STORE_CLOTHES": "-09",              # two digits
    "STORE_AMMO": "-09",                 # two digits
    "STORE_PART": "-09",                 # one digit, 0 to 3
}


def allowed_chars(spec: str) -> set:
    """The characters an ``& INP`` set permits.

    Read the way the original's routine reads it: two characters either side of a
    ``-`` are an inclusive range, and anything else stands for itself. So
    ``"-AZ-az '.-"`` gives every letter plus space, apostrophe and period, and
    ``"-14"`` gives 1 to 4.

    Note the shape of it: a range is written dash-first, so 1 to 5 is ``"-15"`` and
    not ``"1-5"``. Every set in the game is written that way.

    This is the single rule behind several bugs: read as a literal set, a name
    prompt allows only ``A``, ``Z``, ``a`` and ``z``, and a four-choice menu allows
    only 1 and 4.
    """
    out = set()
    i = 0
    n = len(spec)
    while i < n:
        if spec[i] == "-" and i + 2 < n:
            lo, hi = ord(spec[i + 1]), ord(spec[i + 2])
            if lo > hi:
                lo, hi = hi, lo
            out.update(chr(c) for c in range(lo, hi + 1))
            i += 3
        else:
            out.add(spec[i])
            i += 1
    return out


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

    def flush(self):
        """``USR (1)``: throw away anything already typed.

        Not a wait. Line 3030 of the store prints "Press SPACE BAR to leave store"
        and then does ``Z = USR (1)``, which clears the keyboard so a keypress left
        over from the previous screen cannot answer the question that follows.
        Treating that as a wait makes the store ask for a key that was never
        asked for.
        """

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

    Reading is done with :func:`os.read` on file descriptor 0 rather than
    ``sys.stdin.read``, for two reasons that showed up as an unresponsive
    keyboard:

    * ``sys.stdin`` is a buffered text stream. A character read through it can be
      held in Python's buffer rather than consumed from the terminal, so the next
      prompt sees nothing and the keypress appears to be lost.
    * Most prompts take a **single** character -- line 1015's menu, the action
      menu, the river menu. After reading that one character the Return the player
      pressed is still sitting in the line discipline buffer, and the *next* prompt
      consumes it instead of waiting. Every answer then lands one prompt late,
      which feels exactly like the keyboard being ignored.

    So the terminal is put into cbreak mode once, characters are taken straight
    from the descriptor, and after a single-character answer anything else already
    typed is drained. ``poll_key`` stays non-blocking, which is what the travel
    interrupt needs: the day runs on until a key arrives.

    When the input is not a terminal -- a pipe, a test -- cbreak is skipped and
    ``poll_key`` always returns None, so travel is never interrupted.
    """

    def __init__(self, echo: bool = True, interrupt: bool = True):
        super().__init__()
        self.echo = echo
        self.interrupt = interrupt
        self._saved = None
        self._raw_on = False
        self._eof = False
        self._pending = []
        atexit.register(self.close)

    # ------------------------------------------------------------ raw input
    @property
    def _is_tty(self) -> bool:
        try:
            return sys.stdin.isatty()
        except Exception:                          # noqa: BLE001
            return False

    def _ensure_raw(self):
        """Put the terminal into cbreak mode, once, and remember the old settings.

        Deliberately **not** ``tty.setcbreak``: that uses ``TCSAFLUSH``, which
        throws away anything already typed. Entering the mode then discards a
        keystroke that arrived while the game was drawing -- which is the whole
        "the keyboard is unresponsive" complaint, and it is intermittent because
        it depends on whether the key was pressed before or after this ran.

        So the mode is built here and set with ``TCSANOW``, which leaves pending
        input alone. A keystroke typed early is simply read by the next prompt,
        exactly as a canonical terminal would.
        """
        if self._raw_on or not self._is_tty:
            return
        try:
            import termios
            fd = sys.stdin.fileno()
            attrs = termios.tcgetattr(fd)
            self._saved = attrs[:]
            new = attrs[:]
            # no echo (we echo ourselves), no line buffering: a keypress arrives at
            # once, without waiting for Return
            new[3] &= ~(termios.ECHO | termios.ICANON)
            new[6][termios.VMIN] = 1
            new[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSANOW, new)
        except Exception:                          # noqa: BLE001
            self._saved = None
            return
        self._raw_on = True

    def close(self):
        """Put the terminal back the way it was found."""
        if not self._raw_on or self._saved is None:
            self._raw_on = False
            return
        try:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._saved)
        except Exception:                          # noqa: BLE001
            pass
        self._saved = None
        self._raw_on = False

    def _read_char(self):
        """One character straight from the descriptor, or None at end of input."""
        if self._pending:
            return self._pending.pop(0)
        self._ensure_raw()
        try:
            import os
            data = os.read(0, 1)
        except Exception:                          # noqa: BLE001
            self._eof = True
            return None
        if not data:
            self._eof = True
            return None
        return data.decode("latin-1")

    def flush(self):
        """``USR (1)``: discard pending input without waiting."""
        self._drain()

    def _drain(self):
        """Throw away anything else already typed, without waiting.

        Called after a single-character answer so the Return that ended it cannot
        be taken as the answer to the next prompt.
        """
        try:
            import os
            import select
            while select.select([0], [], [], 0)[0]:
                if not os.read(0, 256):
                    self._eof = True
                    return
        except Exception:                          # noqa: BLE001
            pass

    def poll_key(self):
        """``USR (3)``: a key if one is waiting, else None. Never blocks."""
        if not self.interrupt or self._eof:
            return None
        if self._pending:
            return self._pending.pop(0)
        try:
            import select
            if not select.select([0], [], [], 0)[0]:
                return None
        except Exception:                          # noqa: BLE001
            return None
        return self._read_char()

    def wait_key(self, allowed: str = "", prompt: str = "Press SPACE BAR to continue"):
        """Line 950: prompt, then wait for any key."""
        self.print(prompt)
        while True:
            ch = self._read_char()
            if ch is None:
                if self._eof:
                    return ""
                continue
            if ch == "\x1b":                      # swallow an escape sequence
                self._drain()
                continue
            self._echo(ch)
            return ch

    def _debug(self, text):
        """Append to ``$OREGON_DEBUG_INPUT`` when it is set. For chasing input."""
        path = os.environ.get("OREGON_DEBUG_INPUT")
        if not path:
            return
        try:
            with open(path, "a") as fh:
                fh.write(text + "\n")
        except Exception:                          # noqa: BLE001
            pass

    def key(self, allowed: str = "", maxlen: int = 1, default: str = "") -> str:
        """``& INP``: a line of at most *maxlen* characters, Return always ends it.

        Read the way the original reads it: **a line, terminated by Return**. That is
        what makes prompts reliable. The earlier version took a single character and
        then tried to throw away the Return the player had pressed -- and lost the
        race, because the Return often arrives a moment *after* the drain ran. The
        next prompt then got a bare Return, rejected it as not one of the allowed
        characters, and sat there: every answer one prompt late, which reads as a
        dead keyboard.

        A canonical terminal never had that problem for the same reason: the line
        discipline hands over ``1\n`` as one unit, so a Return always belongs to
        exactly one prompt. Reading a line here reproduces that, and
        Nothing is drained before the read: a canonical terminal does not discard
        what was typed early either, it holds it until something reads it, and
        draining here would throw away a whole script that arrived before the first
        prompt was drawn.
        """
        self._ensure_raw()
        got = []
        allowed_set = allowed_chars(allowed) | {"\r", "\n"}
        # Read to the end of the line even once *maxlen* characters have been
        # accepted. Otherwise the Return that ended this prompt stays in the
        # terminal and is handed to the next one, which then rejects it -- so a
        # one-character answer like the main menu would leave every later answer
        # one prompt out of step, which is what made the keyboard look dead.
        while True:
            ch = self._read_char()
            self._debug(f"  read {ch!r}")
            if ch is None:
                if self._eof:
                    break
                continue
            if ch == "\x1b":                          # an escape sequence
                self._drain()
                continue
            if ch in ("\r", "\n"):
                break
            if ch in ("\x7f", "\b"):
                if got:
                    got.pop()
                    self._echo_line(got)
                continue
            if len(got) >= maxlen:
                continue            # & INP beeps at the limit; just skip the key
            if allowed and ch not in allowed_set:
                self._debug(f"  rejected {ch!r} (allowed={allowed!r})")
                continue
            got.append(ch)
            self._echo_line(got)
        self.close()
        self._debug(f"key(allowed={allowed!r}, maxlen={maxlen}) -> {got!r}")
        return "".join(got)

    # ----------------------------------------------------------------- echo
    def _echo(self, ch: str):
        if self.echo and self._is_tty:
            sys.stdout.write(ch if ch not in ("\r", "\n") else "\n")
            sys.stdout.flush()

    def _echo_line(self, got):
        if self.echo and self._is_tty:
            sys.stdout.write("\r" + " " * 40 + "\r")
            sys.stdout.write("".join(got))
            sys.stdout.flush()

    def _at_eof(self) -> bool:
        return self._eof

    # ------------------------------------------------------------- the screen
    def print(self, text: str = ""):
        self.out.append(text)
        sys.stdout.write(text + "\n")
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
        """A scripted answer, filtered exactly as :meth:`TerminalUI.key` filters.

        Applying the same allowed set matters: the filter is what made a name
        prompt accept only four letters and a four-choice menu only two of its
        choices, and a scripted screen that skipped it could never notice.
        """
        a = self._next(default)
        self.record.append(("key", a))
        text = str(a)
        if allowed:
            keep = allowed_chars(allowed)
            text = "".join(ch for ch in text if ch in keep)
        return text[:maxlen] if maxlen else text

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
