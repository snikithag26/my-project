/* Live tab: face recognition (enrol + identify) and expression evaluation with face-api.js, all in the browser. */
const EM={neutral:['😐','Neutral','#7f9a9c'],happy:['😄','Happy','#3fa56b'],surprised:['😮','Surprised','#e0a030'],sad:['😢','Sad','#4f7fd1'],angry:['😠','Angry','#d1514a'],fearful:['😨','Fearful','#8f63c9'],disgusted:['🤢','Disgusted','#8a9a3a']};
const KEYS=Object.keys(EM);
$('bars').innerHTML=KEYS.map(k=>`<div class="row"><span>${EM[k][1]}</span><div class="track"><i id="b_${k}" style="width:0;background:${EM[k][2]}"></i></div><span id="n_${k}">0%</span></div>`).join('');
$('leg').innerHTML=KEYS.map(k=>`<span><span style="color:${EM[k][2]}">●</span> ${EM[k][1]}</span>`).join('');
const vid=$('vid'),ov=$('ov');
let loaded=false,running=false,stream=null,buf=[],log=[],t0=0,bad=0,tickN=0,enrolling=null,streak=0,lastId=null;
const say=(t,warn)=>{$('status').textContent=t;$('status').style.color=warn?'var(--warn)':'var(--good)'};
const OPT=()=>new faceapi.TinyFaceDetectorOptions({inputSize:224,scoreThreshold:.5});
async function loadModels(){
 if(loaded)return true;
 if(typeof faceapi==='undefined'){say('The face-api library did not load. Check your internet connection and reopen the page.',1);return false}
 say('Loading models (first time only)…',0);
 try{const u='https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model/';
  await Promise.all([faceapi.nets.tinyFaceDetector.loadFromUri(u),faceapi.nets.faceExpressionNet.loadFromUri(u),faceapi.nets.faceLandmark68TinyNet.loadFromUri(u),faceapi.nets.faceRecognitionNet.loadFromUri(u)]);loaded=true;return true}
 catch(e){say('Could not load the model files. This page needs internet the first time.',1);return false}
}
function noFace(){const o=ov.getContext('2d');o.clearRect(0,0,ov.width,ov.height);$('emo').textContent='🫥';$('dom').textContent='No face found';$('conf').textContent='Face the camera in good light';KEYS.forEach(k=>{$('b_'+k).style.width='0';$('n_'+k).textContent='0%'})}
function show(ex,box){
 const o=ov.getContext('2d');ov.width=vid.videoWidth;ov.height=vid.videoHeight;o.clearRect(0,0,ov.width,ov.height);
 buf.push(ex);if(buf.length>5)buf.shift();
 const s={};KEYS.forEach(k=>s[k]=buf.reduce((a,b)=>a+b[k],0)/buf.length);
 const dm=KEYS.reduce((a,b)=>s[a]>=s[b]?a:b);
 KEYS.forEach(k=>{$('b_'+k).style.width=(s[k]*100)+'%';$('n_'+k).textContent=Math.round(s[k]*100)+'%'});
 $('emo').textContent=EM[dm][0];$('dom').textContent=EM[dm][1];$('conf').textContent='Confidence '+Math.round(s[dm]*100)+'%';
 o.strokeStyle=EM[dm][2];o.lineWidth=3;o.strokeRect(box.x,box.y,box.width,box.height);tip(dm,s[dm]);return dm;
}
function tip(d,c){
 const h=P().helps,t=$('tip');bad=(['sad','angry','fearful','disgusted'].includes(d)&&c>.5)?bad+1:0;
 const msg={happy:'A good moment for a learning activity or social practice.',neutral:'Calm and steady. Keep the routine going.',surprised:'Check for a sudden change or noise. Give a warning before what comes next.'}[d];
 if(bad>=3){t.className='tip alert';t.textContent='Possible distress ('+EM[d][1].toLowerCase()+') for '+P().name+'. Try: '+(h[0]||'a quiet break')+(h[1]?'; '+h[1]:'')+'.'}
 else{t.className='tip';t.textContent=msg||'Mild negative expression. Keep watching and check in gently.'}
}
function identify(d){
 let best={dist:9,p:null};
 people.forEach(p=>p.faces.forEach(f=>{const x=faceapi.euclideanDistance(d,f);if(x<best.dist)best={dist:x,p}}));
 const w=$('who');
 if(best.p&&best.dist<0.5){const pc=Math.round(Math.max(0,1-best.dist/0.6)*100);w.className='who';w.textContent='Recognised: '+best.p.name+' ('+pc+'% match)';
  streak=best.p.id===lastId?streak+1:1;lastId=best.p.id;
  if(streak>=2&&cur!==best.p.id&&!editing){cur=best.p.id;drawAll()}}
 else{w.className='who unk';w.textContent='Unknown face (no enrolled match)';streak=0;lastId=null}
}
async function tick(){
 if(!running)return;tickN++;
 const need=!!enrolling||(tickN%4===0&&people.some(p=>p.faces.length));
 if(vid.readyState>=2){
  try{
   let q=faceapi.detectSingleFace(vid,OPT()),r;
   r=need?await q.withFaceLandmarks(true).withFaceExpressions().withFaceDescriptor():await q.withFaceExpressions();
   if(!r)noFace();else{const d=show(r.expressions,r.detection.box);log.push(d);
    if(r.descriptor){if(enrolling){enrolling.push(Array.from(r.descriptor));say('Hold still… captured '+enrolling.length+' of 6',0);
      if(enrolling.length>=6){P().faces=enrolling;enrolling=null;save();drawAll();say('Face enrolled for '+P().name+'.',0)}}
      else identify(r.descriptor)}}
  }catch(e){}
  $('strip').innerHTML=log.slice(-150).map(k=>`<span style="background:${EM[k][2]}"></span>`).join('');
 }
 setTimeout(tick,160);
}
$('start').onclick=async()=>{
 if(!await loadModels())return;
 try{stream=await navigator.mediaDevices.getUserMedia({video:{width:640,height:480,facingMode:'user'}})}
 catch(e){say('Camera blocked or not found. Allow camera access and try again.',1);return}
 vid.srcObject=stream;await vid.play();$('ph').style.display='none';buf=[];log=[];bad=0;tickN=0;streak=0;lastId=null;t0=Date.now();running=true;
 $('start').disabled=true;$('stop').disabled=false;$('enroll').disabled=false;$('sum').textContent='';$('who').textContent='Identity: looking for a face…';say('Analysing live. Everything stays on this device.',0);tick();
};
$('enroll').onclick=()=>{if(!$('consent').checked){say('Tick the consent box first.',1);return}enrolling=[];say('Look at the camera… capturing samples for '+P().name,0)};
$('stop').onclick=()=>{
 running=false;enrolling=null;if(stream){stream.getTracks().forEach(t=>t.stop());stream=null}vid.srcObject=null;
 $('start').disabled=false;$('stop').disabled=true;$('enroll').disabled=true;$('ph').style.display='';ov.getContext('2d').clearRect(0,0,ov.width,ov.height);$('who').className='who unk';$('who').textContent='Identity: camera off';
 if(log.length<5){say('Session ended. Too short to summarise.',1);return}
 const c={};log.forEach(k=>c[k]=(c[k]||0)+1);
 const parts=Object.entries(c).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`${EM[k][1]} ${Math.round(v/log.length*100)}%`),secs=Math.round((Date.now()-t0)/1000);
 $('sum').innerHTML='<b>Session summary for '+esc(P().name)+'</b> ('+secs+' s): '+parts.join(', ');
 const dist={};KEYS.forEach(k=>dist[k]=+((c[k]||0)/log.length).toFixed(3));const step=Math.max(1,Math.ceil(log.length/120));
 P().sessions.unshift({at:new Date().toISOString(),secs,parts:parts.join(', '),dist,timeline:log.filter((_,j)=>j%step===0)});save();drawH();say('Session saved.',0);
};