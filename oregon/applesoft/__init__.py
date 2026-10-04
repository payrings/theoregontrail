"""Arithmetic backends for the game's 5-byte Applesoft numbers.

Two implementations sit behind one interface (see :mod:`oregon.applesoft.fac`):

``rom``
    A genuine Apple IIe ROM image running under a py65 6502 emulator. This is
    the default and the authority. Every arithmetic operation is executed by the
    ROM's own ``FADDT``, ``FMULTT``, ``FDIVT``, ``ROUND.FAC``, ``INT`` and
    ``RND``, so the alignment truncation, the shift-and-add multiply, the guard
    byte and the generator are the original's, not an imitation.

``pure``
    The same algorithms in Python, for speed. The test suite compares the two
    operand by operand; where they differ the ROM wins and the Python is fixed.

The paper (section 12) argues that parity needs the ROM, which is why the ROM is
the default rather than a convenience. Select one with ``--num`` on the command
line, or in code with :func:`use`.
"""

from __future__ import annotations

from . import fac
from .fac import Fac

__all__ = ["use", "use_rom", "use_pure", "current", "Fac", "choices", "rom_status",
           "rom_available", "rom_path"]


def rom_available() -> bool:
    """Whether an Apple IIe ROM image is where it is expected."""
    from . import rom
    return rom.available()


def rom_path():
    from . import rom
    return rom.rom_path()

_current = None


def choices():
    return ("rom", "pure")


def rom_status() -> str:
    from . import rom
    return rom.describe()


def use(which: str):
    """Install an arithmetic backend by name: ``"rom"`` or ``"pure"``."""
    global _current
    if which in ("rom", "apple2e-rom", "apple2e"):
        from .rom import RomBackend
        _current = RomBackend()
    elif which in ("pure", "pure-python", "python"):
        from .pure import PureBackend
        _current = PureBackend()
    else:
        raise ValueError(f"unknown numeric backend {which!r}; "
                         f"choose one of {choices()}")
    fac.set_backend(_current)
    return _current


def use_rom():
    return use("rom")


def use_pure():
    return use("pure")


def current():
    return _current


# The ROM is the default when it is present; otherwise the pure-Python path, so
# that the game still runs on a machine with no ROM image.
try:                                    # pragma: no cover - trivial fallback
    use("rom")
except Exception:                      # noqa: BLE001
    use("pure")