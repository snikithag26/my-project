/* Core: helpers, API client, shared state, saving. Loaded first; other scripts share these globals. */
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

let token = localStorage.getItem('autisphere-token'), user = null;
let people = [], cur = null, editing = false;

async function api(method, url, body, raw) {
  const r = await fetch(url, { method, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) }, body: body ? JSON.stringify(body) : undefined });
  if (r.status === 401 && token && !url.startsWith('/api/auth/')) { logout(); throw new Error('Session expired. Please log in again.'); }
  if (!r.ok) { let m = r.statusText; try { const j = await r.json(); m = typeof j.detail === 'string' ? j.detail : 'Please check the details you entered.'; } catch (e) {} throw new Error(m); }
  return raw ? r : r.json();
}

const P = () => people.find(p => p.id === cur) || people[0];
const blank = () => ({
  id: 'p' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6), name: 'New person', age: '', gender: '', city: '', tags: [],
  details: ['Date of birth', 'Parent / guardian', 'Contact', 'School', 'Language', 'Blood group'].map(l => [l, '']),
  care: ['Diagnosed', 'Diagnosed by', 'Therapist', 'Co-conditions', 'Allergies'].map(l => [l, '']),
  meds: [], sensory: [], triggers: [], helps: [], faces: [], sessions: [], mood: [], assessments: []
});

/* Debounced upsert of the current person. flush() sends immediately (used before reports). */
let saveTimer = null, queued = null;
function save() { queued = P(); clearTimeout(saveTimer); saveTimer = setTimeout(flush, 300); }
async function flush() {
  clearTimeout(saveTimer);
  if (!queued) return;
  const p = queued; queued = null;
  try { const saved = await api('PUT', '/api/people/' + p.id, p); if (saved.assessments) p.assessments = saved.assessments; }
  catch (e) { alert('Could not save: ' + e.message); }
}

function tab(i) {
  [0, 1].forEach(j => { $('p' + j).classList.toggle('on', i === j); $('t' + j).setAttribute('aria-selected', i === j); });
  $('ptitle').textContent = ['Profile', 'Live session'][i];
  $('pbar').style.display = '';
}
[0, 1].forEach(i => $('t' + i).onclick = () => tab(i));
['t2', 'p2', 'add', 'del', 'report'].forEach(id => { const e = $(id); if (e) e.hidden = true; }); // removed features
$('theme').onclick = () => { const r = document.documentElement, d = getComputedStyle(r).getPropertyValue('--mode').trim() === 'dark'; r.setAttribute('data-theme', d ? 'light' : 'dark'); };