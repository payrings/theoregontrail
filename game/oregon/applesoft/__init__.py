"""Arithmetic backends for the game's 5-byte Applesoft numbers.

Four implementations sit behind one interface (see :mod:`oregon.applesoft.fac`):

``rom``
    A genuine Apple IIe ROM image running under a py65 6502 emulator. This is
    the default and the authority. Every arithmetic operation is executed by the
    ROM's own ``FADDT``, ``FMULTT``, ``FDIVT``, ``ROUND.FAC``, ``INT`` and
    ``RND``, so the alignment truncation, the shift-and-add multiply, the guard
    byte and the generator are the original's, not an imitation.

``exact``
    The same routines transcribed into Python from the ROM's disassembly
    (:mod:`oregon.applesoft.exact`). It runs without a ROM image and agrees with
    ``rom`` operand by operand (``tests/test_exact.py``; paper section 12.6).

``float`` and ``rounded``
    Host 64-bit floats, plain or rounded to Applesoft's precision after every
    operation: what a port that does not emulate the arithmetic would use (paper
    section 12.8; :mod:`oregon.applesoft.hostfloat`).

Select one with ``--num`` on the command line, or in code with :func:`use`.
"""

from __future__ import annotations

from . import fac
from .fac import Fac

__all__ = ["use", "use_rom", "current", "Fac", "choices", "rom_status",
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
    return ("rom", "exact", "float", "rounded")


def rom_status() -> str:
    from . import rom
    return rom.describe()


def use(which: str):
    """Install an arithmetic backend by name: one of :func:`choices`."""
    global _current
    if which in ("rom", "apple-rom", "apple"):
        from .rom import RomBackend
        _current = RomBackend()
    elif which in ("exact", "python-exact"):
        from .exact import ExactBackend
        _current = ExactBackend()
    elif which in ("float", "host-float"):
        from .hostfloat import FloatBackend
        _current = FloatBackend()
    elif which in ("rounded", "rounded-float"):
        from .hostfloat import RoundedFloatBackend
        _current = RoundedFloatBackend()
    else:
        raise ValueError(f"unknown numeric backend {which!r}; "
                         f"choose one of {choices()}")
    fac.set_backend(_current)
    return _current


def use_rom():
    return use("rom")


def current():
    return _current


# The ROM is the default when it is present; otherwise the Python transcription
# of its routines, so that the game still runs, unchanged, on a machine with no
# ROM image. Only a missing ROM image
# or a missing py65 is a reason to fall back, and the fallback says so: a run that
# believes it is using the ROM must never be silently using Python arithmetic.
try:                                    # pragma: no cover - trivial fallback
    use("rom")
except (FileNotFoundError, ImportError) as _why:
    import warnings as _warnings
    _warnings.warn(f"Applesoft ROM arithmetic unavailable ({_why}); using the "
                   "Python transcription of its routines", RuntimeWarning)
    use("exact")