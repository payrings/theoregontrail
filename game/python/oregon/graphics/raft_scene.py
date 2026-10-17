"""The Columbia River raft, drawn from the pictures in the assets folder.

The river (``b_river``), the raft, the rocks and the direction signs are MECC's
pictures; the raft, rock and sign were copied from a recording of the original and
live in ``float_raft.png``, ``float_rock.png`` and ``float_sign.png``. The positions
are the listing's (line 1110 for the raft) or were measured on the recording:

* the raft's picture is drawn at ``(84 + 8 * hp + 3, 5 * hp - 6)``;
* a rock's picture is drawn at ``(RX + 7, RY)``;
* a direction sign enters at the bottom of the river, at (114, 168), and moves six dots
  right and three up a pass for twenty-two passes.

**Measured on the recording, not in the listing:** a pass of the loop takes about 0.45 s on the original (this game runs it twice as fast)
(the game's own interpreter, not the few thousand passes a second the paper estimated),
and the signs appear on the passes the listing names, 60, 120 and 170 (the first is seen
a few passes later because a pass with more rocks takes longer).
"""

from __future__ import annotations

__all__ = ["available", "draw", "SIGN_START", "SIGN_STEPS", "PASS_SECONDS", "LANDING_PASS",
           "landing_position"]

SIGN_START = (114, 168)
SIGN_STEP = (6, -3)
SIGN_STEPS = 23
PASS_SECONDS = 0.225        # twice the original's pace (the original takes about 0.45 s)

#: the arrival point -- FLOAT 1146 and 1149: ``IF TC = 175 THEN FL(3) = 1: TX = -8: TY = 218``,
#: then ``& IMAGE,6,TX,TY: TX = TX + 6: TY = TY - 3`` every pass. It comes up the river from
#: the bottom left and crosses the landing bank near passes 205 to 225.
LANDING_PASS = 175
LANDING_START = (-8, 218)


def available(ui) -> bool:
    a = getattr(ui, "assets", None)
    return bool(a and a.image("float_raft") and a.image("float_rock") and a.screen("b_river"))


def sign_position(passes_since_start: int):
    if 0 <= passes_since_start < SIGN_STEPS:
        return (SIGN_START[0] + SIGN_STEP[0] * passes_since_start,
                SIGN_START[1] + SIGN_STEP[1] * passes_since_start)
    return None


def landing_position(passes_since_start: int):
    """Where the arrival point is *passes_since_start* passes after pass 175, or None once it
    has left the screen."""
    if passes_since_start < 0:
        return None
    x = LANDING_START[0] + SIGN_STEP[0] * passes_since_start
    y = LANDING_START[1] + SIGN_STEP[1] * passes_since_start
    return (x, y) if x < 280 and y > -22 else None


def draw(ui, hp: int, rocks, signs=(), landing=None):
    """One picture of the river: *rocks* are ``(RX, RY)`` pairs, *signs* the positions."""
    cv = ui.cv
    cv.clear()
    cv.screen("b_river")
    for rx, ry in rocks:
        cv.image("float_rock", rx + 7, ry)
    for x, y in signs:
        cv.image("float_sign", x, y)
    if landing is not None:                       # the arrival point; its own picture if there is one
        cv.image("float_landing" if ui.assets.image("float_landing") else "float_sign", *landing)
    cv.image("float_raft", 84 + 8 * hp + 3, 5 * hp - 6)
    ui.refresh()
