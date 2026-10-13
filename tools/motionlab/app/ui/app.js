/* MotionLab app - plain JavaScript, no build step. Pages: home, references (other people's videos: download,
   analyses + verdicts), videos (your footage: renders, timing, Resolve + library picks), prompts, library, jobs, storage,
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
let MODAL_BACK = null;                 // where Back / Esc / x / a click outside return to (a dialog opened from another)
function modal(html, init, cls = '') {
  const m = $('#modal'); MODAL_BACK = null; $('.mbox', m).className = 'mbox' + (cls ? ' ' + cls : '');
  $('.mbody', m).innerHTML = html; m.hidden = false; $('.mbox', m).scrollTop = 0; if (init) init($('.mbody', m));
}
function modalBack(fn) {               // call right after modal(): a "Back" to the dialog this one came from
  MODAL_BACK = fn;
  const b = document.createElement('button'); b.className = 'btn sm ghost mback'; b.textContent = '← Back'; b.onclick = dismissModal;
  $('#modal .mbody').prepend(b);
}
function closeModal() { MODAL_BACK = null; $('#modal').hidden = true; $('#modal .mbody').innerHTML = ''; }
function dismissModal() { const back = MODAL_BACK; closeModal(); if (back) back(); }
$('#modal').addEventListener('mousedown', e => { if (e.target.id === 'modal' || e.target.closest('.mclose')) dismissModal(); });
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
// Claude Code in a new console in the lab folder, with an optional first message (the app's hand-off texts). task =
// what it is for (system.TASKS: review, feedback, lessons, library, recreate, prompt, free) - it picks the effort level
async function openClaude(prompt = '', task = 'free', label = '') {
  try {
    const r = await api('/api/claude', {prompt, task, label});
    toast('Claude Code is opening in a new window' + (r.effort ? ` (effort: ${r.effort})` : ''), 'ok');
  } catch (e) { toast(e.message, 'err'); }
}
const claudeBtn = (prompt, label = 'Open in Claude Code', task = 'free', name = '', cls = 'sm cl') =>
  `<button class="btn ${cls}" data-claude="${esc(prompt)}" data-task="${task}" data-label="${esc(name)}"><svg class="i"><use href="#i-claude"/></svg>${label}</button>`;
document.addEventListener('click', e => {
  const c = e.target.closest('[data-claude]');
  if (c) { e.preventDefault(); openClaude(c.dataset.claude, c.dataset.task || 'free', c.dataset.label || ''); return; }
  const f = e.target.closest('[data-feedback]');
  if (f) { e.preventDefault(); feedbackModal(f.dataset.feedback); return; }
  if (e.target.closest('[data-tips]')) { e.preventDefault(); tipsModal(); }
});
$('#side-claude').onclick = () => openClaude('');
$('#side-update').onclick = () => updateModal();
$('#side-check').onclick = () => checkUpdates();
$('#side-news').onclick = () => newsModal();
function md(src) {                                     // small Markdown subset for the lab's reports
  const out = []; let para = [], list = null, table = false, pre = null, li = null;
  const inl = s => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/(^|[\s(])\*([^*\s][^*]*?)\*(?=[\s).,:;!?]|$)/g, '$1<i>$2</i>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
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
      li = m[1]; out.push('<li>' + inl(li) + '</li>'); continue;       // li: its raw text, for wrapped lines
    }
    if (/^\s*\|/.test(ln)) {
      if (/^\s*\|[\s|:-]+\|\s*$/.test(ln)) continue;
      if (!table) { flush(); out.push('<table>'); table = true; }
      out.push('<tr>' + ln.trim().replace(/^\||\|$/g, '').split('|').map(c => '<td>' + inl(c.trim()) + '</td>').join('') + '</tr>');
      continue;
    }
    if (list && /^\s{2,}\S/.test(ln)) { li += ' ' + ln.trim(); out[out.length - 1] = '<li>' + inl(li) + '</li>'; continue; }
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
// an empty page: what goes here, and the one button that starts it, in the middle (no "No ... yet" line)
const emptyHero = (icon, title, text, btns) => `<div class="ehero"><svg class="ic"><use href="#i-${icon}"/></svg><h2>${title}</h2>
  <p>${text}</p><div class="row">${btns}</div></div>`;
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
  if (e.key === 'Escape' && !$('#modal').hidden) { dismissModal(); return; }
  if (KEYS && $('#modal').hidden) KEYS(e);
});
document.addEventListener('click', e => {
  const o = e.target.closest('[data-open]');
  if (o) { e.preventDefault(); openPath(o.dataset.open, o.hasAttribute('data-reveal')); }
});

const PAGES = [
  [/^#?\/?$/, pageHome, 'home'], [/^#\/refs$/, pageRefs, 'refs'],
  [/^#\/ref\/([^/?]+)(?:\?(?:e=(\w+)|(misses)))?$/, pageRef, 'refs'], [/^#\/projects$/, pageProjects, 'projects'],
  [/^#\/project\/([^/]+)(?:\/(\w+))?$/, pageProject, 'projects'], [/^#\/library$/, pageLibrary, 'library'],
  [/^#\/jobs(?:\/(\d+))?$/, pageJobs, 'jobs'], [/^#\/storage$/, pageStorage, 'settings'],
  [/^#\/settings$/, pageSettings, 'settings'], [/^#\/knowledge$/, pageKnowledge, 'knowledge'],
  [/^#\/prompts(?:\/([\w-]+))?$/, pagePrompts, 'prompts']];
async function route() {
  CLEAN.forEach(f => { try { f(); } catch (e) { /* ignore */ } }); CLEAN = []; KEYS = null; hideTip();
  const h = location.hash || '#/';
  for (const [rx, fn, nav] of PAGES) {
    const m = h.match(rx);
    if (!m) continue;
    $$('#side a[data-nav]').forEach(a => a.classList.toggle('on', a.dataset.nav === nav));
    document.body.dataset.page = nav;                         // the section's accent colour (app.css)
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
const API_LEVEL = 12;               // the server functions this page needs (server.API_LEVEL)
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
    sideUpdate(p);
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

// ---- the analysis page's Content tab (0.3.5): what the video says (transcript, clickable frame + timecode) and how it
// performs (views against the channel's followers). tools\content.py writes both; they stay on this PC.
function contentTab(el, R, P) {
  el.dataset.done = '1';
  const C = R.content || {}, T = C.transcript, S = C.stats, fps = R.video.fps;
  const n = v => v == null ? '–' : Number(v).toLocaleString('en-US');
  const big = (v, l, t = '') => `<div class="stat" title="${esc(t)}"><div class="n">${v}</div><div class="l">${esc(l)}</div></div>`;
  el.innerHTML = `<div class="grid g2 cgrid"><div class="panel"><div class="row sp"><h2>How it performs</h2>
      <button class="btn sm" data-cjob="content_stats">${S ? 'Update the numbers' : 'Get the numbers'}</button></div>
      ${S ? `<div class="row stats">${big(n(S.views), 'views')}${big(S.outperformer != null ? S.outperformer + '×' : '–', 'views ÷ followers', 'the outperformer score: views against the channel\'s followers (above 1 = it reached beyond the channel)')}
          ${big(n(S.views_per_day), 'views a day', S.days_online ? `over ${S.days_online} days online` : '')}${big(n(S.likes), 'likes')}${big(n(S.comments), 'comments')}${big(n(S.followers), 'followers')}</div>
        <div class="small muted" style="margin-top:8px">${esc(S.uploader || '')} · ${esc(S.platform || '')} · online since ${esc(S.upload_date || '?')} · numbers from ${esc(S.fetched)}${(S.history || []).length > 1 ? ` · ${S.history.length} fetches kept` : ''}</div>`
        : '<div class="muted small">Not fetched yet: one quick request to the video\'s page (no download).</div>'}
      <pre class="log" hidden></pre></div>
    <div class="panel"><h2>Coming soon</h2><div class="small muted">The topics, the hook and the call to action, every shot described, the text on screen, and what ~10 videos on one subject have in common.</div></div></div>
    <div class="panel" style="margin-top:14px"><div class="row sp"><h2>What it says</h2>
      <div class="row">${T ? `<input type="search" id="cq" placeholder="Search the words…" style="width:240px">` : ''}
        <button class="btn sm" data-cjob="content_transcript">${T ? 'Fetch again' : 'Get the transcript'}</button></div></div>
      ${T ? `<div class="small muted" style="margin-bottom:8px">${plural(T.lines.length, 'line')} · ${plural(T.words || 0, 'word')} · ${T.kind === 'auto' ? 'the platform\'s automatic captions' : 'uploaded subtitles'} (${esc(T.lang || '?')})${T.word_timings ? ', timed per word' : ''} · fetched ${esc(T.fetched || '')} · click a line to see it in the player</div>
        <div class="tlines"><table class="t click"><tbody id="clines">${T.lines.map((l, i) => `<tr data-i="${i}" data-f="${l.start}"><td class="fr">f${l.start}</td><td class="tc">${tc(l.start, fps)}</td><td>${esc(l.text)}</td></tr>`).join('')}</tbody></table></div>`
        : '<div class="muted small">No transcript yet: the platform\'s own subtitles are fetched in a few seconds, nothing is downloaded. Videos without subtitles cannot be read yet.</div>'}
      <pre class="log" hidden></pre></div>`;
  $$('[data-cjob]', el).forEach(b => b.onclick = async () => {
    const pre = b.closest('.panel').querySelector('pre.log');
    const j = await startJob(b.dataset.cjob, {name: R.name, again: !!T}, false);
    if (!j) return;
    b.disabled = true; pre.hidden = false; pre.textContent = '';
    followJob(j.id, pre, jj => {
      toast(`${jj.title}: ${jj.status}`, jj.status === 'done' ? 'ok' : 'err');
      if (jj.status === 'done') api('/api/reference/' + encodeURIComponent(R.name)).then(NR => { R.content = NR.content; contentTab(el, R, P); });
      else b.disabled = false;
    });
  });
  if (!T) return;
  const rows = $$('#clines tr', el);
  rows.forEach(tr => tr.onclick = () => { if (P) { P.v.pause(); P.seek(+tr.dataset.f); $('#player').scrollIntoView({behavior: 'smooth', block: 'center'}); } });
  const q = $('#cq', el);
  q.oninput = () => { const s = q.value.toLowerCase(); rows.forEach((tr, i) => { tr.hidden = !!s && !T.lines[i].text.toLowerCase().includes(s); }); };
  let last = -1;
  if (P) P.on(f => {                                        // the line being said is marked while the video plays
    let k = -1;
    for (let i = 0; i < T.lines.length && T.lines[i].start <= f; i++) if (f <= T.lines[i].end) k = i;
    if (k === last) return;
    if (last >= 0 && rows[last]) rows[last].classList.remove('sel');
    if (k >= 0 && rows[k]) rows[k].classList.add('sel');
    last = k;
  });
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
    // possible misses: a red dashed line + a red ▲ (red until you answered it)
    (R.near_misses || []).forEach(m => {
      if (!vis(m.frame, m.frame)) return;
      const x = Math.round(this.x(m.frame) + (this.zoom ? ppf / 2 : 0)), open = !(this.opts.missDone || (() => false))(m.frame);
      g.fillStyle = open ? '#ff3b3b' : '#8a4b4b';
      for (let y = 12; y < H - 24; y += 6) g.fillRect(x, y, 1, 3);
      g.beginPath(); g.moveTo(x - 6, H - 17); g.lineTo(x + 6, H - 17); g.lineTo(x, H - 27); g.fill();
    });
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
    const miss = y >= this.H - 30 && y <= this.H - 14 ? (this.R.near_misses || []).find(m => Math.abs(this.x(m.frame) - x) <= 7) : null;
    const ev = miss ? null : this.R.events.find(ev => { const [ly, h] = this.laneY(this.lanes.lane[ev.id]); return y >= ly && y <= ly + h && f >= ev.start - slack && f <= ev.end + slack; });
    return {f: clamp(f, 0, this.N - 1), ev, miss};
  }
  hover(e) {
    const {f, ev, miss} = this.hit(e);
    if (miss) showTip(`<b class="bad">Possible miss</b> ${ftc(miss.frame, this.fps)}<br>${esc(miss.why)}<br><span class="dim">click to check it</span>`, e.clientX, e.clientY);
    else if (ev) showTip(`<b class="amber mono">${ev.id}</b> ${esc(ev.label)}<br>${frange(ev.start, ev.end, this.fps)}`, e.clientX, e.clientY);
    else showTip(`${ftc(f, this.fps)} · click to jump`, e.clientX, e.clientY);
  }
  click(e) {
    const {f, ev, miss} = this.hit(e);
    if (miss && this.opts.onMiss) this.opts.onMiss(miss);
    else if (ev && this.opts.onSelect) this.opts.onSelect(ev); else if (this.opts.onSeek) this.opts.onSeek(f);
  }
}

// ============================================================================================ home
async function pageHome(main) {
  const s = await api('/api/status');
  const pct = (a, b) => b ? Math.round(100 * a / b) : 0;
  main.innerHTML = `
  <div class="head"><div><h1>MotionLab</h1></div>
    <div class="row"><button class="btn pri" id="an">＋ Analyse a video</button><button class="btn" data-open=".">Open folder</button></div></div>
  ${updateBox(s.update, s.update_result && (s.update_result.set_aside || []).length ? s.update_result : null)}
  <div class="grid g5">
    <a class="stat card" href="#/refs"><div class="n">${s.references}</div><div class="l">references · ${s.events} effects found</div></a>
    <a class="stat card" href="#/refs"><div class="n">${s.verdicts}<span class="muted" style="font-size:18px"> / ${s.events}</span></div>
      <div class="l">effects you checked</div><div class="bar" style="margin-top:8px"><i style="width:${pct(s.verdicts, s.events)}%"></i></div></a>
    <a class="stat card" href="#/projects"><div class="n">${s.projects}</div><div class="l">your videos</div></a>
    <a class="stat card" href="#/library"><div class="n">${s.library}</div><div class="l">saved effects${s.picks ? ` · ${s.picks} picked` : ''}</div></a>
    <a class="stat card" href="#/knowledge"><div class="n" id="kn-n">…</div><div class="l" id="kn-l">reference cards</div></a>
  </div>
  ${s.setup.length ? `<div class="panel upd" style="margin-top:14px"><h2>Setup</h2><ul class="next">${s.setup.map(t => `<li><b>${esc(t.label)}</b> not found <span class="dim small">(${esc(t.need)})</span><div class="small muted">${esc(t.how)}</div></li>`).join('')}</ul>
    <a href="#/settings">Settings → Programs</a></div>` : ''}
  <div class="panel" style="margin-top:14px"><h2>Where to start</h2>
    <div class="small muted" style="margin-bottom:10px">Learn from a video you like, in six steps - click a step to do it.</div>${flowHow()}</div>
  ${s.roadmap ? `<div class="panel roadmap" style="margin-top:14px"><div class="row sp"><h2>Roadmap</h2><span class="row"><span class="hint">click to enlarge</span>${claudeBtn('/whats-next', 'What next? Ask Claude', 'plan', '', 'sm cl')}</span></div>
    <img src="${fileUrl(s.roadmap)}" alt="roadmap"></div>` : ''}
  <div class="panel" style="margin-top:14px"><h2>Status</h2><div class="kv">
      <b>Resolve</b><span>${esc(s.resolve.state)}${s.resolve.checked ? ` <span class="dim small">(checked ${esc(s.resolve.checked)})</span>` : ''}</span>
      <b>Disk</b><span>${bytes(s.free_bytes)} free of ${bytes(s.total_bytes)} · <a href="#/storage">storage</a></span>
      <b>Jobs</b><span>${s.jobs_running.length ? s.jobs_running.map(j => `<a href="#/jobs/${j.id}">${esc(j.title)}</a>`).join(', ') : 'none running'}</span>
      <b>Your videos</b><span>${s.projects_list.map(p => `<a href="#/project/${encodeURIComponent(p.name)}">${esc(p.name)}</a>`).join(', ') || '–'}</span></div>
      <h3>Good to know</h3><div class="small muted">Buttons with <svg class="i"><use href="#i-claude"/></svg> open Claude Code in a new window with the request
      already written. Use one window per task and close it when it is done.</div>
      <div class="row" style="margin-top:8px"><button class="btn sm" data-tips>Tips for working with Claude</button></div></div>`;
  $('#an').onclick = () => analyseModal();
  wireFlowHow(main);
  wireUpdateBox(main, s.update_result);
  const rm = $('.roadmap img', main); if (rm) rm.onclick = () => lightbox([{src: s.roadmap, cap: 'MotionLab roadmap'}], 0);
  api('/api/knowledge').then(K => {
    const n = $('#kn-n', main), l = $('#kn-l', main); if (!n) return;
    const fr = K.cards.filter(c => c.origin === 'shared').length;
    n.textContent = K.cards.length;
    l.textContent = 'reference cards' + (fr ? ` · ${fr} from friends` : '');
  }).catch(() => {});
}

// ---- updates: the sidebar's Update button, its dialog (the CHANGELOG sections newer than this copy), "What's new"
function plural(n, w) { return `${n} ${w}${n === 1 ? '' : 's'}`; }
// updates come from GitHub's "tested" branch: newer pushes wait until the automatic tests pass (updater.check)
function testingText(u) { return u && u.testing ? ` · ${plural(u.testing, 'newer change')} waiting for GitHub's tests` : ''; }
function knowledgeText(cards, lessons) {             // "2 reference cards and 1 lesson"
  return [cards ? plural(cards, 'reference card') : '', lessons ? plural(lessons, 'lesson') : ''].filter(Boolean).join(' and ');
}
function sideUpdate(p) {                             // from the heartbeat: show / label the sidebar buttons
  const kn = p.update_kind === 'knowledge';
  const what = kn ? (knowledgeText(p.update_cards || 0, p.update_lessons || 0) || 'shared knowledge')
    : p.update_kind === 'version' && p.update_version ? 'MotionLab ' + p.update_version : 'changes on GitHub';
  const b = $('#side-update');
  if (b) {
    b.hidden = !p.update;
    if (p.update) { b.classList.toggle('kn', kn); $('b', b).textContent = kn ? 'New from friends' : 'Update available'; $('small', b).textContent = what; }
  }
  const c = $('#side-check');                        // bottom left: always there - check now, or install what was found
  if (!c || c.dataset.busy) return;
  c.classList.toggle('avail', !!p.update);
  $('b', c).textContent = p.update ? (kn ? 'New from friends' : 'Update available') : 'Check for updates';
  const hm = String(p.update_checked || '').slice(11, 16);
  $('small', c).textContent = p.update ? what : p.update_error ? "can't check - click for why"
    : hm ? `up to date · ${hm}${p.update_testing ? ` · ${p.update_testing} in tests` : ''}` : '';
  c.title = p.update ? 'See what changed and install it'
    : (p.update_error ? "Can't check: " + p.update_error + '\n\n' : '') + 'Ask GitHub for a newer MotionLab (or new knowledge from your friends) and install it'
      + (p.update_testing ? `\n${plural(p.update_testing, 'newer change')} still being tested on GitHub - offered when the tests pass` : '');
}
async function checkUpdates() {                      // the sidebar's Check for updates: ask GitHub now, then offer it
  const c = $('#side-check');
  if (c.classList.contains('avail')) { updateModal(); return; }
  if (c.dataset.busy) return;
  c.dataset.busy = '1'; c.disabled = true;
  $('b', c).textContent = 'Checking…'; $('small', c).textContent = 'asking GitHub';
  let u = null;
  try { u = await api('/api/update/check', {}); }
  catch (e) { toast(e.message, 'err'); }
  delete c.dataset.busy; c.disabled = false;
  await ping();
  if (!u) return;
  if (u.error) toast("Can't check for updates: " + u.error, 'err');
  else if (u.restart_needed) banner('restart', `MotionLab ${esc(u.disk_version || '')} is installed - restart to use it. <button class="btn sm pri">Restart now</button>`, restartApp);
  else if (u.can_update) updateModal();
  else toast(`MotionLab ${u.version} is up to date` + (u.testing ? ` - ${plural(u.testing, 'newer change')} still being tested on GitHub` : ''), 'ok');
}
// update banner (home + settings): new version on GitHub, or the result of the last update
function updateBox(u, res) {
  u = u || {};
  if (res && res.updated) return `<div class="panel upd ok"><div class="row sp"><div><b>${res.code_changed === false ? "Friends' knowledge added" : 'Updated to MotionLab ' + esc(res.version || '')}</b> <span class="small muted">(${esc(res.from)} → ${esc(res.to)}, ${(res.changed || []).length} files${res.pip ? ', Python packages updated' : ''})</span></div>
    ${res.whats_new ? '<button class="btn sm" data-shownew>What\'s new</button>' : ''}</div>
    ${res.set_aside && res.set_aside.length ? `<div class="small">Your own changes to <b>${esc(res.set_aside.join(', '))}</b> clashed with the update: the file now has the new version and your changes are kept in git (<code>git stash list</code>) - ask Claude to bring them back if you still need them.</div>` : ''}</div>`;
  if (u.restart_needed) return `<div class="panel upd"><div class="row sp"><b>MotionLab ${esc(u.disk_version || '')} is installed - restart to use it</b><button class="btn sm pri" data-restart>Restart now</button></div></div>`;
  if (!u.can_update) return '';
  const kn = u.kind === 'knowledge';
  return `<div class="panel upd"><div class="row sp"><div><b>${kn ? `New from friends: ${esc(knowledgeText(u.new_cards || 0, u.new_lessons || 0) || 'shared knowledge')}`
      : u.kind === 'version' ? `MotionLab ${esc(u.new_version)} is available` : 'Updates are available'}</b> <span class="small muted">· ${plural(u.behind, 'change')} on GitHub</span>
    ${u.dirty && u.dirty.length ? `<div class="small muted">Your changed files are kept: ${esc(u.dirty.slice(0, 4).join(', '))}${u.dirty.length > 4 ? ' …' : ''}</div>` : ''}</div>
    <div class="row"><button class="btn sm" data-whatsnew>What's new</button><button class="btn sm pri" data-update>${kn ? 'Get it now' : 'Update now'}</button></div></div></div>`;
}
function wireUpdateBox(el, res) {
  const w = $('[data-whatsnew]', el); if (w) w.onclick = () => updateModal();
  const u = $('[data-update]', el); if (u) u.onclick = updateNow;
  const rs = $('[data-restart]', el); if (rs) rs.onclick = restartApp;
  const sn = $('[data-shownew]', el); if (sn && res) sn.onclick = () => whatsNewModal(res);
}
async function updateModal() {
  let u;
  try { u = await api('/api/update'); } catch (e) { toast(e.message, 'err'); return; }
  if (!u.can_update) { toast(u.error || 'MotionLab is up to date', u.error ? 'err' : 'ok'); return; }
  const kn = u.kind === 'knowledge', jobs = +($('#jobcount').textContent || 0);
  const list = (u.changes || []).map(c => `<li>${esc(c)}</li>`).join('');
  modal(`<h2>${kn ? 'New knowledge from your friends' : u.kind === 'version' ? `MotionLab ${esc(u.new_version)} is available` : 'Updates are available'}</h2>
    <div class="small muted">You have MotionLab ${esc(u.version)} · ${plural(u.behind, 'change')} on GitHub${u.checked ? ' · checked ' + esc(u.checked) : ''}${testingText(u)}</div>
    <div class="whatsnew">${kn ? `<p><b>${esc(knowledgeText(u.new_cards || 0, u.new_lessons || 0) || 'Shared knowledge')}</b> - what your friends analysed and
      learned (pacing, effects, their verdicts); lessons wait for a review before they change anything. No restart needed.</p><ul class="small">${list}</ul>`
      : u.whats_new ? `<div class="md">${md(u.whats_new)}</div>` : `<ul class="small">${list}</ul>`}</div>
    ${u.dirty && u.dirty.length ? `<div class="small muted" style="margin-top:10px">Files you changed in this copy are kept: ${esc(u.dirty.slice(0, 4).join(', '))}${u.dirty.length > 4 ? ' …' : ''}</div>` : ''}
    <div class="small muted" style="margin-top:10px">${kn ? 'Only shared knowledge comes in.' : 'MotionLab restarts by itself (about 10 seconds).'} Your videos, analyses, verdicts, settings and knowledge are not touched.</div>
    ${jobs ? '<div class="small amber" style="margin-top:6px">A job is running - update when it has finished (Jobs).</div>' : ''}
    <div class="row" style="margin-top:14px;justify-content:flex-end"><button class="btn" data-later>Later</button><button class="btn pri" data-go ${jobs ? 'disabled' : ''}>${kn ? 'Get it now' : 'Update now'}</button></div>`,
  el => { $('[data-later]', el).onclick = closeModal; $('[data-go]', el).onclick = () => { closeModal(); updateNow(); }; });
}
function whatsNewModal(res) {                        // after an update (the window reloaded) or knowledge that came in
  const kn = res.code_changed === false;
  modal(`<h2>${kn ? "Friends' knowledge added" : `Updated to MotionLab ${esc(res.version || '')}`}</h2>
    <div class="small muted">${!kn && res.from_version ? `from ${esc(res.from_version)} · ` : ''}${plural((res.changed || []).length, 'file')}${res.pip === 'ok' ? ' · Python packages updated' : ''}</div>
    ${res.pip && res.pip !== 'ok' ? `<div class="small bad" style="margin-top:8px">Installing the new Python packages failed - run setup.bat again: ${esc(res.pip)}</div>` : ''}
    ${res.set_aside && res.set_aside.length ? `<div class="small" style="margin-top:8px">Your own changes to <b>${esc(res.set_aside.join(', '))}</b> clashed with the update: the file now has the new version and your changes are kept in git (<code>git stash list</code>) - ask Claude to bring them back if you still need them.</div>` : ''}
    <div class="whatsnew">${res.whats_new ? `<div class="md">${md(res.whats_new)}</div>`
      : kn ? `<p>${esc(knowledgeText(res.new_cards || 0, res.new_lessons || 0) || 'Shared knowledge')} from your friends: the Knowledge page shows them, and Claude reads them in your next analysis.</p>`
      : '<p class="muted">The changelog has no notes for this update.</p>'}</div>
    <div class="row" style="margin-top:14px;justify-content:flex-end"><button class="btn pri" data-ok>Got it</button></div>`,
  el => { $('[data-ok]', el).onclick = closeModal; });
  api('/api/update/seen', {}).catch(() => {});
}
// the sidebar's What's new: every version in CHANGELOG.md as a timeline (newest first; yours marked; a newer one on
// GitHub on top with its Update button), and above it the planned versions from docs/plans.md. Old ones are folded.
function changelogSections(text) {
  const out = [], re = /^## +(\d+(?:\.\d+){1,3})\b(.*)$/gm, heads = [...String(text || '').replace(/\r/g, '').matchAll(re)];
  heads.forEach((m, i) => {
    const rest = m[2].replace(/^\s*-\s*/, '').split(/\s+-\s+/);
    out.push({version: m[1], date: rest.length > 1 ? rest[0] : '', title: rest.length > 1 ? rest.slice(1).join(' - ') : rest[0],
              body: m.input.slice(m.index + m[0].length, i + 1 < heads.length ? heads[i + 1].index : undefined).trim()});
  });
  return out;
}
async function newsModal() {
  let local = [], u = {}, plans = [];
  try { local = changelogSections((await api('/api/text?path=CHANGELOG.md')).text); } catch (e) { toast(e.message, 'err'); return; }
  try { plans = changelogSections((await api('/api/text?path=docs/plans.md')).text).map(s => ({...s, date: ''})); } catch (e) { /* no plans file */ }
  try { u = await api('/api/update'); } catch (e) { /* offline: the local history is enough */ }
  const have = new Set(local.map(s => s.version));
  const upcoming = u.can_update && u.kind === 'version' ? changelogSections(u.whats_new).filter(s => !have.has(s.version)) : [];
  const item = (s, cls, open, badge) => `<details class="tl-item ${cls}" ${open ? 'open' : ''}><summary><span class="tl-ver">${esc(s.version)}</span>
      ${s.date ? `<span class="tl-date">${esc(s.date)}</span>` : ''}<span class="tl-title">${esc(s.title)}</span>${badge ? `<span class="tl-badge">${badge}</span>` : ''}</summary>
      <div class="md small">${md(s.body)}</div></details>`;
  modal(`<div class="row sp"><h2 style="margin:0">What's new in MotionLab</h2><span class="small muted">you have ${esc(PAGE_VERSION)}</span></div>
    <div class="tline">${plans.length ? '<div class="tl-sec">Planned</div>' + plans.map(s => item(s, 'plan', false, 'planned')).join('') + '<div class="tl-sec">Released</div>' : ''}
      ${upcoming.map(s => item(s, 'new', true, 'on GitHub - not installed yet')).join('')}
      ${local.map((s, i) => item(s, s.version === PAGE_VERSION ? 'cur' : '', i === 0 && !upcoming.length || s.version === PAGE_VERSION,
                                 s.version === PAGE_VERSION ? 'your version' : '')).join('')}</div>
    <div class="row" style="justify-content:flex-end;margin-top:10px">${upcoming.length ? '<button class="btn pri" data-up>Update now</button>' : ''}<button class="btn" data-close>Close</button></div>`,
  el => { $('[data-close]', el).onclick = closeModal; const b = $('[data-up]', el); if (b) b.onclick = () => { closeModal(); updateNow(); }; });
}
async function updateNow() {
  overlay('Updating MotionLab from GitHub…');
  try {
    const r = await api('/api/update/apply', {});
    if (r.updated && r.restart !== false) { RELOADING = false; waitForServer('Restarting MotionLab with the new version…'); }
    else if (r.updated) { $('#overlay').hidden = true; route(); ping(); whatsNewModal(r); }
    else { $('#overlay').hidden = true; toast('Already up to date', 'ok'); route(); ping(); }
  } catch (e) { $('#overlay').hidden = true; toast(e.message, 'err'); }
}

async function analyseModal(prefill = '') {
  const [c, ST] = await Promise.all([api('/api/candidates'), api('/api/settings')]);
  const cl = ST.tools.find(t => t.name === 'claude') || {};
  const eff = ST.settings.claude_effort === 'auto' ? ST.tasks.review : ST.settings.claude_effort;
  modal(`<h2>Analyse a video</h2>
    <p class="hint">Your video is only read, never changed. Pick one below or paste the full path of a video file.</p>
    ${c.length ? `<table class="t click" style="margin-bottom:10px"><thead><tr><th>Your downloaded videos</th><th class="num">Size</th><th></th></tr></thead><tbody>
      ${c.map(v => `<tr data-p="${esc(v.path)}" class="${v.path === prefill ? 'sel' : ''}"><td>${esc(v.name)}</td><td class="num">${bytes(v.size)}</td><td>${v.analysed ? '<span class="tag done">analysed</span>' : '<span class="tag">new</span>'}</td></tr>`).join('')}</tbody></table>` : ''}
    <input type="text" id="vpath" placeholder="C:\\path\\to\\video.mp4">
    <div class="form" style="margin-top:10px"><label for="vcat">Category</label>
      <select id="vcat">${ST.categories.map(o => `<option value="${o.id}" ${o.id === ST.settings.default_category ? 'selected' : ''}>${esc(o.label)}</option>`).join('')}</select>
      <label for="vtags">Tags (optional)</label><input type="text" id="vtags" placeholder="e.g. instagram, asmr, recipe">
      <span></span><span class="small dim">Pacing, effects and lessons are kept per category, so cooking shorts don't change how music videos are judged.</span></div>
    <div class="choice">
      <div><button class="btn pri big" id="goc" ${cl.found ? '' : 'disabled'}><svg class="i"><use href="#i-claude"/></svg>Analyse with Claude</button>
        <div class="small">Recommended. MotionLab measures the video (about 1–2 minutes per minute of video), then <b>Claude Code opens by
          itself</b> and names every effect. After that you give your verdicts.
          ${cl.found ? '' : '<div class="bad">Claude Code was not found - <a href="#/settings" onclick="closeModal()">Settings</a>.</div>'}</div></div>
      <div><button class="btn" id="go">Measure only</button>
        <div class="small muted">No Claude for now: the effect names stay guesses until you send it to Claude from the video's page.</div></div></div>
    <label class="chk small" style="margin-top:8px"><input type="checkbox" id="redet"> re-use the earlier measurements (faster)</label>`, el => {
    const inp = $('#vpath', el);
    if (prefill) inp.value = prefill;
    $$('tr[data-p]', el).forEach(r => r.onclick = () => { inp.value = r.dataset.p; $$('tr[data-p]', el).forEach(x => x.classList.toggle('sel', x === r)); });
    const go = async claude => {
      if (!inp.value.trim()) { toast('Pick or paste a video first', 'err'); return; }
      const j = await startJob('analyze', {video: inp.value.trim(), redetect: $('#redet', el).checked, category: $('#vcat', el).value,
                                           tags: $('#vtags', el).value, claude});
      if (!j) return;
      closeModal();
      if (claude) toast('Measuring the video. Claude Code opens by itself when it is done.', 'ok');
    };
    $('#goc', el).onclick = () => go(true);
    $('#go', el).onclick = () => go(false);
  });
}

// ============================================================================================ the workflow of a reference
const FLOW = [
  ['download', 'Download', 'Paste a link to a video you like (YouTube, TikTok, Instagram…)'],
  ['lab', 'Measure', 'MotionLab finds every cut, effect and beat - about 1–2 minutes per minute of video'],
  ['claude', 'Claude checks', 'Claude looks at every effect and names it'],
  ['verdicts', 'Your verdicts', 'You mark each effect Correct, Partly or Wrong'],
  ['feedback', 'Feedback', 'Claude learns from your verdicts for the next video'],
  ['share', 'Share', 'Your friends get what you learned'],
];
const flowHow = () => `<div class="flow how">${FLOW.map(([k, t, d], i) => `<button class="fstep" data-step="${k}"><b>${i + 1}</b><div><div class="ft">${t}</div><div class="fd">${esc(d)}</div></div></button>`).join('')}</div>`;
function wireFlowHow(el) {
  $$('.flow.how [data-step]', el).forEach(b => b.onclick = () => {
    const k = b.dataset.step;
    if (k === 'download') downloadModal(); else if (k === 'lab') analyseModal();
    else location.hash = k === 'share' ? '#/knowledge' : '#/refs';
  });
}
const flowDots = fl => `<span class="fdots" title="${esc(FLOW.map(([k, t], i) => `${i + 1} ${t}${fl.done.includes(k) ? ' ✓' : ''}`).join(' · '))}">${FLOW.map(([k]) => `<i class="${fl.done.includes(k) ? 'd' : k === fl.next ? 'n' : ''}"></i>`).join('')}</span>`;
function flowNext(fl) {
  const left = fl.events - fl.reviewed, open = fl.misses - fl.misses_checked;
  switch (fl.next) {
    case 'claude': return `Next: send it to Claude - ${left} effect${left === 1 ? '' : 's'} not checked yet`;
    case 'verdicts': return fl.given >= fl.real && open ? `Next: check ${open} possible miss${open === 1 ? '' : 'es'}`
      : `Next: your verdicts - ${fl.given} / ${fl.real} effects` + (fl.misses ? `, ${fl.misses_checked} / ${fl.misses} possible misses` : '');
    case 'feedback': return fl.sent ? 'Next: your feedback is exported - let Claude apply it' : 'Next: send your feedback to Claude';
    case 'share': return 'Next: share what you learned (Knowledge)';
    default: return 'All steps done ✓';
  }
}
function flowAction(r, fl, onPage = false) {         // the button for a reference's next step
  const sz = onPage ? '' : 'sm', open = fl.misses - fl.misses_checked;
  switch (fl.next) {
    case 'claude': return claudeBtn(r.review_prompt, 'Send to Claude', 'review', r.title, `${sz} pri`);
    case 'verdicts':
      if (fl.given >= fl.real && open) return onPage ? `<button class="btn ${sz} missbtn" data-tabgo="misses">Check the possible misses</button>`
        : `<a class="btn ${sz} missbtn" href="#/ref/${encodeURIComponent(r.name)}?misses">Check ${open} possible miss${open === 1 ? '' : 'es'}</a>`;
      return onPage ? `<button class="btn ${sz}" data-tabgo="review">Give your verdicts ↓</button>` : `<a class="btn ${sz}" href="#/ref/${encodeURIComponent(r.name)}">Give your verdicts</a>`;
    case 'feedback': return `<button class="btn ${sz} pri" data-feedback="${esc(r.name)}"><svg class="i"><use href="#i-claude"/></svg>Send feedback to Claude</button>`;
    case 'share': return `<a class="btn ${sz}" href="#/knowledge">Share my knowledge</a>`;
    default: return '';
  }
}
function flowStrip(r, fl) {                           // the reference page: the six steps, this video's state, the next one
  return `<div class="flow strip">${FLOW.map(([k, t, d], i) => `<div class="fstep ${fl.done.includes(k) ? 'done' : k === fl.next ? 'next' : ''}" title="${esc(d)}"><b>${fl.done.includes(k) ? '✓' : i + 1}</b><span class="ft">${t}</span></div>`).join('<i class="farr">›</i>')}
    <div class="grow"></div><div class="fnext"><span class="small">${esc(flowNext(fl))}</span>${flowAction(r, fl, true)}</div></div>`;
}

async function feedbackModal(name) {
  try {
    const r = await api(`/api/reference/${encodeURIComponent(name)}/export`, {});
    const say = `Apply the MOTIONLAB FEEDBACK in ${r.path}`;
    modal(`<h2>Feedback for Claude</h2>
      <p class="hint">Saved to <span class="mono">${esc(r.path)}</span>. The button opens Claude Code with the request
      <span class="mono">${esc(say)}</span>. Claude then turns it into lessons and threshold changes, re-checks the effects
      you marked wrong or partly (and the possible misses you called an effect), runs the self-test and tells you what changed.</p>
      <textarea rows="12" readonly class="mono">${esc(r.text)}</textarea>
      <div class="row" style="margin-top:10px">${claudeBtn(say, 'Open in Claude Code (applies it)', 'feedback', name, 'pri')}<button class="btn" id="c1">Copy the feedback text</button><button class="btn" id="c2">Copy the short sentence</button></div>`, el => {
      $('#c1', el).onclick = () => copy(r.text); $('#c2', el).onclick = () => copy(say);
    });
  } catch (e) { toast(e.message, 'err'); }
}

async function tipsModal() {
  let t = '';
  try { t = (await api('/api/text?path=' + encodeURIComponent('docs/claude_tips.md'))).text; } catch (e) { t = '# Tips\n\n' + e.message; }
  modal(`<div class="md">${md(t)}</div>`);
}

// ============================================================================================ delete (Recycle Bin)
async function deleteModal(kind, name, onDone) {
  let P;
  try { P = await api(`/api/delete?kind=${kind}&name=${encodeURIComponent(name)}`); } catch (e) { toast(e.message, 'err'); return; }
  const one = P.items.length === 1;
  modal(`<h2>Delete ${esc(P.title)}?</h2>
    <p class="hint">Everything ticked goes to the Windows <b>Recycle Bin</b> - you can restore it from there until you empty the bin.</p>
    <div class="col delitems">${P.items.map(i => `<label class="delitem ${i.warn.length ? 'warn' : ''}"><input type="checkbox" value="${i.key}" ${i.default || one ? 'checked' : ''} ${one ? 'disabled' : ''}>
      <div><b>${esc(i.label)}</b> · ${bytes(i.bytes)}${i.files > 1 ? ` · ${i.files} files` : ''} <div class="mono small dim">${esc(i.path)}</div>
        <div class="small muted">${esc(i.what)}</div>${i.warn.map(w => `<div class="small warnline">⚠ ${esc(w)}</div>`).join('')}</div></label>`).join('')}</div>
    ${P.notes.map(n => `<div class="small muted" style="margin-top:6px">${esc(n)}</div>`).join('')}
    ${P.keeps.length ? `<div class="small ok" style="margin-top:8px">Stays: ${P.keeps.map(esc).join('; ')}.</div>` : ''}
    ${P.big ? '<div class="small warnline" style="margin-top:6px">Very large: if it does not fit in the Recycle Bin, Windows asks before deleting it for good.</div>' : ''}
    <div class="row" style="margin-top:14px"><button class="btn del" id="delgo">Move to the Recycle Bin</button><button class="btn" id="delno">Cancel</button><span id="delst" class="small muted"></span></div>`, el => {
    $('#delno', el).onclick = closeModal;
    $('#delgo', el).onclick = async () => {
      const keys = $$('input[type=checkbox]', el).filter(x => x.checked).map(x => x.value);
      if (!keys.length) { toast('Tick what should go', 'err'); return; }
      $('#delgo', el).disabled = true; $('#delst', el).textContent = 'moving…';
      // a video this window plays keeps its file open: stop every player first
      $$('video').forEach(v => { try { v.pause(); v.removeAttribute('src'); v.load(); } catch (e) { /* ignore */ } });
      await new Promise(r => setTimeout(r, 400));
      try {
        const r = await api('/api/delete', {kind, name, keys});
        if (r.failed.length) {
          $('#delst', el).innerHTML = `<span class="bad">Not moved: ${r.failed.map(f => esc(f.path)).join(', ')} - ${esc(r.failed[0].why)}</span>`;
          $('#delgo', el).disabled = false; if (r.moved.length) toast(`Moved to the Recycle Bin: ${r.moved.join(', ')}`, 'ok');
          return;
        }
        closeModal(); toast(`Moved to the Recycle Bin (${bytes(r.bytes)}): ${r.moved.join(', ')}`, 'ok');
        if (onDone) onDone(r);
      } catch (e) { $('#delst', el).innerHTML = `<span class="bad">${esc(e.message)}</span>`; $('#delgo', el).disabled = false; }
    };
  });
}
document.addEventListener('click', e => {
  const d = e.target.closest('[data-del]');
  if (!d) return;
  e.preventDefault(); e.stopPropagation();
  const [kind, name, after] = [d.dataset.del, d.dataset.name, d.dataset.after];
  deleteModal(kind, name, () => { if (after && location.hash !== after) location.hash = after; else route(); });
});
const delBtn = (kind, name, after = '', label = '') => `<button class="btn sm ${label ? 'danger' : 'ghost icon'}" data-del="${kind}" data-name="${esc(name)}" data-after="${esc(after)}" title="Delete… (to the Recycle Bin)"><svg class="i"><use href="#i-trash"/></svg>${label}</button>`;

// ============================================================================================ videos (analyses)
async function pageRefs(main) {
  let tests = false, cat = '', tag = '';
  const draw = async () => {
    const [all, wait] = await Promise.all([api('/api/references' + (tests ? '?tests=1' : '')), api('/api/waiting').catch(() => [])]);
    const cats = [...new Map(all.filter(r => r.category).map(r => [r.category, r.category_label])).entries()];
    const tags = [...new Set(all.flatMap(r => r.tags || []))].sort();
    const refs = all.filter(r => (!cat || r.category === cat) && (!tag || (r.tags || []).includes(tag)));
    const pct = (a, b) => b ? Math.round(100 * a / b) : 100;
    const none = !all.length && !wait.length;
    const btns = big => `<button class="btn${big ? ' big' : ''}" id="dl"><svg class="i"><use href="#i-download"/></svg>Download from a link</button>
      <button class="btn pri${big ? ' big' : ''}" id="an">＋ Analyse a video</button>`;
    main.innerHTML = `<div class="head"><div><h1>References</h1><div class="sub">Videos by other creators, broken down cut by cut and effect by effect.</div></div>
      ${none ? '' : `<div class="row">${btns(false)}</div>`}</div>
      ${wait.length ? `<div class="panel waiting"><h2>Downloaded, not analysed yet</h2><table class="t"><tbody>${wait.map(w => `<tr>
        <td>${w.audio ? '<span class="tag">audio</span>' : '<span class="tag">video</span>'}</td><td><b>${esc(w.title || w.name)}</b><div class="small dim mono">${esc(w.name)}</div></td>
        <td class="small muted">${w.url ? `<a href="${esc(w.url)}" target="_blank" rel="noopener">${esc(w.platform || 'link')}</a> · ` : ''}${esc(w.modified)}</td><td class="num small">${bytes(w.size)}</td>
        <td class="row" style="justify-content:flex-end">${w.audio ? '<span class="small dim">for an edit (Videos)</span>' : `<button class="btn sm pri" data-an="${esc(w.path)}">Analyse…</button>`}${delBtn('file', w.rel, '', ' Delete')}</td></tr>`).join('')}</tbody></table></div>` : ''}
      ${all.length ? `<div class="row" style="margin:12px 0"><select id="fcat"><option value="">All categories (${all.length})</option>${cats.map(([k, l]) => `<option value="${k}" ${k === cat ? 'selected' : ''}>${esc(l)} (${all.filter(r => r.category === k).length})</option>`).join('')}</select>
        ${tags.length ? `<select id="ftag"><option value="">All tags</option>${tags.map(t => `<option ${t === tag ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select>` : ''}</div>` : ''}
      ${refs.length ? `<div class="cards">${refs.map(r => { const fl = r.flow; return `<div class="card refcard ${fl.next ? 'n-' + fl.next : 'n-done'}">
        <a class="clink" href="#/ref/${encodeURIComponent(r.name)}">
        ${r.thumb ? `<img class="thumb" src="${fileUrl(r.thumb)}" loading="lazy">` : ''}
        <div class="cb"><div class="ct">${esc(r.title)}</div>
        <div class="small muted">${tc((r.frames || 1) - 1, r.fps)} · ${r.fps} fps · ${r.width}×${r.height}${r.bpm ? ` · ${r.bpm.toFixed(1)} BPM` : ''} · analysed ${esc(r.generated || '')}</div>
        <div class="small">${r.category ? `<span class="tag">${esc(r.category_label)}</span> ` : ''}${(r.tags || []).map(t => `<span class="tag dim">${esc(t)}</span> `).join('')}<span class="muted">${esc((r.format || {}).label || '')}</span></div>
        <div class="small">${r.events} effects · ${r.cuts} hard cuts${r.pacing && r.pacing.cuts_per_min != null ? ` · <b>${r.pacing.cuts_per_min}</b> cuts/min · shots ${r.pacing.avg_shot_s} s` : ''}</div>
        <div class="small muted pgl"><span>Claude checked <b>${fl.reviewed} / ${fl.events}</b></span><span>your verdicts <b>${fl.given} / ${fl.real}</b>${fl.misses ? ` · misses <b class="${fl.misses_checked < fl.misses ? 'bad' : ''}">${fl.misses_checked} / ${fl.misses}</b>` : ''}</span></div>
        <div class="bar duo"><i style="width:${pct(fl.reviewed, fl.events)}%;background:#4fb3ff"></i><i style="width:${pct(fl.given, fl.real)}%"></i></div>
        <div class="small fnl">${flowDots(fl)} <span class="${fl.next ? '' : 'ok'}">${esc(flowNext(fl))}</span></div>
        </div></a>
        <div class="cact">${flowAction(r, fl)}<div class="grow"></div>${delBtn('reference', r.name)}</div></div>`; }).join('')}</div>`
        : none ? emptyHero('refs', 'Learn from a video you like', 'Download it from a link or pick a video file - MotionLab finds every cut and effect, and Claude names them.', btns(true))
        : '<div class="empty">No reference in this category.</div>'}
      <label class="chk small dim" style="margin-top:18px"><input type="checkbox" id="tests" ${tests ? 'checked' : ''}> show the test videos</label>`;
    $('#an').onclick = () => analyseModal();
    $('#dl').onclick = downloadModal;
    $('#tests').onchange = e => { tests = e.target.checked; draw(); };
    $$('[data-an]', main).forEach(b => b.onclick = () => analyseModal(b.dataset.an));
    const fc = $('#fcat', main); if (fc) fc.onchange = e => { cat = e.target.value; draw(); };
    const ft = $('#ftag', main); if (ft) ft.onchange = e => { tag = e.target.value; draw(); };
  };
  await draw();
}

async function pageRef(main, name, selId, openMisses) {
  const R = await api('/api/reference/' + encodeURIComponent(name));
  const fps = R.video.fps, N = R.video.frames, evs = R.events, NM = R.near_misses || [];
  const byId = Object.fromEntries(evs.map(e => [e.id, e]));
  const S = {events: R.verdicts.events || {}, cuts: R.verdicts.cuts || {}, misses: R.verdicts.misses || {}, missed: R.verdicts.missed || ''};
  const vOf = id => (S.events[id] || {}).v || '';
  const mOf = f => (S.misses[String(f)] || {}).v || '';
  let cur = byId[selId] || evs.find(e => !e.false_alarm && !vOf(e.id)) || evs.find(e => !e.false_alarm) || evs[0];
  const fams = [...new Set(evs.map(e => e.family))].sort();
  const nfa = evs.filter(e => e.false_alarm).length;
  const pref = (k, d) => { try { const v = localStorage.getItem('ml.' + k); return v === null ? d : v; } catch (e) { return d; } };
  const setPref = (k, v) => { try { localStorage.setItem('ml.' + k, v); } catch (e) { /* private window */ } };
  let autoNext = pref('autoNext', '1') === '1', sound = pref('previewSound', '0') === '1', rate = +pref('previewRate', '1') || 1;
  let shown = evs, tab = openMisses && NM.length ? 'misses' : 'review';
  main.innerHTML = `
  <div class="head"><div><div class="crumb"><a href="#/refs">References</a> / analysis</div><h1>${esc(R.title)}</h1>
    <div class="sub"><span class="tag">${esc(R.category_label)}</span> ${(R.tags || []).map(t => `<span class="tag dim">${esc(t)}</span> `).join('')}<a href="#" id="editmeta" class="small">edit</a>
      ${R.url ? ` · <a href="${esc(R.url)}" target="_blank" rel="noopener">${esc(R.platform || 'source')}</a>` : ''} · ${R.video.width}×${R.video.height} · ${fps} fps · ${N} frames (f0–${N - 1}, 00:00:00:00 – ${R.video.end_tc})${R.audio.bpm ? ` · ${R.audio.bpm.toFixed(1)} BPM` : ''}
      · ${evs.length} effects, ${R.cuts.length} hard cuts · analysed ${esc(R.generated || '')}${R.source_unchanged ? ' · source unchanged ✓' : ''}</div>
    ${R.pacing ? `<div class="small pacing">Pacing: <b>${R.pacing.cuts_per_min ?? '–'}</b> cuts/min · shots avg <b>${R.pacing.avg_shot_s ?? '–'} s</b> (median ${R.pacing.median_shot_s ?? '–'} s) · <b>${R.pacing.hook_cuts_3s}</b> cut(s) in the first 3 s · <b>${R.pacing.effects_per_min ?? '–'}</b> effects/min${R.pacing.cuts_on_beat_pct != null ? ` · ${R.pacing.cuts_on_beat_pct} % of plain cuts on the beat` : ''}</div>` : ''}</div>
    <div class="row"><button class="btn cl" id="recreate" title="Claude rebuilds this edit with your own clips"><svg class="i"><use href="#i-claude"/></svg>Recreate with my footage…</button>
      ${R.report ? `<button class="btn" data-open="${esc(R.report)}">Open full report</button>` : ''}
      <button class="btn" data-open="${esc('analysis/' + R.name)}">Folder</button>${delBtn('reference', R.name, '#/refs', ' Delete…')}</div></div>
  <div id="flow">${flowStrip(R, R.flow)}</div>
  <div class="watch">
    <div id="player"></div>
    <div class="tl" id="tl1"><canvas height="100"></canvas></div>
    <div class="tl" id="tl2"><canvas height="84"></canvas></div>
    <div class="hint legend">Top: the whole video · below: 60 frames each side of the playhead (red line) · bars = effects (colour = type, line under = your verdict) ·
      white line = hard cut · <b class="bad">red ▲</b> = possible miss · ▼ = music drop · ticks = beats (tall = bar start) ·
      keys: <span class="kbd">←</span><span class="kbd">→</span> frame, <span class="kbd">Shift</span> ten, <span class="kbd">Space</span> play,
      <span class="kbd">J</span><span class="kbd">K</span> previous / next effect, <span class="kbd">N</span> next without verdict, <span class="kbd">1</span><span class="kbd">2</span><span class="kbd">3</span> correct / partly / wrong</div>
  </div>
  <div class="rtabs" id="rtabs"><button class="rtab" data-tab="review">Review effects <span class="cnt" id="cnt-review"></span></button>
    ${NM.length ? '<button class="rtab misstab" data-tab="misses">Possible misses <span class="cnt" id="cnt-misses"></span></button>' : ''}
    <button class="rtab" data-tab="content" title="what the video says and how it performs">Content</button>
    <div class="grow"></div><span class="hint">Your verdicts are saved as you go <span id="saved"></span></span></div>
  <div class="review" id="tab-review">
    <div class="rlist">
      <div class="filters"><input type="search" id="q" placeholder="Search effects, notes…">
        <select id="ff"><option value="">All types</option>${fams.map(f => `<option>${esc(f)}</option>`).join('')}</select>
        <select id="fv"><option value="">All verdicts</option><option value="none">No verdict yet</option><option value="correct">Correct</option>
          <option value="partly">Partly</option><option value="wrong">Wrong</option><option value="relab">Renamed by Claude</option></select>
        ${nfa ? `<label class="chk small"><input type="checkbox" id="showfa"> show the ${nfa} false alarms</label>` : ''}</div>
      <div class="evlist"><table class="t click"><tbody id="rows"></tbody></table></div>
    </div>
    <div class="rcard panel" id="detail"></div>
  </div>
  ${NM.length ? `<div class="missarea" id="tab-misses" hidden>
    <div class="missintro"><b>Possible misses are not effects from the list.</b> They are sudden changes in the picture that no effect and no cut
      explains - places where the lab may have missed an effect. Most are nothing, but only you can say. For each one: look at the frames
      (before · at · after - click one to show it in the player), read Claude's check, then answer.</div>
    <div class="misses" id="misses"></div></div>` : ''}
  <div class="contentarea" id="tab-content" hidden></div>
  <div class="fbbar"><div class="prog"><div class="row sp small"><span id="progt"></span></div><div class="bar"><i id="progb"></i></div></div>
    <button class="btn" id="missedb">Missed effects / general notes</button>
    ${nfa ? '<button class="btn ghost" id="agreefa" title="optional: tells Claude its “not an effect” calls were right">Agree with all false alarms</button>' : ''}
    <div class="grow"></div><button class="btn pri" id="exp"><svg class="i"><use href="#i-claude"/></svg>Send feedback to Claude…</button></div>`;

  const P = R.video.play ? new Player($('#player'), R.video.play, fps, N) : null;
  if (!P) $('#player').innerHTML = '<div class="empty">The source video is not inside the lab folder, so it cannot be played here.</div>';
  const tlOpts = {verdict: vOf, missDone: f => !!mOf(f), onSelect: e => { showTab('review'); select(e, true); },
                  onSeek: f => P && P.seek(f), onMiss: m => { showTab('misses', true); focusMiss(m.frame); }};
  const T1 = new Timeline($('#tl1'), R, tlOpts);
  const T2 = new Timeline($('#tl2'), R, {...tlOpts, zoom: 60});
  if (P) P.on(f => { T1.setPlay(f); T2.setPlay(f); });

  const save = debounce(async () => {
    try { await api(`/api/reference/${encodeURIComponent(name)}/verdicts`, S); $('#saved').textContent = '✓'; refreshFlow(); }
    catch (e) { $('#saved').textContent = '- NOT saved!'; toast('Could not save: ' + e.message, 'err'); }
  }, 450);
  const refreshFlow = debounce(async () => {             // the step strip follows your verdicts
    try { const NR = await api('/api/reference/' + encodeURIComponent(name)); $('#flow').innerHTML = flowStrip(NR, NR.flow); } catch (e) { /* keep the old one */ }
  }, 1500);
  const changed = () => { $('#saved').textContent = '…'; save(); progress(); rows(); T1.draw(); T2.draw(); };
  const progress = () => {
    const real = evs.filter(e => !e.false_alarm), fas = evs.filter(e => e.false_alarm);
    const n = real.filter(e => vOf(e.id)).length, nf = fas.filter(e => vOf(e.id)).length, mc = NM.filter(m => mOf(m.frame)).length;
    $('#progt').textContent = `${n} / ${real.length} effects with your verdict` + (NM.length ? ` · possible misses ${mc} / ${NM.length}` : '')
      + (fas.length ? ` · false alarms ${nf} / ${fas.length} (optional)` : '');
    $('#progb').style.width = (100 * (n + mc) / Math.max(1, real.length + NM.length)) + '%';
    const cr = $('#cnt-review'); cr.textContent = n >= real.length ? 'all done ✓' : `${real.length - n} left`; cr.classList.toggle('ok', n >= real.length);
    const cm = $('#cnt-misses');
    if (cm) { cm.textContent = mc >= NM.length ? 'all answered ✓' : `${NM.length - mc} to check`; cm.closest('.rtab').classList.toggle('open', mc < NM.length); }
  };
  const rows = () => {
    const q = $('#q').value.toLowerCase(), ff = $('#ff').value, fv = $('#fv').value, fa = $('#showfa') && $('#showfa').checked;
    const list = evs.filter(e => (fa || !e.false_alarm || e.id === cur.id) && (!ff || e.family === ff)
      && (!fv || e.id === cur.id || (fv === 'none' ? !vOf(e.id) : fv === 'relab' ? e.relabelled : vOf(e.id) === fv))
      && (!q || (e.id + ' ' + e.label + ' ' + e.what + ' ' + ((S.events[e.id] || {}).note || '')).toLowerCase().includes(q)));
    shown = list.length ? list : evs;
    $('#rows').innerHTML = list.map(e => `<tr data-id="${e.id}" class="${e.id === cur.id ? 'sel' : ''} ${e.false_alarm ? 'fa' : ''}">
      <td><span class="vdot ${vOf(e.id)}"></span></td><td class="mono amber">${e.id}</td>
      <td><i class="sw" style="background:${FAM[e.family] || '#888'}"></i>${esc(e.label)}${e.relabelled ? ' <span class="relab" title="renamed by Claude">✎</span>' : ''}${(S.events[e.id] || {}).library ? ' <span class="amber" title="wanted in the library">★</span>' : ''}
        ${(S.events[e.id] || {}).note ? `<div class="small muted">${esc(S.events[e.id].note.slice(0, 70))}</div>` : ''}</td>
      <td class="fr small">f${e.start}${e.end !== e.start ? '–' + e.end : ''}</td></tr>`).join('')
      || '<tr><td colspan="4" class="muted">No effect matches.</td></tr>';
    $$('#rows tr[data-id]').forEach(tr => tr.onclick = () => select(byId[tr.dataset.id], true));
  };
  const detail = () => {
    const e = cur, st = S.events[e.id] || {}, n = e.end - e.start + 1, i = shown.indexOf(e);
    const el = $('#detail');
    el.innerHTML = `<div class="rbody"><div class="rhead"><div class="evhead"><span class="id">${e.id}</span><span class="ty">${esc(e.label)}</span>${chip(e.family)}</div>
        <span class="small muted">${i >= 0 ? `${i + 1} of ${shown.length}` : ''}</span></div>
      ${e.relabelled ? `<div class="relab">first guess <s>${esc(e.auto_label)}</s> · renamed by Claude</div>` : ''}
      ${!e.reviewed ? '<div class="small warnline">Not checked by Claude yet: the name is a guess.</div>' : ''}
      ${e.false_alarm ? '<div class="bad small">a false alarm (not an edit effect) - a verdict is optional</div>' : ''}
      ${e.preview ? `<div class="pvbox"><video class="pv" src="${fileUrl(e.preview)}" autoplay loop playsinline ${sound ? '' : 'muted'}></video>
        <div class="pvbar"><span class="small muted">loop ${e.preview_range ? `f${e.preview_range[0]}–${e.preview_range[1]}` : ''} · frame + timecode in the picture</span><div class="grow"></div>
          ${[0.25, 0.5, 1].map(r => `<button class="btn sm rate ${r === rate ? 'on' : ''}" data-pr="${r}">${r === 1 ? '1×' : r === 0.5 ? '½' : '¼'}</button>`).join('')}
          <label class="chk small"><input type="checkbox" id="pvsnd" ${sound ? 'checked' : ''}> sound</label>
          <button class="btn sm" id="inbig" title="play it in the big player above">▶ big player</button></div></div>` : ''}
      <div class="kv" style="margin-top:8px"><b>Frames</b><span>${frange(e.start, e.end, fps)}</span><b>Length</b><span>${n} frame${n > 1 ? 's' : ''} (${(n / fps).toFixed(2)} s)</span></div>
      <h3>What happens</h3><div class="what">${linkify(e.what)}</div>
      ${e.evidence.length ? `<h3>Measured evidence</h3><ul class="small" style="margin:0;padding-left:18px;color:#c9c9d0">${e.evidence.map(x => `<li>${linkify(x)}</li>`).join('')}</ul>` : ''}
      <details class="fold"><summary>In depth: timing, easing, origin and how to rebuild it</summary><div class="in"><div class="kv">
        ${e.timing ? `<b>Timing</b><span>${esc(e.timing)}</span>` : ''}${e.easing ? `<b>Easing</b><span>${esc(e.easing)}</span>` : ''}
        ${e.origin ? `<b>Made</b><span>${esc(e.origin)}</span>` : ''}${e.confidence ? `<b>Confidence</b><span>${esc(e.confidence)}</span>` : ''}
        ${e.stacked && e.stacked.length ? `<b>Also</b><span>${esc(e.stacked.join(', '))}</span>` : ''}</div>
        ${e.rebuild ? `<h3>How to rebuild it in Resolve</h3><div class="what">${linkify(e.rebuild)}</div>` : ''}</div></details>
      <details class="fold"><summary>Frame list (${e.sheets.length} contact sheet${e.sheets.length === 1 ? '' : 's'})</summary><div class="in">
        <div class="sheets" style="margin-top:8px">${e.sheets.map((s, k) => `<img src="${fileUrl(s)}" data-i="${k}" loading="lazy" alt="">`).join('')}</div></div></details></div>
      <div class="ractions"><div class="verdicts">${['correct', 'partly', 'wrong'].map((v, k) => `<button class="btn vb ${st.v === v ? 'on' : ''}" data-v="${v}" title="key ${k + 1}">
          ${['✓ Correct', '~ Partly', '✗ Wrong'][k]} <span class="kbd">${k + 1}</span></button>`).join('')}</div>
        <textarea id="note" rows="2" placeholder="${st.v === 'partly' || st.v === 'wrong' ? 'What is wrong? e.g. “it\'s a zoom, not a flash; it starts at f340” - then K or Ctrl+Enter for the next effect' : 'Note (optional): what is right or wrong?'}">${esc(st.note || '')}</textarea>
        <div class="row nav"><button class="btn" id="pv">◀ Previous <span class="kbd">J</span></button><button class="btn" id="nx">Next ▶ <span class="kbd">K</span></button>
          <button class="btn ghost" id="nopen">Next without a verdict <span class="kbd">N</span></button><div class="grow"></div>
          <div class="col" style="gap:2px"><label class="chk small"><input type="checkbox" id="lib" ${st.library ? 'checked' : ''}> I want this effect in my library</label>
          <label class="chk small" title="after Partly / Wrong you write a note first"><input type="checkbox" id="auto" ${autoNext ? 'checked' : ''}> after “Correct”, go to the next effect</label></div></div></div>`;
    const pv = $('.pv', el);
    if (pv) {
      pv.playbackRate = rate; pv.addEventListener('loadedmetadata', () => { pv.playbackRate = rate; });
      $$('[data-pr]', el).forEach(b => b.onclick = () => { rate = +b.dataset.pr; setPref('previewRate', rate); pv.playbackRate = rate; $$('[data-pr]', el).forEach(x => x.classList.toggle('on', x === b)); });
      $('#pvsnd', el).onchange = ev => { sound = ev.target.checked; setPref('previewSound', sound ? '1' : '0'); pv.muted = !sound; };
      $('#inbig', el).onclick = () => { if (P) { P.loop.checked = true; P.playRange(e.start, Math.max(e.end, e.start + 2)); $('.watch').scrollIntoView({behavior: 'smooth', block: 'start'}); } };
    }
    $$('.vb', el).forEach(b => b.onclick = () => setVerdict(b.dataset.v));
    const note = $('#note', el);
    note.oninput = ev => { (S.events[e.id] = S.events[e.id] || {}).note = ev.target.value; $('#saved').textContent = '…'; save(); };
    note.onblur = () => rows();
    note.onkeydown = ev => { if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); note.blur(); move(1); } };
    $('#lib', el).onchange = ev => { (S.events[e.id] = S.events[e.id] || {}).library = ev.target.checked; changed(); };
    $('#auto', el).onchange = ev => { autoNext = ev.target.checked; setPref('autoNext', autoNext ? '1' : '0'); };
    $('#pv', el).onclick = () => move(-1); $('#nx', el).onclick = () => move(1); $('#nopen', el).onclick = nextOpen;
    $$('.sheets img', el).forEach(img => img.onclick = () => lightbox(e.sheets.map((s, k) => ({src: s, cap: `${e.id} ${e.label} · sheet ${k + 1}`})), +img.dataset.i));
    $$('[data-seek]', el).forEach(a => a.onclick = ev => { ev.preventDefault(); if (P) { P.v.pause(); P.seek(+a.dataset.seek); } });
  };
  const endCard = () => {                                 // after the last effect: what is left to do
    const real = evs.filter(e => !e.false_alarm), n = real.filter(e => vOf(e.id)).length, open = NM.filter(m => !mOf(m.frame)).length;
    $('#detail').innerHTML = `<div class="endcard"><h2>${n >= real.length ? 'Every effect has your verdict ✓' : 'That was the last effect in the list'}</h2>
      <div class="muted">${n} / ${real.length} effects with your verdict.</div>
      ${open ? `<div class="missline">Still to check: <b>${open} possible miss${open === 1 ? '' : 'es'}</b> - changes in the picture that no effect explains.</div>
        <button class="btn missbtn" data-tabgo="misses">Check the possible misses</button>` : ''}
      <div style="margin-top:14px">Then send everything to Claude: it turns your verdicts into lessons.</div>
      <div class="row" style="margin-top:8px"><button class="btn pri" data-feedback="${esc(name)}"><svg class="i"><use href="#i-claude"/></svg>Send feedback to Claude…</button>
        ${n < real.length ? '<button class="btn" id="endopen">Go to the next effect without a verdict</button>' : ''}<button class="btn ghost" id="endback">◀ Back to the list</button></div></div>`;
    const eb = $('#endback'); if (eb) eb.onclick = () => select(cur, true);
    const eo = $('#endopen'); if (eo) eo.onclick = nextOpen;
  };
  const setVerdict = v => {
    const st = S.events[cur.id] = S.events[cur.id] || {};
    st.v = st.v === v ? '' : v; changed();
    if (st.v === 'correct' && autoNext) { move(1); return; }
    detail();
    if (st.v === 'partly' || st.v === 'wrong') $('#note').focus();
  };
  const select = (e, seek) => {
    cur = e; T1.sel = T2.sel = e.id;
    history.replaceState(null, '', `#/ref/${encodeURIComponent(name)}?e=${e.id}`);
    rows(); detail(); T1.draw(); T2.draw();
    const tr = $(`#rows tr[data-id="${e.id}"]`), box = $('.evlist');      // scroll the list only, not the page
    if (tr && box && (tr.offsetTop < box.scrollTop || tr.offsetTop + tr.offsetHeight > box.scrollTop + box.clientHeight)) box.scrollTop = tr.offsetTop - 60;
    if (seek && P) { P.range = [e.start, e.end]; P.v.pause(); P.seek(e.start); }
  };
  const move = d => {
    const i = shown.indexOf(cur);
    if (d > 0 && i === shown.length - 1) { endCard(); return; }
    select(shown[i < 0 ? 0 : clamp(i + d, 0, shown.length - 1)], true);
  };
  const nextOpen = () => {
    const i = Math.max(0, shown.indexOf(cur));
    const e = [...shown.slice(i + 1), ...shown.slice(0, i + 1)].find(x => !x.false_alarm && !vOf(x.id) && x !== cur);
    if (e) select(e, true); else endCard();
  };
  // ---------------------------------------------------------------------------------------- possible misses
  const drawMisses = () => {
    const box = $('#misses'); if (!box) return;
    box.innerHTML = NM.map((m, i) => { const st = S.misses[String(m.frame)] || {}, v = st.v || '';
      return `<div class="miss ${v ? 'm-' + v : 'm-open'}" data-i="${i}" id="miss-${m.frame}">
        <div class="row sp"><span class="mstate">${v === 'effect' ? '★ an effect' : v === 'none' ? '✓ not an effect' : '● to check'}</span>
          <a href="#" class="fr" data-seek="${m.frame}">${ftc(m.frame, fps)}</a></div>
        <div class="f3">${m.frames.map((f, k) => `<figure><img src="${fileUrl(f)}" data-f="${m.frame - 1 + k}" title="f${m.frame - 1 + k} - click to show it in the player"><figcaption>${['before', 'at', 'after'][k] || ''} · f${m.frame - 1 + k}</figcaption></figure>`).join('')}</div>
        <div class="small muted">${esc(m.why)}</div>
        ${m.checked ? `<div class="claudechk"><b>Claude checked:</b> ${linkify(m.checked)}</div>` : '<div class="small dim">Claude has not checked this one yet.</div>'}
        <div class="row mbtns"><button class="btn sm ${v === 'effect' ? 'on' : ''}" data-mv="effect">★ It's an effect</button><button class="btn sm ${v === 'none' ? 'on' : ''}" data-mv="none">✓ Not an effect</button></div>
        <input type="text" data-mn placeholder="${v === 'effect' ? 'What is it? e.g. “a clock pops in, no fade”' : 'Note (optional)'}" value="${esc(st.note || '')}"></div>`; }).join('');
    $$('.miss', box).forEach(el => {
      const m = NM[+el.dataset.i], k = String(m.frame);
      $$('img', el).forEach(img => img.onclick = () => { if (P) { P.v.pause(); P.seek(+img.dataset.f); } });
      $$('[data-seek]', el).forEach(a => a.onclick = ev => { ev.preventDefault(); if (P) { P.v.pause(); P.seek(m.frame); } });
      $$('[data-mv]', el).forEach(b => b.onclick = () => {
        const st = S.misses[k] = S.misses[k] || {};
        st.v = st.v === b.dataset.mv ? '' : b.dataset.mv; changed(); drawMisses();
        if (st.v === 'effect') { const inp = $(`#miss-${m.frame} [data-mn]`); if (inp) inp.focus(); }
      });
      $('[data-mn]', el).oninput = ev => { (S.misses[k] = S.misses[k] || {}).note = ev.target.value; $('#saved').textContent = '…'; save(); };
    });
  };
  const focusMiss = f => { const el = $('#miss-' + f); if (el) { el.scrollIntoView({behavior: 'smooth', block: 'center'}); el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 1200); } if (P) { P.v.pause(); P.seek(f); } };
  const showTab = (t, scroll = false) => {
    if (t === 'misses' && !NM.length) t = 'review';
    tab = t;
    $$('#rtabs .rtab').forEach(b => b.classList.toggle('on', b.dataset.tab === t));
    $('#tab-review').hidden = t !== 'review'; if ($('#tab-misses')) $('#tab-misses').hidden = t !== 'misses';
    $('#tab-content').hidden = t !== 'content';
    if (t === 'content' && !$('#tab-content').dataset.done) contentTab($('#tab-content'), R, P);
    if (scroll) $('#rtabs').scrollIntoView({behavior: 'smooth', block: 'start'});
  };
  $$('#rtabs .rtab').forEach(b => b.onclick = () => showTab(b.dataset.tab, true));
  const tabGo = ev => { const g = ev.target.closest('[data-tabgo]'); if (g) { ev.preventDefault(); showTab(g.dataset.tabgo, true); } };
  main.addEventListener('click', tabGo); onCleanup(() => main.removeEventListener('click', tabGo));

  ['#q', '#ff', '#fv', '#showfa'].forEach(s => { if ($(s)) $(s).addEventListener('input', rows); });
  if ($('#agreefa')) $('#agreefa').onclick = () => {
    evs.filter(e => e.false_alarm).forEach(e => { const st = S.events[e.id] = S.events[e.id] || {}; if (!st.v) st.v = 'correct'; });
    changed(); detail(); toast('All false alarms marked as correctly dismissed', 'ok');
  };
  $('#missedb').onclick = () => modal(`<h2>Missed effects / general notes</h2>
    <p class="hint">Anything the analysis missed or got wrong overall. Mention frames or timecodes, e.g. “speed ramp around f1210 / 00:00:48:10”.
      The red possible misses have their own answers (tab “Possible misses”).</p>
    <textarea id="mt" rows="10">${esc(S.missed)}</textarea><div class="row" style="margin-top:10px"><button class="btn pri" id="mok">Save</button></div>`, el => {
    $('#mok', el).onclick = () => { S.missed = $('#mt', el).value; changed(); closeModal(); };
  });
  $('#exp').onclick = () => feedbackModal(name);
  $('#recreate').onclick = () => createVideoModal({from: 'reference', pick: R.name});
  $('#editmeta', main).onclick = e => { e.preventDefault(); metaModal(R); };
  KEYS = e => {
    if (e.target.matches('input, textarea, select')) return;
    const k = e.key;
    if (P && (k === 'ArrowLeft' || k === 'ArrowRight')) { P.step((k === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? 10 : 1)); e.preventDefault(); }
    else if (P && k === ' ') { P.toggle(); e.preventDefault(); }
    else if (P && k === 'Home') { P.seek(0); e.preventDefault(); }
    else if (tab !== 'review') return;
    else if (k === 'j' || k === 'J') move(-1);
    else if (k === 'k' || k === 'K') move(1);
    else if (k === 'n' || k === 'N') nextOpen();
    else if (k === '1' || k === '2' || k === '3') setVerdict(['correct', 'partly', 'wrong'][+k - 1]);
  };
  drawMisses(); progress(); showTab(tab); select(cur, false);
  if (P && selId) P.seek(cur.start);
  if (tab === 'misses') setTimeout(() => $('#rtabs').scrollIntoView({block: 'start'}), 50);
}

// ============================================================================================ projects
async function pageProjects(main) {
  const ps = await api('/api/projects');
  const cv = big => `<button class="btn pri${big ? ' big' : ''}" id="cvnew"><svg class="i"><use href="#i-claude"/></svg>Create video</button>`;
  main.innerHTML = `<div class="head"><div><h1>Videos</h1><div class="sub">Your own videos, made from a reference or a prompt.</div></div>
      ${ps.length ? `<div class="row">${cv(false)}<button class="btn" data-open="projects">Folder</button></div>` : ''}</div>
    ${ps.length ? `<div class="cards">${ps.map(p => `<div class="card refcard"><a class="clink" href="#/project/${encodeURIComponent(p.name)}">
      ${p.thumb ? `<img class="thumb" src="${fileUrl(p.thumb)}" loading="lazy">` : ''}
      <div class="cb"><div class="ct">${esc(p.name)}</div>
      <div class="small muted">${p.clips} clips · ${bytes(p.footage_bytes)} of footage</div>
      <div class="small">${p.plans.length} edit version${p.plans.length === 1 ? '' : 's'} · ${p.renders.length} render${p.renders.length === 1 ? '' : 's'}${p.resolve.length ? ' · in Resolve: ' + esc(p.resolve.join(', ')) : ''}</div></div></a>
      <div class="cact"><a class="btn sm" href="#/project/${encodeURIComponent(p.name)}">Open</a><div class="grow"></div>${delBtn('project', p.name)}</div></div>`).join('')}</div>`
      : emptyHero('videos', 'Make your first video', 'Use the edit of a reference you analysed, or one of your prompts - with your own clips.', cv(true))}`;
  $('#cvnew', main).onclick = () => createVideoModal();
}

// Create video (0.3.3): from a reference (its edit, 1:1, with your clips) or from a prompt (a script, a hook, a shot);
// the video's folder records what it is made from (build\made_from.json) and Claude Code does the work
async function createVideoModal(pre = {}) {
  const [refs, PRM, ps] = await Promise.all([api('/api/references'), api('/api/prompts'), api('/api/projects')]);
  const KL = Object.fromEntries(PRM.kinds.map(k => [k.id, k.label]));
  let from = pre.from || '', pick = pre.pick || '';
  modal(`<h2>Create a video</h2>
    <div class="cvchoice">
      <button class="cvopt" data-from="reference"><svg class="ic"><use href="#i-refs"/></svg><b>Use a reference</b>
        <span>The cuts, effects and timing of a video you analysed, with your own clips</span></button>
      <button class="cvopt" data-from="prompt"><svg class="ic"><use href="#i-prompts"/></svg><b>Use a prompt</b>
        <span>A brief, a talking script or a hook from your Prompts</span></button></div>
    <div id="cvpick"></div>
    <div id="cvclips" hidden><h3>Your clips</h3>
      <div class="row"><select id="cvp" style="max-width:320px">${ps.map(x => `<option value="${esc(x.name)}">${esc(x.name)} (${x.clips} clips)</option>`).join('')}<option value="">+ a new video…</option></select>
        <input type="text" id="cvname" placeholder="name, e.g. cooking vlog 1" hidden style="max-width:260px"><button class="btn sm" id="cvmk" hidden>Create the folder</button></div>
      <div class="small muted" id="cvhint" style="margin-top:6px"></div></div>
    <div class="row" style="margin-top:14px"><button class="btn pri" id="cvgo" disabled><svg class="i"><use href="#i-claude"/></svg>Start in Claude Code</button>
      <span class="small muted">Claude makes it with you - first a preview, then, if you want, a DaVinci Resolve project. It can take an hour or more.</span></div>`, el => {
    const sel = $('#cvp', el), name = $('#cvname', el), mk = $('#cvmk', el);
    const say = () => from === 'reference' ? `/recreate-video ${pick} ${sel.value}` : `/recreate-video prompt:${pick} ${sel.value}`;
    const upd = () => {
      const ready = from && pick && sel.value;
      $('#cvgo', el).disabled = !ready;
      const nw = !sel.value; name.hidden = mk.hidden = !nw;
      const P = ps.find(x => x.name === sel.value);
      $('#cvhint', el).innerHTML = nw ? 'A new folder for this video - copy your clips into it.'
        : P && !P.clips ? `<span class="amber">No clips in ${esc(P.name)} yet</span> - copy them into its folder, then start.` : 'Your clips are only read, never changed.';
    };
    const showPick = () => {
      $$('.cvopt', el).forEach(b => b.classList.toggle('on', b.dataset.from === from));
      const box = $('#cvpick', el);
      if (from === 'reference') {
        const rs = refs.filter(r => !r.test);
        box.innerHTML = `<h3>Which reference?</h3>${rs.length ? `<div class="cvlist">${rs.map(r => `<label class="cvitem${r.name === pick ? ' on' : ''}"><input type="radio" name="cvr" value="${esc(r.name)}" ${r.name === pick ? 'checked' : ''}>
          ${r.thumb ? `<img src="${fileUrl(r.thumb)}" loading="lazy">` : ''}<span><b>${esc(r.title)}</b><br><span class="small muted">${esc(r.category_label || '')} · ${r.events} effects · ${(r.duration_s || 0).toFixed(0)} s</span></span></label>`).join('')}</div>`
          : '<div class="empty">No reference yet - download and analyse one first (<a href="#/refs" onclick="closeModal()">References</a>).</div>'}`;
      } else if (from === 'prompt') {
        box.innerHTML = `<h3>Which prompt?</h3><input type="search" id="cvq" placeholder="Search your prompts…" style="max-width:340px">
          <div class="cvlist" id="cvpl"></div>`;
        const draw = q => { $('#cvpl', box).innerHTML = PRM.items.filter(x => !q || [x.id, x.title, x.text, ...(x.tags || [])].join(' ').toLowerCase().includes(q)).slice(0, 60)
          .map(x => `<label class="cvitem${x.id === pick ? ' on' : ''}"><input type="radio" name="cvr" value="${esc(x.id)}" ${x.id === pick ? 'checked' : ''}>
            <span><b class="mono">${esc(x.id)}</b> ${esc(x.title || '')} <span class="tag">${esc(KL[x.kind] || x.kind)}</span>${(x.tags || []).map(g => ` <span class="fchip sm">${esc(g)}</span>`).join('')}<br>
            <span class="small muted">${esc(x.text.slice(0, 150))}${x.text.length > 150 ? '…' : ''}</span>${(x.style_refs || []).length
              ? `<br><span class="small">Style like: ${x.style_refs.map(n => esc(((PRM.styles || {})[n] || {}).title || n)).join(', ')}</span>` : ''}</span></label>`).join('') || '<div class="empty">No prompt matches.</div>'; wire(); };
        $('#cvq', box).oninput = debounce(e => draw(e.target.value.trim().toLowerCase()), 150);
        draw('');
      }
      wire();
      $('#cvclips', el).hidden = !from; upd();
    };
    const wire = () => $$('input[name=cvr]', el).forEach(r => r.onchange = () => {
      pick = r.value; $$('.cvitem', el).forEach(x => x.classList.toggle('on', $('input', x).checked)); upd(); });
    $$('.cvopt', el).forEach(b => b.onclick = () => { if (from !== b.dataset.from) pick = ''; from = b.dataset.from; showPick(); });
    sel.onchange = upd;
    mk.onclick = async () => {
      try {
        const r = await api('/api/projects/new', {name: name.value});
        ps.push({name: r.name, clips: 0});
        sel.insertAdjacentHTML('afterbegin', `<option value="${esc(r.name)}">${esc(r.name)} (new)</option>`); sel.value = r.name;
        openPath(r.folder); upd(); toast(`Folder “${r.name}” created - copy your clips into it`, 'ok');
      } catch (e) { toast(e.message, 'err'); }
    };
    $('#cvgo', el).onclick = async () => {
      try {
        await api(`/api/project/${encodeURIComponent(sel.value)}/made_from`, {kind: from, id: pick});
        openClaude(say(), 'recreate', `${from === 'reference' ? pick : 'prompt ' + pick} → ${sel.value}`);
        closeModal(); location.hash = '#/project/' + encodeURIComponent(sel.value);
      } catch (e) { toast(e.message, 'err'); }
    };
    if (from) showPick(); else upd();
  });
}

async function pageProject(main, name, tab = 'overview') {
  const P = await api('/api/project/' + encodeURIComponent(name));
  const tabs = [['overview', 'Overview'], ['renders', 'Renders'], ['graphics', `Graphics${P.overlays && P.overlays.length ? ` (${P.overlays.length})` : ''}`],
                ['timing', 'Timing check'], ['resolve', 'Resolve & library']];
  main.innerHTML = `<div class="head"><div><div class="crumb"><a href="#/projects">Videos</a> /</div><h1>${esc(P.name)}</h1>
    <div class="sub">${P.sources.length} clips · ${P.plans.length} edit version(s) · ${P.renders.length} render(s)</div></div>
    <div class="row"><button class="btn" data-open="${esc('projects/' + P.name)}">Folder</button>${delBtn('project', P.name, '#/projects', ' Delete…')}</div></div>
    <div class="tabs">${tabs.map(([k, l]) => `<a href="#/project/${encodeURIComponent(name)}/${k}" class="${k === tab ? 'on' : ''}">${l}</a>`).join('')}</div>
    <div id="tab"></div>`;
  const el = $('#tab');
  if (tab === 'renders') return projRenders(el, P);
  if (tab === 'graphics') return projGraphics(el, P);
  if (tab === 'timing') return projTiming(el, P);
  if (tab === 'resolve') return projResolve(el, P);
  return projOverview(el, P);
}

function outcomePanel(P) {
  const O = (P.outcome || {}).aspects || {}, mf = P.made_from || [];
  return `<div class="panel outcome"><div class="row sp"><h2>How did it turn out?</h2><span class="small muted">${(P.outcome || {}).updated
      ? 'saved ' + esc(P.outcome.updated) : 'tell Claude what worked - it reads this next time'}</span></div>
    ${mf.length ? `<div class="small" style="margin-bottom:8px">Made from: ${mf.map(x => x.kind === 'reference'
      ? `<a href="#/ref/${encodeURIComponent(x.id)}">${esc(x.id)}</a>` : `<a href="#/prompts/${esc(x.id)}">prompt ${esc(x.id)}</a>`).join(', ')}</div>` : ''}
    <div class="ogrid">${ASPECTS.map(([k, l]) => { const a = O[k] || {};
      return `<div class="orow" data-k="${k}"><span class="olab">${esc(l)}</span><span class="row" style="gap:4px">${['good', 'ok', 'bad'].map(r =>
        `<button class="btn sm vrb ${r}${a.rating === r ? ' on' : ''}" data-r="${r}">${r === 'ok' ? 'OK' : r[0].toUpperCase() + r.slice(1)}</button>`).join('')}</span>
        <input type="text" class="onote" placeholder="what to keep or change (Enter saves)" value="${esc(a.note || '')}"></div>`; }).join('')}</div>
    <div class="row" style="margin-top:10px">${claudeBtn(`/recreate-video improve ${P.name}`, 'Improve it with Claude (the parts marked OK / Bad)', 'recreate', P.name)}</div></div>`;
}
function wireOutcome(el, P) {
  const save = async (k, rating, note, msg) => {
    try { P.outcome = await api(`/api/project/${encodeURIComponent(P.name)}/outcome`, {aspects: {[k]: {rating, note}}}); toast(msg, 'ok'); }
    catch (e) { toast(e.message, 'err'); }
  };
  $$('.orow', el).forEach(row => {
    const k = row.dataset.k, note = $('.onote', row);
    $$('[data-r]', row).forEach(b => b.onclick = () => {
      const was = b.classList.contains('on');
      $$('[data-r]', row).forEach(x => x.classList.toggle('on', x === b && !was));
      save(k, was ? null : b.dataset.r, note.value, was ? 'Removed' : 'Saved');
    });
    note.onkeydown = e => { if (e.key === 'Enter') save(k, ($('[data-r].on', row) || {dataset: {}}).dataset.r || null, note.value, 'Note saved'); };
  });
}
function projOverview(el, P) {
  el.innerHTML = `${outcomePanel(P)}<div class="grid g2" style="margin-top:14px"><div class="panel"><h2>Your footage (read-only)</h2>
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
  wireOutcome(el, P);
}

function projRenders(el, P) {
  const vids = [...P.renders, ...P.compares];
  const fpsOf = () => (P.plans[0] || {}).fps || 25, frames = (P.plans[0] || {}).frames;
  el.innerHTML = `<div class="grid g2">${P.renders.map((r, i) => `<div class="panel"><div class="row sp"><h2>${r.kind === 'resolve' ? 'From DaVinci Resolve' : 'Lab render'}</h2>
      <span class="small muted">${esc(r.name)} · ${bytes(r.size)} · ${esc(r.modified)}</span></div><div id="pl${i}"></div>
      <div class="row" style="margin-top:8px"><button class="btn sm" data-open="${esc(r.rel)}">Open in player</button><button class="btn sm" data-open="${esc(r.rel)}" data-reveal>Show in folder</button>
        <div class="grow"></div>${delBtn('file', r.rel, '', ' Delete…')}</div></div>`).join('')}</div>
    <h3>Side by side with the reference</h3>
    <div class="grid g2">${P.compares.map((r, i) => `<div class="panel"><div class="row sp" style="margin-bottom:6px"><span class="small muted">${esc(r.name)} · ${bytes(r.size)}</span>${delBtn('file', r.rel, '', ' Delete…')}</div><div id="cp${i}"></div></div>`).join('')
      || '<div class="muted">none</div>'}</div>`;
  P.renders.forEach((r, i) => new Player($('#pl' + i, el), r.rel, fpsOf(), frames));
  P.compares.forEach((r, i) => new Player($('#cp' + i, el), r.rel, fpsOf(), frames));
  if (!vids.length) el.innerHTML = '<div class="empty">No renders yet.</div>';
}

// ---- Videos > Graphics (0.3.2): the video's HTML graphics (tools\overlay.py): settings, render, save to the library
function gsetInput(s) {
  const a = `data-set="${esc(s.id)}" data-type="${esc(s.type)}"`, v = s.value;
  if (s.type === 'color') return `<input type="color" ${a} value="${esc(v)}">`;
  if (s.type === 'boolean') return `<input type="checkbox" ${a} ${v ? 'checked' : ''}>`;
  if (s.type === 'enum') return `<select ${a}>${(s.options || []).map(o => `<option value="${esc(o.value)}" ${o.value === v ? 'selected' : ''}>${esc(o.label)}</option>`).join('')}</select>`;
  if (s.type === 'number') return `<input type="number" ${a} value="${esc(v)}"${s.min != null ? ` min="${s.min}"` : ''}${s.max != null ? ` max="${s.max}"` : ''} step="${s.step ?? 'any'}">`;
  return `<input type="text" ${a} value="${esc(v)}">`;
}
const gsetValue = i => i.dataset.type === 'boolean' ? i.checked : i.dataset.type === 'number' ? Number(i.value) : i.value;
const gthumb = g => g.thumb ? `<img src="${fileUrl(g.thumb)}?v=${g.thumb_v}" alt="" loading="lazy">` : '<div class="muted small">no picture yet</div>';

function projGraphics(el, P) {
  const O = P.overlays || [];
  const top = `<div class="row sp" style="margin-bottom:12px"><div class="hint">Titles, clocks, captions and other graphics, rendered as see-through clips for your video and for DaVinci Resolve. Change a setting, Save, then Render.</div>
    <button class="btn sm" id="gcap">Captions…</button></div>`;
  if (!O.length) {
    el.innerHTML = top + `<div class="empty">No graphics in this video yet. Add one from the <a href="#/library">Library</a> (Graphics → Use in a video), make captions from a subtitle file, or ask Claude for a new one when you recreate a video.</div>`;
    captionsBtn(el, P);
    return;
  }
  el.innerHTML = top + `
    <div class="col">${O.map(o => {
      const st = o.current ? `<span class="ok">rendered ✓</span> <span class="muted">${esc(o.rendered_at)}</span>`
        : o.rendered ? '<span class="amber">settings changed: render it again</span>' : '<span class="amber">not rendered yet</span>';
      return `<div class="gcard" data-g="${esc(o.name)}"><div class="gthumb">${gthumb(o)}</div>
        <div><div class="row sp"><b style="font-size:15px">${esc(o.name)}</b><span class="small muted">${o.frames} frames ${frange(0, o.frames - 1, o.fps)} · ${o.width}×${o.height} · ${o.fps} fps</span></div>
          <div class="small" style="margin:4px 0 10px">${st} · ${o.used_in.length ? `in the edit: ${o.used_in.map(esc).join(', ')}` : '<span class="muted">not in an edit version yet</span>'}</div>
          ${o.captions ? `<div class="small" style="margin:-4px 0 10px">Captions: ${plural(o.captions.cues, 'line')}, ${plural(o.captions.words, 'word')} from the ${esc(o.captions.what)}${o.captions.estimated ? ' · <span class="amber">word times estimated (the file has one time per line)</span>' : ''}</div>` : ''}
          ${o.problem ? `<div class="bad small">${esc(o.problem)}</div>` : ''}
          ${o.settings.length ? `<div class="gset">${o.settings.map(s => `<label title="${esc(s.id)}">${esc(s.label || s.id)}</label><div>${gsetInput(s)}</div>`).join('')}</div>`
            : '<div class="muted small">This graphic has no settings yet (Claude can add them: text, colours, timing).</div>'}
          <div class="row" style="margin-top:10px">${o.settings.length ? '<button class="btn sm" data-gsave disabled>Save settings</button>' : ''}
            <button class="btn sm ${o.current ? '' : 'pri'}" data-grender>Render</button>
            <button class="btn sm" data-glib ${o.current ? '' : 'disabled title="render it first"'}>Save to library…</button>
            ${o.srt ? `<button class="btn sm" data-open="${esc(o.srt)}" data-reveal title="the same captions as subtitles: import it into DaVinci Resolve's subtitle track and correct them there">Subtitles for Resolve (.srt)</button>` : ''}
            <button class="btn sm" data-open="${esc(o.folder)}">Folder</button></div>
          <div class="row" style="margin-top:8px"><span class="small muted">DaVinci Resolve:</span>
            <button class="btn sm" data-gclip ${o.rendered ? '' : 'disabled'} title="a numbered copy of this render to drag into Resolve's media pool - Resolve locks the files it uses, so the graphic itself stays free to render again">Clip for Resolve (.mov)</button>
            <button class="btn sm" data-gswap ${o.rendered ? '' : 'disabled'} title="after a new render: replaces this graphic in the project open in Resolve - position, length, size, opacity and blend mode on your timeline stay">Swap in DaVinci Resolve</button></div>
          <pre class="log" hidden></pre></div></div>`;
    }).join('')}</div>`;
  captionsBtn(el, P);
  $$('.gcard', el).forEach(card => {
    const name = card.dataset.g, pre = $('pre.log', card), save = $('[data-gsave]', card);
    $$('[data-set]', card).forEach(i => { i.oninput = i.onchange = () => { if (save) save.disabled = false; }; });
    if (save) save.onclick = async () => {
      const values = {};
      $$('[data-set]', card).forEach(i => { values[i.dataset.set] = gsetValue(i); });
      try { await api(`/api/project/${encodeURIComponent(P.name)}/overlay`, {overlay: name, values}); toast(`${name}: settings saved - render it to see them`, 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    };
    const run = async (kind, args, btn, then) => {
      if (save && !save.disabled) { toast('Save the settings first', 'err'); return; }
      const j = await startJob(kind, {project: P.name, overlay: name, ...args}, false);
      if (!j) return;
      btn.disabled = true; pre.hidden = false; pre.textContent = '';
      followJob(j.id, pre, jj => {
        toast(`${jj.title}: ${jj.status}`, jj.status === 'done' ? 'ok' : 'err');
        if (jj.status !== 'done') { btn.disabled = false; return; }
        if (then) then(); else route();
      });
    };
    $('[data-grender]', card).onclick = e => run('overlay_render', {}, e.target);
    $('[data-gswap]', card).onclick = e => run('overlay_refresh', {}, e.target, () => { e.target.disabled = false; });
    $('[data-gclip]', card).onclick = e => run('overlay_resolve_clip', {}, e.target, async () => {
      e.target.disabled = false;
      try {
        const NP = await api('/api/project/' + encodeURIComponent(P.name));
        const o2 = (NP.overlays || []).find(x => x.name === name);
        if (o2 && o2.resolve_clips && o2.resolve_clips[0]) openPath(o2.resolve_clips[0], true);
      } catch (err) { toast(err.message, 'err'); }
    });
    $('[data-glib]', card).onclick = e => modal(`<h2>Save “${esc(name)}” to the graphics library</h2>
      <div class="small muted">The library keeps its HTML, its settings as they are now and the rendered clip. Every video can use it (Library → Graphics), and you can drag the clip into a Power Bin in DaVinci Resolve.</div>
      <div class="row" style="margin-top:12px"><label>Name <input id="glname" value="${esc(name)}" style="width:220px"></label>
        <label class="chk"><input type="checkbox" id="glrep"> replace one with that name</label></div>
      <div class="row" style="margin-top:12px"><button class="btn pri" id="glgo">Save to library</button></div>`, m => {
      $('#glgo', m).onclick = () => { const nm = $('#glname', m).value.trim(), rep = $('#glrep', m).checked; closeModal(); run('overlay_save', {name: nm, replace: rep}, e.target); };
    });
  });
}

function captionsBtn(el, P) {
  // captions from a video's own words (speech to text, faster-whisper) or from a subtitle file (.srt / .vtt)
  const b = $('#gcap', el);
  if (!b) return;
  const SPc = P.speech || {}, media = P.media || [];
  b.onclick = () => modal(`<h2>Captions</h2>
    <div class="small muted">Styled captions timed to the words (change the style afterwards on this tab) and the same captions as an .srt for DaVinci Resolve's subtitle track. Your files are only read.</div>
    <div class="col" style="margin-top:12px">
      <label class="chk"><input type="radio" name="gcsrc" value="video" ${SPc.available && media.length ? 'checked' : 'disabled'}> <b>From the words in a video</b> (speech to text, on this PC)</label>
      <div class="col" id="gcvid" style="margin-left:24px">${SPc.available ? (media.length ? `
        <label>Video <select id="gcm">${media.map(m => `<option value="${esc(m.path)}">${esc(m.label)}</option>`).join('')}</select></label>
        <div class="hint">Pick the render of your edit, so the captions follow its cuts - or one of your clips.</div>
        <label>Names and words it might not know <input id="gcnames" placeholder="e.g. MotionLab, 4AM, Nemzzz, DaVinci Resolve"></label>
        <label>Model <select id="gcmod"><option value="small">small - the most accurate</option><option value="base">base - lighter, for slow laptops (ignores the names)</option></select></label>`
        : '<div class="hint">This video has no render or clip yet.</div>')
        : '<div class="hint">Speech to text is not installed yet: <a href="#/settings">Settings → Programs → Speech to text → Install</a> (one time, about 520 MB).</div>'}</div>
      <label class="chk"><input type="radio" name="gcsrc" value="file" ${SPc.available && media.length ? '' : 'checked'} ${P.plans.length ? '' : 'disabled'}> <b>From a subtitle file</b> (.srt / .vtt from YouTube, CapCut, Resolve's “Create Subtitles from Audio”)${P.plans.length ? '' : ' - needs an edit version (its size, rate and length)'}</label>
      <div style="margin-left:24px"><input id="gcf" placeholder="C:\\...\\my video.srt"></div>
      <label>Name <input id="gcn" value="captions" style="width:200px"></label></div>
    <div class="hint" style="margin-top:6px">The same name again replaces the words of those captions and keeps their style.</div>
    <div class="row" style="margin-top:12px"><button class="btn pri" id="gcgo">Make the captions</button><span id="gcmsg" class="small"></span></div><pre class="log" hidden></pre>`, m => {
    $('#gcgo', m).onclick = async () => {
      const go = $('#gcgo', m), src = ($('input[name=gcsrc]:checked', m) || {}).value;
      if (!src) { toast('Pick where the words come from', 'err'); return; }
      const args = {project: P.name, name: $('#gcn', m).value.trim()};
      if (src === 'video') Object.assign(args, {file: $('#gcm', m).value, names: $('#gcnames', m).value.trim(), model: $('#gcmod', m).value});
      else args.file = $('#gcf', m).value.trim();
      const j = await startJob('overlay_captions', args, false);
      if (!j) return;
      go.disabled = true; const pre = $('pre.log', m); pre.hidden = false;
      followJob(j.id, pre, jj => {
        if (jj.status === 'done') { closeModal(); route(); }
        else { $('#gcmsg', m).innerHTML = '<span class="bad">did not work - see the log</span>'; go.disabled = false; }
      });
    };
  });
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
  if (!P.resolve.length) { el.innerHTML = '<div class="empty">No DaVinci Resolve version of this video yet - Claude makes one when it recreates a video.</div>'; return; }
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
  main.innerHTML = `<div class="head"><div><h1>Library</h1><div class="sub">Graphics and effects you saved, ready for any of your videos.</div></div></div>
    <div class="grid g2"><div class="panel"><h2>Saved effects</h2>${L.items.length ? `<table class="t"><thead><tr><th>Effect</th><th>Recipe</th><th>Macros</th><th>Check in Resolve</th><th>Saved</th></tr></thead><tbody>
      ${L.items.map(i => `<tr><td><b>${esc(i.title)}</b></td><td><a href="#" data-open="${esc(i.recipe)}">${esc(i.name)}.md</a></td>
        <td>${i.macros.map(m => `<a href="#" data-open="${esc(m)}" data-reveal>${esc(m.split('/').pop())}</a>`).join(', ') || '<span class="muted small">recipe only</span>'}</td>
        <td>${i.check ? `<a href="#" data-open="${esc(i.check)}" title="the macro rendered in DaVinci Resolve next to the real frame"><img src="${fileUrl(i.check)}" alt="check" style="height:48px;border-radius:4px"></a>` : '–'}</td>
        <td class="small muted">${esc(i.modified)}</td></tr>`).join('')}</tbody></table>
      <div class="row" style="margin-top:8px"><button class="btn sm" data-open="library/README.md">Library index</button><button class="btn sm" data-open="library" data-reveal>Folder</button></div>`
      : '<div class="empty">Nothing saved yet.</div>'}</div>
    <div class="panel"><h2>Picked for saving</h2>${L.picks.length ? `<ul>${L.picks.map(p => `<li><b>${esc(p.effect)}</b> <span class="muted small">from <a href="#/project/${encodeURIComponent(p.project)}/resolve">${esc(p.project)}</a></span>${p.note ? `<div class="small muted">${esc(p.note)}</div>` : ''}</li>`).join('')}</ul>
      <div class="hint" style="margin-top:10px">Claude saves them (it needs Resolve open). In Claude Code say:</div>
      <div class="claude" style="margin-top:6px"><span>${esc(say)}</span><span class="row">${claudeBtn(say, 'Open in Claude Code', 'library')}<button class="btn sm" id="cs">Copy</button></span></div>`
      : `<div class="empty">Nothing picked yet. Open one of your videos (Videos page) → “Resolve &amp; library” and tick the effects you want.</div>`}</div></div>`;
  const cs = $('#cs'); if (cs) cs.onclick = () => copy(say);
  // graphics (0.3.2): yours (library\graphics) + the examples that come with MotionLab
  const G = L.graphics || [];
  $('.head', main).insertAdjacentHTML('afterend', `<h2 style="margin:4px 0 4px">Graphics</h2>
    <div class="hint" style="margin-bottom:10px">HTML graphics (titles, clocks, lower thirds…) whose text, colours and timing you change per video (Videos → Graphics). “Yours” are the ones you saved from a video; the examples come with MotionLab. A saved one keeps its rendered clip: drag that .mov into a Power Bin in DaVinci Resolve to have it in every project.</div>
    <div class="glib">${G.map(g => `<div class="gl"><div class="gthumb">${gthumb(g)}</div>
      <div class="row sp" style="margin-top:8px"><b>${esc(g.name)}</b><span class="tag">${g.kind === 'yours' ? 'yours' : 'example'}</span></div>
      <div class="small muted">${g.frames} frames · ${g.width}×${g.height} · ${g.fps} fps · ${plural(g.settings.length, 'setting')}</div>
      <div class="row" style="margin-top:8px"><button class="btn sm" data-use="${esc(g.name)}">Use in a video…</button>
        ${g.mov ? `<button class="btn sm" data-open="${esc(g.mov)}" data-reveal>The clip (.mov)</button>` : ''}</div></div>`).join('') || '<div class="empty">No graphics.</div>'}</div>`);
  $$('[data-use]', main).forEach(b => b.onclick = () => {
    const g = G.find(x => x.name === b.dataset.use), V = L.videos || [];
    const fits = v => !v.width || (v.width === g.width && v.height === g.height && Math.abs((v.fps || 0) - g.fps) < 0.01);
    modal(`<h2>Use “${esc(g.name)}” in a video</h2>
      <div class="small muted">A copy goes into the video's build\\overlays folder and is rendered right away; then change its settings on the video's Graphics tab.</div>
      ${V.length ? `<div class="row" style="margin-top:12px"><label>Video <select id="guv">${V.map(v => `<option value="${esc(v.name)}" ${fits(v) ? '' : 'disabled'}>${esc(v.name)}${fits(v) ? '' : ` (its edit is ${v.width}×${v.height} at ${v.fps} fps)`}</option>`).join('')}</select></label>
        <label>Name <input id="gun" value="${esc(g.name)}" style="width:200px"></label></div>
        <div class="hint" style="margin-top:6px">${esc(g.width + '×' + g.height)} at ${g.fps} fps: a video whose edit has another size or rate needs Claude to adapt the graphic.</div>
        <div class="row" style="margin-top:12px"><button class="btn pri" id="gugo">Add and render</button><span id="gumsg" class="small"></span></div><pre class="log" hidden></pre>`
      : '<div class="empty" style="margin-top:12px">No videos yet (Videos page).</div>'}`, m => {
      const go = $('#gugo', m);
      if (!go) return;
      const sel = $('#guv', m);
      const first = [...sel.options].find(o => !o.disabled);
      if (first) sel.value = first.value; else go.disabled = true;
      go.onclick = async () => {
        const project = sel.value, name = $('#gun', m).value.trim();
        const j = await startJob('overlay_new', {project, graphic: g.name, name}, false);
        if (!j) return;
        go.disabled = true; const pre = $('pre.log', m); pre.hidden = false;
        followJob(j.id, pre, jj => {
          if (jj.status === 'done') { closeModal(); location.hash = `#/project/${encodeURIComponent(project)}/graphics`; }
          else { $('#gumsg', m).innerHTML = '<span class="bad">did not work - see the log</span>'; go.disabled = false; }
        });
      };
    });
  });
}

// ============================================================================================ prompts (0.4)
// the prompt library: proven prompts per kind, split into their structure; Claude writes new ones like them
// (/write-prompt). One file per prompt in knowledge\local\prompts\ - the ratings live there too.
const PSRC = {tested: 'tested by you', creator: 'creator', written: 'written by Claude'};
// what a prompt is for (its tags): the page filters by it, /write-prompt copies examples made for the same thing first
const PURPOSES = ['vlog', 'talking head', 'music video', 'ad / product', 'cinematic b-roll', 'transitions', 'sfx',
                  'captions', 'motion graphics', 'colour', 'tutorial', 'storytelling'];
const ASPECTS = [['sound', 'Sound & music'], ['sfx', 'SFX'], ['colour', 'Colour'], ['captions', 'Captions'],
                 ['graphics', 'Motion graphics'], ['effects', 'Effects & transitions'], ['pacing', 'Pacing & cuts'], ['overall', 'Overall']];
const KSHORT = {shot: 'Video shot', image: 'Image', hook: 'Hook', script: 'Talking script', brief: 'Brief for Claude'};
// the parts Claude checks (prompts.SLOTS), in plain words
const SLOT_LABEL = {references: 'Uploads (what each is for)', keep: 'What stays the same', change: 'What changes', subject: 'Subject',
  action: 'Action', setting: 'Setting', camera: 'Camera', lens: 'Lens', light: 'Light', look: 'Look', motion: 'Motion',
  beats: 'Timing (beats)', audio: 'Sound', 'length / aspect': 'Length & format', avoid: 'What to avoid', composition: 'Composition',
  materials: 'Materials', pattern: 'Kind of hook', 'opening line': 'First line', 'on screen': 'On screen', promise: 'Promise',
  hook: 'Hook', problem: 'Problem', points: 'Main points', proof: 'Proof', 'call to action': 'Call to action',
  'format & length': 'Long or short, length & format', 'story & hook': 'Story & hook', 'feel / style': 'Feel & style reference',
  footage: 'Footage & b-roll', 'order & structure': 'Order & structure', 'pacing & cuts': 'Pacing & cuts', colour: 'Colour grading',
  music: 'Music', sfx: 'SFX', 'motion graphics': 'Motion graphics', transitions: 'Transitions', 'captions & text': 'Captions & text',
  effects: 'Effects (zooms, speed ramps, shake)', 'voice & audio': 'Voice & audio clean-up', ending: 'Ending & call to action',
  deliverable: 'Where it ends up', 'questions first': 'Questions to ask you first'};
const slotLabel = s => SLOT_LABEL[s] || (s ? s[0].toUpperCase() + s.slice(1) : '');
const STAT = {clear: ['✓', 'clear'], vague: ['~', 'vague'], missing: ['✗', 'missing']};
// a brief's check in the order a video is made (prompts.SLOTS["brief"]): the plan, the edit, sound, look, finish
const BRIEF_GROUPS = [['The plan', ['format & length', 'story & hook', 'feel / style', 'footage', 'order & structure']],
  ['The edit', ['pacing & cuts', 'transitions', 'effects']], ['Sound', ['voice & audio', 'music', 'sfx']],
  ['Look & text', ['colour', 'motion graphics', 'captions & text']], ['Finish', ['ending', 'deliverable', 'questions first']]];
const RUN = {brief: 'Run it - make the video', script: 'Record it - make the video', hook: 'Use it in a video', shot: 'Run it on the site', image: 'Run it on the site'};
const pstars = n => `<span class="stars" title="Claude's review of the prompt: ${n} of 5">${'★'.repeat(n)}<span class="off">${'★'.repeat(5 - n)}</span></span>`;
const ptitle = p => p.title || p.title_auto || p.text.trim().split(/\s+/).slice(0, 8).join(' ') + (p.text.trim().split(/\s+/).length > 8 ? '…' : '');
// what a prompt needs, in two words: the tool / model, and what you bring (your clips, a photo, you on camera)
// a site or app outside MotionLab that the prompt runs on (an account, credits, a setup): the "Needs another tool" filter
const TOOLS = /higgsfield|invideo|kling|runway|pika|luma|hailuo|minimax|sora|veo|midjourney|nano ?banana|gpt[- ]?image|chatgpt|dall-?e|seedance|flux|leonardo|ideogram|krea|capcut|hedra|heygen|elevenlabs|suno|wan ?2/i;
function ptool(p) {
  if (p.model && TOOLS.test(p.model)) return p.model;
  if (p.kind !== 'shot' && p.kind !== 'image') return '';
  if (p.model) return p.model;
  const m = (p.text || '').match(TOOLS);
  return m ? m[0][0].toUpperCase() + m[0].slice(1) : p.kind === 'shot' ? 'an AI video tool' : 'an AI image tool';
}
const ptoolChip = p => { const t = ptool(p);
  return t ? `<span class="pgneed pgtool" title="Runs on ${esc(t)} - a separate tool (an account, credits or a setup)">${esc(t)}</span>` : ''; };
// what you bring: your clips, a photo, you on camera - or nothing (text only)
function pneeds(p) {
  const t = p.text || '', refs = ((p.structure || []).find(x => x.slot === 'references') || {}).text || '';
  const out = [];
  if (p.kind === 'brief') out.push('your clips');
  else if (p.kind === 'script' || p.kind === 'hook') out.push('you on camera');
  else {
    const both = t + ' ' + refs;
    if (/@video\d*|source clip|tripod clip|your (clip|video|footage)|upload(ed)? (a |your )?(clip|video)|video[- ]to[- ]video/i.test(both)) out.push('your clip');
    else if (/@image\d*|reference (image|photo|picture)|your (photo|picture|selfie)|upload(ed)? (a |your )?(photo|image|picture)|image[- ]to[- ]video|start frame/i.test(both)) out.push('your photo');
    else out.push('text only');
  }
  return out;
}
const pcategory = p => (p.tags || []).find(x => PURPOSES.includes(x)) || (p.tags || [])[0] || '';
const pexUrl = (R, f) => fileUrl(`${R.folder}/examples/${f}`);
const pexMedia = (R, f, cls = '') => /\.(mp4|webm)$/i.test(f)
  ? `<video class="${cls}" src="${pexUrl(R, f)}#t=0.5" preload="metadata" muted playsinline></video>` : `<img class="${cls}" src="${pexUrl(R, f)}" loading="lazy" alt="">`;
const pcounts = st => Object.entries(STAT).map(([k, [ic, l]]) => { const n = st.filter(x => x.status === k).length;
  return n ? `<span class="cs ${k}" title="${n} ${l}">${ic} ${n}</span>` : ''; }).join('');
function psource(p) {
  const s = p.source || {};
  return s.type === 'creator' ? `<span class="tag">${esc(s.creator || 'creator')}</span>${s.link ? ` <a href="${esc(s.link)}" target="_blank" rel="noopener" class="small">link</a>` : ''}${s.file ? ` <span class="small dim" title="the file it came from">${esc(s.file)}</span>` : ''}`
    : `<span class="tag${s.type === 'tested' ? ' done' : ''}">${esc(PSRC[s.type] || s.type)}</span>${p.made_from && p.made_from.length ? ` <span class="small muted">from ${p.made_from.map(x => `<a href="#" data-goto="${esc(x)}">${esc(x)}</a>`).join(', ')}</span>` : ''}`;
}
const pusedLine = u => `<div class="small pused">Used in <a href="#/project/${encodeURIComponent(u.project)}">${esc(u.project)}</a>${Object.keys(u.aspects || {}).length
  ? ': ' + ASPECTS.filter(([k]) => (u.aspects[k] || {}).rating).map(([k, l]) => `<span class="vr ${u.aspects[k].rating}">${esc(l)} ${u.aspects[k].rating === 'ok' ? 'OK' : u.aspects[k].rating}</span>`).join(' ')
  : ' - <span class="muted">not rated yet (the video\'s Overview: “How did it turn out?”)</span>'}</div>`;
function pstyleBlock(p, R) {                           // after 0.3.4: "al estilo de Clavero" = a reference you analysed, measured
  const SR = R.styles || {};
  if (!STYLE_KINDS.includes(p.kind)) return '';
  const linked = p.style_refs || [], sug = (R.suggest || {})[p.id] || [];
  const one = n => { const s = SR[n];
    return `<div class="psref">${s && s.thumb ? `<img src="${fileUrl(s.thumb)}" loading="lazy" alt="">` : '<span></span>'}
      <div><a href="#/ref/${encodeURIComponent(n)}"><b>${esc(s ? s.title : n)}</b></a>${s && s.uploader ? ` <span class="small muted">by ${esc(s.uploader)}</span>` : ''}
        <div class="small">${s ? esc(s.line) : '<span class="bad">not analysed on this PC any more</span>'}</div></div>
      <button class="btn sm ghost" data-sdel="${esc(n)}" title="Unlink - Claude no longer copies its style">✕</button></div>`; };
  if (!linked.length && !sug.length && !Object.keys(SR).length) return '';
  return `<div class="pstyle"><div class="row"><span class="psl">Style like</span>${linked.length ? '' : '<span class="small muted">a video you analysed - Claude copies its measured pacing, effects and look</span>'}
      <span class="grow"></span><button class="btn sm ghost" data-spick>+ ${linked.length ? 'another reference' : 'pick from your references'}</button></div>
    ${linked.map(one).join('')}
    ${sug.map(x => `<div class="pssug small"><span>Found in your references: <b>${esc((SR[x.name] || {}).title || x.name)}</b> <span class="muted">(${esc(x.why)})</span></span>
      <button class="btn sm" data-suse="${esc(x.name)}">Use its style</button></div>`).join('')}
    ${linked.length ? '<div class="small muted">Claude reads its measured style when it checks, optimizes or runs this prompt - click <b>Optimize with Claude</b> to write it into the prompt.</div>' : ''}</div>`;
}
function pcheckBlock(p, R) {                           // Claude's check: a row per part, grouped for briefs, + what you want
  const rv = p.review || {}, st = p.structure || [], w = p.wishes || {}, checked = st.some(x => x.status);
  if (!st.length && rv.stars == null) return `<div class="pcheck none"><b>Not checked by Claude yet.</b> ${claudeBtn(`/write-prompt analyse ${p.id}`, 'Check it with Claude', 'prompt', p.id)}
    <span class="small muted">Claude looks at each part (${(R.kinds.find(k => k.id === p.kind) || {slots: []}).slots.slice(0, 7).map(slotLabel).join(', ').toLowerCase()}…) and marks it clear, vague or missing, with a tip.</span></div>`;
  const rowH = x => { const [ic] = STAT[x.status] || ['•'];
    return `<div class="crow ${esc(x.status || 'plain')}"><span class="cic">${ic}</span><span class="clab">${esc(slotLabel(x.slot))}</span>
      <span class="csay">${x.text ? esc(x.text) : '<i class="dim">not said</i>'}${x.tip ? `<span class="ctip">${esc(x.tip)}</span>` : ''}</span>
      <input type="text" class="cwish" data-slot="${esc(x.slot)}" placeholder="what you want here…" value="${esc(w[x.slot] || '')}"></div>`; };
  let rows = st.map(rowH).join('');
  if (p.kind === 'brief') {
    const seen = new Set();
    rows = BRIEF_GROUPS.map(([g, slots]) => { const xs = slots.flatMap(s => st.filter(x => x.slot === s)); xs.forEach(x => seen.add(x));
      return xs.length ? `<div class="cgroup">${esc(g)}</div>${xs.map(rowH).join('')}` : ''; }).join('');
    const rest = st.filter(x => !seen.has(x));
    if (rest.length) rows += `<div class="cgroup">Other</div>${rest.map(rowH).join('')}`;
  }
  return `<div class="pcheck flat"><div class="pchead"><b>Claude's check</b>${rv.stars != null ? pstars(rv.stars) : ''}${checked ? pcounts(st) : ''}
      <span class="small muted">${checked ? '- say what you want next to any part, then Optimize' : ''}</span></div>
    ${rv.why ? `<div class="small pwhy">${esc(rv.why)}</div>` : ''}${rv.fix ? `<div class="small pfix"><b>Claude suggests:</b> ${esc(rv.fix)}</div>` : ''}
    ${rows ? `<div class="clist"><div class="crow chead"><span></span><span>Part</span><span>What your prompt says · Claude's tip</span><span>What you want</span></div>${rows}</div>` : ''}
    <div class="row" style="margin-top:10px">${checked ? '' : '<span class="small muted">An older check without clear / vague / missing -</span>'}
      <button class="btn sm pri" data-opt title="Claude writes a better version from its check and what you want (a new prompt; this one stays)"><svg class="i"><use href="#i-claude"/></svg>Optimize with Claude</button>
      ${claudeBtn(`/write-prompt analyse ${p.id}`, 'Check it again', 'prompt', p.id)}<span class="small muted" data-wsaved></span></div></div>`;
}
const PFILTERS = [['', 'All'], ['tool', 'Needs another tool'], ['own', 'No other tool'], ['todo', 'Not checked yet']];
const pfilterOk = (p, f) => !f || (f === 'tool' ? !!ptool(p) : f === 'own' ? !ptool(p) : !p.structure && !p.review);
async function pagePrompts(main, arg) {               // every kind in one grid; a click opens the prompt
  const ctx = {R: await api('/api/prompts')};
  let q = '', pf = '';
  try { pf = localStorage.getItem('ml.pfilter') || ''; } catch (e) { /* no storage: all */ }
  if (!PFILTERS.some(([k]) => k === pf)) pf = '';
  const any = ctx.R.items.length;
  main.innerHTML = `<div class="head"><div><h1>Prompts</h1><div class="sub">Briefs for Claude, prompts for AI video and image tools, hooks and scripts. Click one to open it.</div></div>
      ${any ? `<div class="row"><input type="search" id="pq" placeholder="Search your prompts…" style="width:230px"><button class="btn pri" id="padd">Add prompts</button>
        <button class="btn" data-open="${esc(ctx.R.folder)}" data-reveal>Folder</button></div>` : ''}</div>
    ${any ? '<div class="row pfilters" id="pfil"></div><div id="ptodo"></div>' : ''}<div id="plist" class="pgrid"></div>`;
  if (!any) {
    $('#plist', main).className = '';
    $('#plist', main).innerHTML = emptyHero('prompts', 'Keep your best prompts here', 'Paste one you use, attach a creator\'s guide, or let Claude write one from zero. Claude checks each part and helps you improve it.',
      '<button class="btn pri big" id="padd">Add prompts</button>');
    $('#padd', main).onclick = () => addPromptsModal(ctx.R);
    return;
  }
  $('#padd', main).onclick = () => addPromptsModal(ctx.R);
  const row = p => { const res = (p.result || {}).rating, rv = p.review || {}, ex = (p.examples || [])[0], cat = pcategory(p);
    const rating = res ? `<span class="vr ${res}" title="what it made - your rating">${res === 'ok' ? 'OK' : res[0].toUpperCase() + res.slice(1)}</span>`
      : rv.stars != null ? pstars(rv.stars) : '<span class="small amber">not checked yet</span>';
    return `<button class="pgc k-${esc(p.kind)}" data-id="${esc(p.id)}" title="${esc(KSHORT[p.kind] || p.kind)} · ${esc(p.id)} - click to open">
      ${ex ? `<span class="pgthumb">${pexMedia(ctx.R, ex)}</span>` : ''}
      <span class="pgtop"><span class="kbadge k-${esc(p.kind)}">${esc(KSHORT[p.kind] || p.kind)}</span>${cat ? `<span class="pgcat">${esc(cat)}</span>` : ''}</span>
      <b class="pgtitle">${esc(ptitle(p))}</b>
      <span class="pgfoot"><span class="pgneeds">${ptoolChip(p)}${pneeds(p).map(x => `<span class="pgneed">${esc(x)}</span>`).join('')}</span>${rating}</span></button>`; };
  const draw = () => {
    const all = ctx.R.items, list = $('#plist', main);
    $('#pfil', main).innerHTML = PFILTERS.map(([k, l]) => { const n = all.filter(p => pfilterOk(p, k)).length;
      return k && !n ? '' : `<button class="fchip${k === pf ? ' on' : ''}" data-pf="${k}">${l} <span class="dim">${n}</span></button>`; }).join('');
    $$('[data-pf]', main).forEach(b => b.onclick = () => { pf = b.dataset.pf; try { localStorage.setItem('ml.pfilter', pf); } catch (e) { /* not kept */ } draw(); });
    const todo = all.filter(p => pfilterOk(p, 'todo')).map(p => p.id);
    $('#ptodo', main).innerHTML = pf === 'todo' && todo.length ? `<div class="small muted pftodo">Claude reads each one and marks what is clear, vague or missing, with a tip. ${claudeBtn(`/write-prompt analyse ${todo.join(' ')}`, todo.length === 1 ? 'Check it with Claude' : `Check these ${todo.length} with Claude`, 'prompt', 'analyse')}</div>` : '';
    const items = all.filter(p => pfilterOk(p, pf) && (!q || [p.id, p.title, p.title_auto, p.text, p.model, (p.source || {}).creator, KSHORT[p.kind], ...(p.tags || [])].join(' ').toLowerCase().includes(q)))
      .sort((a, b) => (b.updated || b.added || '').localeCompare(a.updated || a.added || '') || b.id.localeCompare(a.id));
    list.innerHTML = items.map(row).join('') || `<div class="empty">${q ? 'No prompt matches the search.' : 'Nothing here.'}</div>`;
    $$('.pgc', list).forEach(c => c.onclick = () => promptModal(c.dataset.id, ctx));
  };
  ctx.draw = draw;
  ctx.reload = async () => { ctx.R = await api('/api/prompts'); draw(); };
  const pq = $('#pq', main);
  pq.oninput = debounce(() => { q = pq.value.trim().toLowerCase(); draw(); }, 150);
  draw();
  if (arg && /^[a-z]+-\d+$/.test(arg)) {               // #/prompts/<id> (a link from a video, an optimized version): open it
    history.replaceState(null, '', '#/prompts');
    promptModal(arg, ctx);
  }
}
// one prompt in focus: the whole text, Style like, Claude's check with what you want, Optimize, Run it, your rating
function promptModal(id, ctx) {
  const R = ctx.R, all = R.items, p = all.find(x => x.id === id);
  if (!p) { toast(`${id} is not in your prompts any more`, 'err'); return; }
  const res = p.result || {}, rv = p.review || {}, help = R.help || {};
  const versions = all.filter(x => (x.made_from || []).includes(p.id));
  const shot = p.kind === 'shot' || p.kind === 'image';
  modal(`<div class="pm">
    <div class="row phead"><button class="kbadge k-${esc(p.kind)}" data-kind title="${esc(help[p.kind] || '')} - click to change the kind">${esc(KSHORT[p.kind] || p.kind)} ▾</button>
      <h2 class="ptitle">${esc(ptitle(p))}</h2><span class="mono small dim">${esc(p.id)}</span><span class="grow"></span>${rv.stars != null ? pstars(rv.stars) : ''}
      <span class="small dim">${esc(p.updated || p.added || '')}</span></div>
    <div class="row pfor small">${psource(p)}${p.model ? `<span class="chip">${esc(p.model)}</span>` : ''}${p.pattern ? `<span class="chip">${esc(p.pattern)}</span>` : ''}
      ${p.workflow ? `<span class="chip" title="one step of a multi-step recipe">${esc(p.workflow)}${p.step ? ` · step ${p.step}` : ''}</span>` : ''}
      <span class="muted">For:</span>${(p.tags || []).map(x => `<span class="fchip sm">${esc(x)}</span>`).join('') || '<span class="dim">not set</span>'}
      <button class="btn sm ghost" data-for title="What is it for? (vlog, talking head, SFX, transitions...)">Edit</button></div>
    <div class="ptextwrap"><pre class="ptext">${esc(p.text)}</pre></div>
    ${p.notes ? `<div class="small muted"><b>How to use:</b> ${esc(p.notes)}</div>` : ''}
    <div class="row pfor small"><span class="muted">Needs:</span>${ptoolChip(p)}${pneeds(p).map(x => `<span class="pgneed">${esc(x)}</span>`).join('')}
      ${ptool(p) ? '<span class="muted">- the first is a separate tool: an account, credits or a setup</span>' : ''}</div>
    <div class="pex"><div class="row"><span class="psl2">What it makes</span>${(p.examples || []).length ? '' : '<span class="small muted">a picture or clip of the result - yours, or the creator\'s example. The first one is the card\'s picture.</span>'}
        <span class="grow"></span><label class="btn sm ghost">+ Add a picture or clip<input type="file" data-exadd accept=".jpg,.jpeg,.png,.webp,.gif,.mp4,.webm" hidden></label></div>
      ${(p.examples || []).length ? `<div class="pexlist">${p.examples.map(f => `<figure data-ex="${esc(f)}">${/\.(mp4|webm)$/i.test(f)
        ? `<video src="${pexUrl(R, f)}" controls muted loop playsinline preload="metadata"></video>` : `<img src="${pexUrl(R, f)}" alt="" loading="lazy" data-exview>`}
        <button class="btn sm ghost" data-exdel="${esc(f)}" title="Remove it (Recycle Bin)">✕</button></figure>`).join('')}</div>` : ''}</div>
    ${pstyleBlock(p, R)}
    ${pcheckBlock(p, R)}
    ${versions.length ? `<div class="small pver">Optimized: ${versions.map(x => `<a href="#" data-goto="${esc(x.id)}">${esc(x.id)}${x.title ? ' - ' + esc(x.title) : ''}</a>`).join(', ')}</div>` : ''}
    ${((R.used || {})[p.id] || []).map(pusedLine).join('')}
    <div class="row prate"><button class="btn sm run" data-run title="${shot ? 'Copies it - paste it into the site (Higgsfield, Seedance, Kling...)' : 'Create video with this prompt'}">▶ ${RUN[p.kind] || 'Run it'}</button>
      <button class="btn sm" data-copy>Copy</button>
      <button class="btn sm cl" data-remix title="Claude keeps what worked in this prompt and changes what you say"><svg class="i"><use href="#i-claude"/></svg>Use it, change…</button>
      <button class="btn sm danger" data-pdel title="Move it to the Recycle Bin"><svg class="i"><use href="#i-trash"/></svg>Delete</button>
      <span class="grow"></span><span class="small muted">What it made:</span>
      ${['good', 'ok', 'bad'].map(r => `<button class="btn sm${res.rating === r ? ' on' : ''}" data-r="${r}">${r === 'ok' ? 'OK' : r[0].toUpperCase() + r.slice(1)}</button>`).join('')}
      <input type="text" class="pnote" placeholder="a note on the result (Enter saves)" value="${esc(res.note || '')}"></div></div>`, c => {
    const reopen = async () => { await ctx.reload(); promptModal(p.id, ctx); };
    const note = $('.pnote', c);
    const save = async (rating, msg) => {
      try { const r = await api('/api/prompts/rate', {id: p.id, rating, note: note.value});
        p.result = r.result; $$('[data-r]', c).forEach(b => b.classList.toggle('on', b.dataset.r === (r.result || {}).rating)); toast(msg, 'ok'); ctx.draw(); }
      catch (e) { toast(e.message, 'err'); }
    };
    $$('[data-r]', c).forEach(b => b.onclick = () => { const was = (p.result || {}).rating; save(was === b.dataset.r ? null : b.dataset.r, was === b.dataset.r ? 'Rating removed' : 'Rating saved'); });
    note.onkeydown = e => { if (e.key === 'Enter') save((p.result || {}).rating || null, 'Note saved'); };
    $('[data-copy]', c).onclick = () => copy(p.text);
    const back = () => promptModal(p.id, ctx);
    $('[data-remix]', c).onclick = () => { remixModal(p); modalBack(back); };
    $('[data-for]', c).onclick = () => { forModal(p, reopen); modalBack(back); };
    $('[data-pdel]', c).onclick = () => { delPromptModal(p); modalBack(back); };
    $('[data-kind]', c).onclick = () => { kindModal(p, R); modalBack(back); };
    $('[data-run]', c).onclick = () => {
      if (shot) { copy(p.text); toast('Copied - paste it into the site (Higgsfield, Seedance, Kling…), then rate what it made here', 'ok'); }
      else createVideoModal({from: 'prompt', pick: p.id}).then(() => modalBack(back));
    };
    $$('[data-goto]', c).forEach(a => a.onclick = e => { e.preventDefault(); promptModal(a.dataset.goto, ctx); });
    const saveWishes = async () => {                       // the wishes go with the prompt (Optimize reads them)
      const wishes = Object.fromEntries($$('.cwish', c).map(i => [i.dataset.slot, i.value.trim()]).filter(([, v]) => v));
      try { const r = await api('/api/prompts/wishes', {id: p.id, wishes}); p.wishes = r.wishes;
        const s = $('[data-wsaved]', c); if (s) s.textContent = Object.keys(wishes).length ? `your wishes saved (${Object.keys(wishes).length})` : ''; }
      catch (e) { toast(e.message, 'err'); }
    };
    $$('.cwish', c).forEach(i => { i.onchange = saveWishes; i.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); i.blur(); } }; });
    const opt = $('[data-opt]', c);
    if (opt) opt.onclick = async () => { await saveWishes(); openClaude(`/write-prompt optimize ${p.id}`, 'prompt', p.id); };
    const setStyle = async (refs, msg) => {
      try { await api('/api/prompts/style', {id: p.id, refs}); toast(msg, 'ok'); await reopen(); }
      catch (e) { toast(e.message, 'err'); }
    };
    const exIn = $('[data-exadd]', c);
    exIn.onchange = async () => {
      for (const f of [...exIn.files]) {
        if (f.size > 30e6) { toast(`${f.name}: pictures and clips up to 30 MB`, 'err'); continue; }
        try { await api('/api/prompts/example', {id: p.id, name: f.name, data: b64(await f.arrayBuffer())}); }
        catch (e) { toast(e.message, 'err'); }
      }
      await reopen();
    };
    $$('[data-exdel]', c).forEach(bt => bt.onclick = async () => {
      try { await api('/api/prompts/example', {id: p.id, remove: bt.dataset.exdel}); toast('Removed (Recycle Bin)', 'ok'); await reopen(); }
      catch (e) { toast(e.message, 'err'); }
    });
    $$('[data-exview]', c).forEach(im => im.onclick = () => {
      const pics = (p.examples || []).filter(f => !/\.(mp4|webm)$/i.test(f));
      lightbox(pics.map(f => ({src: `${R.folder}/examples/${f}`, cap: ptitle(p)})), Math.max(0, pics.indexOf(im.closest('figure').dataset.ex)));
    });
    const linkMsg = (p.structure || []).length ? 'Linked - now click Optimize with Claude so its measured style goes into the prompt'
      : 'Linked - Claude uses its measured style when it checks this prompt';
    $$('[data-suse]', c).forEach(b => b.onclick = () => setStyle([...(p.style_refs || []), b.dataset.suse], linkMsg));
    $$('[data-sdel]', c).forEach(b => b.onclick = () => setStyle((p.style_refs || []).filter(n => n !== b.dataset.sdel), 'Unlinked'));
    const sp = $('[data-spick]', c);
    if (sp) sp.onclick = () => { styleModal(p, R, n => setStyle([...(p.style_refs || []), n], linkMsg)); modalBack(back); };
  }, 'wide');
}
const STYLE_KINDS = ['brief', 'script', 'hook'];           // prompts that make a video (prompts.STYLE_KINDS)
// pick an analysed reference whose measured style a prompt follows (the ones its words seem to mean first)
function styleModal(p, R, done) {
  const SR = R.styles || {}, sug = ((R.suggest || {})[p.id] || []).map(x => x.name), have = p.style_refs || [];
  const names = [...sug, ...Object.keys(SR).filter(n => !sug.includes(n))].filter(n => !have.includes(n) && SR[n]);
  const why = Object.fromEntries(((R.suggest || {})[p.id] || []).map(x => [x.name, x.why]));
  modal(`<h2>Style like…</h2>
    <p class="hint">A video you analysed: Claude copies what the lab measured in it - cuts per minute, shot lengths, the first 3 seconds, its effects, the beat - and looks at its frames for the colour.
      Not there? <a href="#/refs">References</a>: download it and click Analyse first.</p>
    ${names.length > 6 ? '<input type="search" id="stq" placeholder="Search: title, creator…" style="max-width:340px">' : ''}
    <div class="cvlist" id="stl"></div>`, el => {
    const draw = q => {
      $('#stl', el).innerHTML = names.filter(n => !q || [n, SR[n].title, SR[n].uploader, SR[n].category_label].join(' ').toLowerCase().includes(q))
        .map(n => { const s = SR[n];
          return `<button class="cvitem" data-n="${esc(n)}">${s.thumb ? `<img src="${fileUrl(s.thumb)}" loading="lazy" alt="">` : ''}<span><b>${esc(s.title)}</b>${s.uploader ? ` <span class="small muted">by ${esc(s.uploader)}</span>` : ''}
            ${why[n] ? ` <span class="tag done">${esc(why[n])}</span>` : ''}<br><span class="small muted">${esc(s.category_label || '')} · ${esc(s.line)}</span></span></button>`; }).join('')
        || `<div class="empty">${Object.keys(SR).length ? 'Nothing more to pick.' : 'No analysed reference yet - <a href="#/refs">References</a>: download one and click Analyse.'}</div>`;
      $$('[data-n]', el).forEach(b => b.onclick = () => { closeModal(); done(b.dataset.n); });
    };
    const q = $('#stq', el);
    if (q) { q.oninput = debounce(() => draw(q.value.trim().toLowerCase()), 150); q.focus(); }
    draw('');
  });
}
// "Use it, change...": Claude keeps what worked in a prompt (structure, wording) and changes what the user says
function remixModal(p) {
  modal(`<h2>Use ${esc(p.id)}, change…</h2>
    <p class="hint">Claude keeps what worked in ${esc(p.id)} - its structure and wording - and changes what you write here. Leave it empty for a new one just like it.</p>
    <pre class="ptext" style="max-height:150px">${esc(p.text)}</pre>
    <textarea id="rmx" rows="4" style="width:100%" placeholder="e.g. the same camera move, but a cooking vlog at night - 9:16, 8 seconds"></textarea>
    <div class="row" style="margin-top:10px"><button class="btn pri" id="rmgo"><svg class="i"><use href="#i-claude"/></svg>Open in Claude Code</button></div>`, el => {
    $('#rmx', el).focus();
    $('#rmgo', el).onclick = () => {
      const c = $('#rmx', el).value.trim().replace(/\s+/g, ' ');
      openClaude(`/write-prompt ${p.kind} like ${p.id}${c ? ' - change: ' + c : ''}`, 'prompt', p.id); closeModal();
    };
  });
}
function forModal(p, done) {
  const own = (p.tags || []).filter(x => !PURPOSES.includes(x));
  modal(`<h2>What is ${esc(p.id)} for?</h2>
    <p class="hint">Pick or type: the Prompts page filters by it, and Claude copies examples made for the same thing first.</p>
    <div class="row">${PURPOSES.map(x => `<button class="fchip${(p.tags || []).includes(x) ? ' on' : ''}" data-t="${esc(x)}">${esc(x)}</button>`).join('')}</div>
    <input type="text" id="fown" style="margin-top:10px" placeholder="your own, comma-separated - e.g. make money online, fitness" value="${esc(own.join(', '))}">
    <div class="row" style="margin-top:10px"><button class="btn pri" id="fsave">Save</button></div>`, el => {
    $$('[data-t]', el).forEach(b => b.onclick = () => b.classList.toggle('on'));
    $('#fsave', el).onclick = async () => {
      const tags = [...$$('[data-t].on', el).map(b => b.dataset.t), ...$('#fown', el).value.split(',').map(s => s.trim().toLowerCase()).filter(Boolean)];
      try { const r = await api('/api/prompts/tags', {id: p.id, tags}); p.tags = r.tags; closeModal(); toast('Saved', 'ok'); done(); }
      catch (e) { toast(e.message, 'err'); }
    };
  });
}
// a prompt saved under the wrong kind (e.g. a brief for Claude saved as a talking script): it moves, with a new id
function kindModal(p, R) {
  modal(`<h2>What kind of prompt is ${esc(p.id)}?</h2>
    <div class="kpick">${R.kinds.map(k => `<label class="kopt${k.id === p.kind ? ' on' : ''}"><input type="radio" name="kk" value="${k.id}"${k.id === p.kind ? ' checked' : ''}>
      <span class="kbadge k-${k.id}">${esc(KSHORT[k.id] || k.label)}</span><span class="small muted">${esc((R.help || {})[k.id] || '')}</span></label>`).join('')}</div>
    <p class="hint">It gets a new id of that kind; Claude's next check uses the parts of that kind.</p>
    <div class="row" style="margin-top:10px"><button class="btn pri" id="kgo">Save</button></div>`, el => {
    $$('input[name=kk]', el).forEach(r => r.onchange = () => $$('.kopt', el).forEach(x => x.classList.toggle('on', $('input', x).checked)));
    $('#kgo', el).onclick = async () => {
      const k = ($('input[name=kk]:checked', el) || {}).value;
      if (!k || k === p.kind) { closeModal(); return; }
      try { const r = await api('/api/prompts/kind', {id: p.id, kind: k}); closeModal(); toast(`${p.id} is now ${r.id}`, 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    };
  });
}
function delPromptModal(p) {
  modal(`<h2>Delete ${esc(p.id)}?</h2>
    <p>${esc(p.title || p.text.slice(0, 160) + (p.text.length > 160 ? '…' : ''))}</p>
    <p class="hint">It goes to the Windows Recycle Bin - restore it from there if you change your mind.</p>
    <div class="row" style="margin-top:10px"><button class="btn danger" id="pdel">Delete</button><button class="btn" data-close>Cancel</button></div>`, el => {
    $('[data-close]', el).onclick = dismissModal;
    $('#pdel', el).onclick = async () => {
      try { await api('/api/prompts/delete', {id: p.id}); closeModal(); toast(`${p.id} moved to the Recycle Bin`, 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    };
  });
}
// Add prompts (0.3.4): 1) I have a prompt - paste any text or attach files (no format); the kind is guessed; a guide or a
// PDF goes to Claude (Let Claude sort it); Claude then checks it. 2) Generate a new prompt from zero - Claude writes it.
const b64 = buf => { const u = new Uint8Array(buf); let s = '';
  for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); };
function addPromptsModal(R) {
  R = R || {kinds: [], help: {}};
  const start = () => modal(`<h2>Add prompts</h2>
    <div class="cvchoice">
      <button class="cvopt" data-m="have"><svg class="ic"><use href="#i-prompts"/></svg><b>1. I have a prompt</b>
        <span>Paste it or attach a file. Claude then checks it - what is clear, vague or missing - and you say what you want.</span></button>
      <button class="cvopt" data-m="new"><svg class="ic"><use href="#i-claude"/></svg><b>2. Generate a new prompt from zero</b>
        <span>Tell Claude what you want to make - it writes the prompt from the best examples in your library.</span></button></div>`, el => {
    $$('.cvopt', el).forEach(b => b.onclick = () => {           // the next step on its own screen; Back returns here
      const have = b.dataset.m === 'have';
      modal(`<h2>${have ? '1. I have a prompt' : '2. Generate a new prompt from zero'}</h2><div id="amode"></div>`,
        m => (have ? havePromptForm : newPromptForm)($('#amode', m), R));
      modalBack(start);
    });
  });
  start();
}
function newPromptForm(box, R) {
  const kinds = (R.kinds || []).length ? R.kinds.map(k => k.id) : Object.keys(KSHORT);
  box.innerHTML = `<h3>What kind of prompt?</h3>
    <div class="kpick">${kinds.map((k, i) => `<label class="kopt${i === 0 ? ' on' : ''}"><input type="radio" name="nk" value="${k}"${i === 0 ? ' checked' : ''}>
      <span class="kbadge k-${k}">${esc(KSHORT[k] || k)}</span><span class="small muted">${esc((R.help || {})[k] || '')}</span></label>`).join('')}</div>
    <h3>What do you want to make?</h3>
    <textarea id="nwant" rows="5" style="width:100%" placeholder="e.g. a 10-15 min vlog of my first day in London from my Osmo Pocket 3 + Nano clips: chronological, a warm cinematic grade, whooshes on the transitions, a hook from my best line"></textarea>
    <div class="row" style="margin-top:8px;gap:6px"><span class="small muted">For:</span>${PURPOSES.map(x => `<button class="fchip sm" data-t="${esc(x)}">${esc(x)}</button>`).join('')}</div>
    <div class="row" style="margin-top:8px"><input type="text" id="nmodel" placeholder="for which model or tool? (optional - Claude Code, Seedance 2.0, Kling 3.0, Nano Banana…)" style="max-width:520px"></div>
    ${Object.keys(R.styles || {}).length ? `<div class="row" id="nstyle" style="margin-top:8px"><label class="small">In the style of <select id="nsty"><option value="">- none -</option>${Object.entries(R.styles).map(([n, s]) =>
      `<option value="${esc(n)}">${esc(s.title)}${s.uploader ? ' - ' + esc(s.uploader) : ''}</option>`).join('')}</select></label>
      <span class="small muted">a video you analysed: Claude copies its measured pacing and effects</span></div>` : ''}
    <div class="row" style="margin-top:12px"><button class="btn pri" id="ngo"><svg class="i"><use href="#i-claude"/></svg>Generate it in Claude Code</button>
      <span class="small muted">Claude asks what is missing, writes it, checks it and saves it here.</span></div>`;
  const nst = () => { const k = $('input[name=nk]:checked', box).value; if ($('#nstyle', box)) $('#nstyle', box).hidden = !STYLE_KINDS.includes(k); };
  $$('input[name=nk]', box).forEach(r => r.onchange = () => { $$('.kopt', box).forEach(x => x.classList.toggle('on', $('input', x).checked)); nst(); });
  nst();
  $$('[data-t]', box).forEach(b => b.onclick = () => b.classList.toggle('on'));
  $('#nwant', box).focus();
  $('#ngo', box).onclick = () => {
    const k = $('input[name=nk]:checked', box).value, w = $('#nwant', box).value.trim().replace(/\s+/g, ' ');
    const tags = $$('[data-t].on', box).map(b => b.dataset.t), m = $('#nmodel', box).value.trim();
    const sty = $('#nsty', box) && STYLE_KINDS.includes(k) ? $('#nsty', box).value : '';
    if (!w) { toast('Say what you want to make first', 'err'); $('#nwant', box).focus(); return; }
    openClaude(`/write-prompt ${k} - want: ${w}${tags.length ? ' - for: ' + tags.join(', ') : ''}${m ? ' - model: ' + m : ''}${sty ? ' - style: ' + sty : ''}`, 'prompt', 'new');
    closeModal();
  };
}
function havePromptForm(box, R) {
  const files = [];                                          // attached here: {file, rel, text}
  const kinds = (R.kinds || []).length ? R.kinds.map(k => k.id) : Object.keys(KSHORT);
  box.innerHTML = `<div class="small muted">Paste a prompt, or attach a file (.txt, .md, .docx, .pdf). Several prompts? Put a line with only
      <code>---</code> between them, or let Claude sort the file. Your prompts stay on this PC.</div>
    <textarea id="ptxt" rows="12" style="width:100%;margin-top:10px" spellcheck="false" placeholder="Paste your prompt here…"></textarea>
    <div class="row" style="margin-top:6px"><label class="btn sm">Attach a file
      <input type="file" id="pfile" accept=".txt,.md,.docx,.pdf" multiple hidden></label><span id="pfiles" class="small muted"></span></div>
    <div class="row" style="margin-top:10px;flex-wrap:wrap;gap:8px">
      <label class="small">Kind <select id="pkind"><option value="">guess from the text</option>${kinds.map(k => `<option value="${k}">${esc(KSHORT[k] || k)}</option>`).join('')}</select></label>
      <label class="small">Where from <select id="psrc"><option value="tested">mine / tested by me</option><option value="creator">a creator's (name / link)</option><option value="found">found somewhere</option></select></label>
      <input type="text" id="pwho" placeholder="creator name and/or link" hidden style="min-width:260px"></div>
    <div class="row" style="margin-top:8px;gap:6px"><span class="small muted">For:</span>${PURPOSES.map(x => `<button class="fchip sm" data-t="${esc(x)}">${esc(x)}</button>`).join('')}</div>
    <label class="small" style="display:block;margin-top:10px"><input type="checkbox" id="prv" checked> Then let Claude check it - each part clear, vague or missing, with tips (opens Claude Code)</label>
    <div class="row" style="margin-top:10px"><button class="btn pri" id="psave">Save</button>
      <button class="btn" id="psort" title="A guide or a file with several prompts, or a PDF: Claude reads it and saves every prompt in it">Let Claude sort it</button>
      <span id="pres" class="small"></span></div>`;
  const el = box;
  const txt = $('#ptxt', el), kind = $('#pkind', el), src = $('#psrc', el), who = $('#pwho', el), res = $('#pres', el);
  const say = (html, cls = '') => { res.innerHTML = cls ? `<span class="${cls}">${html}</span>` : html; };
  txt.focus();
  const guess = debounce(async () => {                      // the first option shows the guess
    const t = txt.value.trim();
    let k = '';
    try { if (t) k = (await api('/api/prompts/guess', {text: t})).kind; } catch (e) { /* keep "guess" */ }
    kind.options[0].textContent = k ? `guess: ${KSHORT[k] || k}` : 'guess from the text';
  }, 400);
  txt.oninput = guess;
  $$('[data-t]', el).forEach(b => b.onclick = () => b.classList.toggle('on'));
  const tags = () => $$('[data-t].on', el).map(b => b.dataset.t);
  src.onchange = () => { who.hidden = src.value !== 'creator'; if (!who.hidden) who.focus(); };
  const source = () => {
    if (src.value === 'tested') return {type: 'tested'};
    const w = who.value.trim(), link = (w.match(/https?:\/\/\S+/) || [''])[0];
    return {type: 'creator', creator: src.value === 'creator' ? w.replace(link, '').replace(/[\s,-]+$/, '').trim() : '', link: src.value === 'creator' ? link : ''};
  };
  const showFiles = () => { $('#pfiles', el).innerHTML = files.map(f => `<span class="tag">${esc(f.file)}</span>${f.text ? '' : ' <span class="amber">Claude reads it</span>'}`).join(' '); };
  $('#pfile', el).onchange = async e => {
    for (const f of [...e.target.files]) {
      if (f.size > 30e6) { say(`${esc(f.name)}: files up to 30 MB`, 'bad'); continue; }
      say(`reading ${esc(f.name)}…`);
      try {
        const r = await api('/api/prompts/file', {name: f.name, data: b64(await f.arrayBuffer())});
        files.push(r);
        if (r.text) { txt.value = (txt.value.trim() ? txt.value.trim() + '\n---\n' : '') + r.text; guess(); }
        say(r.text ? `${esc(r.file)}: its text is above - <b>Save</b> keeps it as one prompt; several prompts in it? <b>Let Claude sort it</b>`
          : `${esc(r.file)}: the lab reads no PDFs - <b>Let Claude sort it</b> reads it and saves its prompts`);
      } catch (err) { say(esc(err.message), 'bad'); }
    }
    e.target.value = ''; showFiles();
  };
  const done = (ids, kindOf) => {                            // saved: show them, maybe open Claude for the check
    say(`Saved ${plural(ids.length, 'prompt')}: ${ids.map(esc).join(', ')}`, 'ok');
    $('#psave', el).remove(); $('#psort', el).remove();
    if ($('#prv', el).checked) openClaude(`/write-prompt analyse ${ids.join(' ')}`, 'prompt', 'analyse');
    else res.insertAdjacentHTML('beforeend', ' ' + claudeBtn(`/write-prompt analyse ${ids.join(' ')}`, 'Check them with Claude', 'prompt', 'analyse'));
    const h = '#/prompts';                                   // the page behind the dialog shows them
    if (location.hash === h) route(); else location.hash = h;
  };
  $('#psave', el).onclick = async () => {
    if (!txt.value.trim()) { say(files.length ? 'A PDF has no text here - use <b>Let Claude sort it</b>' : 'Paste a prompt or attach a file first', 'bad'); return; }
    try {
      const r = await api('/api/prompts/import', {text: txt.value, kind: kind.value, source: source(), file: files.length === 1 ? files[0].file : '', tags: tags()});
      done(r.saved.map(x => x.id), r.saved[0].kind);
    } catch (e) { say(esc(e.message), 'bad'); }
  };
  $('#psort', el).onclick = async () => {
    try {
      const rels = files.map(f => f.rel);
      const typed = txt.value.trim(), fromFiles = files.map(f => f.text).filter(Boolean).join('\n---\n').trim();
      if (typed && typed !== fromFiles) {                    // pasted text: a file Claude can read
        const r = await api('/api/prompts/file', {name: `pasted ${new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')}.txt`,
                                                   data: b64(new TextEncoder().encode(typed))});
        rels.push(r.rel);
      }
      if (!rels.length) { say('Paste a guide or attach a file first', 'bad'); return; }
      const s = source(), from = s.type === 'tested' ? 'tested by me' : s.creator || s.link ? `creator ${s.creator} ${s.link}`.trim() : '';
      openClaude(`/write-prompt import ${rels.join(' ')}${kind.value ? ` - kind ${kind.value}` : ''}${from ? ` - source: ${from}` : ''}${tags().length ? ` - for: ${tags().join(', ')}` : ''}`, 'prompt', 'import');
      say('Claude Code opened: it reads the file(s), saves every prompt in them and checks them. The Prompts page shows them when it is done.', 'ok');
      $('#psave', el).remove(); $('#psort', el).remove();
    } catch (e) { say(esc(e.message), 'bad'); }
  };
}

// ============================================================================================ jobs
async function pageJobs(main, id) {
  const list = await api('/api/jobs');
  main.innerHTML = `<div class="head"><div><h1>Jobs</h1><div class="sub">What MotionLab is working on. Jobs keep running when you switch pages.</div></div>
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
    <div class="small muted mono" style="margin-bottom:8px">${esc(j.command)}</div>
    ${j.then_claude ? `<div class="small amber" style="margin-bottom:8px"><svg class="i"><use href="#i-claude"/></svg>Claude Code opens by itself when this measuring is done.</div>` : ''}<pre class="log" id="jlog"></pre>
    <div class="row" style="margin-top:8px"><button class="btn danger" id="jc" ${j.status === 'running' ? '' : 'hidden'}>Stop this job</button></div>`;
  $('#jc').onclick = async () => { if (!confirm('Stop this job?')) return; try { await api(`/api/jobs/${id}/cancel`, {}); } catch (e) { toast(e.message, 'err'); } };
  followJob(+id, $('#jlog'), jj => {
    $('#jst').className = 'tag ' + jj.status; $('#jst').textContent = jj.status; $('#jc').hidden = true;
    toast(`${jj.title}: ${jj.status}`, jj.status === 'done' ? 'ok' : 'err');
  });
}

// ============================================================================================ storage
// Settings has two tabs since 0.3.3: General (#/settings) and Storage (#/storage - the old page, out of the sidebar)
const setTabs = cur => `<div class="tabs">${[['#/settings', 'General'], ['#/storage', 'Storage']].map(([h, l]) =>
  `<a href="${h}" class="${h === cur ? 'on' : ''}">${l}</a>`).join('')}</div>`;
async function pageStorage(main) {
  main.innerHTML = `<div class="head"><div><h1>Settings</h1></div></div>${setTabs('#/storage')}<div class="loading">Measuring every folder of the lab… (a few seconds)</div>`;
  const S = await api('/api/storage');
  const COL = {source: '#4fb3ff', keep: '#3ecf8e', cache: '#ffc400', checks: '#ff9f43', finals: '#c56bff', env: '#5c5c66'};
  const used = S.units.reduce((a, u) => a + u.total, 0);
  const target = u => u === 'tools\\selftest' ? 'selftest' : u.split('\\').pop();
  main.innerHTML = `<div class="head"><div><h1>Settings</h1><div class="sub">Storage: MotionLab uses ${bytes(used)} · ${bytes(S.free_bytes)} free of ${bytes(S.total_bytes)} on this drive.
    Only data the lab can rebuild can be freed; your videos and everything learned are never touched.</div></div></div>${setTabs('#/storage')}
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
// Settings > Programs: the pinned HyperFrames / GSAP vs the newest on npm (asked once a day, motionlab.upstream) and
// the upgrade test (overlay.py upgrade-test renders the examples with both versions and compares every frame)
function upstreamBox(S) {
  const U = S.upstream || {}, P = U.packages || {}, hf = P.hyperframes || {}, gs = P.gsap || {};
  if (!hf.pinned || !(S.tools.find(t => t.name === 'hyperframes') || {}).found) return '';
  const pkg = (name, p) => `${name} <b>${esc(p.pinned)}</b>${p.installed && p.installed !== p.pinned ? ` <span class="amber">(installed ${esc(p.installed)} - Install again)</span>` : ''}${p.latest ? (p.newer
    ? ` · <span class="amber">${esc(p.latest)} on npm</span> <a href="${esc(p.notes)}" target="_blank" rel="noopener">what changed</a>` : ' · the newest') : ''}`;
  const t = hf.latest && (U.tests || {})[hf.latest];
  const worst = t && t.examples ? Math.max(...t.examples.map(x => x.max_diff ?? 255)) : null;
  const adopt = t && t.pass ? `Pin HyperFrames ${t.hyperframes}${t.gsap !== gs.pinned ? ` and GSAP ${t.gsap}` : ''} for MotionLab: run tools\\overlay.py pin ${t.hyperframes}${t.gsap !== gs.pinned ? ` --gsap ${t.gsap}` : ''}, then selftest.py --extended and tools\\dev\\smoke.py, and add a CHANGELOG line` : '';
  const test = !hf.newer && !gs.newer ? '' : t ? (t.pass
      ? `<span class="tag done">tested ${esc(String(t.when || '').slice(0, 10))}: same frames</span> <span class="small muted">(max ${worst}/255 on ${t.examples.length} examples, render ${t.examples.map(x => `${x.seconds_pinned} → ${x.seconds_candidate} s`).join(', ')}). A MotionLab update brings it once the repo owner adopts it.</span> ${claudeBtn(adopt, 'Adopt it (repo owner)', 'free', 'hyperframes')}`
      : `<span class="tag failed">tested ${esc(String(t.when || '').slice(0, 10))}: frames differ</span> <span class="small muted">${t.examples.map(x => `${esc(x.example)} ${x.error ? 'error' : x.max_diff + '/255'}`).join(' · ')} - MotionLab keeps ${esc(hf.pinned)}.</span>`)
      + ' <button class="btn sm" data-hftest>Test again</button>'
    : '<button class="btn sm" data-hftest title="Installs it in a scratch folder (.app\\dev), renders the overlay examples with both versions and compares every frame - a few minutes, ~300 MB">Test it</button>';
  return `<div class="upstream small"><div><b>HTML overlay packages:</b> ${pkg('HyperFrames', hf)} &nbsp;|&nbsp; ${pkg('GSAP', gs)}</div>
    <div class="row" style="margin-top:6px">${test}<span class="grow"></span><span class="dim">${U.checked ? `npm checked ${esc(U.checked.replace('T', ' ').slice(0, 16))}` : 'not checked yet'}${U.error ? ` · <span class="bad">${esc(U.error)}</span>` : ''}
      · <a href="#" id="upnpm">check now</a></span></div>
    <div class="dim">MotionLab only uses versions that passed this test; newer HyperFrames come several times a day.</div></div>`;
}
async function downloadModal() {
  const S = await api('/api/settings');
  const yt = S.tools.find(t => t.name === 'yt-dlp') || {};
  modal(`<h2>Download from a link</h2>
    <p class="hint">${yt.found ? '' : `<b class="bad">The downloader (yt-dlp) was not found.</b> ${esc(yt.how || '')} · <a href="#/settings">Settings</a><br>`}
      One video per link. Only download what you are allowed to use.</p>
    <input type="text" id="durl" placeholder="Paste a link - YouTube, TikTok, Instagram, Vimeo…">
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
  main.innerHTML = `<div class="head"><div><h1>Settings</h1><div class="sub">Programs, downloads, Claude Code and updates. Your settings stay on this PC.</div></div></div>${setTabs('#/settings')}
  <div class="panel"><div class="row sp"><h2>Programs</h2><button class="btn sm" id="recheck">Check again</button></div>
    <table class="t tools"><thead><tr><th>Program</th><th></th><th>Found at</th><th>Version</th><th>What for · how to get it</th></tr></thead><tbody>
    ${S.tools.map(t => `<tr><td><b>${esc(t.label)}</b><div class="need">${esc(t.need)}</div></td>
      <td class="st">${t.found ? '<span class="tag done">found</span>' : `<span class="tag ${t.need === 'required' ? 'failed' : ''}">missing</span>`}</td>
      <td class="mono small">${esc(t.path || '–')}</td><td class="small">${esc(t.version || '')}</td><td class="small muted">${esc(t.how)}${t.name === 'hyperframes' && (!t.found || /not downloaded/.test(t.version || ''))
        ? ((S.tools.find(x => x.name === 'node') || {}).found ? ' <button class="btn sm" data-hfinst>Install</button>' : ' <b>Install Node.js first.</b>') : ''}${t.name === 'speech' && (!t.found || /not downloaded/.test(t.version || ''))
        ? ' <button class="btn sm" data-spinst>Install</button>' : ''}</td></tr>`).join('')}
    </tbody></table>${upstreamBox(S)}</div>
  <div class="grid g2" style="margin-top:14px">
    <div class="panel"><h2>Downloads (yt-dlp)</h2><div class="form">
      <label for="ytp">yt-dlp.exe</label><input type="text" id="ytp" value="${esc(st.ytdlp_path)}" placeholder="empty = find it automatically">
      <label for="pre">Default format</label><select id="pre">${S.presets.map(o => `<option value="${o.id}" ${o.id === st.download_preset ? 'selected' : ''}>${esc(o.label)} → ${esc(o.folder)}</option>`).join('')}</select>
      <label for="nm">File name</label><input type="text" id="nm" class="mono" value="${esc(st.download_name)}">
      <span></span><div class="small muted">yt-dlp fields, e.g. <code>%(title).80s [%(id)s].%(ext)s</code> or <code>%(uploader)s - %(title)s.%(ext)s</code> (no folders)</div></div></div>
    <div class="panel"><h2>Claude Code</h2><div class="form">
      <label for="clp">claude</label><input type="text" id="clp" value="${esc(st.claude_path)}" placeholder="empty = find it automatically">
      <label for="cle">Effort</label><select id="cle"><option value="auto" ${st.claude_effort === 'auto' ? 'selected' : ''}>Recommended for each task: checking a video ${esc(S.tasks.review)}, feedback ${esc(S.tasks.feedback)}, recreating a video ${esc(S.tasks.recreate)}, writing prompts ${esc(S.tasks.prompt || 'medium')}, what next ${esc(S.tasks.plan || 'high')}</option>
        ${S.efforts.map(x => `<option value="${x}" ${st.claude_effort === x ? 'selected' : ''}>always ${x}</option>`).join('')}</select>
      <span></span><div class="small muted">How hard Claude thinks in the windows the app opens. Higher = more careful, slower, and it uses more of
        your Claude plan; “max” is for a problem Claude got stuck on. In a running window you can still change it with <code>/effort</code>.</div>
      <label>DaVinci Resolve</label><div>${(S.resolve_mcp || {}).registered
          ? `<span class="ok">Claude Code can look into DaVinci Resolve</span> <span class="small muted">(MCP ${esc(S.resolve_mcp.version || '')}, this PC, safe mode on)</span> <button class="btn sm" data-rmcp="resolve_mcp_remove">Disconnect</button>`
          : `<button class="btn sm" data-rmcp="resolve_mcp_install">Connect Claude Code to DaVinci Resolve (MCP)</button>`}
        <div class="small muted">Optional, needs Resolve Studio and Node.js. Claude can then read your open project (timelines, clips, markers)
          in a chat; it asks before changing anything there, and the lab's own Resolve builder still makes the rebuilds. New chats pick it up.</div></div></div>
      <div class="small muted" style="margin-top:10px">The review of every contact sheet, learning from your feedback and the rebuilds
      run in Claude Code; the app opens it in the lab folder with the exact request, so Claude starts working right away.</div>
      <div class="row" style="margin-top:10px">${claudeBtn('', 'Open Claude Code in the lab folder')}<button class="btn sm" data-tips>Tips for working with Claude</button></div></div>
  </div>
  <div class="panel" style="margin-top:14px"><h2>Sharing &amp; updates</h2>
    ${updateBox(S.update, null)}
    <div class="form">
      <label for="who">Your name</label><div><input type="text" id="who" value="${esc(st.author)}" placeholder="e.g. alex (shown on what you share)" style="max-width:320px">
        <div class="small muted">Used for “Share my knowledge” - letters, numbers and - only.</div></div>
      <label>GitHub</label><div class="small">${S.update && S.update.remote ? `<span class="mono">${esc(S.update.remote)}</span> · branch ${esc(S.update.branch || '')}` : `<span class="muted">${esc((S.update && S.update.error) || 'not checked yet')}</span>`}
        ${S.update && S.update.checked ? `<div class="dim">checked ${esc(S.update.checked)} · ${S.update.can_update ? `<b class="amber">${S.update.behind} update(s) waiting</b>` : 'up to date'}${S.update.ahead ? ` · ${S.update.ahead} of your commits not on GitHub yet` : ''}${testingText(S.update)}</div>` : ''}</div>
      <label>Updates</label><div class="col" style="gap:4px">
        <label class="chk small"><input type="radio" name="upm" value="ask" ${st.update_mode === 'ask' ? 'checked' : ''}><span>show the <b>Update available</b> button with what's new and wait for my click (recommended)</span></label>
        <label class="chk small"><input type="radio" name="upm" value="auto" ${st.update_mode === 'auto' ? 'checked' : ''}><span>install new versions by itself when MotionLab starts, then show what's new</span></label>
        <label class="chk small"><input type="radio" name="upm" value="off" ${st.update_mode === 'off' ? 'checked' : ''}><span>don't look for updates (<i>Check now</i> still works)</span></label>
        <div class="small muted">An update never touches your videos, analyses, verdicts, settings or knowledge.</div></div>
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
  const hft = $('[data-hftest]', main); if (hft) hft.onclick = async () => {
    hft.disabled = true;
    try { await startJob('overlays_upgrade_test', {}); } catch (e) { toast(e.message, 'err'); hft.disabled = false; }
  };
  const upc = $('#upnpm', main); if (upc) upc.onclick = async e => {
    e.preventDefault();
    try { await api('/api/upstream/check', {}); route(); } catch (err) { toast(err.message, 'err'); }
  };
  const spb = $('[data-spinst]', main); if (spb) spb.onclick = async () => {
    spb.disabled = true;
    try { await startJob('speech_install', {}); } catch (e) { toast(e.message, 'err'); spb.disabled = false; }
  };
  const hfb = $('[data-hfinst]', main); if (hfb) hfb.onclick = async () => {
    hfb.disabled = true;
    try { await startJob('overlays_install', {}); } catch (e) { toast(e.message, 'err'); hfb.disabled = false; }
  };
  $$('[data-rmcp]', main).forEach(b => b.onclick = async () => {
    b.disabled = true;
    try { await startJob(b.dataset.rmcp, {}); } catch (e) { toast(e.message, 'err'); b.disabled = false; }
  });
  wireUpdateBox(main);
  $('#upcheck').onclick = async () => {
    const b = $('#upcheck'); b.disabled = true; b.textContent = 'Checking…';
    try {
      const u = await api('/api/update/check', {});
      toast(u.error ? u.error : u.can_update ? (u.kind === 'version' ? `MotionLab ${u.new_version} is available` : `${plural(u.behind, 'change')} on GitHub`) : 'Up to date', u.error ? 'err' : 'ok');
      route(); ping();
    }
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
                                             claude_effort: $('#cle').value,
                                             author: $('#who').value,
                                             update_mode: ($('input[name=upm]:checked') || {}).value || 'ask'}});
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
    main.innerHTML = `<div class="head"><div><h1>Knowledge</h1><div class="sub">What you and your friends learned from references: a card per video, pacing per category, and lessons.
      Only text and numbers are shared - never videos.</div></div>
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
          <div class="row" style="margin-top:8px">${claudeBtn('Review the incoming lessons in knowledge\\incoming\\ (see Reviewing incoming lessons in the analyze-reference skill) and merge the good ones into the shared lessons.md', 'Review them in Claude Code', 'lessons')}</div>` : '<div class="dim small">None.</div>'}
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
// after an update the restarted window shows once what came in (the CHANGELOG sections between the two versions)
api('/api/update').then(u => { const r = u && u.result; if (r && r.updated && !r.seen) whatsNewModal(r); }).catch(() => {});
