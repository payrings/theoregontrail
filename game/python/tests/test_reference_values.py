"""The reference values the paper prints, checked against the transcription.

Paper section 12.6 gives the values the original's arithmetic produces: the
fifteen numbers the random generator gives for a known seed, the quirk in the
multiplication, and the seeds that turn out to give the same game. Those values
are in the paper, so the transcription can be checked against the paper
without an Apple II ROM image and without any of Apple's material.
"""
from oregon.applesoft.exact import ExactBackend
from oregon.applesoft.fac import Fac
from oregon.applesoft.rng import rnd

# Paper 12.6: the fifteen values of RND (1) from the seed 81 00 00 00 00, and the
# seed they leave behind.
SEQUENCE = [
    0.4072949117, 0.6080416190, 0.2595170654, 0.0826876603, 0.3586615882,
    0.9610444016, 0.5672113707, 0.6001326921, 0.3342543155, 0.6068662971,
    0.6758213558, 0.3164409971, 0.0368823348, 0.0349148413, 0.2833032483,
]
SEED_AFTER = "7F110D1F95"
ONE = bytes([0x81, 0, 0, 0, 0])


def test_the_random_sequence_is_the_one_the_paper_prints():
    """The generator gives the paper's fifteen values, and the paper's final seed."""
    seed = bytes([0x81, 0, 0, 0, 0])
    got = []
    for _ in range(15):
        value, seed = rnd(seed, ONE)
        got.append(Fac(value).to_float())
    assert [f"{v:.10f}" for v in got] == [f"{v:.10f}" for v in SEQUENCE], got
    assert seed.hex().upper() == SEED_AFTER, seed.hex()


def test_the_multiply_quirk_is_reproduced():
    """Paper 12.6: the ROM's multiply shifts one bit too far for these operands.

    The left operand is in stored form, with an implicit leading 1, and the right
    operand and the result are in working form, with an explicit one.
    """
    left = Fac(bytes.fromhex("884d000000"))
    right = Fac(bytes.fromhex("8fdd0000a3"))
    assert ExactBackend().mul(left, right).raw() == bytes.fromhex("97b0f90041")


def test_the_seeds_that_merge_merge_at_once():
    """Paper 12.6: RND(-519) and RND(-1038) give the same sequence from then on."""
    exact = ExactBackend()
    seeds = {}
    for n in (519, 1038):
        arg = bytes(exact.from_str(f"-{n}").raw())
        _, seeds[n] = rnd(bytes(5), arg)
    assert seeds[519].hex().upper() == "784000818A", seeds[519].hex()
    assert seeds[1038].hex().upper() == "784000818B", seeds[1038].hex()
    _, after_519 = rnd(seeds[519], ONE)
    _, after_1038 = rnd(seeds[1038], ONE)
    assert after_519 == after_1038 == bytes.fromhex("8007f3b788"), after_519.hex()
