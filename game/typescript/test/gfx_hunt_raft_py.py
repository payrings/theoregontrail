import sys, hashlib, json
import os
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','python'))
import warnings; warnings.filterwarnings("ignore")
from oregon.graphics import assets as A, gui, backends, hunt_scene, raft_scene
from oregon import hunt
class B(backends.ScriptBackend):
    def __init__(s): super().__init__(""); s.h=[]
    def show(s,img): s.h.append(hashlib.md5(img.tobytes()).hexdigest()[:8])
folder=sys.argv[1]
a=A.Assets(folder); b=B(); ui=gui.GraphicalUI(a,b)
h=hunt.HuntRng(bytes.fromhex("86519ebd9f"))
n=[0]
def getkey():
    n[0]+=1
    k=n[0]
    if k%97==5: return "\r"
    if k%53==7: return " "
    if k%41==3: return "i"
    if k%31==2: return "\x1d"
    return None
import builtins
def _m(*a,key=None):
    if key is None: return builtins.max(*a)
    it=a[0]; best=builtins.max(key(q) for q in it)
    return next(p for p in sorted(it,key=lambda p:(p[1],p[0])) if key(p)==best)
hunt_scene.max=_m
r=hunt_scene.play(ui,a.hunt(),30,h.below,hunt.allowed_types(11),hunt.ANIMALS,getkey=getkey,live=False)
print(json.dumps(r), len(b.h), hashlib.md5("".join(b.h).encode()).hexdigest()[:10], b.h, b.h[-1])
# field
b2=B(); ui2=gui.GraphicalUI(a,b2)
from oregon.graphics import hunt_field
h=hunt.HuntRng(bytes.fromhex("86519ebd9f")); n[0]=0
r=hunt_field.play(ui2,20,h.below,h.below,hunt.allowed_types(11),hunt.ANIMALS,2500,getkey=getkey,pause=0.0)
print("field", json.dumps(r), len(b2.h))
# raft
b3=B(); ui3=gui.GraphicalUI(a,b3)
raft_scene.draw(ui3,9,[(40,60),(100,100)],[raft_scene.sign_position(3)],raft_scene.landing_position(30))
print("raft", b3.h)
