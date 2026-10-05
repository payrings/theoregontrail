"""The game's state, in one object whose fields are the BASIC variable names.

Applesoft has no local variables and every library runs inside the main program, so
every variable is global and the libraries share it (paper section 2.1). This class
is the same idea: one object, named as the listing names its variables, so the
Python can be read against the BASIC. Appendix A is the reference for the names and
this file's comments give each one's meaning.

Variables that the original only uses as scratch -- ``Z``, ``V``, ``X``, ``Y``,
``L``, ``I``, ``B``'s array side, ``Q``'s array side -- live here too where the game
depends on them, and are marked as such. Values are :class:`~oregon.applesoft.fac.Fac`
unless the comment says otherwise.
"""

from __future__ import annotations

from . import num
from .applesoft.fac import Fac

__all__ = ["State"]


class State:
    """Everything the journey needs, named as the BASIC names it."""

    def __init__(self):
        # --- the constants C0 to C4 and P5, and the rest of VAR.BIN -----------
        self.C0, self.C1, self.C2, self.C3, self.C4 = (num.ZERO, num.ONE, num.TWO,
                                                        num.THREE, num.FOUR)
        self.P5 = num.HALF
        self.PQ = num.parse(".25")        # a spare constant in VAR.BIN
        self.S = 0                        # disk side: 0 for side one, 1 for side two
        self.RE_max = 14                  # RE, the highest event number
        self.SR = num.ONE                 # a graphics flag; see GAPS.md
        self.DF = num.ONE                 # another

        # --- dates, Appendix A ------------------------------------------------
        self.AD = num.ONE                 # day of the month
        self.AM = num.ONE                 # month, 3 to 7 on departure
        self.AY = num.ONE                 # year, 1848

        # --- weather, sections 4.5 and 6 -------------------------------------
        self.AR = num.parse("3")          # accumulated rain
        self.AS = num.ZERO                # snow on the ground
        self.W = num.ZERO                 # the weather code, 0 to 9
        self.TM = num.ZERO                # the temperature class, 0 to 5
        self.QT = num.ZERO                # the month's minimum temperature
        self.QP = num.ZERO                # the month's rain chance
        self.TR = num.ZERO                # today's rain
        self.TS = num.ZERO                # today's snow
        self.PP = num.ZERO                # the rain flag
        self.ZO = 0                       # the climate zone, 0 to 4

        # --- the party, section 5 ---------------------------------------------
        self.H = num.ZERO                 # party health; 0 is perfect, 139 the cap
        self.H0 = num.ZERO                # the number currently sick or injured
        self.HR = num.ZERO                # hardship set by the day's events
        self.FS = num.ZERO                # the freeze and starve factor; uncapped
        self.ZT = num.ZERO                # the temperature penalty
        self.ZC = num.ZERO                # the clothing penalty
        self.ZF = num.ZERO                # the ration penalty
        self.ZP = num.ZERO                # the pace and weather penalty
        self.NP = 5                       # people alive
        self.H1 = [num.ZERO] * 5          # each member's illness number
        self.H2 = [num.ZERO] * 5          # each member's days left
        self.N = [""] * 5                 # the names, N$(0 to 4)

        # --- movement, section 4 ----------------------------------------------
        self.LM = 0                       # the current landmark
        self.NM = 0                       # the next landmark
        self.MD = num.ONE                 # the segment's speed base: 20 or 12
        self.D = num.ZERO                 # miles left in the segment
        self.DD = num.ZERO                # the segment's full length
        self.M = num.ZERO                 # total miles travelled
        self.BS = num.ZERO                # the base speed, set at line 660
        self.V = num.ZERO                 # miles travelled today, line 3245
        self.SD = 0                       # stopped days remaining
        self.P = num.ONE                  # pace: 1 steady, 2 strenuous, 3 grueling
        self.R = num.ONE                  # rations: 1 filling, 2 meager, 3 bare
        self.FC = num.ZERO                # pounds of food eaten a day
        self.F0 = num.ZERO                # the ration penalty, 2 * (R - 1)
        self.OP = num.ZERO                # sets of clothing per person
        self.W1 = 0                       # 1 while at a river crossing
        self.LL = 0                       # 0 at a landmark, 1 on the trail
        self.IX = num.ONE                 # the risk divisor at rivers: 1, or 5 with a guide

        # --- goods, section 7 -------------------------------------------------
        # I(2) to I(8): oxen, clothing, bullets, wheels, axles, tongues, food.
        self.I = [num.ZERO] * 9
        self.I1 = num.ONE                 # the wagon flag; not used in play
        self.MY = num.ZERO                # money in dollars
        self.PF = num.ZERO                # pounds of food during the daily cycle

        # --- events, section 8 ------------------------------------------------
        self.RE = [num.ZERO] * 15         # RE(0 to 14), the fifteen event chances
        self.A = 0                        # the dialogue slot, 0 to 2
        self.F9 = 0                       # a screen-redraw flag
        self.B = 0                        # cannot continue: 2 no oxen, 5-7 a part,
                                          # 1 Return pressed

        # --- graves, section 10.2 --------------------------------------------
        # TOMB.SEQ holds two records, one per disk side: the segment code and the
        # miles along it at which a grave was left.
        self.SN = [0, 0]                  # SN(0 to 1)
        self.ML = [0, 0]                  # ML(0 to 1)
        self.DL = -1                      # the distance of the next grave
        self.LN = 0                       # which record a grave was read from

        # --- rivers, section 9.3 ---------------------------------------------
        self.RC = 0                       # the river row, 0 to 3
        self.RD = num.ZERO                # the current depth, to one decimal
        self.RW = num.ZERO                # the current width
        self.RS = num.ZERO                # the current swiftness
        self.RB = 0                       # the bottom: 0 smooth, 1 muddy, 2 rough

        # --- scratch the game depends on --------------------------------------
        self.T = [""] * 11                # T$(0 to 10): the loss lines, and the
                                          # river option text between uses
        # Q and Q() are two different variables (paper 2.5, rule b), and so are B
        # and B(). BUY.LIB 50003 and TRADE.LIB 50011 set the *scalar* Q to a fort
        # tier and to a rounded holding; neither touches the array the map draws.
        self.Q = num.ZERO                 # Q, the scalar
        self.Q_arr = [0] * 17             # Q(0 to 16), the landmark history
        self.B_arr = [95, 70, 81, 95, 23, 20]   # B(0 to 5), the travel-screen
                                          # column positions from Appendix E.5
        self.Q1 = 1                       # the next slot in Q()
        self.Z = num.ZERO                 # the scalar Z, scratch
        self.Z_arr = []                    # Z(), a separate variable

        # --- graphics-only state, kept so the call sites are visible ----------
        self.IXpix = 0
        self.IX2 = 0
        self.Y1 = 0
        self.Y2 = 0
        self.X1 = 0
        self.X2 = 0
        self.G = 0

    # ---------------------------------------------------------------- helpers
    def inv(self, item: int) -> Fac:
        """``I(item)`` for items 2 to 8."""
        return self.I[item]

    def set(self, item: int, value):
        self.I[item] = value

    def food(self) -> Fac:
        return self.PF if not self.PF.is_zero() else self.I[8]

    def health_band(self) -> int:
        """``INT (H / 35)``: 0 good, 1 fair, 2 poor, 3 very poor."""
        return num.trunc(num.div(self.H, num.parse("35")))

    def party_names(self):
        return [n for n in self.N[:max(0, self.NP)]]

    def is_traveling(self) -> bool:
        return self.SD == 0
