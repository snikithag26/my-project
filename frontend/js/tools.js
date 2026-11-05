/* Support tools tab: screening, stress forecast, language simplifier, mood tracker, visual schedule. */
const TOOLS = [['screen', 'ASD screening'], ['stress', 'Stress forecast'], ['simplify', 'Language simplifier'], ['mood', 'Mood tracker'], ['sched', 'Visual schedule']];
let tool = 'screen', AQ = null;
const RENDER = { screen: rScreen, stress: rStress, simplify: rSimplify, mood: rMood, sched: rSched };
const errHtml = m => `<p class="err">${esc(m)}</p>`;

function drawTools() {
  $('p2').innerHTML = `<section class="card"><h2>Support tools · ${esc(P().name)}</h2><div class="sub" role="tablist">${TOOLS.map(t => `<button role="tab" data-t="${t[0]}" aria-selected="${t[0] === tool}">${t[1]}</button>`).join('')}</div><div id="tool"></div></section>`;
  $('p2').querySelectorAll('[data-t]').forEach(b => b.onclick = () => { tool = b.dataset.t; drawTools(); });
  RENDER[tool]().catch(e => $('tool').innerHTML = errHtml(e.message));
}

async function rScreen() {
  if (!AQ) AQ = await api('GET', '/api/screening/questions');
  const p = P(), ans = Array(10).fill(null);
  $('tool').innerHTML = `<p class="hint">The server scores your answers with the AQ-10 rules, then a trained classifier estimates the probability. Results are saved to this person’s record.</p>
  <div class="grid"><div><div class="ctl">Age <input type="text" id="s_age" value="${esc(p.age || 18)}" style="width:70px" aria-label="Age">
   <select id="s_g" aria-label="Gender"><option value="m"${/^f/i.test(p.gender) ? '' : ' selected'}>Male</option><option value="f"${/^f/i.test(p.gender) ? ' selected' : ''}>Female</option></select>
   <select id="s_j" aria-label="Jaundice at birth"><option value="0">No jaundice at birth</option><option value="1">Jaundice at birth</option></select>
   <select id="s_f" aria-label="Family history"><option value="0">No family history of ASD</option><option value="1">Family history of ASD</option></select></div>
   ${AQ.map((q, i) => `<div class="q"><p>${i + 1}. ${esc(q)}</p><div class="seg" data-i="${i}"><button>Agree</button><button>Disagree</button></div></div>`).join('')}</div>
  <div><button class="btn pri" id="s_go">Get result</button><div class="res" id="s_res" style="margin-top:12px">Answer all 10 questions, then press “Get result”.</div></div></div>`;
  $('tool').querySelectorAll('.seg').forEach(s => s.querySelectorAll('button').forEach((b, k) => b.onclick = () => { ans[+s.dataset.i] = k === 0 ? 1 : 0; s.querySelectorAll('button').forEach((x, m) => x.classList.toggle('sel', m === k)); }));
  $('s_go').onclick = async () => {
    if (ans.includes(null)) { $('s_res').textContent = 'Please answer every question first.'; return; }
    try {
      const r = await api('POST', '/api/screening/predict', { answers: ans, age: parseInt($('s_age').value) || 18, gender: $('s_g').value, jaundice: $('s_j').value === '1', family_asd: $('s_f').value === '1', person_id: P().id });
      const col = r.score <= 2 ? 'var(--good)' : 'var(--warn)';
      $('s_res').innerHTML = `<div class="big" style="color:${col}">${esc(r.level)}</div><p>AQ-10 score <b>${r.score}/10</b> · model probability <b>${Math.round(r.probability * 100)}%</b><br><span class="hint">${esc(r.model)}</span></p><p>${esc(r.advice)}</p><b>Why this prediction?</b>
      ${r.explanation.slice(0, 5).map(e => `<div style="font-size:14px;margin-top:6px">${e.effect >= 0 ? '▲' : '▽'} Q${e.item} ${e.effect >= 0 ? 'raised' : 'lowered'} the probability by ${Math.abs(Math.round(e.effect * 100))} points</div>`).join('')}
      <p class="hint">Support tool, not a diagnosis.</p>`;
      const fresh = await api('GET', '/api/people'); const me = fresh.find(x => x.id === P().id); if (me) P().assessments = me.assessments;
    } catch (e) { $('s_res').innerHTML = errHtml(e.message); }
  };
}

async function rStress() {
  const F = [['Sleep last night (hours)', 'sleep', 0, 12, 6], ['Noise level', 'noise', 0, 10, 6], ['Unexpected routine changes', 'change', 0, 10, 4], ['Crowded places', 'crowd', 0, 10, 3], ['Mood today (1 low – 5 high)', 'mood', 1, 5, 3]];
  $('tool').innerHTML = `<div class="grid"><div>${F.map(f => `<label class="sl">${f[0]}<span id="v_${f[1]}">${f[4]}</span></label><input type="range" id="r_${f[1]}" min="${f[2]}" max="${f[3]}" value="${f[4]}" aria-label="${f[0]}">`).join('')}</div><div class="res" id="st_res"></div></div>
  <p class="hint">Random Forest trained on a simulated dataset (documented as synthetic). High forecasts are saved to the person’s record.</p>`;
  let t; const go = () => { clearTimeout(t); t = setTimeout(async () => {
    const b = { person_id: P().id }; F.forEach(f => { b[f[1]] = +$('r_' + f[1]).value; $('v_' + f[1]).textContent = b[f[1]]; });
    try {
      const r = await api('POST', '/api/stress/predict', b), col = r.level === 'Low' ? 'var(--good)' : 'var(--warn)', mx = Math.max(...r.drivers.map(d => d.effect), .05);
      $('st_res').innerHTML = `<div class="big" style="color:${col}">${r.risk}% · ${r.level}</div><p>${esc(r.advice)}</p><b>What is driving it</b>${r.drivers.map(d => `<div style="font-size:14px;margin-top:6px">${esc(d.factor)}<div class="meter"><i style="width:${Math.max(0, d.effect) / mx * 100}%;background:${col}"></i></div></div>`).join('')}`;
    } catch (e) { $('st_res').innerHTML = errHtml(e.message); } }, 200); };
  F.forEach(f => $('r_' + f[1]).oninput = go); go();
}

async function rSimplify() {
  $('tool').innerHTML = `<div class="grid"><div><textarea id="si" rows="7" aria-label="Text to simplify">The teacher will commence the examination shortly, and it is imperative that you remain seated and refrain from communicating with your classmates.</textarea><p><button class="btn pri" id="si_go">Simplify</button></p></div><div class="res" id="si_res">Press “Simplify”.</div></div>`;
  $('si_go').onclick = async () => {
    try { const r = await api('POST', '/api/nlp/simplify', { text: $('si').value });
      $('si_res').innerHTML = `<b>Simple version</b><p style="font-size:18px"><mark>${esc(r.simple)}</mark></p><p>Reading grade: <b>${r.grade_before}</b> → <b>${r.grade_after}</b></p>`;
    } catch (e) { $('si_res').innerHTML = errHtml(e.message); }
  };
}

async function rMood() {
  const E = [['😞', 1], ['😕', 2], ['😐', 3], ['🙂', 4], ['😄', 5]];
  $('tool').innerHTML = `<p class="sub" style="margin:0 0 8px">How is today going? Tap one to log it.</p><div class="moods">${E.map(e => `<button data-v="${e[1]}" aria-label="Mood ${e[1]} of 5">${e[0]}</button>`).join('')}</div><div class="res"><svg id="mc" viewBox="0 0 560 200" width="100%" role="img" aria-label="Mood over time"></svg><div id="ms"></div></div>`;
  $('tool').querySelectorAll('[data-v]').forEach(b => b.onclick = () => { (P().mood ||= []).push({ at: new Date().toISOString(), v: +b.dataset.v }); save(); chart(); });
  function chart() {
    const L = (P().mood || []).slice(-14).map(m => m.v), W = 560, H = 200, p = 28;
    if (!L.length) { $('mc').innerHTML = ''; $('ms').textContent = 'No mood entries yet.'; return; }
    const x = i => p + i * (W - 2 * p) / Math.max(1, L.length - 1), y = v => H - p - (v - 1) * (H - 2 * p) / 4;
    $('mc').innerHTML = [1, 2, 3, 4, 5].map(v => `<line x1="${p}" x2="${W - p}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="6" y="${y(v) + 4}">${v}</text>`).join('') +
      `<polyline fill="none" stroke="var(--accent)" stroke-width="3" stroke-linejoin="round" points="${L.map((v, i) => x(i) + ',' + y(v)).join(' ')}"/>` + L.map((v, i) => `<circle cx="${x(i)}" cy="${y(v)}" r="5" fill="var(--accent)"/>`).join('');
    const m = a => a.reduce((s, v) => s + v, 0) / a.length, d = m(L.slice(Math.floor(L.length / 2))) - m(L.slice(0, Math.ceil(L.length / 2)));
    $('ms').innerHTML = `Average <b>${m(L).toFixed(1)}</b> · Trend: <b>${d > .3 ? 'improving' : d < -.3 ? 'declining' : 'steady'}</b> · ${L.length} entries`;
  }
  chart();
}

async function rSched() {
  const p = P();
  p.schedule ||= [{ n: 'Wake up and brush teeth', i: '🪥', t: '7:00 AM' }, { n: 'Eat breakfast', i: '🥣', t: '7:30 AM' }, { n: 'Go to school', i: '🚌', t: '8:15 AM' }, { n: 'Quiet time', i: '🎧', t: '12:30 PM' }, { n: 'Homework', i: '📚', t: '4:00 PM' }, { n: 'Bedtime story', i: '🌙', t: '8:30 PM' }].map(x => ({ ...x, d: false }));
  const draw = () => {
    const d = p.schedule.filter(x => x.d).length;
    $('tool').innerHTML = `<div class="grid"><div>${p.schedule.map((k, i) => `<button class="task${k.d ? ' done' : ''}" data-i="${i}"><span class="ic">${k.i}</span><span><b>${esc(k.n)}</b><small>${esc(k.t)}</small></span><span style="margin-left:auto;font-size:22px">${k.d ? '✅' : '⬜'}</span></button>`).join('')}</div>
    <div><div class="res"><b>${d} of ${p.schedule.length} done</b><div class="meter"><i style="width:${p.schedule.length ? d / p.schedule.length * 100 : 0}%"></i></div></div>
    <h3 style="font-size:1rem;margin:16px 0 6px">Add a task</h3><input type="text" id="tn" placeholder="e.g. Feed the dog" aria-label="Task name"><p class="ctl"><select id="ti" aria-label="Icon"><option>🐶</option><option>📚</option><option>🎨</option><option>🚿</option><option>🍎</option><option>🎵</option></select><input type="text" id="tt" value="5:00 PM" aria-label="Time" style="width:110px"><button class="btn pri" id="ta">Add</button><button class="btn" id="tr">Reset day</button></p></div></div>`;
    $('tool').querySelectorAll('.task').forEach(b => b.onclick = () => { p.schedule[+b.dataset.i].d = !p.schedule[+b.dataset.i].d; save(); draw(); });
    $('ta').onclick = () => { const n = $('tn').value.trim(); if (n) { p.schedule.push({ n, i: $('ti').value, t: $('tt').value, d: false }); save(); draw(); } };
    $('tr').onclick = () => { p.schedule.forEach(x => x.d = false); save(); draw(); };
  };
  draw();
}
