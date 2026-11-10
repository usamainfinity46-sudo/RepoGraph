import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import crypto from 'node:crypto';
import { createCanvas, loadImage } from '@napi-rs/canvas';
import { drawFrame, DURATION, FPS, C } from './film.mjs';

const ROOT=path.dirname(fileURLToPath(import.meta.url));
const PROJECT=path.resolve(ROOT,'../..');
const {values}=parseArgs({options:{
  stills:{type:'boolean'},format:{type:'string',default:'both'},
  width:{type:'string'},height:{type:'string'},fps:{type:'string'},
  ffmpeg:{type:'string'},output:{type:'string'},duration:{type:'string'},
}});
const OUT=path.resolve(values.output||path.join(PROJECT,'dist/marketing'));
fs.mkdirSync(OUT,{recursive:true});
const formats=values.format==='both'?['landscape','portrait']:[values.format];
if(formats.some(f=>!['landscape','portrait'].includes(f)))throw new Error('Use landscape, portrait or both');
const times=[3.85,9.25,16.5,24.5,33.6,40.5,47.8,56.5];

async function stills(format){
  const width=format==='landscape'?1920:1080,height=format==='landscape'?1080:1920;
  const canvas=createCanvas(width,height),ctx=canvas.getContext('2d');
  const folder=path.join(OUT,`stills-${format}`);fs.mkdirSync(folder,{recursive:true});
  const images=[];
  for(let i=0;i<times.length;i++){
    drawFrame(ctx,width,height,times[i]);
    const file=path.join(folder,`${String(i+1).padStart(2,'0')}-${times[i]}.png`);
    fs.writeFileSync(file,canvas.toBuffer('image/png'));images.push(file);
  }
  const thumbW=format==='landscape'?800:360,thumbH=thumbW*height/width;
  const cols=format==='landscape'?2:4,rows=Math.ceil(images.length/cols),gap=20,caption=35;
  const sheet=createCanvas(cols*(thumbW+gap)+gap,rows*(thumbH+caption+gap)+gap);
  const sc=sheet.getContext('2d');sc.fillStyle='#D7DDD8';sc.fillRect(0,0,sheet.width,sheet.height);
  for(let i=0;i<images.length;i++){
    const x=gap+(i%cols)*(thumbW+gap),y=gap+Math.floor(i/cols)*(thumbH+caption+gap);
    sc.drawImage(await loadImage(images[i]),x,y,thumbW,thumbH);
    sc.fillStyle=C.ink;sc.font='500 17px "RG Mono"';sc.fillText(`${String(i+1).padStart(2,'0')} / ${times[i].toFixed(2)}s`,x,y+thumbH+24);
  }
  const sheetFile=path.join(OUT,`contact-${format}.png`);fs.writeFileSync(sheetFile,sheet.toBuffer('image/png'));
  drawFrame(ctx,width,height,9.25);
  fs.writeFileSync(path.join(OUT,`RepoGraph-Cover-${format}.png`),canvas.toBuffer('image/png'));
  // A separate strip checks the reveal and handoff at a scene boundary.
  const strip=createCanvas(1600,format==='landscape'?280:745),st=strip.getContext('2d');
  for(let i=0;i<5;i++){
    drawFrame(ctx,width,height,5.35+i*.19);
    st.drawImage(canvas,i*320,0,320,320*height/width);
  }
  fs.writeFileSync(path.join(OUT,`transition-${format}.png`),strip.toBuffer('image/png'));
  console.log(JSON.stringify({mode:'stills',format,contact:sheetFile}));
}

async function render(format){
  const width=Number(values.width||(format==='landscape'?3840:1080));
  const height=Number(values.height||(format==='landscape'?2160:1920));
  const fps=Number(values.fps||FPS),duration=Number(values.duration||DURATION);
  const ffmpeg=values.ffmpeg||process.env.FFMPEG;
  if(!ffmpeg||!fs.existsSync(ffmpeg))throw new Error('Provide --ffmpeg PATH or FFMPEG pointing to the installed FFmpeg');
  const score=path.join(OUT,'score.wav');
  if(!fs.existsSync(score))throw new Error('Create score.wav with soundtrack.py first');
  const suffix=width>=3840?'4k':format==='portrait'?'vertical':height>=1080?'1080p':`${height}p-preview`;
  const target=path.join(OUT,`RepoGraph-Brand-Film-${suffix}.mp4`);
  const args=['-hide_banner','-loglevel','warning','-y','-f','rawvideo','-pixel_format','rgba',
    '-video_size',`${width}x${height}`,'-framerate',String(fps),'-i','pipe:0','-i',score,
    '-map','0:v:0','-map','1:a:0','-t',String(duration),'-c:v','libx264','-preset','medium',
    '-crf','17','-vf','scale=in_range=full:out_range=tv:out_color_matrix=bt709',
    '-pix_fmt','yuv420p','-profile:v','high','-color_primaries','bt709',
    '-color_trc','bt709','-colorspace','bt709','-threads','6',
    '-c:a','aac','-b:a','256k','-ar','48000','-af','loudnorm=I=-16:TP=-1.5:LRA=7',
    '-movflags','+faststart','-metadata','title=RepoGraph — One line changes',
    '-metadata','comment=Original motion design and music. Workflow visualizations use a controlled RepoGraph example.',target];
  const encoder=spawn(ffmpeg,args,{stdio:['pipe','ignore','pipe'],windowsHide:true});
  let errors='';encoder.stderr.on('data',chunk=>{errors=(errors+chunk.toString()).slice(-12000);});
  let inputError=null;encoder.stdin.on('error',error=>{inputError=error;});
  const completion=new Promise((resolve,reject)=>{
    encoder.once('error',reject);encoder.once('close',code=>code===0?resolve():reject(new Error(errors||`FFmpeg exited ${code}`)));
  });
  // Attach a rejection handler immediately; a full render can take several minutes.
  completion.catch(()=>{});
  const canvas=createCanvas(width,height),ctx=canvas.getContext('2d');
  const frames=Math.round(duration*fps),start=Date.now();
  for(let frame=0;frame<frames;frame++){
    if(inputError)throw inputError;
    drawFrame(ctx,width,height,frame/fps);
    const data=ctx.getImageData(0,0,width,height).data;
    const buffer=Buffer.from(data.buffer,data.byteOffset,data.byteLength);
    if(!encoder.stdin.write(buffer))await once(encoder.stdin,'drain');
    if(frame%120===0){
      const elapsed=(Date.now()-start)/1000;
      console.log(JSON.stringify({format,frame,total:frames,percent:Math.round(frame/frames*100),elapsed:Math.round(elapsed),renderFps:frame?Number((frame/elapsed).toFixed(1)):0}));
    }
  }
  encoder.stdin.end();await completion;
  const receipt={status:'rendered',format,width,height,fps,duration,seconds:Math.round((Date.now()-start)/1000),file:target,bytes:fs.statSync(target).size,
    sha256:crypto.createHash('sha256').update(fs.readFileSync(target)).digest('hex')};
  fs.writeFileSync(path.join(OUT,`render-${suffix}.json`),JSON.stringify(receipt,null,2));
  console.log(JSON.stringify(receipt));
}

for(const format of formats){if(values.stills)await stills(format);else await render(format);}
