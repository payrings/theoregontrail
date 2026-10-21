"""A small version of the experiment of paper 12.7, with no ROM image.

The paper plays every seed under the ROM's arithmetic and under two simpler
ones, and reports that the transcription agrees with the ROM on every game,
that rounded floats end every game the same way with the same score, and that
plain floats take a different course in about half the games and end about one
game in sixty differently.

The ROM half needs an image, so it is not here. What is here are the two claims
that do not need one, checked over a few dozen seeds: rounded floats change no
game's ending and no game's score, and plain floats take a different course in
a good share of the games. It is a scaled-down version, so it checks the
direction of the difference and not the exact share.
"""
import contextlib
import io
import json

import pytest

SEEDS = list(range(40))
# The trace's cells: the values, then the event, then the seed bytes. The event is
# left out, as the paper leaves it out: a different arithmetic can change which
# event fires, and that shows up in the numbers around it.
VALUES = 25


def play(backend, seed, tmp_path):
    """One game from the preset start, under the named arithmetic."""
    from oregon import applesoft
    from oregon.__main__ import main
    trace = tmp_path / f"{backend}-{seed}.trace"
    applesoft.use(backend)
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            main(["--preset", "--demo", "--seed", str(seed), "--num", backend,
                  "--trace", str(trace), "--data", str(tmp_path / backend)])
    finally:
        applesoft.use("rom" if applesoft.rom_available() else "exact")
    found = [l for l in err.getvalue().splitlines() if l.startswith("SUMMARY ")]
    assert found, f"no summary for seed {seed} under {backend}"
    summary = json.loads(found[-1][len("SUMMARY "):])
    rows = [l.split(" ") for l in trace.read_text().splitlines()
            if l.strip() and not l.startswith("#")]
    return summary, rows


def differs(a, b):
    """Whether two traces of a game differ anywhere, value by value."""
    if len(a) != len(b):
        return True
    for row_a, row_b in zip(a, b):
        for cell_a, cell_b in zip(row_a[:VALUES], row_b[:VALUES]):
            if cell_a != cell_b:
                return True
        if row_a[26] != row_b[26]:                 # the five seed bytes
            return True
    return False


@pytest.fixture(scope="module")
def games(tmp_path_factory):
    """Every seed, played under each of the three arithmetics."""
    out = {}
    for backend in ("exact", "rounded", "float"):
        for seed in SEEDS:
            out[(backend, seed)] = play(backend, seed, tmp_path_factory.mktemp(backend))
    return out


def test_rounded_floats_change_no_game(games):
    """Paper 12.7: rounded floats end every game as the transcription does.

    Over the 62,883 games of the paper's experiment every game ended the same
    way and scored the same, and only the last digit of a value differed on the
    way. The same two things are checked here, over a few dozen games.
    """
    for seed in SEEDS:
        exact = games[("exact", seed)]
        rounded = games[("rounded", seed)]
        assert rounded[0]["ending"] == exact[0]["ending"], (
            seed, exact[0]["ending"], rounded[0]["ending"])
        assert rounded[0]["score"] == exact[0]["score"], (
            seed, exact[0]["score"], rounded[0]["score"])


def test_rounded_floats_change_a_few_games_along_the_way(games):
    """Paper 12.7: 10.19% of the games differ somewhere under rounded floats.

    The difference is a last digit in a value, and it does not reach the end of
    the game. Over a few dozen games the exact share cannot be pinned down, so
    this checks that few games differ and that most do not.
    """
    changed = [seed for seed in SEEDS
               if differs(games[("exact", seed)][1], games[("rounded", seed)][1])]
    assert len(changed) <= len(SEEDS) // 2, changed


def test_plain_floats_change_a_good_share_of_the_games(games):
    """Paper 12.7: 54.89% of the games differ somewhere under plain floats.

    The paper finds 45.11% of them identical on every day and 1.56% ending
    differently. Over a few dozen games the exact shares cannot be pinned down,
    so this checks that the difference is there in a good share of the games
    and that it hardly ever reaches the end of one.
    """
    changed = [seed for seed in SEEDS
               if differs(games[("exact", seed)][1], games[("float", seed)][1])]
    assert len(changed) >= len(SEEDS) // 4, changed
    endings = [seed for seed in SEEDS
               if games[("float", seed)][0]["ending"] != games[("exact", seed)][0]["ending"]]
    assert len(endings) <= len(SEEDS) // 4, endings
