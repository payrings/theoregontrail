"""Shared fixtures: an arithmetic backend and a scripted game context."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from oregon import applesoft                                  # noqa: E402
from oregon.context import Context                            # noqa: E402
from oregon.files import Files                                # noqa: E402
from oregon.rng import ScriptedRnd                           # noqa: E402
from oregon.trace import Tracer                               # noqa: E402
from oregon.ui import ScriptedUI                              # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def backend():
    """The ROM backend when the image is there, otherwise the pure-Python one."""
    return applesoft.use("rom" if applesoft.rom_available() else "pure")


@pytest.fixture
def game(tmp_path):
    """A context with a scripted screen, a scripted generator and a private disk."""
    ui = ScriptedUI([], allow_repeat=True, max_prompts=3000)
    rng = ScriptedRnd(" ".join(["0.5"] * 200000))
    return Context(ui=ui, rng=rng, files=Files(tmp_path / "data"), trace=Tracer())
