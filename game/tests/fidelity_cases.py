"""Formula cases for the fidelity tests: each runs the rebuild's code on given inputs.

``tests/data/fidelity.json`` holds, for each group below, a list of cases. A case is
the five-byte value of every input and the five-byte value of every output that the
**real Applesoft interpreter** produced when it ran the listing's own statements
(``basic`` below) on those inputs. ``test_fidelity.py`` feeds the same inputs to the
rebuild's code and demands the same five bytes.

The expected values were recorded from the Apple IIe ROM's BASIC interpreter, driven
as a program (not through ``oregon.applesoft``), so they do not depend on the code
under test. The recording script is not part of this repository: it needs a second,
independent 6502 core. The cases are plain data and can be checked without it.

Inputs are stored values, the kind a BASIC variable holds. Many are made by
multiplying two decimals and storing, so that they are not short decimals: the
interesting failures (paper 12.3, review finding B1) come from values whose low bits
are not zero.
"""

from __future__ import annotations

import tempfile

from oregon import num
from oregon.applesoft.fac import Fac
from oregon.context import Context
from oregon.files import Files
from oregon.rng import Rnd
from oregon.ui import ScriptedUI

__all__ = ["GROUPS", "hexof", "fac_from_hex", "LITERALS"]

_DIR = tempfile.mkdtemp(prefix="oregon-fidelity-")


def hexof(f: Fac) -> str:
    """The five stored bytes, with every zero written the same way."""
    b = f.raw()
    return "0000000000" if b[0] == 0 else b.hex()


def fac_from_hex(h: str) -> Fac:
    return Fac(bytes.fromhex(h))


# ------------------------------------------------------------------ small helpers
def whole(n) -> Fac:
    return num.store(num.parse(str(int(n))))


def tidy(r, lo, hi, dp=1) -> Fac:
    return num.store(num.parse(f"{r.uniform(lo, hi):.{dp}f}"))


def dirty(r, lo, hi) -> Fac:
    """A stored product of two decimals: a value with bits in all its places."""
    x, y = r.uniform(lo, hi), r.uniform(0.6, 1.4)
    return num.store(num.mul(num.parse(f"{x:.5f}"), num.parse(f"{y:.5f}")))


def either(r, lo, hi) -> Fac:
    return dirty(r, lo, hi) if r.random() < 0.6 else tidy(r, lo, hi, 2)


def ctx() -> Context:
    return Context(ui=ScriptedUI([], allow_repeat=True, max_prompts=500),
                   rng=SpyRnd(), files=Files(_DIR))


class SpyRnd(Rnd):
    """A generator that hands out chosen stored values and records every ``below``.

    It does not override ``below``: the comparison is the real one, so the decision
    is the code's own. ``decisions`` holds ``(tag, chance, result)`` for each call.
    """

    def __init__(self, draws=()):
        super().__init__()
        self.draws = [d for d in draws]
        self.i = 0
        self.decisions = []

    def rnd(self, arg: Fac) -> Fac:
        if not self.draws:
            return num.store(num.parse(".5"))
        v = self.draws[self.i % len(self.draws)]
        self.i += 1
        return v

    def below(self, tag, chance):
        res = super().below(tag, chance)
        self.decisions.append((tag, chance.raw(), res))
        return res


class ForcedRnd(SpyRnd):
    """``below`` returns True for the tags in ``true_tags`` whatever the draw, and
    records the chance it was given -- for reaching the code that follows."""

    def __init__(self, true_tags=(), draws=()):
        super().__init__(draws)
        self.true_tags = tuple(true_tags)
        self.chances = []

    def below(self, tag, chance):
        self.chances.append((tag, chance.raw()))
        res = any(tag.startswith(t) for t in self.true_tags)
        self.decisions.append((tag, chance.raw(), res))
        self.rnd1(tag)
        return res

    def first(self, prefix):
        for tag, raw in self.chances:
            if tag.startswith(prefix):
                return Fac(raw)
        raise AssertionError(f"no draw tagged {prefix!r}: "
                             f"{[t for t, _ in self.chances]}")


GROUPS: dict = {}


def group(name, basic, ins, outs, gen, run, consts=None):
    GROUPS[name] = dict(basic=basic, ins=ins, outs=outs, gen=gen, run=run,
                        consts=consts or {})


# ---------------------------------------------------------------- 650-660 the speed
def _speed_gen(r):
    return dict(J2=num.store(num.div(num.parse(str(r.randint(0, 40))), num.parse("2"))),
                J3=whole(r.randint(0, 20)), NP=whole(r.randint(1, 5)),
                R=whole(r.randint(1, 3)), P=whole(r.randint(1, 3)),
                MD=whole(r.choice((12, 20))))


def _speed_run(i):
    from oregon import trail
    c = ctx()
    st = c.st
    st.I[2], st.I[3] = i["J2"], i["J3"]
    st.NP, st.R, st.P, st.MD = num.as_int(i["NP"]), i["R"], i["P"], i["MD"]
    trail.speed(c)
    return dict(FC=st.FC, BS=st.BS, OP=st.OP, F0=st.F0)


group("speed 650-660",
      {650: "V=J2/4:IF V>1 THEN V=1",
       660: "FC=NP*(4-R):BS=MD*V*(P+1)/2:OP=J3/NP:F0=2*(R-1):V=BS"},
      "J2 J3 NP R P MD", "FC BS OP F0", _speed_gen, _speed_run)


# ------------------------------------------------------------ 3207-3230 the health
def _health_gen(r):
    return dict(TM=either(r, 0, 6), OP=either(r, 0, 4), F0=whole(r.choice((0, 2, 4))),
                PF=whole(r.choice((0, r.randint(1, 1500)))), FS=either(r, 0, 3),
                P=whole(r.randint(1, 3)), W=whole(r.randint(0, 9)),
                H=either(r, 0, 139), H0=whole(r.randint(0, 5)),
                HR=r.choice((num.ZERO, either(r, 0, 5))), FC=whole(r.randint(1, 15)))


def _health_run(i):
    from oregon import trail
    c = ctx()
    st = c.st
    st.TM, st.OP, st.F0, st.PF, st.FS = i["TM"], i["OP"], i["F0"], i["PF"], i["FS"]
    st.P, st.W, st.H, st.HR, st.FC = i["P"], i["W"], i["H"], i["HR"], i["FC"]
    st.H0 = num.as_int(i["H0"])
    trail.health_today(c)
    return dict(ZT=st.ZT, ZC=st.ZC, ZF=st.ZF, ZP=st.ZP, FS=st.FS, H=st.H, PF=st.PF)


group("health 3207-3230",
      {3207: "ZT=TM-C3:IF ZT<C0 THEN ZT=C2-TM",
       3210: "ZC=5-TM-TM-OP:IF ZC<C0 THEN ZC=C0",
       3215: "X=(ZC>P5):Y=(PF=C0):ZF=F0:IF Y THEN ZF=8",
       3220: "ZP=(W>5)+(W>7)+P+P",
       3225: "Z=FS*P5:IF X OR Y THEN Z=FS+.8",
       3230: "FS=Z:H=.9*H+ZT+ZC+ZF+ZP+FS+H0+HR:PF=PF-FC:IF PF<C0 THEN PF=C0"},
      "TM OP F0 PF FS P W H H0 HR FC", "ZT ZC ZF ZP FS H PF", _health_gen, _health_run,
      consts=dict(C0=0, C2=2, C3=3, P5=".5"))


# --------------------------------------------------------- 3240 rain and snow ground
def _acc_gen(r):
    return dict(AR=either(r, 0, 4), AS=r.choice((num.ZERO, either(r, 0, 60))),
                TR=r.choice((num.ZERO, tidy(r, 0.2, 0.8), either(r, 0, 1))),
                TS=r.choice((num.ZERO, either(r, 0, 5))), TM=either(r, 0, 6),
                W=whole(r.randint(0, 9)))


def _acc_run(i):
    from oregon import trail
    c = ctx()
    st = c.st
    for k in ("AR", "AS", "TR", "TS", "TM", "W"):
        setattr(st, k, i[k])
    trail.accumulate(c)
    return dict(AR=st.AR, AS=st.AS)


group("accumulate 3240",
      {3240: "AR=.9*AR+TR:AS=.97*AS+TS:IF AS THEN:IF TM>C2 OR W=8 THEN AR=AR+P5:AS=AS-5:IF AS<C0 THEN AS=C0"},
      "AR AS TR TS TM W", "AR AS", _acc_gen, _acc_run, consts=dict(C0=0, C2=2, P5=".5"))


# ------------------------------------------------------------- 3244-3246 the travel
def _travel_gen(r):
    return dict(AS=r.choice((num.ZERO, either(r, 0, 50))), BS=either(r, 0, 25),
                H0=whole(r.randint(0, 5)), SD=whole(r.choice((0, 0, 0, 1))),
                D=either(r, 0, 200), M=either(r, 0, 1900))


def _travel_run(i):
    from oregon import trail
    c = ctx()
    st = c.st
    st.AS, st.BS, st.D, st.M = i["AS"], i["BS"], i["D"], i["M"]
    st.H0, st.SD = num.as_int(i["H0"]), num.as_int(i["SD"])
    trail.travel_today(c)
    return dict(V=st.V, D=st.D, M=st.M)


group("travel 3244-3246",
      {3244: "Z=1-AS/40:IF Z<0 THEN Z=0",
       3245: "V=BS*(C1-.1*H0)*NOT SD*Z:IF 1.1*V>D THEN V=D",
       3246: "D=D-V:M=M+V"},
      "AS BS H0 SD D M", "V D M", _travel_gen, _travel_run, consts=dict(C1=1))


# ------------------------------------------------------------------ 105 FN W(Z)
def _fnw_gen(r):
    from oregon.data import climate as CL
    zo, am, which = r.randint(0, 4), r.randint(3, 7), r.randint(0, 1)
    code = ord(CL.WC[zo][am * 2 + which - 2])
    return dict(Z=whole(which), A=whole(code), ZO=whole(zo), AM=whole(am))


def _fnw_run(i):
    from oregon import trail
    c = ctx()
    st = c.st
    st.ZO, st.AM = num.as_int(i["ZO"]), i["AM"]
    return dict(Q=trail.fn_w(st, num.as_int(i["Z"])))


group("FN W line 105",
      {105: "Q=(NOT Z+.003*Z)*(A-30)-20*NOT Z"},
      "Z A ZO AM", "Q", _fnw_gen, _fnw_run)


# ----------------------------------------------------------- 3206 rain, snow, heavy
def _rain_gen(r):
    return dict(Z=whole(r.randint(0, 1)), TM=whole(r.randint(0, 5)))


def _rain_run(i):
    from oregon import trail
    c = ctx()
    st = c.st
    st.PP = num.ONE
    st.TM = i["TM"]
    z = num.as_int(i["Z"])
    c.rng = SpyRnd()
    c.rng.below = lambda tag, chance, _z=z: bool(_z) if tag == "3206 heavy rain" else False
    trail.weather(c)
    return dict(TR=st.TR, TS=st.TS, W=st.W)


group("rain 3206",
      {3206: "TR=.2+.6*Z:W=6+Z+Z:IF TM<C2 THEN W=W+C1:TS=8*TR:TR=C0"},
      "Z TM", "TR TS W", _rain_gen, _rain_run, consts=dict(C0=0, C1=1, C2=2))


# ------------------------------------------------------------ 3160 today's chances
def _re_gen(r):
    return dict(AS=r.choice((num.ZERO, either(r, 0, 50))), AR=either(r, 0, 4),
                H=either(r, 0, 139), D=either(r, 0, 200), DL=whole(r.randint(0, 200)),
                PF=whole(r.choice((0, r.randint(1, 1500)))), W=whole(r.randint(0, 9)),
                TM=either(r, 0, 6))


def _re_run(i):
    from oregon import events, trail
    c = ctx()
    st = c.st
    for k in ("AS", "AR", "H", "D", "PF", "W", "TM"):
        setattr(st, k, i[k])
    st.DL = num.as_int(i["DL"])
    st.SD = 0
    fired = events.fire
    events.fire = lambda c, which: None
    try:
        trail.event_loop(c)
    finally:
        events.fire = fired
    return {"R0": st.RE[0], "R1": st.RE[14], "R3": st.RE[3], "R4": st.RE[4],
            "R5": st.RE[5], "R6": st.RE[6]}


group("events 3160",
      {3160: "R0=(AS>30):R1=P5*(AR<.1):R3=.01+H/1500:R4=(D<DL):R5=.05*(PF=0):R6=(W>7)+.15*(TM<C2)"},
      "AS AR H D DL PF W TM", "R0 R1 R3 R4 R5 R6", _re_gen, _re_run,
      consts=dict(C2=2, P5=".5"))


# ------------------------------------------------------- 50150 the river's state
def _rc_gen(r):
    from oregon.data import rivers as R
    rc = r.randrange(len(R.RC))
    row = R.RC[rc]
    return dict(AR=either(r, 0, 3), RC=whole(rc), R0=num.store(num.parse(str(row[0]))),
                R1=num.store(num.parse(str(row[1]))), R2=num.store(num.parse(str(row[2]))))


def _rc_run(i):
    from oregon import river
    c = ctx()
    st = c.st
    st.RC, st.AR = num.as_int(i["RC"]), i["AR"]
    river.conditions(c)
    return dict(RD=st.RD, RW=st.RW, RS=st.RS)


group("river 50150",
      {50150: "RD=INT((R0+AR*2)*10+.5)/10:RW=INT(R1+15*AR):RS=R2+AR"},
      "AR RC R0 R1 R2", "RD RW RS", _rc_gen, _rc_run)


# ---------------------------------------------------- 50040 a ford that is too deep
def _party(c):
    st = c.st
    for k in range(3, 9):
        st.I[k] = whole(5 + k)
    st.I[2] = whole(6)
    st.NP = 5
    st.N = ["Zeke", "Jed", "Anna", "Mary", "Joey"]


def _deep_gen(r):
    return dict(RD=num.store(num.parse(f"{r.uniform(3, 7):.1f}")),
                IX=whole(r.choice((1, 5))))


def _deep_run(i):
    from oregon import river
    c = ctx()
    _party(c)
    c.st.RD, c.st.IX = i["RD"], i["IX"]
    c.rng = ForcedRnd()
    river.ford(c)
    return dict(V1=c.rng.first("50205 goods"), V2=c.rng.first("50185 ox"),
                V3=c.rng.first("50175 person"))


group("ford deep 50040",
      {50040: "V1=(RD/10)/IX:V2=((RD-1)/10)/IX:V3=((RD-2.5)/10)/IX"},
      "RD IX", "V1 V2 V3", _deep_gen, _deep_run)


# ------------------------------------------------------ 50060 and 50070 shallow fords
def _shallow_gen(r):
    return dict(IX=whole(r.choice((1, 5))),
                RN=num.store(num.parse(f"{r.random():.6f}")),
                RD=num.store(num.parse(f"{r.uniform(0.5, 2.4):.1f}")))


def _mud_run(i):
    from oregon import river
    from oregon.data import rivers as R
    c = ctx()
    _party(c)
    c.st.RD, c.st.IX, c.st.RB = num.parse("1.5"), i["IX"], R.muddy
    c.rng = ForcedRnd()
    river.ford(c)
    return dict(V4=c.rng.first("50060"))


group("ford mud 50060", {50060: "V4=.4/IX"}, "IX", "V4",
      lambda r: dict(IX=whole(r.choice((1, 5)))), _mud_run)


def _rough_run(i):
    from oregon import river
    from oregon.data import rivers as R
    c = ctx()
    _party(c)
    c.st.RD, c.st.IX, c.st.RB = i["RD"], i["IX"], R.rough
    c.rng = ForcedRnd(true_tags=("50070",), draws=[i["RN"]])
    river.ford(c)
    return dict(V5=c.rng.first("50070"), V6=c.rng.first("50205 goods"))


group("ford rough 50070",
      {50070: "V5=.16/IX:V6=.1+RN*.3"}, "IX RN RD", "V5 V6", _shallow_gen, _rough_run)


# ----------------------------------------------------------- 50085 floating a wagon
def _float_gen(r):
    return dict(RD=num.store(num.parse(f"{r.uniform(1.5, 7):.1f}")), RS=either(r, 0, 12),
                IX=whole(r.choice((1, 5))))


def _float_run(i):
    from oregon import river, trail
    c = ctx()
    _party(c)
    c.st.RD, c.st.RS, c.st.IX = i["RD"], i["RS"], i["IX"]
    c.rng = ForcedRnd(true_tags=("50085",))
    run_days = trail.run_stopped_days
    trail.run_stopped_days = lambda c: None
    try:
        river.float_crossing(c)
    finally:
        trail.run_stopped_days = run_days
    return dict(V1=c.rng.first("50085"), V2=c.rng.first("50205 goods"),
                V3=c.rng.first("50175 person"))


group("float 50085",
      {50085: "V1=(RD>2.5)*(RS/20)/IX:V2=(.4+RS/25)/IX:V3=((RS-3)/15)/IX"},
      "RD RS IX", "V1 V2 V3", _float_gen, _float_run)


# ------------------------------------------------------------------ 50115 the ferry
def _ferry_gen(r):
    return dict(RS=either(r, 0, 14), MY=either(r, 20, 900))


def _ferry_run(i):
    from oregon import river, trail
    c = ctx()
    _party(c)
    st = c.st
    st.RD, st.RS, st.MY = num.parse("4"), i["RS"], i["MY"]
    c.ui = ScriptedUI(["y"], allow_repeat=True, max_prompts=50)
    c.rng = ForcedRnd(true_tags=("50120",), draws=[num.store(num.parse(".6"))])
    run_days = trail.run_stopped_days
    trail.run_stopped_days = lambda c: None
    try:
        river.ferry(c)
    finally:
        trail.run_stopped_days = run_days
    return dict(V=c.rng.first("50120"), MY=st.MY)


group("ferry 50115",
      {50115: "MY=MY-V0:V=.05*(RS>5)+.1*(RS>10)"},
      "RS MY V0", "V MY", lambda r: dict(_ferry_gen(r), V0=whole(5)), _ferry_run)


# --------------------------------------------------------------- 910-950 the bill
def _bill_gen(r):
    food = r.choice((r.randint(0, 2000), r.randint(0, 99)))
    return dict(Y5=whole(r.randint(0, 9)), Y6=whole(food % 256), Y7=whole(food // 256),
                Y8=whole(r.randint(0, 20)), Y9=whole(r.randint(0, 60)),
                X0=whole(r.randint(0, 3)), X1=whole(r.randint(0, 3)),
                X2=whole(r.randint(0, 3)))


def _bill_run(i):
    from oregon import buysupplies
    c = ctx()
    peek = {905: "Y5", 906: "Y6", 907: "Y7", 908: "Y8", 909: "Y9", 910: "X0",
            911: "X1", 912: "X2"}
    for addr, name in peek.items():
        c.mem.poke(addr, num.as_int(i[name]))
    return dict(TB=buysupplies.bill(c))


group("bill 910-4000",
      {4000: "Z=0:V=40*Y5:Z=Z+V:V=.2*(Y7*256+Y6):Z=Z+V:V=10*Y8:Z=Z+V:V=2*Y9:Z=Z+V:V=10*(X0+X1+X2):Z=Z+V:TB=Z"},
      "Y5 Y6 Y7 Y8 Y9 X0 X1 X2", "TB", _bill_gen, _bill_run)


# ---------------------------------------------- 50020 the toll, 50060 the cents
def _toll_gen(r):
    return dict(I2=num.store(num.div(num.parse(str(r.randint(0, 60))), num.parse("2"))))


def _toll_run(i):
    from oregon import endl
    c = ctx()
    c.st.I[2] = i["I2"]
    return dict(V=endl.barlow_toll(c.st))


group("toll 50020",
      {50020: "V=5+INT(I2+.5)*.5:Z=V:V=Z:V=INT(V*100+.5)/100"}, "I2", "V",
      _toll_gen, _toll_run)


def _cents_gen(r):
    return dict(MY=either(r, 0, 900))


def _cents_run(i):
    from oregon import endl
    c = ctx()
    st = c.st
    st.MY = i["MY"]
    st.I[2] = whole(4)
    st.AY, st.AM, st.AD = num.parse("1848"), num.parse("3"), num.ONE
    st.N = ["Zeke", "Jed", "Anna", "Mary", "Joey"]
    endl.write_handover(c)
    return dict(MY=st.MY, Q9=Fac.from_int(c.mem.peek(917)))


group("cents 50060-50070",
      {50060: "MY=INT(MY*100+.5)/100", 50070: "Q9=INT((MY-INT(MY))*100+.5)"},
      "MY", "MY Q9", _cents_gen, _cents_run)


# ----------------------------------------- fire, thief, wagon and river losses
def _rn(r):
    return num.store(num.parse(f"{r.random():.7f}"))


def _fire_gen(r):
    return dict(RN=_rn(r), YY=whole(r.choice((r.randint(1, 20), r.randint(1, 2000)))))


def _fire_run(i):
    from oregon import lf
    c = ctx()
    c.st.I[3] = i["YY"]
    c.rng = ForcedRnd(true_tags=("50000 fire item 3",),
                      draws=[num.store(num.parse(".25")), i["RN"], num.store(num.parse(".25"))])
    lf.fire(c)
    return dict(I3=c.st.I[3])


group("fire 50000", {50000: "X=INT(RN*YY+1):I3=YY-X"}, "RN YY", "I3",
      _fire_gen, _fire_run)


def _thief_gen(r):
    return dict(RN=_rn(r), YY=whole(r.choice((r.randint(1, 100), r.randint(101, 2000)))))


def _thief_run(i):
    from oregon import lf
    c = ctx()
    c.st.I[3] = i["YY"]
    c.rng = SpyRnd(draws=[num.store(num.parse(".3")), i["RN"]])       # item 3, then X
    lf.thief(c)
    return dict(I3=c.st.I[3])


group("thief 52010", {52010: "X=100*(YY>100)+YY*(YY<101):X=INT(RN*X+1):I3=YY-X"},
      "RN YY", "I3", _thief_gen, _thief_run)


def _wagon_gen(r):
    return dict(RN=_rn(r), I4=whole(r.randint(0, 900)), I5=whole(r.randint(0, 3)))


def _wagon_run(i):
    from oregon import lf
    out = {}
    c = ctx()
    c.st.I[4] = i["I4"]
    c.rng = ForcedRnd(true_tags=("51010 found item 4",),
                      draws=[num.store(num.parse(".9")), num.store(num.parse(".9")), i["RN"]])
    lf.abandoned_wagon(c)
    out["I4"] = c.st.I[4]
    c = ctx()
    c.st.I[5] = i["I5"]
    c.rng = ForcedRnd(true_tags=("51010 found item 5",),
                      draws=[num.store(num.parse(".9"))] * 3 + [i["RN"]])
    lf.abandoned_wagon(c)
    out["I5"] = c.st.I[5]
    return out


group("abandoned wagon 51010",
      {51000: "X=INT(RN*3+1):X=X+X*(4=4)*20:I4=I4+X",
       51001: "X=INT(RN*3+1):IF I5+X<4 THEN I5=I5+X"},
      "RN I4 I5", "I4 I5", _wagon_gen, _wagon_run)


def _loss_gen(r):
    v = num.store(num.div(num.parse(str(r.randint(1, 9))), num.parse("10")))
    lo = num.store(num.parse(f"{r.random():.7f}"))
    near = Fac(_step(v.b, r.choice((-1, 0, 1))))
    return dict(V=v, R1=r.choice((lo, near)), RN=_rn(r), I3=whole(r.randint(0, 30)))


def _loss_run(i):
    from oregon import river
    c = ctx()
    c.st.I[3] = i["I3"]
    c.rng = SpyRnd(draws=[i["R1"], i["RN"]])
    river.losses(c, i["V"], 3, "50205 goods")
    return dict(I3=c.st.I[3])


group("goods lost 50205",
      {50205: "X=I3:IF X AND R1<V THEN Y=INT(RN*X+1):I3=X-Y"},
      "V R1 RN I3", "I3", _loss_gen, _loss_run)


# ------------------------------------------------------------ BUY.LIB at a fort
def _fort_gen(r):
    from oregon.data import goods as G
    item = r.randrange(7)
    return dict(B0=num.store(num.parse(str(G.PRICE[item]))), IT=whole(item),
                Q=whole(r.randint(1, 6)), Z=whole(r.choice((1, r.randint(1, 60)))),
                MY=either(r, 0, 900), I3=whole(r.randint(0, 3)))


def _fort_run(i):
    from oregon import fortbuy
    item, q, n = num.as_int(i["IT"]), num.as_int(i["Q"]), num.as_int(i["Z"])
    p = fortbuy.price(item, q)
    st = ctx().st
    st.MY = i["MY"]
    st.I[item + 2] = i["I3"]
    t = whole(1 if fortbuy.too_dear(st, n, p) else 0)
    fortbuy.purchase(st, item, n, p)
    return dict(V=p, T=t, MY=st.MY, J=st.I[item + 2])


group("fort BUY.LIB 50025-50030",
      {50025: "V=B0:V=V+.25*Q*V",
       50026: "K=1+19*(IT=2):T=0:IF (Z*V)>MY+.001 THEN T=1",
       50027: "J=I3+Z*K:MY=MY-Z*V"},
      "B0 IT Q Z MY I3", "V T MY J", _fort_gen, _fort_run)


# ------------------------------------------------- comparisons with a decimal literal
#: Every decimal the game compares a draw with in place, as ``RND (1) < .3``. The
#: literal is the right operand, so it still carries the bits FIN left in the
#: extension byte when the comparison is made.
LITERALS = [".3", ".33", ".5", ".4", ".16", ".05", ".15", ".1", ".2", ".6", ".01", ".9",
            ".97", ".007", ".06", ".02", ".003", ".8", ".25", ".51"]


def _step(b: bytes, d: int) -> bytes:
    """The positive value *d* places from *b* (the 31-bit significand carries)."""
    e, m = b[0], int.from_bytes(b[1:], "big") & 0x7FFFFFFF
    m += d
    if m < 0:
        e, m = e - 1, m + (1 << 31)
    elif m >= 1 << 31:
        e, m = e + 1, m - (1 << 31)
    return bytes([e]) + m.to_bytes(4, "big")


def _cmp_gen_for(lit):
    def gen(r):
        base = num.store(num.parse(lit)).b
        return dict(R=Fac(_step(base, r.choice((-2, -1, 0, 0, 0, 1, 2)))))
    return gen


def _cmp_run_for(lit):
    def run(i):
        lit_f = num.parse(lit)
        return dict(KL=whole(int(num.lt(i["R"], lit_f))),
                    KG=whole(int(num.gt(i["R"], lit_f))),
                    KE=whole(int(num.eq(i["R"], lit_f))))
    return run


for _lit in LITERALS:
    # each IF is on a line of its own: everything after THEN belongs to the IF
    group(f"compare with {_lit}",
          {9000: f"IF R<{_lit} THEN KL=1", 9001: f"IF R>{_lit} THEN KG=1",
           9002: f"IF R={_lit} THEN KE=1"},
          "R", "KL KG KE", _cmp_gen_for(_lit), _cmp_run_for(_lit))
