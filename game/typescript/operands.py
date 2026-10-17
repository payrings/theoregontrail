#!/usr/bin/env python3
"""Write random operand/result lines from Python's `exact` backend, for the TypeScript check.

    python3 operands.py SEED COUNT > ops.txt
    node dist/optest.js ops.txt          # "N checked, 0 differ"
"""
import random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))
from oregon.applesoft import use
use("exact")
from oregon import num
from oregon.applesoft.fac import Fac
def rv():
    k=random.random()
    if k<.3: return num.parse(str(random.choice([1,2,3,5,10,35,40,50,139,2000,1600,12,24])))
    if k<.5: return num.parse(random.choice(['.9','.1','.06','.007','1.2','.95','.105','.97','.003','.2','.6','8','.067']))
    if k<.8:
        return Fac(bytes((random.randint(0x70,0x95),random.randint(0,255)&(0xff if random.random()<.5 else 0x7f)|(0x80 if random.random()<.3 else 0),random.randint(0,255),random.randint(0,255),random.randint(0,255))))
    return Fac(bytes((random.randint(0x70,0x95),random.randint(0,127),random.randint(0,255),random.randint(0,255),random.randint(0,255))), random.randint(0,255))
random.seed(int(sys.argv[1]))
for i in range(int(sys.argv[2])):
    a,b=rv(),rv()
    for opn in ('add','sub','mul','div','addc','mulc','divc','cmp'):
        try:
            r=getattr(num,opn)(a,b) if opn!='cmp' else num.cmp(a,b)
            out=r if isinstance(r,int) else r.b.hex()+':%02x'%r.ext
        except Exception as e: out='ERR%s'%getattr(e,'code','?')
        print(a.b.hex(),'%02x'%a.ext,b.b.hex(),'%02x'%b.ext,opn,out)
    for opn in ('int_','str_','round'):
        try:
            if opn=='int_': r=num.int_(a); out=r.b.hex()+':%02x'%r.ext
            elif opn=='round': r=num.store(a); out=r.b.hex()
            else: out=num.str_(a)
        except Exception as e: out='ERR%s'%getattr(e,'code','?')
        print(a.b.hex(),'%02x'%a.ext,'-','00',opn,out)
