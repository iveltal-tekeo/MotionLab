/* MotionLab app - plain JavaScript, no build step. Pages: home, references (other people's videos: download,
   analyses + verdicts), videos (your footage: renders, timing, Resolve + library picks), library, jobs, storage,
   settings (programs + downloads). Routes keep their first names (#/refs, #/projects). Every frame shown = number +
   timecode. */
'use strict';

// ============================================================================================ helpers
const TOKEN = document.querySelector('meta[name=ml-token]').content;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const pad = n => String(n).padStart(2, '0');
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
function tc(f, fps) {
  const nom = Math.max(1, Math.round(fps || 25)); f = Math.max(0, Math.round(f));
  const s = Math.floor(f / nom);
  return `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}:${pad(f % nom)}`;
}
const ftc = (f, fps) => `<span class="fr">f${f}</span> <span class="tc">(${tc(f, fps)})</span>`;
const frange = (a, b, fps) => a === b ? ftc(a, fps)
  : `<span class="fr">f${a}–${b}</span> <span class="tc">(${tc(a, fps)} – ${tc(b, fps)})</span>`;
function bytes(n) {
  if (n == null) return '–';
  const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0;
  while (n >= 1000 && i < 4) { n /= 1000; i++; }
  return (n >= 100 || i === 0 ? n.toFixed(0) : n.toFixed(1)) + ' ' + u[i];
}
const fileUrl = rel => '/files/' + String(rel).split('/').map(encodeURIComponent).join('/');
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
// frame references in text (f336, f336-347) become links that move the player
const linkify = s => esc(s).replace(/\bf(\d{1,6})(?:[–-](\d{1,6}))?\b/g,
  (m, a, b) => `<a href="#" class="fr" data-seek="${a}">${m}</a>`);

async function api(path, body) {
  const opt = body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-ML-Token': TOKEN},
                                        body: JSON.stringify(body)};
  const r = await fetch(path, opt);
  let j = null;
  try { j = await r.json(); } catch (e) { /* not JSON */ }
  if (!r.ok) throw new Error((j && j.error) || `${r.status} ${r.statusText}`);
  return j;
}
function toast(msg, kind = '') {
  const t = document.createElement('div'); t.className = 'toast ' + kind; t.textContent = msg;
  $('#toasts').append(t); setTimeout(() => t.remove(), kind === 'err' ? 9000 : 4500);
}
function modal(html, init) {
  const m = $('#modal'); $('.mbody', m).innerHTML = html; m.hidden = false; if (init) init($('.mbody', m));
}
function closeModal() { $('#modal').hidden = true; $('#modal .mbody').innerHTML = ''; }
$('#modal').addEventListener('mousedown', e => { if (e.target.id === 'modal' || e.target.closest('.mclose')) closeModal(); });
let LB = {list: [], i: 0};
function lightbox(list, i) { LB = {list, i}; showLB(); }
function showLB() {
  const lb = $('#lightbox'), it = LB.list[LB.i]; if (!it) return;
  $('img', lb).src = fileUrl(it.src); $('.lbcap', lb).textContent = `${it.cap || it.src}   (${LB.i + 1} / ${LB.list.length}, arrows to browse)`;
  lb.hidden = false;
}
$('#lightbox').addEventListener('click', () => { $('#lightbox').hidden = true; });
const tip = $('#tip');
function showTip(html, x, y) { tip.innerHTML = html; tip.hidden = false; tip.style.left = Math.min(x + 14, innerWidth - 380) + 'px'; tip.style.top = (y + 16) + 'px'; }
function hideTip() { tip.hidden = true; }
async function copy(text) {
  try { await navigator.clipboard.writeText(text); }
  catch (e) { const ta = document.createElement('textarea'); ta.value = text; document.body.append(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
  toast('Copied to the clipboard', 'ok');
}
async function openPath(path, reveal = false) {
  try { await api('/api/open', {path, reveal}); } catch (e) { toast(e.message, 'err'); }
}
// Claude Code in a new console in the lab folder, with an optional first message (the app's hand-off texts)
async function openClaude(prompt = '') {
  try { await api('/api/claude', {prompt}); toast('Claude Code is opening in a new window', 'ok'); }
  catch (e) { toast(e.message, 'err'); }
}
const claudeBtn = (prompt, label = 'Open in Claude Code') =>
  `<button class="btn sm cl" data-claude="${esc(prompt)}"><svg class="i"><use href="#i-claude"/></svg>${label}</button>`;
document.addEventListener('click', e => {
  const c = e.target.closest('[data-claude]');
  if (c) { e.preventDefault(); openClaude(c.dataset.claude); }
});
$('#side-claude').onclick = () => openClaude('');
function md(src) {                                     // small Markdown subset for the lab's reports
  const out = []; let para = [], list = null, table = false, pre = null;
  const inl = s => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  const flush = () => {
    if (para.length) { out.push('<p>' + inl(para.join(' ')) + '</p>'); para = []; }
    if (list) { out.push(`</${list}>`); list = null; }
    if (table) { out.push('</table>'); table = false; }
  };
  for (const ln of String(src).replace(/\r/g, '').split('\n')) {
    let m;
    if (/^```/.test(ln)) { if (pre === null) { flush(); pre = []; } else { out.push('<pre class="log">' + esc(pre.join('\n')) + '</pre>'); pre = null; } continue; }
    if (pre !== null) { pre.push(ln); continue; }
    if (/^\s*$/.test(ln)) { flush(); continue; }
    if ((m = ln.match(/^(#{1,3})\s+(.*)/))) { flush(); out.push(`<h${m[1].length}>${inl(m[2])}</h${m[1].length}>`); continue; }
    if ((m = ln.match(/^\s*[-*]\s+(.*)/)) || (m = ln.match(/^\s*\d+\.\s+(.*)/))) {
      const kind = /^\s*\d+\./.test(ln) ? 'ol' : 'ul';
      if (para.length || table || list !== kind) { flush(); out.push(`<${kind}>`); list = kind; }
      out.push('<li>' + inl(m[1]) + '</li>'); continue;
    }
    if (/^\s*\|/.test(ln)) {
      if (/^\s*\|[\s|:-]+\|\s*$/.test(ln)) continue;
      if (!table) { flush(); out.push('<table>'); table = true; }
      out.push('<tr>' + ln.trim().replace(/^\||\|$/g, '').split('|').map(c => '<td>' + inl(c.trim()) + '</td>').join('') + '</tr>');
      continue;
    }
    if (list && /^\s{2,}\S/.test(ln)) { out[out.length - 1] = out[out.length - 1].replace(/<\/li>$/, ' ' + inl(ln.trim()) + '</li>'); continue; }
    if (list || table) flush();
    para.push(ln.trim());
  }
  flush();
  return out.join('\n');
}

// effect family colours (taxonomy.FAMILIES)
const FAM = {
  'Hard cut': '#e9e9ec', 'Flash / white frame': '#fff1a6', 'Dip to black / white': '#9aa0ff', 'Crossfade': '#7fd1ff',
  'Zoom punch in / out': '#ff9f43', 'Whip pan': '#ff6b9a', 'Spin': '#c56bff', 'Shake': '#ff7a59', 'Speed ramp': '#5ad8a6',
  'Freeze frame': '#4fb3ff', 'Stutter / frame repeat / strobe': '#ffc400', 'RGB split / glitch': '#ff4d6d',
  'Blur in / out': '#a0c4ff', 'Color flash / invert / saturation pop': '#f15bb5', 'Light leak / film burn': '#ffb703',
  'Split screen / mirror': '#2ec4b6', 'Text / graphics': '#e76f51', 'Wipe / mask / shape reveal': '#8ac926',
  'Unknown / other': '#8e8e98'};
const VCOL = {correct: '#3ecf8e', partly: '#ffc400', wrong: '#ff5a5a'};
const chip = fam => `<span class="chip"><i class="sw" style="background:${FAM[fam] || '#888'}"></i>${esc(fam)}</span>`;

// ============================================================================================ app shell
let CLEAN = [];          // cleanup callbacks of the page on screen
let KEYS = null;         // keyboard handler of the page on screen
const onCleanup = fn => CLEAN.push(fn);
document.addEventListener('keydown', e => {
  if (!$('#lightbox').hidden) {
    if (e.key === 'Escape') $('#lightbox').hidden = true;
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { LB.i = clamp(LB.i + (e.key === 'ArrowRight' ? 1 : -1), 0, LB.list.length - 1); showLB(); }
    e.preventDefault(); return;
  }
  if (e.key === 'Escape' && !$('#modal').hidden) { closeModal(); return; }
  if (KEYS && $('#modal').hidden) KEYS(e);
});
document.addEventListener('click', e => {
  const o = e.target.closest('[data-open]');
  if (o) { e.preventDefault(); openPath(o.dataset.open, o.hasAttribute('data-reveal')); }
});

const PAGES = [
  [/^#?\/?$/, pageHome, 'home'], [/^#\/refs$/, pageRefs, 'refs'],
  [/^#\/ref\/([^/?]+)(?:\?e=(\w+))?$/, pageRef, 'refs'], [/^#\/projects$/, pageProjects, 'projects'],
  [/^#\/project\/([^/]+)(?:\/(\w+))?$/, pageProject, 'projects'], [/^#\/library$/, pageLibrary, 'library'],
  [/^#\/jobs(?:\/(\d+))?$/, pageJobs, 'jobs'], [/^#\/storage$/, pageStorage, 'storage'],
  [/^#\/settings$/, pageSettings, 'settings'], [/^#\/knowledge$/, pageKnowledge, 'knowledge']];
async function route() {
  CLEAN.forEach(f => { try { f(); } catch (e) { /* ignore */ } }); CLEAN = []; KEYS = null; hideTip();
  const h = location.hash || '#/';
  for (const [rx, fn, nav] of PAGES) {
    const m = h.match(rx);
    if (!m) continue;
    $$('#side a[data-nav]').forEach(a => a.classList.toggle('on', a.dataset.nav === nav));
    const main = $('#main'); main.scrollTop = 0; main.innerHTML = '<div class="loading">Loading…</div>';
    try { await fn(main, ...m.slice(1).map(x => x && decodeURIComponent(x))); }
    catch (e) { main.innerHTML = `<div class="empty">This page could not load: ${esc(e.message)}</div>`; }
    return;
  }
  location.hash = '#/';
}
window.addEventListener('hashchange', route);

// heartbeat: keeps the server alive while the window is open; shows jobs + Resolve; notices updates / restarts
const PAGE_VERSION = (document.querySelector('meta[name=ml-version]') || {}).content || '';
const API_LEVEL = 2;               // the server functions this page needs (server.API_LEVEL)
let RELOADING = false;
window.addEventListener('unhandledrejection', e => toast('Something went wrong: ' + ((e.reason && e.reason.message) || e.reason), 'err'));
function overlay(text) {
  let o = $('#overlay');
  if (!o) { o = document.createElement('div'); o.id = 'overlay'; document.body.append(o); }
  o.innerHTML = `<div class="obox"><div class="spin"></div><div>${esc(text)}</div></div>`; o.hidden = false;
}
async function waitForServer(text) {
  if (RELOADING) return;
  RELOADING = true; overlay(text);
  for (let i = 0; i < 150; i++) {
    await new Promise(r => setTimeout(r, 1000));
    try {
      const p = await (await fetch('/api/ping', {cache: 'no-store'})).json();
      if (p.app === 'motionlab' && (p.phase || 'ready') === 'ready') { location.reload(); return; }
    } catch (e) { /* not back yet */ }
  }
  overlay('MotionLab did not come back by itself. Close this window and start MotionLab again.');
}
async function restartApp() {
  try { await api('/api/restart', {}); }
  catch (e) {
    toast(/not found|404/i.test(e.message) ? 'This MotionLab is too old to restart itself: close every MotionLab window and start it again (MotionLab.bat or the shortcut)' : e.message, 'err');
    return;
  }
  waitForServer('Restarting MotionLab…');
}
function banner(id, html, onBtn) {
  if ($('#' + id)) return;
  const b = document.createElement('div'); b.id = id; b.className = 'banner'; b.innerHTML = html;
  const btn = $('button', b); if (btn && onBtn) btn.onclick = onBtn;
  document.body.append(b);
}
async function ping() {
  if (RELOADING) return;
  try {
    const p = await api('/api/ping');
    if (p.phase === 'updating' || p.phase === 'restarting') { waitForServer(p.phase === 'updating' ? 'Updating MotionLab from GitHub…' : 'Restarting MotionLab…'); return; }
    if ((p.api || 1) < API_LEVEL) banner('oldsrv', 'MotionLab was updated but its server is still the old one. <button class="btn sm pri">Restart now</button>', restartApp);
    else if (PAGE_VERSION && p.version !== PAGE_VERSION) { location.reload(); return; }
    const up = $('#side a[data-nav=settings] .updot'); if (up) up.hidden = !p.update;
    $('#jobcount').textContent = p.running || '';
    const st = (p.resolve || {}).state || '…';
    const d = $('#resolve-state .dot');
    d.className = 'dot ' + (st === 'running' ? 'running' : st === 'not responding' ? 'bad' : '');
    $('#resolve-state span').textContent = st;
    const gone = $('#gone'); if (gone) gone.remove();
  } catch (e) {
    $('#resolve-state span').textContent = 'app server stopped';
    if (!$('#gone')) {
      const b = document.createElement('div'); b.id = 'gone'; b.className = 'toast err';
      b.style.cssText = 'position:fixed;left:50%;top:14px;transform:translateX(-50%);z-index:90;max-width:640px';
      b.textContent = 'The MotionLab server has stopped (the PC slept or it was closed). Close this window and double-click MotionLab.bat again - your verdicts are saved.';
      document.body.append(b);
    }
  }
}
setInterval(ping, 4000); ping();
window.addEventListener('pagehide', () => navigator.sendBeacon('/api/bye', JSON.stringify({token: TOKEN})));

async function startJob(kind, args, follow = true) {
  try {
    const j = await api('/api/jobs', {kind, args});
    toast('Started: ' + j.title); ping();
    if (follow) location.hash = '#/jobs/' + j.id;
    return j;
  } catch (e) { toast(e.message, 'err'); return null; }
}
function followJob(id, pre, onDone) {
  let since = 0, stop = false;
  const tick = async () => {
    if (stop) return;
    try {
      const j = await api(`/api/jobs/${id}?since=${since}`);
      if (j.log.length) {
        const atEnd = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 30;
        pre.textContent += j.log.join('\n') + '\n'; since += j.log.length;
        if (atEnd) pre.scrollTop = pre.scrollHeight;
      }
      if (j.status === 'running' || j.status === 'cancelling') setTimeout(tick, 700);
      else { ping(); if (onDone) onDone(j); }
    } catch (e) { setTimeout(tick, 2000); }
  };
  tick(); onCleanup(() => { stop = true; });
}

// ============================================================================================ player
class Player {
  /* frame-accurate video: the shown frame comes from requestVideoFrameCallback (presented media time) */
  constructor(el, src, fps, frames, label = '') {
    this.fps = fps; this.N = frames || 1e9; this.frame = 0; this.range = null; this.fns = [];
    el.innerHTML = `<div class="player"><video preload="auto" playsinline src="${fileUrl(src)}"></video>
      <div class="pbar">
        <button class="btn" data-a="start" title="First frame (Home)">⏮</button>
        <button class="btn" data-a="-10" title="10 frames back (Shift+←)">−10</button>
        <button class="btn" data-a="-1" title="1 frame back (←)">−1</button>
        <button class="btn pri" data-a="play" title="Play / pause (Space)">▶</button>
        <button class="btn" data-a="1" title="1 frame on (→)">+1</button>
        <button class="btn" data-a="10" title="10 frames on (Shift+→)">+10</button>
        <span class="hint">&nbsp;speed</span>
        <button class="btn rate" data-r="0.25">¼</button><button class="btn rate" data-r="0.5">½</button><button class="btn rate on" data-r="1">1×</button>
        <label class="chk small" title="Repeat the selected event"><input type="checkbox" data-a="loop"> loop</label>
        ${label ? `<span class="hint">${esc(label)}</span>` : ''}
        <span class="now">f0<span class="tc">00:00:00:00</span></span></div></div>`;
    this.v = $('video', el); this.now = $('.now', el); this.pb = $('[data-a=play]', el); this.loop = $('[data-a=loop]', el);
    $$('[data-a]', el).forEach(b => b.addEventListener('click', () => {
      const a = b.dataset.a;
      if (a === 'play') this.toggle(); else if (a === 'start') this.seek(0); else if (a !== 'loop') this.step(+a);
    }));
    $$('[data-r]', el).forEach(b => b.addEventListener('click', () => {
      this.v.playbackRate = +b.dataset.r; $$('[data-r]', el).forEach(x => x.classList.toggle('on', x === b));
    }));
    this.v.addEventListener('play', () => { this.pb.textContent = '❚❚'; });
    this.v.addEventListener('pause', () => { this.pb.textContent = '▶'; });
    const applyPending = () => {                            // a seek asked for before the video was ready
      if (this.pending == null) return;
      this.v.currentTime = (this.pending + 0.5) / this.fps;
      if (this.v.readyState >= 2) this.pending = null;      // keep it until a frame can really be shown
    };
    this.v.addEventListener('loadedmetadata', applyPending);
    this.v.addEventListener('canplay', applyPending);
    const cb = (now, md) => {
      const f = Math.round(md.mediaTime * this.fps);
      if (f !== this.frame) { this.frame = f; this.show(); this.emit(); }
      if (this.range && this.loop.checked && !this.v.paused && f >= this.range[1]) this.seek(this.range[0]);
      this.vfc = this.v.requestVideoFrameCallback(cb);
    };
    if ('requestVideoFrameCallback' in HTMLVideoElement.prototype) this.vfc = this.v.requestVideoFrameCallback(cb);
    else this.v.addEventListener('timeupdate', () => { this.frame = Math.floor(this.v.currentTime * this.fps + 1e-3); this.show(); this.emit(); });
    onCleanup(() => { this.v.pause(); this.v.removeAttribute('src'); this.v.load(); });
  }
  on(fn) { this.fns.push(fn); }
  emit() { this.fns.forEach(f => f(this.frame)); }
  show() { this.now.innerHTML = `f${this.frame}<span class="tc">${tc(this.frame, this.fps)}</span>`; }
  seek(f) {
    f = clamp(Math.round(f), 0, this.N - 1);
    if (this.v.readyState < 1) this.pending = f;        // not loaded yet: seek on loadedmetadata
    else this.v.currentTime = (f + 0.5) / this.fps;     // middle of frame f: the decoder shows exactly f
    if (f !== this.frame) { this.frame = f; this.show(); this.emit(); }
  }
  step(d) { this.v.pause(); this.seek(this.frame + d); }
  toggle() { if (this.v.paused) this.v.play().catch(() => {}); else this.v.pause(); }
  playRange(a, b) { this.range = [a, b]; this.seek(a); this.v.play().catch(() => {}); }
}

// ============================================================================================ timeline
class Timeline {
  /* events (lanes by overlap), hard cuts, shots, beats, drops; zoom = frames each side of the playhead (0 = all) */
  constructor(wrap, R, opts = {}) {
    this.c = $('canvas', wrap); this.R = R; this.fps = R.video.fps; this.N = R.video.frames; this.zoom = opts.zoom || 0;
    this.opts = opts; this.play = 0; this.sel = null; this.v0 = 0; this.v1 = this.N - 1;
    this.lanes = Timeline.pack(R.events, Math.max(2, this.N / 600));
    this.H = this.c.height;
    this.c.addEventListener('mousemove', e => this.hover(e));
    this.c.addEventListener('mouseleave', hideTip);
    this.c.addEventListener('click', e => this.click(e));
    const ro = new ResizeObserver(() => this.draw()); ro.observe(this.c); onCleanup(() => ro.disconnect());
  }
  static pack(evs, gap) {
    const ends = [], lane = {};
    [...evs].sort((a, b) => a.start - b.start).forEach(e => {
      let i = ends.findIndex(x => x + gap < e.start);
      if (i < 0) { i = ends.length; ends.push(0); }
      ends[i] = e.end; lane[e.id] = i;
    });
    return {lane, n: Math.max(1, ends.length)};
  }
  setPlay(f) {
    this.play = f;
    if (this.zoom) { this.v0 = f - this.zoom; this.v1 = f + this.zoom; }
    this.draw();
  }
  x(f) { return (f - this.v0) / (this.v1 - this.v0 + 1) * this.W; }
  fAt(x) { return Math.floor(this.v0 + x / this.W * (this.v1 - this.v0 + 1)); }
  laneY(i) { const top = 16, h = (this.H - 34) / this.lanes.n; return [top + i * h, Math.max(4, h - 2)]; }
  draw() {
    const c = this.c, dpr = window.devicePixelRatio || 1, W = c.clientWidth, H = this.H;
    if (!W) return;
    this.W = W; c.width = W * dpr; c.height = H * dpr; c.style.height = H + 'px';
    const g = c.getContext('2d'); g.scale(dpr, dpr); g.clearRect(0, 0, W, H);
    const R = this.R, vis = (a, b) => b >= this.v0 && a <= this.v1, ppf = W / (this.v1 - this.v0 + 1);
    R.shots.forEach((s, i) => { if (vis(s.start, s.end)) { g.fillStyle = i % 2 ? '#141418' : '#101013'; g.fillRect(this.x(s.start), 12, this.x(s.end + 1) - this.x(s.start), H - 30); } });
    g.fillStyle = '#3a3a44';
    R.audio.beats.forEach(b => { if (vis(b, b)) g.fillRect(Math.round(this.x(b)), 0, 1, 5); });
    g.fillStyle = '#6a6a78';
    R.audio.downbeats.forEach(b => { if (vis(b, b)) g.fillRect(Math.round(this.x(b)), 0, 1, 9); });
    R.events.forEach(e => {
      if (!vis(e.start, e.end)) return;
      const [y, h] = this.laneY(this.lanes.lane[e.id]);
      const x0 = this.x(e.start), w = Math.max(2, this.x(e.end + 1) - x0);
      g.fillStyle = FAM[e.family] || '#888'; g.globalAlpha = e.false_alarm ? 0.35 : 0.9; g.fillRect(x0, y, w, h); g.globalAlpha = 1;
      const v = (this.opts.verdict || (() => ''))(e.id);
      if (v) { g.fillStyle = VCOL[v]; g.fillRect(x0, y + h - 3, w, 3); }
      if (this.sel === e.id) { g.strokeStyle = '#fff'; g.lineWidth = 2; g.strokeRect(x0 - 1, y - 1, w + 2, h + 2); }
      if (this.zoom && w > 34) { g.fillStyle = '#000'; g.font = '11px Consolas'; g.fillText(e.id, x0 + 3, y + h - 4); }
    });
    g.fillStyle = '#e9e9ec';
    R.cuts.forEach(cu => { if (vis(cu.frame, cu.frame)) g.fillRect(Math.round(this.x(cu.frame)), 12, 1, H - 30); });
    g.fillStyle = '#ffc400';
    R.audio.drops.forEach(d => { if (!vis(d.frame, d.frame)) return; const x = this.x(d.frame); g.beginPath(); g.moveTo(x - 5, 0); g.lineTo(x + 5, 0); g.lineTo(x, 8); g.fill(); });
    // time ruler
    g.fillStyle = '#5c5c66'; g.font = '10.5px Consolas';
    const fpsN = Math.max(1, Math.round(this.fps));
    const steps = [1, 5, fpsN, fpsN * 5, fpsN * 10, fpsN * 30, fpsN * 60];
    const lab = steps.find(s => s * ppf >= 70) || fpsN * 60;
    const tick = steps.find(s => s * ppf >= 6) || lab;
    for (let f = Math.ceil(Math.max(0, this.v0) / tick) * tick; f <= Math.min(this.N - 1, this.v1); f += tick) {
      const x = Math.round(this.x(f)), big = f % lab === 0;
      g.fillRect(x, H - 16, 1, big ? 6 : 3);
      if (big) g.fillText(this.zoom ? `f${f}` : tc(f, this.fps).slice(3, 8), x + 2, H - 3);
    }
    // playhead
    const px = Math.round(this.x(this.play) + (this.zoom ? ppf / 2 : 0));
    g.fillStyle = '#ff5a5a'; g.fillRect(px, 0, 2, H);
    if (this.zoom) {
      const t = `f${this.play}  ${tc(this.play, this.fps)}`; g.font = 'bold 11px Consolas';
      const tw = g.measureText(t).width + 10, lx = Math.min(px + 4, W - tw - 2);
      g.fillStyle = '#ff5a5a'; g.fillRect(lx, H - 15, tw, 14); g.fillStyle = '#000'; g.fillText(t, lx + 5, H - 4);
    }
  }
  hit(e) {
    const r = this.c.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top, f = this.fAt(x);
    const slack = Math.max(1, Math.round(3 / (this.W / (this.v1 - this.v0 + 1))));
    const ev = this.R.events.find(ev => { const [ly, h] = this.laneY(this.lanes.lane[ev.id]); return y >= ly && y <= ly + h && f >= ev.start - slack && f <= ev.end + slack; });
    return {f: clamp(f, 0, this.N - 1), ev};
  }
  hover(e) {
    const {f, ev} = this.hit(e);
    if (ev) showTip(`<b class="amber mono">${ev.id}</b> ${esc(ev.label)}<br>${frange(ev.start, ev.end, this.fps)}`, e.clientX, e.clientY);
    else showTip(`${ftc(f, this.fps)} · click to jump`, e.clientX, e.clientY);
  }
  click(e) {
    const {f, ev} = this.hit(e);
    if (ev && this.opts.onSelect) this.opts.onSelect(ev); else if (this.opts.onSeek) this.opts.onSeek(f);
  }
}

// ============================================================================================ home
async function pageHome(main) {
  const s = await api('/api/status');
  const pct = (a, b) => b ? Math.round(100 * a / b) : 0;
  main.innerHTML = `
  <div class="head"><div><h1>MotionLab</h1><div class="sub">Your local lab in ${esc(s.lab)} · your videos stay on this PC; only what you share goes to GitHub</div></div>
    <div class="row"><button class="btn pri" id="an">＋ Analyse a video</button><button class="btn" data-open=".">Open lab folder</button></div></div>
  ${updateBox(s.update, s.update_result)}
  <div class="grid g5">
    <a class="stat card" href="#/refs"><div class="n">${s.references}</div><div class="l">references analysed · ${s.events} effects found</div></a>
    <a class="stat card" href="#/refs"><div class="n">${s.verdicts}<span class="muted" style="font-size:18px"> / ${s.events}</span></div>
      <div class="l">your verdicts · the lab learns from these</div><div class="bar" style="margin-top:8px"><i style="width:${pct(s.verdicts, s.events)}%"></i></div></a>
    <a class="stat card" href="#/projects"><div class="n">${s.projects}</div><div class="l">your videos (your footage, edited in a reference's style)</div></a>
    <a class="stat card" href="#/library"><div class="n">${s.library}</div><div class="l">library effects · ${s.picks} picked for saving</div></a>
    <a class="stat card" href="#/knowledge"><div class="n" id="kn-n">…</div><div class="l" id="kn-l">references known (yours + friends')</div></a>
  </div>
  <div class="grid g2" style="margin-top:14px">
    <div class="panel"><h2>Next steps</h2>${s.next.length ? `<ul class="next">${s.next.map(n => `<li><a href="${esc(n.go)}">${esc(n.text)}</a>
      ${n.claude ? `<div class="claude" style="margin-top:4px"><span>${esc(n.claude)}</span><span class="row">${claudeBtn(n.claude)}<button class="btn sm" data-copy="${esc(n.claude)}">Copy</button></span></div>` : ''}</li>`).join('')}</ul>`
      : '<div class="muted">Nothing waiting.</div>'}
      ${s.setup.length ? `<h3>Setup</h3><ul class="next">${s.setup.map(t => `<li><b>${esc(t.label)}</b> not found <span class="dim small">(${esc(t.need)})</span><div class="small muted">${esc(t.how)}</div></li>`).join('')}</ul>
        <a href="#/settings">Settings → programs</a>` : ''}</div>
    <div class="panel"><h2>Status</h2><div class="kv">
      <b>Resolve</b><span>${esc(s.resolve.state)}${s.resolve.checked ? ` <span class="dim small">(checked ${esc(s.resolve.checked)})</span>` : ''}</span>
      <b>Disk</b><span>${bytes(s.free_bytes)} free of ${bytes(s.total_bytes)} · <a href="#/storage">storage</a></span>
      <b>Jobs</b><span>${s.jobs_running.length ? s.jobs_running.map(j => `<a href="#/jobs/${j.id}">${esc(j.title)}</a>`).join(', ') : 'none running'}</span>
      <b>Your videos</b><span>${s.projects_list.map(p => `<a href="#/project/${encodeURIComponent(p.name)}">${esc(p.name)}</a>`).join(', ') || '–'}</span></div>
      <h3>Good to know</h3><div class="small muted">Verdicts you give here are saved in the lab right away. Downloads, the automatic
      pass, the reports and the Resolve check-ups run from here; looking at the sheets, learning from your feedback and building
      in Resolve happen in Claude Code - the <b class="amber">Open in Claude Code</b> buttons start it with the right request.</div></div>
  </div>
  ${s.roadmap ? `<div class="panel roadmap" style="margin-top:14px"><div class="row sp"><h2>Roadmap</h2><span class="hint">click to enlarge</span></div>
    <img src="${fileUrl(s.roadmap)}" alt="roadmap"></div>` : ''}`;
  $('#an').onclick = () => analyseModal();
  $$('[data-copy]', main).forEach(b => b.onclick = () => copy(b.dataset.copy));
  wireUpdateBox(main);
  const rm = $('.roadmap img', main); if (rm) rm.onclick = () => lightbox([{src: s.roadmap, cap: 'MotionLab roadmap'}], 0);
  api('/api/knowledge').then(K => {
    const n = $('#kn-n', main), l = $('#kn-l', main); if (!n) return;
    n.textContent = K.cards.length;
    l.textContent = `references known · ${K.cards.filter(c => c.origin === 'shared').length} from friends · ${K.pending.cards + K.pending.lessons} to share`;
    const ul = $('ul.next', main);
    if (ul && (K.pending.cards || K.pending.lessons)) ul.insertAdjacentHTML('beforeend', `<li><a href="#/knowledge">Share what you learned: ${K.pending.cards} reference(s), ${K.pending.lessons} lesson(s) not shared yet</a></li>`);
    if (ul && !K.author) ul.insertAdjacentHTML('beforeend', '<li><a href="#/settings">Set your name for sharing knowledge with friends (Settings)</a></li>');
  }).catch(() => {});
}

// update banner (home + settings): new version on GitHub, or the result of the last update
function updateBox(u, res) {
  u = u || {};
  if (res && res.updated) return `<div class="panel upd ok"><b>Updated to MotionLab ${esc(res.version || '')}</b> <span class="small muted">(${esc(res.from)} → ${esc(res.to)}, ${(res.changed || []).length} files${res.pip ? ', Python packages updated' : ''})</span>
    ${res.set_aside && res.set_aside.length ? `<div class="small">Your own changes to <b>${esc(res.set_aside.join(', '))}</b> clashed with the update: the file now has the new version and your changes are kept in git (<code>git stash list</code>) - ask Claude to bring them back if you still need them.</div>` : ''}</div>`;
  if (u.restart_needed) return `<div class="panel upd"><div class="row sp"><b>MotionLab ${esc(u.disk_version || '')} is installed - restart to use it</b><button class="btn sm pri" data-restart>Restart now</button></div></div>`;
  if (!u.can_update) return '';
  return `<div class="panel upd"><div class="row sp"><div><b>MotionLab ${esc(u.new_version || 'update')} is available</b> <span class="small muted">· ${u.behind} change(s) on GitHub</span>
    ${u.dirty && u.dirty.length ? `<div class="small muted">Your changed files are kept: ${esc(u.dirty.slice(0, 4).join(', '))}${u.dirty.length > 4 ? ' …' : ''}</div>` : ''}</div>
    <div class="row"><button class="btn sm" data-whatsnew>What's new</button><button class="btn sm pri" data-update>Update now</button></div></div>
    <div class="md small" data-wn hidden>${md(u.whats_new || (u.changes || []).map(c => '- ' + c).join('\n'))}</div></div>`;
}
function wireUpdateBox(el) {
  const w = $('[data-whatsnew]', el); if (w) w.onclick = () => { const b = $('[data-wn]', el); b.hidden = !b.hidden; };
  const u = $('[data-update]', el); if (u) u.onclick = updateNow;
  const rs = $('[data-restart]', el); if (rs) rs.onclick = restartApp;
}
async function updateNow() {
  overlay('Updating MotionLab from GitHub…');
  try {
    const r = await api('/api/update/apply', {});
    if (r.updated) { RELOADING = false; waitForServer('Restarting MotionLab with the new version…'); }
    else { $('#overlay').hidden = true; toast('Already up to date', 'ok'); route(); }
  } catch (e) { $('#overlay').hidden = true; toast(e.message, 'err'); }
}

async function analyseModal(prefill = '') {
  const [c, ST] = await Promise.all([api('/api/candidates'), api('/api/settings')]);
  modal(`<h2>Analyse a video</h2>
    <p class="hint">The lab only reads the video (it checks the SHA-256 before and after). Put new videos in <code>refs\\</code> or paste a full path.</p>
    ${c.length ? `<table class="t click" style="margin-bottom:10px"><thead><tr><th>In refs\\</th><th class="num">Size</th><th></th></tr></thead><tbody>
      ${c.map(v => `<tr data-p="${esc(v.path)}"><td>${esc(v.name)}</td><td class="num">${bytes(v.size)}</td><td>${v.analysed ? '<span class="tag done">analysed</span>' : '<span class="tag">new</span>'}</td></tr>`).join('')}</tbody></table>` : ''}
    <input type="text" id="vpath" placeholder="C:\\path\\to\\video.mp4">
    <div class="form" style="margin-top:10px"><label for="vcat">Category</label>
      <select id="vcat">${ST.categories.map(o => `<option value="${o.id}" ${o.id === ST.settings.default_category ? 'selected' : ''}>${esc(o.label)}</option>`).join('')}</select>
      <label for="vtags">Tags (optional)</label><input type="text" id="vtags" placeholder="e.g. instagram, asmr, recipe">
      <span></span><span class="small dim">Pacing, effects and lessons are kept per category, so cooking shorts don't change how music videos are judged.</span></div>
    <div class="row" style="margin-top:10px"><button class="btn pri" id="go">Start the automatic pass</button>
      <label class="chk small"><input type="checkbox" id="redet"> re-use cached measurements (after threshold changes)</label></div>
    <hr><div class="hint">The automatic pass detects cuts and effects (about 1–2 minutes per minute of video). Then Claude looks at every
      contact sheet and names each effect properly - in Claude Code:</div>
    <div class="claude" style="margin-top:6px"><span id="cc">/analyze-reference "&lt;path&gt;"</span><span class="row"><button class="btn sm cl" id="cco"><svg class="i"><use href="#i-claude"/></svg>Open in Claude Code</button><button class="btn sm" id="ccb">Copy</button></span></div>`, el => {
    const inp = $('#vpath', el), upd = () => { $('#cc', el).textContent = `/analyze-reference "${inp.value || '<path>'}"`; };
    $('#cco', el).onclick = () => { if (!inp.value.trim()) { toast('Pick or paste a video first', 'err'); return; } openClaude($('#cc', el).textContent); };
    if (prefill) { inp.value = prefill; upd(); }
    $$('tr[data-p]', el).forEach(r => r.onclick = () => { inp.value = r.dataset.p; upd(); });
    inp.oninput = upd;
    $('#ccb', el).onclick = () => copy($('#cc', el).textContent);
    $('#go', el).onclick = async () => {
      if (!inp.value.trim()) { toast('Pick or paste a video first', 'err'); return; }
      const j = await startJob('analyze', {video: inp.value.trim(), redetect: $('#redet', el).checked, category: $('#vcat', el).value, tags: $('#vtags', el).value});
      if (j) closeModal();
    };
  });
}

// ============================================================================================ videos (analyses)
async function pageRefs(main) {
  let tests = false, cat = '', tag = '';
  const draw = async () => {
    const all = await api('/api/references' + (tests ? '?tests=1' : ''));
    const cats = [...new Map(all.filter(r => r.category).map(r => [r.category, r.category_label])).entries()];
    const tags = [...new Set(all.flatMap(r => r.tags || []))].sort();
    const refs = all.filter(r => (!cat || r.category === cat) && (!tag || (r.tags || []).includes(tag)));
    main.innerHTML = `<div class="head"><div><h1>References</h1><div class="sub">Videos by others that the lab breaks down: download one, analyse it, then check every effect and give your verdict.</div></div>
      <div class="row"><label class="chk small"><input type="checkbox" id="tests" ${tests ? 'checked' : ''}> show self-test videos</label>
      <button class="btn" id="dl"><svg class="i"><use href="#i-download"/></svg>Download from a link</button>
      <button class="btn pri" id="an">＋ Analyse a video</button></div></div>
      ${all.length ? `<div class="row" style="margin-bottom:12px"><select id="fcat"><option value="">All categories (${all.length})</option>${cats.map(([k, l]) => `<option value="${k}" ${k === cat ? 'selected' : ''}>${esc(l)} (${all.filter(r => r.category === k).length})</option>`).join('')}</select>
        ${tags.length ? `<select id="ftag"><option value="">All tags</option>${tags.map(t => `<option ${t === tag ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select>` : ''}</div>` : ''}
      ${refs.length ? `<div class="cards">${refs.map(r => `<a class="card" href="#/ref/${encodeURIComponent(r.name)}">
        ${r.thumb ? `<img class="thumb" src="${fileUrl(r.thumb)}" loading="lazy">` : ''}
        <div class="cb"><div class="ct">${esc(r.title)}</div>
        <div class="small muted">${tc((r.frames || 1) - 1, r.fps)} · ${r.fps} fps · ${r.width}×${r.height}${r.bpm ? ` · ${r.bpm.toFixed(1)} BPM` : ''} · analysed ${esc(r.generated || '')}</div>
        <div class="small">${r.category ? `<span class="tag">${esc(r.category_label)}</span> ` : ''}${(r.tags || []).map(t => `<span class="tag dim">${esc(t)}</span> `).join('')}<span class="muted">${esc((r.format || {}).label || '')}</span></div>
        <div class="small">${r.events} effects · ${r.cuts} hard cuts${r.pacing && r.pacing.cuts_per_min != null ? ` · <b>${r.pacing.cuts_per_min}</b> cuts/min · shots ${r.pacing.avg_shot_s} s` : ''}</div>
        <div class="small muted">Claude's review ${r.reviewed}/${r.events}</div><div class="bar"><i style="width:${r.events ? 100 * r.reviewed / r.events : 0}%;background:#4fb3ff"></i></div>
        <div class="small muted">Your verdicts ${r.verdicts}/${r.events}</div><div class="bar"><i style="width:${r.events ? 100 * r.verdicts / r.events : 0}%"></i></div>
        </div></a>`).join('')}</div>` : '<div class="empty">No references yet. Click “Download from a link” (or drop a video into the refs folder), then “Analyse a video”.</div>'}`;
    $('#an').onclick = () => analyseModal();
    $('#dl').onclick = downloadModal;
    $('#tests').onchange = e => { tests = e.target.checked; draw(); };
    const fc = $('#fcat', main); if (fc) fc.onchange = e => { cat = e.target.value; draw(); };
    const ft = $('#ftag', main); if (ft) ft.onchange = e => { tag = e.target.value; draw(); };
  };
  await draw();
}

async function pageRef(main, name, selId) {
  const R = await api('/api/reference/' + encodeURIComponent(name));
  const fps = R.video.fps, N = R.video.frames, evs = R.events;
  const byId = Object.fromEntries(evs.map(e => [e.id, e]));
  const S = {events: R.verdicts.events || {}, cuts: R.verdicts.cuts || {}, missed: R.verdicts.missed || ''};
  let cur = byId[selId] || evs.find(e => !e.false_alarm) || evs[0];
  const fams = [...new Set(evs.map(e => e.family))].sort();
  const nfa = evs.filter(e => e.false_alarm).length;
  let shown = evs;                                        // the rows on screen (J / K walk through these)
  main.innerHTML = `
  <div class="head"><div><div class="crumb"><a href="#/refs">References</a> / analysis</div><h1>${esc(R.title)}</h1>
    <div class="sub"><span class="tag">${esc(R.category_label)}</span> ${(R.tags || []).map(t => `<span class="tag dim">${esc(t)}</span> `).join('')}<a href="#" id="editmeta" class="small">edit</a>
      ${R.url ? ` · <a href="${esc(R.url)}" target="_blank" rel="noopener">${esc(R.platform || 'source')}</a>` : ''} · ${R.video.width}×${R.video.height} · ${fps} fps · ${N} frames (f0–${N - 1}, 00:00:00:00 – ${R.video.end_tc})${R.audio.bpm ? ` · ${R.audio.bpm.toFixed(1)} BPM` : ''}
      · ${evs.length} effects, ${R.cuts.length} hard cuts · analysed ${esc(R.generated || '')}${R.source_unchanged ? ' · source unchanged ✓' : ''}</div>
    ${R.pacing ? `<div class="small pacing">Pacing: <b>${R.pacing.cuts_per_min ?? '–'}</b> cuts/min · shots avg <b>${R.pacing.avg_shot_s ?? '–'} s</b> (median ${R.pacing.median_shot_s ?? '–'} s) · <b>${R.pacing.hook_cuts_3s}</b> cut(s) in the first 3 s · <b>${R.pacing.effects_per_min ?? '–'}</b> effects/min${R.pacing.cuts_on_beat_pct != null ? ` · ${R.pacing.cuts_on_beat_pct} % of plain cuts on the beat` : ''}</div>` : ''}</div>
    <div class="row">${R.report ? `<button class="btn" data-open="${esc(R.report)}">Open full report</button>` : ''}
      <button class="btn" data-open="${esc('analysis/' + R.name)}">Folder</button></div></div>
  <div class="refwrap">
    <div class="refleft">
      <div id="player"></div>
      <div class="tl" id="tl1"><canvas height="100"></canvas></div>
      <div class="tl" id="tl2"><canvas height="84"></canvas></div>
      <div class="hint" style="margin-top:6px">Top: the whole video · below: 60 frames each side of the playhead (red) · coloured bars = effects
        (colour = type, line under = your verdict) · white line = hard cut · ▼ = music drop · ticks = beats (tall = bar start)</div>
      <div class="hint" style="margin-top:4px"><span class="kbd">←</span> <span class="kbd">→</span> one frame · <span class="kbd">Shift</span> ten ·
        <span class="kbd">Space</span> play / pause · <span class="kbd">J</span> <span class="kbd">K</span> previous / next effect ·
        <span class="kbd">1</span> <span class="kbd">2</span> <span class="kbd">3</span> correct / partly / wrong</div>
      <div class="filters"><input type="search" id="q" placeholder="Search effects, notes…">
        <select id="ff"><option value="">All effect types</option>${fams.map(f => `<option>${esc(f)}</option>`).join('')}</select>
        <select id="fv"><option value="">All verdicts</option><option value="none">No verdict yet</option><option value="correct">Correct</option>
          <option value="partly">Partly</option><option value="wrong">Wrong</option><option value="relab">Renamed by Claude</option></select>
        ${nfa ? `<label class="chk small"><input type="checkbox" id="showfa"> show the ${nfa} false alarms</label>` : ''}</div>
      <div class="evlist"><table class="t click"><thead><tr><th></th><th>ID</th><th>Effect</th><th>Frames</th><th>Timecode</th><th>Your note</th></tr></thead><tbody id="rows"></tbody></table></div>
      ${(R.near_misses || []).length ? `<h3>Possible misses · ${(R.near_misses || []).length}</h3><div class="hint">Sudden changes no effect and no cut explains.
        Most are nothing; if one is an effect, say what it is and add it to your missed effects.</div><div class="misses" id="misses"></div>` : ''}
    </div>
    <div class="detail panel" id="detail"></div>
  </div>
  <div class="fbbar"><div class="prog"><div class="row sp small"><span id="progt"></span><span id="saved" class="muted"></span></div><div class="bar"><i id="progb"></i></div></div>
    <button class="btn" id="missedb">Missed effects / general notes</button>
    ${nfa ? '<button class="btn ghost" id="agreefa" title="optional: tells Claude its “not an effect” calls were right">Agree with all false alarms</button>' : ''}
    <div class="grow"></div><button class="btn pri" id="exp">Send feedback to Claude…</button></div>`;

  const P = R.video.play ? new Player($('#player'), R.video.play, fps, N) : null;
  if (!P) $('#player').innerHTML = '<div class="empty">The source video is not inside the lab folder, so it cannot be played here.</div>';
  const vOf = id => (S.events[id] || {}).v || '';
  const T1 = new Timeline($('#tl1'), R, {verdict: vOf, onSelect: e => select(e, true), onSeek: f => P && P.seek(f)});
  const T2 = new Timeline($('#tl2'), R, {zoom: 60, verdict: vOf, onSelect: e => select(e, true), onSeek: f => P && P.seek(f)});
  if (P) P.on(f => { T1.setPlay(f); T2.setPlay(f); });

  const save = debounce(async () => {
    try { await api(`/api/reference/${encodeURIComponent(name)}/verdicts`, S); $('#saved').textContent = 'saved ✓'; }
    catch (e) { $('#saved').textContent = 'not saved!'; toast('Could not save: ' + e.message, 'err'); }
  }, 450);
  const changed = () => { $('#saved').textContent = 'saving…'; save(); progress(); rows(); T1.draw(); T2.draw(); };
  const progress = () => {
    const real = evs.filter(e => !e.false_alarm), fas = evs.filter(e => e.false_alarm);
    const n = real.filter(e => vOf(e.id)).length, nf = fas.filter(e => vOf(e.id)).length;
    $('#progt').textContent = `${n} / ${real.length} effects with your verdict` + (fas.length ? ` · false alarms ${nf} / ${fas.length} (optional)` : '');
    $('#progb').style.width = (100 * n / Math.max(1, real.length)) + '%';
  };
  const rows = () => {
    const q = $('#q').value.toLowerCase(), ff = $('#ff').value, fv = $('#fv').value, fa = $('#showfa') && $('#showfa').checked;
    const list = evs.filter(e => (fa || !e.false_alarm || e.id === cur.id) && (!ff || e.family === ff)
      && (!fv || (fv === 'none' ? !vOf(e.id) : fv === 'relab' ? e.relabelled : vOf(e.id) === fv))
      && (!q || (e.id + ' ' + e.label + ' ' + e.what + ' ' + ((S.events[e.id] || {}).note || '')).toLowerCase().includes(q)));
    shown = list.length ? list : evs;
    $('#rows').innerHTML = list.map(e => `<tr data-id="${e.id}" class="${e.id === cur.id ? 'sel' : ''} ${e.false_alarm ? 'fa' : ''}">
      <td><span class="vdot ${vOf(e.id)}"></span></td><td class="mono amber">${e.id}</td>
      <td>${chip(e.family).replace(esc(e.family), esc(e.label))}${e.relabelled ? ` <span class="relab">was <s>${esc(e.auto_label)}</s></span>` : ''}${(S.events[e.id] || {}).library ? ' <span class="amber" title="wanted in the library">★</span>' : ''}</td>
      <td class="fr">f${e.start}${e.end !== e.start ? '–' + e.end : ''}</td><td class="tc">${tc(e.start, fps)}</td>
      <td class="small muted">${esc(((S.events[e.id] || {}).note || '').slice(0, 60))}</td></tr>`).join('')
      || '<tr><td colspan="6" class="muted">No effect matches.</td></tr>';
    $$('#rows tr[data-id]').forEach(tr => tr.onclick = () => select(byId[tr.dataset.id], true));
  };
  const detail = () => {
    const e = cur, st = S.events[e.id] || {}, n = e.end - e.start + 1;
    const el = $('#detail');
    el.innerHTML = `<div class="evhead"><span class="id">${e.id}</span><span class="ty">${esc(e.label)}</span>${chip(e.family)}</div>
      ${e.relabelled ? `<div class="relab">auto-detected as <s>${esc(e.auto_label)}</s> · renamed by Claude's review</div>` : ''}
      ${e.false_alarm ? '<div class="bad small">a false alarm (not an edit effect) - a verdict is optional</div>' : ''}
      <div class="kv" style="margin-top:10px"><b>Frames</b><span>${frange(e.start, e.end, fps)}</span>
        <b>Length</b><span>${n} frame${n > 1 ? 's' : ''} (${(n / fps).toFixed(2)} s)</span></div>
      <div class="verdicts">${['correct', 'partly', 'wrong'].map((v, i) => `<button class="btn vb ${st.v === v ? 'on' : ''}" data-v="${v}" title="key ${i + 1}">
        ${['✓ Correct', '~ Partly', '✗ Wrong'][i]}</button>`).join('')}</div>
      <textarea id="note" rows="3" placeholder="What is right or wrong? e.g. “it's a zoom, not a flash; it starts at f340”">${esc(st.note || '')}</textarea>
      <label class="chk small" style="margin-top:6px"><input type="checkbox" id="lib" ${st.library ? 'checked' : ''}> I want this effect in my library</label>
      <div class="row" style="margin-top:10px"><button class="btn" id="playev">▶ Play this effect</button>
        <button class="btn ghost" id="pv">◀ Previous</button><button class="btn ghost" id="nx">Next ▶</button></div>
      <h3>What happens</h3><div class="what">${linkify(e.what)}</div>
      ${e.evidence.length ? `<h3>Measured evidence</h3><ul class="small" style="margin:0;padding-left:18px;color:#c9c9d0">${e.evidence.map(x => `<li>${linkify(x)}</li>`).join('')}</ul>` : ''}
      <details class="fold"><summary>In depth: timing, easing, origin and how to rebuild it</summary><div class="in"><div class="kv">
        ${e.timing ? `<b>Timing</b><span>${esc(e.timing)}</span>` : ''}${e.easing ? `<b>Easing</b><span>${esc(e.easing)}</span>` : ''}
        ${e.origin ? `<b>Made</b><span>${esc(e.origin)}</span>` : ''}${e.confidence ? `<b>Confidence</b><span>${esc(e.confidence)}</span>` : ''}
        ${e.stacked && e.stacked.length ? `<b>Also</b><span>${esc(e.stacked.join(', '))}</span>` : ''}</div>
        ${e.rebuild ? `<h3>How to rebuild it in Resolve</h3><div class="what">${linkify(e.rebuild)}</div>` : ''}</div></details>
      <details class="fold"><summary>Preview loop and frame list (${e.sheets.length} contact sheet${e.sheets.length === 1 ? '' : 's'})</summary><div class="in">
        ${e.preview ? `<video src="${fileUrl(e.preview)}" autoplay loop muted playsinline style="width:100%;border-radius:6px;background:#000;margin-top:6px"></video>` : ''}
        <div class="sheets" style="margin-top:8px">${e.sheets.map((s, i) => `<img src="${fileUrl(s)}" data-i="${i}" loading="lazy" alt="">`).join('')}</div></div></details>`;
    $$('.vb', el).forEach(b => b.onclick = () => setVerdict(b.dataset.v));
    $('#note', el).oninput = ev => { (S.events[e.id] = S.events[e.id] || {}).note = ev.target.value; $('#saved').textContent = 'saving…'; save(); };
    $('#note', el).onblur = () => rows();
    $('#lib', el).onchange = ev => { (S.events[e.id] = S.events[e.id] || {}).library = ev.target.checked; changed(); };
    $('#playev', el).onclick = () => { if (P) { P.loop.checked = true; P.playRange(e.start, e.end); } };
    $('#pv', el).onclick = () => move(-1); $('#nx', el).onclick = () => move(1);
    $$('.sheets img', el).forEach(img => img.onclick = () => lightbox(e.sheets.map((s, i) => ({src: s, cap: `${e.id} ${e.label} · sheet ${i + 1}`})), +img.dataset.i));
    $$('[data-seek]', el).forEach(a => a.onclick = ev => { ev.preventDefault(); if (P) { P.v.pause(); P.seek(+a.dataset.seek); } });
  };
  const setVerdict = v => {
    const st = S.events[cur.id] = S.events[cur.id] || {};
    st.v = st.v === v ? '' : v; changed(); detail();
  };
  const select = (e, seek) => {
    cur = e; T1.sel = T2.sel = e.id;
    history.replaceState(null, '', `#/ref/${encodeURIComponent(name)}?e=${e.id}`);
    detail(); rows(); T1.draw(); T2.draw();
    const tr = $(`#rows tr[data-id="${e.id}"]`), box = $('.evlist');      // scroll the list only, not the page
    if (tr && box) {
      const top = tr.offsetTop - box.querySelector('thead').offsetHeight;
      if (top < box.scrollTop || top + tr.offsetHeight > box.scrollTop + box.clientHeight) box.scrollTop = top - 40;
    }
    if (seek && P) { P.range = [e.start, e.end]; P.v.pause(); P.seek(e.start); }
  };
  const move = d => {
    const i = shown.indexOf(cur);
    select(shown[i < 0 ? 0 : clamp(i + d, 0, shown.length - 1)], true);
  };
  ['#q', '#ff', '#fv', '#showfa'].forEach(s => { if ($(s)) $(s).addEventListener('input', rows); });
  if ($('#agreefa')) $('#agreefa').onclick = () => {
    evs.filter(e => e.false_alarm).forEach(e => { const st = S.events[e.id] = S.events[e.id] || {}; if (!st.v) st.v = 'correct'; });
    changed(); detail(); toast('All false alarms marked as correctly dismissed', 'ok');
  };
  const missBox = $('#misses');
  if (missBox) {
    missBox.innerHTML = (R.near_misses || []).map((m, i) => `<div class="miss" data-i="${i}">
      <div class="row sp"><a href="#" class="fr" data-seek="${m.frame}">f${m.frame}</a><span class="tc">${esc(m.tc)}</span></div>
      <div class="small muted">${esc(m.why)}</div>
      ${m.checked ? `<div class="small" style="margin-top:4px"><b>Claude checked:</b> ${esc(m.checked)}</div>` : ''}
      <div class="f3">${m.frames.map((f, k) => `<img src="${fileUrl(f)}" data-f="${m.frame - 1 + k}" title="f${m.frame - 1 + k} - click to jump">`).join('')}</div>
      <div class="row"><input type="text" placeholder="what is it? (optional)" style="flex:1"><button class="btn sm">Add to missed effects</button></div></div>`).join('');
    $$('.miss', missBox).forEach(box => {
      const m = R.near_misses[+box.dataset.i];
      $$('img', box).forEach(img => img.onclick = () => { if (P) { P.v.pause(); P.seek(+img.dataset.f); } });
      $('[data-seek]', box).onclick = ev => { ev.preventDefault(); if (P) { P.v.pause(); P.seek(m.frame); } };
      $('button', box).onclick = () => {
        const what = $('input', box).value.trim();
        S.missed = ((S.missed || '').trim() + `\nmissed: f${m.frame} (${m.tc})` + (what ? ' - ' + what : '')).trim();
        changed(); box.classList.add('added'); $('button', box).textContent = 'Added ✓';
      };
    });
  }
  $('#missedb').onclick = () => modal(`<h2>Missed effects / general notes</h2>
    <p class="hint">Anything the analysis missed or got wrong overall. Mention frames or timecodes, e.g. “speed ramp around f1210 / 00:00:48:10”.</p>
    <textarea id="mt" rows="10">${esc(S.missed)}</textarea><div class="row" style="margin-top:10px"><button class="btn pri" id="mok">Save</button></div>`, el => {
    $('#mok', el).onclick = () => { S.missed = $('#mt', el).value; changed(); closeModal(); };
  });
  $('#exp').onclick = async () => {
    try {
      const r = await api(`/api/reference/${encodeURIComponent(name)}/export`, {});
      const say = `Apply the MOTIONLAB FEEDBACK in ${r.path}`;
      modal(`<h2>Feedback for Claude</h2>
        <p class="hint">Saved to <span class="mono">${esc(r.path)}</span>. In Claude Code, paste the text below (it starts with MOTIONLAB FEEDBACK),
        or just say: <span class="mono">${esc(say)}</span>. Claude then turns it into lessons and threshold changes, re-checks the events
        you marked wrong or partly, runs the self-test and tells you what changed.</p>
        <textarea rows="14" readonly class="mono">${esc(r.text)}</textarea>
        <div class="row" style="margin-top:10px">${claudeBtn(say, 'Open in Claude Code (applies it)')}<button class="btn" id="c1">Copy the feedback text</button><button class="btn" id="c2">Copy the short sentence</button></div>`, el => {
        $('#c1', el).onclick = () => copy(r.text); $('#c2', el).onclick = () => copy(say);
      });
    } catch (e) { toast(e.message, 'err'); }
  };
  $('#editmeta', main).onclick = e => { e.preventDefault(); metaModal(R); };
  KEYS = e => {
    if (e.target.matches('input, textarea, select')) return;
    const k = e.key;
    if (P && (k === 'ArrowLeft' || k === 'ArrowRight')) { P.step((k === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? 10 : 1)); e.preventDefault(); }
    else if (P && k === ' ') { P.toggle(); e.preventDefault(); }
    else if (P && k === 'Home') { P.seek(0); e.preventDefault(); }
    else if (k === 'j' || k === 'J') move(-1);
    else if (k === 'k' || k === 'K') move(1);
    else if (k === '1' || k === '2' || k === '3') setVerdict(['correct', 'partly', 'wrong'][+k - 1]);
  };
  progress(); select(cur, false);
  if (P && selId) P.seek(cur.start);
}

// ============================================================================================ projects
async function pageProjects(main) {
  const ps = await api('/api/projects');
  main.innerHTML = `<div class="head"><div><h1>Videos</h1><div class="sub">Your own footage, edited in the style of a reference - rendered by the lab (option 1) and rebuilt in DaVinci Resolve (option 2).</div></div></div>
    ${ps.length ? `<div class="cards">${ps.map(p => `<a class="card" href="#/project/${encodeURIComponent(p.name)}">
      ${p.thumb ? `<img class="thumb" src="${fileUrl(p.thumb)}" loading="lazy">` : ''}
      <div class="cb"><div class="ct">${esc(p.name)}</div>
      <div class="small muted">${p.clips} clips · ${bytes(p.footage_bytes)} of footage</div>
      <div class="small">${p.plans.length} edit version${p.plans.length === 1 ? '' : 's'} · ${p.renders.length} render${p.renders.length === 1 ? '' : 's'}${p.resolve.length ? ' · in Resolve: ' + esc(p.resolve.join(', ')) : ''}</div></div></a>`).join('')}</div>`
      : '<div class="empty">No videos yet. They are made with Claude: put your clips in projects\\&lt;name&gt;\\, then ask Claude Code for an edit in a reference\'s style.</div>'}`;
}

async function pageProject(main, name, tab = 'overview') {
  const P = await api('/api/project/' + encodeURIComponent(name));
  const tabs = [['overview', 'Overview'], ['renders', 'Renders'], ['timing', 'Timing check'], ['resolve', 'Resolve & library']];
  main.innerHTML = `<div class="head"><div><div class="crumb"><a href="#/projects">Videos</a> /</div><h1>${esc(P.name)}</h1>
    <div class="sub">${P.sources.length} clips · ${P.plans.length} edit version(s) · ${P.renders.length} render(s)</div></div>
    <div class="row"><button class="btn" data-open="${esc('projects/' + P.name)}">Folder</button></div></div>
    <div class="tabs">${tabs.map(([k, l]) => `<a href="#/project/${encodeURIComponent(name)}/${k}" class="${k === tab ? 'on' : ''}">${l}</a>`).join('')}</div>
    <div id="tab"></div>`;
  const el = $('#tab');
  if (tab === 'renders') return projRenders(el, P);
  if (tab === 'timing') return projTiming(el, P);
  if (tab === 'resolve') return projResolve(el, P);
  return projOverview(el, P);
}

function projOverview(el, P) {
  el.innerHTML = `<div class="grid g2"><div class="panel"><h2>Your footage (read-only)</h2>
    <table class="t"><thead><tr><th>ID</th><th>File</th><th>Format</th><th class="num">Length</th><th class="num">Size</th></tr></thead><tbody>
    ${P.sources.map(s => `<tr><td class="mono amber">${s.id}</td><td>${esc(s.name)}${s.exists ? '' : ' <span class="bad">missing</span>'}</td>
      <td class="small muted">${esc(s.resolution || '')} · ${s.fps || '?'} fps</td>
      <td class="num">${s.duration_s ? s.duration_s.toFixed(1) + ' s' : '–'}</td><td class="num">${bytes(s.size)}</td></tr>`).join('')}</tbody></table></div>
    <div class="panel"><h2>Edit versions</h2><table class="t"><thead><tr><th>Version</th><th>Length</th><th class="num">Layers</th><th>Levels</th></tr></thead><tbody>
    ${P.plans.map(p => `<tr><td class="mono amber">${esc(p.version)}</td><td>${p.frames} frames · f0–${p.frames - 1} <span class="tc">(00:00:00:00 – ${esc(p.duration_tc)})</span> · ${p.fps} fps</td>
      <td class="num">${p.layers}</td><td class="small muted">${esc(p.levels)}</td></tr>`).join('')}</tbody></table>
    <div class="small muted" style="margin-top:8px">Edit scripts: ${P.edit_scripts.map(s => `<a href="#" data-open="${esc(s)}" data-reveal>${esc(s.split('/').pop())}</a>`).join(', ') || '–'}</div></div></div>
    <h3>Storyboards (one frame per second of every clip)</h3>
    <div class="sheets" style="grid-template-columns:repeat(3,1fr)">${P.boards.map((b, i) => `<img src="${fileUrl(b)}" data-i="${i}" loading="lazy">`).join('')}</div>`;
  $$('.sheets img', el).forEach(img => img.onclick = () => lightbox(P.boards.map(b => ({src: b})), +img.dataset.i));
}

function projRenders(el, P) {
  const vids = [...P.renders, ...P.compares];
  const fpsOf = () => (P.plans[0] || {}).fps || 25, frames = (P.plans[0] || {}).frames;
  el.innerHTML = `<div class="grid g2">${P.renders.map((r, i) => `<div class="panel"><div class="row sp"><h2>${r.kind === 'resolve' ? 'From DaVinci Resolve' : 'Lab render'}</h2>
      <span class="small muted">${esc(r.name)} · ${bytes(r.size)} · ${esc(r.modified)}</span></div><div id="pl${i}"></div>
      <div class="row" style="margin-top:8px"><button class="btn sm" data-open="${esc(r.rel)}">Open in player</button><button class="btn sm" data-open="${esc(r.rel)}" data-reveal>Show in folder</button></div></div>`).join('')}</div>
    <h3>Side by side (made by render_video.py --compare)</h3>
    <div class="grid g2">${P.compares.map((r, i) => `<div class="panel"><div class="small muted" style="margin-bottom:6px">${esc(r.name)} · ${bytes(r.size)}</div><div id="cp${i}"></div></div>`).join('')
      || '<div class="muted">none</div>'}</div>`;
  P.renders.forEach((r, i) => new Player($('#pl' + i, el), r.rel, fpsOf(), frames));
  P.compares.forEach((r, i) => new Player($('#cp' + i, el), r.rel, fpsOf(), frames));
  if (!vids.length) el.innerHTML = '<div class="empty">No renders yet.</div>';
}

function projTiming(el, P) {
  if (!P.verifies.length) { el.innerHTML = '<div class="empty">No timing check yet.</div>'; return; }
  const fps = (P.plans[0] || {}).fps || 25, keys = P.verifies[0].rows;
  el.innerHTML = `<div class="panel"><h2>Does the render change picture on the reference's key frames?</h2>
    <div class="row" style="margin-bottom:10px">${P.verifies.map(v => `<div class="stat"><div class="n">${v.hits}<span class="muted" style="font-size:16px"> / ${v.keys}</span></div>
      <div class="l">${esc(v.name)} · brightness correlation ${v.luma_corr}</div>
      <button class="btn sm" style="margin-top:6px" data-run="${esc(v.name)}">Run again</button></div>`).join('')}</div>
    <table class="t"><thead><tr><th>Frame</th><th>Timecode</th><th>What happens in the reference</th>${P.verifies.map(v => `<th>${esc(v.name)}</th>`).join('')}</tr></thead><tbody>
    ${keys.map((k, i) => `<tr><td class="fr">f${k.frame}</td><td class="tc">${tc(k.frame, fps)}</td><td>${esc(k.what)}</td>
      ${P.verifies.map(v => { const r = v.rows[i] || {}; return `<td>${r.our_hit ? '<span class="ok">✓ same frame</span>' : '<span class="bad">✗ missed</span>'} <span class="small dim">${r.our_change ?? ''}</span></td>`; }).join('')}</tr>`).join('')}
    </tbody></table></div>`;
  $$('[data-run]', el).forEach(b => b.onclick = () => startJob('verify_timing', {project: P.name, render: b.dataset.run}));
}

function projResolve(el, P) {
  if (!P.resolve.length) { el.innerHTML = '<div class="empty">This video has no DaVinci Resolve rebuild yet (option 2, made with Claude).</div>'; return; }
  const fps = (P.plans[0] || {}).fps || 25;
  const render = P.renders.find(r => r.kind === 'resolve') || P.renders[0];
  const picks = Object.assign({}, P.library_picks || {});
  const savePicks = debounce(async () => {
    try { await api(`/api/project/${encodeURIComponent(P.name)}/picks`, {picks}); $('#psaved').textContent = 'saved ✓'; }
    catch (e) { toast(e.message, 'err'); }
  }, 400);
  el.innerHTML = P.resolve.map((R, ri) => {
    const d = R.drift, f = d ? d.findings : [];
    const byUnit = {};
    f.forEach(x => (byUnit[x.unit] = byUnit[x.unit] || []).push(x));
    return `<div class="grid g2"><div class="panel"><h2>Timeline <span class="amber">${esc(R.timeline)}</span></h2>
      <div class="kv"><b>Project</b><span>${esc(R.project)} (Resolve)</span><b>Built from</b><span>${R.units} pieces: ${R.clips} Edit-page clips, ${R.comps} Fusion comps,
        ${R.luts} grade LUTs, ${R.tracks} video tracks</span>
        <b>Backup</b><span>${R.drp ? `<a href="#" data-open="${esc(R.drp)}" data-reveal>${esc(R.drp.split('/').pop())}</a>` : '–'}</span>
        <b>Report</b><span>${R.report ? `<a href="#" class="showrep" data-rep="${esc(R.report)}">option 2 report</a>` : '–'}</span></div>
      <div class="row" style="margin-top:12px"><button class="btn" data-job="resolve_doctor">Check-up</button>
        <button class="btn" data-job="resolve_diff">What did I change by hand?</button><span class="hint">needs Resolve running</span></div>
      <pre class="log" id="rlog${ri}" hidden></pre></div>
      <div class="panel"><h2>Changed by hand in Resolve</h2>${d ? `<div class="small muted" style="margin-bottom:8px">last checked ${esc(d.checked)}</div>
        ${f.length ? Object.entries(byUnit).map(([u, xs]) => `<div style="margin-bottom:10px"><b class="amber">${esc(u)}</b>
          <span class="small muted">V${xs[0].track} · ${frange(xs[0].start, xs[0].end, fps)}</span>
          <ul class="small" style="margin:4px 0">${xs.map(x => `<li>${esc(x.what)}: <span class="muted">lab</span> ${esc(x.lab)} <span class="muted">→ now</span> <b>${esc(x.live)}</b></li>`).join('')}</ul></div>`).join('')
          : '<div class="ok">Nothing: the timeline is exactly what the lab built.</div>'}
        ${R.edits.length ? `<div class="small muted">Your edited comps are kept as text: ${R.edits.map(p => `<a href="#" data-open="${esc(p)}" data-reveal>${esc(p.split('/').pop())}</a>`).join(', ')}</div>` : ''}`
        : '<div class="muted">Not checked yet: click “What did I change by hand?”.</div>'}</div></div>
      <div class="row sp" style="margin:18px 0 8px"><div><h2 style="margin:0">Effects in this rebuild</h2>
        <div class="hint">Tick the effects you want saved in your library (a Fusion macro + a recipe each). Claude does the saving in Resolve; this is your list.</div></div>
        <span id="psaved" class="small muted">${P.picks_updated ? 'saved ' + esc(P.picks_updated) : ''}</span></div>
      <div class="col">${R.effects.map(g => {
        const u0 = g.units[0], mid = Math.round((u0.start + u0.end) / 2), pk = picks[g.title] || {};
        return `<div class="fx ${pk.pick ? 'picked' : ''}" data-fx="${esc(g.title)}">
          ${render ? `<img loading="lazy" src="/api/thumb?video=${encodeURIComponent(render.rel)}&f=${mid}&fps=${fps}" title="f${mid} (${tc(mid, fps)}) in ${esc(render.name)}">` : '<div></div>'}
          <div><div class="row sp"><b style="font-size:15px">${esc(g.title)}</b><label class="chk"><input type="checkbox" data-pick ${pk.pick ? 'checked' : ''}> save to library</label></div>
          <div class="small" style="margin:3px 0 6px">${esc(g.what)}</div>
          <div class="units">${g.units.map(u => `${esc(u.name)} ${u.track ? `V${u.track}` : ''} ${frange(u.start, u.end, fps)}`).join(' · ')}</div>
          <textarea data-note rows="2" placeholder="Anything to change before saving? e.g. “sparks need bright heads”" style="margin-top:8px">${esc(pk.note || '')}</textarea></div></div>`;
      }).join('')}</div>`;
  }).join('<hr>') + '<div id="repbox" class="panel md" style="margin-top:18px" hidden></div>';
  $$('[data-job]', el).forEach(b => b.onclick = async () => {
    const pre = b.closest('.panel').querySelector('pre.log');
    const j = await startJob(b.dataset.job, {project: P.name}, false);
    if (!j) return;
    pre.hidden = false; pre.textContent = '';
    $$('[data-job]', el).forEach(x => { x.disabled = true; });
    followJob(j.id, pre, jj => {
      $$('[data-job]', el).forEach(x => { x.disabled = false; });
      toast(`${jj.title}: ${jj.status}`, jj.status === 'done' ? 'ok' : 'err');
      if (b.dataset.job === 'resolve_diff') api('/api/project/' + encodeURIComponent(P.name)).then(NP => { Object.assign(P, NP); });
    });
  });
  $$('.fx', el).forEach(box => {
    const k = box.dataset.fx;
    $('[data-pick]', box).onchange = e => { (picks[k] = picks[k] || {}).pick = e.target.checked; box.classList.toggle('picked', e.target.checked); $('#psaved').textContent = 'saving…'; savePicks(); };
    $('[data-note]', box).oninput = e => { (picks[k] = picks[k] || {}).note = e.target.value; $('#psaved').textContent = 'saving…'; savePicks(); };
  });
  $$('.fx img', el).forEach(img => { img.onclick = () => { const lb = $('#lightbox'); $('img', lb).src = img.src; $('.lbcap', lb).textContent = img.title; lb.hidden = false; }; });
  $$('.showrep', el).forEach(a => a.onclick = async e => {
    e.preventDefault();
    const box = $('#repbox'); const t = await api('/api/text?path=' + encodeURIComponent(a.dataset.rep));
    box.innerHTML = md(t.text); box.hidden = false; box.scrollIntoView({behavior: 'smooth'});
  });
}

// ============================================================================================ library
async function pageLibrary(main) {
  const L = await api('/api/library');
  const say = 'Save the library picks as Fusion macros + recipes in library\\';
  main.innerHTML = `<div class="head"><div><h1>Library</h1><div class="sub">Effects you approved, saved for reuse: a Fusion macro (.setting) and a recipe (.md) each.</div></div></div>
    <div class="grid g2"><div class="panel"><h2>Saved effects</h2>${L.items.length ? `<table class="t"><thead><tr><th>Effect</th><th>Recipe</th><th>Macros</th><th>Check in Resolve</th><th>Saved</th></tr></thead><tbody>
      ${L.items.map(i => `<tr><td><b>${esc(i.title)}</b></td><td><a href="#" data-open="${esc(i.recipe)}">${esc(i.name)}.md</a></td>
        <td>${i.macros.map(m => `<a href="#" data-open="${esc(m)}" data-reveal>${esc(m.split('/').pop())}</a>`).join(', ') || '<span class="muted small">recipe only</span>'}</td>
        <td>${i.check ? `<a href="#" data-open="${esc(i.check)}" title="the macro rendered in DaVinci Resolve next to the real frame"><img src="${fileUrl(i.check)}" alt="check" style="height:48px;border-radius:4px"></a>` : '–'}</td>
        <td class="small muted">${esc(i.modified)}</td></tr>`).join('')}</tbody></table>
      <div class="row" style="margin-top:8px"><button class="btn sm" data-open="library/README.md">Library index</button><button class="btn sm" data-open="library" data-reveal>Folder</button></div>`
      : '<div class="empty">Nothing saved yet.</div>'}</div>
    <div class="panel"><h2>Picked for saving</h2>${L.picks.length ? `<ul>${L.picks.map(p => `<li><b>${esc(p.effect)}</b> <span class="muted small">from <a href="#/project/${encodeURIComponent(p.project)}/resolve">${esc(p.project)}</a></span>${p.note ? `<div class="small muted">${esc(p.note)}</div>` : ''}</li>`).join('')}</ul>
      <div class="hint" style="margin-top:10px">Claude saves them (it needs Resolve open). In Claude Code say:</div>
      <div class="claude" style="margin-top:6px"><span>${esc(say)}</span><span class="row">${claudeBtn(say)}<button class="btn sm" id="cs">Copy</button></span></div>`
      : `<div class="empty">Nothing picked yet. Open one of your videos (Videos page) → “Resolve &amp; library” and tick the effects you want.</div>`}</div></div>`;
  const cs = $('#cs'); if (cs) cs.onclick = () => copy(say);
}

// ============================================================================================ jobs
async function pageJobs(main, id) {
  const list = await api('/api/jobs');
  main.innerHTML = `<div class="head"><div><h1>Jobs</h1><div class="sub">Tasks the app runs for you with the lab's own tools. They keep running if you switch pages.</div></div>
    <div class="row"><button class="btn" data-k="selftest">Run the self-test</button><button class="btn" data-k="storage">Storage report</button></div></div>
    <div class="grid" style="grid-template-columns:minmax(0,1fr) minmax(0,1.6fr)">
      <div class="panel"><table class="t click"><thead><tr><th>#</th><th>Job</th><th>Status</th><th class="num">Time</th></tr></thead><tbody>
      ${list.map(j => `<tr data-id="${j.id}" class="${+id === j.id ? 'sel' : ''}"><td class="mono">${j.id}</td><td>${esc(j.title)}<div class="small dim">${esc(j.started)}</div></td>
        <td><span class="tag ${j.status}">${j.status}</span></td><td class="num">${j.seconds}s</td></tr>`).join('') || '<tr><td colspan="4" class="muted">No jobs yet in this session.</td></tr>'}
      </tbody></table></div>
      <div class="panel" id="jd">${id ? '' : '<div class="muted">Select a job to see its output.</div>'}</div></div>`;
  $$('[data-k]', main).forEach(b => b.onclick = () => startJob(b.dataset.k, {}));
  $$('tr[data-id]', main).forEach(tr => tr.onclick = () => { location.hash = '#/jobs/' + tr.dataset.id; });
  if (!id) return;
  const j = list.find(x => x.id === +id);
  if (!j) { $('#jd').innerHTML = '<div class="muted">This job is not in this session.</div>'; return; }
  $('#jd').innerHTML = `<div class="row sp"><h2>${esc(j.title)}</h2><span class="tag ${j.status}" id="jst">${j.status}</span></div>
    <div class="small muted mono" style="margin-bottom:8px">${esc(j.command)}</div><pre class="log" id="jlog"></pre>
    <div class="row" style="margin-top:8px"><button class="btn danger" id="jc" ${j.status === 'running' ? '' : 'hidden'}>Stop this job</button></div>`;
  $('#jc').onclick = async () => { if (!confirm('Stop this job?')) return; try { await api(`/api/jobs/${id}/cancel`, {}); } catch (e) { toast(e.message, 'err'); } };
  followJob(+id, $('#jlog'), jj => {
    $('#jst').className = 'tag ' + jj.status; $('#jst').textContent = jj.status; $('#jc').hidden = true;
    toast(`${jj.title}: ${jj.status}`, jj.status === 'done' ? 'ok' : 'err');
  });
}

// ============================================================================================ storage
async function pageStorage(main) {
  main.innerHTML = '<div class="loading">Measuring every folder of the lab… (a few seconds)</div>';
  const S = await api('/api/storage');
  const COL = {source: '#4fb3ff', keep: '#3ecf8e', cache: '#ffc400', checks: '#ff9f43', finals: '#c56bff', env: '#5c5c66'};
  const used = S.units.reduce((a, u) => a + u.total, 0);
  const target = u => u === 'tools\\selftest' ? 'selftest' : u.split('\\').pop();
  main.innerHTML = `<div class="head"><div><h1>Storage</h1><div class="sub">The lab uses ${bytes(used)} · ${bytes(S.free_bytes)} free of ${bytes(S.total_bytes)} on this drive.
    Only data the lab can rebuild can be freed; your videos and everything learned are never touched.</div></div></div>
    <div class="row small" style="margin-bottom:10px">${S.cats.map(c => `<span class="chip"><i class="sw" style="background:${COL[c]}"></i>${c}</span>`).join('')}
      <span class="hint">source = your videos · keep = results and knowledge · cache = rebuildable · checks = comparison videos · finals = full renders</span></div>
    <div class="panel"><table class="t"><thead><tr><th>Folder</th><th></th>${S.cats.map(c => `<th class="num">${c}</th>`).join('')}<th class="num">total</th><th></th></tr></thead><tbody>
    ${S.units.map(u => { const fr = S.prunable.reduce((a, c) => a + u[c], 0); return `<tr><td class="mono small">${esc(u.name)}</td>
      <td><div class="stbar">${S.cats.map(c => `<i style="width:${100 * u[c] / Math.max(1, u.total)}%;background:${COL[c]}"></i>`).join('')}</div></td>
      ${S.cats.map(c => `<td class="num small">${u[c] ? bytes(u[c]) : '–'}</td>`).join('')}<td class="num">${bytes(u.total)}</td>
      <td>${fr > 5e6 && u.name !== '.venv' ? `<button class="btn sm" data-t="${esc(target(u.name))}" data-n="${esc(u.name)}">Free space…</button>` : ''}</td></tr>`; }).join('')}
    </tbody></table></div>
    <h3>What can be freed, and how it comes back</h3><div class="panel"><table class="t"><tbody>
    ${S.freeable.map(f => `<tr><td class="num" style="width:90px">${bytes(f.bytes)}</td><td><b>${esc(f.what)}</b></td><td class="small muted">${esc(f.how)}</td></tr>`).join('')}</tbody></table></div>`;
  $$('[data-t]', main).forEach(b => b.onclick = () => modal(`<h2>Free space: ${esc(b.dataset.n)}</h2>
    <p class="hint">Pick what may go. First a dry run lists every file; nothing is deleted until you confirm.</p>
    <div class="col"><label class="chk"><input type="checkbox" value="cache" checked> cache (rebuildable data, e.g. footage caches)</label>
      <label class="chk"><input type="checkbox" value="checks"> checks (comparison videos, section renders)</label>
      <label class="chk"><input type="checkbox" value="finals"> finals (full renders)</label></div>
    <div class="row" style="margin-top:12px"><button class="btn" id="dry">Dry run</button><button class="btn danger" id="real" disabled>Delete these files</button></div>
    <pre class="log" id="plog" style="margin-top:10px" hidden></pre>`, el => {
    const what = () => $$('input[type=checkbox]:checked', el).map(x => x.value);
    $('#dry', el).onclick = async () => {
      const j = await startJob('prune', {target: b.dataset.t, what: what(), yes: false}, false); if (!j) return;
      const pre = $('#plog', el); pre.hidden = false; pre.textContent = '';
      followJob(j.id, pre, jj => { $('#real', el).disabled = jj.status !== 'done'; });
    };
    $('#real', el).onclick = async () => {
      if (!confirm('Delete the files listed in the dry run? They can be rebuilt, but that takes time.')) return;
      const j = await startJob('prune', {target: b.dataset.t, what: what(), yes: true}, false); if (!j) return;
      const pre = $('#plog', el); pre.textContent = ''; $('#real', el).disabled = true;
      followJob(j.id, pre, jj => toast(`Free space: ${jj.status}`, jj.status === 'done' ? 'ok' : 'err'));
    };
  }));
}

// ============================================================================================ downloads (yt-dlp)
const FILE_RX = /^[A-Za-z]:\\.+\.(mp4|mkv|webm|mov|m4v|mp3|m4a)$/i;
async function downloadModal() {
  const S = await api('/api/settings');
  const yt = S.tools.find(t => t.name === 'yt-dlp') || {};
  modal(`<h2>Download from a link</h2>
    <p class="hint">${yt.found ? `yt-dlp ${esc(yt.version || '')} · <span class="mono small">${esc(yt.path)}</span>`
      : `<b class="bad">yt-dlp not found.</b> ${esc(yt.how || '')} · <a href="#/settings">Settings</a>`}<br>
      Videos are saved in <code>refs\</code>, audio in <code>refs\audio\</code>. One video per link (no playlists).
      Only download what you are allowed to use.</p>
    <input type="text" id="durl" placeholder="https://www.youtube.com/watch?v=…  (YouTube, Vimeo, TikTok, Instagram … anything yt-dlp supports)">
    <div class="row" style="margin-top:10px"><select id="dpre">${S.presets.map(o => `<option value="${o.id}" ${o.id === S.settings.download_preset ? 'selected' : ''}>${esc(o.label)}</option>`).join('')}</select>
      <button class="btn pri" id="dgo" ${yt.found ? '' : 'disabled'}><svg class="i"><use href="#i-download"/></svg>Download</button>
      <span id="dst" class="small muted"></span></div>
    <pre class="log" id="dlog" hidden style="max-height:240px;margin-top:10px"></pre>
    <div id="ddone" hidden style="margin-top:10px"></div>`, el => {
    const inp = $('#durl', el); inp.focus();
    inp.onkeydown = e => { if (e.key === 'Enter') $('#dgo', el).click(); };
    $('#dgo', el).onclick = async () => {
      const url = inp.value.trim();
      if (!/^https?:\/\//i.test(url)) { toast('Paste a full link starting with https://', 'err'); return; }
      const j = await startJob('download', {url, preset: $('#dpre', el).value}, false);
      if (!j) return;
      $('#dgo', el).disabled = true; $('#dst', el).textContent = 'downloading…'; $('#ddone', el).hidden = true;
      const pre = $('#dlog', el); pre.hidden = false; pre.textContent = '';
      followJob(j.id, pre, done => {
        $('#dgo', el).disabled = false;
        $('#dst', el).textContent = done.status === 'done' ? 'done ✓' : done.status;
        const file = pre.textContent.split('\n').map(l => l.trim()).reverse().find(l => FILE_RX.test(l));
        if (done.status !== 'done' || !file) return;
        const isVideo = !/\.(mp3|m4a)$/i.test(file);
        const rel = file.toLowerCase().startsWith(S.lab.toLowerCase() + '\\') ? file.slice(S.lab.length + 1).replace(/\\/g, '/') : '';
        const box = $('#ddone', el); box.hidden = false;
        box.innerHTML = `<div class="small">Saved: <span class="mono">${esc(file)}</span></div>
          <div class="row" style="margin-top:8px">${isVideo ? '<button class="btn pri" id="dan">Analyse it</button>' : ''}
          ${rel ? '<button class="btn" id="dop">Show in folder</button>' : ''}</div>`;
        if (isVideo) $('#dan', el).onclick = () => { closeModal(); analyseModal(file); };
        if (rel) $('#dop', el).onclick = () => openPath(rel, true);
      });
    };
  });
}

// ============================================================================================ settings
async function pageSettings(main) {
  const S = await api('/api/settings');
  const st = S.settings;
  main.innerHTML = `<div class="head"><div><h1>Settings</h1><div class="sub">The programs the lab uses and your download preferences -
    saved in <span class="mono">settings.json</span> in the lab folder (yours, not part of the shared app).</div></div></div>
  <div class="panel"><div class="row sp"><h2>Programs</h2><button class="btn sm" id="recheck">Check again</button></div>
    <table class="t tools"><thead><tr><th>Program</th><th></th><th>Found at</th><th>Version</th><th>What for · how to get it</th></tr></thead><tbody>
    ${S.tools.map(t => `<tr><td><b>${esc(t.label)}</b><div class="need">${esc(t.need)}</div></td>
      <td class="st">${t.found ? '<span class="tag done">found</span>' : `<span class="tag ${t.need === 'required' ? 'failed' : ''}">missing</span>`}</td>
      <td class="mono small">${esc(t.path || '–')}</td><td class="small">${esc(t.version || '')}</td><td class="small muted">${esc(t.how)}</td></tr>`).join('')}
    </tbody></table></div>
  <div class="grid g2" style="margin-top:14px">
    <div class="panel"><h2>Downloads (yt-dlp)</h2><div class="form">
      <label for="ytp">yt-dlp.exe</label><input type="text" id="ytp" value="${esc(st.ytdlp_path)}" placeholder="empty = find it automatically">
      <label for="pre">Default format</label><select id="pre">${S.presets.map(o => `<option value="${o.id}" ${o.id === st.download_preset ? 'selected' : ''}>${esc(o.label)} → ${esc(o.folder)}</option>`).join('')}</select>
      <label for="nm">File name</label><input type="text" id="nm" class="mono" value="${esc(st.download_name)}">
      <span></span><div class="small muted">yt-dlp fields, e.g. <code>%(title).80s [%(id)s].%(ext)s</code> or <code>%(uploader)s - %(title)s.%(ext)s</code> (no folders)</div></div></div>
    <div class="panel"><h2>Claude Code</h2><div class="form">
      <label for="clp">claude</label><input type="text" id="clp" value="${esc(st.claude_path)}" placeholder="empty = find it automatically"></div>
      <div class="small muted" style="margin-top:10px">The review of every contact sheet, learning from your feedback and the Resolve
      rebuilds run in Claude Code; the app opens it in the lab folder with the right request.</div>
      <div class="row" style="margin-top:10px">${claudeBtn('', 'Open Claude Code in the lab folder')}</div></div>
  </div>
  <div class="panel" style="margin-top:14px"><h2>Sharing &amp; updates</h2>
    ${updateBox(S.update, null)}
    <div class="form">
      <label for="who">Your name</label><div><input type="text" id="who" value="${esc(st.author)}" placeholder="e.g. alex (shown on what you share)" style="max-width:320px">
        <div class="small muted">Used for “Share my knowledge” - letters, numbers and - only.</div></div>
      <label>GitHub</label><div class="small">${S.update && S.update.remote ? `<span class="mono">${esc(S.update.remote)}</span> · branch ${esc(S.update.branch || '')}` : `<span class="muted">${esc((S.update && S.update.error) || 'not checked yet')}</span>`}
        ${S.update && S.update.checked ? `<div class="dim">checked ${esc(S.update.checked)} · ${S.update.can_update ? `<b class="amber">${S.update.behind} update(s) waiting</b>` : 'up to date'}${S.update.ahead ? ` · ${S.update.ahead} of your commits not on GitHub yet` : ''}</div>` : ''}</div>
      <label>Updates</label><div class="col" style="gap:4px">
        <label class="chk small"><input type="checkbox" id="upc" ${st.update_check ? 'checked' : ''}> check GitHub for a new version when MotionLab starts</label>
        <label class="chk small"><input type="checkbox" id="upa" ${st.update_auto ? 'checked' : ''}> install it right away (your videos, analyses, settings and knowledge are never touched)</label></div>
      <span></span><div class="row"><button class="btn sm" id="upcheck">Check now</button>${S.update && S.update.can_update ? '<button class="btn sm pri" data-update>Update now</button>' : ''}</div>
      ${S.update && S.update.git && !S.update.repo ? `<label for="conn">Connect to GitHub</label><div><div class="row"><input type="text" id="conn" placeholder="https://github.com/name/MotionLab" style="max-width:360px"><button class="btn sm" id="connb">Connect</button></div>
        <div class="small muted">This copy was not installed with git clone. Connecting turns on updates and sharing; only the app's own files are replaced by the repo's version.</div></div>` : ''}
    </div></div>
  <div class="row" style="margin-top:12px"><button class="btn pri" id="save">Save settings</button><span id="sv" class="small muted"></span></div>
  <div class="grid g2" style="margin-top:14px">
    <div class="panel"><h2>Shortcuts</h2><div class="small muted">A “MotionLab” shortcut with the app icon, opens the app without a console window.</div>
      <div class="row" style="margin-top:10px"><button class="btn" data-sc="desktop">Add to the Desktop</button><button class="btn" data-sc="startmenu">Add to the Start menu</button></div></div>
    <div class="panel"><h2>About</h2><div class="kv"><b>Version</b><span>MotionLab ${esc(S.version)}</span><b>Lab folder</b><span class="mono small">${esc(S.lab)}</span></div>
      <div class="row" style="margin-top:10px"><button class="btn" data-open=".">Open the lab folder</button></div></div>
  </div>`;
  $('#recheck').onclick = () => route();
  wireUpdateBox(main);
  $('#upcheck').onclick = async () => {
    const b = $('#upcheck'); b.disabled = true; b.textContent = 'Checking…';
    try { const u = await api('/api/update/check', {}); toast(u.error ? u.error : u.can_update ? `${u.behind} update(s) available` : 'Up to date', u.error ? 'err' : 'ok'); route(); }
    catch (e) { toast(e.message, 'err'); b.disabled = false; b.textContent = 'Check now'; }
  };
  const cb = $('#connb'); if (cb) cb.onclick = async () => {
    if (!confirm('Connect this copy to ' + $('#conn').value + '? The app\'s own files are replaced by the repo version; your data stays.')) return;
    try { const r = await api('/api/update/connect', {url: $('#conn').value}); toast('Connected to ' + r.remote, 'ok'); route(); } catch (e) { toast(e.message, 'err'); }
  };
  $('#save').onclick = async () => {
    try {
      await api('/api/settings', {settings: {ytdlp_path: $('#ytp').value, download_preset: $('#pre').value,
                                             download_name: $('#nm').value, claude_path: $('#clp').value,
                                             author: $('#who').value, update_check: $('#upc').checked,
                                             update_auto: $('#upa').checked}});
      $('#sv').textContent = 'saved ✓'; toast('Settings saved', 'ok'); setTimeout(route, 500);
    } catch (e) { toast(e.message, 'err'); }
  };
  $$('[data-sc]', main).forEach(b => b.onclick = async () => {
    try { const r = await api('/api/shortcut', {where: b.dataset.sc}); toast('Shortcut created: ' + r.path, 'ok'); }
    catch (e) { toast(e.message, 'err'); }
  });
}

// ============================================================================================ category / tags editor
async function metaModal(R) {
  const ST = await api('/api/settings');
  modal(`<h2>Category and tags</h2>
    <p class="hint">What kind of video this is. Pacing, effects and lessons are compared within a category, and shared that way.</p>
    <div class="form"><label for="mcat">Category</label><select id="mcat">${ST.categories.map(o => `<option value="${o.id}" ${o.id === R.category ? 'selected' : ''}>${esc(o.label)}</option>`).join('')}</select>
      <label for="mtags">Tags</label><input type="text" id="mtags" value="${esc((R.tags || []).join(', '))}" placeholder="e.g. instagram, asmr, recipe"></div>
    <div class="row" style="margin-top:12px"><button class="btn pri" id="msave">Save</button></div>`, el => {
    $('#msave', el).onclick = async () => {
      try { await api(`/api/reference/${encodeURIComponent(R.name)}/meta`, {category: $('#mcat', el).value, tags: $('#mtags', el).value}); closeModal(); toast('Saved', 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    };
  });
}

// ============================================================================================ knowledge
const fmtNum = v => v == null ? '–' : v;
async function pageKnowledge(main) {
  const K = await api('/api/knowledge');
  const U = await api('/api/update').catch(() => ({}));
  let cat = '';
  const pend = K.pending.cards + K.pending.lessons;
  const draw = () => {
    const cards = K.cards.filter(c => !cat || (c.category || 'unset') === cat);
    main.innerHTML = `<div class="head"><div><h1>Knowledge</h1><div class="sub">What everyone's MotionLab has learned: one card per analysed reference (yours and your friends'),
      pacing per category, and lessons. Shared through GitHub - only text and numbers, never videos or frames.</div></div>
      <div class="row">${K.summary ? `<button class="btn" data-open="${esc(K.summary.replace(/\\/g, '/'))}">Summary Claude reads</button>` : ''}<button class="btn" id="resum">Rebuild summary</button></div></div>
    <div class="grid g2">
      <div class="panel"><h2>Share what you learned</h2>
        <div class="kv"><b>Your name</b><span>${K.author ? `<b>${esc(K.author)}</b>` : '<a href="#/settings">not set - Settings</a>'}</span>
          <b>Not shared yet</b><span>${K.pending.cards} reference card(s), ${K.pending.lessons} lesson(s)${K.pending.card_titles.length ? `<div class="small muted">${K.pending.card_titles.map(esc).join(' · ')}</div>` : ''}</span>
          <b>GitHub</b><span class="small">${U.remote ? `<span class="mono">${esc(U.remote)}</span>` : `<span class="muted">${esc(U.error || 'not connected')}</span>`}</span>
          <b>Last shares</b><span class="small muted">${K.shares.length ? K.shares.slice(-3).reverse().map(x => `${esc(x.when)}: ${x.cards} card(s), ${x.lessons} lesson(s) via ${esc(x.how)}`).join('<br>') : 'none yet'}</span></div>
        <div class="row" style="margin-top:12px"><button class="btn pri" id="share" ${K.author ? '' : 'disabled'}><svg class="i"><use href="#i-knowledge"/></svg>Share my knowledge</button>
          <span class="small muted">${pend ? '' : 'everything is shared'}</span></div>
        <div id="shareres" class="small" style="margin-top:8px"></div></div>
      <div class="panel"><h2>From your friends</h2>
        <div class="small muted">Shared cards arrive with every update. Friends without GitHub access send a pack file: put it in <code>knowledge\\inbox\\</code>.</div>
        ${K.inbox.length ? `<table class="t" style="margin-top:8px"><tbody>${K.inbox.map(x => `<tr><td class="mono small">${esc(x.file)}</td><td class="small">${x.error ? `<span class="bad">${esc(x.error)}</span>` : `${esc(x.author)} · ${x.cards} card(s), ${x.lessons} lesson(s)`}</td><td>${x.error ? '' : `<button class="btn sm" data-imp="${esc(x.file)}">Import</button>`}</td></tr>`).join('')}</tbody></table>` : '<div class="dim small" style="margin-top:8px">No packs in the inbox.</div>'}
        <div class="row" style="margin-top:8px"><button class="btn sm" data-open="knowledge/inbox">Open the inbox folder</button></div>
        <h3>Lessons waiting for review</h3>${K.incoming.length ? `<div class="small">${K.incoming.map(x => `${esc(x.file)} (${x.lessons})`).join(' · ')}</div>
          <div class="row" style="margin-top:8px">${claudeBtn('Review the incoming lessons in knowledge\\incoming\\ (see Reviewing incoming lessons in the analyze-reference skill) and merge the good ones into the shared lessons.md', 'Review them in Claude Code')}</div>` : '<div class="dim small">None.</div>'}
      </div></div>
    <h3>Pacing by category</h3>
    <div class="panel"><table class="t"><thead><tr><th>Category</th><th class="num">References</th><th>By</th><th class="num">Cuts / min</th><th class="num">Avg shot</th><th class="num">Cuts in 3 s</th><th class="num">Effects / min</th><th class="num">On beat</th><th>Effects seen most</th></tr></thead><tbody>
      ${K.categories.map(c => `<tr class="${c.category === cat ? 'sel' : ''}" data-cat="${esc(c.category)}" style="cursor:pointer"><td><b>${esc(c.label)}</b></td><td class="num">${c.references}</td><td class="small">${esc(c.authors.join(', '))}</td>
        <td class="num">${fmtNum(c.cuts_per_min)}</td><td class="num">${c.avg_shot_s == null ? '–' : c.avg_shot_s + ' s'}</td><td class="num">${fmtNum(c.hook_cuts_3s)}</td><td class="num">${fmtNum(c.effects_per_min)}</td>
        <td class="num">${c.cuts_on_beat_pct == null ? '–' : c.cuts_on_beat_pct + ' %'}</td><td class="small muted">${Object.entries(c.families).slice(0, 4).map(([f, n]) => `${esc(f)} ${n}`).join(' · ')}</td></tr>`).join('') || '<tr><td colspan="9" class="dim">No cards yet - analyse a reference.</td></tr>'}
    </tbody></table></div>
    <h3>References ${cat ? `in ${esc((K.categories.find(c => c.category === cat) || {}).label || cat)} <a href="#" id="allcats" class="small">show all</a>` : ''}</h3>
    <div class="panel"><table class="t click"><thead><tr><th>Video</th><th>By</th><th>Category</th><th>Format</th><th class="num">Cuts / min</th><th class="num">Avg shot</th><th class="num">Effects / min</th><th class="num">Verdicts</th><th></th></tr></thead><tbody>
      ${cards.map((c, i) => { const P = c.pacing || {}, V = c.verdicts || {}; return `<tr data-i="${K.cards.indexOf(c)}"><td><b>${esc(c.title)}</b>${c.url ? ` <a href="${esc(c.url)}" target="_blank" rel="noopener" class="small" onclick="event.stopPropagation()">${esc(c.platform || 'link')}</a>` : ''}</td>
        <td class="small">${esc(c.author || '')}</td><td class="small">${esc(c.category_label || '')}</td><td class="small muted">${esc((c.format || {}).label || '')}</td>
        <td class="num">${fmtNum(P.cuts_per_min)}</td><td class="num">${P.avg_shot_s == null ? '–' : P.avg_shot_s + ' s'}</td><td class="num">${fmtNum(P.effects_per_min)}</td>
        <td class="num small">${V.given || 0}/${V.events || 0}</td><td>${c.origin === 'local' ? (c.pending ? '<span class="tag running">not shared</span>' : '<span class="tag done">shared</span>') : '<span class="tag">friend</span>'}</td></tr>`; }).join('') || '<tr><td colspan="9" class="dim">Nothing here yet.</td></tr>'}
    </tbody></table></div>`;
    $$('tr[data-cat]', main).forEach(r => r.onclick = () => { cat = cat === r.dataset.cat ? '' : r.dataset.cat; draw(); });
    const ac = $('#allcats', main); if (ac) ac.onclick = e => { e.preventDefault(); cat = ''; draw(); };
    $$('tr[data-i]', main).forEach(r => r.onclick = () => cardModal(K.cards[+r.dataset.i]));
    $$('[data-imp]', main).forEach(b => b.onclick = async () => {
      try { const r = await api('/api/knowledge/import', {file: b.dataset.imp}); toast(`Imported ${r.cards} card(s) and ${r.lessons} lesson(s) from ${r.author}`, 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    });
    $('#resum', main).onclick = async () => { try { await api('/api/knowledge/summary', {}); toast('Summary rebuilt', 'ok'); route(); } catch (e) { toast(e.message, 'err'); } };
    $('#share', main).onclick = async () => {
      const b = $('#share', main); b.disabled = true; b.textContent = 'Sharing…';
      const out = $('#shareres', main);
      try {
        const r = await api('/api/knowledge/share', {});
        if (r.nothing) out.innerHTML = '<span class="muted">Nothing new to share.</span>';
        else if (r.pushed && r.restarting) { waitForServer('Shared ✓ - GitHub also had a new MotionLab version: restarting with it…'); return; }
        else if (r.pushed) { out.innerHTML = `<span class="ok">Shared ${r.cards} reference card(s) and ${r.lessons} lesson(s) on GitHub ✓</span> <span class="muted">- your friends get them with their next update.</span>`; setTimeout(route, 2500); }
        else out.innerHTML = `<span class="bad">Not uploaded: ${esc(r.error || 'unknown reason')}</span>${r.pack ? `<div>Send this file to a friend who can upload it (they put it in knowledge\\inbox\\): <a href="#" data-open="${esc(r.pack)}" data-reveal class="mono">${esc(r.pack)}</a></div>` : ''}`;
      } catch (e) { out.innerHTML = `<span class="bad">${esc(e.message)}</span>`; }
      b.disabled = false; b.innerHTML = '<svg class="i"><use href="#i-knowledge"/></svg>Share my knowledge';
    };
  };
  draw();
}

async function cardModal(c) {
  let C = c;
  try { C = await api('/api/knowledge/card?id=' + encodeURIComponent(c._file || c.video_id)); } catch (e) { /* the list entry is enough */ }
  const P = C.pacing || {};
  const fx = (C.effects || []).filter(e => !e.false_alarm && e.family !== 'Hard cut');
  modal(`<h2>${esc(C.title)}</h2>
    <div class="small muted">${esc(C.category_label || '')} · ${esc((C.format || {}).label || '')} · by ${esc(C.author || 'you')}${C.url ? ` · <a href="${esc(C.url)}" target="_blank" rel="noopener">${esc(C.platform || 'link')}</a>` : ''}
      ${C.analysis ? ` · <a href="#/ref/${encodeURIComponent(C.analysis)}" onclick="closeModal()">open the analysis</a>` : ''}</div>
    <div class="small pacing" style="margin:10px 0">Pacing: <b>${fmtNum(P.cuts_per_min)}</b> cuts/min · shots avg <b>${fmtNum(P.avg_shot_s)} s</b> (p10 ${fmtNum(P.p10_shot_s)} s, p90 ${fmtNum(P.p90_shot_s)} s) · <b>${fmtNum(P.hook_cuts_3s)}</b> cut(s) in 3 s · <b>${fmtNum(P.effects_per_min)}</b> effects/min${P.bpm ? ` · ${P.bpm} BPM` : ''}</div>
    <table class="t"><thead><tr><th>Effect</th><th>Frames</th><th>What happens</th><th>Verdict</th></tr></thead><tbody>
      ${fx.map(e => `<tr><td class="small"><b>${esc(e.label)}</b></td><td class="small mono">f${e.start}–${e.end}<div class="dim">${esc(e.tc_start || '')}</div></td>
        <td class="small">${esc(e.what || '')}${e.note ? `<div class="amber">note: ${esc(e.note)}</div>` : ''}</td>
        <td class="small">${e.verdict ? `<span class="vdot ${esc(e.verdict)}"></span> ${esc(e.verdict)}` : '–'}</td></tr>`).join('') || '<tr><td colspan="4" class="dim">No effects besides cuts.</td></tr>'}
    </tbody></table>`);
}

route();
