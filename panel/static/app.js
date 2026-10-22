/* COD Panel - single page admin UI (no build step, vanilla JS) */
'use strict';

const S = {
  user: null, needsSetup: false, version: '',
  view: 'dashboard', games: [], instances: [], system: null,
  inst: null, tab: 'overview', mapsData: null, mapsGame: null, mapsMod: null,
  events: [], ws: null, timer: null, draft: null,
};

const ICON = {
  dash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><rect x="3" y="3" width="7" height="9" rx="2"/><rect x="14" y="3" width="7" height="5" rx="2"/><rect x="14" y="12" width="7" height="9" rx="2"/><rect x="3" y="16" width="7" height="5" rx="2"/></svg>',
  server: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><circle cx="7.5" cy="7.5" r="1" fill="currentColor"/><circle cx="7.5" cy="16.5" r="1" fill="currentColor"/></svg>',
  download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M12 3v12m0 0l4-4m-4 4l-4-4"/><path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"/></svg>',
  map: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14M15 6v14"/></svg>',
  log: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M5 4h14v16H5z"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>',
  cog: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.3 1.9l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.9-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.9.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.9 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.9l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.9.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.9-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.9V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z"/></svg>',
  play: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 4l12 8-12 8z"/></svg>',
  stop: '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
  restart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-3-6.7"/><path d="M21 3v6h-6"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 5v14M5 12h14"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13"/></svg>',
  terminal: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M13 15h4"/></svg>',
};

/* ---------------- api ---------------- */
async function api(method, path, body, isForm) {
  const opt = { method, headers: {} };
  if (body && !isForm) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
  if (isForm) opt.body = body;
  const res = await fetch(path, opt);
  if (res.status === 401) { S.user = null; render(); throw new Error('Bejelentkezés szükséges.'); }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }
  if (!res.ok) throw new Error((data && data.detail) || res.statusText);
  return data;
}
const GET = p => api('GET', p);
const POST = (p, b) => api('POST', p, b);
const PATCH = (p, b) => api('PATCH', p, b);
const DEL = p => api('DELETE', p);

/* ---------------- utils ---------------- */
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));

function toast(msg, kind) {
  const el = document.createElement('div');
  el.className = 'toast ' + (kind || '');
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), kind === 'err' ? 7000 : 3800);
}
const fail = e => toast(e.message || String(e), 'err');

function uptime(sec) {
  if (!sec) return '-';
  const d = Math.floor(sec / 86400), h = Math.floor(sec % 86400 / 3600), m = Math.floor(sec % 3600 / 60);
  return (d ? d + 'n ' : '') + (h ? h + 'ó ' : '') + m + 'p';
}
function stateBadge(st) {
  if (!st) return '<span class="badge off"><i class="dot"></i>leállítva</span>';
  if (st.state === 'running') return '<span class="badge on"><i class="dot on"></i>fut</span>';
  if (st.state === 'crashed') return '<span class="badge err"><i class="dot err"></i>összeomlott</span>';
  if (st.state === 'starting') return '<span class="badge info"><i class="dot"></i>indul</span>';
  if (st.state === 'stopping') return '<span class="badge info"><i class="dot"></i>leáll</span>';
  return '<span class="badge off"><i class="dot"></i>leállítva</span>';
}
/* Automatikus frissítés: MINDIG csak egy élő időzítő lehet. (Korábban az
   időzítőből hívott nézet új setInterval-t indított a régi törlése nélkül,
   így a futó időzítők száma 1.5 másodpercenként megduplázódott.) */
function stopPoll() {
  if (S.timer) { clearInterval(S.timer); S.timer = null; }
}

function startPoll(ms, view, fn) {
  stopPoll();
  S.timer = setInterval(() => {
    if (S.view !== view || !S.user) return stopPoll();
    if (document.hidden) return;          // háttérben lévő fülön ne dolgozzunk
    fn();
  }, ms);
}

function modal(title, bodyHtml, footHtml) {
  $('#modal').innerHTML = `<div class="modal-bg"><div class="modal">
    <header><h2>${esc(title)}</h2><div class="spacer"></div>
      <button class="btn sm ghost" id="m-x">&times;</button></header>
    <div class="body">${bodyHtml}</div>
    ${footHtml ? `<footer>${footHtml}</footer>` : ''}
  </div></div>`;
  $('#m-x').onclick = closeModal;
  $('.modal-bg').onclick = e => { if (e.target.classList.contains('modal-bg')) closeModal(); };
}
const closeModal = () => { $('#modal').innerHTML = ''; };

/* ---------------- boot ---------------- */
async function boot() {
  try {
    const me = await GET('/api/me');
    S.user = me.user; S.needsSetup = me.needs_setup; S.version = me.version;
  } catch (e) { /* ignore */ }
  window.addEventListener('hashchange', route);
  route();
}

function route() {
  const h = (location.hash || '#/dashboard').slice(2).split('/');
  S.view = h[0] || 'dashboard';
  if (S.view === 'server') { S.instId = h[1]; S.tab = h[2] || 'overview'; }
  if (S.view === 'maps') { S.mapsGame = h[1] || null; }
  render();
}
const go = path => { location.hash = '#/' + path; };

/* ---------------- render ---------------- */
async function render() {
  if (S.ws) { S.ws.close(); S.ws = null; }
  stopPoll();
  if (!S.user) return renderLogin();

  $('#root').innerHTML = `<div id="app">${sidebar()}<main id="main"><div class="login-wrap"><span class="loading"></span></div></main></div>`;
  $$('.nav-item').forEach(el => el.onclick = () => go(el.dataset.go));
  $('#logout').onclick = async () => { await POST('/api/logout'); S.user = null; render(); };

  try {
    if (S.view === 'dashboard') await viewDashboard();
    else if (S.view === 'servers') await viewServers();
    else if (S.view === 'server') await viewServer();
    else if (S.view === 'games') await viewGames();
    else if (S.view === 'maps') await viewMaps();
    else if (S.view === 'log') await viewLog();
    else if (S.view === 'settings') await viewSettings();
    else go('dashboard');
  } catch (e) { $('#main').innerHTML = `<div class="empty"><h3>Hiba</h3><p>${esc(e.message)}</p></div>`; }
}

function sidebar() {
  const item = (id, label, icon) =>
    `<div class="nav-item ${S.view === id ? 'active' : ''}" data-go="${id}">${icon}<span>${label}</span></div>`;
  return `<aside class="sidebar">
    <div class="brand"><div class="brand-logo">CP</div>
      <div><b>COD Panel</b><span>v${esc(S.version)} • ${esc(S.user)}</span></div></div>
    ${item('dashboard', 'Áttekintés', ICON.dash)}
    ${item('servers', 'Szerverek', ICON.server)}
    <div class="nav-sep">Tartalom</div>
    ${item('games', 'Játékfájlok', ICON.download)}
    ${item('maps', 'Map kezelő', ICON.map)}
    <div class="nav-sep">Rendszer</div>
    ${item('log', 'Napló', ICON.log)}
    ${item('settings', 'Beállítások', ICON.cog)}
    <div class="sidebar-foot">
      <button class="btn sm ghost" id="logout" style="width:100%">Kijelentkezés</button>
    </div>
  </aside>`;
}


/* ---------------- map választó (bélyegképekkel) ---------------- */
const mapImgUrl = (gid, m) => `/api/games/${gid}/mapimage/${encodeURIComponent(m)}`;

function mapOf(maps, name) {
  return (maps || []).find(m => m.map === name) || { map: name, label: name, source: 'stock' };
}

function mapCardHtml(gid, m, selected) {
  const label = m.label || m.map;
  return `<div class="mapcard ${selected ? 'sel' : ''}" data-map="${esc(m.map)}">
    <div class="mapthumb"><span class="ph">${esc(label.slice(0, 2).toUpperCase())}</span>
      <img loading="lazy" alt="" src="${mapImgUrl(gid, m.map)}" onerror="this.remove()"></div>
    <div class="mapmeta"><b>${esc(label)}</b><span class="mono">${esc(m.map)}</span>
      ${m.source === 'custom' ? '<span class="badge accent">custom</span>' : ''}</div></div>`;
}

/* gomb, ami a kiválasztott mapot mutatja képpel; kattintásra megnyitja a választót */
function mapButtonHtml(gid, m, id) {
  const label = m.label || m.map;
  return `<button type="button" class="mapbtn" id="${id}" data-value="${esc(m.map)}">
    <img class="thumb" alt="" src="${mapImgUrl(gid, m.map)}" onerror="this.style.visibility='hidden'">
    <span class="lines"><b>${esc(label)}</b><span class="mono">${esc(m.map)}</span></span>
    <span class="chev">▼</span></button>`;
}

function pickMap(gid, maps, current) {
  return new Promise(resolve => {
    let done = false;
    const finish = v => { if (!done) { done = true; closeModal(); resolve(v); } };
    modal('Map választása', `
      <input id="mapsearch" placeholder="Keresés név vagy kód szerint… (pl. Toujane)">
      <div class="mapgrid" id="mapgrid">${maps.map(m => mapCardHtml(gid, m, m.map === current)).join('')}</div>
      <div class="help" style="margin-top:12px">A képek a saját játékfájljaidból származnak.
        Amelyiknél nincs kép, ott a Map kezelőben feltölthetsz sajátot.</div>`,
      `<button class="btn ghost" id="m-cancel">Mégse</button>`);
    $('#m-cancel').onclick = () => finish(null);
    $('#m-x').onclick = () => finish(null);
    $('.modal-bg').onclick = e => { if (e.target.classList.contains('modal-bg')) finish(null); };
    $$('#mapgrid .mapcard').forEach(c => c.onclick = () => finish(c.dataset.map));
    const search = $('#mapsearch');
    search.oninput = () => {
      const q = search.value.toLowerCase();
      $$('#mapgrid .mapcard').forEach(c => {
        const hit = c.textContent.toLowerCase().includes(q);
        c.style.display = hit ? '' : 'none';
      });
    };
    search.focus();
  });
}

/* a mapbtn gombok bekötése: kattintásra választó, utána frissíti a gomb tartalmát */
function wireMapButtons(gid, maps) {
  $$('.mapbtn').forEach(btn => btn.onclick = async () => {
    const picked = await pickMap(gid, maps, btn.dataset.value);
    if (!picked) return;
    btn.dataset.value = picked;
    const m = mapOf(maps, picked);
    btn.querySelector('.lines').innerHTML =
      `<b>${esc(m.label || m.map)}</b><span class="mono">${esc(m.map)}</span>`;
    const img = btn.querySelector('img');
    img.style.visibility = '';
    img.onerror = () => { img.style.visibility = 'hidden'; };
    img.src = mapImgUrl(gid, picked);
    if (btn.dataset.onpick === 'rotation') btn.dispatchEvent(new CustomEvent('mappicked'));
  });
}

/* ---------------- login ---------------- */
function renderLogin() {
  const setup = S.needsSetup;
  $('#root').innerHTML = `<div class="login-wrap"><form class="login" id="lf">
    <div class="brand" style="justify-content:center"><div class="brand-logo">CP</div></div>
    <h2>${setup ? 'Panel beállítása' : 'COD Panel'}</h2>
    <p class="sub">${setup ? 'Add meg az admin felhasználót és jelszót (min. 8 karakter).'
      : 'Call of Duty szerver adminisztráció'}</p>
    <div class="field"><label>Felhasználónév</label><input id="u" autocomplete="username" required></div>
    <div class="field"><label>Jelszó</label><input id="p" type="password" autocomplete="current-password" required></div>
    <button class="btn primary" style="width:100%" type="submit">${setup ? 'Létrehozás' : 'Belépés'}</button>
  </form></div>`;
  $('#lf').onsubmit = async ev => {
    ev.preventDefault();
    const body = { username: $('#u').value, password: $('#p').value };
    try {
      const r = await POST(setup ? '/api/setup' : '/api/login', body);
      S.user = r.user; S.needsSetup = false;
      toast('Üdv, ' + r.user + '!', 'ok');
      render();
    } catch (e) { fail(e); }
  };
}

/* ---------------- dashboard ---------------- */
async function viewDashboard() {
  const [sys, list, events] = await Promise.all([GET('/api/system'), GET('/api/instances'), GET('/api/events?limit=12')]);
  S.system = sys; S.instances = list;
  const stat = (label, value, sub) => `<div class="card stat"><span class="label">${label}</span>
    <span class="value">${value}${sub ? ` <small>${sub}</small>` : ''}</span></div>`;
  const players = list.reduce((a, i) => a + (i.status.players || 0), 0);
  $('#main').innerHTML = `
    <div class="topbar"><div><h1>Áttekintés</h1>
      <div class="sub">${esc(sys.data_dir)}</div></div><div class="spacer"></div>
      <button class="btn primary" id="new">${ICON.plus} Új szerver</button></div>
    <div class="grid c4" style="margin-bottom:18px">
      ${stat('Futó szerverek', sys.running, '/ ' + sys.instances)}
      ${stat('Játékosok', players, 'online')}
      ${stat('Szabad memória', sys.mem_free_mb, 'MB / ' + sys.mem_total_mb)}
      ${stat('Szabad hely', sys.disk_free_gb, 'GB / ' + sys.disk_total_gb)}
    </div>
    ${libWarning((sys.libs && sys.libs.missing) || [], null)}
    ${sys.lib32 ? '' : `<div class="card" style="border-color:rgba(255,93,93,.4);margin-bottom:18px">
      <b style="color:var(--red)">Figyelem:</b> nem találom a 32 bites libeket (lib32gcc / libstdc++ i386).
      A COD szerverek 32 bites binárisok, ezek nélkül nem indulnak.
      <div class="mono" style="margin-top:8px">dpkg --add-architecture i386 &amp;&amp; apt update &amp;&amp; apt install -y lib32gcc-s1 lib32stdc++6</div></div>`}
    <div class="grid c2">
      <div>${list.length ? list.map(srvCard).join('') : `<div class="card empty">
        <h3>Még nincs szerver</h3><p>Hozz létre egyet, a játékfájlokat a panel letölti.</p></div>`}</div>
      <div class="card pad0"><div style="padding:18px 18px 0"><h3>Legutóbbi események</h3></div>
        <table><tbody>${events.map(e => `<tr><td style="width:120px;color:var(--muted)" class="mono">
          ${new Date(e.ts * 1000).toLocaleTimeString('hu-HU')}</td><td>${esc(e.text)}</td></tr>`).join('')
        || '<tr><td style="color:var(--muted)">Nincs esemény.</td></tr>'}</tbody></table></div>
    </div>`;
  wireServerCards();
  $$('[data-libs]').forEach(b => b.onclick = () => installLibs(b, b.dataset.libs || null));
  $('#new').onclick = newServerModal;
  startPoll(6000, 'dashboard', () => viewDashboard().catch(() => {}));
}

function srvCard(i) {
  const st = i.status || {};
  return `<div class="card srv-card" style="margin-bottom:16px">
    <div class="srv-top">
      <div style="flex:1;min-width:0">
        <div class="title" data-open="${i.id}">${esc(i.name)}</div>
        <div class="srv-meta">
          <span class="badge accent">${esc(i.game_short)}</span>
          <span class="mono">${esc(i.ip)}:${i.port}</span>
          <span>${esc(st.map || i.map)}</span>
          <span>${esc(st.gametype || i.gametype)}</span>
        </div>
      </div>
      ${stateBadge(st)}
    </div>
    <div class="kv">
      <span class="k">Játékos</span><span>${st.players != null ? st.players : 0} / ${i.maxplayers}</span>
      <span class="k">Uptime</span><span>${uptime(st.uptime)}</span>
      <span class="k">Memória</span><span>${st.rss_mb ? st.rss_mb + ' MB' : '-'}</span>
    </div>
    <div class="bar"><i style="width:${Math.min(100, (st.players || 0) / i.maxplayers * 100)}%"></i></div>
    <div class="btn-row">
      ${st.state === 'running'
      ? `<button class="btn sm red" data-act="stop" data-id="${i.id}">${ICON.stop} Stop</button>
           <button class="btn sm" data-act="restart" data-id="${i.id}">${ICON.restart} Újra</button>`
      : `<button class="btn sm green" data-act="start" data-id="${i.id}">${ICON.play} Indítás</button>`}
      <button class="btn sm ghost" data-open="${i.id}">Kezelés</button>
      <div class="spacer"></div>
      ${i.installed ? '' : '<span class="badge err">játékfájlok hiányoznak</span>'}
    </div></div>`;
}

function wireServerCards() {
  $$('[data-open]').forEach(el => el.onclick = () => go('server/' + el.dataset.open));
  $$('[data-act]').forEach(el => el.onclick = async () => {
    const { act, id } = el.dataset;
    el.disabled = true; el.innerHTML = '<span class="loading"></span>';
    try { await POST(`/api/instances/${id}/${act}`); toast('Rendben: ' + act, 'ok'); }
    catch (e) { fail(e); }
    render();
  });
}

/* ---------------- servers ---------------- */
async function viewServers() {
  const list = await GET('/api/instances');
  S.instances = list;
  $('#main').innerHTML = `
    <div class="topbar"><div><h1>Szerverek</h1><div class="sub">${list.length} példány</div></div>
      <div class="spacer"></div><button class="btn primary" id="new">${ICON.plus} Új szerver</button></div>
    ${list.length ? `<div class="grid c2">${list.map(srvCard).join('')}</div>`
      : `<div class="card empty"><h3>Nincs szerver</h3>
         <p>Kattints az „Új szerver” gombra: válassz játékot, módot, mapot — a panel elintézi a többit.</p></div>`}`;
  wireServerCards();
  $('#new').onclick = newServerModal;
  startPoll(7000, 'servers', () => viewServers().catch(() => {}));
}

async function newServerModal() {
  const games = S.games.length ? S.games : (S.games = await GET('/api/games'));
  const cards = games.map(g => `<label class="chip" style="display:block;padding:12px">
      <input type="radio" name="g" value="${g.id}" ${g.id === 'cod2' ? 'checked' : ''} style="margin-right:8px">
      <b>${esc(g.name)}</b>
      <div style="color:var(--muted);font-size:12px;margin-top:4px">
        ${g.installed ? '<span class="badge on">telepítve</span>' : '<span class="badge off">szerverfájlok nincsenek telepítve</span>'}
        &nbsp;${esc(g.executable)} • ${g.gametypes.length} játékmód</div></label>`).join('');
  modal('Új szerver létrehozása', `
    <div class="field"><label>Játék</label><div class="grid" style="gap:8px">${cards}</div></div>
    <div class="form-grid">
      <div class="field"><label>Szerver neve (hostname)</label><input id="f-name" value="Új COD szerver"></div>
      <div class="field"><label>Azonosító (könyvtár/cfg név)</label><input id="f-id" placeholder="automatikus"></div>
      <div class="field"><label>IP</label><input id="f-ip" value="0.0.0.0"></div>
      <div class="field"><label>Port</label><input id="f-port" type="number" value="28960"></div>
      <div class="field"><label>Max játékos</label><input id="f-slots" type="number" value="20"></div>
      <div class="field"><label>RCON jelszó</label><input id="f-rcon" value="${Math.random().toString(36).slice(2, 10)}"></div>
      <div class="field"><label>Játékmód</label><select id="f-gt"></select></div>
      <div class="field"><label>Induló map</label><select id="f-map"></select></div>
      <div class="field"><label>Mod (fs_game, opcionális)</label><input id="f-mod" placeholder="pl. mods/mymod"></div>
    </div>
    <label class="switch"><input type="checkbox" id="f-autostart"><span class="track"></span>
      <span>Induljon a panel indulásakor</span></label>`,
    `<button class="btn ghost" id="m-cancel">Mégse</button>
     <button class="btn primary" id="m-create">Létrehozás</button>`);

  const syncGame = () => {
    const gid = $('input[name=g]:checked').value;
    const g = games.find(x => x.id === gid);
    $('#f-gt').innerHTML = g.gametypes.map(([v, l]) => `<option value="${v}" ${v === g.default_gametype ? 'selected' : ''}>${esc(l)} (${v})</option>`).join('');
    $('#f-map').innerHTML = g.stock_maps.map(m =>
      `<option value="${m}" ${m === g.default_map ? 'selected' : ''}>${esc((g.map_names || {})[m] || m)} — ${m}</option>`).join('');
    $('#f-port').value = g.default_port;
    $('#f-slots').value = g.default_maxplayers;
  };
  $$('input[name=g]').forEach(r => r.onchange = syncGame);
  syncGame();
  $('#m-cancel').onclick = closeModal;
  $('#m-create').onclick = async () => {
    const body = {
      game: $('input[name=g]:checked').value,
      name: $('#f-name').value, id: $('#f-id').value || undefined,
      ip: $('#f-ip').value, port: +$('#f-port').value, maxplayers: +$('#f-slots').value,
      gametype: $('#f-gt').value, map: $('#f-map').value, mod: $('#f-mod').value,
      hostname: $('#f-name').value, rcon_password: $('#f-rcon').value,
      autostart: $('#f-autostart').checked,
    };
    try {
      const inst = await POST('/api/instances', body);
      closeModal(); toast('Szerver létrehozva: ' + inst.name, 'ok');
      go('server/' + inst.id);
    } catch (e) { fail(e); }
  };
}

/* ---------------- server detail ---------------- */
async function viewServer() {
  const i = await GET('/api/instances/' + S.instId);
  S.inst = i;
  const st = i.status || {};
  const tab = (id, label) => `<div class="tab ${S.tab === id ? 'active' : ''}" data-tab="${id}">${label}</div>`;
  $('#main').innerHTML = `
    <div class="topbar">
      <div><h1>${esc(i.name)}</h1>
        <div class="sub">${esc(i.game_name)} • <span class="mono">${esc(i.ip)}:${i.port}</span> • id: ${esc(i.id)}</div></div>
      <div class="spacer"></div>${stateBadge(st)}
      <div class="btn-row">
        ${st.state === 'running'
      ? `<button class="btn red" data-act="stop" data-id="${i.id}">${ICON.stop} Stop</button>
             <button class="btn" data-act="restart" data-id="${i.id}">${ICON.restart} Újraindítás</button>`
      : `<button class="btn green" data-act="start" data-id="${i.id}">${ICON.play} Indítás</button>`}
      </div>
    </div>
    <div class="tabs">
      ${tab('overview', 'Áttekintés')}${tab('settings', 'Beállítások')}${tab('rotation', 'Map rotáció')}
      ${tab('maps', 'Mapok')}${tab('console', 'Konzol')}${tab('cfg', 'cfg / parancs')}
    </div><div id="tabbody"></div>`;
  $$('[data-tab]').forEach(el => el.onclick = () => go(`server/${i.id}/${el.dataset.tab}`));
  wireServerCards();
  const body = $('#tabbody');
  if (S.tab === 'overview') tabOverview(body, i);
  else if (S.tab === 'settings') tabSettings(body, i);
  else if (S.tab === 'rotation') tabRotation(body, i);
  else if (S.tab === 'maps') tabMapsEmbed(body, i);
  else if (S.tab === 'console') tabConsole(body, i);
  else if (S.tab === 'cfg') tabCfg(body, i);
}

function tabOverview(el, i) {
  const st = i.status || {};
  const pl = st.playerlist || [];
  el.innerHTML = `${st.missing_lib ? libWarning([st.missing_lib], i.game) : ''}<div class="grid c2">
    <div class="card"><h3>Állapot</h3><div class="kv">
      <span class="k">Állapot</span><span>${stateBadge(st)}</span>
      <span class="k">PID</span><span class="mono">${st.pid || '-'}</span>
      <span class="k">Uptime</span><span>${uptime(st.uptime)}</span>
      <span class="k">Memória</span><span>${st.rss_mb ? st.rss_mb + ' MB' : '-'}</span>
      <span class="k">Újraindítások</span><span>${st.restarts || 0}</span>
      <span class="k">Jelenlegi map</span><span>${esc(st.map || i.map)}</span>
      <span class="k">Játékmód</span><span>${esc(st.gametype || i.gametype)}</span>
      <span class="k">Játékos</span><span>${st.players != null ? st.players : 0} / ${i.maxplayers}</span>
      <span class="k">Mod</span><span>${esc(i.mod || '(nincs)')}</span>
      <span class="k">Autostart</span><span>${i.autostart ? 'igen' : 'nem'}</span>
      <span class="k">Auto újraindítás</span><span>${i.autorestart ? 'igen' : 'nem'}</span>
    </div>
    ${st.exit_code != null && st.state !== 'running' ? `<div class="hr"></div>
      <div style="color:var(--muted);font-size:13px">Utolsó kilépési kód: ${st.exit_code}</div>` : ''}
    </div>
    <div class="card pad0"><div style="padding:18px 18px 0"><h3>Játékosok (${pl.length})</h3></div>
      <table><thead><tr><th>Név</th><th>Pont</th><th>Ping</th><th></th></tr></thead><tbody>
      ${pl.length ? pl.map(p => `<tr><td>${esc(p.name)}</td><td>${p.score}</td><td>${p.ping}</td>
        <td style="text-align:right"><button class="btn sm red" data-kick="${esc(p.name)}">Kick</button></td></tr>`).join('')
      : '<tr><td colspan="4" style="color:var(--muted)">Nincs játékos a szerveren.</td></tr>'}
      </tbody></table></div>
    <div class="card"><h3>Gyors műveletek</h3>
      <div class="btn-row">
        <button class="btn sm" data-cmd="map_rotate">Következő map</button>
        <button class="btn sm" data-cmd="fast_restart">Kör újraindítása</button>
        <button class="btn sm" data-cmd="status">status</button>
        <button class="btn sm" data-cmd="serverinfo">serverinfo</button>
      </div>
      <div class="hr"></div>
      <div class="field"><label>Map váltás azonnal</label>
        <div class="inline"><div style="flex:1;min-width:180px">${mapButtonHtml(i.game, mapOf(i.maps, i.map), 'qmap')}</div>
        <select id="qgt">${i.gametypes.map(([v, l]) => `<option value="${v}" ${v === i.gametype ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select>
        <button class="btn primary" id="qgo">Váltás</button></div>
        <div class="help">A váltás élőben történik (rcon/konzol), a cfg nem módosul.</div></div>
    </div>
    <div class="card"><h3>Veszélyzóna</h3>
      <p style="color:var(--muted);font-size:13px">A szerver példány és a hozzá tartozó cfg törlése. A játékfájlok és a mapok megmaradnak.</p>
      <button class="btn red" id="del">${ICON.trash} Szerver törlése</button></div>
  </div>`;
  const send = async (cmd) => {
    try { await POST(`/api/instances/${i.id}/command`, { command: cmd, via: 'stdin' }); toast('Elküldve: ' + cmd, 'ok'); }
    catch (e) {
      try { await POST(`/api/instances/${i.id}/command`, { command: cmd, via: 'rcon' }); toast('RCON: ' + cmd, 'ok'); }
      catch (e2) { fail(e2); }
    }
  };
  $$('[data-libs]').forEach(b => b.onclick = () => installLibs(b, b.dataset.libs || null));
  $$('[data-cmd]').forEach(b => b.onclick = () => send(b.dataset.cmd));
  $$('[data-kick]').forEach(b => b.onclick = () => send(`clientkick ${b.dataset.kick}`));
  wireMapButtons(i.game, i.maps);
  $('#qgo').onclick = () => send(`g_gametype ${$('#qgt').value}; map ${$('#qmap').dataset.value}`);
  $('#del').onclick = async () => {
    if (!confirm(`Biztosan törlöd a(z) "${i.name}" szervert?`)) return;
    try { await DEL('/api/instances/' + i.id); toast('Törölve.', 'ok'); go('servers'); } catch (e) { fail(e); }
  };
}

function toggleHtml(attr, key, active) {
  return `<label class="switch sm" title="Ha kikapcsolod, a panel egyáltalán nem írja bele a cfg-be">
    <input type="checkbox" ${attr}="${key}" ${active ? 'checked' : ''}><span class="track"></span>
    <span class="sw-text">${active ? 'aktív' : 'kikapcsolva'}</span></label>`;
}

function wireToggles() {
  $$('[data-toggle], [data-gt-toggle], [data-limit-toggle]').forEach(t => {
    t.onchange = () => {
      const box = t.closest('.dvar');
      if (box) box.classList.toggle('off', !t.checked);
      const txt = t.parentElement.querySelector('.sw-text');
      if (txt) txt.textContent = t.checked ? 'aktív' : 'kikapcsolva';
    };
  });
}

/* one dvar: name + on/off switch + value + plain-language description */
function field(f, val, off) {
  const v = val != null ? val : (f.default || '');
  const id = 'dv-' + f.key;
  const active = !off.has(f.key);
  let input;
  if (f.type === 'bool') {
    input = `<select id="${id}" data-key="${f.key}">
      <option value="1" ${String(v) === '1' ? 'selected' : ''}>Bekapcsolva (1)</option>
      <option value="0" ${String(v) !== '1' ? 'selected' : ''}>Kikapcsolva (0)</option></select>`;
  } else if (f.type === 'select') {
    input = `<select id="${id}" data-key="${f.key}">${f.options.map(([ov, ol]) =>
      `<option value="${ov}" ${String(v) === ov ? 'selected' : ''}>${esc(ol)} (${ov})</option>`).join('')}</select>`;
  } else {
    const t = f.type === 'int' ? 'number' : 'text';
    input = `<input id="${id}" data-key="${f.key}" type="${t}" value="${esc(v)}">`;
  }
  return `<div class="dvar ${active ? '' : 'off'}">
    <div class="dvar-head">
      <div class="names"><span class="dvar-label">${esc(f.label)}</span><span class="mono dvar-key">${f.key}</span></div>
      ${toggleHtml('data-toggle', f.key, active)}
    </div>
    ${input}
    <div class="desc">${esc(f.desc || '')}</div>
    ${f.help ? `<div class="desc tip">${esc(f.help)}</div>` : ''}</div>`;
}

/* a plain start-parameter block (no dvar toggle, but same look + description) */
function baseField(label, key, inputHtml, desc) {
  return `<div class="dvar">
    <div class="dvar-head"><div class="names"><span class="dvar-label">${esc(label)}</span>
      ${key ? `<span class="mono dvar-key">${key}</span>` : ''}</div></div>
    ${inputHtml}<div class="desc">${esc(desc)}</div></div>`;
}

function tabSettings(el, i) {
  const off = new Set(i.dvars_off || []);
  const gtOn = i.gametype_enabled !== false;
  const limits = i.limits || {};
  const limitFields = i.limit_dvars.map(key => {
    const full = `scr_${i.gametype}_${key}`;
    const on = limits[full] != null && limits[full] !== '';
    return `<div class="dvar ${on ? '' : 'off'}">
      <div class="dvar-head"><div class="names"><span class="dvar-label">${esc(key)}</span>
        <span class="mono dvar-key">${full}</span></div>
        ${toggleHtml('data-limit-toggle', full, on)}</div>
      <input data-limit="${full}" value="${esc(limits[full] || '')}" placeholder="pl. 20">
      <div class="desc">${esc((i.limit_desc || {})[key] || '')}</div></div>`;
  }).join('');

  el.innerHTML = `
    <div class="card" style="margin-bottom:16px"><h3>Indítási paraméterek</h3>
      <div class="help" style="margin-bottom:14px">Ezek a szerver parancssorába kerülnek
        (<span class="mono">+set ...</span>), nem a cfg-be.</div>
      <div class="dvar-grid">
        ${baseField('Panel-beli név', '', `<input id="s-name" value="${esc(i.name)}">`,
    'Csak a panelen belüli megnevezés. A játékosok a lenti sv_hostname értéket látják.')}
        ${baseField('IP cím', 'net_ip', `<input id="s-ip" value="${esc(i.ip)}">`,
      'Melyik hálózati címen figyeljen a szerver. 0.0.0.0 = az összes elérhető cím.')}
        ${baseField('Port', 'net_port', `<input id="s-port" type="number" value="${i.port}">`,
        'A szerver UDP portja. Több szerver esetén mindegyiknek más port kell (28960, 28961 ...).')}
        ${baseField('Max játékos', 'sv_maxclients', `<input id="s-slots" type="number" value="${i.maxplayers}">`,
          'Hány játékos fér fel egyszerre a szerverre.')}
        <div class="dvar ${gtOn ? '' : 'off'}">
          <div class="dvar-head"><div class="names"><span class="dvar-label">Játékmód</span>
            <span class="mono dvar-key">g_gametype</span></div>
            ${toggleHtml('data-gt-toggle', 'g_gametype', gtOn)}</div>
          <select id="s-gt">${i.gametypes.map(([v, l]) =>
            `<option value="${v}" ${v === i.gametype ? 'selected' : ''}>${esc(l)} (${v})</option>`).join('')}</select>
          <div class="desc">${esc(i.gametype_desc || '')}</div></div>
        ${baseField('Induló map', '+map', mapButtonHtml(i.game, mapOf(i.maps, i.map), 's-map'),
    'Ezzel a mappal indul a szerver. Kattints a képre a választóhoz. Ha van map rotáció, a panel helyette a rotációt indítja (+map_rotate).')}
        ${baseField('Mod', 'fs_game', `<input id="s-mod" list="modlist" value="${esc(i.mod || '')}" placeholder="(alap)">
          <datalist id="modlist">${i.mods.map(m => `<option>${m}</option>`).join('')}</datalist>`,
      'Mod könyvtár neve (pl. mods/mymod). Üresen hagyva az alap játék fut.')}
        ${baseField('Extra indítási paraméterek', '', `<input id="s-extra" value="${esc(i.extra_params || '')}" placeholder="+set sv_cheats 0">`,
        'Bármilyen további parancssori kapcsoló, szóközzel elválasztva.')}
      </div>
      <div class="inline" style="gap:24px;margin-top:6px">
        <label class="switch"><input type="checkbox" id="s-autostart" ${i.autostart ? 'checked' : ''}><span class="track"></span>
          <span>Induljon a panel indulásakor</span></label>
        <label class="switch"><input type="checkbox" id="s-autorestart" ${i.autorestart ? 'checked' : ''}><span class="track"></span>
          <span>Automatikus újraindítás összeomlás után</span></label>
      </div>
    </div>
    <div class="card" style="margin-bottom:16px"><h3>Játékmód limitek (${esc(i.gametype)})</h3>
      <div class="help" style="margin-bottom:14px">Minden játékmódhoz külön tárolódnak,
        ezért a mód váltásakor más mezők jelennek meg.</div>
      <div class="dvar-grid">${limitFields}</div></div>
    ${i.dvar_groups.map(g => `<div class="card" style="margin-bottom:16px"><h3>${esc(g.title)}</h3>
      <div class="dvar-grid">${g.fields.map(f => field(f, (i.dvars || {})[f.key], off)).join('')}</div></div>`).join('')}
    <div class="card" style="margin-bottom:16px"><h3>Egyéni dvar-ok / cfg sorok</h3>
      <div class="field"><label>Ezek változtatás nélkül a cfg végére kerülnek</label>
        <textarea id="s-extracfg" rows="6" placeholder='set sv_fps "20"&#10;set scr_sd_bombtimer "30"'>${esc(i.extra_cfg || '')}</textarea>
        <span class="help">Ide jöhet minden, aminek nincs saját mezője a fenti listákban.</span></div></div>
    <div class="btn-row" style="position:sticky;bottom:12px">
      <button class="btn primary" id="save">Mentés és cfg írása</button>
      <button class="btn" id="saverestart">Mentés + újraindítás</button>
    </div>`;
  wireToggles();
  wireMapButtons(i.game, i.maps);

  const collect = () => {
    const dvars = {};
    $$('[data-key]').forEach(inp => { dvars[inp.dataset.key] = inp.value; });
    const dvars_off = [];
    $$('[data-toggle]').forEach(t => { if (!t.checked) dvars_off.push(t.dataset.toggle); });
    const newLimits = {};
    $$('[data-limit]').forEach(inp => {
      const key = inp.dataset.limit;
      const tgl = document.querySelector(`[data-limit-toggle="${key}"]`);
      if (tgl && tgl.checked && inp.value !== '') newLimits[key] = inp.value;
    });
    Object.keys(limits).forEach(k => {
      if (!(k in newLimits) && !document.querySelector(`[data-limit="${k}"]`)) newLimits[k] = limits[k];
    });
    return {
      name: $('#s-name').value, ip: $('#s-ip').value, port: +$('#s-port').value,
      maxplayers: +$('#s-slots').value, gametype: $('#s-gt').value,
      gametype_enabled: $('[data-gt-toggle]').checked,
      map: $('#s-map').dataset.value,
      mod: $('#s-mod').value, extra_params: $('#s-extra').value,
      autostart: $('#s-autostart').checked, autorestart: $('#s-autorestart').checked,
      dvars, dvars_off, limits: newLimits, extra_cfg: $('#s-extracfg').value,
    };
  };
  const save = async (restart) => {
    try {
      await PATCH('/api/instances/' + i.id, collect());
      if (restart) await POST(`/api/instances/${i.id}/restart`);
      toast(restart ? 'Mentve, szerver újraindítva.' : 'Mentve, cfg frissítve.', 'ok');
      render();
    } catch (e) { fail(e); }
  };
  $('#save').onclick = () => save(false);
  $('#saverestart').onclick = () => save(true);
}

function tabRotation(el, i) {
  let rot = (i.rotation || []).slice();
  const draw = () => {
    $('#rot').innerHTML = rot.length ? rot.map((r, idx) => `<div class="rot-row">
      <span class="idx">${idx + 1}.</span>
      <img class="thumb" style="width:52px;height:38px;border-radius:6px;object-fit:cover;background:#1b2534"
           alt="" src="${mapImgUrl(i.game, r.map)}" onerror="this.style.visibility='hidden'">
      <select data-r="${idx}" data-k="gametype">${i.gametypes.map(([v, l]) =>
      `<option value="${v}" ${v === r.gametype ? 'selected' : ''}>${esc(l)} (${v})</option>`).join('')}</select>
      <select data-r="${idx}" data-k="map">${i.maps.map(m =>
      `<option value="${m.map}" ${m.map === r.map ? 'selected' : ''}>${esc(m.label || m.map)} — ${m.map}</option>`).join('')}</select>
      <button class="btn sm ghost" data-up="${idx}">↑</button>
      <button class="btn sm ghost" data-down="${idx}">↓</button>
      <button class="btn sm red" data-rm="${idx}">${ICON.trash}</button></div>`).join('')
      : '<div style="color:var(--muted)">Nincs rotáció — a szerver az induló mapon marad.</div>';
    $('#rotpreview').textContent = rot.map(r => `gametype ${r.gametype} map ${r.map}`).join(' ') || '(üres)';
    $$('[data-r]').forEach(s => s.onchange = () => { rot[+s.dataset.r][s.dataset.k] = s.value; draw(); });
    $$('[data-rm]').forEach(b => b.onclick = () => { rot.splice(+b.dataset.rm, 1); draw(); });
    $$('[data-up]').forEach(b => b.onclick = () => { const x = +b.dataset.up; if (x > 0) { [rot[x - 1], rot[x]] = [rot[x], rot[x - 1]]; draw(); } });
    $$('[data-down]').forEach(b => b.onclick = () => { const x = +b.dataset.down; if (x < rot.length - 1) { [rot[x + 1], rot[x]] = [rot[x], rot[x + 1]]; draw(); } });
  };
  el.innerHTML = `<div class="card" style="margin-bottom:16px">
      <div class="card-head"><h3>Map rotáció</h3><div class="spacer"></div>
        <select id="addgt" style="max-width:190px">${i.gametypes.map(([v, l]) => `<option value="${v}" ${v === i.gametype ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select>
        <div style="width:230px">${mapButtonHtml(i.game, mapOf(i.maps, i.map), 'addmap')}</div>
        <button class="btn sm primary" id="add">${ICON.plus} Hozzáadás</button></div>
      <div id="rot"></div>
      <div class="hr"></div>
      <div class="btn-row">
        <button class="btn sm" id="all-stock">Összes alap map hozzáadása</button>
        <button class="btn sm" id="all-custom">Összes custom map hozzáadása</button>
        <button class="btn sm ghost" id="clear">Törlés</button></div>
    </div>
    <div class="card" style="margin-bottom:16px"><h3>sv_mapRotation</h3>
      <div class="mono" id="rotpreview" style="color:var(--muted);word-break:break-all"></div></div>
    <div class="btn-row"><button class="btn primary" id="save">Mentés</button>
      <button class="btn" id="saverestart">Mentés + újraindítás</button></div>`;
  draw();
  wireMapButtons(i.game, i.maps);
  $('#add').onclick = () => { rot.push({ gametype: $('#addgt').value, map: $('#addmap').dataset.value }); draw(); };
  $('#all-stock').onclick = () => { i.maps.filter(m => m.source === 'stock').forEach(m => rot.push({ gametype: $('#addgt').value, map: m.map })); draw(); };
  $('#all-custom').onclick = () => { i.maps.filter(m => m.source === 'custom').forEach(m => rot.push({ gametype: $('#addgt').value, map: m.map })); draw(); };
  $('#clear').onclick = () => { rot = []; draw(); };
  const save = async (restart) => {
    try {
      await PATCH('/api/instances/' + i.id, { rotation: rot });
      if (restart) await POST(`/api/instances/${i.id}/restart`);
      toast('Rotáció mentve.', 'ok'); render();
    } catch (e) { fail(e); }
  };
  $('#save').onclick = () => save(false);
  $('#saverestart').onclick = () => save(true);
}

function tabConsole(el, i) {
  el.innerHTML = `<div class="card pad0" style="padding:16px">
    <div class="card-head"><h3>${ICON.terminal} Élő konzol</h3><div class="spacer"></div>
      <label class="switch"><input type="checkbox" id="autoscroll" checked><span class="track"></span><span>Auto scroll</span></label>
      <button class="btn sm ghost" id="logfile">Log fájl</button></div>
    <div class="console" id="con"></div>
    <div class="console-input">
      <select id="via" style="width:120px"><option value="stdin">konzol</option><option value="rcon">rcon</option></select>
      <input id="cmd" placeholder="pl. status / map mp_toujane / say Hello" style="flex:1">
      <button class="btn primary" id="send">Küldés</button></div>
    <div class="help" style="margin-top:8px">A „konzol” közvetlenül a szerver stdin-jére ír (nem kell rcon jelszó).</div>
  </div>`;
  const con = $('#con');
  const add = line => {
    const div = document.createElement('div');
    let cls = '';
    if (line.includes('[panel')) cls = 'l-panel';
    if (/HIBA|error|Error/.test(line)) cls = 'l-err';
    if (line.includes('[rcon')) cls = 'l-rcon';
    div.className = cls; div.textContent = line;
    con.appendChild(div);
    if ($('#autoscroll').checked) con.scrollTop = con.scrollHeight;
    while (con.childNodes.length > 1200) con.removeChild(con.firstChild);
  };
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  S.ws = new WebSocket(`${proto}://${location.host}/api/instances/${i.id}/console/ws`);
  S.ws.onmessage = ev => add(ev.data);
  S.ws.onerror = () => add('[panel] a konzol kapcsolat megszakadt');
  const send = async () => {
    const cmd = $('#cmd').value.trim();
    if (!cmd) return;
    try { await POST(`/api/instances/${i.id}/command`, { command: cmd, via: $('#via').value }); $('#cmd').value = ''; }
    catch (e) { fail(e); }
  };
  $('#send').onclick = send;
  $('#cmd').onkeydown = e => { if (e.key === 'Enter') send(); };
  $('#logfile').onclick = async () => {
    const txt = await fetch(`/api/instances/${i.id}/logfile`).then(r => r.text());
    modal('Log fájl', `<pre class="mono" style="max-height:60vh;overflow:auto;white-space:pre-wrap">${esc(txt)}</pre>`);
  };
}

function tabCfg(el, i) {
  el.innerHTML = `<div class="grid c2">
    <div class="card"><h3>Generált ${esc(i.id)}.cfg</h3>
      <div class="help" style="margin-bottom:8px">${esc(i.cfg_path)}</div>
      <textarea rows="22" readonly>${esc(i.cfg)}</textarea>
      <div class="btn-row" style="margin-top:12px"><button class="btn" id="write">Kiírás a lemezre</button></div></div>
    <div class="card"><h3>Indítási parancs</h3>
      <textarea rows="8" readonly>${esc(i.command)}</textarea>
      <div class="hr"></div><h3>LinuxGSM megfelelő</h3>
      <div class="help">Ez a panel ugyanazokat a binárisokat és paramétereket használja, mint a
        LinuxGSM <span class="mono">${esc(i.game)}server</span> script.</div></div></div>`;
  $('#write').onclick = async () => {
    try { await POST(`/api/instances/${i.id}/writecfg`); toast('cfg kiírva.', 'ok'); } catch (e) { fail(e); }
  };
}

/* ---------------- games ---------------- */
async function installLibs(btn, gid) {
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="loading"></span> telepítés...'; }
  try {
    const r = await POST('/api/libs/install', gid ? { game: gid } : {});
    const names = (r.installed || []).map(x => x.lib).join(', ');
    toast(names ? 'Telepítve: ' + names : 'Nem volt mit telepíteni.', 'ok');
    render();
  } catch (e) { fail(e); if (btn) { btn.disabled = false; btn.textContent = 'Újra'; } }
}

function libWarning(missing, gid) {
  if (!missing || !missing.length) return '';
  return `<div class="card" style="border-color:rgba(255,93,93,.45);margin-bottom:18px">
    <div class="card-head"><h3 style="color:var(--red)">Hiányzó 32 bites rendszerkönyvtár</h3></div>
    <p style="margin:0 0 12px;color:var(--muted);font-size:13.5px">
      A szerver nem indul el, amíg ez hiányzik: <span class="mono">${esc(missing.join(', '))}</span>.
      A CoD / CoD2 / CoD:UO binárisok a GCC 3-as C++ runtime-ot kérik, ami a mai
      disztribúciókban már nincs benne. A panel a Debian archívumából szerzi be, és a
      saját <span class="mono">data/lib32</span> könyvtárába teszi — a rendszerhez nem nyúl.</p>
    <button class="btn primary" data-libs="${gid || ''}">${ICON.download} Hiányzó könyvtárak telepítése</button>
  </div>`;
}
async function viewGames() {
  const games = await GET('/api/games');
  S.games = games;
  const card = g => {
    const busy = ['downloading', 'verifying', 'extracting'].includes(g.status);
    return `<div class="card">
      <div class="card-head"><h3>${esc(g.name)}</h3><div class="spacer"></div>
        ${g.installed ? '<span class="badge on">telepítve</span>' : '<span class="badge off">nincs telepítve</span>'}</div>
      <div class="kv" style="margin-bottom:12px">
        <span class="k">Bináris</span><span class="mono">${esc(g.executable)}</span>
        <span class="k">Mod könyvtár</span><span class="mono">${esc(g.moddir)}</span>
        <span class="k">Alap port</span><span>${g.default_port}</span>
        <span class="k">Játékmódok</span><span>${g.gametypes.map(x => x[0]).join(', ')}</span>
        <span class="k">Méret</span><span>${g.size_mb} MB</span>
        <span class="k">Útvonal</span><span class="mono" style="font-size:11px">${esc(g.path)}</span>
        ${(g.legacy_libs || []).length ? `<span class="k">Extra lib</span><span>${
          (g.missing_libs || []).length
            ? `<span class="badge err">${esc(g.missing_libs.join(', '))} hiányzik</span>`
            : `<span class="badge on">${esc(g.legacy_libs.join(', '))} rendben</span>`}</span>` : ''}
      </div>
      ${busy ? `<div class="bar" style="margin-bottom:8px"><i style="width:${g.percent}%"></i></div>
        <div class="help">${esc(g.message)}</div>` : ''}
      ${g.status === 'error' ? `<div class="badge err" style="margin-bottom:8px">${esc(g.message)}</div>` : ''}
      <div class="btn-row">
        ${g.install_mode === 'manual' ? ''
      : `<button class="btn ${g.installed ? '' : 'primary'}" data-install="${g.id}" ${busy ? 'disabled' : ''}>
             ${ICON.download} ${g.installed ? 'Újratelepítés' : 'Szerverfájlok telepítése'}</button>`}
        <button class="btn sm ghost" data-maps="${g.id}">Mapok</button>
        ${g.installed ? `<button class="btn sm red" data-rm="${g.id}">${ICON.trash}</button>` : ''}
      </div>
      ${g.install_mode === 'manual'
      ? `<div class="help" style="margin-top:10px">
           Ehhez a játékhoz <b>nincs letölthető szerverfájl</b> — a saját MW2 (Steam) telepítésed
           és az <a href="https://docs.iw4x.io/hosting/server-hosting/" target="_blank" rel="noopener">IW4x</a>
           fájljai kellenek. Másold őket ide:
           <div class="mono" style="margin-top:6px">${esc(g.path)}</div>
           úgy, hogy a <span class="mono">${esc(g.executable)}</span> a könyvtár gyökerébe kerüljön.
           Windows bináris, ezért <span class="mono">wine</span> is kell a konténerben
           (<span class="mono">apt install wine</span>).</div>`
      : `<div class="help" style="margin-top:8px">Forrás: <span class="mono">${esc(g.archive_url)}</span></div>`}
    </div>`;
  };
  const allMissing = [...new Set(games.flatMap(g => g.missing_libs || []))];
  $('#main').innerHTML = `
    <div class="topbar"><div><h1>Játékfájlok</h1>
      <div class="sub">Egy kattintásos telepítés a LinuxGSM tükrökről (MD5 ellenőrzéssel)</div></div></div>
    ${libWarning(allMissing, null)}
    <div class="grid c2">${games.map(card).join('')}</div>`;
  $$('[data-libs]').forEach(b => b.onclick = () => installLibs(b, b.dataset.libs || null));
  $$('[data-install]').forEach(b => b.onclick = async () => {
    try {
      await POST(`/api/games/${b.dataset.install}/install`, { force: true });
      toast('Telepítés elindult, a folyamat itt követhető.', 'ok'); viewGames();
    } catch (e) { fail(e); }
  });
  $$('[data-maps]').forEach(b => b.onclick = () => go('maps/' + b.dataset.maps));
  $$('[data-rm]').forEach(b => b.onclick = async () => {
    if (!confirm('Törlöd a játék szerverfájljait? A mapok is törlődnek.')) return;
    try { await DEL(`/api/games/${b.dataset.rm}/install`); toast('Törölve.', 'ok'); viewGames(); } catch (e) { fail(e); }
  });
  if (games.some(g => ['downloading', 'verifying', 'extracting'].includes(g.status))) {
    startPoll(1500, 'games', () => viewGames().catch(() => {}));
  } else {
    stopPoll();
  }
}

/* ---------------- maps ---------------- */
async function viewMaps() {
  if (!S.games.length) S.games = await GET('/api/games');
  const gid = S.mapsGame || S.games[0].id;
  S.mapsGame = gid;
  const data = await GET(`/api/games/${gid}/maps${S.mapsMod ? '?mod=' + encodeURIComponent(S.mapsMod) : ''}`);
  S.mapsData = data;
  $('#main').innerHTML = `
    <div class="topbar"><div><h1>Map kezelő</h1>
      <div class="sub">Custom map letöltése egy kattintással, utána azonnal kiválasztható</div></div>
      <div class="spacer"></div>
      <select id="gsel">${S.games.map(g => `<option value="${g.id}" ${g.id === gid ? 'selected' : ''}>${esc(g.short)} — ${esc(g.name)}</option>`).join('')}</select>
      <select id="msel">${data.mods.map(m => `<option ${m === data.mod ? 'selected' : ''}>${m}</option>`).join('')}</select>
    </div>
    ${data.installed ? '' : `<div class="card" style="border-color:rgba(255,93,93,.4);margin-bottom:16px">
      A játék szerverfájljai nincsenek telepítve. <a href="#/games">Telepítés →</a></div>`}
    <div class="grid c2" style="margin-bottom:16px">
      <div class="card"><h3>${ICON.download} Letöltés URL-ről</h3>
        <div class="field"><label>Közvetlen link (.iwd, .pk3, .ff vagy .zip)</label>
          <input id="url" placeholder="https://.../mp_custommap.zip"></div>
        <button class="btn primary" id="dl">Letöltés és telepítés</button>
        <div class="help" style="margin-top:8px">A zip csomagokat a panel kibontja: a
          <span class="mono">usermaps/</span>, <span class="mono">main/</span> és <span class="mono">mods/</span>
          könyvtárszerkezetet megtartja, különben a megfelelő helyre teszi a fájlokat.</div></div>
      <div class="card"><h3>Feltöltés gépről</h3>
        <div class="field"><label>Fájl kiválasztása</label><input type="file" id="file"></div>
        <button class="btn" id="up">Feltöltés és telepítés</button>
        <div class="help" style="margin-top:8px">Cél: <span class="mono">${esc(data.mod)}</span>
          ${['cod4', 'codwaw'].includes(gid) ? ' (mp_* fájlok a usermaps/ alá kerülnek)' : ''}</div></div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-head"><h3>Elérhető mapok (${data.maps.length})</h3><div class="spacer"></div>
        <button class="btn sm" id="genimg">Bélyegképek legyártása</button></div>
      <div class="help" style="margin-bottom:12px">A képek a saját játékfájljaidból (loadscreen textúrák) készülnek.
        Ha valamelyiknél nincs kép, a kártya bal felső sarkában lévő gombbal tölthetsz fel sajátot.</div>
      <div class="mapgrid">${data.maps.map(m => `<div class="mapcard" data-map="${esc(m.map)}">
        <button class="imgbtn" data-setimg="${esc(m.map)}">kép</button>
        <div class="mapthumb"><span class="ph">${esc((m.label || m.map).slice(0, 2).toUpperCase())}</span>
          <img loading="lazy" alt="" src="${mapImgUrl(gid, m.map)}" onerror="this.remove()"></div>
        <div class="mapmeta"><b>${esc(m.label || m.map)}</b><span class="mono">${esc(m.map)}</span>
          ${m.source === 'custom' ? '<span class="badge accent">custom map</span>' : ''}</div></div>`).join('')}</div></div>
    <div class="card pad0">
      <div style="padding:18px 18px 0"><h3>Telepített fájlok</h3></div>
      <table><thead><tr><th>Fájl</th><th>Mapok</th><th>Méret</th><th></th></tr></thead><tbody>
      ${data.assets.length ? data.assets.map(a => `<tr>
        <td class="mono">${esc(a.rel)}</td>
        <td>${a.maps.map(m => `<span class="badge">${esc(m)}</span>`).join(' ') || '<span style="color:var(--muted)">-</span>'}</td>
        <td>${a.size_mb} MB</td>
        <td style="text-align:right">${a.stock ? '<span class="badge off">alap</span>'
      : `<button class="btn sm red" data-del="${esc(a.rel)}">${ICON.trash}</button>`}</td></tr>`).join('')
      : '<tr><td colspan="4" style="color:var(--muted)">Nincs fájl.</td></tr>'}
      </tbody></table></div>`;
  $('#gsel').onchange = e => { S.mapsMod = null; go('maps/' + e.target.value); };
  $('#msel').onchange = e => { S.mapsMod = e.target.value; viewMaps(); };
  $('#dl').onclick = async () => {
    const url = $('#url').value.trim();
    if (!url) return;
    const btn = $('#dl'); btn.disabled = true; btn.innerHTML = '<span class="loading"></span> letöltés...';
    try {
      const r = await POST(`/api/games/${gid}/maps/url`, { url, mod: data.mod });
      toast(`Telepítve: ${r.installed.length} fájl${r.maps.length ? ', mapok: ' + r.maps.join(', ') : ''}`, 'ok');
      viewMaps();
    } catch (e) { fail(e); btn.disabled = false; btn.textContent = 'Letöltés és telepítés'; }
  };
  $('#up').onclick = async () => {
    const f = $('#file').files[0];
    if (!f) return toast('Válassz fájlt.', 'err');
    const fd = new FormData(); fd.append('file', f); fd.append('mod', data.mod);
    const btn = $('#up'); btn.disabled = true; btn.innerHTML = '<span class="loading"></span> feltöltés...';
    try {
      const r = await api('POST', `/api/games/${gid}/maps/upload`, fd, true);
      toast(`Telepítve: ${r.installed.length} fájl${r.maps.length ? ', mapok: ' + r.maps.join(', ') : ''}`, 'ok');
      viewMaps();
    } catch (e) { fail(e); btn.disabled = false; btn.textContent = 'Feltöltés és telepítés'; }
  };
  $$('[data-del]').forEach(b => b.onclick = async () => {
    if (!confirm('Törlöd: ' + b.dataset.del + '?')) return;
    try { await DEL(`/api/games/${gid}/maps?rel=${encodeURIComponent(b.dataset.del)}`); viewMaps(); } catch (e) { fail(e); }
  });
  $('#genimg').onclick = async (ev) => {
    const btn = ev.currentTarget;
    btn.disabled = true; btn.innerHTML = '<span class="loading"></span> készítés...';
    try {
      const r = await POST(`/api/games/${gid}/mapimages`);
      toast(`${r.generated.length} kép elkészült${r.missing.length ? `, ${r.missing.length} maphoz nincs kép a játékfájlokban` : ''}`, 'ok');
      viewMaps();
    } catch (e) { fail(e); btn.disabled = false; btn.textContent = 'Bélyegképek legyártása'; }
  };
  $$('[data-setimg]').forEach(b => b.onclick = (ev) => {
    ev.stopPropagation();
    mapImageModal(gid, b.dataset.setimg);
  });
}

function mapImageModal(gid, mapname) {
  modal(`Kép a(z) ${mapname} maphoz`, `
    <div class="mapthumb" style="max-width:320px;border-radius:12px;margin-bottom:16px">
      <span class="ph">nincs kép</span>
      <img alt="" src="${mapImgUrl(gid, mapname)}?t=${Date.now()}" onerror="this.remove()"></div>
    <div class="field"><label>Kép feltöltése (PNG, JPG, GIF, WEBP)</label>
      <input type="file" id="mi-file" accept="image/*"></div>
    <div class="field"><label>vagy kép URL-je</label>
      <input id="mi-url" placeholder="https://.../map.jpg"></div>
    <div class="help">A saját kép felülírja a játékfájlokból kinyert bélyegképet.</div>`,
    `<button class="btn red ghost" id="mi-clear">Saját kép törlése</button>
     <button class="btn ghost" id="mi-cancel">Mégse</button>
     <button class="btn primary" id="mi-save">Mentés</button>`);
  $('#mi-cancel').onclick = closeModal;
  $('#mi-clear').onclick = async () => {
    try { await DEL(`/api/games/${gid}/mapimage/${encodeURIComponent(mapname)}`); closeModal(); toast('Saját kép törölve.', 'ok'); render(); }
    catch (e) { fail(e); }
  };
  $('#mi-save').onclick = async () => {
    const file = $('#mi-file').files[0];
    const url = $('#mi-url').value.trim();
    try {
      if (file) {
        const fd = new FormData(); fd.append('file', file);
        await api('POST', `/api/games/${gid}/mapimage/${encodeURIComponent(mapname)}`, fd, true);
      } else if (url) {
        await POST(`/api/games/${gid}/mapimage/${encodeURIComponent(mapname)}`, { url });
      } else { return toast('Válassz fájlt vagy adj meg URL-t.', 'err'); }
      closeModal(); toast('Kép mentve.', 'ok'); render();
    } catch (e) { fail(e); }
  };
}

function tabMapsEmbed(el, i) {
  el.innerHTML = `<div class="card"><h3>Mapok ehhez a szerverhez</h3>
    <p style="color:var(--muted);font-size:13.5px">Játék: <b>${esc(i.game_name)}</b>, mod könyvtár:
      <span class="mono">${esc(i.mod || i.mods[0])}</span></p>
    <div class="mapgrid" style="margin:14px 0">${i.maps.map(m => mapCardHtml(i.game, m, m.map === i.map)).join('')}</div>
    <div class="btn-row"><button class="btn primary" id="tomaps">${ICON.download} Map letöltése / feltöltése</button></div></div>`;
  $('#tomaps').onclick = () => { S.mapsMod = i.mod || null; go('maps/' + i.game); };
}

/* ---------------- log + settings ---------------- */
async function viewLog() {
  const events = await GET('/api/events?limit=200');
  $('#main').innerHTML = `<div class="topbar"><h1>Napló</h1></div>
    <div class="card pad0"><table><thead><tr><th>Idő</th><th>Típus</th><th>Hivatkozás</th><th>Esemény</th></tr></thead>
      <tbody>${events.map(e => `<tr><td class="mono">${new Date(e.ts * 1000).toLocaleString('hu-HU')}</td>
        <td><span class="badge">${esc(e.kind)}</span></td><td class="mono">${esc(e.ref || '')}</td>
        <td>${esc(e.text)}</td></tr>`).join('') || '<tr><td colspan="4">Nincs esemény.</td></tr>'}</tbody></table></div>`;
}

async function viewSettings() {
  const [sys, tok] = await Promise.all([GET('/api/system'), GET('/api/token')]);
  $('#main').innerHTML = `<div class="topbar"><h1>Beállítások</h1></div>
    <div class="card" style="margin-bottom:16px"><h3>AI vezérlés (MCP)</h3>
      <p style="color:var(--muted);font-size:13.5px;margin-top:0">
        A panel MCP szerveren keresztül vezérelhető AI-ból (map váltás, szerver indítás,
        új szerver, konzol a hibakereséshez). Ehhez kell egy API token.</p>
      <div class="kv" style="margin-bottom:14px">
        <span class="k">Token</span><span>${tok.exists
      ? `<span class="badge on">aktív</span> <span class="mono">…${esc(tok.hint)}</span>`
      : '<span class="badge off">nincs</span>'}</span>
        <span class="k">Létrehozva</span><span>${tok.created ? new Date(tok.created * 1000).toLocaleString('hu-HU') : '-'}</span>
      </div>
      <div id="tokenbox"></div>
      <div class="btn-row">
        <button class="btn primary" id="newtoken">${tok.exists ? 'Új token (a régi érvénytelen lesz)' : 'Token készítése'}</button>
        ${tok.exists ? '<button class="btn red" id="revoke">Visszavonás</button>' : ''}
      </div></div>
    <div class="grid c2">
      <div class="card"><h3>Jelszó módosítása</h3>
        <div class="field"><label>Jelenlegi jelszó</label><input type="password" id="old"></div>
        <div class="field"><label>Új jelszó (min. 8 karakter)</label><input type="password" id="new"></div>
        <button class="btn primary" id="pw">Mentés</button></div>
      <div class="card"><h3>Rendszer</h3><div class="kv">
        <span class="k">Panel verzió</span><span>${esc(sys.version)}</span>
        <span class="k">Adat könyvtár</span><span class="mono">${esc(sys.data_dir)}</span>
        <span class="k">Lemez</span><span>${sys.disk_free_gb} / ${sys.disk_total_gb} GB szabad</span>
        <span class="k">Memória</span><span>${sys.mem_free_mb} / ${sys.mem_total_mb} MB szabad</span>
        <span class="k">Load</span><span>${sys.load.join(' / ')}</span>
        <span class="k">32-bit libek</span><span>${sys.lib32 ? '<span class="badge on">rendben</span>' : '<span class="badge err">hiányzik</span>'}</span>
        <span class="k">Szerverek</span><span>${sys.running} fut / ${sys.instances}</span>
      </div></div></div>`;
  $('#newtoken').onclick = async () => {
    if (!confirm('Új token készítése? A korábbi azonnal érvénytelen lesz.')) return;
    try {
      const r = await POST('/api/token');
      const base = location.origin;
      $('#tokenbox').innerHTML = `<div class="card" style="background:#0e131c;margin-bottom:14px">
        <b style="color:var(--accent-2)">Ez a token csak most látható — másold ki!</b>
        <div class="field" style="margin-top:10px"><input id="tokval" readonly value="${esc(r.token)}"></div>
        <div class="field"><label>Claude Code / Claude Desktop beállítás</label>
          <textarea rows="12" readonly>${esc(JSON.stringify({
        mcpServers: {
          codpanel: {
            command: '/opt/codpanel/venv/bin/python',
            args: ['-m', 'panel.mcp_server'],
            env: { PYTHONPATH: '/opt/codpanel/app', CODPANEL_URL: base, CODPANEL_TOKEN: r.token },
          },
        },
      }, null, 2))}</textarea></div>
        <button class="btn sm" id="copytok">Token másolása</button></div>`;
      $('#copytok').onclick = () => {
        const el = $('#tokval'); el.select();
        navigator.clipboard?.writeText(el.value).then(() => toast('Másolva.', 'ok'),
          () => toast('Jelöld ki és másold kézzel.', 'err'));
      };
      toast('Token elkészült.', 'ok');
    } catch (e) { fail(e); }
  };
  if ($('#revoke')) $('#revoke').onclick = async () => {
    if (!confirm('Visszavonod a tokent? Az MCP kapcsolat megszűnik.')) return;
    try { await DEL('/api/token'); toast('Visszavonva.', 'ok'); viewSettings(); } catch (e) { fail(e); }
  };
  $('#pw').onclick = async () => {
    try {
      await POST('/api/password', { old: $('#old').value, new: $('#new').value });
      toast('Jelszó módosítva.', 'ok'); $('#old').value = $('#new').value = '';
    } catch (e) { fail(e); }
  };
}

boot();
