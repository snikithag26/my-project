/* Login / register screen and app start-up. */
let registering = false;
function logout() { token = null; localStorage.removeItem('autisphere-token'); location.reload(); }
$('logout').onclick = logout;
$('a_sw').onclick = () => {
  registering = !registering;
  $('nameRow').hidden = $('roleRow').hidden = !registering;
  $('a_go').textContent = registering ? 'Create account' : 'Log in';
  $('a_sw').textContent = registering ? 'I already have an account' : 'Create an account';
  $('a_err').textContent = '';
};
$('af').onsubmit = async e => {
  e.preventDefault(); $('a_err').textContent = '';
  try {
    const body = { email: $('a_email').value.trim(), password: $('a_pw').value };
    if (registering) Object.assign(body, { name: $('a_name').value.trim(), role: $('a_role').value });
    const r = await api('POST', registering ? '/api/auth/register' : '/api/auth/login', body);
    token = r.token; localStorage.setItem('autisphere-token', token); start();
  } catch (err) { $('a_err').textContent = err.message; }
};
async function start() {
  try { user = await api('GET', '/api/me'); } catch (e) { $('login').hidden = false; return; }
  people = await api('GET', '/api/people');
  people = people.length ? [people[0]] : [blank()];   // one person per account
  cur = people[0].id;
  editing = !profileComplete(P());                     // force the registration form
  $('uchip').textContent = user.name + ' · ' + user.role;
  $('login').hidden = true; $('app').hidden = false;
  drawAll(); lockTabs(); tab(0);
}
token ? start() : ($('login').hidden = false);