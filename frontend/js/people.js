/* People tab: profile view/edit, person picker. Extracted state (people, cur, editing) lives in app.js. */
const PAIRS=[['details','Personal details']];
function drawP(){
 const p=P(),ini=(p.name.split(/\s+/).map(w=>w[0]||'').join('').slice(0,2)||'?').toUpperCase();
 $('pick').innerHTML=people.map(x=>`<option value="${x.id}"${x.id===p.id?' selected':''}>${esc(x.name)}${x.faces.length?' 👤':''}</option>`).join('');
 let h=`<div class="bar"><span></span><span>${editing?'<button class="btn" id="cx">Cancel</button> ':''}<button class="btn pri" id="ed">${editing?'Save profile':'Edit profile'}</button></span></div><section class="card head"><div class="avatar" aria-hidden="true">${esc(ini)}</div><div style="flex:1;min-width:240px">`;
 h+=editing?`<input type="text" id="f_name" value="${esc(p.name)}" aria-label="Name"><div class="grid" style="margin-top:8px;gap:8px"><input type="text" id="f_age" value="${esc(p.age)}" aria-label="Age" placeholder="Age"><input type="text" id="f_gender" value="${esc(p.gender)}" aria-label="Gender" placeholder="Gender"><input type="text" id="f_city" value="${esc(p.city)}" aria-label="City" placeholder="City"></div><input type="text" id="f_tags" style="margin-top:8px" value="${esc(p.tags.join(', '))}" aria-label="Tags, comma separated" placeholder="Tags, comma separated">`
  :`<h1>${esc(p.name)}</h1><div>Age ${esc(p.age||'–')} · ${esc(p.gender||'–')} · ${esc(p.city||'–')}</div><div class="tags">${p.tags.map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>`;
 h+='</div></section><div class="grid">';
 PAIRS.forEach(([k,t])=>{h+=`<section class="card"><h2>${t}</h2><dl>${p[k].map((r,i)=>`<dt>${r[0]}</dt><dd>${editing?`<input type="text" data-k="${k}" data-i="${i}" value="${esc(r[1])}" aria-label="${r[0]}">`:esc(r[1]||'–')}</dd>`).join('')}</dl></section>`});
 h+=`<section class="card"><h2>Face recognition</h2><p>${p.faces.length?`Enrolled (${p.faces.length} samples). This person can be recognised on the Live tab.`:'Not enrolled yet. Open the Live tab, start the camera and press “Enroll face”.'}</p>${p.faces.length?'<button class="btn" id="rmf">Remove face data</button>':''}</section></div>`;
 h+='<section class="card" style="margin-top:16px"><h2>Saved sessions</h2><div id="sess"></div></section>';$('p0').innerHTML=h;drawSessions();
 $('ed').onclick=()=>{if(editing){p.name=$('f_name').value.trim()||p.name;p.age=$('f_age').value;p.gender=$('f_gender').value;p.city=$('f_city').value;p.tags=$('f_tags').value.split(',').map(s=>s.trim()).filter(Boolean);
  document.querySelectorAll('[data-k]').forEach(i=>p[i.dataset.k][+i.dataset.i][1]=i.value);
  document.querySelectorAll('[data-l]').forEach(i=>p[i.dataset.l]=i.value.split('\n').map(s=>s.trim()).filter(Boolean));save()}editing=!editing;drawAll()};
 if(editing)$('cx').onclick=()=>{editing=false;drawAll()};
 if(p.faces.length)$('rmf').onclick=()=>{p.faces=[];save();drawAll()};
}
/* ---------- Saved sessions (Profile tab) + analysis page ---------- */
const POS=['happy'],DIS=['sad','angry','fearful','disgusted'];
const sum=(d,ks)=>ks.reduce((a,k)=>a+(d[k]||0),0);
const fmtDate=at=>new Date(at).toLocaleString('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
const fmtDur=s=>{const m=Math.floor(s/60);return m?m+' min '+(s%60)+' s':s+' s'};
function sessDist(s){ /* old sessions only saved a text summary, so rebuild numbers from it */
 if(s.dist)return s.dist;
 const d={};KEYS.forEach(k=>d[k]=0);
 (s.parts||'').split(',').forEach(x=>{const m=x.trim().match(/^(\w+)\s+(\d+)%$/);if(!m)return;const k=KEYS.find(k=>EM[k][1]===m[1]);if(k)d[k]=m[2]/100});
 return d;
}
function drawSessions(){
 const el=$('sess');if(!el)return;
 const s=P().sessions;
 el.innerHTML=s.length?s.map((h,i)=>`<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:10px 0;border-top:1px solid var(--line)"><div style="flex:1;min-width:200px"><b>${fmtDate(h.at)}</b> · ${fmtDur(h.secs)}<div class="hint">${esc(h.parts)}</div></div><button class="btn" data-an="${i}">Analyse</button></div>`).join(''):'<p class="hint">No sessions yet. Start the camera on the Live tab, then press Stop to save a session.</p>';
 el.querySelectorAll('[data-an]').forEach(b=>b.onclick=()=>analyse(+b.dataset.an));
}
function drawH(){ /* the list now lives on the Profile tab */
 $('hh').textContent='Saved sessions are on the Profile tab';$('hist').style.display='none';drawSessions();
}
function lineSvg(series,first,last,hi){
 const W=560,H=200,pd=30,n=Math.max(...series.map(s=>s.v.length));
 const x=i=>pd+i*(W-2*pd)/Math.max(1,n-1),y=v=>H-pd-v*(H-2*pd)/100;
 let g=[0,25,50,75,100].map(v=>`<line x1="${pd}" x2="${W-pd}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="0" y="${y(v)+4}" font-size="11" fill="currentColor">${v}%</text>`).join('');
 series.forEach(s=>{
  g+=`<polyline fill="none" stroke="${s.c}" stroke-width="3" stroke-linejoin="round" points="${s.v.map((v,i)=>x(i)+','+y(v)).join(' ')}"/>`;
  if(n<=20)g+=s.v.map((v,i)=>`<circle cx="${x(i)}" cy="${y(v)}" r="${i===hi?8:4}" fill="${s.c}"${i===hi?' stroke="currentColor" stroke-width="2"':''}/>`).join('');
 });
 g+=`<text x="${pd}" y="${H-6}" font-size="11" fill="currentColor">${first}</text><text x="${W-pd}" y="${H-6}" font-size="11" text-anchor="end" fill="currentColor">${last}</text>`;
 return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Line chart">${g}</svg><div class="hint"><span style="color:var(--good)">●</span> Positive (happy) &nbsp; <span style="color:var(--warn)">●</span> Distress (sad, angry, fearful, disgusted)</div>`;
}
function rolling(tl,ks){
 const n=tl.length,w=Math.max(3,Math.round(n/10));
 return tl.map((_,j)=>{const seg=tl.slice(Math.max(0,j-w),Math.min(n,j+w+1));return seg.filter(k=>ks.includes(k)).length/seg.length*100});
}
function stat(label,val,prev,goodUp,note){
 let dh='<div class="hint">No earlier session to compare</div>';
 if(prev!=null){const d=Math.round(val-prev),c=d===0?'inherit':((goodUp?d>0:d<0)?'var(--good)':'var(--warn)');
  dh=`<div style="color:${c};font-weight:600">${d>0?'▲ +':d<0?'▼ ':'● '}${d} points vs previous</div>`}
 return `<div class="card" style="flex:1;min-width:170px"><div class="hint">${label}</div><div style="font-size:2rem;font-weight:700">${Math.round(val)}%</div>${dh}${note?`<div class="hint">${note}</div>`:''}</div>`;
}
function analyse(i){
 const p=P(),s=p.sessions[i],prev=p.sessions[i+1],d=sessDist(s),pd=prev?sessDist(prev):null;
 const pos=sum(d,POS)*100,dis=sum(d,DIS)*100,calm=(d.neutral||0)*100;
 const ppos=pd?sum(pd,POS)*100:null,pdis=pd?sum(pd,DIS)*100:null,pcalm=pd?(pd.neutral||0)*100:null;
 let verdict='This is the first saved session, so there is nothing to compare with yet.';
 if(pd){const diff=(pos-dis)-(ppos-pdis);
  verdict=diff>5?'Better than the previous session: more positive and/or less distress.':diff<-5?'A harder session than the previous one: more distress and/or less positive expression. Worth checking what was different that day.':'Similar to the previous session.';
  verdict+=' (compared with '+fmtDate(prev.at)+')'}
 const bars=KEYS.map(k=>{const a=(d[k]||0)*100,b=pd?(pd[k]||0)*100:0;
  return `<div style="margin:8px 0"><div style="display:flex;justify-content:space-between"><span>${EM[k][0]} ${EM[k][1]}</span><span>${Math.round(a)}%${pd?` <span class="hint">(before: ${Math.round(b)}%)</span>`:''}</span></div>
  <div style="height:10px;border-radius:5px;background:var(--line);overflow:hidden"><i style="display:block;height:100%;width:${a}%;background:${EM[k][2]}"></i></div>
  ${pd?`<div style="height:6px;margin-top:3px;border-radius:3px;background:var(--line);overflow:hidden"><i style="display:block;height:100%;width:${b}%;background:${EM[k][2]};opacity:.4"></i></div>`:''}</div>`}).join('');
 const tl=s.timeline||[];
 const timeline=tl.length>=2?`<div style="display:flex;height:18px;border-radius:4px;overflow:hidden;margin-bottom:10px">${tl.map(k=>`<span style="flex:1;background:${EM[k][2]}"></span>`).join('')}</div>`+lineSvg([{c:'var(--good)',v:rolling(tl,POS)},{c:'var(--warn)',v:rolling(tl,DIS)}],'Start','End ('+fmtDur(s.secs)+')')
  :'<p class="hint">The minute-by-minute view is only available for sessions recorded after this update.</p>';
 const all=p.sessions.slice().reverse(),cs=all.length-1-i;
 const trend=all.length>=2?lineSvg([{c:'var(--good)',v:all.map(x=>sum(sessDist(x),POS)*100)},{c:'var(--warn)',v:all.map(x=>sum(sessDist(x),DIS)*100)}],fmtDate(all[0].at).slice(0,6),fmtDate(all[all.length-1].at).slice(0,6),cs)
  :'<p class="hint">The trend appears once there are two or more saved sessions.</p>';
 $('p0').innerHTML=`<div class="bar"><span></span><button class="btn" id="an_back">← Back to profile</button></div>
 <section class="card"><h2>Session analysis · ${esc(p.name)}</h2><div><b>${fmtDate(s.at)}</b> · ${fmtDur(s.secs)}</div><p style="margin-top:8px">${esc(verdict)}</p></section>
 <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:16px">${stat('Positive (happy)',pos,ppos,true)}${stat('Calm (neutral)',calm,pcalm,true)}${stat('Distress',dis,pdis,false,'sad, angry, fearful, disgusted')}</div>
 <div class="grid" style="margin-top:16px"><section class="card"><h2>Expression mix${pd?' vs previous':''}</h2>${bars}${pd?'<p class="hint">Faded bar = previous session.</p>':''}</section>
 <section class="card"><h2>During this session</h2>${timeline}</section></div>
 <section class="card" style="margin-top:16px"><h2>Progress over all sessions</h2>${trend}<p class="hint">The larger dot marks this session.</p></section>
 <p class="hint">Expressions are estimated by the camera model and can be wrong. This supports, and does not replace, professional judgement.</p>`;
 $('an_back').onclick=()=>drawAll();
 window.scrollTo(0,0);
}
function drawAll(){drawP();drawH()}
$('pick').onchange=e=>{cur=e.target.value;editing=false;drawAll()};