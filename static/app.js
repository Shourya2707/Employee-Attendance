'use strict';
/* Rollbase — attendance register on a NoSQL document store. Vanilla JS, no build step.
   All stats are computed here from /api/employees and /api/attendance. */

// ---------- template helper (escapes every interpolated value unless it is already html``) ----------
class Raw { constructor(s) { this.s = s; } toString() { return this.s; } }
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const val = v => v instanceof Raw ? v.s : Array.isArray(v) ? v.map(val).join('') : v === false || v == null ? '' : esc(v);
const html = (str, ...vals) => new Raw(str.reduce((a, s, i) => a + s + (i < vals.length ? val(vals[i]) : ''), ''));
const $ = (s, el = document) => el.querySelector(s);

// ---------- icons: 24px grid, 1.5px stroke ----------
const P = {
  grid: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z',
  mark: 'M9 11.5l2 2 4-4.5M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z',
  list: 'M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01',
  users: 'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20c.6-3.3 3.2-5.5 6.5-5.5s5.9 2.2 6.5 5.5M16 4.3a3.5 3.5 0 0 1 0 6.4M18 14.8c1.9.8 3.1 2.6 3.5 5.2',
  chart: 'M4 20V10M10 20V4M16 20v-7M21 20H3',
  download: 'M12 4v11M7 10.5l5 5 5-5M5 20h14',
  keyboard: 'M3 7a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1zM7 10h.01M11 10h.01M15 10h.01M8 14h8',
  menu: 'M4 7h16M4 12h16M4 17h10',
  search: 'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4',
  sun: 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4',
  moon: 'M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z',
  arrow: 'M7 17 17 7M8 7h9v9',
  left: 'M15 6l-6 6 6 6', right: 'M9 6l6 6-6 6',
  x: 'M6 6l12 12M18 6 6 18',
  plus: 'M12 5v14M5 12h14',
  edit: 'M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4',
  trash: 'M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3',
  check: 'M5 12.5l4.5 4.5L19 7',
  alert: 'M12 9v4M12 16.5h.01M10.3 4.2 2.8 17.5A2 2 0 0 0 4.5 20.5h15a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z',
  up: 'M12 19V5M6 11l6-6 6 6', down: 'M12 5v14M6 13l6 6 6-6',
};
const icon = (n, s = 20) => html`<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${P[n]}"/></svg>`;
const wave = () => html`<svg class="wave" viewBox="0 0 300 220" preserveAspectRatio="xMidYMid slice" aria-hidden="true">${[...Array(16)].map((_, i) =>
  html`<path d="M-20 ${30 + i * 12} C 70 ${-20 + i * 15}, 170 ${120 + i * 7}, 330 ${10 + i * 14}" fill="none" stroke="#fff" stroke-width=".7"/>`)}</svg>`;

// ---------- dates, numbers ----------
const D = s => new Date(s + 'T12:00:00Z');
const iso = d => d.toISOString().slice(0, 10);
const addDays = (s, n) => { const d = D(s); d.setUTCDate(d.getUTCDate() + n); return iso(d); };
const dow = s => D(s).getUTCDay();
const isWork = s => dow(s) > 0 && dow(s) < 6;
const monday = s => addDays(s, -((dow(s) + 6) % 7));
const fmt = (s, o = { weekday: 'short', day: 'numeric', month: 'short' }) => D(s).toLocaleDateString('en-GB', { timeZone: 'UTC', ...o });
const longDate = s => fmt(s, { weekday: 'long', day: 'numeric', month: 'long' });
const mins = t => t ? +t.slice(0, 2) * 60 + +t.slice(3, 5) : null;
const hhmm = m => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(Math.round(m % 60)).padStart(2, '0')}`;
const dur = m => `${Math.floor(m / 60)}h ${String(Math.round(m % 60)).padStart(2, '0')}m`;
const pct = x => x == null ? '–' : `${Math.round(x * 100)}%`;
const plural = (n, w) => `${n.toLocaleString()} ${w}${n === 1 ? '' : 's'}`;
const workdays = (from, to) => { const out = []; for (let d = from; d <= to; d = addDays(d, 1)) if (isWork(d)) out.push(d); return out; };
const SHIFT_START = 540, LATE_AFTER = 570; // shift starts 09:00, late after 09:30

// ---------- state + indexes ----------
const STATUSES = ['Present', 'Late', 'Half-Day', 'On Leave', 'Absent'];
const SHORT = { Present: 'Present', Late: 'Late', 'Half-Day': 'Half-day', 'On Leave': 'Leave', Absent: 'Absent' };
const CODE = { Present: 'P', Late: 'L', 'Half-Day': 'H', 'On Leave': 'LV', Absent: 'A' };
const ATTENDED = new Set(['Present', 'Late', 'Half-Day']);
const cls = s => 's-' + (s || 'none').toLowerCase().replace(/\s+/g, '-');
const S = { emps: [], att: [], today: new Date().toLocaleDateString('en-CA'), version: null, loaded: false, offset: 0, counted: false, weekOff: 0 };
const byKey = new Map(), byDate = new Map(), byEmp = new Map(), byId = new Map();
const key = (id, d) => id + '|' + d;
function index() {
  S.att.sort((a, b) => b.date.localeCompare(a.date) || a.employee_id.localeCompare(b.employee_id));
  [byKey, byDate, byEmp, byId].forEach(m => m.clear());
  S.emps.forEach(e => byId.set(e.employee_id, e));
  for (const r of S.att) {
    byKey.set(key(r.employee_id, r.date), r);
    (byDate.get(r.date) || byDate.set(r.date, []).get(r.date)).push(r);
    (byEmp.get(r.employee_id) || byEmp.set(r.employee_id, []).get(r.employee_id)).push(r);
  }
}
const upsertLocal = r => { const i = S.att.findIndex(x => x.employee_id === r.employee_id && x.date === r.date); i < 0 ? S.att.push(r) : (S.att[i] = r); index(); };
const removeLocal = r => { S.att = S.att.filter(x => !(x.employee_id === r.employee_id && x.date === r.date)); index(); };
const staff = () => S.emps.filter(e => (e.status || 'Active') === 'Active');
const headOn = d => staff().filter(e => !e.created_at || e.created_at.slice(0, 10) <= d).length;
const depts = () => [...new Set(S.emps.map(e => e.department))].sort();
const inRange = (from, to) => S.att.filter(r => r.date >= from && r.date <= to);
function tally(rs) {
  const t = { Present: 0, Late: 0, 'Half-Day': 0, 'On Leave': 0, Absent: 0, n: rs.length };
  rs.forEach(r => { if (r.status in t) t[r.status]++; });
  t.att = t.Present + t.Late + t['Half-Day'];
  t.rate = t.n ? t.att / t.n : null;
  t.onTime = t.n ? t.Present / t.n : null;
  return t;
}
const lateBy = rs => { const m = rs.filter(r => r.status === 'Late' && r.checkin_time).map(r => mins(r.checkin_time) - SHIFT_START); return m.length ? m.reduce((a, b) => a + b) / m.length : null; };
const prevDay = d => [...byDate.keys()].filter(x => x < d && isWork(x)).sort().pop();
const avClass = id => 'av-' + [...id].reduce((a, c) => a + c.charCodeAt(0), 0) % 6;
const initials = n => n.split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();
const avatar = (id, name, lg) => html`<span class="avatar ${avClass(id)}${lg ? ' lg' : ''}" aria-hidden="true">${initials(name || id)}</span>`;
const pill = s => html`<span class="pill ${cls(s)}">${s ? SHORT[s] : 'Not marked'}</span>`;

// ---------- api ----------
async function api(url, body, method = 'POST') {
  const res = await fetch(url, body ? { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : undefined);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}
async function load() {
  const [emps, att] = await Promise.all([api('/api/employees'), api('/api/attendance')]);
  Object.assign(S, { emps, att, loaded: true });
  index(); render();
}
async function poll() {
  try {
    const s = await api('/api/live-status');
    if (s.today) S.today = s.today;
    if (s.engine) S.engine = s.engine;
    if (s.server_time) S.offset = new Date(s.server_time.replace(' ', 'T')) - Date.now();
    if (s.version !== S.version) { setSync('syncing'); await load(); S.version = s.version; }
    setSync('ok');
  } catch { setSync('offline'); }
}
function setSync(state) {
  const el = $('#sync'); el.dataset.state = state;
  el.textContent = { ok: 'Synced', syncing: 'Syncing…', offline: 'Offline · retrying' }[state];
  if (state === 'ok') el.dataset.tip = `Checked for changes at ${new Date().toLocaleTimeString('en-GB')}`;
  $('#todayLabel').textContent = fmt(S.today, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
}

// ---------- routing ----------
function route() {
  const [p, q = ''] = location.hash.slice(2).split('?');
  return { view: VIEWS[p] ? p : 'overview', q: Object.fromEntries(new URLSearchParams(q)) };
}
const link = (view, q = {}) => { const s = new URLSearchParams(Object.entries(q).filter(([, v]) => v !== '' && v != null)).toString(); return `#/${view}${s ? '?' + s : ''}`; };
function setQ(patch) { const r = route(); history.replaceState(null, '', link(r.view, { ...r.q, ...patch })); render(); }

function render() {
  const r = route(), v = VIEWS[r.view];
  renderChrome(r.view);
  if (!S.loaded) { $('#main').innerHTML = skeleton(); return; }
  const a = document.activeElement, fid = a && a.id && $('#main').contains(a) ? a.id : null, sel = a && a.selectionStart;
  $('#main').innerHTML = v.render(r.q);
  document.title = `${v.title} · Rollbase`;
  const f = fid && document.getElementById(fid);
  if (f) { f.focus({ preventScroll: true }); if (sel != null && f.setSelectionRange) try { f.setSelectionRange(sel, sel); } catch { } }
  if (!S.counted && r.view === 'overview') countUp();
}
const skeleton = () => html`<div class="page-head"><div class="sk" style="width:280px;height:64px"></div></div>
  <div class="grid-ov">${['k1', 'k2', 'k3', 'k4', 'week', 'reg', 'dept'].map(a => html`<div class="sk" style="grid-area:${a};height:${a[0] === 'k' ? 168 : 300}px"></div>`)}</div>`;

const NAV = [['overview', 'Overview', 'grid'], ['mark', 'Mark Attendance', 'mark'], ['records', 'Records', 'list'], ['employees', 'Employees', 'users'], ['reports', 'Reports', 'chart']];
function renderChrome(view) {
  const unmarked = S.loaded && isWork(S.today) ? staff().filter(e => !byKey.has(key(e.employee_id, S.today))).length : 0;
  $('#nav').innerHTML = html`<div class="nav-h"><span>Menu</span></div>
    ${NAV.map(([v, label, ic]) => html`<a class="nav-a" href="#/${v}" ${v === view ? new Raw('aria-current="page"') : ''} data-tip="${label}" data-tip-rail>${icon(ic)}<span class="label">${label}</span>${v === 'mark' && unmarked ? html`<span class="badge" aria-label="${unmarked} not marked">${unmarked}</span>` : ''}</a>`)}
    <div class="nav-h"><span>General</span></div>
    <a class="nav-a" href="/api/export-csv" download data-tip="Export all records as CSV" data-tip-rail>${icon('download')}<span class="label">Export CSV</span></a>
    <button class="nav-a" data-act="keys" data-tip="Keyboard shortcuts  ?" data-tip-rail>${icon('keyboard')}<span class="label">Keyboard shortcuts</span></button>`;
  const docs = S.emps.length + S.att.length;
  $('#sideCard').innerHTML = html`${wave()}<h3><span class="dot" aria-hidden="true"></span>${S.engine || 'Document store'}</h3>
    <p>${S.loaded ? `2 collections · ${docs.toLocaleString('en-IN')} documents` : 'Connecting…'}${S.engine === 'JSON file' ? html`<br>MongoDB offline, using attendance_db.json` : ''}</p>`;
  const mobile = matchMedia('(max-width: 899px)').matches, root = document.documentElement;
  $('#hamburger').setAttribute('aria-expanded', mobile ? root.classList.contains('drawer-open') : !root.classList.contains('rail'));
}

// ---------- overview ----------
function overview() {
  const t = S.today, recs = byDate.get(t) || [], tt = tally(recs), head = headOn(t), work = isWork(t);
  const prev = prevDay(t), pt = prev && tally(byDate.get(prev));
  const unmarked = staff().filter(e => !byKey.has(key(e.employee_id, t)));
  const dpts = tt.rate != null && pt?.rate != null ? Math.round((tt.rate - pt.rate) * 100) : null;
  const late = lateBy(recs);
  const kpi = (area, title, n, foot, href, extra = '', hero) => html`<section class="card kpi${hero ? ' hero' : ''}" style="grid-area:${area}">
    <h2>${title}</h2><a class="icon-btn sm go" href="${href}" aria-label="${title}: open details">${icon('arrow', 16)}</a>
    <div class="big"><span data-count="${n}">${n}</span>${extra}</div><div class="foot">${foot}</div></section>`;
  const checkedIn = recs.filter(r => r.checkin_time).length;
  return html`<div class="page-head"><div><h1>Overview</h1>
      <p>${longDate(t)} · ${work ? `${checkedIn} of ${head} checked in` : 'Not a working day'}</p></div>
    <div class="actions"><a class="btn" href="/api/export-csv?month=${t.slice(0, 7)}" download>${icon('download', 18)} Export ${fmt(t, { month: 'short' })}</a>
      <a class="btn primary" href="#/mark">${icon('mark', 18)} Mark attendance</a></div></div>
  <div class="grid-ov">
    ${kpi('k1', 'Present today', tt.att, html`${pct(tt.rate)} of marked${dpts != null ? html` · <span class="delta">${icon(dpts >= 0 ? 'up' : 'down', 12)}${Math.abs(dpts)} pts</span> vs ${fmt(prev, { weekday: 'short' })}` : ''}`,
      link('records', { from: t, to: t }), html`<small>/ ${head}</small>`, true)}
    ${kpi('k2', 'Late arrivals', tt.Late, late != null ? `avg ${Math.round(late)} min after 09:00` : 'Nobody late so far', link('records', { from: t, to: t, status: 'Late' }))}
    ${kpi('k3', 'On leave / absent', tt['On Leave'] + tt.Absent, `${tt['On Leave']} on leave · ${tt.Absent} absent`, link('records', { from: t, to: t, status: 'On Leave,Absent' }))}
    ${kpi('k4', 'Not yet marked', work ? unmarked.length : 0, work ? (unmarked.length ? html`<a class="link" href="#/mark">Open today's register</a>` : 'Register complete') : 'Weekend', '#/mark')}
    ${weekCard()}${registerCard(unmarked, recs, head, work)}${deptCard()}${liveCard(recs)}${gaugeCard()}
    ${dbCard()}
  </div>`;
}

function weekCard() {
  const mon = addDays(monday(S.today), 7 * S.weekOff), days = [...Array(7)].map((_, i) => addDays(mon, i));
  const bars = days.map(d => {
    const lbl = fmt(d, { weekday: 'short' }).slice(0, 3), rs = byDate.get(d) || [];
    if (!isWork(d) || d > S.today || !rs.length) {
      const why = !isWork(d) ? 'Weekend · non-working day' : d > S.today ? 'Upcoming' : 'No records';
      return html`<div class="cap off" data-tip="${fmt(d)}\n${why}"><div class="track"></div><span class="lbl">${lbl}</span></div>`;
    }
    const t = tally(rs), miss = headOn(d) - t.n, today = d === S.today;
    const tip = `${fmt(d)} · ${pct(t.rate)} in office\n${t.Present} present · ${t.Late} late · ${t['Half-Day']} half-day\n${t['On Leave']} on leave · ${t.Absent} absent${miss > 0 ? `\n${miss} not marked yet` : ''}`;
    return html`<button class="cap${today ? ' today' : ''}" data-tip="${tip}" aria-label="${tip}"><div class="track"><div class="fill" style="height:${t.rate * 100}%">${today ? html`<span class="val" style="top:8px">${pct(t.rate)}</span>` : ''}</div></div><span class="lbl">${lbl}</span></button>`;
  });
  return html`<section class="card wk" style="grid-area:week">
    <div class="card-h"><div><h2>${S.weekOff ? `Week of ${fmt(mon, { day: 'numeric', month: 'short' })}` : 'This week'}</h2><span class="sub">Share of marked employees in office (present, late or half-day)</span></div>
      <div class="actions"><button class="icon-btn sm" data-act="week" data-d="-1" aria-label="Previous week">${icon('left', 16)}</button>
      <button class="icon-btn sm" data-act="week" data-d="1" aria-label="Next week" ${S.weekOff >= 0 ? new Raw('disabled') : ''}>${icon('right', 16)}</button></div></div>
    <div class="capsules"><div class="yax">${[100, 50, 0].map(v => html`<span style="top:calc((100% - 28px) * ${(100 - v) / 100})">${v}%</span>`)}</div>
      <div class="grid">${[0, 50, 100].map(v => html`<i style="top:${v}%"></i>`)}</div>${bars}</div>
    ${weekStats(days)}</section>`;
}
function weekStats(days) {
  const ds = days.filter(d => isWork(d) && d <= S.today && byDate.has(d));
  if (!ds.length) return '';
  const all = tally(ds.flatMap(d => byDate.get(d))), best = ds.reduce((a, d) => (tally(byDate.get(d)).rate > tally(byDate.get(a)).rate ? d : a));
  const stat = (label, v) => html`<div><small>${label}</small><b class="num">${v}</b></div>`;
  return html`<div class="wk-stats">${stat('Week average', pct(all.rate))}${stat('Best day', fmt(best, { weekday: 'long' }))}${stat('Late arrivals', all.Late)}</div>`;
}

function registerCard(unmarked, recs, head, work) {
  let body;
  if (!work) body = html`<p class="headline">No register today</p><p class="muted" style="margin-top:8px">${fmt(S.today, { weekday: 'long' })} isn't a working day. The next register opens Monday.</p>`;
  else if (unmarked.length) body = html`<p class="headline">${plural(unmarked.length, 'employee')} not marked yet</p>
    <ul class="rows" style="margin:16px 0">${unmarked.slice(0, 3).map(e => html`<li>${avatar(e.employee_id, e.name)}<div class="who"><b>${e.name}</b><small>${e.department}</small></div></li>`)}</ul>
    ${unmarked.length > 3 ? html`<p class="muted" style="margin:-8px 0 16px">and ${unmarked.length - 3} more</p>` : ''}
    <button class="btn primary" data-act="allPresent" data-date="${S.today}">${icon('check', 18)} Mark all present</button>`;
  else {
    const last = recs.map(r => r.marked_at || '').sort().pop();
    body = html`<div class="done"><span class="ok">${icon('check', 22)}</span><p class="headline">Register complete</p>
      <p class="muted">All ${head} employees marked${last ? ` · last entry at ${last.slice(11, 16)}` : ''}.</p></div>
      <a class="btn" href="#/mark" style="margin-top:auto">Review entries</a>`;
  }
  return html`<section class="card register" style="grid-area:reg"><div class="card-h"><h2>Today's register</h2></div>${body}</section>`;
}

function deptCard() {
  const from = addDays(S.today, -29), rs = inRange(from, S.today), all = tally(rs);
  const rows = depts().map(d => ({ d, t: tally(rs.filter(r => r.department === d)) })).filter(x => x.t.n).sort((a, b) => b.t.rate - a.t.rate);
  return html`<section class="card" style="grid-area:dept"><div class="card-h"><div><h2>Departments</h2><span class="sub">In-office rate, last 30 days · company ${pct(all.rate)}</span></div></div>
    <ul class="rows depts">${rows.map(({ d, t }) => {
    const out = t.rate < all.rate - 0.05;
    return html`<li class="${out ? 'outlier' : ''}"><a class="link" style="color:inherit;font-weight:500" href="${link('records', { dept: d, from, to: S.today })}">${d}${out ? html`<span class="tag">below avg</span>` : ''}</a><b class="num">${pct(t.rate)}</b><div class="bar"><i style="width:${t.rate * 100}%"></i></div></li>`;
  })}</ul></section>`;
}

function liveCard(recs) {
  const ins = recs.filter(r => r.checkin_time).sort((a, b) => b.checkin_time.localeCompare(a.checkin_time));
  return html`<section class="card" style="grid-area:live"><div class="card-h"><div><h2>Live check-ins</h2><span class="sub">${plural(ins.length, 'check-in')} today · most recent first</span></div>
    <a class="btn sm" href="${link('records', { from: S.today, to: S.today, sort: '-in' })}">View all</a></div>
    ${ins.length ? html`<ul class="rows">${ins.slice(0, 5).map(r => {
    const e = byId.get(r.employee_id) || {};
    const why = r.status === 'Late' ? (r.notes ? `Late: ${r.notes}` : `Late by ${mins(r.checkin_time) - SHIFT_START} min`) : e.designation;
    return html`<li>${avatar(r.employee_id, r.employee_name)}<div class="who"><b>${r.employee_name}</b><small class="${r.status === 'Late' ? 'note' : ''}">${why}</small></div><span class="time">${r.checkin_time}</span>${pill(r.status)}</li>`;
  })}</ul>` : html`<div class="empty"><b>No check-ins yet</b><span>Nobody has a check-in time recorded for today.</span><a class="btn primary sm" href="#/mark">Open register</a></div>`}</section>`;
}

function gaugeCard() {
  const from = S.today.slice(0, 8) + '01', t = tally(inRange(from, S.today)), pm = addDays(from, -1), pt = tally(inRange(pm.slice(0, 8) + '01', pm));
  const segs = [['On time', t.Present, 'var(--present)'], ['Late', t.Late, 'var(--late)'], ['Half-day', t['Half-Day'], 'var(--half)'], ['Leave / absent', t['On Leave'] + t.Absent, 'url(#hatch)']];
  let at = 0;
  const arcs = t.n ? segs.map(([, n, c]) => { const len = n / t.n * 100, a = at; at += len; return len > 0.5 ? html`<path d="M20 120 A100 100 0 0 1 220 120" pathLength="100" stroke-dasharray="${Math.max(len - 1, .3)} 200" stroke-dashoffset="${-a}" style="stroke:${c}"/>` : ''; }) : '';
  return html`<section class="card gauge-card" style="grid-area:gauge"><div class="card-h"><div><h2>Month to date</h2><span class="sub">${fmt(S.today, { month: 'long' })} · ${plural(t.n, 'person-day')}</span></div></div>
    <div class="gauge"><svg viewBox="0 0 240 132" role="img" aria-label="${segs.map(s => `${s[0]} ${s[1]}`).join(', ')}">
      <defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" style="fill:var(--leave-bg)"/><rect width="2.4" height="6" style="fill:var(--leave)"/></pattern></defs>
      <g fill="none" stroke-width="30"><path d="M20 120 A100 100 0 0 1 220 120" style="stroke:var(--line-2)"/>${arcs}</g></svg>
      <div class="center"><b>${pct(t.onTime)}</b><small>on time</small></div></div>
    <div class="legend">${segs.map(([l, n, c]) => html`<span><i class="sw" style="background:${c === 'url(#hatch)' ? 'var(--hatch-leave)' : c}"></i>${l} <b class="num">${n}</b></span>`)}</div>
    ${pt.n ? html`<p class="muted prev" style="text-align:center;margin-top:16px;font-size:12px">${fmt(pm, { month: 'long' })}: ${pct(pt.onTime)} on time over ${plural(pt.n, 'person-day')}</p>` : ''}</section>`;
}

// The NoSQL side of the app: what is stored, how it is indexed, and the last document written.
function dbCard() {
  const last = S.att.reduce((a, r) => (!a || r.marked_at > a.marked_at ? r : a), null);
  const ago = last && Math.round((Date.now() + S.offset - new Date(last.marked_at.replace(' ', 'T'))) / 60000);
  const show = v => JSON.stringify(v.length > 20 ? v.slice(0, 19) + '…' : v);
  const doc = last && ['employee_id', 'date', 'status', 'checkin_time', 'checkout_time', 'notes'].map(k => html`  <i>"${k}"</i>: <b>${show(last[k])}</b>`);
  const col = (name, n, idx, tip = '') => html`<li data-tip="${tip}"><code>${name}</code><span class="num">${n.toLocaleString('en-IN')} docs</span><small>index: ${idx}</small></li>`;
  return html`<section class="card db" style="grid-area:db" aria-label="Document store">${wave()}
    <div class="db-head"><h2>Document store</h2><span class="engine"><span class="dot" aria-hidden="true"></span>${S.engine || 'Connecting'}</span></div>
    <ul class="cols">${col('employees', S.emps.length, 'employee_id · unique')}${col('attendance', S.att.length, 'employee_id + date · unique', 'Marking someone twice on one day updates their document (upsert) instead of creating a duplicate')}</ul>
    ${last ? html`<p class="lbl">Latest write · ${ago < 1 ? 'just now' : ago < 60 ? `${ago} min ago` : fmt(last.date, { day: 'numeric', month: 'short' }) + ' ' + last.marked_at.slice(11, 16)}</p>
    <pre class="doc">{
${new Raw(doc.join(',\n'))}
}</pre>` : ''}</section>`;
}

function countUp() {
  S.counted = true;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.querySelectorAll('[data-count]').forEach(el => {
    const end = +el.dataset.count, t0 = performance.now();
    const step = t => { const k = Math.min(1, (t - t0) / 700); el.textContent = Math.round(end * (1 - (1 - k) ** 3)); if (k < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  });
}

// ---------- mark attendance ----------
function markView(q) {
  const date = q.date || S.today, dept = q.dept || '', s = (q.q || '').toLowerCase();
  const people = staff().filter(e => !e.created_at || e.created_at.slice(0, 10) <= date);
  const marked = people.filter(e => byKey.has(key(e.employee_id, date))).length, left = people.length - marked;
  const shown = people.filter(e => (!dept || e.department === dept) && (!s || `${e.name} ${e.employee_id} ${e.designation}`.toLowerCase().includes(s)));
  const groups = depts().filter(d => !dept || d === dept).map(d => [d, shown.filter(e => e.department === d)]).filter(g => g[1].length);
  const row = e => {
    const r = byKey.get(key(e.employee_id, date)), id = e.employee_id;
    return html`<div class="mrow" tabindex="0" id="row-${id}" data-id="${id}" aria-label="${e.name}, ${r ? r.status : 'not marked'}">
      <div class="who">${avatar(id, e.name)}<div><b>${e.name}</b><small>${e.designation} · ${id}</small></div></div>
      <div class="seg" role="group" aria-label="Status for ${e.name}">${STATUSES.map((st, i) => html`<button id="b-${id}-${i}" class="${cls(st)}" data-act="mark" data-id="${id}" data-s="${st}" aria-pressed="${r?.status === st}" tabindex="-1">${SHORT[st]}</button>`)}</div>
      <input class="input" type="time" id="t-${id}" data-time="${id}" value="${r?.checkin_time || ''}" aria-label="Check-in time for ${e.name}" ${r && ATTENDED.has(r.status) ? '' : new Raw('disabled')}></div>`;
  };
  const note = !isWork(date) ? `${longDate(date)} is not a working day. Entries saved here still count in reports.` : date > S.today ? `${longDate(date)} is in the future.` : '';
  return html`<div class="page-head"><div><h1>Mark attendance</h1><p>${longDate(date)} · ${marked} of ${people.length} marked</p></div>
    <div class="actions"><input class="input" type="date" id="markDate" data-q="date" value="${date}" aria-label="Register date">
      <button class="btn primary" data-act="allPresent" data-date="${date}" ${left ? '' : new Raw('disabled')}>${icon('check', 18)} Mark remaining ${left || ''} present</button></div></div>
    ${note ? html`<div class="notice">${icon('alert')}${note}</div>` : ''}
    <section class="card">
      <div class="mark-top"><span class="count"><b class="num">${marked}</b> / ${people.length} marked</span>
        <div class="progress" role="progressbar" aria-label="Marked" aria-valuenow="${marked}" aria-valuemax="${people.length}"><i style="width:${people.length ? marked / people.length * 100 : 0}%"></i></div>
        <span class="muted" style="font-size:12px"><kbd>j</kbd> <kbd>k</kbd> move · <kbd>1</kbd>–<kbd>5</kbd> set status</span></div>
      <div class="toolbar" style="margin:16px 0 0">${searchBox('markQ', q.q, 'Search name, ID or role')}${deptChips(dept)}</div>
      ${groups.length ? groups.map(([d, es]) => html`<div class="dept-h"><span>${d}</span><span>${es.filter(e => byKey.has(key(e.employee_id, date))).length} / ${es.length}</span></div>${es.map(row)}`)
      : html`<div class="empty"><b>No one matches “${q.q || dept}”</b><button class="btn sm" data-act="clear">Clear search</button></div>`}
    </section>`;
}
const searchBox = (id, v, ph) => html`<label class="search">${icon('search', 18)}<span class="sr">${ph}</span><input class="input" type="search" id="${id}" data-q="q" value="${v || ''}" placeholder="${ph}" autocomplete="off"></label>`;
const deptChips = cur => html`<div class="chips" role="group" aria-label="Department">${['', ...depts()].map(d => html`<button class="chip" data-act="q" data-k="dept" data-v="${d}" aria-pressed="${(cur || '') === d}">${d || 'All'}</button>`)}</div>`;

function statusDefaults(rec, status, date) {
  const now = new Date(Date.now() + S.offset), nowT = hhmm(now.getHours() * 60 + now.getMinutes());
  if (!ATTENDED.has(status)) return { checkin_time: '', checkout_time: '' };
  const cin = rec?.checkin_time || (status === 'Late' ? (date === S.today && mins(nowT) > LATE_AFTER ? nowT : '') : '09:00');
  return { checkin_time: cin, checkout_time: rec?.checkout_time || '' };
}
async function save(rec, msg) {
  const prev = byKey.get(key(rec.employee_id, rec.date));
  upsertLocal(rec); render();
  try { upsertLocal({ ...rec, ...(await api('/api/attendance', rec)) }); toast(msg, { key: 'save' }); return true; }
  catch (err) { prev ? upsertLocal(prev) : removeLocal(rec); render(); toast(`Couldn't save: ${err.message}`, { err: true }); return false; }
}
function setStatus(id, status, date = route().q.date || S.today) {
  const e = byId.get(id), prev = byKey.get(key(id, date));
  if (prev?.status === status) return;
  save({ employee_id: id, employee_name: e.name, department: e.department, date, status, notes: prev?.notes || '', ...statusDefaults(prev, status, date) },
    `${e.name} marked ${SHORT[status].toLowerCase()} for ${fmt(date)}`);
}
function setTime(id, t) {
  const date = route().q.date || S.today, prev = byKey.get(key(id, date)), e = byId.get(id);
  if (!prev) return;
  let status = prev.status;
  if (status === 'Present' && mins(t) > LATE_AFTER) status = 'Late';
  else if (status === 'Late' && t && mins(t) <= LATE_AFTER) status = 'Present';
  save({ ...prev, checkin_time: t, status }, status !== prev.status ? `${e.name} marked ${status.toLowerCase()} · checked in ${t}` : `${e.name} checked in at ${t}`);
}
async function allPresent(date) {
  try {
    const r = await api('/api/attendance/mark-all-present', { date });
    toast(r.marked != null ? `Marked ${plural(r.marked, 'employee')} present for ${fmt(r.date || date)}` : (r.message || 'Remaining employees marked present'));
    await load();
  } catch (err) { toast(`Couldn't mark: ${err.message}`, { err: true }); }
}

// ---------- records ----------
const COLS = [['date', 'Date'], ['name', 'Employee'], ['dept', 'Department'], ['status', 'Status'], ['in', 'Check-in'], ['out', 'Check-out'], ['hours', 'Hours'], ['', 'Notes']];
const sortVal = (r, k) => ({ date: r.date, name: r.employee_name, dept: r.department, status: STATUSES.indexOf(r.status), in: r.checkin_time || '~', out: r.checkout_time || '~', hours: hoursOf(r) ?? -1 }[k]);
const hoursOf = r => r.checkin_time && r.checkout_time ? mins(r.checkout_time) - mins(r.checkin_time) : null;
const PAGE = 50;
function recordsView(q) {
  const st = q.status ? q.status.split(',') : [], s = (q.q || '').toLowerCase(), sort = q.sort || '-date';
  const k = sort.replace('-', ''), dir = sort[0] === '-' ? -1 : 1;
  const rows = S.att.filter(r => (!st.length || st.includes(r.status)) && (!q.dept || r.department === q.dept) && (!q.from || r.date >= q.from) && (!q.to || r.date <= q.to)
    && (!s || `${r.employee_name} ${r.employee_id} ${r.notes}`.toLowerCase().includes(s)))
    .sort((a, b) => { const x = sortVal(a, k), y = sortVal(b, k); return (x < y ? -1 : x > y ? 1 : 0) * dir || b.date.localeCompare(a.date) || a.employee_name.localeCompare(b.employee_name); });
  const pages = Math.max(1, Math.ceil(rows.length / PAGE)), page = Math.min(pages, Math.max(1, +q.page || 1)), slice = rows.slice((page - 1) * PAGE, page * PAGE);
  const month = q.from && q.to && q.from.slice(0, 7) === q.to.slice(0, 7) ? q.from.slice(0, 7) : '';
  const filtered = st.length || q.dept || q.from || q.to || q.q;
  const th = ([c, label]) => !c ? html`<th>${label}</th>` : html`<th ${k === c ? new Raw(`aria-sort="${dir > 0 ? 'ascending' : 'descending'}"`) : ''}><button data-act="q" data-k="sort" data-v="${k === c && dir < 0 ? c : '-' + c}">${label}${k === c ? icon(dir > 0 ? 'up' : 'down', 12) : ''}</button></th>`;
  return html`<div class="page-head"><div><h1>Records</h1><p>${rows.length.toLocaleString()} of ${S.att.length.toLocaleString()} records${q.from || q.to ? ` · ${q.from ? fmt(q.from) : 'start'} – ${q.to ? fmt(q.to) : 'today'}` : ''}</p></div>
    <div class="actions"><a class="btn" href="/api/export-csv${month ? '?month=' + month : ''}" download>${icon('download', 18)} Export ${month ? fmt(month + '-01', { month: 'long' }) : 'all'} CSV</a></div></div>
  <section class="card">
    <div class="toolbar">${searchBox('recQ', q.q, 'Search name, ID or note')}
      <select class="input" id="recDept" data-q="dept" aria-label="Department"><option value="">All departments</option>${depts().map(d => html`<option ${d === q.dept ? new Raw('selected') : ''}>${d}</option>`)}</select>
      <input class="input" type="date" id="recFrom" data-q="from" value="${q.from || ''}" aria-label="From date">
      <input class="input" type="date" id="recTo" data-q="to" value="${q.to || ''}" aria-label="To date">
      ${filtered ? html`<button class="btn ghost sm" data-act="clear">${icon('x', 16)} Clear filters</button>` : ''}</div>
    <div class="chips" role="group" aria-label="Status" style="margin-bottom:16px">${STATUSES.map(x => html`<button class="chip" data-act="status" data-v="${x}" aria-pressed="${st.includes(x)}"><span class="pill ${cls(x)}" style="height:auto;padding:0;background:none">${SHORT[x]}</span></button>`)}</div>
    ${slice.length ? html`<div class="table-wrap"><table><thead><tr>${COLS.map(th)}<th><span class="sr">Actions</span></th></tr></thead><tbody>
      ${slice.map(r => { const h = hoursOf(r); return html`<tr><td>${fmt(r.date, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}</td>
        <td><div class="who">${avatar(r.employee_id, r.employee_name)}<div><b>${r.employee_name}</b><small>${r.employee_id}</small></div></div></td>
        <td>${r.department}</td><td>${pill(r.status)}</td><td>${r.checkin_time || '–'}</td><td>${r.checkout_time || '–'}</td><td>${h != null ? dur(h) : '–'}</td>
        <td class="notes" title="${r.notes}">${r.notes || ''}</td>
        <td class="acts"><button class="icon-btn sm bare" data-act="edit" data-id="${r.employee_id}" data-date="${r.date}" aria-label="Edit ${r.employee_name} on ${r.date}">${icon('edit', 16)}</button>
          <button class="icon-btn sm bare" data-act="del" data-id="${r.employee_id}" data-date="${r.date}" aria-label="Delete ${r.employee_name} on ${r.date}">${icon('trash', 16)}</button></td></tr>`; })}
    </tbody></table></div>
    <div class="pager"><span class="muted">Showing ${((page - 1) * PAGE + 1).toLocaleString()}–${Math.min(page * PAGE, rows.length).toLocaleString()} of ${rows.length.toLocaleString()}</span>
      <div class="actions"><button class="btn sm" data-act="q" data-k="page" data-v="${page - 1}" ${page > 1 ? '' : new Raw('disabled')}>${icon('left', 16)} Previous</button>
      <span class="num">Page ${page} of ${pages}</span>
      <button class="btn sm" data-act="q" data-k="page" data-v="${page + 1}" ${page < pages ? '' : new Raw('disabled')}>Next ${icon('right', 16)}</button></div></div>`
      : html`<div class="empty"><b>No records match these filters</b><span>Try a wider date range or fewer statuses.</span><button class="btn sm" data-act="clear">Clear filters</button></div>`}
  </section>`;
}
function editDrawer(id, date) {
  const r = byKey.get(key(id, date));
  openDrawer(html`<div class="dh"><div><h2 id="drawerTitle">Edit record</h2><span class="muted">${r.employee_name} · ${longDate(date)}</span></div><button class="icon-btn sm bare" data-act="close" aria-label="Close">${icon('x', 18)}</button></div>
    <form class="db" data-form="edit" data-id="${id}" data-date="${date}"><div class="form-grid">
      <div class="field full"><label for="f-status">Status</label><select class="input" id="f-status" name="status">${STATUSES.map(s => html`<option ${s === r.status ? new Raw('selected') : ''}>${s}</option>`)}</select></div>
      <div class="field"><label for="f-in">Check-in</label><input class="input" type="time" id="f-in" name="checkin_time" value="${r.checkin_time}"><span class="hint">After 09:30 counts as late</span></div>
      <div class="field"><label for="f-out">Check-out</label><input class="input" type="time" id="f-out" name="checkout_time" value="${r.checkout_time}"></div>
      <div class="field full"><label for="f-notes">Notes</label><textarea class="input" id="f-notes" name="notes" rows="3">${r.notes}</textarea></div></div>
      <div class="df"><button type="button" class="btn" data-act="close">Cancel</button><button class="btn primary">Save changes</button></div></form>`);
}
async function del(id, date) {
  const r = byKey.get(key(id, date));
  removeLocal(r); render();
  try {
    await api('/api/attendance', { employee_id: id, date }, 'DELETE');
    toast(`Deleted ${r.employee_name} · ${fmt(date)}`, { action: ['Undo', () => save(r, `Restored ${r.employee_name} · ${fmt(date)}`)] });
  } catch (err) { upsertLocal(r); render(); toast(`Couldn't delete: ${err.message}`, { err: true }); }
}

// ---------- employees ----------
function empStats(id, from = addDays(S.today, -41)) {
  const rs = (byEmp.get(id) || []).filter(r => r.date >= from && r.date <= S.today), t = tally(rs);
  const ins = rs.filter(r => ATTENDED.has(r.status) && r.checkin_time).map(r => mins(r.checkin_time));
  return { t, rs, punct: t.Present + t.Late ? t.Present / (t.Present + t.Late) : null, avgIn: ins.length ? ins.reduce((a, b) => a + b) / ins.length : null };
}
function employeesView(q) {
  const s = (q.q || '').toLowerCase();
  const list = S.emps.filter(e => (!q.dept || e.department === q.dept) && (!s || `${e.name} ${e.employee_id} ${e.designation} ${e.city || ''}`.toLowerCase().includes(s)));
  return html`<div class="page-head"><div><h1>Employees</h1><p>${plural(staff().length, 'active employee')} across ${plural(depts().length, 'department')}</p></div>
    <div class="actions"><button class="btn primary" data-act="addEmp">${icon('plus', 18)} Add employee</button></div></div>
  <div class="toolbar">${searchBox('empQ', q.q, 'Search name, ID, role or city')}${deptChips(q.dept)}</div>
  ${list.length ? html`<div class="emp-grid">${list.map(e => {
    const { t, punct } = empStats(e.employee_id), today = byKey.get(key(e.employee_id, S.today));
    return html`<button class="card emp" data-act="emp" data-id="${e.employee_id}"><div class="top">${avatar(e.employee_id, e.name)}<div><b>${e.name}</b><small>${e.designation}</small></div></div>
      <small>${e.department}${e.city ? ` · ${e.city}` : ''} · ${e.employee_id}</small>
      <div class="stats"><span><b class="num">${pct(t.rate)}</b>in office</span><span><b class="num">${pct(punct)}</b>on time</span><span style="text-align:right">Today<br>${pill(today?.status)}</span></div></button>`;
  })}</div>` : html`<div class="card empty"><b>No employees match</b><span>Check the spelling or add them to the directory.</span><button class="btn primary sm" data-act="addEmp">${icon('plus', 16)} Add employee</button></div>`}`;
}
function empPanel(id) {
  const e = byId.get(id), { t, punct, avgIn } = empStats(id), start = addDays(monday(S.today), -35);
  const notes = (byEmp.get(id) || []).filter(r => r.notes && r.status !== 'Present').slice(0, 5);
  const weeks = [...Array(6)].map((_, w) => addDays(start, w * 7));
  openDrawer(html`<div class="dh"><div style="display:flex;gap:16px;align-items:center">${avatar(id, e.name, true)}<div><h2 id="drawerTitle">${e.name}</h2><span class="muted">${e.designation} · ${id}</span></div></div><button class="icon-btn sm bare" data-act="close" aria-label="Close">${icon('x', 18)}</button></div>
    <div class="db"><p class="muted">${[e.department, e.city, e.email, e.phone].filter(x => x && x !== 'N/A').join(' · ')}</p>
      <div class="stat-row"><div class="stat"><b>${pct(t.rate)}</b><small>Attendance, 6 weeks</small></div><div class="stat"><b>${pct(punct)}</b><small>On time when in</small></div><div class="stat"><b>${avgIn != null ? hhmm(avgIn) : '–'}</b><small>Average check-in</small></div></div>
      <div><div class="card-h" style="margin-bottom:8px"><h2>Last 6 weeks</h2><span class="sub">${t.Late} late · ${t['On Leave']} leave · ${t.Absent} absent</span></div>
        <div class="cal"><span></span>${['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map(d => html`<span class="h">${d}</span>`)}
        ${weeks.map(w => html`<span class="wk">${fmt(w, { day: 'numeric', month: 'short' })}</span>${[0, 1, 2, 3, 4].map(i => {
    const d = addDays(w, i), r = byKey.get(key(id, d));
    if (d > S.today) return html`<span class="c s-future" data-tip="${fmt(d)} · upcoming"></span>`;
    return html`<span class="c ${cls(r?.status)}" data-tip="${fmt(d)} · ${r ? r.status : 'No record'}${r?.checkin_time ? ' · in ' + r.checkin_time : ''}${r?.notes ? '\n' + r.notes : ''}">${r ? CODE[r.status] : '–'}</span>`;
  })}`)}</div>
        <div class="legend" style="justify-content:flex-start">${STATUSES.map(s => html`<span><i class="sw c ${cls(s)}" style="height:12px"></i>${CODE[s]} ${SHORT[s]}</span>`)}</div></div>
      <div><div class="card-h" style="margin-bottom:8px"><h2>Recent notes</h2><a class="link" href="${link('records', { q: id })}" data-act="close">All records</a></div>
        ${notes.length ? html`<ul class="rows">${notes.map(r => html`<li><div class="who"><b>${r.notes}</b><small>${fmt(r.date)}${r.checkin_time ? ' · in ' + r.checkin_time : ''}</small></div>${pill(r.status)}</li>`)}</ul>` : html`<p class="muted">No late, leave or absence notes on file.</p>`}</div></div>`);
}
function addEmpDrawer() {
  const next = 'EMP' + (Math.max(1000, ...S.emps.map(e => +e.employee_id.replace(/\D/g, '') || 0)) + 1);
  const f = (name, label, attrs = '', full) => html`<div class="field${full ? ' full' : ''}"><label for="a-${name}">${label}</label><input class="input" id="a-${name}" name="${name}" ${new Raw(attrs)}><span class="err" id="e-${name}"></span></div>`;
  openDrawer(html`<div class="dh"><div><h2 id="drawerTitle">Add employee</h2><span class="muted">They appear in the register from today</span></div><button class="icon-btn sm bare" data-act="close" aria-label="Close">${icon('x', 18)}</button></div>
    <form class="db" data-form="add" novalidate><div class="form-err" id="e-form" hidden></div><div class="form-grid">
      ${f('employee_id', 'Employee ID', `value="${next}" required`)}${f('name', 'Full name', 'required autocomplete="off"')}
      <div class="field"><label for="a-department">Department</label><select class="input" id="a-department" name="department" required><option value="">Choose…</option>${depts().map(d => html`<option>${d}</option>`)}</select><span class="err" id="e-department"></span></div>
      ${f('designation', 'Designation', 'required')}${f('email', 'Email', 'type="email"')}${f('phone', 'Phone', 'type="tel"')}${f('city', 'City', '', true)}</div>
      <div class="df"><button type="button" class="btn" data-act="close">Cancel</button><button class="btn primary">${icon('plus', 18)} Add employee</button></div></form>`);
}
async function submitAdd(form) {
  const body = Object.fromEntries(new FormData(form));
  form.querySelectorAll('.err').forEach(e => (e.textContent = ''));
  form.querySelectorAll('[aria-invalid]').forEach(e => e.removeAttribute('aria-invalid'));
  const fail = (field, msg) => {
    const el = $('#e-' + field, form);
    if (field === 'form') { el.hidden = false; el.textContent = msg; return; }
    el.textContent = msg; const inp = $('#a-' + field, form); inp.setAttribute('aria-invalid', 'true'); inp.focus();
  };
  const missing = ['employee_id', 'name', 'department', 'designation'].find(k => !body[k].trim());
  if (missing) return fail(missing, 'Required');
  try {
    const e = await api('/api/employees', body);
    S.emps.push(e); index(); $('#drawer').close(); render();
    toast(`Added ${e.name} to ${e.department}`);
  } catch (err) {
    const m = err.message.toLowerCase();
    fail(['designation', 'department', 'email', 'phone', 'city', 'name'].find(k => m.includes(k)) || (/\bid\b|employee id/.test(m) ? 'employee_id' : 'form'), err.message);
  }
}

// ---------- reports ----------
function reportsView(q) {
  const weeks = +q.weeks || 4, from = addDays(monday(S.today), -7 * (weeks - 1)), to = S.today;
  const rs = inRange(from, to), days = workdays(from, to).filter(d => byDate.has(d));
  const series = days.map(d => ({ d, t: tally(byDate.get(d)) }));
  return html`<div class="page-head"><div><h1>Reports</h1><p>${fmt(from)} – ${fmt(to)} · ${plural(days.length, 'working day')} · ${plural(rs.length, 'record')}</p></div>
    <div class="actions"><div class="chips" role="group" aria-label="Period">${[2, 4, 6].map(w => html`<button class="chip" data-act="q" data-k="weeks" data-v="${w}" aria-pressed="${w === weeks}">${w} weeks</button>`)}</div>
      <a class="btn" href="/api/export-csv" download>${icon('download', 18)} Export CSV</a></div></div>
  ${rs.length ? html`<div class="grid-rep">${trendCard(series)}${heatCard(rs)}${lateCard(rs)}</div>` : html`<div class="card empty"><b>No records in this period</b><a class="btn primary sm" href="#/mark">Open register</a></div>`}`;
}
function trendCard(series) {
  const vals = series.flatMap(s => [s.t.rate, s.t.onTime]), lo = Math.max(0, Math.floor((Math.min(...vals) * 100 - 5) / 10) * 10), Y = v => 100 - (v * 100 - lo) / (100 - lo) * 100;
  const X = i => series.length > 1 ? i / (series.length - 1) * 100 : 50, ticks = [lo, lo + (100 - lo) / 2, 100];
  const line = (k, c) => html`<polyline points="${series.map((s, i) => `${X(i)},${Y(s.t[k])}`).join(' ')}" fill="none" style="stroke:${c}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`;
  const every = Math.ceil(series.length / 8), col = series.length > 1 ? 100 / (series.length - 1) : 100;
  return html`<section class="card wide"><div class="card-h"><div><h2>Daily attendance</h2><span class="sub">Share of marked employees per working day · y-axis starts at ${lo}%</span></div>
    <div class="legend" style="margin:0"><span><i class="sw" style="background:var(--g-700);height:3px"></i>In office</span><span><i class="sw" style="background:var(--late);height:3px"></i>On time</span></div></div>
    <div class="trend" style="margin-bottom:32px">${ticks.map(v => html`<span class="yl" style="top:${100 - (v - lo) / (100 - lo) * 100}%">${Math.round(v)}%</span>`)}
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${ticks.map(v => html`<line x1="0" x2="100" y1="${100 - (v - lo) / (100 - lo) * 100}" y2="${100 - (v - lo) / (100 - lo) * 100}" style="stroke:var(--line)" vector-effect="non-scaling-stroke"/>`)}${line('rate', 'var(--g-700)')}${line('onTime', 'var(--late)')}</svg>
      <div class="hit" style="left:${-col / 2}%;width:${100 + col}%">${series.map(s => html`<button data-tip="${fmt(s.d)}\nIn office ${pct(s.t.rate)} · on time ${pct(s.t.onTime)}\n${s.t.Late} late · ${s.t['On Leave'] + s.t.Absent} leave/absent" aria-label="${fmt(s.d)}: in office ${pct(s.t.rate)}, on time ${pct(s.t.onTime)}"></button>`)}</div>
      ${series.map((s, i) => i % every === 0 || i === series.length - 1 ? html`<span class="xl" style="left:${X(i)}%">${fmt(s.d, { day: 'numeric', month: 'short' })}</span>` : '')}</div></section>`;
}
function heatCard(rs) {
  const grid = depts().map(d => [d, [1, 2, 3, 4, 5].map(w => tally(rs.filter(r => r.department === d && dow(r.date) === w)))]);
  const rates = grid.flatMap(g => g[1].map(t => t.rate)).filter(x => x != null), lo = Math.min(...rates), hi = Math.max(...rates);
  const k = r => hi > lo ? (r - lo) / (hi - lo) : 1;
  return html`<section class="card"><div class="card-h"><div><h2>Department × weekday</h2><span class="sub">In-office rate · darker is higher</span></div></div>
    <div class="heat"><span></span>${['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map(d => html`<span class="h">${d}</span>`)}
    ${grid.map(([d, ts]) => html`<span class="rl">${d}</span>${ts.map((t, i) => t.rate == null ? html`<span class="c s-none">–</span>` :
    html`<span class="c" tabindex="0" style="background:color-mix(in srgb, var(--g-700) ${Math.round(12 + k(t.rate) * 80)}%, var(--g-50));color:${k(t.rate) > .5 ? '#fff' : 'var(--ink)'}" data-tip="${d} · ${['Mon', 'Tue', 'Wed', 'Thu', 'Fri'][i]}s\n${pct(t.rate)} in office over ${plural(t.n, 'record')}">${pct(t.rate)}</span>`)}`)}</div>
    <div class="scale"><span>${pct(lo)}</span><i style="background:linear-gradient(90deg, color-mix(in srgb, var(--g-700) 12%, var(--g-50)), var(--g-700))"></i><span>${pct(hi)}</span></div></section>`;
}
function lateCard(rs) {
  const by = new Map();
  rs.filter(r => r.status === 'Late').forEach(r => (by.get(r.employee_id) || by.set(r.employee_id, []).get(r.employee_id)).push(r));
  const top = [...by.values()].sort((a, b) => b.length - a.length || lateBy(b) - lateBy(a)).slice(0, 7);
  return html`<section class="card"><div class="card-h"><div><h2>Most late arrivals</h2><span class="sub">Count in period · average minutes after 09:00</span></div></div>
    ${top.length ? html`<ul class="rows">${top.map(l => {
    const r = l[0], notes = l.map(x => x.notes).filter(Boolean), common = notes.sort((a, b) => notes.filter(n => n === b).length - notes.filter(n => n === a).length)[0];
    return html`<li>${avatar(r.employee_id, r.employee_name)}<div class="who"><b>${r.employee_name}</b><small>${r.department}${common ? ` · “${common}”` : ''}</small></div>
        <span class="time">${l.length}×</span><span class="pill s-late">${lateBy(l) != null ? `+${Math.round(lateBy(l))} min` : 'Late'}</span></li>`;
  })}</ul>` : html`<div class="empty"><b>No late arrivals</b><span>Everyone checked in by 09:30 in this period.</span></div>`}</section>`;
}

const VIEWS = {
  overview: { title: 'Overview', render: overview }, mark: { title: 'Mark attendance', render: markView }, records: { title: 'Records', render: recordsView },
  employees: { title: 'Employees', render: employeesView }, reports: { title: 'Reports', render: reportsView },
};

// ---------- overlays: drawer, palette, shortcuts, toast, tooltip ----------
function openDrawer(content) { const d = $('#drawer'); d.innerHTML = content; d.open || d.showModal(); }
function toast(msg, { err, action, key: k } = {}) {
  const box = $('#toasts');
  if (k) box.querySelector(`[data-key="${k}"]`)?.remove();
  const el = document.createElement('div');
  el.className = 'toast' + (err ? ' err' : ''); el.setAttribute('role', err ? 'alert' : 'status'); if (k) el.dataset.key = k;
  el.innerHTML = html`<span>${msg}</span>${action ? html`<button data-undo>${action[0]}</button>` : ''}<button aria-label="Dismiss" data-x>${icon('x', 14)}</button>`;
  el.addEventListener('click', e => { if (e.target.closest('[data-undo]')) action[1](); if (e.target.closest('button')) el.remove(); });
  box.append(el); while (box.children.length > 3) box.firstChild.remove();
  setTimeout(() => el.remove(), action ? 8000 : 4500);
}
const SHORTCUTS = [['Ctrl K', 'Search employees, pages and actions'], ['?', 'Show this list'], ['g then o / m / r / e / p', 'Go to Overview, Mark, Records, Employees, Reports'], ['[', 'Collapse or expand the sidebar'], ['j / k', 'Next / previous employee (Mark attendance)'], ['1 – 5', 'Present, Late, Half-day, Leave, Absent (Mark attendance)'], ['Esc', 'Close a panel or dialog']];
function openKeys() {
  const d = $('#keys');
  d.innerHTML = html`<div class="dh" style="display:flex;justify-content:space-between;align-items:center;padding:20px 24px"><h2 id="keysTitle" style="font-size:20px">Keyboard shortcuts</h2><button class="icon-btn sm bare" data-act="close" aria-label="Close">${icon('x', 18)}</button></div>
    <dl>${SHORTCUTS.map(([k, v]) => html`<dt>${k.split(' ').map(x => ['then', '/', '–'].includes(x) ? ` ${x} ` : html`<kbd>${x}</kbd> `)}</dt><dd>${v}</dd>`)}</dl>`;
  d.showModal();
}
let palItems = [], palSel = 0;
function openPalette() {
  const d = $('#palette');
  d.innerHTML = html`<div class="ps">${icon('search')}<input id="palQ" placeholder="Search employees or jump to a page" aria-label="Search" role="combobox" aria-expanded="true" aria-controls="palList" autocomplete="off"><kbd>Esc</kbd></div><ul id="palList" role="listbox"></ul>`;
  d.showModal(); palFilter('');
}
function palFilter(s) {
  s = s.toLowerCase(); palSel = 0;
  const views = NAV.map(([v, l, ic]) => ({ group: 'Pages', label: l, ic, run: () => (location.hash = '#/' + v) }));
  const acts = [{ label: 'Mark everyone remaining present today', ic: 'check', run: () => allPresent(S.today) }, { label: 'Add employee', ic: 'plus', run: addEmpDrawer },
    { label: 'Export all records as CSV', ic: 'download', run: () => (location.href = '/api/export-csv') }, { label: 'Toggle dark theme', ic: 'moon', run: toggleTheme }, { label: 'Keyboard shortcuts', ic: 'keyboard', run: openKeys }].map(a => ({ ...a, group: 'Actions' }));
  const emps = S.emps.map(e => ({ group: 'Employees', label: e.name, sub: `${e.department} · ${e.employee_id}`, id: e.employee_id, run: () => { location.hash = '#/employees'; empPanel(e.employee_id); } }));
  palItems = [...views, ...acts, ...emps].filter(i => `${i.label} ${i.sub || ''}`.toLowerCase().includes(s)).slice(0, 40);
  let g = '';
  $('#palList').innerHTML = palItems.length ? html`${palItems.map((it, i) => html`${it.group !== g ? html`<li class="ph" role="presentation">${(g = it.group)}</li>` : ''}<li role="option" id="pi-${i}" data-i="${i}" aria-selected="${i === palSel}">${it.id ? avatar(it.id, it.label) : icon(it.ic)}<span>${it.label}</span>${it.sub ? html`<small>${it.sub}</small>` : ''}</li>`)}`
    : html`<li class="ph" role="presentation">Nothing matches “${s}”</li>`;
  palMark();
}
function palMark() { document.querySelectorAll('#palList [role=option]').forEach(li => li.setAttribute('aria-selected', +li.dataset.i === palSel)); $('#palQ').setAttribute('aria-activedescendant', 'pi-' + palSel); $('#pi-' + palSel)?.scrollIntoView({ block: 'nearest' }); }
function palRun(i) { const it = palItems[i]; if (!it) return; $('#palette').close(); it.run(); }

function showTip(el) {
  const tip = $('#tip');
  if (el.hasAttribute('data-tip-rail') && !(document.documentElement.classList.contains('rail') && innerWidth >= 900)) return;
  tip.textContent = el.dataset.tip; tip.hidden = false;
  const r = el.getBoundingClientRect(), t = tip.getBoundingClientRect(), side = el.hasAttribute('data-tip-rail');
  const x = side ? r.right + 12 : Math.min(innerWidth - t.width - 8, Math.max(8, r.left + r.width / 2 - t.width / 2));
  const y = side ? r.top + r.height / 2 - t.height / 2 : r.top - t.height - 8 < 8 ? r.bottom + 8 : r.top - t.height - 8;
  tip.style.left = x + 'px'; tip.style.top = y + 'px';
}

// ---------- chrome actions ----------
const store = (k, v) => { try { localStorage.setItem(k, v); } catch { } };
function toggleTheme() { const r = document.documentElement, dark = r.dataset.theme !== 'dark'; r.dataset.theme = dark ? 'dark' : 'light'; store('rollbase.theme', r.dataset.theme); themeIcon(); }
const themeIcon = () => { const dark = document.documentElement.dataset.theme === 'dark'; $('#themeBtn').innerHTML = icon(dark ? 'sun' : 'moon'); $('#themeBtn').setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme'); };
function setMobileNav(open) { document.documentElement.classList.toggle('drawer-open', open); $('#scrim').hidden = !open; renderChrome(route().view); if (open) $('#nav a')?.focus(); }
function toggleSidebar() {
  if (innerWidth < 900) return setMobileNav(!document.documentElement.classList.contains('drawer-open'));
  store('rollbase.rail', document.documentElement.classList.toggle('rail') ? '1' : '0'); renderChrome(route().view);
}

// ---------- event wiring (delegated) ----------
const ACT = {
  week: a => { S.weekOff += +a.dataset.d; render(); },
  allPresent: a => { a.disabled = true; allPresent(a.dataset.date); },
  mark: a => setStatus(a.dataset.id, a.dataset.s),
  q: a => setQ({ [a.dataset.k]: a.dataset.v, ...(a.dataset.k !== 'page' && { page: '' }) }),
  status: a => { const cur = (route().q.status || '').split(',').filter(Boolean), v = a.dataset.v; setQ({ status: (cur.includes(v) ? cur.filter(x => x !== v) : [...cur, v]).join(','), page: '' }); },
  clear: () => { const r = route(); history.replaceState(null, '', link(r.view, r.view === 'mark' && r.q.date ? { date: r.q.date } : {})); render(); },
  edit: a => editDrawer(a.dataset.id, a.dataset.date),
  del: a => del(a.dataset.id, a.dataset.date),
  emp: a => empPanel(a.dataset.id),
  addEmp: addEmpDrawer,
  close: a => a.closest('dialog').close(),
  keys: openKeys,
};
document.addEventListener('click', e => {
  const a = e.target.closest('[data-act]');
  if (a && ACT[a.dataset.act]) ACT[a.dataset.act](a, e);
  if (e.target.closest('#nav a') && innerWidth < 900) setMobileNav(false);
  const li = e.target.closest('#palList [data-i]'); if (li) palRun(+li.dataset.i);
  if (e.target.matches('dialog')) e.target.close(); // click on backdrop
});
document.addEventListener('input', e => {
  if (e.target.id === 'palQ') return palFilter(e.target.value);
  if (e.target.type === 'search') setQ({ q: e.target.value, page: '' });
});
document.addEventListener('change', e => {
  const t = e.target;
  if (t.dataset.time) setTime(t.dataset.time, t.value);
  else if (t.dataset.q && t.type !== 'search') setQ({ [t.dataset.q]: t.value, page: '' });
});
document.addEventListener('submit', e => {
  const f = e.target; e.preventDefault();
  if (f.dataset.form === 'add') submitAdd(f);
  if (f.dataset.form === 'edit') {
    const r = byKey.get(key(f.dataset.id, f.dataset.date)), v = Object.fromEntries(new FormData(f));
    if (!ATTENDED.has(v.status)) v.checkin_time = v.checkout_time = '';
    $('#drawer').close(); save({ ...r, ...v }, `Updated ${r.employee_name} · ${fmt(r.date)}`);
  }
});
let gPending = false;
document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); return $('#palette').open ? $('#palette').close() : openPalette(); }
  if ($('#palette').open && e.target.id === 'palQ') {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); palSel = (palSel + (e.key === 'ArrowDown' ? 1 : -1) + palItems.length) % palItems.length; palMark(); }
    if (e.key === 'Enter') { e.preventDefault(); palRun(palSel); }
    return;
  }
  if (e.key === 'Escape' && document.documentElement.classList.contains('drawer-open')) return setMobileNav(false);
  if (e.target.closest('input, select, textarea, dialog[open]') || e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.key === '?') return openKeys();
  if (gPending) { gPending = false; const v = { o: 'overview', m: 'mark', r: 'records', e: 'employees', p: 'reports' }[e.key]; if (v) location.hash = '#/' + v; return; }
  if (e.key === 'g') { gPending = true; setTimeout(() => (gPending = false), 1200); return; }
  if (e.key === '[') return toggleSidebar();
  if (route().view !== 'mark') return;
  const rows = [...document.querySelectorAll('.mrow')], cur = e.target.closest?.('.mrow'), i = rows.indexOf(cur);
  if (e.key === 'j' || e.key === 'k') { e.preventDefault(); rows[Math.max(0, Math.min(rows.length - 1, i + (e.key === 'j' ? 1 : -1)))]?.focus(); }
  if (cur && /^[1-5]$/.test(e.key)) setStatus(cur.dataset.id, STATUSES[e.key - 1]);
});
document.addEventListener('mouseover', e => { const el = e.target.closest('[data-tip]'); el ? showTip(el) : ($('#tip').hidden = true); });
document.addEventListener('focusin', e => { const el = e.target.closest('[data-tip]'); el ? showTip(el) : ($('#tip').hidden = true); });
document.addEventListener('scroll', () => ($('#tip').hidden = true), true);
let lastView = route().view;
addEventListener('hashchange', () => { const v = route().view; if (v !== lastView) { scrollTo(0, 0); lastView = v; $('#drawer').open && $('#drawer').close(); } render(); });
$('#hamburger').innerHTML = icon('menu'); $('#hamburger').onclick = toggleSidebar;
$('#scrim').onclick = () => setMobileNav(false);
$('#searchBtn').innerHTML = html`${icon('search', 18)}<span>Search employees or jump to…</span><kbd>Ctrl K</kbd>`; $('#searchBtn').onclick = openPalette;
$('#themeBtn').onclick = toggleTheme; themeIcon();
render(); poll(); setInterval(poll, 5000);
