import {readFileSync,readdirSync,statSync} from 'node:fs';
import {inflateSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const D=fileURLToPath(new URL('../dist/',import.meta.url));
const {Assets}=await import(D+'gfx/assets.js'); const {GraphicalUI}=await import(D+'gfx/gui.js');
const HS=await import(D+'gfx/hunt_scene.js'), HF=await import(D+'gfx/hunt_field.js'), RS=await import(D+'gfx/raft_scene.js');
const {HuntRng,allowedTypes,ANIMALS}=await import(D+'hunt.js');
const folder=process.argv[2];
const files=new Map();
(function walk(d,rel){for(const f of readdirSync(d)){const p=d+'/'+f,r=rel?rel+'/'+f:f;statSync(p).isDirectory()?walk(p,r):files.set(r,new Uint8Array(readFileSync(p)))}})(folder,'');
const a=await Assets.load(files,async b=>new Uint8Array(inflateSync(b)));
const md5=im=>createHash('md5').update(Buffer.from(im.data.buffer,im.data.byteOffset,im.data.byteLength)).digest('hex').slice(0,8);
// RGBA -> RGB bytes like PIL tobytes
const rgb=im=>{const o=Buffer.alloc(im.w*im.h*3);for(let i=0;i<im.w*im.h;i++){o[i*3]=im.data[i*4];o[i*3+1]=im.data[i*4+1];o[i*3+2]=im.data[i*4+2]}return o};
const hashImg=im=>createHash('md5').update(rgb(im)).digest('hex').slice(0,8);
function mk(){const h=[];const be={show(i){h.push(hashImg(i))},poll(){return null},async read(){return null},async readTimeout(){return null},async pump(){},flush(){},async sleep(){}};return [be,h]}
let n=0;const getkey=()=>{n++;const k=n;if(k%97==5)return "\r";if(k%53==7)return " ";if(k%41==3)return "i";if(k%31==2)return "\x1d";return null};
let [be,h]=mk();let ui=new GraphicalUI(a,be);
let hr=new HuntRng([0x86,0x51,0x9e,0xbd,0x9f]);
let r=await HS.play(ui,a.hunt(),30,hr.below,allowedTypes(11),ANIMALS,{getkey,live:false});
console.log(JSON.stringify(r),h.length,createHash('md5').update(h.join('')).digest('hex').slice(0,10),JSON.stringify(h),h[h.length-1]);
[be,h]=mk();ui=new GraphicalUI(a,be);hr=new HuntRng([0x86,0x51,0x9e,0xbd,0x9f]);n=0;
r=await HF.play(ui,20,hr.below,hr.below,allowedTypes(11),ANIMALS,2500,{getkey,pause:0});
console.log("field",JSON.stringify(r),h.length);
[be,h]=mk();ui=new GraphicalUI(a,be);
RS.draw(ui,9,[[40,60],[100,100]],[RS.signPosition(3)],RS.landingPosition(30));
console.log("raft",JSON.stringify(h));
