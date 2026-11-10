import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { GlobalFonts } from '@napi-rs/canvas';

const ROOT=path.dirname(fileURLToPath(import.meta.url));
GlobalFonts.registerFromPath(path.join(ROOT,'assets/fonts/SpaceGrotesk.ttf'),'RG Display');
GlobalFonts.registerFromPath(path.join(ROOT,'assets/fonts/IBMPlexMono-Regular.ttf'),'RG Mono');
export const DATA=JSON.parse(fs.readFileSync(path.join(ROOT,'assets/demo.json'),'utf8'));
export const FPS=60,DURATION=60;
export const C={cream:'#F3F2EA',paper:'#FCFCF8',ink:'#111C29',blue:'#2451FF',citrus:'#DFFF5B',coral:'#FF785B',muted:'#68736B',line:'#CCD2C6',mint:'#B9E3CE'};

const clamp=x=>Math.min(1,Math.max(0,x));
const ease=x=>1-Math.pow(1-clamp(x),5);
const smooth=x=>{x=clamp(x);return x*x*(3-2*x);};
const p=(t,a,d=.8)=>ease((t-a)/d);
const lerp=(a,b,t)=>a+(b-a)*t;
function group(c,a,fn){if(a<=0)return;c.save();c.globalAlpha*=clamp(a);fn();c.restore();}
function fill(c,color,W,H){c.fillStyle=color;c.fillRect(0,0,W,H);}
function rect(c,x,y,w,h,color){c.fillStyle=color;c.fillRect(x,y,w,h);}
function circle(c,x,y,r,color,stroke=null,lw=2){c.beginPath();c.arc(x,y,Math.max(0,r),0,2*Math.PI);if(color){c.fillStyle=color;c.fill();}if(stroke){c.strokeStyle=stroke;c.lineWidth=lw;c.stroke();}}
function line(c,x,y,xx,yy,color,lw=3){c.beginPath();c.moveTo(x,y);c.lineTo(xx,yy);c.lineWidth=lw;c.strokeStyle=color;c.stroke();}
function txt(c,s,x,y,size,color=C.ink,weight=500,mono=false,track=0){c.font=`${weight} ${size}px "${mono?'RG Mono':'RG Display'}"`;c.textBaseline='top';c.fillStyle=color;c.letterSpacing=`${track}px`;c.fillText(s,x,y);}
function width(c,s,size,weight=500,mono=false){c.font=`${weight} ${size}px "${mono?'RG Mono':'RG Display'}"`;c.letterSpacing='0px';return c.measureText(s).width;}
function center(c,s,x,y,size,color=C.ink,weight=500,mono=false){txt(c,s,x-width(c,s,size,weight,mono)/2,y,size,color,weight,mono);}
function label(c,s,x,y,color=C.muted,size=18){txt(c,s,x,y,size,color,400,true,1);}
function rise(c,s,x,y,size,t,start,color=C.ink){const q=p(t,start,.8);c.save();c.beginPath();c.rect(x-12,y-5,2100,size*1.4);c.clip();txt(c,s,x,y+(1-q)*size*1.2,size,color,600,false,-size*.035);c.restore();}
function arrow(c,x,y,length,color,q=1,lw=4){line(c,x,y,x+length*q,y,color,lw);if(q>.97){line(c,x+length-15,y-11,x+length,y,color,lw);line(c,x+length-15,y+11,x+length,y,color,lw);}}
function tick(c,x,y,color,size=1){c.beginPath();c.moveTo(x-12*size,y);c.lineTo(x-3*size,y+9*size);c.lineTo(x+15*size,y-12*size);c.strokeStyle=color;c.lineWidth=4*size;c.stroke();}
function mark(c,x,y,size,color=C.blue,accent=C.citrus,q=1){
  const pts=[[.2,.16],[.61,.16],[.8,.38],[.2,.55],[.8,.84]];
  [[0,1],[1,2],[2,3],[0,3],[3,4]].forEach(([a,b],i)=>{
    const v=clamp((q-i*.08)/.56);line(c,x+pts[a][0]*size,y+pts[a][1]*size,x+lerp(pts[a][0],pts[b][0],v)*size,y+lerp(pts[a][1],pts[b][1],v)*size,color,size*.063);
  });
  pts.forEach(([a,b],i)=>circle(c,x+a*size,y+b*size,size*.055*p(q,i*.07,.5),i===4?accent:color));
}
function brand(c,x,y,size,color=C.ink,accent=C.blue){mark(c,x,y-3,size*1.15,color,accent);txt(c,'RepoGraph',x+size*1.35,y,size,color,600,false,-size*.025);}
function furniture(c,W,H,V,index,color=C.ink,accent=C.blue){
  brand(c,V?72:94,V?82:54,V?31:29,color,accent);
  label(c,'MCP + SKILL',W-(V?280:263),V?96:67,color,V?17:15);
  const y=H-(V?74:48),left=V?74:95,right=W-left;
  line(c,left,y,right,y,color,1);
  const x=lerp(left,right,(index+1)/8);circle(c,x,y,4,accent);
  label(c,index===7?'npmjs.com/package/repograph-kit':'LOCAL REPOSITORY INTELLIGENCE',left,y+17,color,V?15:13);
}

function operator(c,x,y,size,t){
  c.save();c.translate(x,y);c.rotate((1-p(t,1.8,.65))*.45);
  rect(c,-size/2,-size/2,size,size,C.blue);
  const q=p(t,2,.6),r=size*.24;
  line(c,-r,0,r,0,C.cream,size*.055);
  line(c,0,-r,0,r,C.cream,size*.055);
  group(c,1-q,()=>{
    line(c,-r*.86,-r*.5,r*.86,r*.5,C.cream,size*.055);
    line(c,-r*.86,r*.5,r*.86,-r*.5,C.cream,size*.055);
  });
  c.restore();
}
function hook(c,W,H,V,t){
  fill(c,C.citrus,W,H);furniture(c,W,H,V,0);
  label(c,'A CHANGE IN pricing.py',V?75:95,V?243:213,C.ink,V?23:20);
  rise(c,'One line.',V?72:88,V?330:280,V?171:206,t,.06,C.ink);
  const q=p(t,.65,.9),cy=V?920:465,cx=V?540:1390;
  group(c,q,()=>{
    const xx=(1-q)*170;
    txt(c,'price',V?105+xx:1070+xx,cy-26,V?43:40,C.ink,400,true);
    txt(c,'quantity',V?680+xx:1545+xx,cy-26,V?43:40,C.ink,400,true);
    operator(c,cx+xx,cy,V?170:182,t);
    label(c,t<2.15?'return price * quantity':'return price + quantity',V?220:1120,cy+155,C.ink,V?25:21);
    label(c,'CONTROLLED EXAMPLE',V?75:1070,cy-185,C.ink,V?19:16);
  });
  const ly=V?1225:655;
  line(c,V?74:95,ly,V?1008:1830,ly,C.ink,2);
  if(V){rise(c,'What else',72,1360,117,t,3.12,C.ink);rise(c,'moves?',72,1486,117,t,3.3,C.blue);}
  else{rise(c,'What else moves?',93,758,119,t,3.13,C.ink);arrow(c,1330,838,435,C.blue,p(t,3.6,1),7);}
}

function reveal(c,W,H,V,t){
  fill(c,C.blue,W,H);furniture(c,W,H,V,1,C.cream,C.citrus);
  const cx=V?540:1520,cy=V?575:500;
  const size=V?340:318;
  group(c,p(t,.1),()=>{
    c.save();c.translate(cx,cy);c.rotate(Math.sin(t*.6)*.035);c.translate(-cx,-cy);
    mark(c,cx-size/2,cy-size/2,size,C.cream,C.citrus,clamp(t/1.6));c.restore();
  });
  const yy=cy+(V?280:270),span=V?620:560,travel=((t*.24)%1);
  line(c,cx-span/2,yy,cx+span/2,yy,C.cream,2);
  circle(c,cx-span/2+travel*span,yy,9,C.citrus);
  if(V){
    rise(c,'RepoGraph.',72,1000,154,t,.3,C.cream);
    rise(c,'See the',74,1235,108,t,.9,C.cream);
    rise(c,'connections.',74,1355,108,t,1.1,C.citrus);
    label(c,'REPOSITORY INTELLIGENCE FOR YOUR AGENT',76,1582,C.cream,20);
  }else{
    rise(c,'RepoGraph.',85,360,206,t,.2,C.cream);
    rise(c,'See the connections.',96,660,72,t,1.0,C.citrus);
    label(c,'LOCAL REPOSITORY INTELLIGENCE / MCP',99,815,C.cream,22);
  }
}

function curvePoint(q,pts){const a=1-q;return [a*a*a*pts[0][0]+3*a*a*q*pts[1][0]+3*a*q*q*pts[2][0]+q*q*q*pts[3][0],a*a*a*pts[0][1]+3*a*a*q*pts[1][1]+3*a*q*q*pts[2][1]+q*q*q*pts[3][1]];}
function wire(c,pts,q,t,color=C.blue){
  c.beginPath();for(let i=0;i<=60*q;i++){const v=curvePoint(Math.min(i/60,q),pts);if(i===0)c.moveTo(...v);else c.lineTo(...v);}c.lineWidth=4;c.strokeStyle=color;c.stroke();
  if(q>.97){const v=curvePoint((t*.34)%1,pts);circle(c,...v,7,color);}
}
function graphNode(c,x,y,r,name,sub,type,q,V){
  const color=type==='source'?C.blue:type==='test'?C.citrus:C.ink;
  circle(c,x,y,r*q,color);
  group(c,q,()=>{
    if(type==='test')center(c,'T',x,y-(V?27:23),V?48:42,C.ink,500,true);
    else center(c,type==='source'?'Δ':'f',x,y-(V?36:28),V?66:52,C.cream,500);
    center(c,name,x,y+r+27,V?31:25,C.ink,400,true);
    center(c,sub,x,y+r+73,V?20:15,C.muted,400,true);
  });
}
function impact(c,W,H,V,t){
  fill(c,C.cream,W,H);furniture(c,W,H,V,2);
  const x=V?74:95;
  label(c,'INDEX → IMPACT',x,V?227:204,C.muted,V?24:20);
  rise(c,'Trace the',x,V?313:286,V?133:139,t,.06);
  rise(c,'impact.',x,V?458:439,V?133:139,t,.26,C.blue);
  group(c,p(t,.8),()=>{
    txt(c,'Potential dependents.',x,V?646:646,V?38:34,C.muted);
    txt(c,'File-and-line evidence.',x,V?700:696,V?38:34,C.muted);
  });
  const s=V?[540,950]:[1345,302],a=V?[284,1265]:[1035,619],b=V?[805,1265]:[1640,619],d=V?[284,1580]:[1035,862];
  wire(c,[[s[0]-(V?70:64),s[1]],[a[0],s[1]],[a[0],a[1]-150],[a[0],a[1]]],p(t,1.0,1),t);
  wire(c,[[s[0]+(V?70:64),s[1]],[b[0],s[1]],[b[0],b[1]-150],[b[0],b[1]]],p(t,1.3,1),t+.65);
  const side=V?110:865;
  wire(c,[[a[0]-(V?59:51),a[1]],[side,a[1]],[side,d[1]],[d[0],d[1]]],p(t,1.85,1),t+1.3);
  graphNode(c,...s,V?70:64,'pricing.py','CHANGED SOURCE','source',p(t,.3),V);
  graphNode(c,...a,V?59:51,'checkout.py','IMPORT / LINE 01','module',p(t,1.0),V);
  graphNode(c,...b,V?59:51,V?'test_pricing.py':'tests/test_pricing.py','DIRECT CONSUMER','test',p(t,1.3),V);
  graphNode(c,...d,V?49:40,V?'test_checkout.py':'tests/test_checkout.py','TRANSITIVE CONSUMER','test',p(t,1.9),V);
  group(c,p(t,2.7),()=>{
    const xx=V?635:95,yy=V?1535:819;
    txt(c,'04',xx,yy,V?100:108,C.blue,500,false,-5);
    txt(c,'source files indexed',V?xx:xx+183,V?yy+124:yy+55,V?26:26,C.ink);
  });
  label(c,'WORKFLOW VISUALIZATION',V?73:1341,V?1790:182,C.muted,V?17:15);
}

function band(c,x,y,w,h,name,sub,color,t,start,V){
  const q=p(t,start,.95),xx=x+(1-q)*350;
  rect(c,xx,y,w,h,color);
  group(c,q,()=>{
    tick(c,xx+41,y+49,color===C.blue?C.citrus:C.ink,V?1.1:.9);
    txt(c,name,xx+91,y+25,V?35:28,color===C.blue?C.cream:C.ink,400,true);
    txt(c,sub,xx+91,y+(V?100:86),V?29:24,color===C.blue?C.cream:C.ink);
  });
}
function tests(c,W,H,V,t){
  fill(c,C.ink,W,H);furniture(c,W,H,V,3,C.cream,C.citrus);
  const x=V?74:95;
  label(c,'TEST SELECTION',x,V?226:208,C.cream,V?24:20);
  rise(c,'Choose tests',x,V?311:290,V?112:117,t,.05,C.cream);
  rise(c,'with evidence.',x,V?437:420,V?112:117,t,.23,C.citrus);
  const bx=V?72:1056,by=V?1060:314,bw=V?936:776;
  band(c,bx,by,bw,V?178:148,'tests/test_pricing.py','Direct dependency',C.citrus,t,1.05,V);
  band(c,bx,by+(V?226:222),bw,V?178:148,'tests/test_checkout.py','Transitive dependency',C.blue,t,1.4,V);
  group(c,p(t,1.0),()=>{
    txt(c,String(Math.floor(2*clamp((t-1)/.5))).padStart(2,'0'),x,V?745:703,V?186:185,C.citrus,500,false,-6);
    txt(c,'suggested tests',V?360:386,V?859:817,V?37:35,C.cream);
  });
  group(c,p(t,2.25),()=>{
    const yy=V?1570:815,xx=V?73:1056;
    line(c,xx,yy,xx+bw,yy,C.cream,1);
    circle(c,xx+((t-2.25)*.25%1)*bw,yy,5,C.citrus);
    label(c,V?'pricing.py → checkout.py → test_checkout.py':'pricing.py → checkout.py → tests/test_checkout.py',xx,yy+37,C.cream,V?20:17);
    txt(c,'Broader checks when coverage is uncertain.',xx,yy+99,V?28:25,C.cream);
  });
  label(c,'WORKFLOW VISUALIZATION',V?74:1056,V?986:229,C.cream,V?17:15);
}

function gate(c,x,y,w,t,V){
  const pivot=x+w*.53,rail=y+153,q=p(t,3.0,.6);
  line(c,x,rail,x+w,rail,C.blue,5);
  const ang=q*Math.PI/2;
  line(c,pivot,y,pivot+Math.sin(ang)*252,y+Math.cos(ang)*252,C.ink,12);
  circle(c,pivot,y,13,C.ink);
  let sx;
  if(t<2.2)sx=lerp(x+20,pivot-67,p(t,.8,1.4));
  else sx=lerp(pivot-67,x+w-30,p(t,3.1,1.0));
  circle(c,sx,rail,29,C.blue);
  if(q>.93){circle(c,pivot-11,y-56,24,C.blue);tick(c,pivot-11,y-56,C.citrus,.8);}
  label(c,q>.93?'APPROVED':'REVIEWED PLAN',x,y-85,C.ink,V?25:21);
}
function control(c,W,H,V,t){
  fill(c,C.cream,W,H);furniture(c,W,H,V,4);
  const x=V?74:95;
  label(c,'REVIEWED VERIFICATION',x,V?231:204,C.muted,V?22:20);
  rise(c,'You approve.',x,V?318:302,V?112:120,t,.05);
  rise(c,'Then it runs.',x,V?446:438,V?112:120,t,.24,C.blue);
  gate(c,V?102:1056,V?867:380,V?872:728,t,V);
  group(c,p(t,4.1,.7),()=>{
    const yy=V?1250:785,xx=V?73:1055,ww=V?935:774;
    rect(c,xx,yy,ww*.49,V?165:137,C.mint);
    rect(c,xx+ww*.51,yy,ww*.49,V?165:137,C.coral);
    label(c,'BASELINE',xx+23,yy+18,C.ink,V?20:16);
    label(c,'CHANGED RUN',xx+ww*.51+23,yy+18,C.ink,V?20:16);
    txt(c,`${DATA.baseline_passed} passed`,xx+23,yy+66,V?54:46,C.ink);
    txt(c,`${DATA.changed_failed} failed`,xx+ww*.51+23,yy+66,V?54:46,C.ink);
    txt(c,`${DATA.potential_regressions} potential regressions`,xx,yy+(V?206:160),V?44:35,C.ink,600);
  });
  const fy=V?1658:774,fw=V?900:790;
  ['Prepare','Review','Approve'].forEach((s,i)=>{
    const xx=x+i*fw/3,q=p(t,.5+i*.9);
    circle(c,xx+23,fy+23,23,q>.97?C.blue:C.line);
    if(q>.97)tick(c,xx+23,fy+23,C.cream,.8);
    txt(c,s,xx-8,fy+75,V?32:28,C.ink);
    if(i<2)arrow(c,xx+62,fy+23,fw/3-111,C.blue,q,2);
  });
  label(c,'CONTROLLED EXAMPLE / INJECTED DEFECT',V?74:1056,V?1545:988,C.muted,V?18:13);
  if(!V)txt(c,'Host opt-in + approval of a reviewed plan.',x,946,23,C.muted);
  else label(c,'HOST OPT-IN + REVIEWED APPROVAL',74,1810,C.muted,18);
}

function mechanism(c,x,y,r,t){
  const q=p(t,.65,2.7),size=r*1.7;
  const pts=[[.2,.16],[.61,.16],[.8,.38],[.2,.55],[.8,.84]];
  const pairs=[[0,1],[1,2],[2,3],[0,3],[3,4]];
  pairs.forEach(([a,b],i)=>{
    const yy=y-r*.67+i*r*.34;
    const ax=lerp(x-r*.81,x-size/2+pts[a][0]*size,q),ay=lerp(yy,y-size/2+pts[a][1]*size,q);
    const bx=lerp(x+r*.81,x-size/2+pts[b][0]*size,q),by=lerp(yy,y-size/2+pts[b][1]*size,q);
    line(c,ax,ay,bx,by,i===4?C.citrus:C.cream,20);
    circle(c,ax,ay,16,i===4?C.citrus:C.cream);circle(c,bx,by,16,i===4?C.citrus:C.cream);
    const travel=(t*.38+i*.17)%1;
    circle(c,lerp(ax,bx,travel),lerp(ay,by,travel),7,C.blue);
  });
}
function local(c,W,H,V,t){
  fill(c,C.blue,W,H);furniture(c,W,H,V,5,C.cream,C.citrus);
  const x=V?76:925;
  label(c,'THE ANALYSIS ENGINE',x,V?235:215,C.cream,V?24:20);
  rise(c,'Local analysis.',x,V?330:312,V?112:110,t,.04,C.cream);
  rise(c,V?'For your':'For your agent.',x,V?464:436,V?112:110,t,.25,C.citrus);
  if(V)rise(c,'agent.',x,596,112,t,.43,C.citrus);
  group(c,p(t,.8),()=>{
    txt(c,'No LLM API key',x,V?813:661,V?41:42,C.cream);
    txt(c,'for the RepoGraph engine.',x,V?872:722,V?34:32,C.cream);
  });
  group(c,p(t,.35),()=>mechanism(c,V?540:452,V?1318:553,V?310:308,t));
  const yy=V?1730:930;
  const phrase='PYTHON / JAVASCRIPT / TYPESCRIPT / ';
  const step=width(c,phrase,V?26:25,400,true)+25;
  c.save();c.beginPath();c.rect(V?72:94,yy-12,W-(V?144:188),60);c.clip();
  for(let i=-1;i<5;i++)txt(c,phrase,(V?72:94)+i*step-((t*34)%step),yy,V?26:25,C.cream,400,true,1);
  c.restore();
}

function skillGlyph(c,x,y,size,t){
  for(let i=0;i<3;i++){
    const q=p(t,.2+i*.12,.8),yy=y+i*size*.28;
    circle(c,x,yy+size*.035,size*.035,C.ink);
    rect(c,x+size*.15,yy,size*(i===2?.53:.75)*q,size*.07,C.ink);
  }
  arrow(c,x+size*.15,y+size*.91,size*.75,C.ink,p(t,.8),size*.025);
}
function pair(c,W,H,V,t){
  fill(c,C.ink,W,H);
  const split=V?700:0,cy=V?850:300;
  rect(c,W*.5,split,W*.5,H-split,C.citrus);
  if(V)rect(c,0,split,W*.5,810,C.blue);
  brand(c,V?72:94,V?82:54,V?31:29,C.cream,C.citrus);
  label(c,'MCP + SKILL',W-(V?280:263),V?96:67,V?C.cream:C.ink,V?17:15);
  if(V){rise(c,'Two ways in.',74,315,127,t,.07,C.cream);txt(c,'One connected workflow.',78,512,39,C.cream);}
  else{label(c,'TOOLS FOR YOUR AGENT',95,215,C.cream,21);label(c,'GUIDANCE FOR THE WORKFLOW',W*.5+100,215,C.ink,21);}
  const lx=V?112:178,rx=V?650:1150;
  rise(c,'MCP',lx,cy,V?116:168,t,.18,C.cream);
  rise(c,'Skill',rx,cy,V?116:168,t,.37,C.ink);
  group(c,p(t,.65),()=>{
    const sz=V?240:243;
    mark(c,lx+5,cy+(V?236:242),sz,C.citrus,C.cream);
    skillGlyph(c,rx+30,cy+(V?245:256),sz,t);
  });
  const py=V?1520:824;
  rect(c,0,py,W,V?400:256,V?C.ink:C.blue);
  group(c,p(t,2.1),()=>{
    txt(c,'26',V?74:95,py+(V?34:26),V?154:133,C.citrus,500,false,0);
    txt(c,'CI jobs passed',V?340:344,py+(V?116:94),V?35:33,C.cream);
    txt(c,'Linux / macOS / Windows',V?74:1040,py+(V?257:57),V?29:33,C.cream);
    label(c,'RELEASE INSTALL + PROTOCOL CHECKS · NODE 22 / 24',V?74:1040,py+(V?316:121),C.cream,V?15:16);
  });
}

function cta(c,W,H,V,t){
  fill(c,C.citrus,W,H);furniture(c,W,H,V,7);
  const x=V?74:95;
  if(V){rise(c,'Know the',x,300,133,t,.05);rise(c,'impact.',x,449,133,t,.22,C.blue);rise(c,'Make your',x,714,101,t,.65);rise(c,'next move.',x,831,101,t,.83);}
  else{rise(c,'Know the impact.',x,235,150,t,.05);rise(c,'Make your next move.',x,413,120,t,.28);group(c,p(t,.7),()=>mark(c,1538,258,247,C.blue,C.ink));}
  const yy=V?1150:669,ww=V?932:1240,hh=V?116:92;
  group(c,p(t,1.1),()=>{
    rect(c,x,yy,ww,hh,C.blue);rect(c,x,yy+hh+20,ww,hh,C.ink);
    const a='npm i repograph-kit',b='npx repograph-kit setup';
    txt(c,a.slice(0,Math.floor(clamp((t-1.25)/.85)*a.length)),x+28,yy+25,V?43:43,C.cream,400,true);
    txt(c,b.slice(0,Math.floor(clamp((t-2.2)/1.0)*b.length)),x+28,yy+hh+45,V?43:43,C.citrus,400,true);
  });
  group(c,p(t,1.8),()=>{
    txt(c,'Node 22+ · uv or Python 3.11–3.13',x,V?1518:931,V?25:23,C.ink);
    if(V)brand(c,x,1674,68,C.ink,C.blue);
    else arrow(c,1450,yy+101,289,C.blue,p(t,2.1),6);
  });
}

const scenes=[
  {a:0,b:6,fn:hook},{a:6,b:12,fn:reveal},{a:12,b:20,fn:impact},{a:20,b:28,fn:tests},
  {a:28,b:36,fn:control},{a:36,b:44,fn:local},{a:44,b:50,fn:pair},{a:50,b:60,fn:cta},
];
export function drawFrame(c,width,height,time){
  const V=height>width,W=V?1080:1920,H=V?1920:1080,t=Math.min(DURATION-1/FPS,Math.max(0,time));
  const index=scenes.findIndex(s=>t>=s.a&&t<s.b),s=scenes[index];
  c.save();c.scale(width/W,height/H);c.lineCap='round';c.lineJoin='round';
  s.fn(c,W,H,V,t-s.a);
  if(index<scenes.length-1&&t>s.b-.6){
    const q=smooth((t-(s.b-.6))/.6);
    c.save();c.beginPath();
    if(index===0||index===4||index===6){
      const center=index===0?(V?[540,920]:[1390,465]):index===4?(V?[880,1020]:[1730,533]):[W*.5,H*.55];
      c.arc(center[0],center[1],Math.hypot(W,H)*q,0,Math.PI*2);
    }else if(index===1||index===3){
      const offset=W*(1-q);c.moveTo(offset+250,0);c.lineTo(W+250,0);c.lineTo(W+250,H);c.lineTo(offset-250,H);c.closePath();
    }else if(index===2)c.rect(0,H*(1-q),W,H);
    else c.rect(W*(1-q),0,W,H);
    c.clip();scenes[index+1].fn(c,W,H,V,0);c.restore();
  }
  c.restore();
}
