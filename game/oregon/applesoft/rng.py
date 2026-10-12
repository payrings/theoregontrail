"""Applesoft's random generator, ``RND`` at ``$EFAE``, as an exact integer model.

This module is used by the ``exact``, ``float`` and ``rounded`` backends. It does not
call a backend's ``add`` and ``mul``: an arithmetic that differs from the ROM's by
one unit in the last place gives a generator that drifts away from the ROM's
sequence at once. Instead it models, bit for bit, the four ROM routines ``RND``
itself uses:

* ``FMULT`` -- shift-and-add over the five multiplier bytes (extension first),
  keeping a 32-bit result and an 8-bit extension. A zero multiplier byte is
  handled by a byte shift, and a zero byte that follows another zero byte shifts
  one bit further: ``MULTIPLY.1`` enters ``SHIFT.RIGHT.1`` with whatever carry the
  previous byte left, and that routine's bit count depends on it.
* ``FADD`` -- the smaller operand is shifted right, the bits shifted out go to the
  extension, and a carry out of the sum shifts everything right once.
* ``NORMALIZE.FAC`` -- shift left until bit 31 is set, lowering the exponent.
* ``ROUND.FAC`` -- add one to the significand when the extension is $80 or more.

The routine: load the seed, multiply by the five bytes at ``$EFA6``, add the five
bytes at ``$EFAA``, exchange the first and last significand bytes, clear the sign,
put the exponent in the extension, force the exponent to ``$80``, normalise, round
and store as the new seed. A negative argument skips the multiply and add and is
itself scrambled into the seed; a zero argument returns the seed unchanged. The
result lies in ``[0, 1)``.

Checked against the emulated ROM: every seed the game can reach -- all 65,536
``RND(-n)`` seeds followed by draws, and a chain of two million draws -- with no
disagreement. Arbitrary seeds the game never produces are another matter: for a
seed whose exponent byte is below $77 the model and the ROM can differ (for
example ``6F EE 00 00 01`` followed by ``RND(1)``), so the model is exact only on
the states the game itself reaches. ``tests/test_parity.py`` repeats a smaller version of that check
whenever the ROM image is present.
"""

from __future__ import annotations

from .fac import Fac

__all__ = ["applesoft_rnd", "rnd", "MULTIPLIER", "ADDEND"]

MULTIPLIER = bytes((0x98, 0x35, 0x44, 0x7A, 0x68))   # $EFA6
ADDEND = bytes((0x68, 0x28, 0xB1, 0x46, 0x20))       # $EFAA
MULT = MULTIPLIER
ADDC = ADDEND

def unpack(b):
    e=b[0]
    if e==0: return 0,0,0
    return e,((b[1]|0x80)<<24)|(b[2]<<16)|(b[3]<<8)|b[4],b[1]>>7
def normalise(e,m,x):
    """NORMALIZE.FAC.2: shift mantissa:extension left until bit 31 is set."""
    s=0
    while (m>>24)==0:
        m=((m<<8)|x)&0xFFFFFFFF; x=0; s+=8
        if s==32: return 0,0,0
    while not m&0x80000000:
        m=((m<<1)|(x>>7))&0xFFFFFFFF; x=(x<<1)&0xFF; s+=1
    if s>=e: return 0,0,0
    return e-s,m,x
def fmult(e1,m1,x1,e2,m2):
    """FAC (e1,m1,x1) times ARG (e2,m2): the ROM's shift-and-add, extension included."""
    if e1==0 or e2==0: return 0,0,0
    e=e1+e2-128
    if e<=0: return 0,0,0
    if e>255: raise OverflowError
    res=0; ext=0; carry=0
    for byte in (x1,m1&0xFF,(m1>>8)&0xFF,(m1>>16)&0xFF,(m1>>24)&0xFF):
        if byte==0:
            # MULTIPLY.1 jumps to SHIFT.RIGHT.1 for a zero byte: one byte to the
            # right. That routine's bit count depends on the carry flag it is
            # entered with, which is set after a non-zero byte and clear after a
            # zero one, so a zero byte that follows a zero byte shifts one bit more.
            ext=res&0xFF; res>>=8
            if not carry:
                ext=((res&1)<<7)|(ext>>1); res>>=1
            carry=0
            continue
        carry=1
        for k in range(8):
            c=0
            if (byte>>k)&1:
                res+=m2; c=res>>32; res&=0xFFFFFFFF
            ext=((res&1)<<7)|(ext>>1); res=(c<<31)|(res>>1)
    return normalise(e,res,ext)
def shr(m,x,n,keep_ext):
    """Shift mantissa (and extension) right n bits the way SHIFT.RIGHT does."""
    if n>=8:
        while n>=8:
            x=m&0xFF; m>>=8; n-=8
    elif not keep_ext:
        x=0
    for _ in range(n):
        x=((m&1)<<7)|(x>>1); m>>=1
    return m,x
def fadd(e1,m1,x1,e2,m2):
    """FAC + ARG, both positive; ARG comes from memory so has no extension."""
    if e2==0: return e1,m1,x1
    if e1==0: return e2,m2,0
    if e2<e1:
        ms,xs=shr(m2,0,e1-e2,False); argx=x1; e=e1; base=m1
    elif e2>e1:
        ms,xs=shr(m1,x1,e2-e1,True); argx=0; e=e2; base=m2
    else:
        ms,xs,argx,e,base=m2,x1,0,e1,m1
        xs=0; argx=x1
    t=xs+argx; x=t&0xFF; s=base+ms+(t>>8)
    if s>>32:
        x=((s&1)<<7)|(x>>1); s>>=1; e+=1
        if e>255: raise OverflowError
    return e,s,x
def round_pack(e,m,x):
    if e==0: return bytes(5)
    if x&0x80:
        m+=1
        if m>>32: m=0x80000000; e+=1
    return bytes((e,(m>>24)&0x7F,(m>>16)&0xFF,(m>>8)&0xFF,m&0xFF))
def rnd(seed,arg):
    """Return (value bytes, new seed bytes) for RND(arg) with the given seed."""
    ea,ma,sa=unpack(arg)
    if ea and sa:
        e,m,x=ea,ma,0
    else:
        e,m,s=unpack(seed); x=0
        if ea==0: return bytes(seed),bytes(seed)
        e,m,x=fmult(e,m,0,*unpack(MULT)[:2])
        e,m,x=fadd(e,m,x,*unpack(ADDC)[:2])
    b1,b4=(m>>24)&0xFF,m&0xFF
    m=(b4<<24)|(m&0x00FFFF00)|b1
    x=e; e=0x80
    e,m,x=normalise(e,m,x)
    out=round_pack(e,m,x)
    return out,out


def applesoft_rnd(backend, arg: Fac) -> Fac:
    """One ``RND`` call for a Python backend: returns the value, updates the seed."""
    value, seed = rnd(bytes(backend.get_seed()), bytes(arg.raw()))
    backend.set_seed(seed)
    return Fac(value)
