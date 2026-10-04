"""The byte-level memory the BASIC uses: PEEK and POKE.

Running a new Applesoft program clears every variable, so the game passes state
between programs in memory locations 900 to 917 and writes the party names as
zero-terminated ASCII from 1920 (paper section 2.3, Appendix C). Modelling this
faithfully is not decoration: the two layouts at the start and the end of the
journey differ, and one of them is why the raft game reads the oxen from 909 while
the store wrote them to 905.

Two layouts exist and must not be confused:

======================  ==========================================  ====================
address                  at the start of the journey               at the end
======================  ==========================================  ====================
900                      (not written; the party is five)           people alive
901                      year - 1800                              year - 1800
902                      month, 3 to 7                            month
903                      day, always 1                             day
904                      the wagon flag, 1                        bullets, low byte
905                      yokes of oxen                             bullets, high byte
906, 907                 pounds of food, low then high             pounds of food
908                      sets of clothing                          sets of clothing
909                      boxes of bullets                          oxen, as I(2) + .5
910, 911, 912            spare wheels, axles, tongues             spare parts
913, 914                 money times ten, low then high            whole dollars
915                      profession: 1 banker, 2 carpenter, 3 farmer  unchanged
916                      (not used)                                health band, INT(H/35)
917                      (not used)                                cents
======================  ==========================================  ====================

A POKE of a value above 255 is Applesoft's ILLEGAL QUANTITY error, code 53. That
is not a corner case: it is what stops the game at The Dalles after 255 years
(paper section 13), so :meth:`Memory.poke` raises rather than truncating.
"""

from __future__ import annotations

from .errors import ApplesoftError, ILLEGAL_QUANTITY

__all__ = ["Memory", "HANDOFF_START", "HANDOFF_END", "NAMES_BASE", "KEYBOARD",
           "ERROR_CODE", "ERROR_LINE", "INIT_FLAG", "DISK_FLAG", "SOUND",
           "POWER_UP"]

HANDOFF_START = 900
HANDOFF_END = 917
NAMES_BASE = 1920
KEYBOARD = (78, 79)          # the 16-bit counter the keyboard routine keeps
ERROR_CODE = 222
ERROR_LINE = (218, 219)
INIT_FLAG = 919              # set to 1 once a program has finished initialising
DISK_FLAG = 955              # 254 when a two-sided disk is configured
SOUND = 975                  # 0 or 255
POWER_UP = 1012


class Memory:
    """64 KB of byte memory, addressed the way the Apple II is."""

    def __init__(self, program: str = "OREGON TRAIL"):
        self._b = bytearray(0x10000)
        self.program = program

    # ------------------------------------------------------------------ bytes
    def peek(self, address: int) -> int:
        if address < 0:
            address += 0x10000
        return self._b[address & 0xFFFF]

    def peek_word(self, address: int) -> int:
        """``PEEK (Z) + PEEK (Z + 1) * 256``, and ``DEF FN P``."""
        return self.peek(address) + self.peek(address + 1) * 256

    def poke(self, address: int, value, line: int = 0):
        """``POKE (address, value)``.

        A value above 255 is ILLEGAL QUANTITY in Applesoft, error 53. The game
        relies on this: ``POKE 901, AY - 1800`` at ``END.LIB`` 50050 stops with
        "Error 53 at line #50050" once the year passes 2055 (paper section 13).
        """
        n = int(value)
        if n < 0 or n > 255:
            raise ApplesoftError(ILLEGAL_QUANTITY, line or 0, self.program,
                                 f"POKE {address},{n}")
        if address < 0:
            address += 0x10000
        self._b[address & 0xFFFF] = n

    def poke_word(self, address: int, value: int, line: int = 0):
        """The ``FN HI`` / ``FN LO`` split: high byte first at ``address + 1``."""
        n = int(value)
        if n < 0 or n > 65535:
            raise ApplesoftError(ILLEGAL_QUANTITY, line or 0, self.program,
                                 f"16-bit store of {n} at {address}")
        self.poke(address, n % 256, line)
        self.poke(address + 1, n // 256, line)

    # ------------------------------------------------------------ text screen
    def put_names(self, names, line: int = 6045):
        """MENU 6045: the five names from 1920, each ended by a zero byte."""
        at = NAMES_BASE
        for name in names:
            for ch in str(name):
                self.poke(at, ord(ch), line)
                at += 1
            self.poke(at, 0, line)
            at += 1
        return at

    def get_names(self, count: int = 5) -> list:
        """OREGON TRAIL 29010: read the zero-terminated names back from 1920.

        An empty name is stored as a single zero byte and reads back as an empty
        string, which is why a name the player leaves blank survives the hand-over.
        """
        at = NAMES_BASE
        names = []
        for _ in range(count):
            s = ""
            while True:
                if at > 4000:
                    break
                b = self.peek(at)
                if b:
                    s += chr(b)
                else:
                    at += 1
                    break
                at += 1
            names.append(s)
        return names

    # --------------------------------------------------------- the keyboard
    @property
    def keyboard_counter(self) -> int:
        """``PEEK (78) + PEEK (79) * 256``: how long the player took to press a key."""
        return self.peek_word(KEYBOARD[0])

    @keyboard_counter.setter
    def keyboard_counter(self, value: int):
        self.poke(KEYBOARD[0], value % 256)
        self.poke(KEYBOARD[1], value // 256)
