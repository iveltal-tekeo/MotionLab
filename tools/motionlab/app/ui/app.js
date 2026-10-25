/* MotionLab app - plain JavaScript, no build step. Since 0.4 the ways in: Analyze (#/analyze: other people's
   videos - download, analyse, Claude's check, your verdicts; #/ref/<name> = one analysis), Prepare (#/prepare: the
   script - improve yours or write one from zero, /write-script), Edit (#/edit: your clips -
   a new edit, renders, graphics, Resolve; #/project/<name>), Generate (#/generate + the prompt library #/prompts), then
   Claude's memory (#/memory: what Claude learned + the saved effects and graphics), Jobs and Settings (+ Storage and
   Claude skills). The 0.3 routes (#/refs, #/projects, #/knowledge, #/library) still work. Every frame shown = number +
   timecode. */
'use strict';

// ============================================================================================ helpers
const TOKEN = document.querySelector('meta[name=ml-token]').content;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const pad = n => String(n).padStart(2, '0');
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
// ---- the user's language (Settings > Language, 2026-10-18, the user: "we need a spanish version of the entire app";
// Spain, tú). The words = window.ML_I18N, inlined by the server before this file (motionlab\i18n.py: ui\i18n\es.json +
// its part files; English = {}: a missing key shows the English). A key = the English exactly as written here, with
// {name} placeholders and inline tags; 'Open|verb' = a key with a context. t(en, vars) = the text; tn(n, one, other,
// vars) = a count ({n} = the number); ta() = t() for an attribute; plural() reads the catalogue's _nouns. Numbers:
// numStr (as the code prints them), numLoc (grouped), dec (fixed decimals); numIn reads "4.1" and "4,1". Never
// translated: commands, ids, file names, the f480 (00:00:16:00) notation, the MOTIONLAB FEEDBACK export
// (tools\motionlab\app\CLAUDE.md "Languages"; tools\dev\i18n_check.py check / todo <area>).
const LANG = document.documentElement.lang || 'en';
const I18N = window.ML_I18N || {};
const CTX = /(\S)\|[a-z][a-z0-9 _-]{0,40}$/;
const fillVars = (s, v) => v ? String(s).replace(/\{(\w+)\}/g, (m, k) => (k in v ? String(v[k]) : m)) : s;
function t(en, vars) {
  let s = I18N[en];
  if (s && typeof s === 'object') s = s.other;
  return fillVars(typeof s === 'string' && s ? s : String(en).replace(CTX, '$1'), vars);
}
const PLURAL = LANG === 'en' ? null : new Intl.PluralRules(LANG);
function tn(n, one, other, vars) {
  const v = {n: numStr(n), ...vars}, s = I18N[other];
  if (s && typeof s === 'object') return fillVars(s[PLURAL ? PLURAL.select(n) : +n === 1 ? 'one' : 'other'] || s.other || s.one, v);
  return fillVars(typeof s === 'string' && s ? s : String(+n === 1 ? one : other).replace(CTX, '$1'), v);
}
const ta = (en, vars) => esc(t(en, vars));
const NUMF = LANG === 'en' ? null : new Intl.NumberFormat(LANG, {maximumFractionDigits: 20});
const numStr = v => NUMF && typeof v === 'number' && isFinite(v) ? NUMF.format(v) : String(v);
const NUML = new Intl.NumberFormat(LANG);
const numLoc = v => NUML.format(v);
const DECF = {};
const dec = (v, d = 1) => LANG === 'en' ? Number(v).toFixed(d)
  : (DECF[d] = DECF[d] || new Intl.NumberFormat(LANG, {minimumFractionDigits: d, maximumFractionDigits: d})).format(v);
const numIn = s => { const x = String(s ?? '').trim(); return x === '' ? NaN : Number(/^-?\d*,\d+$/.test(x) ? x.replace(',', '.') : x); };
const andWords = list => LANG === 'en' ? list.join(' and ') : new Intl.ListFormat(LANG, {type: 'conjunction'}).format(list);
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
  return dec(n, n >= 100 || i === 0 ? 0 : 1) + ' ' + u[i];
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
  const b = document.createElement('button'); b.className = 'btn sm ghost mback'; b.textContent = t('← Back'); b.onclick = dismissModal;
  $('#modal .mbody').prepend(b);
}
function closeModal() { MODAL_BACK = null; $('#modal').hidden = true; $('#modal .mbody').innerHTML = ''; }
function dismissModal() { const back = MODAL_BACK; closeModal(); if (back) back(); }
$('#modal').addEventListener('mousedown', e => { if (e.target.id === 'modal' || e.target.closest('.mclose')) dismissModal(); });
let LB = {list: [], i: 0};
function lightbox(list, i) { LB = {list, i}; showLB(); }
function showLB() {
  const lb = $('#lightbox'), it = LB.list[LB.i]; if (!it) return;
  $('img', lb).src = fileUrl(it.src); $('.lbcap', lb).textContent = t('{cap}   ({i} / {n}, arrows to browse)', {cap: it.cap || it.src, i: LB.i + 1, n: LB.list.length});
  lb.hidden = false;
}
$('#lightbox').addEventListener('click', () => { $('#lightbox').hidden = true; });
const tip = $('#tip');
function showTip(html, x, y) { tip.innerHTML = html; tip.hidden = false; tip.style.left = Math.min(x + 14, innerWidth - 380) + 'px'; tip.style.top = (y + 16) + 'px'; }
function hideTip() { tip.hidden = true; }
async function copy(text) {
  try { await navigator.clipboard.writeText(text); }
  catch (e) { const ta = document.createElement('textarea'); ta.value = text; document.body.append(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
  toast(t('Copied to the clipboard'), 'ok');
}
async function openPath(path, reveal = false) {
  try { await api('/api/open', {path, reveal}); } catch (e) { toast(e.message, 'err'); }
}
// Claude Code in a new console in the lab folder, with an optional first message (the app's hand-off texts). task =
// what it is for (system.TASKS: review, feedback, lessons, library, recreate, prompt, free). First a small dialog:
// the model (Opus = every plan, the default; Fable = the strongest, Max plans; or Claude Code's own choice) and the
// effort, pre-filled from Settings and the task - "Don't ask again" saves them (Settings > Claude Code brings it back).
const MODEL_WORDS = {
  opus: ['Opus', t('the model every Claude plan includes - the right one for most tasks')],
  fable: ['Fable', t('the strongest model, for long or open-ended work. Max plans have their own weekly limit for it; on other plans Claude Code asks before it bills credits')],
  auto: [t('As set in Claude Code'), t('whatever you chose there with /model')],
};
async function launchClaude(body) {
  try {
    const r = await api('/api/claude', body);
    const how = [r.model ? MODEL_WORDS[r.model][0] : '', r.effort ? t('effort {level}', {level: r.effort}) : ''].filter(Boolean).join(', ');
    toast(how ? t('Claude Code is opening in a new window ({how})', {how}) : t('Claude Code is opening in a new window'), 'ok');
  } catch (e) { toast(e.message, 'err'); }
}
async function openClaude(prompt = '', task = 'free', label = '') {
  let o;
  try { o = await api('/api/claude', {task, options: true}); } catch (e) { toast(e.message, 'err'); return; }
  if (!o.ask) return launchClaude({prompt, task, label});
  modal(`<h2>${t('Open in Claude Code')}</h2>
    ${prompt ? `<div class="claude" style="margin-bottom:12px"><span class="mono small">${esc(prompt.length > 220 ? prompt.slice(0, 220) + '…' : prompt)}</span></div>` : `<p class="small muted">${t('A free chat in the lab folder.')}</p>`}
    <div class="cmodels">${o.models.map(m => `<label class="chk-open cmodel"><input type="radio" name="cmodel" value="${m}" ${m === o.model ? 'checked' : ''}><span><b>${MODEL_WORDS[m][0]}${m === 'fable' && o.fable_fits ? ` <em class="tag">${t('stronger for this task')}</em>` : ''}</b><small>${MODEL_WORDS[m][1]}</small></span></label>`).join('')}</div>
    <div class="row" style="margin-top:12px;gap:14px;align-items:center"><label for="ceff" class="small muted">${t('Effort')}</label>
      <select id="ceff">${o.efforts.map(x => `<option value="${x}">${x}</option>`).join('')}</select>
      <span class="small muted" id="cefh"></span></div>
    <label class="chk" style="margin-top:12px"><input type="checkbox" id="cask"><span>${t("Don't ask again - use this every time (Settings > Claude Code brings the question back)")}</span></label>
    <div class="row" style="margin-top:14px"><button class="btn pri" id="cgo"><svg class="i"><use href="#i-claude"/></svg>${t('Open in Claude Code')}</button><button class="btn" id="cno">${t('Cancel')}</button></div>`, el => {
    const eff = $('#ceff', el), hint = $('#cefh', el);
    const sync = () => {
      const m = $('input[name=cmodel]:checked', el).value, rec = o.recommended[m === 'auto' ? 'opus' : m];
      hint.textContent = rec ? t('recommended for this: {level}', {level: rec}) : '';
    };
    eff.value = o.effort || 'high';
    $$('input[name=cmodel]', el).forEach(i => i.onchange = () => { const m = i.value, rec = o.recommended[m === 'auto' ? 'opus' : m]; if (rec) eff.value = rec; sync(); });
    sync();
    $('#cno', el).onclick = closeModal;
    $('#cgo', el).onclick = () => {
      const model = $('input[name=cmodel]:checked', el).value, effort = eff.value, remember = $('#cask', el).checked;
      closeModal(); launchClaude({prompt, task, label, model, effort, remember});
    };
  });
}
const claudeBtn = (prompt, label = t('Open in Claude Code'), task = 'free', name = '', cls = 'sm cl') =>
  `<button class="btn ${cls}" data-claude="${esc(prompt)}" data-task="${task}" data-label="${esc(name)}"><svg class="i"><use href="#i-claude"/></svg>${label}</button>`;
document.addEventListener('click', e => {
  const c = e.target.closest('[data-claude]');
  if (c) { e.preventDefault(); openClaude(c.dataset.claude, c.dataset.task || 'free', c.dataset.label || ''); return; }
  const f = e.target.closest('[data-feedback]');
  if (f) { e.preventDefault(); sendFeedback(f.dataset.feedback); return; }
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
// Home's motion graphic: how MotionLab is used, in four slow scenes (24 s loop). Pure CSS - only transform and opacity
// move, so the graphics card does it; nothing runs while the window is hidden; still with reduced motion (app.css)
const HERO_LINES = [[t('Like a video?'), t('Paste its link.')], [t('Use it as a reference.'), t('MotionLab finds every cut and effect.')],
                    [t('Claude names each one.'), t('You say if it is right.')], [t('Make yours.'), t('The same rhythm, with your own clips.')]];
const heroAnim = () => `<div class="hero"><div class="hero-text">
    <div class="hero-lines">${HERO_LINES.map(([h, sub], i) => `<div class="hero-line hl${i + 1}"><b>${h}</b><span>${sub}</span></div>`).join('')}</div>
    <button class="btn pri" id="hero-go"><svg class="i"><use href="#i-download"/></svg>${t('Paste a link')}</button></div>
  <div class="hero-stage" aria-hidden="true">
    <div class="hs-mon"><i class="hs-b b1"></i><i class="hs-b b2"></i><i class="hs-b b3"></i><i class="hs-tint"></i>
      <span class="hs-lab l-ref">${t('reference')}</span><span class="hs-lab l-you">${t('your clips')}</span><span class="hs-play">▶</span></div>
    <div class="hs-tags">${['zoom', 'flash', t('whip pan')].map((w, i) => `<span class="hs-tag t${i + 1}">${w} <b>✓</b></span>`).join('')}</div>
    <div class="hs-track">${[13, 9, 16, 8, 14, 11, 17, 12].map((w, i) => `<i class="hs-clip" style="flex:${w}"><i class="hs-you" style="animation-delay:${(i * 0.22).toFixed(2)}s"></i></i>`).join('')}
      ${[13, 22, 38, 46, 60, 71, 88].map((x, i) => `<i class="hs-mark" style="left:${x}%;animation-delay:${(i * 0.3).toFixed(1)}s"></i>`).join('')}
      <i class="hs-head"><i></i></i></div>
    <span class="hs-done">${t('▶ your video')}</span></div></div>`;
// an empty page: what goes here, and the one button that starts it, in the middle (no "No ... yet" line)
const emptyHero = (icon, title, text, btns) => `<div class="ehero"><svg class="ic"><use href="#i-${icon}"/></svg><h2>${title}</h2>
  <p>${text}</p><div class="row">${btns}</div></div>`;
// an optional step: a bold OPTIONAL tag (+ a hint); its number is grey and dashed (.opt) - the user, 2026-10-14: optional
// steps numbered like the required ones look obligatory
const optTag = (hint = '') => `<span class="optag" title="${ta('You can skip this step')}">${t('Optional')}</span>${hint ? `<span class="nehint">${hint}</span>` : ''}`;
// ---- Reviews: one pattern everywhere (2026-10-18, the user: "lets improve the reivew workflow. in all sections i need
// you to make it the same way if im either reviewing a script in prepare, reviewing a video analyzed or an edit or a
// generation of motion graphics, it needs to look the same so that the user is familiar with the process of reviewing
// it and making it easier in the future"). The thing being judged on the left, reviewPanel() on the right. One
// control, two word sets - the section's heading asks the question: "Is Claude right?" = Correct / Partly / Wrong
// (what Claude said: effects, thumbnail patterns, its check of a script / prompt / title), "How did it turn out?" =
// Good / OK / Bad (a result: a video's parts, what a prompt made); possible misses and sound effects answer on the
// same buttons. The stored values never change. [value, symbol, word, tone]
const SCALES = {
  claims: [['correct', '✓', t('Correct'), 'pos'], ['partly', '~', t('Partly'), 'mid'], ['wrong', '✗', t('Wrong'), 'neg']],
  result: [['good', '✓', t('Good'), 'pos'], ['ok', '~', t('OK'), 'mid'], ['bad', '✗', t('Bad'), 'neg']],
  miss: [['none', '✓', t('Not an effect'), 'pos'], ['effect', '★', t("It's an effect"), 'mid']],
  sound: [['none', '', t('None|sound'), 'ans'], ['some', '', t('Some|sound'), 'ans'], ['many', '', t('Many|sound'), 'ans']]};
const rvTone = (scale, v) => ((SCALES[scale] || []).find(x => x[0] === v) || [])[3] || '';
// the one control: ✓ ~ ✗ in green / amber / red, keys 1 2 3, a second press clears it; the words show on the current row
const rvButtons = (scale, v, size = '') => `<span class="rvscale${size ? ' ' + size : ''}">${(SCALES[scale] || []).map(([val, sym, word, tone], i) =>
  `<button type="button" class="btn rvb ${tone}${sym ? ' has-s' : ''}${v === val ? ' on' : ''}" data-v="${val}" title="${ta('{word} - key {key}, again to clear it', {word, key: i + 1})}">${sym ? `<span class="s">${sym}</span>` : ''}<span class="w">${esc(word)}</span><span class="kbd">${i + 1}</span></button>`).join('')}</span>`;
// a saved answer shown read-only (cards, a video's index, "Used in"): the same symbol, word and colour as the control
const rvChip = (scale, v, tip = '') => { const s = (SCALES[scale] || []).find(x => x[0] === v);
  return s ? `<span class="rvchip ${s[3]}"${tip ? ` title="${esc(tip)}"` : ''}>${s[1] ? s[1] + ' ' : ''}${esc(s[2])}</span>` : ''; };
// a place's saves one at a time, in the order given: a later answer never lands before an earlier one
const rvQueue = () => { let q = Promise.resolve(); return fn => (q = q.then(fn, fn)); };
/* reviewPanel(host, opts) -> {el, redraw(), select(sec, id), cur(), next(d), nextOpen(), focusNote(), flush(), saving(),
   saved(ok), destroy()} - THE review panel (its contract: tools\motionlab\app\CLAUDE.md "Reviews"). host = the <aside>
   beside the thing being judged; it becomes .panel.rvp: "N of M reviewed" + a live bar, one row per item (rvButtons +
   a note), Previous / Next / Next not reviewed (J K N), the tick "after ✓, go to the next one" (localStorage
   ml.autoNext, one setting everywhere) and the one last step *Send it to Claude*.
   opts: title (html), head (html beside the saved state), filters (html: the place wires them and calls redraw), top
   (html above the rows), sections: [{id, ask (the question), intro (a line under it), scale (SCALES), note: 'text'
   (Enter = a new line) | 'line' (Enter saves), items: () => [{id, label (html), sub (html), optional, red (red until
   answered)}] - read again on every redraw, so filters apply -, all: () => the same unfiltered, for the counts (default
   items), get: id => {v, note} (the saved answer, in the scale's values), set: (id, {v, note}) => the place's own save
   (change its state at once, then save; a Promise - false = not saved, the place said why), hint: v => the note's
   placeholder, empty: the words for an empty list, domId}], extra: {item: (sec, id) => html on the current row, panel:
   html under the rows}, start: true (the first row without an answer) | {sec, id} | false, onMove: (sec, id, first) =>
   the left side shows that item (first = as the panel opens), onEnd: () => after the last row, deselect: a click on
   the current row lets it go, autoNext: false = no tick, stale: '' | () => '' (an amber line), send: {hint (what
   Claude does there), cmd + task + name (opened in Claude Code), go: async () => {} (runs first), ready: () => bool
   (default: one answer), glow: () => bool (default: every row that is not optional answered), more: html}, dialog:
   true when it sits in #modal. Its keys come from the document's keydown (RV_LIVE), never while typing elsewhere. */
let RV_LIVE = [];                                     // the review panels on screen: they get the keys first
function reviewPanel(host, opts) {
  const o = {title: t('Your review'), sections: [], start: true, ...opts};
  const secs = o.sections, byId = Object.fromEntries(secs.map(s => [s.id, s]));
  let auto = true, cur = null, gone = false, busy = 0, failed = false;
  try { auto = localStorage.getItem('ml.autoNext') !== '0'; } catch (e) { /* no storage: on */ }
  const lists = {}, pend = new Map(), K = (sid, id) => `${sid}\u0001${id}`;
  host.classList.add('panel', 'rvp');
  host.innerHTML = `<header class="rvp-h"><h2>${o.title}</h2><span class="rvp-st" aria-live="polite"></span>${o.head || ''}</header>
    <div class="rvp-prog"></div>${o.filters ? `<div class="rvp-filters">${o.filters}</div>` : ''}<div class="rvp-stale small amber" hidden></div>
    ${o.top ? `<div class="rvp-top">${o.top}</div>` : ''}
    <div class="rvp-body">${secs.map(s => `<section class="rvsec" data-sec="${esc(s.id)}"${s.domId ? ` id="${esc(s.domId)}"` : ''}><h3>${s.ask}</h3>${s.intro ? `<div class="small muted rvsec-i">${s.intro}</div>` : ''}<ol class="rvrows"></ol></section>`).join('')}</div>
    <nav class="rvnav"><button type="button" class="btn sm" data-rvgo="-1">${t('◀ Previous')} <span class="kbd">J</span></button><button type="button" class="btn sm" data-rvgo="1">${t('Next ▶')} <span class="kbd">K</span></button><button type="button" class="btn sm ghost" data-rvgo="open">${t('Next not reviewed')} <span class="kbd">N</span></button></nav>
    ${(o.extra || {}).panel ? `<div class="rvp-extra">${o.extra.panel}</div>` : ''}
    ${o.autoNext === false ? '' : `<label class="chk small rvauto" title="${ta('after ~ or ✗ you write a note first')}"><input type="checkbox"${auto ? ' checked' : ''}> ${t('after ✓, go to the next one')}</label>`}
    ${o.send ? `<footer class="rvsend"><div class="small muted rvsend-h">${(typeof o.send.hint === 'function' ? o.send.hint() : o.send.hint) || ''}</div>
      <button type="button" class="btn pri big rvsendb"${o.send.cmd ? ` data-cmd="${esc(o.send.cmd)}"` : ''} disabled><svg class="i"><use href="#i-claude"/></svg>${t('Send it to Claude')}</button>
      ${o.send.more ? `<div class="rvmore small">${o.send.more}</div>` : ''}</footer>` : ''}`;
  const secEl = Object.fromEntries($$('.rvsec', host).map(el => [el.dataset.sec, el]));
  const st = (txt, c = '') => { const e = $('.rvp-st', host); if (e) { e.textContent = txt; e.className = 'rvp-st' + (c ? ' ' + c : ''); } };
  const ans = (s, id) => { const a = s.get(id) || {}, p = pend.get(K(s.id, id)); return {v: a.v || '', note: p ? p.text : (a.note || '')}; };
  const isCur = (sid, id) => !!cur && cur.sec === sid && cur.id === String(id);
  const hintOf = (s, v) => s.hint ? s.hint(v) : ['mid', 'neg'].includes(rvTone(s.scale, v)) ? t('What is wrong? (saved as you type)') : t('A note (optional)');
  const cls = (s, it, a) => ['rvrow', a.v ? 'v-' + rvTone(s.scale, a.v) : '', isCur(s.id, it.id) ? 'cur' : '', a.note.trim() ? 'has-note' : '',
    it.red ? 'red' : '', it.optional ? 'opt' : ''].filter(Boolean).join(' ');
  const labHtml = it => (it.label || esc(it.id)) + (it.sub ? `<div class="rvsub">${it.sub}</div>` : '');
  const rowHtml = (s, it) => { const a = ans(s, it.id), ph = esc(hintOf(s, a.v));
    return `<li class="${cls(s, it, a)}" data-sec="${esc(s.id)}" data-id="${esc(it.id)}"><div class="rvlab">${labHtml(it)}</div>${rvButtons(s.scale, a.v)}
      ${s.note === 'line' ? `<input type="text" class="rvnote" value="${esc(a.note)}" placeholder="${ph}">` : `<textarea class="rvnote" rows="2" placeholder="${ph}">${esc(a.note)}</textarea>`}<div class="rvx"></div></li>`; };
  const rowEl = (sid, id) => secEl[sid] && $$('.rvrow', secEl[sid]).find(r => r.dataset.id === String(id));
  const paint = (li, s, it) => {             // a row in place: its answer, colour and note - never the note being typed in
    const a = ans(s, it.id), n = $('.rvnote', li), lab = $('.rvlab', li), h = labHtml(it);
    li.className = cls(s, it, a);
    $$('.rvb', li).forEach(b => b.classList.toggle('on', b.dataset.v === a.v));
    if (n !== document.activeElement && n.value !== a.note) n.value = a.note;
    n.placeholder = hintOf(s, a.v);
    if (lab._h !== h) { lab.innerHTML = h; lab._h = h; }
  };
  const extraOn = () => {                    // the item's extra (e.g. the library tick) on the current row only
    $$('.rvx', host).forEach(x => { if (x.innerHTML) x.innerHTML = ''; });
    const li = cur && rowEl(cur.sec, cur.id);
    if (li && o.extra && o.extra.item) $('.rvx', li).innerHTML = o.extra.item(cur.sec, cur.id) || '';
  };
  const fill = s => {                        // a section's rows: the same items = painted in place (a click, the caret stay)
    const items = (s.items() || []).map(it => ({...it, id: String(it.id)})), ol = $('.rvrows', secEl[s.id]), have = $$('.rvrow', ol);
    lists[s.id] = items;
    if (have.length === items.length && have.every((li, i) => li.dataset.id === items[i].id)) { have.forEach((li, i) => paint(li, s, items[i])); return; }
    const f = document.activeElement, keep = f && f.classList.contains('rvnote') && ol.contains(f)
      ? {id: f.closest('.rvrow').dataset.id, a: f.selectionStart, b: f.selectionEnd} : null;
    ol.innerHTML = items.map(it => rowHtml(s, it)).join('') || `<li class="rvempty small muted">${esc(s.empty || t('Nothing here.'))}</li>`;
    if (cur && cur.sec === s.id) extraOn();
    const li = keep && rowEl(s.id, keep.id), n = li && $('.rvnote', li);
    if (n) { n.focus({preventScroll: true}); try { n.setSelectionRange(keep.a, keep.b); } catch (e) { /* not a text field */ } }
  };
  const flat = () => secs.flatMap(s => (lists[s.id] || []).map(it => ({s, it})));
  const redraw = () => {
    if (gone) return;
    secs.forEach(fill);
    let n = 0, m = 0, on = 0, om = 0, any = false;
    secs.forEach(s => ((s.all ? s.all() : lists[s.id]) || []).forEach(it => { const a = ans(s, String(it.id));
      if (a.v || a.note.trim()) any = true;
      if (it.optional) { om++; if (a.v) on++; } else { m++; if (a.v) n++; } }));
    const done = m > 0 && n >= m, pg = $('.rvp-prog', host), sl = typeof o.stale === 'function' ? o.stale() : o.stale, se = $('.rvp-stale', host);
    pg.hidden = !m && !om;
    pg.innerHTML = m ? `<span>${done ? `<b class="ok">${m === 1 ? t('Reviewed') : t('All {m} reviewed', {m})} ✓</b>` : t('<b>{n}</b> of {m} reviewed', {n, m})}${om ? `<span class="dim"> · ${t('{on} of {om} optional', {on, om})}</span>` : ''}</span>
      <div class="bar"><i style="width:${Math.round(100 * n / m)}%"></i></div>` : `<span>${t('{on} of {om} answered', {on, om})} <span class="dim">${t('(optional)')}</span></span>`;
    se.hidden = !sl; se.textContent = sl || '';
    if (o.send) {
      const b = $('.rvsendb', host), ok = o.send.ready ? !!o.send.ready() : any;
      if (!b.dataset.busy) b.disabled = !ok;
      b.title = ok ? '' : t('Give one answer first');
      $('.rvsend', host).classList.toggle('ready', ok && (o.send.glow ? !!o.send.glow() : done));
      if (typeof o.send.hint === 'function') $('.rvsend-h', host).innerHTML = o.send.hint() || '';   // 0.5.3: live
    }
    const L = flat(); $$('[data-rvgo]', host).forEach(b => { b.disabled = !L.length; });
  };
  const scrollRow = li => {                  // the rows scroll inside the panel - never the page
    const box = $('.rvp-body', host);
    if (box && li && (li.offsetTop < box.scrollTop || li.offsetTop + li.offsetHeight > box.scrollTop + box.clientHeight)) box.scrollTop = Math.max(0, li.offsetTop - 40);
  };
  const setCur = (sid, id) => {              // the current row (onMove is the caller's: move() or the place itself)
    const f = document.activeElement;
    if (f && f.classList.contains('rvnote') && host.contains(f)) { const li = f.closest('.rvrow'); if (!(li.dataset.sec === sid && li.dataset.id === String(id))) f.blur(); }
    const old = cur; cur = sid == null || !byId[sid] ? null : {sec: sid, id: String(id)};
    [old, cur].forEach(c => { if (!c) return; const li = rowEl(c.sec, c.id), it = (lists[c.sec] || []).find(x => x.id === c.id); if (li && it) paint(li, byId[c.sec], it); });
    extraOn();
    if (cur) scrollRow(rowEl(cur.sec, cur.id));
  };
  const move = (sid, id, first = false) => { setCur(sid, id); if (o.onMove) o.onMove(sid, sid == null ? null : String(id), first); };
  const at = () => { const L = flat(); return [L, cur ? L.findIndex(x => x.s.id === cur.sec && x.it.id === cur.id) : -1]; };
  const next = d => {
    const [L, i] = at(); if (!L.length) return;
    if (d > 0 && i === L.length - 1) { if (o.onEnd) o.onEnd(); return; }
    const j = i < 0 ? (d > 0 ? 0 : L.length - 1) : clamp(i + d, 0, L.length - 1);
    if (j !== i) move(L[j].s.id, L[j].it.id);
  };
  const open1 = (L, i) => [...L.slice(i + 1), ...L.slice(0, Math.max(0, i))].find(y => !y.it.optional && !ans(y.s, y.it.id).v);
  const nextOpen = () => { const [L, i] = at(), x = open1(L, i); if (x) move(x.s.id, x.it.id); else if (o.onEnd) o.onEnd(); };
  const focusNote = () => { const li = cur && rowEl(cur.sec, cur.id), n = li && $('.rvnote', li); if (n) { n.focus({preventScroll: true}); scrollRow(li); } };
  const save = (s, id, a) => {               // the place's own save; the header says saving… / saved ✓ / NOT saved
    busy++; st(t('saving…'));
    let r; try { r = s.set(id, a); } catch (e) { r = Promise.reject(e); }
    return Promise.resolve(r).then(x => { if (x === false) failed = true; }, e => { failed = true; toast(t('Not saved: {err}', {err: e.message}), 'err'); })
      .finally(() => { if (--busy || gone) return; st(failed ? t('NOT saved') : t('saved ✓'), failed ? 'bad' : 'ok'); failed = false; });
  };
  const answer = (sid, id, v) => {
    const s = byId[sid]; if (!s) return;
    id = String(id);
    if (!isCur(sid, id)) move(sid, id);
    const k = K(sid, id), p = pend.get(k), a = ans(s, id), nv = a.v === v ? '' : v, tone = rvTone(s.scale, nv);
    if (p) { clearTimeout(p.t); pend.delete(k); }
    save(s, id, {v: nv, note: a.note});
    redraw();
    if (tone === 'pos' && auto && o.autoNext !== false) next(1);
    else if (tone === 'mid' || tone === 'neg' || (tone === 'ans' && nv !== 'none')) focusNote();
  };
  const flushOne = k => { const p = pend.get(k); if (!p) return null; clearTimeout(p.t); pend.delete(k);
    const a = p.s.get(p.id) || {}; return save(p.s, p.id, {v: a.v || '', note: p.text}); };
  const flush = () => Promise.all([...pend.keys()].map(flushOne));
  const noteInput = n => {                   // saved as you type (450 ms after the last key) and when the note is left
    const li = n.closest('.rvrow'), s = byId[li.dataset.sec], k = K(s.id, li.dataset.id), p = pend.get(k);
    if (p) clearTimeout(p.t);
    pend.set(k, {s, id: li.dataset.id, text: n.value, t: setTimeout(() => flushOne(k), 450)});
    st('…');
  };
  const sendNow = async () => {
    const b = $('.rvsendb', host); if (!b || b.disabled) return;
    b.disabled = true; b.dataset.busy = '1';
    try { await flush(); if (o.send.go) await o.send.go(); if (o.send.cmd) await openClaude(o.send.cmd, o.send.task || 'free', o.send.name || ''); }
    catch (e) { toast(e.message, 'err'); }
    finally { delete b.dataset.busy; if (!gone) redraw(); }
  };
  host.addEventListener('mousedown', e => { if (e.target.closest('.rvb, [data-rvgo]')) e.preventDefault(); });   // Space stays with the page
  host.addEventListener('click', e => {
    const b = e.target.closest('.rvb');
    if (b) { const li = b.closest('.rvrow'); if (li) answer(li.dataset.sec, li.dataset.id, b.dataset.v); return; }
    const g = e.target.closest('[data-rvgo]');
    if (g) { if (g.dataset.rvgo === 'open') nextOpen(); else next(+g.dataset.rvgo); return; }
    if (e.target.closest('.rvsendb')) { sendNow(); return; }
    const li = e.target.closest('.rvrow');
    if (!li || e.target.closest('.rvnote, .rvx, a, button, input, select, label')) return;
    if (!isCur(li.dataset.sec, li.dataset.id)) move(li.dataset.sec, li.dataset.id); else if (o.deselect) move(null, null);
  });
  host.addEventListener('focusin', e => { const n = e.target, li = n.classList && n.classList.contains('rvnote') && n.closest('.rvrow');
    if (li && !isCur(li.dataset.sec, li.dataset.id)) move(li.dataset.sec, li.dataset.id); });
  host.addEventListener('input', e => { if (e.target.classList && e.target.classList.contains('rvnote')) noteInput(e.target); });
  host.addEventListener('focusout', e => { const n = e.target, li = n.classList && n.classList.contains('rvnote') && n.closest('.rvrow');
    if (li) flushOne(K(li.dataset.sec, li.dataset.id)); });
  const ac = $('.rvauto input', host);
  if (ac) ac.onchange = () => { auto = ac.checked; try { localStorage.setItem('ml.autoNext', auto ? '1' : '0'); } catch (e) { /* private window */ } };
  const keys = e => {                        // true = handled (the document's keydown stops there)
    const el = e.target && e.target.nodeType === 1 ? e.target : null;
    if (el && el.classList.contains('rvnote') && host.contains(el)) {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); el.blur(); next(1); return true; }   // save + next
      if (e.key === 'Escape' || (e.key === 'Enter' && el.tagName === 'INPUT')) { e.preventDefault(); el.blur(); return true; }
      return false;
    }
    // typing in another field keeps its keys; a tick or a button that has the focus does not
    if ((el && el.closest('textarea, select, [contenteditable], input:not([type=checkbox]):not([type=radio]):not([type=button]):not([type=range])'))
      || e.ctrlKey || e.metaKey || e.altKey) return false;
    const k = (e.key || '').toLowerCase();
    if (k === 'j') next(-1); else if (k === 'k') next(1); else if (k === 'n') nextOpen();
    else if (/^[1-9]$/.test(k)) {
      if (!cur) { const [L] = at(), x = open1(L, -1) || L[0]; if (x) move(x.s.id, x.it.id); }    // first show which one
      else { const sc = SCALES[byId[cur.sec].scale] || []; if (+k > sc.length) return false; answer(cur.sec, cur.id, sc[+k - 1][0]); }
    } else return false;
    e.preventDefault(); return true;
  };
  const self = {el: host, dialog: !!o.dialog, keys, redraw, next, nextOpen, focusNote, flush, select: setCur, cur: () => cur && {...cur},
    saving: () => st(t('saving…')), saved: ok => st(ok ? t('saved ✓') : t('NOT saved'), ok ? 'ok' : 'bad'),
    alive: () => !gone && host.isConnected && host.offsetParent !== null,
    destroy: () => { if (gone) return; flush(); gone = true; RV_LIVE = RV_LIVE.filter(x => x !== self); }};
  RV_LIVE.push(self);
  if (!o.dialog) onCleanup(self.destroy);
  redraw();
  const L0 = flat(), x0 = o.start && typeof o.start === 'object' ? {s: byId[o.start.sec], it: {id: String(o.start.id)}} : o.start ? open1(L0, -1) || L0[0] : null;
  if (x0 && x0.s) move(x0.s.id, x0.it.id, true);
  return self;
}
// the panel on screen gets the keys first (1 2 3, J K N, its note's Ctrl+Enter / Esc); a dialog's panel inside its
// dialog - never under the teleprompter (its own keys) or the lightbox (handled before)
const rvKey = (e, inModal) => {
  RV_LIVE = RV_LIVE.filter(p => p.el.isConnected);
  if ($('.tprompt')) return false;
  const p = RV_LIVE.slice().reverse().find(x => x.dialog === inModal && x.alive());
  return !!p && p.keys(e);
};
const chip = fam => `<span class="chip"><i class="sw" style="background:${FAM[fam] || '#888'}"></i>${esc(t(fam ?? ''))}</span>`;

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
  const inModal = !$('#modal').hidden;
  if (rvKey(e, inModal)) return;                         // a review panel (reviewPanel): its keys first
  if (e.key === 'Escape' && inModal) { dismissModal(); return; }
  if (KEYS && !inModal) KEYS(e);
});
document.addEventListener('click', e => {
  const o = e.target.closest('[data-open]');
  if (o) { e.preventDefault(); openPath(o.dataset.open, o.hasAttribute('data-reveal')); }
});

// ---- the NEW badge (2026-10-24, a friend's ask: "a red NEW, top left, on everything new"): GET /api/seen = per
// section of the sidebar when the user last left it + the cards clicked since (.app\seen.json - every window agrees).
// A card is new when its own time (a render finished, a script saved, an analysis done) is after that and it was not
// clicked; leaving the section clears them all (route), a click clears one. Keys carry the card's time: a reused id
// (script-014 deleted, then a new script-014) is a new card. The Editor's videos count a finished render only.
let SEEN = {}, SEEN_P = null;
const NEW_SECTIONS = ['analyze', 'edit', 'generate', 'prepare', 'motion', 'memory'];
const pkey = p => `${p.id}@${Math.round(p.created || 0)}`;          // a prompt / script / title: its id + when it was saved
const isNew = (key, when, sec = document.body.dataset.page) => { const s = NEW_SECTIONS.includes(sec) && SEEN[sec];
  return !!(s && when && when > s.at && !(s.clicked || []).includes(key)); };
const newTag = (key, when, sec = document.body.dataset.page) => isNew(key, when, sec)
  ? `<span class="newtag" data-newsec="${esc(sec)}" data-newkey="${esc(key)}">${t('NEW')}</span>` : '';
const loadSeen = async () => { try { if (SEEN_P) await SEEN_P; SEEN = await api('/api/seen'); } catch (e) { /* no badges */ } };
document.addEventListener('click', e => {                 // a click on a NEW card: that card is seen
  const card = e.target.closest(':has(> .newtag)'), b = card && card.querySelector(':scope > .newtag');
  if (!b) return;
  b.remove();
  api('/api/seen', {section: b.dataset.newsec, key: b.dataset.newkey}).then(r => { SEEN = r; }).catch(() => {});
}, true);

// the pages (0.4: Analyze / Edit - shown as Editor since 2026-10-15, #/edit stays - / Generate / Claude's memory); a 0.3
// address is rewritten to its new name
const ALIASES = {'#/refs': '#/analyze', '#/analyser': '#/analyze', '#/generator': '#/generate', '#/projects': '#/edit', '#/editor': '#/edit', '#/knowledge': '#/memory/shared', '#/library': '#/memory',
                 '#/memory/learned': '#/memory/shared'};     // 2026-10-18: Share with friends -> Shared knowledge
const PAGES = [
  [/^#?\/?$/, pageHome, 'home'], [/^#\/analyze(?:\/(videos|thumbs|texts))?$/, pageRefs, 'analyze'],
  [/^#\/texts\/([^/?]+)$/, pageTexts, 'analyze'],
  [/^#\/ref\/([^/?]+)(?:\?(?:e=(\w+)|(misses)|(verdicts)))?$/, pageRef, 'analyze'], [/^#\/edit$/, pageProjects, 'edit'],
  [/^#\/thumbs\/([^/?]+)$/, pageThumbs, 'analyze'],
  [/^#\/project\/([^/]+)(?:\/(\w+))?$/, pageProject, 'edit'], [/^#\/prepare$/, pagePrepare, 'prepare'],
  [/^#\/generate$/, pageGenerate, 'generate'], [/^#\/motion(?:\/(\w+))?(?:\/([\w-]+))?$/, pageMotion, 'motion'],
  [/^#\/prompts(?:\/([\w-]+))?$/, pagePrompts, 'generate'], [/^#\/memory(?:\/(\w+))?$/, pageMemory, 'memory'],
  [/^#\/jobs(?:\/(\d+))?$/, pageJobs, 'jobs'], [/^#\/storage$/, pageStorage, 'settings'],
  [/^#\/settings$/, pageSettings, 'settings'], [/^#\/skills$/, pageSkills, 'settings']];
// soft = the same page drawn again with what changed (liveTick): no "Loading…", the scroll and typed search words kept
async function route(soft) {
  soft = soft === true;
  const main = $('#main'), y = main.scrollTop;
  const keep = soft ? $$('input[id], textarea[id], select[id]', main).filter(x => !['file', 'checkbox', 'radio'].includes(x.type)).map(x => [x.id, x.value]) : [];
  CLEAN.forEach(f => { try { f(); } catch (e) { /* ignore */ } }); CLEAN = []; KEYS = null; hideTip();
  let h = location.hash || '#/';
  if (ALIASES[h]) { h = ALIASES[h]; history.replaceState(null, '', h); }
  for (const [rx, fn, nav] of PAGES) {
    const m = h.match(rx);
    if (!m) continue;
    const prev = document.body.dataset.page;
    if (!soft && prev && prev !== nav && NEW_SECTIONS.includes(prev))           // left a section: its NEW badges go
      SEEN_P = api('/api/seen', {section: prev, leave: true}).then(r => { SEEN = r; }).catch(() => {});
    $$('#side a[data-nav]').forEach(a => a.classList.toggle('on', a.dataset.nav === nav));
    document.body.dataset.page = nav;                         // the section's accent colour (app.css)
    if (!soft) { main.scrollTop = 0; main.innerHTML = `<div class="loading">${t('Loading…')}</div>`; liveBase(h); }
    try { await loadSeen(); await fn(main, ...m.slice(1).map(x => x && decodeURIComponent(x))); }
    catch (e) { main.innerHTML = `<div class="empty">${t('This page could not load: {err}', {err: esc(e.message)})}</div>`; }
    if (soft) {
      keep.forEach(([id, v]) => { const x = document.getElementById(id);
        if (x && main.contains(x) && x.value !== v) { x.value = v; x.dispatchEvent(new Event('input', {bubbles: true})); } });
      main.scrollTop = y;
    }
    return;
  }
  location.hash = '#/';
}
window.addEventListener('hashchange', () => route());

// ---- pages that update by themselves (2026-10-24, a friend's ask: "what is created shows up without going to another
// section and back"): every 5 s a list page asks GET /api/changes?s=<its data> (directory listings and file times on
// the server - live.py) and draws itself again when that changed. Never while a dialog, the lightbox or the
// teleprompter is open, while the user types or a video plays with sound: it waits until then. A page of ONE thing
// (a video, an analysis, a set) is never redrawn by itself.
const LIVE_PAGES = [[/^#?\/?$/, 'home'], [/^#\/analyze(?:\/(?:videos|thumbs|texts))?$/, 'analyze'], [/^#\/edit$/, 'projects'],
  [/^#\/generate$/, 'generate'], [/^#\/prepare$/, 'prompts'], [/^#\/prompts$/, 'prompts'], [/^#\/motion(?:\/(?:learned|logos))?$/, 'motion'],
  [/^#\/memory(?:\/\w+)?$/, 'memory']];
const LV = {hash: '', sig: null, due: false, busy: false};
const liveOf = h => (LIVE_PAGES.find(([rx]) => rx.test(h)) || [])[1];
function liveBase(h) {                                     // the page as drawn now = the fingerprint to compare with
  LV.hash = h; LV.sig = null; LV.due = false;
  const s = liveOf(h);
  if (s) api('/api/changes?s=' + s).then(r => { if (LV.hash === h && LV.sig === null) LV.sig = r.sig; }).catch(() => {});
}
function userBusy() {
  const a = document.activeElement;
  return !$('#modal').hidden || !$('#lightbox').hidden || !!$('.tprompt, .yttest') || !!$('#main .nerm, #main .lgpop')
    || !!(a && (a.isContentEditable || (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) && !['checkbox', 'radio', 'button', 'file'].includes(a.type))))
    || $$('#main video').some(v => !v.paused && !v.muted);
}
async function liveTick() {
  if (RELOADING || document.hidden || LV.busy) return;
  const h = location.hash || '#/', s = liveOf(h);
  if (!s || LV.hash !== h) return;
  LV.busy = true;
  try {
    const r = await api('/api/changes?s=' + s);
    if (LV.hash === h) {
      if (LV.sig === null) LV.sig = r.sig;
      else if (r.sig !== LV.sig) { LV.sig = r.sig; LV.due = true; }
      if (LV.due && !userBusy() && (location.hash || '#/') === h) { LV.due = false; await route(true); }
    }
  } catch (e) { /* the next tick */ }
  LV.busy = false;
}
setInterval(liveTick, 5000);

// heartbeat: keeps the server alive while the window is open; shows jobs + Resolve; notices updates / restarts
const PAGE_VERSION = (document.querySelector('meta[name=ml-version]') || {}).content || '';
const API_LEVEL = 32;            // the server functions this page needs (server.API_LEVEL)
let RELOADING = false;
window.addEventListener('unhandledrejection', e => toast(t('Something went wrong: {err}', {err: (e.reason && e.reason.message) || e.reason}), 'err'));
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
  overlay(t('MotionLab did not come back by itself. Close this window and start MotionLab again.'));
}
async function restartApp() {
  try { await api('/api/restart', {}); }
  catch (e) {
    toast(/not found|404/i.test(e.message) ? t('This MotionLab is too old to restart itself: close every MotionLab window and start it again (MotionLab.bat or the shortcut)') : e.message, 'err');
    return;
  }
  waitForServer(t('Restarting MotionLab…'));
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
    if (p.phase === 'updating' || p.phase === 'restarting') { waitForServer(p.phase === 'updating' ? t('Updating MotionLab from GitHub…') : t('Restarting MotionLab…')); return; }
    if ((p.api || 1) < API_LEVEL) banner('oldsrv', `${t('MotionLab was updated but its server is still the old one.')} <button class="btn sm pri">${t('Restart now')}</button>`, restartApp);
    else if (PAGE_VERSION && p.version !== PAGE_VERSION) { location.reload(); return; }
    sideUpdate(p);
    liveLine(p.claude || []);
    $('#jobcount').textContent = p.running || '';
    const st = (p.resolve || {}).state || '…';
    const d = $('#resolve-state .dot');
    d.className = 'dot ' + (st === 'running' ? 'running' : st === 'not responding' ? 'bad' : '');
    $('#resolve-state span').textContent = t(st);
    const gone = $('#gone'); if (gone) gone.remove();
  } catch (e) {
    $('#resolve-state span').textContent = t('app server stopped');
    if (!$('#gone')) {
      const b = document.createElement('div'); b.id = 'gone'; b.className = 'toast err';
      b.style.cssText = 'position:fixed;left:50%;top:14px;transform:translateX(-50%);z-index:90;max-width:640px';
      b.textContent = t('The MotionLab server has stopped (the PC slept or it was closed). Close this window and double-click MotionLab.bat again - your verdicts are saved.');
      document.body.append(b);
    }
  }
}
setInterval(ping, 4000); ping();
window.addEventListener('pagehide', () => navigator.sendBeacon('/api/bye', JSON.stringify({token: TOKEN})));

async function startJob(kind, args, follow = true) {
  try {
    const j = await api('/api/jobs', {kind, args});
    toast(t('Started: {title}', {title: j.title})); ping();
    if (follow) location.hash = '#/jobs/' + j.id;
    return j;
  } catch (e) { toast(e.message, 'err'); return null; }
}
function followJob(id, pre, onDone, onStatus) {     // onStatus(job): a waiting job starts, a running one stops
  let since = 0, stop = false, last = '';
  const tick = async () => {
    if (stop) return;
    try {
      const j = await api(`/api/jobs/${id}?since=${since}`);
      if (j.log.length) {
        const atEnd = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 30;
        pre.textContent += j.log.join('\n') + '\n'; since += j.log.length;
        if (atEnd) pre.scrollTop = pre.scrollHeight;
      }
      if (j.status !== last) { last = j.status; if (onStatus) onStatus(j); }
      if (['running', 'cancelling', 'queued'].includes(j.status)) setTimeout(tick, j.status === 'queued' ? 1500 : 700);
      else { ping(); if (onDone) onDone(j); }
    } catch (e) { setTimeout(tick, 2000); }
  };
  tick(); onCleanup(() => { stop = true; });
}

// ============================================================================================ report a problem
// 0.4.2.1: the scrubbed report first (what happened, versions, the log's last lines), then GitHub's new-issue page
// in the browser - the user reads it there and presses Submit; nothing is sent by MotionLab
const reportBtn = (job = '', cls = 'sm') => `<button class="btn ${cls}" data-report="${esc(job)}" title="${ta('Opens a GitHub issue filled in for you - you read it and send it')}">${t('Report a problem…')}</button>`;
async function reportModal(job = '') {
  let R;
  try { R = await api('/api/report' + (job ? '?job=' + encodeURIComponent(job) : '')); } catch (e) { toast(e.message, 'err'); return; }
  modal(`<h2>${t('Report a problem')}</h2>
    <p class="hint">${t('This is the whole report. Your name, your folders and e-mail addresses are taken out. Nothing is sent from MotionLab: {how}', {how: R.repo
      ? t('GitHub opens with it filled in - read it there, then press <b>Submit</b> yourself (you need a GitHub account).')
      : t('this copy is not connected to GitHub - copy the report and send it to whoever shared MotionLab with you.')})}</p>
    <label class="small" for="rpn">${t('What were you doing? (optional)')}</label>
    <textarea id="rpn" rows="2" placeholder="${ta('e.g. I pasted a TikTok link and pressed Download')}"></textarea>
    <pre class="log rpbody" id="rpb"></pre><div class="small muted" id="rpt"></div>
    <div class="row" style="margin-top:10px">${R.repo ? `<button class="btn pri" id="rpo">${t('Open on GitHub')}</button>` : ''}<button class="btn${R.repo ? '' : ' pri'}" id="rpc">${t('Copy the report')}</button></div>`, el => {
    const show = r => {
      R = r; $('#rpb', el).textContent = `${r.title}\n\n${r.body}`;
      $('#rpt', el).textContent = r.dropped ? t("GitHub's link has room for the last {n} of {total} log lines; Copy the report has all of them.", {n: r.lines - r.dropped, total: r.lines}) : '';
    };
    show(R);
    const note = () => $('#rpn', el).value;
    $('#rpn', el).oninput = debounce(async () => { try { show(await api('/api/report', {job: R.job, note: note()})); } catch (e) { /* keep */ } }, 500);
    $('#rpc', el).onclick = async () => { try { show(await api('/api/report', {job: R.job, note: note()})); } catch (e) { /* the shown one */ } copy(`${R.title}\n\n${R.body}`); };
    const o = $('#rpo', el); if (o) o.onclick = async () => {
      try { const r = await api('/api/report', {job: R.job, note: note(), open: true}); show(r); toast(t('GitHub opened in your browser: read the report, then press Submit'), 'ok'); }
      catch (e) { toast(e.message, 'err'); }
    };
  });
}
document.addEventListener('click', e => {
  const r = e.target.closest('[data-report]');
  if (r) { e.preventDefault(); e.stopPropagation(); reportModal(r.dataset.report); }
});

// ============================================================================================ player
// 0.4.2.1: HEVC (TikTok's best format) plays only where Windows has the HEVC Video Extension, AV1 / ProRes / MPEG-2
// often not at all: such a video gets a small H.264 copy for the player (job player_copy, .app\player\; the same
// frames at the same times, so frame numbers still match). The address ?player=copy forces it (tests on a PC that
// has the extension).
const FORCE_COPY = new URLSearchParams(location.search).get('player') === 'copy';
const CODEC_TYPE = {h264: 'avc1.640028', hevc: 'hvc1.1.6.L120.90', av1: 'av01.0.08M.08', vp9: 'vp09.00.40.08'};
const codecWord = c => ({hevc: 'HEVC', av1: 'AV1', h264: 'H.264', vp9: 'VP9', prores: 'ProRes', mpeg2video: 'MPEG-2'})[c] || (c ? String(c).toUpperCase() : '');
function browserPlays(c) {                            // c = /api/player: the codec ffprobe found (+ its tag)
  if (c.codec === 'vp8') return true;
  const k = CODEC_TYPE[c.codec];
  if (!k) return false;                               // ProRes, DNxHD, MPEG-2, old MPEG-4: no browser plays them
  const t = `video/mp4; codecs="${c.codec === 'hevc' && c.tag === 'hev1' ? k.replace('hvc1', 'hev1') : k}"`;
  return document.createElement('video').canPlayType(t) !== '' && (!window.MediaSource || MediaSource.isTypeSupported(t));
}
class Player {
  /* frame-accurate video: the shown frame comes from requestVideoFrameCallback (presented media time).
     0.4.3.5 (the user: "the controls are on the left, it's very hard to click play/pause and also to move to a specific
     point"): a click on the picture = play / pause (a big ▶ before the first play), a seek bar as wide as the video
     (drag it; the pointer shows the frame + timecode), the transport in the middle like an editor's viewer, the length,
     sound and full screen; keys when the player has the focus: Space, ← → (Shift = 10), Home / End, M, F */
  constructor(el, src, fps, frames, label = '') {
    this.fps = fps; this.N = frames || 1e9; this.frame = 0; this._range = null; this.fns = []; this.looping = false;
    const nf = 'tabindex="-1"';                              // the buttons never take the focus: the keys stay with the player
    el.innerHTML = `<div class="player" tabindex="0"><div class="pview"><video preload="auto" playsinline src="${fileUrl(src)}"></video>
        <span class="pflash" aria-hidden="true"></span><button class="pbig" data-a="play" ${nf} aria-label="${ta('Play')}">▶</button></div>
      <div class="pscrub" title="${ta('Click or drag to move')}"><div class="pstrack"><i class="psrange" hidden></i><i class="psfill"></i><i class="pshead"></i></div><span class="pstip" hidden></span></div>
      <div class="pbar">
        <div class="pbl"><span class="now">f0<span class="tc">00:00:00:00</span></span><span class="ptot"></span>${label ? `<span class="hint">${esc(label)}</span>` : ''}</div>
        <div class="pbc">
          <button class="btn" data-a="start" ${nf} title="${ta('First frame (Home)')}">⏮</button>
          <button class="btn" data-a="-10" ${nf} title="${ta('10 frames back (Shift+←)')}">−10</button>
          <button class="btn" data-a="-1" ${nf} title="${ta('1 frame back (←)')}">−1</button>
          <button class="btn pplay" data-a="play" ${nf} title="${ta('Play / pause (Space, or click the picture)')}">▶</button>
          <button class="btn" data-a="1" ${nf} title="${ta('1 frame on (→)')}">+1</button>
          <button class="btn" data-a="10" ${nf} title="${ta('10 frames on (Shift+→)')}">+10</button></div>
        <div class="pbr">
          <span class="prates" title="${ta('Speed')}"><button class="btn rate" data-r="0.25" ${nf}>¼</button><button class="btn rate" data-r="0.5" ${nf}>½</button><button class="btn rate on" data-r="1" ${nf}>1×</button></span>
          <button class="btn ptog" data-t="loop" ${nf} title="${ta('Repeat - the selected part, else the whole video')}">⟳</button>
          <button class="btn ptog" data-t="mute" ${nf} title="${ta('Sound on / off (M)')}">🔊</button>
          <button class="btn" data-t="full" ${nf} title="${ta('Full screen (F)')}">⛶</button></div></div>
      <div class="pnote small" hidden></div></div>`;
    this.root = $('.player', el); this.v = $('video', el); this.now = $('.now', el); this.pb = $('.pplay', el); this.tot = $('.ptot', el);
    this.src = src; this.note = $('.pnote', el); this.fill = $('.psfill', el); this.head = $('.pshead', el); this.rng = $('.psrange', el);
    this.fl = $('.pflash', el);
    $$('button', this.root).forEach(b => b.addEventListener('mousedown', e => e.preventDefault()));   // keep the focus
    $$('[data-a]', el).forEach(b => b.addEventListener('click', () => {
      const a = b.dataset.a;
      if (a === 'play') this.toggle(); else if (a === 'start') this.seek(0); else this.step(+a);
      this.root.focus({preventScroll: true});
    }));
    $$('[data-r]', el).forEach(b => b.addEventListener('click', () => {
      this.v.playbackRate = +b.dataset.r; $$('[data-r]', el).forEach(x => x.classList.toggle('on', x === b));
    }));
    $$('[data-t]', el).forEach(b => b.addEventListener('click', () => {
      const w = b.dataset.t;
      if (w === 'loop') this.setLoop(!this.looping); else if (w === 'mute') this.mute(); else this.full();
    }));
    this.v.addEventListener('click', () => { const go = this.v.paused; this.toggle(); this.flash(go ? '▶' : '❚❚'); this.root.focus({preventScroll: true}); });
    this.v.addEventListener('dblclick', () => this.full());
    this.v.addEventListener('play', () => { this.pb.textContent = '❚❚'; this.root.classList.add('playing', 'started'); });
    this.v.addEventListener('pause', () => { this.pb.textContent = '▶'; this.root.classList.remove('playing'); });
    this.v.addEventListener('ended', () => { if (this.looping) { this.seek(this._range ? this._range[0] : 0); this.v.play().catch(() => {}); } });
    this.v.addEventListener('loadedmetadata', () => { const T = this.total(); this.tot.textContent = T > 1 ? ` / ${tc(T - 1, this.fps)}` : ''; this.show(); this.paintRange(); });
    this.root.addEventListener('keydown', e => {
      if (e.target.matches('input, textarea, select')) return;
      const k = e.key;
      if (k === ' ') this.toggle();
      else if (k === 'ArrowLeft' || k === 'ArrowRight') this.step((k === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? 10 : 1));
      else if (k === 'Home') this.seek(0);
      else if (k === 'End') { this.v.pause(); this.seek(this.total() - 1); }
      else if (k === 'm' || k === 'M') this.mute();
      else if (k === 'f' || k === 'F') this.full();
      else return;                                          // other keys go on to the page (the analysis page's J K N 1 2 3)
      e.preventDefault(); e.stopPropagation();
    });
    // the seek bar: a click or a drag moves to that frame (the video waits while dragging), the pointer shows where
    const sc = $('.pscrub', el), tip = $('.pstip', el);
    const fAt = e => { const r = sc.getBoundingClientRect(), T = this.total();
      return clamp(Math.round((e.clientX - r.left) / Math.max(1, r.width) * (T - 1)), 0, T - 1); };
    let drag = false, was = false;
    sc.addEventListener('pointerdown', e => {
      if (e.button) return;
      drag = true; was = !this.v.paused; this.v.pause(); sc.setPointerCapture(e.pointerId); sc.classList.add('drag');
      this.seek(fAt(e)); this.root.focus({preventScroll: true});
    });
    sc.addEventListener('pointermove', e => {
      const f = fAt(e), r = sc.getBoundingClientRect();
      tip.hidden = false; tip.style.left = `${clamp(e.clientX - r.left, 46, r.width - 46)}px`;
      tip.innerHTML = `f${f}<span class="tc">${tc(f, this.fps)}</span>`;
      if (drag) this.seekSoon(f);
    });
    const end = () => { if (!drag) return; drag = false; sc.classList.remove('drag'); if (was) this.v.play().catch(() => {}); };
    sc.addEventListener('pointerup', end); sc.addEventListener('pointercancel', end);
    sc.addEventListener('pointerleave', () => { if (!drag) tip.hidden = true; });
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
      if (this._range && this.looping && !this.v.paused && f >= this._range[1]) this.seek(this._range[0]);
      this.vfc = this.v.requestVideoFrameCallback(cb);
    };
    if ('requestVideoFrameCallback' in HTMLVideoElement.prototype) this.vfc = this.v.requestVideoFrameCallback(cb);
    else this.v.addEventListener('timeupdate', () => { this.frame = Math.floor(this.v.currentTime * this.fps + 1e-3); this.show(); this.emit(); });
    // 0.4.2.1: a format this browser cannot play -> a copy for the player only (the codec check, the error event,
    // a video that loads without a picture)
    this.v.addEventListener('error', () => this.needCopy());
    this.v.addEventListener('loadedmetadata', () => { if (!this.v.videoWidth && !this.copied) this.needCopy(); });
    this.checkCodec();
    onCleanup(() => { this.gone = true; this.v.pause(); this.v.removeAttribute('src'); this.v.load(); });
  }
  say(html, cls = '') { this.note.className = 'pnote small ' + cls; this.note.innerHTML = html; this.note.hidden = !html; }
  async checkCodec() {
    let c;
    try { c = await api('/api/player?path=' + encodeURIComponent(this.src)); } catch (e) { return; }
    if (this.gone) return;
    const cannot = FORCE_COPY || (c.codec && !browserPlays(c));
    if (c.copy && cannot) this.useCopy(c.copy, c);
    else if (cannot) this.needCopy(c);
  }
  async needCopy(c = null) {                           // make (or wait for) the copy, then switch to it
    if (this.copying || this.copied || this.gone) return;
    this.copying = true;
    let r;
    try { r = await api('/api/player/copy', {path: this.src}); }
    catch (e) { this.say(t('This video does not play on this PC, and a playable copy could not be started: {err}', {err: esc(e.message)}), 'bad'); return; }
    if (r.copy) { this.useCopy(r.copy, r); return; }
    const fmt = codecWord(r.codec || (c || {}).codec);
    this.say(fmt ? t('<b>This video\'s format ({fmt}) does not play on this PC.</b> MotionLab is making a copy that does, for this player only - the frame numbers stay the same. <a href="#/jobs/{job}">progress</a>', {fmt: esc(fmt), job: r.job})
      : t('<b>This video\'s format does not play on this PC.</b> MotionLab is making a copy that does, for this player only - the frame numbers stay the same. <a href="#/jobs/{job}">progress</a>', {job: r.job}), 'amber');
    const tick = async () => {
      if (this.gone) return;
      let j; try { j = await api(`/api/jobs/${r.job}?since=999999`); } catch (e) { setTimeout(tick, 2000); return; }
      if (['running', 'queued', 'cancelling'].includes(j.status)) { setTimeout(tick, 1000); return; }
      if (j.status !== 'done') { this.say(`${t('The copy for the player could not be made.')} ${reportBtn(j.id)}`, 'bad'); this.copying = false; return; }
      try { const i = await api('/api/player?path=' + encodeURIComponent(this.src)); if (i.copy) this.useCopy(i.copy, i); } catch (e) { /* stays */ }
    };
    tick();
  }
  useCopy(rel, c) {
    this.copied = true; this.copying = false;
    const f = this.frame;                              // the same frame in the copy, once it has loaded
    this.pending = null;
    this.v.addEventListener('loadeddata', () => { if (f) this.v.currentTime = (f + 0.5) / this.fps; }, {once: true});
    this.v.src = fileUrl(rel);
    const fmt = codecWord(c && c.codec);
    this.say(fmt ? t('Playing a copy made for this PC (the original is {fmt}, which does not play here): same frames, same timing. The analysis uses the original.', {fmt: esc(fmt)})
      : t('Playing a copy made for this PC: same frames, same timing. The analysis uses the original.'), 'dim');
  }
  on(fn) { this.fns.push(fn); }
  emit() { this.fns.forEach(f => f(this.frame)); }
  show() {
    this.now.innerHTML = `f${this.frame}<span class="tc">${tc(this.frame, this.fps)}</span>`;
    const T = this.total(), p = T > 1 ? `${clamp(this.frame / (T - 1), 0, 1) * 100}%` : '0%';
    this.fill.style.width = p; this.head.style.left = p;
  }
  total() { return this.N < 1e9 ? this.N : Math.max(1, Math.round((this.v.duration || 0) * this.fps)); }   // frames
  get range() { return this._range; }
  set range(r) { this._range = r; this.paintRange(); }
  paintRange() {                                         // the selected part (an effect) marked on the seek bar
    const r = this._range, T = this.total();
    this.rng.hidden = !r || T < 2;
    if (!this.rng.hidden) { this.rng.style.left = `${r[0] / (T - 1) * 100}%`; this.rng.style.width = `${Math.max(0.4, (r[1] - r[0]) / (T - 1) * 100)}%`; }
  }
  setLoop(on) { this.looping = !!on; $('[data-t=loop]', this.root).classList.toggle('on', this.looping); }
  mute() { this.v.muted = !this.v.muted; const b = $('[data-t=mute]', this.root); b.textContent = this.v.muted ? '🔇' : '🔊'; b.classList.toggle('on', this.v.muted); }
  full() { if (document.fullscreenElement) document.exitFullscreen().catch(() => {}); else this.root.requestFullscreen().catch(() => {}); }
  flash(s) { const f = this.fl; f.textContent = s; f.classList.remove('go'); void f.offsetWidth; f.classList.add('go'); }
  seekSoon(f) {                                          // while dragging: one seek per screen frame
    this.want = f;
    if (!this.raf) this.raf = requestAnimationFrame(() => { this.raf = 0; this.seek(this.want); });
  }
  seek(f) {
    const T = this.total();                              // not loaded yet and no frame count: any frame waits for it
    f = clamp(Math.round(f), 0, (T > 1 ? T : this.N) - 1);
    if (this.v.readyState < 1) this.pending = f;        // not loaded yet: seek on loadedmetadata
    else this.v.currentTime = (f + 0.5) / this.fps;     // middle of frame f: the decoder shows exactly f
    if (f !== this.frame) { this.frame = f; this.show(); this.emit(); }
  }
  step(d) { this.v.pause(); this.seek(this.frame + d); }
  toggle() { if (this.v.paused) this.v.play().catch(() => {}); else this.v.pause(); }
  playRange(a, b) { this.range = [a, b]; this.seek(a); this.v.play().catch(() => {}); }   // range: the setter marks it
}

// ---- the analysis page's Content tab (0.3.5): what the video says (transcript, clickable frame + timecode) and how it
// performs (views against the channel's followers). tools\content.py writes both; they stay on this PC.
function contentTab(el, R, P) {
  el.dataset.done = '1';
  const C = R.content || {}, T = C.transcript, S = C.stats, fps = R.video.fps;
  const n = v => v == null ? '–' : numLoc(Number(v));
  const big = (v, l, hint = '') => `<div class="stat" title="${esc(hint)}"><div class="n">${v}</div><div class="l">${esc(l)}</div></div>`;
  const lang = esc(T && T.lang || '?');
  const kindW = !T ? '' : T.kind === 'auto'
    ? (T.word_timings ? t("the platform's automatic captions ({lang}), timed per word", {lang}) : t("the platform's automatic captions ({lang})", {lang}))
    : (T.word_timings ? t('uploaded subtitles ({lang}), timed per word', {lang}) : t('uploaded subtitles ({lang})', {lang}));
  el.innerHTML = `<div class="grid g2 cgrid"><div class="panel"><div class="row sp"><h2>${t('How it performs')}</h2>
      <button class="btn sm" data-cjob="content_stats">${S ? t('Update the numbers') : t('Get the numbers')}</button></div>
      ${S ? `<div class="row stats">${big(n(S.views), t('views'))}${big(S.outperformer != null ? numStr(S.outperformer) + '×' : '–', t('views ÷ followers'), t("the outperformer score: views against the channel's followers (above 1 = it reached beyond the channel)"))}
          ${big(n(S.views_per_day), t('views a day'), S.days_online ? t('over {n} days online', {n: S.days_online}) : '')}${big(n(S.likes), t('likes'))}${big(n(S.comments), t('comments'))}${big(n(S.followers), t('followers'))}</div>
        <div class="small muted" style="margin-top:8px">${esc(S.uploader || '')} · ${esc(S.platform || '')} · ${t('online since {date}', {date: esc(S.upload_date || '?')})} · ${t('numbers from {when}', {when: esc(S.fetched)})}${(S.history || []).length > 1 ? ` · ${t('{n} fetches kept', {n: S.history.length})}` : ''}</div>`
        : `<div class="muted small">${t("Not fetched yet: one quick request to the video's page (no download).")}</div>`}
      <pre class="log" hidden></pre></div>
    <div class="panel"><h2>${t('Coming soon')}</h2><div class="small muted">${t('The topics, the hook and the call to action, every shot described, the text on screen, and what ~10 videos on one subject have in common.')}</div></div></div>
    <div class="panel" style="margin-top:14px"><div class="row sp"><h2>${t('What it says')}</h2>
      <div class="row">${T ? `<input type="search" id="cq" placeholder="${ta('Search the words…')}" style="width:240px">` : ''}
        <button class="btn sm" data-cjob="content_transcript">${T ? t('Fetch again') : t('Get the transcript')}</button></div></div>
      ${T ? `<div class="small muted" style="margin-bottom:8px">${plural(T.lines.length, 'line')} · ${plural(T.words || 0, 'word')} · ${kindW} · ${t('fetched {when}', {when: esc(T.fetched || '')})} · ${t('click a line to see it in the player')}</div>
        <div class="tlines"><table class="t click"><tbody id="clines">${T.lines.map((l, i) => `<tr data-i="${i}" data-f="${l.start}"><td class="fr">f${l.start}</td><td class="tc">${tc(l.start, fps)}</td><td>${esc(l.text)}</td></tr>`).join('')}</tbody></table></div>`
        : `<div class="muted small">${t("No transcript yet: the platform's own subtitles are fetched in a few seconds, nothing is downloaded. Videos without subtitles cannot be read yet.")}</div>`}
      <pre class="log" hidden></pre></div>`;
  $$('[data-cjob]', el).forEach(b => b.onclick = async () => {
    const pre = b.closest('.panel').querySelector('pre.log');
    const j = await startJob(b.dataset.cjob, {name: R.name, again: !!T}, false);
    if (!j) return;
    b.disabled = true; pre.hidden = false; pre.textContent = '';
    followJob(j.id, pre, jj => {
      toast(`${jj.title}: ${t(jj.status)}`, jj.status === 'done' ? 'ok' : 'err');
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

// ---- one analysis > Overview (0.4): the rhythm, the content side (hook, talking, text) and / or the cinematic side
// (signature effects, transitions, camera, speed, colour) for the video's focus, Claude's breakdown, and Use it
const BD = [['hook', t('The hook (first 3 s)')], ['structure', t('Structure')], ['captions', t('Captions')], ['text_graphics', t('Text & graphics')],
  ['broll', t('B-roll')], ['sound', t('Sound')], ['cta', t('Call to action')], ['transitions', t('Transitions')], ['camera', t('Camera')],
  ['grade', t('Colour grade')], ['rhythm', t('Rhythm')], ['rebuild_tips', t('To make one like it')]];
const kvRow = (k, v) => v == null || v === '' ? '' : `<b>${esc(k)}</b><span>${v}</span>`;
function overviewTab(el, R, showTab) {
  el.dataset.done = '1';
  const PF = R.profile || {}, P = PF.pacing || R.pacing || {}, C = PF.content || {}, K = PF.cinematic || {}, B = R.breakdown || {};
  const f = R.focus || 'both', showC = f !== 'cinematic', showK = f !== 'content';
  const H = C.hook || {}, SP = C.speech, TX = C.text, n = (o, w) => plural(o || 0, w);
  const listOf = o => Object.entries(o || {}).map(([k, v]) => `<span class="chip">${esc(t(k))} <b>${v}</b></span>`).join(' ') || `<span class="dim">${t('none|list')}</span>`;
  const bdVal = v => Array.isArray(v) ? `<ul>${v.map(x => `<li>${linkify(x)}</li>`).join('')}</ul>` : `<div>${linkify(v)}</div>`;
  const reviewed = R.flow && R.flow.done.includes('claude');
  el.innerHTML = `<div class="ovgrid">
    <div class="panel"><h2>${t('Rhythm')}</h2><div class="kv">
      ${kvRow(t('Cuts'), P.cuts_per_min != null ? t('<b>{n}</b> per minute', {n: numStr(P.cuts_per_min)}) : '')}
      ${kvRow(t('Shots'), P.avg_shot_s != null ? t('{avg} s on average (median {median} s · shortest 10 % under {p10} s · longest 10 % over {p90} s)',
        {avg: numStr(P.avg_shot_s), median: numStr(P.median_shot_s ?? '–'), p10: numStr(P.p10_shot_s ?? '–'), p90: numStr(P.p90_shot_s ?? '–')}) : '')}
      ${kvRow(t('First 3 s'), `${n(P.hook_cuts_3s, 'cut')}${P.first_cut_s != null ? ` · ${t('first cut at {s} s', {s: numStr(P.first_cut_s)})}` : ''}`)}
      ${kvRow(t('On the beat'), P.cuts_on_beat_pct != null ? `${t('{pct} % of the plain cuts', {pct: numStr(P.cuts_on_beat_pct)})}${R.audio.bpm ? ` · ${dec(R.audio.bpm, 1)} BPM` : ''}` : (R.audio.bpm ? `${dec(R.audio.bpm, 1)} BPM` : ''))}
      ${kvRow(t('Effects'), P.effects_per_min != null ? t('{n} per minute', {n: numStr(P.effects_per_min)}) : '')}</div></div>
    ${showC ? `<div class="panel"><h2>${t('Content creation')}</h2><div class="kv">
      ${kvRow(t('The hook (3 s)'), [n(H.cuts, 'cut'), H.words != null ? tn(H.words, '{n} word spoken', '{n} words spoken') : '', H.text_on_screen ? t('text on screen') : ''].filter(Boolean).join(' · '))}
      ${SP ? kvRow(t('Talking'), `${t('{wpm} words a minute · talking {pct} % of the time · {words}', {wpm: numStr(SP.words_per_min), pct: numStr(SP.talk_pct), words: n(SP.words, 'word')})} <span class="dim">(${esc(SP.source === 'speech' ? t('speech to text') : t("the platform's subtitles"))})</span>`)
        : kvRow(t('Talking'), `<span class="dim">${t('no transcript yet')}</span> <button class="btn sm ghost" data-ovgo="content">${t('What it says →')}</button>`)}
      ${TX ? kvRow(t('Text on screen'), `${TX.appearances ? t('pops up {times} ({per}/min, {each} s each)', {times: n(TX.appearances, 'time'), per: numStr(TX.per_min), each: numStr(TX.avg_on_s ?? '–')}) : t('no text pops up')}${TX.captions_likely ? ` · <b>${t('burned-in captions')}</b>` : ''}${TX.visible_pct != null ? ` <span class="dim">· ${t('text-like shapes {pct} % of the time', {pct: numStr(TX.visible_pct)})}</span>` : ''}`) : ''}
      </div></div>` : ''}
    ${showK ? `<div class="panel"><h2>${t('Cinematic')}</h2><div class="kv">
      ${kvRow(t('Signature'), (K.signature || []).map(chip).join(' ') || `<span class="dim">${t('no effects besides cuts')}</span>`)}
      ${kvRow(t('Transitions'), listOf(K.transitions))}
      ${kvRow(t('Camera'), listOf(K.camera))}
      ${kvRow(t('Speed'), listOf(K.speed))}
      ${PF.colour ? kvRow(t('Colour'), esc(PF.colour.line || '')) : ''}</div></div>` : ''}
  </div>
  ${showK || R.colour ? colourPanel(R) : ''}
  <div class="panel bd"><div class="row sp"><h2>${t('What makes it work')} <span class="small muted">· ${t("Claude's breakdown")}</span></h2>${B.summary ? '' : ''}</div>
    ${Object.keys(B).length ? `${B.summary ? `<p class="bdsum">${linkify(B.summary)}</p>` : ''}<div class="bdgrid">${BD.filter(([k]) => B[k]).map(([k, l]) => `<div class="bdi"><h3>${l}</h3>${bdVal(B[k])}</div>`).join('')}</div>`
      : `<div class="small muted">${reviewed ? t('Claude checked the effects before 0.4 - ask it again for the breakdown:') : t('Claude has not checked this video yet. It looks at every effect and writes what makes the video work:')}</div>
         <div class="row" style="margin-top:8px">${claudeBtn(R.review_prompt, reviewed ? t('Ask Claude for the breakdown') : t('Send to Claude'), 'review', R.title, 'pri')}</div>`}</div>
  <div class="panel useit"><h2>${t('Use it')}</h2><div class="row">
    <button class="btn pri" data-use="edit"><svg class="i"><use href="#i-edit"/></svg>${t('Edit my clips like this…')}</button>
    <button class="btn" data-use="prompts"><svg class="i"><use href="#i-generate"/></svg>${t('Prompts for AI tools like this…')}</button>
    <button class="btn ghost" data-use="again" title="${ta('the same video again with another focus - the measurements are re-used')}">${t('Analyse again with another focus…')}</button></div>
    <div class="small muted" style="margin-top:8px">${t('Claude also reads it from its memory when you edit or generate - nothing to copy.')}</div></div>
  <div id="ovtook"></div>`;
  el.insertAdjacentHTML('afterbegin', `<div class="liveline" data-live="${esc(R.name)}" data-name="${esc(R.label || R.title || R.name)}" hidden></div>`);
  liveLine(LIVE);
  tookPanel($('#ovtook', el), 'analysis', R.name);
  $$('[data-ovgo]', el).forEach(b => b.onclick = () => showTab(b.dataset.ovgo, true));
  wireColour(el, R);
  $('[data-use=edit]', el).onclick = () => newEdit({from: 'reference', pick: R.name});
  $('[data-use=prompts]', el).onclick = () => aiPromptsModal('shot', R.name);
  $('[data-use=again]', el).onclick = () => addVideosModal({files: R.source ? [R.source] : [], focus: f === 'both' ? 'content' : 'both', pick: true, again: true});
}

// ---- the Overview's Colour & look (0.4, the cinematic focus: "colour grading"): colour\colour.json (motionlab.colour)
function colourPanel(R) {
  const C = R.colour;
  if (!C) return `<div class="panel colour"><h2>${esc(t('Colour & look'))}</h2><div class="small muted">${t('Not measured yet - it takes a few seconds (no new decoding).')}</div>
    <div class="row" style="margin-top:8px"><button class="btn sm" id="colgo">${t('Measure the colour')}</button></div></div>`;
  const S = C.summary || {}, N = Math.max(1, (C.shots[C.shots.length - 1] || {}).end + 1 || 1);
  const num = (v, u = '') => v == null ? '–' : `${numStr(Math.round(v * 10) / 10)}${u}`;
  const warm = S.warmth == null ? '–' : S.warmth > 6 ? t('warm ({n})', {n: num(S.warmth)}) : S.warmth < -4 ? t('cool ({n})', {n: num(S.warmth)}) : t('neutral ({n})', {n: num(S.warmth)});
  return `<div class="panel colour"><div class="row sp"><h2>${esc(t('Colour & look'))}</h2><span class="small muted">${esc(t(C.made_from || ''))}</span></div>
    <div class="row" style="gap:6px;margin-bottom:10px">${(S.words || []).map(w => `<span class="chip">${esc(t(w))}</span>`).join('') || '<span class="chip">natural</span>'}${S.consistent === false ? `<span class="small amber">${t('changes from shot to shot')}</span>` : ''}</div>
    ${(S.palette || []).length ? `<div class="cpal">${S.palette.map(([c, w]) => `<div class="cpc" style="flex:${Math.max(0.06, w)};background:${esc(c)}" title="${esc(c)} · ${Math.round(w * 100)} %"><span>${esc(c)}</span></div>`).join('')}</div>` : ''}
    <div class="cstrip" title="${ta("every shot's main colour, in order")}">${C.shots.map(x => `<i style="flex:${x.end - x.start + 1};background:${esc(((x.palette || [])[0] || ['#333'])[0])}" data-f="${x.start}"
      data-tip="${esc(`f${x.start}-${x.end} (${x.tc}-${x.tc_end})${x.words.length ? ': ' + x.words.map(w => t(w)).join(', ') : ''}`)}"></i>`).join('')}</div>
    <div class="kv" style="margin-top:10px">
      ${kvRow(t('Brightness'), t('{level} · blacks {black} · whites {white} · contrast {contrast}', {level: num(S.brightness, ' %'), black: num(S.black, ' %'), white: num(S.white, ' %'), contrast: num(S.contrast)}))}
      ${kvRow(t('Colour'), S.bw ? esc(t('black & white')) : `${t('saturation {sat} · {warmth} · tint {tint}', {sat: num(S.saturation, ' %'), warmth: warm, tint: num(S.tint)})}${S.shadows && S.highlights ? ` · ${t('shadows {shadows}, highlights {highlights}', {shadows: hueWord(S.shadows), highlights: hueWord(S.highlights)})}` : ''}`)}
      ${S.letterbox || (S.vignette != null && S.vignette < 0.85) ? kvRow(t('Frame|framing'), [S.letterbox ? t('letterbox {size}', {size: esc(S.letterbox)}) : '', S.vignette != null && S.vignette < 0.85 ? t('vignette (corners {pct} % of the centre)', {pct: Math.round(S.vignette * 100)}) : ''].filter(Boolean).join(' · ')) : ''}</div>
    <div class="small muted" style="margin-top:8px">${t('An edit <b>in its style</b> matches your footage to this look (a match LUT - also for DaVinci Resolve).')}</div></div>`;
}
function hueWord(ab) {
  const [a, b] = ab, c = Math.hypot(a, b);
  if (c < 3) return t('neutral|hue');
  const h = (Math.atan2(b, a) * 180 / Math.PI + 360) % 360;
  return [[20, t('red|hue')], [50, t('orange|hue')], [75, t('yellow|hue')], [165, t('green|hue')], [200, t('teal|hue')], [260, t('blue|hue')], [300, t('purple|hue')], [345, t('magenta|hue')], [360, t('red|hue')]].find(([l]) => h <= l)[1];
}
function wireColour(el, R) {
  $$('.cstrip i', el).forEach(i => { i.onmousemove = e => showTip(esc(i.dataset.tip), e.clientX, e.clientY); i.onmouseleave = hideTip; });
  const go = $('#colgo', el);
  if (go) go.onclick = async () => {
    try { await api('/api/jobs', {kind: 'colour', args: {name: R.name}, queue: true}); toast(t('Measuring the colour - a few seconds'), 'ok'); setTimeout(route, 4000); }
    catch (e) { toast(e.message, 'err'); }
  };
}

// ============================================================================================ timeline
class Timeline {
  /* events (lanes by overlap), hard cuts, shots, beats, drops; zoom = frames each side of the playhead (0 = all) */
  constructor(wrap, R, opts = {}) {
    this.c = $('canvas', wrap); this.R = R; this.fps = R.video.fps; this.N = R.video.frames; this.zoom = opts.zoom || 0;
    this.opts = opts; this.play = 0; this.sel = null; this.v0 = 0; this.v1 = this.N - 1;
    this.lanes = Timeline.pack(R.events, Math.max(2, this.N / 600));
    this.H = this.c.height;
    this.c.style.height = this.H + 'px';     // fixed now: a draw never resizes it (no ResizeObserver loop when shown later)
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
    this.W = W; c.width = W * dpr; c.height = H * dpr;
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
      const lbl = `f${this.play}  ${tc(this.play, this.fps)}`; g.font = 'bold 11px Consolas';
      const tw = g.measureText(lbl).width + 10, lx = Math.min(px + 4, W - tw - 2);
      g.fillStyle = '#ff5a5a'; g.fillRect(lx, H - 15, tw, 14); g.fillStyle = '#000'; g.fillText(lbl, lx + 5, H - 4);
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
    if (miss) showTip(`<b class="bad">${t('Possible miss')}</b> ${ftc(miss.frame, this.fps)}<br>${esc(miss.why)}<br><span class="dim">${t('click to check it')}</span>`, e.clientX, e.clientY);
    else if (ev) showTip(`<b class="amber mono">${ev.id}</b> ${esc(t(ev.label ?? ''))}<br>${frange(ev.start, ev.end, this.fps)}`, e.clientX, e.clientY);
    else showTip(t('{at} · click to jump', {at: ftc(f, this.fps)}), e.clientX, e.clientY);
  }
  click(e) {
    const {f, ev, miss} = this.hit(e);
    if (miss && this.opts.onMiss) this.opts.onMiss(miss);
    else if (ev && this.opts.onSelect) this.opts.onSelect(ev); else if (this.opts.onSeek) this.opts.onSeek(f);
  }
}

// ============================================================================================ home
// Home (0.4): one question - what do you want to do? - and the ways in (Prepare added after 0.4.1), then Claude's memory, setup warnings
// (only when a program is missing), the roadmap and the status
const WAYS = [   // the Analyser's card names its three ways (2026-10-18, the user: videos, thumbnails, scripts)
  ['analyze', t('Analyze what works'), t("Videos cut by cut, a channel's thumbnails, scripts and prompts. MotionLab measures them; Claude names what makes them work and remembers it for your videos.")],
  ['prepare', t('Prepare a video'), t('What you say on camera: improve a script you have, or answer a few questions and Claude writes one - a hook in the first 3 s, a structure that holds, one clear ask.')],
  ['edit', t('Edit my clips'), t('Your clips, cut in the style of up to three videos you analysed - or your way: “hook first, 3 s cuts, fast”. A quick draft takes minutes.')],
  ['generate', t('Generate a video'), t('From zero, no clips: a motion-graphics video Claude writes and renders, or a plan with every prompt for AI video tools (Higgsfield, Kling, Seedance…).')]];
function wayActs(k) {
  if (k === 'analyze') return `<button class="btn pri" data-way="link"><svg class="i"><use href="#i-analyze"/></svg>${t('Videos')}</button><button class="btn" data-way="thumbs">${t('Thumbnails')}</button><button class="btn" data-way="texts">${t('Scripts')}</button>`;
  if (k === 'prepare') return `<button class="btn pri" data-way="simp"><svg class="i"><use href="#i-scriptok"/></svg>${t('Improve a script')}</button><button class="btn" data-way="snew">${t('From zero')}</button>`;
  if (k === 'edit') return `<button class="btn pri" data-way="edit"><svg class="i"><use href="#i-edit"/></svg>${t('Start an edit')}</button>`;
  return `<button class="btn pri" data-way="gfx"><svg class="i"><use href="#i-claude"/></svg>${t('Motion graphics')}</button><button class="btn" data-way="ai">${t('AI video tools|button')}</button>`;
}
async function pageHome(main) {
  const s = await api('/api/status');
  const an = [plural(s.references, 'video'), s.thumbs && plural(s.thumbs, 'thumbnail'), s.texts && tn(s.texts, '{n} script & prompts', '{n} scripts & prompts')].filter(Boolean);
  const foot = {analyze: an.length === 1 ? tn(s.references, '{n} video analysed', '{n} videos analysed') : an.join(' · '), prepare: plural(s.scripts || 0, 'script'), edit: plural(s.projects, 'edit'),
                generate: t('{prompts} in your library', {prompts: plural(s.prompts || 0, 'prompt')})};
  main.innerHTML = `
  ${heroAnim()}
  ${updateBox(s.update, s.update_result && (s.update_result.set_aside || []).length ? s.update_result : null)}
  <h2 class="ways-q">${t('What do you want to do?')}</h2>
  <div class="ways">${WAYS.map(([k, name, d]) => `<div class="way w-${k}"><div class="way-top"><svg class="ic"><use href="#i-${k}"/></svg></div>
      <h3>${name}</h3><p>${d}</p><div class="row way-act">${wayActs(k)}</div><a class="way-foot" href="#/${k}">${foot[k]} →</a></div>`).join('')}</div>
  ${s.setup.length ? `<div class="panel upd" style="margin-top:14px"><h2>${t('Setup')}</h2><ul class="next">${s.setup.map(tool => `<li>${t('<b>{name}</b> not found', {name: esc(t(tool.label))})} <span class="dim small">(${esc(t(tool.need))})</span><div class="small muted">${esc(t(tool.how))}</div></li>`).join('')}</ul>
    <a href="#/settings">${t('Settings → Programs')}</a></div>` : ''}
  ${s.roadmap_live ? `<div class="panel roadmap" style="margin-top:14px"><div class="row sp"><h2>${t('Roadmap')}</h2><span class="hint">${t('click to enlarge')}</span></div>
    <div class="rmlive"><iframe src="${fileUrl(s.roadmap_live)}" title="${ta('MotionLab roadmap')}" loading="lazy" tabindex="-1"></iframe>
      <button class="rmhit" aria-label="${ta('Enlarge the roadmap')}"></button></div></div>`
  : s.roadmap ? `<div class="panel roadmap" style="margin-top:14px"><div class="row sp"><h2>${t('Roadmap')}</h2><span class="hint">${t('click to enlarge')}</span></div>
    <img src="${fileUrl(s.roadmap)}" alt="${ta('roadmap')}"></div>` : ''}`;
  $('#hero-go', main).onclick = () => addVideosModal();
  const WAY_GO = {link: () => addVideosModal(), thumbs: () => addThumbsModal(), texts: () => addTextsModal(), edit: () => newEdit(),
                  gfx: () => generateModal('graphics'), ai: () => generateModal('ai'), simp: () => scriptImproveModal(), snew: () => scriptNewModal()};
  $$('[data-way]', main).forEach(b => b.onclick = () => WAY_GO[b.dataset.way]());
  wireUpdateBox(main, s.update_result);
  const rm = $('.roadmap img', main); if (rm) rm.onclick = () => lightbox([{src: s.roadmap, cap: t('MotionLab roadmap')}], 0);
  const rh = $('.rmhit', main); if (rh) rh.onclick = () => roadmapBig(fileUrl(s.roadmap_live));
}
// the roadmap = docs/roadmap/index.html, a motion graphic drawn live from docs/roadmap/roadmap.json (tools/roadmap.py):
// small on Home (no clicks inside), full size on a click - there you can hover a version for its full name
function roadmapBig(src) {
  const el = document.createElement('div'); el.id = 'rmbig';
  el.innerHTML = `<button class="btn sm rmx" aria-label="${ta('Close')}">✕</button><iframe src="${src}" title="${ta('MotionLab roadmap')}"></iframe>
    <div class="lbcap">${t('hover a version for its full name · Esc or a click outside closes it')}</div>`;
  const close = () => { el.remove(); document.removeEventListener('keydown', esc, true); };
  const esc = e => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); } };
  el.onclick = e => { if (e.target === el || e.target.closest('.rmx')) close(); };
  document.addEventListener('keydown', esc, true);
  document.body.append(el);
}
// Generate > AI video tools: Claude writes the prompts (the prompt library's "Generate a new prompt", a shot first)
async function aiPromptsModal(kind = 'shot', style = '') {
  let R;
  try { R = await api('/api/prompts'); } catch (e) { toast(e.message, 'err'); return; }
  modal(`<h2>${t('Prompts for AI video and image tools')}</h2>
    <p class="hint">${t('Tell Claude what you want to make. It writes the prompts in the structure that worked best in your library, checks them and saves them in your <a href="#/prompts" onclick="closeModal()">prompt library</a>. You paste them into the tool, then bring the clips to the <a href="#/edit" onclick="closeModal()">Editor</a>.')}</p>
    <div id="amode"></div>`, m => newPromptForm($('#amode', m), R, kind, style));
}

// ---- updates: the sidebar's Update button, its dialog (the CHANGELOG sections newer than this copy), "What's new"
// "3 videos": in another language the noun's two forms come from the catalogue's _nouns ("vídeo", "vídeos")
function plural(n, w) { const f = (I18N._nouns || {})[w]; return Array.isArray(f) ? `${numStr(n)} ${f[n === 1 ? 0 : 1]}` : `${n} ${w}${n === 1 ? '' : 's'}`; }
// updates come from GitHub's "tested" branch: newer pushes wait until the automatic tests pass (updater.check)
function testingText(u) { return u && u.testing ? ` · ${t('{changes} on GitHub not released yet', {changes: plural(u.testing, 'newer change')})}` : ''; }
function knowledgeText(cards, lessons) {             // "2 reference cards and 1 lesson"
  return andWords([cards ? plural(cards, 'reference card') : '', lessons ? plural(lessons, 'lesson') : ''].filter(Boolean));
}
function sideUpdate(p) {                             // from the heartbeat: show / label the sidebar buttons
  const kn = p.update_kind === 'knowledge';
  const what = kn ? (knowledgeText(p.update_cards || 0, p.update_lessons || 0) || t('shared knowledge'))
    : p.update_kind === 'version' && p.update_version ? 'MotionLab ' + p.update_version : t('changes on GitHub');
  const b = $('#side-update');
  if (b) {
    b.hidden = !p.update;
    if (p.update) { b.classList.toggle('kn', kn); $('b', b).textContent = kn ? t('New from friends') : t('Update available'); $('small', b).textContent = what;
      $('use', b).setAttribute('href', kn ? '#i-shared' : '#i-update'); }      // friends' knowledge = the shared icon
  }
  const c = $('#side-check');                        // bottom left: always there - check now, or install what was found
  if (!c || c.dataset.busy) return;
  c.classList.toggle('avail', !!p.update);
  $('b', c).textContent = p.update ? (kn ? t('New from friends') : t('Update available')) : t('Check for updates');
  const hm = String(p.update_checked || '').slice(11, 16);
  $('small', c).textContent = p.update ? what : p.update_error ? t("can't check - click for why")
    : hm ? (p.update_testing ? t('up to date · {hm} · {n} not released yet', {hm, n: p.update_testing}) : t('up to date · {hm}', {hm})) : '';
  c.title = p.update ? t('See what changed and install it')
    : (p.update_error ? t("Can't check: {err}", {err: p.update_error}) + '\n\n' : '') + t('Ask GitHub for a newer MotionLab (or new knowledge from your friends) and install it|update')
      + (p.update_testing ? '\n' + t("{changes} on GitHub not released yet - offered once GitHub's tests pass (they run for a new version)", {changes: plural(p.update_testing, 'newer change')}) : '');
}
async function checkUpdates() {                      // the sidebar's Check for updates: ask GitHub now, then offer it
  const c = $('#side-check');
  if (c.classList.contains('avail')) { updateModal(); return; }
  if (c.dataset.busy) return;
  c.dataset.busy = '1'; c.disabled = true;
  $('b', c).textContent = t('Checking…'); $('small', c).textContent = t('asking GitHub');
  let u = null;
  try { u = await api('/api/update/check', {}); }
  catch (e) { toast(e.message, 'err'); }
  delete c.dataset.busy; c.disabled = false;
  await ping();
  if (!u) return;
  if (u.error) toast(t("Can't check for updates: {error}", {error: u.error}), 'err');
  else if (u.restart_needed) banner('restart', `${t('MotionLab {version} is installed - restart to use it.', {version: esc(u.disk_version || '')})} <button class="btn sm pri">${t('Restart now')}</button>`, restartApp);
  else if (u.can_update) updateModal();
  else toast(u.testing ? t('MotionLab {version} is up to date - {changes} on GitHub not released yet', {version: u.version, changes: plural(u.testing, 'newer change')})
    : t('MotionLab {version} is up to date', {version: u.version}), 'ok');
}
// the user's own changes an update replaced (2026-10-24, a friend's ask: tuning lost in silence): named, kept as a
// patch on the server (updater.restore_kept) and back in one click; older records only had git's stash
const setAside = res => {
  const local = (res.to_local || []).length ? `<div class="small kept"><span>${t('Your own detection settings stay in use on this PC: {keys}', {keys: esc(res.to_local.join(', '))})}</span></div>` : '';
  const rest = (res.set_aside || []).filter(f => !(res.to_local || []).length || f !== 'tools/config.json');
  return local + (!rest.length ? '' : res.kept && !res.kept_restored ? keptLine(res.kept, rest)
    : res.kept_restored ? '' : `<div class="small">${t('Your own changes to <b>{files}</b> clashed with the update: the file now has the new version and your changes are kept in git (<code>git stash list</code>) - ask Claude to bring them back if you still need them.', {files: esc(rest.join(', '))})}</div>`);
};
const keptLine = (name, files) => `<div class="small kept"><span>${t('The update replaced your own changes to <b>{files}</b> - they are kept.', {files: esc(files.join(', '))})}</span>
  <button class="btn sm" data-kept="${esc(name)}">${t('Bring them back')}</button></div>`;
document.addEventListener('click', async e => {
  const b = e.target.closest('[data-kept]');
  if (!b) return;
  b.disabled = true;
  try {
    const r = await api('/api/update/restore', {name: b.dataset.kept});
    if (r.restored) {
      b.closest('.kept').remove();
      toast(t('Your changes are back: {files}', {files: r.files.join(', ')}), 'ok');
      if (r.restart) banner('restart', `${t('Restart MotionLab to use them.')} <button class="btn sm pri">${t('Restart now')}</button>`, restartApp);
    } else { b.disabled = false; toast(t('They could not go back by themselves - the update changed the same lines. Ask Claude to merge your kept changes.'), 'err'); }
  } catch (err) { b.disabled = false; toast(err.message, 'err'); }
});
// update banner (home + settings): new version on GitHub, or the result of the last update
function updateBox(u, res) {
  u = u || {};
  // "1 files" stays as the English always said it (the Spanish counts it right)
  if (res && res.updated) return `<div class="panel upd ok"><div class="row sp"><div><b>${res.code_changed === false ? t("Friends' knowledge added") : t('Updated to MotionLab {version}', {version: esc(res.version || '')})}</b> <span class="small muted">(${esc(res.from)} → ${esc(res.to)}, ${tn((res.changed || []).length, '{n} files', '{n} files')}${res.pip ? ', ' + t('Python packages updated') : ''})</span></div>
    ${res.whats_new ? `<button class="btn sm" data-shownew>${t("What's new")}</button>` : ''}</div>
    ${setAside(res)}</div>`;
  if (u.restart_needed) return `<div class="panel upd"><div class="row sp"><b>${t('MotionLab {version} is installed - restart to use it', {version: esc(u.disk_version || '')})}</b><button class="btn sm pri" data-restart>${t('Restart now')}</button></div></div>`;
  if (!u.can_update) return '';
  const kn = u.kind === 'knowledge';
  return `<div class="panel upd"><div class="row sp"><div><b>${kn ? t('New from friends: {what}', {what: esc(knowledgeText(u.new_cards || 0, u.new_lessons || 0) || t('shared knowledge'))})
      : u.kind === 'version' ? t('MotionLab {version} is available', {version: esc(u.new_version)}) : t('Updates are available')}</b> <span class="small muted">· ${t('{changes} on GitHub', {changes: plural(u.behind, 'change')})}</span>
    ${u.dirty && u.dirty.length ? `<div class="small muted">${t('Your changed files are kept: {files}', {files: esc(u.dirty.slice(0, 4).join(', ')) + (u.dirty.length > 4 ? ' …' : '')})}</div>` : ''}</div>
    <div class="row"><button class="btn sm" data-whatsnew>${t("What's new")}</button><button class="btn sm pri" data-update>${kn ? t('Get it now') : t('Update now')}</button></div></div></div>`;
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
  if (!u.can_update) { toast(u.error || t('MotionLab is up to date'), u.error ? 'err' : 'ok'); return; }
  const kn = u.kind === 'knowledge', jobs = +($('#jobcount').textContent || 0);
  const list = (u.changes || []).map(c => `<li>${esc(c)}</li>`).join('');
  modal(`<h2>${kn ? '<svg class="i shic"><use href="#i-shared"/></svg>' + t('New knowledge from your friends') : u.kind === 'version' ? t('MotionLab {version} is available', {version: esc(u.new_version)}) : t('Updates are available')}</h2>
    <div class="small muted">${t('You have MotionLab {version}', {version: esc(u.version)})} · ${t('{changes} on GitHub', {changes: plural(u.behind, 'change')})}${u.checked ? ' · ' + t('checked {when}', {when: esc(u.checked)}) : ''}${testingText(u)}</div>
    <div class="whatsnew">${kn ? `<p>${t('<b>{what}</b> - what your friends analysed and learned (pacing, effects, their verdicts); lessons wait for a review before they change anything. No restart needed.', {what: esc(knowledgeText(u.new_cards || 0, u.new_lessons || 0) || t('Shared knowledge'))})}</p><ul class="small">${list}</ul>
      <p class="small muted">${t('Once it is in, <a href="#/memory/shared" onclick="closeModal()">Claude\'s memory › Shared knowledge</a> shows who shared what - and everything from a friend carries {badge}.', {badge: sharedChip(t('a friend'))})}</p>`
      : u.whats_new ? `<div class="md">${md(u.whats_new)}</div>` : `<ul class="small">${list}</ul>`}</div>
    ${u.dirty && u.dirty.length ? `<div class="small muted" style="margin-top:10px">${t('Files you changed in this copy are kept: {files}', {files: esc(u.dirty.slice(0, 4).join(', ')) + (u.dirty.length > 4 ? ' …' : '')})}</div>` : ''}
    <div class="small muted" style="margin-top:10px">${kn ? t('Only shared knowledge comes in.') : t('MotionLab restarts by itself (about 10 seconds).')} ${t('Your videos, analyses, verdicts, settings and knowledge are not touched.')}</div>
    ${jobs ? `<div class="small amber" style="margin-top:6px">${t('A job is running - update when it has finished (Jobs).')}</div>` : ''}
    <div class="row" style="margin-top:14px;justify-content:flex-end"><button class="btn" data-later>${t('Later')}</button><button class="btn pri" data-go ${jobs ? 'disabled' : ''}>${kn ? t('Get it now') : t('Update now')}</button></div>`,
  el => { $('[data-later]', el).onclick = closeModal; $('[data-go]', el).onclick = () => { closeModal(); updateNow(); }; });
}
function whatsNewModal(res) {                        // after an update (the window reloaded) or knowledge that came in
  const kn = res.code_changed === false;
  modal(`<h2>${kn ? t("Friends' knowledge added") : t('Updated to MotionLab {version}', {version: esc(res.version || '')})}</h2>
    <div class="small muted">${!kn && res.from_version ? t('from {version}', {version: esc(res.from_version)}) + ' · ' : ''}${plural((res.changed || []).length, 'file')}${res.pip === 'ok' ? ' · ' + t('Python packages updated') : ''}</div>
    ${res.pip && res.pip !== 'ok' ? `<div class="small bad" style="margin-top:8px">${t('Installing the new Python packages failed - run setup.bat again: {error}', {error: esc(res.pip)})}</div>` : ''}
    ${setAside(res)}
    <div class="whatsnew">${res.whats_new ? `<div class="md">${md(res.whats_new)}</div>`
      : kn ? `<p>${t("{what} from your friends: Claude's memory shows them, and Claude reads them in your next analysis.", {what: esc(knowledgeText(res.new_cards || 0, res.new_lessons || 0) || t('Shared knowledge'))})}</p>
        <p><a href="#/memory/shared" onclick="closeModal()"><svg class="i"><use href="#i-shared"/></svg>${t("See who shared what in Claude's memory › Shared knowledge")}</a></p>`
      : `<p class="muted">${t('The changelog has no notes for this update.')}</p>`}</div>
    <div class="row" style="margin-top:14px;justify-content:flex-end"><button class="btn pri" data-ok>${t('Got it')}</button></div>`,
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
  if (LANG !== 'en') {                               // a version's notes in the app's language when CHANGELOG.<lang>.md has it
    try {
      const tr = new Map(changelogSections((await api(`/api/text?path=CHANGELOG.${LANG}.md`)).text).map(s => [s.version, s]));
      local = local.map(s => tr.get(s.version) || s);
    } catch (e) { /* no translated notes: the English ones */ }
  }
  try { plans = changelogSections((await api('/api/text?path=docs/plans.md')).text).map(s => ({...s, date: ''})); } catch (e) { /* no plans file */ }
  try { u = await api('/api/update'); } catch (e) { /* offline: the local history is enough */ }
  const have = new Set(local.map(s => s.version));
  const upcoming = u.can_update && u.kind === 'version' ? changelogSections(u.whats_new).filter(s => !have.has(s.version)) : [];
  const item = (s, cls, open, badge) => `<details class="tl-item ${cls}" ${open ? 'open' : ''}><summary><span class="tl-ver">${esc(s.version)}</span>
      ${s.date ? `<span class="tl-date">${esc(s.date)}</span>` : ''}<span class="tl-title">${esc(s.title)}</span>${badge ? `<span class="tl-badge">${badge}</span>` : ''}</summary>
      <div class="md small">${md(s.body)}</div></details>`;
  modal(`<div class="row sp"><h2 style="margin:0">${t("What's new in MotionLab")}</h2><span class="small muted">${t('you have {version}', {version: esc(PAGE_VERSION)})}</span></div>
    <div class="tline">${plans.length ? `<div class="tl-sec">${t('Planned')}</div>` + plans.map(s => item(s, 'plan', false, t('planned|version'))).join('') + `<div class="tl-sec">${t('Released')}</div>` : ''}
      ${upcoming.map(s => item(s, 'new', true, t('on GitHub - not installed yet'))).join('')}
      ${local.map((s, i) => item(s, s.version === PAGE_VERSION ? 'cur' : '', i === 0 && !upcoming.length || s.version === PAGE_VERSION,
                                 s.version === PAGE_VERSION ? t('your version') : '')).join('')}</div>
    <div class="row" style="justify-content:flex-end;margin-top:10px">${upcoming.length ? `<button class="btn pri" data-up>${t('Update now')}</button>` : ''}<button class="btn" data-close>${t('Close')}</button></div>`,
  el => { $('[data-close]', el).onclick = closeModal; const b = $('[data-up]', el); if (b) b.onclick = () => { closeModal(); updateNow(); }; });
}
async function updateNow() {
  overlay(t('Updating MotionLab from GitHub…'));
  try {
    const r = await api('/api/update/apply', {});
    if (r.updated && r.restart !== false) { RELOADING = false; waitForServer(t('Restarting MotionLab with the new version…')); }
    else if (r.updated) { $('#overlay').hidden = true; route(); ping(); whatsNewModal(r); }
    else { $('#overlay').hidden = true; toast(t('Already up to date'), 'ok'); route(); ping(); }
  } catch (e) { $('#overlay').hidden = true; toast(e.message, 'err'); }
}

// Analyze > Add videos (0.4): links and / or files (up to 10), what Claude should look at (content creation,
// cinematic, both), and whether Claude checks each one when it is measured - then they are analysed one after another
const FOCUS_OPTS = [
  ['content', t('Content creation'), t('Talking, the hook, captions and on-screen text, pacing, motion graphics.'), t('TikToks, Reels, YouTube, vlogs, podcasts'), t('+ the transcript and the views')],
  ['cinematic', t('Cinematic'), t('Effects, transitions, camera moves, speed ramps and the colour grade.'), t('music videos, edits, trailers, ads'), t('+ the colour look')],
  ['both', t('Both'), t('Everything - the content and the cinematic side.'), t('when you are not sure'), t('takes a little longer')]];
const AV_MAX = 10;
// Claude's usual time per item on this PC (0.4.5, GET /api/estimate = What it took's numbers) -> one line before a batch.
// Whole sentences per item (the callers' video / text / edit), so each language words them its own way: [one, n of
// them, not measured yet]; another item needs its three lines here
const EST_LINES = {
  video: [t('Claude usually takes about {time} a video on this PC'), t('Claude usually takes about {time} a video on this PC - about <b>{total}</b> for {n}'),
          t("Claude's time per video is not measured on this PC yet")],
  text: [t('Claude usually takes about {time} a text on this PC'), t('Claude usually takes about {time} a text on this PC - about <b>{total}</b> for {n}'),
         t("Claude's time per text is not measured on this PC yet")],
  edit: [t('Claude usually takes about {time} an edit on this PC'), t('Claude usually takes about {time} an edit on this PC - about <b>{total}</b> for {n}'),
         t("Claude's time per edit is not measured on this PC yet")]};
function estWords(e, n, what = 'video') {
  const [one, many, none] = EST_LINES[what] || EST_LINES.video;
  return e ? fillVars(n > 1 ? many : one, {time: minWords(e.minutes), total: minWords(e.minutes * n), n}) : none;
}
async function addVideosModal(pre = {}) {
  const [cands, ST, EST] = await Promise.all([api('/api/candidates'), api('/api/settings'), api('/api/estimate').catch(() => ({}))]);
  const cl = ST.tools.find(x => x.name === 'claude') || {}, yt = ST.tools.find(x => x.name === 'yt-dlp') || {};
  const picked = new Set(pre.files || []);
  let focus = pre.focus || ST.settings.default_focus || 'both';
  const fresh = cands.filter(c => !c.analysed), done = cands.filter(c => c.analysed);
  const elsewhere = (pre.files || []).filter(p => !cands.some(c => c.path === p)).map(p => ({path: p, name: p, size: null, analysed: true}));
  const fileRow = c => `<label class="avfile"><input type="checkbox" value="${esc(c.path)}" ${picked.has(c.path) ? 'checked' : ''}>
    <span class="grow">${esc(c.name)}</span><span class="small dim">${bytes(c.size)}</span>${c.analysed ? `<span class="tag done">${t('analysed - again')}</span>` : `<span class="tag">${t('new|video')}</span>`}</label>`;
  modal(`<h2>${t('Analyze videos')}</h2>
    <div class="avstep"><b>1</b><span>${t('Which videos?')}</span><span class="small muted">${t('up to {n} at a time - they are analysed one after another', {n: AV_MAX})}</span></div>
    <textarea id="avl" rows="3" placeholder="${ta('Paste links, one per line - YouTube, TikTok, Instagram, Vimeo…')}">${esc((pre.links || []).join('\n'))}</textarea>
    ${yt.found ? '' : `<div class="small amber">${t('Links need the downloader (yt-dlp): <a href="#/settings" onclick="closeModal()">Settings → Programs</a>. Files work without it.')}</div>`}
    <div class="small muted" style="margin:8px 0 4px">${t('or pick videos you already have (in the refs folder):')}</div>
    <div class="avfiles" id="avfiles">${[...elsewhere, ...fresh, ...done].map(fileRow).join('') || `<div class="small dim">${t('No videos in refs yet - paste a link, or the path of a video below.')}</div>`}</div>
    <div class="row" style="margin-top:6px"><input type="text" id="avpath" placeholder="${ta('…or the full path of a video elsewhere, e.g. C:\\Videos\\clip.mp4')}" style="flex:1"><button class="btn sm" id="avadd">${t('Add')}</button></div>
    <div class="avstep"><b>2</b><span>${t('What should Claude look at?')}</span></div>
    <div class="avmodes">${FOCUS_OPTS.map(([k, lab, d, ex, extra]) => `<label class="avmode${k === focus ? ' on' : ''}"><input type="radio" name="avf" value="${k}" ${k === focus ? 'checked' : ''}>
      <b>${lab}</b><span>${d}</span><span class="small dim">${ex}</span><span class="small acc">${extra}</span></label>`).join('')}</div>
    <div class="row small" style="margin-top:8px"><label>${t('Kind of video')} <select id="avcat">${ST.categories.map(o => `<option value="${o.id}" ${o.id === ST.settings.default_category ? 'selected' : ''}>${esc(t(o.label))}</option>`).join('')}</select></label>
      <span class="dim">${t('pacing and lessons are compared within a kind')}</span></div>
    <div class="avstep"><b>3</b><span>${t("Claude's check")}</span></div>
    <label class="chk avclaude"><input type="radio" name="avc" value="1" ${cl.found ? 'checked' : 'disabled'}><span>${t('<b>Claude checks them when they are measured</b> (recommended) - one Claude Code window for all of them: it names every effect and writes what makes each video work, so it can use it in your edits.')}${cl.found ? '' : ` <span class="bad">${t('Claude Code was not found - Settings.')}</span>`}
      <span class="small muted" id="avest"></span></span></label>
    <label class="chk avclaude"><input type="radio" name="avc" value="0" ${cl.found ? '' : 'checked'}><span>${t('<b>Measure only</b> - send them to Claude later (each video gets a <i>Send to Claude</i> button).')}</span></label>
    <details class="fold" style="margin-top:10px"><summary>${t('More options')}</summary><div class="in"><div class="form">
      <label for="avtags">${t('Tags')} ${optTag()}</label><input type="text" id="avtags" placeholder="${ta('e.g. instagram, asmr, recipe')}">
      <span></span><label class="chk small"><input type="checkbox" id="avre"> ${t('re-use the earlier measurements of videos analysed before (faster)')}</label></div></div></details>
    <div class="row" style="margin-top:14px"><button class="btn pri big" id="avgo" disabled><svg class="i"><use href="#i-analyze"/></svg>${t('Analyze')}</button>
      <span id="avsum" class="small muted"></span></div>`, el => {
    const links = () => $('#avl', el).value.split(/\s+/).map(x => x.trim()).filter(Boolean);
    const files = () => $$('#avfiles input:checked', el).map(x => x.value);
    const upd = () => {
      const L = links(), F = files(), n = L.length + F.length, bad = L.filter(u => !/^https?:\/\/\S+$/i.test(u));
      const b = $('#avgo', el);
      b.disabled = !n || n > AV_MAX || bad.length > 0 || (L.length && !yt.found);
      b.innerHTML = `<svg class="i"><use href="#i-analyze"/></svg>${n > 1 ? t('Analyze {n} videos', {n}) : n === 1 ? t('Analyze the video') : t('Analyze') + ' '}`;
      const what = [L.length ? tn(L.length, '{n} link (downloaded first)', '{n} links (downloaded first)') : '', F.length ? plural(F.length, 'file') : ''].filter(Boolean).join(' + ');
      $('#avsum', el).innerHTML = bad.length ? `<span class="bad">${t('not a link: {link}', {link: esc(bad[0])})}</span>` : n > AV_MAX ? `<span class="bad">${t('at most {n} at a time', {n: AV_MAX})}</span>`
        : n ? `${what} · ${focus !== 'cinematic' ? t('about 1–2 minutes per minute of video, + the transcript') : t('about 1–2 minutes per minute of video')}` : t('Paste a link or pick a video.');
      $('#avest', el).innerHTML = ' ' + estWords(EST.review, n) + '.';
    };
    $('#avl', el).oninput = upd;
    $('#avfiles', el).onchange = upd;
    $$('input[name=avf]', el).forEach(r => r.onchange = () => { focus = r.value; $$('.avmode', el).forEach(x => x.classList.toggle('on', $('input', x).checked)); upd(); });
    $('#avadd', el).onclick = () => {
      const v = $('#avpath', el).value.trim().replace(/^"|"$/g, '');
      if (!v) return;
      const box = $('#avfiles', el);
      if (box.querySelector('.dim')) box.innerHTML = '';
      box.insertAdjacentHTML('afterbegin', fileRow({path: v, name: v, size: null, analysed: false}));
      box.querySelector('input').checked = true; $('#avpath', el).value = ''; upd();
    };
    $('#avgo', el).onclick = async () => {
      const b = $('#avgo', el); b.disabled = true;
      try {
        const r = await api('/api/analyze/batch', {links: links(), files: files(), focus, category: $('#avcat', el).value,
          tags: $('#avtags', el).value, claude: ($('input[name=avc]:checked', el) || {}).value === '1', redetect: $('#avre', el).checked});
        closeModal(); ping();
        toast(tn(r.jobs.length, 'Analysing {n} video - follow them in the Analyser', 'Analysing {n} videos - follow them in the Analyser'), 'ok');
        if (location.hash !== '#/analyze') location.hash = '#/analyze'; else route();
      } catch (e) { toast(e.message, 'err'); b.disabled = false; }
    };
    if (pre.again) $('#avre', el).checked = true;           // another focus for a video analysed before: re-use its measurements
    if (pre.pick) $('#avfiles', el).scrollIntoView({block: 'center'}); else $('#avl', el).focus();
    upd();
  }, 'wide');
}
// ============================================================================================ the workflow of a reference
const FLOW = [
  ['download', t('Download'), t('Paste a link to a video you like (YouTube, TikTok, Instagram…)')],
  ['lab', t('Measure'), t('MotionLab finds every cut, effect and beat - about 1–2 minutes per minute of video')],
  ['claude', t('Claude checks'), t('Claude looks at every effect and names it')],
  ['verdicts', t('Your review'), t('Is Claude right? You mark each effect Correct, Partly or Wrong')],
  ['feedback', t('Send it to Claude'), t('Claude learns from your review for the next video')],
  ['share', t('Share'), t('Your friends get what you learned')],
];
const flowDots = fl => `<span class="fdots" title="${esc(FLOW.map(([k, t], i) => `${i + 1} ${t}${fl.done.includes(k) ? ' ✓' : ''}`).join(' · '))}">${FLOW.map(([k]) => `<i class="${fl.done.includes(k) ? 'd' : k === fl.next ? 'n' : ''}"></i>`).join('')}</span>`;
// since 0.4 a video is ready for edits once Claude checked it; verdicts, feedback and sharing teach Claude (optional).
// bare = the step alone, without "Next: " / "Ready ✓ · " (the video's page shows it beside its own word)
function flowNext(fl, bare = false) {
  const left = fl.events - fl.reviewed, open = fl.misses - fl.misses_checked;
  const ready = s => bare ? s : t('Ready ✓ · {step}', {step: s});
  switch (fl.next) {
    case 'claude': { const s = tn(left, 'send it to Claude - {n} effect not checked yet', 'send it to Claude - {n} effects not checked yet');
      return bare ? s : t('Next: {step}', {step: s}); }
    case 'verdicts': return ready(fl.given >= fl.real && open ? tn(open, 'optional: check {n} possible miss', 'optional: check {n} possible misses')
      : t('optional: your review teaches Claude ({given} / {real})', {given: fl.given, real: fl.real}));
    case 'feedback': return ready(fl.sent ? t('your review is sent - let Claude apply it') : t('optional: send your review to Claude'));
    case 'share': return ready(t('optional: share it with your friends'));
    default: return ready(t('all steps done'));
  }
}
function flowAction(r, fl, onPage = false) {         // the button for a reference's next step
  const sz = onPage ? '' : 'sm', open = fl.misses - fl.misses_checked;
  switch (fl.next) {
    case 'claude': return claudeBtn(r.review_prompt, t('Send to Claude'), 'review', r.title, `${sz} pri`);
    case 'verdicts':
      if (fl.given >= fl.real && open) return onPage ? `<button class="btn ${sz} missbtn" data-tabgo="misses">${t('Check the possible misses')}</button>`
        : `<a class="btn ${sz} missbtn" href="#/ref/${encodeURIComponent(r.name)}?misses">${tn(open, 'Check {n} possible miss', 'Check {n} possible misses')}</a>`;
      return onPage ? `<button class="btn ${sz}" data-tabgo="review">${t('Review the effects')} ↓</button>` : `<a class="btn ${sz}" href="#/ref/${encodeURIComponent(r.name)}?verdicts">${t('Review the effects')}</a>`;
    case 'feedback': return `<button class="btn ${sz}" data-feedback="${esc(r.name)}"><svg class="i"><use href="#i-claude"/></svg>${t('Send it to Claude')}</button>`;
    case 'share': return `<a class="btn ${sz}" href="#/memory/shared">${t('Share my knowledge')}</a>`;
    default: return '';
  }
}
// the video's page: where it stands + the one next thing (0.4.3.5, the user: "remove the listing in analyze as well" -
// the numbered steps Download > Measure > Claude checks | Teach Claude 4 5 6 were as ambiguous as Prepare's)
function flowStrip(r, fl) {
  const nx = flowNext(fl, true), cap = s => s.charAt(0).toUpperCase() + s.slice(1);
  return `<div class="flow strip">${fl.next === 'claude' ? `<b class="amber">${t('Not checked by Claude yet')}</b>`
      : `<b class="ok">${t('✓ Ready')}</b><span class="small muted">${t('Claude checked it - your edits and prompts can use its style')}</span>`}
    <div class="grow"></div>${fl.next ? `<div class="fnext"><span class="small${fl.next === 'claude' ? '' : ' muted'}">${esc(cap(nx))}</span>${flowAction(r, fl, true)}</div>` : ''}</div>`;
}

// *Send it to Claude* on an analysis (2026-10-18: the one last step of every review): the verdicts go out as the
// MOTIONLAB FEEDBACK text (feedback\app_<time>.txt, what tools\feedback.py reads) and Claude Code opens with the same
// hand-off as before - Claude turns it into lessons and thresholds, checks again what you marked wrong or partly (and
// the possible misses you called an effect) and says what changed. The raw text: *Copy what Claude gets* on the page.
async function sendFeedback(name) {
  try {
    const r = await api(`/api/reference/${encodeURIComponent(name)}/export`, {});
    await openClaude(`Apply the MOTIONLAB FEEDBACK in ${r.path}`, 'feedback', name);
  } catch (e) { toast(e.message, 'err'); }
}

async function tipsModal() {
  let txt = '';
  try { txt = (await api('/api/text?path=' + encodeURIComponent('docs/claude_tips.md'))).text; } catch (e) { txt = '# ' + t('Tips') + '\n\n' + e.message; }
  modal(`<div class="md">${md(txt)}</div>`);
}

// ============================================================================================ delete (Recycle Bin)
async function deleteModal(kind, name, onDone) {
  let P;
  try { P = await api(`/api/delete?kind=${kind}&name=${encodeURIComponent(name)}`); } catch (e) { toast(e.message, 'err'); return; }
  const one = P.items.length === 1;
  // the server's words (what each item is, warnings, notes) go through t(): a fixed one has its Spanish by key
  modal(`<h2>${t('Delete {name}?', {name: esc(P.title)})}</h2>
    <p class="hint">${t('Everything ticked goes to the Windows <b>Recycle Bin</b> - you can restore it from there until you empty the bin.')}</p>
    <div class="col delitems">${P.items.map(i => `<label class="delitem ${i.warn.length ? 'warn' : ''}"><input type="checkbox" value="${i.key}" ${i.default || one ? 'checked' : ''} ${one ? 'disabled' : ''}>
      <div><b>${esc(t(i.label))}</b> · ${bytes(i.bytes)}${i.files > 1 ? ' · ' + tn(i.files, '{n} file', '{n} files') : ''} <div class="mono small dim">${esc(i.path)}</div>
        <div class="small muted">${esc(t(i.what))}</div>${i.warn.map(w => `<div class="small warnline">⚠ ${esc(t(w))}</div>`).join('')}</div></label>`).join('')}</div>
    ${P.notes.map(n => `<div class="small muted" style="margin-top:6px">${esc(t(n))}</div>`).join('')}
    ${P.keeps.length ? `<div class="small ok" style="margin-top:8px">${t('Stays: {list}.', {list: P.keeps.map(k => esc(t(k))).join('; ')})}</div>` : ''}
    ${P.big ? `<div class="small warnline" style="margin-top:6px">${t('Very large: if it does not fit in the Recycle Bin, Windows asks before deleting it for good.')}</div>` : ''}
    <div class="row" style="margin-top:14px"><button class="btn del" id="delgo">${t('Move to the Recycle Bin')}</button><button class="btn" id="delno">${t('Cancel')}</button><span id="delst" class="small muted"></span></div>`, el => {
    $('#delno', el).onclick = closeModal;
    $('#delgo', el).onclick = async () => {
      const keys = $$('input[type=checkbox]', el).filter(x => x.checked).map(x => x.value);
      if (!keys.length) { toast(t('Tick what should go'), 'err'); return; }
      $('#delgo', el).disabled = true; $('#delst', el).textContent = t('moving…');
      // a video this window plays keeps its file open: stop every player first
      $$('video').forEach(v => { try { v.pause(); v.removeAttribute('src'); v.load(); } catch (e) { /* ignore */ } });
      await new Promise(r => setTimeout(r, 400));
      try {
        const r = await api('/api/delete', {kind, name, keys});
        if (r.failed.length) {
          $('#delst', el).innerHTML = `<span class="bad">${t('Not moved: {paths} - {why}', {paths: r.failed.map(f => esc(f.path)).join(', '), why: esc(t(r.failed[0].why))})}</span>`;
          $('#delgo', el).disabled = false; if (r.moved.length) toast(t('Moved to the Recycle Bin: {list}', {list: r.moved.join(', ')}), 'ok');
          return;
        }
        closeModal(); toast(t('Moved to the Recycle Bin ({size}): {list}', {size: bytes(r.bytes), list: r.moved.join(', ')}), 'ok');
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
const delBtn = (kind, name, after = '', label = '') => `<button class="btn sm ${label ? 'danger' : 'ghost icon'}" data-del="${kind}" data-name="${esc(name)}" data-after="${esc(after)}" title="${ta('Delete… (to the Recycle Bin)')}"><svg class="i"><use href="#i-trash"/></svg>${label}</button>`;

// ============================================================================================ videos (analyses)
const FOCUS_SHORT = {content: t('Content'), cinematic: t('Cinematic'), both: t('Content + cinematic')};
const focusChip = f => f ? `<span class="fchip sm focus-${esc(f)}" title="${ta('what Claude looked at')}">${esc(FOCUS_SHORT[f] || f)}</span>` : '';
// the lines a card shows for its focus (profile.py: the hook / talking / text; the signature effects / transitions)
const focusLines = r => { const L = r.lines || {}, f = r.focus || 'both';
  return [f !== 'cinematic' && L.content, f !== 'content' && L.cinematic, f !== 'content' && L.colour].filter(Boolean)
    .map(x => `<div class="small muted pline">${esc(x)}</div>`).join(''); };
// Analyze > in progress: the downloads and analyses running or waiting their turn (queued jobs) - refreshed every 2 s
// while any is active. A finished one shows for 5 s, then it is gone; a failed one stays until its ✕ (the user,
// 2026-10-15: "Done ... showing all the time? make it a 5 s pop up and then it disappears forever, or a discard
// option"). The ✕'d ones are remembered in this browser (by number + start: the numbers restart with the app).
const DONE_SHOW_S = 5;
const jobKey = j => `${j.id}@${j.started}`;
const GONE_JOBS = new Set((() => { try { return JSON.parse(localStorage.getItem('ml.goneJobs') || '[]'); } catch (e) { return []; } })());
const hideJob = k => { GONE_JOBS.add(k); try { localStorage.setItem('ml.goneJobs', JSON.stringify([...GONE_JOBS].slice(-200))); } catch (e) { /* this session only */ } };
function progressPanel(el, onEnd, kinds = ['download', 'analyze'], match = () => true) {
  let stop = false, last = '', was = new Set(), timer = null;      // was = the jobs active at the last tick
  const word = s => ({queued: t('waiting|job'), running: t('running|job'), cancelling: t('cancelling|job'), done: t('done|job'),
                      failed: t('failed|job'), cancelled: t('cancelled|job')})[s] || s;   // a job's state on its tag
  const tick = async () => {
    if (stop) return;
    clearTimeout(timer);
    let list = [];
    try { list = (await api('/api/jobs')).filter(j => kinds.includes(j.kind) && match(j)); } catch (e) { /* the next tick */ }
    const act = list.filter(j => j.status === 'running' || j.status === 'queued' || j.status === 'cancelling')
      .sort((a, b) => (a.status === 'queued') - (b.status === 'queued') || a.id - b.id);   // running first, then in turn
    const ended = list.filter(j => !act.includes(j) && j.ended_ago_s != null && !GONE_JOBS.has(jobKey(j)));
    const fresh = ended.filter(j => j.status !== 'failed' && j.ended_ago_s < DONE_SHOW_S);
    const recent = [...ended.filter(j => j.status === 'failed' && j.ended_ago_s < 900), ...fresh].slice(0, 4);
    const sig = act.map(j => j.id + j.status).join() + '|' + recent.map(j => j.id + j.status).join();
    const now = new Set(act.map(j => j.id));
    if ([...was].some(id => !now.has(id))) onEnd();     // one ended (a download that queued its analysis too)
    was = now;
    if (sig !== last) {
      last = sig;
      const bad = recent.some(j => j.status === 'failed');
      el.innerHTML = act.length || recent.length ? `<div class="panel progress"><div class="row sp"><h2>${act.length ? t('Working on {jobs}', {jobs: plural(act.length, 'job')}) : bad ? t('Something went wrong') : t('Done|jobs')}</h2><a class="small" href="#/jobs">${t('all jobs')} →</a></div>
        ${[...act, ...recent].map(j => `<div class="pjob ${esc(j.status)}"><span class="tag ${esc(j.status)}">${esc(word(j.status))}</span>
          <span class="grow">${esc(j.title)}${j.then ? ` <span class="small dim">${t('→ then analysed')}</span>` : ''}${j.then_claude ? ` <span class="small amber">${t('→ then Claude checks it')}</span>` : ''}</span>
          <a class="small" href="#/jobs/${j.id}">${t('log|job')}</a>${j.status === 'queued' ? `<button class="btn sm ghost" data-cancel="${j.id}">${t('Remove')}</button>` : ''}${j.status === 'failed' ? reportBtn(j.id, 'sm ghost') : ''}
          ${recent.includes(j) ? `<button class="btn sm ghost icon" data-hide="${esc(jobKey(j))}" title="${ta('Hide')}">✕</button>` : ''}</div>`).join('')}</div>` : '';
      $$('[data-cancel]', el).forEach(b => b.onclick = async () => { try { await api(`/api/jobs/${b.dataset.cancel}/cancel`, {}); tick(); } catch (e) { toast(e.message, 'err'); } });
      $$('[data-hide]', el).forEach(b => b.onclick = () => { hideJob(b.dataset.hide); last = ''; tick(); });
    }
    if (act.length) timer = setTimeout(tick, 2000);
    else if (fresh.length) timer = setTimeout(tick, (DONE_SHOW_S - Math.max(...fresh.map(j => j.ended_ago_s))) * 1000 + 150);
  };
  tick();
  return () => { stop = true; clearTimeout(timer); };
}
// Analyze > Downloaded, not analysed yet: one row per file; the files of one post (an Instagram carousel, a TikTok
// photo post with its sound - 0.4.2.1, downloads.json "post") under one heading, in their order
const waitKind = w => w.photo ? 'photo' : w.audio ? 'audio' : 'video';
const waitWord = w => ({photo: t('photo'), audio: t('audio'), video: t('video')})[waitKind(w)];   // the kind on its tag
const waitRow = (w, part = '') => `<tr class="${part ? 'postpart' : ''}">
  <td>${part ? `<span class="small dim">${part}</span> ` : ''}<span class="tag">${waitWord(w)}</span></td><td><b>${esc(part ? w.name.replace(/ \[[^\]]+\]\.\w+$/, '') || w.name : w.title || w.name)}</b><div class="small dim mono">${esc(w.name)}</div></td>
  <td class="small muted">${w.url && !part ? `<a href="${esc(w.url)}" target="_blank" rel="noopener">${esc(w.platform || t('link'))}</a> · ` : ''}${esc(w.modified)}</td><td class="num small">${bytes(w.size)}</td>
  <td class="row" style="justify-content:flex-end">${w.photo ? `<span class="small dim">${t('a photo of the post')}</span>` : w.audio ? `<span class="small dim">${part ? t("the post's sound") : t('music for an edit (Editor)')}</span>` : `<button class="btn sm pri" data-an="${esc(w.path)}">${t('Analyze…')}</button>`}${delBtn('file', w.rel, '', ' ' + t('Delete'))}</td></tr>`;
function waitRows(wait) {
  const groups = [];
  wait.forEach(w => { const g = w.post && groups.find(x => x.post === w.post); if (g) g.items.push(w); else groups.push({post: w.post || null, items: [w]}); });
  return groups.map(g => {
    if (!g.post) return waitRow(g.items[0]);
    const f = g.items[0], n = f.parts || g.items.length, kinds = {};
    g.items.forEach(w => { kinds[waitKind(w)] = (kinds[waitKind(w)] || 0) + 1; });
    const gone = n - g.items.length;                 // parts analysed or deleted since
    return `<tr class="posthead"><td><span class="tag post">${t('post')}</span></td><td><b>${esc(f.title || f.name)}</b>
        <div class="small dim">${t('one post, {parts}: {kinds}', {parts: plural(n, 'part'), kinds: Object.entries(kinds).map(([k, c]) => plural(c, k)).join(', ')})}${gone > 0 ? ' ' + tn(gone, '({n} analysed or removed)', '({n} analysed or removed)') : ''}</div></td>
      <td class="small muted"><a href="${esc(g.post)}" target="_blank" rel="noopener">${esc(f.platform || t('link'))}</a> · ${esc(f.modified)}</td>
      <td class="num small">${bytes(g.items.reduce((a, w) => a + w.size, 0))}</td><td></td></tr>`
      + g.items.map(w => waitRow(w, t('part {part} of {n}', {part: w.part, n}))).join('');
  }).join('');
}
// Analyser > the downloads nobody analysed (0.4.3.5, the user: "make it a little row that says X pending videos ...
// and if clicked u go to that list" - the analysed videos come first, like the Editor)
function waitingModal(wait) {
  const vids = wait.filter(w => !w.photo && !w.audio);
  modal(`<h2>${t('Downloaded, not analysed yet')}</h2>
    <div class="small muted" style="margin-top:-4px">${wait.length > vids.length ? t('Videos you downloaded and did not analyse yet, and music or photos from your downloads. Analyse one, or delete what you do not need (it goes to the Recycle Bin).')
      : t('Videos you downloaded and did not analyse yet. Analyse one, or delete what you do not need (it goes to the Recycle Bin).')}</div>
    ${vids.length > 1 ? `<div class="row" style="margin-top:12px"><button class="btn pri" id="wall"><svg class="i"><use href="#i-analyze"/></svg>${vids.length > AV_MAX ? t('Analyse the first {n}…', {n: AV_MAX}) : t('Analyse all {n}…', {n: vids.length})}</button></div>` : ''}
    <div class="waiting" style="margin-top:12px"><table class="t"><tbody>${waitRows(wait)}</tbody></table></div>`, el => {
    $$('[data-an]', el).forEach(b => b.onclick = () => { closeModal(); addVideosModal({files: [b.dataset.an], pick: true}); });
    const all = $('#wall', el); if (all) all.onclick = () => { closeModal(); addVideosModal({files: vids.slice(0, AV_MAX).map(w => w.path), pick: true}); };
  }, 'wide');
}
// one analysis as a card like the Editor's (0.4.3.5): a frame with the date it was analysed, the name, the length; the
// rhythm in one line; the next step with its button
// ---- thumbnail sets (0.4.5, the user: "I give 15 thumbnails from mr beast, it analyzes them and then sees common
// patterns like font, color, structure ... then that information can be used when im generating thumbnails"):
// analysis\thumbs\<set> (motionlab\thumbsets.py): the pictures only (no video), measured by the lab; Claude's
// /analyze-reference thumbs <set> writes the patterns (style.json); the user marks each one; Ready to post uses them
const THUMBS_JOBS = ['thumbs_fetch', 'thumbs_links', 'thumbs_measure', 'thumbs_more', 'thumbs_refresh', 'thumbs_fontmatch'];
// a set's pictures in order (the user, 2026-10-15: "add some filters like most viewed or less viewed ... and some data
// to the card like the date"): # = as added; views; date (YouTube's "3 weeks ago" = an approximate date, ≈)
const TS_SORTS = [['n', '#'], ['views_d', t('Most viewed|thumbnails')], ['views_a', t('Least viewed|thumbnails')], ['date_d', t('Newest|thumbnails')],
  ['date_a', t('Oldest|thumbnails')]];
// newest / oldest: the place in the channel's listing first (exact), else the date (a picture from a link)
const tsDay = it => Date.parse(it.upload_date || '') || 0;
const tsSortCmp = {n: (a, b) => a.n - b.n, views_d: (a, b) => (b.views ?? -1) - (a.views ?? -1), views_a: (a, b) => (a.views ?? Infinity) - (b.views ?? Infinity),
  date_d: (a, b) => (a.pos != null && b.pos != null ? a.pos - b.pos : tsDay(b) - tsDay(a)),
  date_a: (a, b) => (a.pos != null && b.pos != null ? b.pos - a.pos : (tsDay(a) || Infinity) - (tsDay(b) || Infinity))};
const tsSorted = (items, k) => items.slice().sort((a, b) => tsSortCmp[k](a, b) || a.n - b.n);
const COMPACT = LANG === 'en' ? null : new Intl.NumberFormat(LANG, {notation: 'compact', maximumFractionDigits: 1});   // 1,2 mil
const compactNum = v => COMPACT ? COMPACT.format(v) : v >= 1e9 ? `${+(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `${+(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${Math.round(v / 1e3)}K` : String(v);
// an exact date as a date; an approximate one (YouTube's "3 weeks ago" read back) in the same words, not a false day
const AGO = {day: n => tn(n, '≈ {n} day ago', '≈ {n} days ago'), week: n => tn(n, '≈ {n} week ago', '≈ {n} weeks ago'),
  month: n => tn(n, '≈ {n} month ago', '≈ {n} months ago'), year: n => tn(n, '≈ {n} year ago', '≈ {n} years ago')};
const dayWords = (d, approx) => { const m = /^(\d{4})-(\d\d)-(\d\d)$/.exec(d || ''); if (!m) return '';
  if (!approx) return `${+m[3]} ${MONTHS[+m[2] - 1]} ${m[1]}`;
  const days = Math.max(0, Math.round((Date.now() - Date.UTC(+m[1], +m[2] - 1, +m[3])) / 864e5));
  const [n, w] = days < 14 ? [days, 'day'] : days < 60 ? [Math.round(days / 7), 'week'] : days < 365 ? [Math.round(days / 30), 'month'] : [Math.round(days / 365), 'year'];
  return n === 0 ? t('≈ today') : AGO[w](n); };
const lenOf = s => s == null ? '' : s >= 3600 ? `${Math.floor(s / 3600)}:${pad(Math.floor(s % 3600 / 60))}:${pad(Math.round(s % 60))}` : `${Math.floor(s / 60)}:${pad(Math.round(s % 60))}`;
let TS_SORT = 'n';
const setSlug = s => String(s || '').normalize().replace(/[^\p{L}\p{N}_\-. ]+/gu, '_').trim().replace(/\s+/g, '_')
  .replace(/\.{2,}/g, '_').replace(/_{2,}/g, '_').replace(/^[_. ]+|[_. ]+$/g, '').slice(0, 80);
const hexOk = c => /^#[0-9a-f]{6}$/i.test(String(c || ''));
function setCard(s) {                               // s.label = the user's own name for the set (shown as it is)
  const tm = strTime(s.updated);
  return `<div class="card pcard setcard">${newTag(`ts:${s.name}@${Math.round(s.created || 0)}`, s.created)}<a class="clink" href="#/thumbs/${encodeURIComponent(s.name)}">
    <div class="ppic">${s.cover ? `<img src="${fileUrl(s.cover)}" loading="lazy" alt="">` : '<svg class="ic"><use href="#i-thumb"/></svg>'}
      <span class="pbadges">${s.has_style ? '' : `<span class="pbadge todo" title="${ta('Claude has not looked at them yet')}">${t('patterns not found yet')}</span>`}</span>
      ${tm ? `<span class="pwhen">${esc(whenWords(tm))}</span>` : ''}</div>
    <div class="cb"><span class="ct">${esc(s.label)}</span><div class="small">${s.channel_total ? t('{thumbnails} <span class="muted">of {total} on the channel</span>', {thumbnails: plural(s.count, 'thumbnail'), total: numStr(s.channel_total)})
      : plural(s.count, 'thumbnail')}${s.measured < s.count ? ' · ' + tn(s.measured, '{n} measured', '{n} measured') : ''}</div></div></a>
    <div class="pfacts"><span class="fchip sm">${t('Thumbnail set')}</span>${s.has_style ? `<span class="small ok">${t('✓ patterns found')}</span>` : ''}</div>
    <span class="pdel">${delBtn('thumbs', s.name)}</span></div>`;
}
// ---- Preview your thumbnail (2026-10-24, the user: "upload ur thumbnails and have it like a test on a fake generated
// yotubue page (updated if possible) like a preview layout thumnbail to see if the thumnbail matches the vibe or pops
// from a normal youtube user feed"): a full-window copy of today's YouTube layouts - Home grid, Search, the Up next
// column, a phone - with the user's pictures among big channels' newest, most viewed videos (then: "besides big
// youtubers like mrbeast ... probably of highly viewed recent videos" - motionlab\thumbfeed.py, the job thumb_feed,
// *Channels…* = the list) or the real thumbnails of the sets analysed here (GET /api/thumbtest: their titles, channels,
// views, lengths), and ones made in MotionLab (Ready to post). Dark / light, Shuffle, Squint (a blur: what still reads
// is what pops), Where is mine? Nothing is saved: the pictures stay in this window.
function thumbTest() {
  const o = document.createElement('div'); o.className = 'yttest';
  const T = {mine: [], layout: 'home', theme: 'dark', blur: false, set: '', seed: 1, pool: [], made: [], sets: [], big: {}, busy: false, edit: false};
  const cf = new Intl.NumberFormat(LANG === 'es' ? 'es-ES' : 'en-US', {notation: 'compact', maximumFractionDigits: 1});
  const views = n => t('{n} views', {n: cf.format(n || 0)});
  const AGES = [[1, 'hour'], [5, 'hour'], [1, 'day'], [3, 'day'], [1, 'week'], [2, 'week'], [3, 'week'], [1, 'month'], [4, 'month'], [1, 'year']];
  const ago = k => { const [n, u] = AGES[k % AGES.length];
    return u === 'hour' ? tn(n, '{n} hour ago', '{n} hours ago') : u === 'day' ? tn(n, '{n} day ago', '{n} days ago')
      : u === 'week' ? tn(n, '{n} week ago', '{n} weeks ago') : u === 'month' ? tn(n, '{n} month ago', '{n} months ago') : tn(n, '{n} year ago', '{n} years ago'); };
  const dur = s => { s = Math.round(+s || 0); if (!s) return ''; const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
    return h ? `${h}:${pad(m)}:${pad(x)}` : `${m}:${pad(x)}`; };
  const rnd = k => { let x = Math.sin(T.seed * 9301 + k * 49297) * 233280; return x - Math.floor(x); };
  const HUES = [4, 28, 48, 140, 190, 215, 265, 300, 330];
  const avatar = (name, k) => `<span class="ytav" style="background:hsl(${HUES[(name || '?').charCodeAt(0) % HUES.length]} 55% ${T.theme === 'dark' ? 38 : 58}%)">${esc((name || '?').trim().charAt(0).toUpperCase())}</span>`;
  // the feed: the pool (one set or all), shuffled by the seed, the user's pictures put among the first ones seen
  const feed = (n, shift = 0) => {
    const pool = T.pool.filter(x => !T.set || x.set === T.set).map((x, i) => ({...x, k: i})).sort((a, b) => rnd(a.k) - rnd(b.k));
    const items = [];
    for (let i = 0; i < n; i++) items.push(pool.length ? {...pool[i % pool.length], k: i} : {k: i, blank: true});
    const slots = [1, 6, 9, 3, 11, 4].map(s => (s + shift + Math.floor(rnd(97) * 3)) % Math.max(n, 1));
    T.mine.forEach((m, j) => { const at = slots[j % slots.length]; items.splice(at, 0, {...m, mine: true, k: 1000 + j}); });
    return items.slice(0, Math.max(n, T.mine.length));
  };
  const med = () => { const v = T.pool.map(x => x.views).filter(Boolean).sort((a, b) => a - b); return v.length ? v[Math.floor(v.length / 2)] : 12000; };
  const meta = x => x.mine ? `${views(med())} · ${ago(2)}` : `${views(x.views)} · ${ago(x.k + Math.floor(rnd(x.k) * 4))}`;
  const pic = (x, cls = '') => x.blank ? `<span class="ytpic blank ${cls}"></span>`
    : `<span class="ytpic ${cls}${x.mine ? ' mine' : ''}"><img src="${esc(x.src || fileUrl(x.img))}" alt="" loading="lazy">${x.duration || x.mine ? `<i class="ytdur">${x.mine ? esc(x.len || '8:24') : dur(x.duration)}</i>` : ''}${!x.mine && rnd(x.k + 7) > 0.86 ? `<b class="ytwatched" style="width:${Math.round(20 + rnd(x.k) * 70)}%"></b>` : ''}</span>`;
  const title = x => x.blank ? '<span class="ytline"></span><span class="ytline short"></span>' : esc(x.title || t('Your video title'));
  const chan = x => x.blank ? '' : esc(x.channel || '');
  const VIEWS = {
    home: () => `<div class="ytchips">${[t('All'), t('Music'), t('Gaming'), t('Live'), t('Podcasts'), t('Recently uploaded'), t('New to you')].map((c, i) => `<span class="${i ? '' : 'on'}">${c}</span>`).join('')}</div>
      <div class="ytgrid">${feed(12).map(x => `<div class="ytcard">${pic(x)}<div class="ytinfo">${x.blank ? '<span class="ytav"></span>' : avatar(x.channel, x.k)}<div><b>${title(x)}</b><span>${chan(x)}</span><span>${x.blank ? '' : meta(x)}</span></div></div></div>`).join('')}</div>`,
    search: () => `<div class="ytsearch">${feed(6).map(x => `<div class="ytrow">${pic(x, 'big')}<div class="ytrinfo"><b>${title(x)}</b><span>${x.blank ? '' : meta(x)}</span>
        <span class="ytrch">${x.blank ? '' : avatar(x.channel, x.k)}${chan(x)}</span><span class="ytsnip">${x.blank ? '' : esc(t('Watch it to the end - the best part is the last minute.'))}</span></div></div>`).join('')}</div>`,
    upnext: () => { const L = feed(11, 2), first = L.find(x => !x.mine) || {blank: true};
      return `<div class="ytwatch"><div class="ytplayer">${first.blank ? '' : `<img src="${esc(first.src || fileUrl(first.img))}" alt="">`}<span class="ytbar"><i></i></span></div>
        <b class="ytwtitle">${title(first)}</b><div class="ytrch">${first.blank ? '' : avatar(first.channel, 0)}${chan(first)}</div></div>
        <div class="ytside">${L.filter(x => x !== first).slice(0, 10).map(x => `<div class="ytsrow">${pic(x, 'small')}<div><b>${title(x)}</b><span>${chan(x)}</span><span>${x.blank ? '' : meta(x)}</span></div></div>`).join('')}</div>`; },
    phone: () => `<div class="ytphone"><div class="ytpbar"><span class="ytlogo"><i></i>YouTube</span></div>${feed(6).map(x => `<div class="ytpcard">${pic(x)}<div class="ytinfo">${x.blank ? '<span class="ytav"></span>' : avatar(x.channel, x.k)}<div><b>${title(x)}</b><span>${x.blank ? '' : `${chan(x)} · ${meta(x)}`}</span></div></div></div>`).join('')}</div>`};
  const LAYOUTS = [['home', t('Home')], ['search', t('Search')], ['upnext', t('Up next')], ['phone', t('Phone')]];
  const draw = () => {
    const q = T.layout === 'search' ? (T.mine[0] || {}).title || '' : '';
    o.innerHTML = `<div class="yttools"><b class="yttt"><svg class="i"><use href="#i-thumb"/></svg>${t('Preview your thumbnail')}</b>
        <label class="btn sm pri"><svg class="i"><use href="#i-upload"/></svg>${t('Add your thumbnail…')}<input type="file" hidden multiple accept="image/*,.heic,.avif"></label>
        ${T.made.length ? `<select class="ytmade"><option value="">${t('Or one made in MotionLab…')}</option>${T.made.map((m, i) => `<option value="${i}">${esc(m.video)} · ${esc(m.img.split('/').pop())}</option>`).join('')}</select>` : ''}
        <span class="grow"></span>
        <div class="seg ytseg">${LAYOUTS.map(([k, l]) => `<button data-lay="${k}" class="${T.layout === k ? 'on' : ''}">${l}</button>`).join('')}</div>
        <div class="seg ytseg"><button data-th="dark" class="${T.theme === 'dark' ? 'on' : ''}">${t('Dark')}</button><button data-th="light" class="${T.theme === 'light' ? 'on' : ''}">${t('Light')}</button></div>
        <select class="ytset" title="${ta('The videos around yours')}"><option value="_big" ${T.set === '_big' ? 'selected' : ''}>${t('Big creators - newest, most viewed')}</option>${T.sets.map(s => `<option value="${esc(s.name)}" ${T.set === s.name ? 'selected' : ''}>${esc(s.label)}</option>`).join('')}<option value="" ${T.set === '' ? 'selected' : ''}>${t('All of them')}</option></select>
        <button class="btn sm${T.blur ? ' on' : ''}" data-blur title="${ta('Blurs the page: what you can still read from a distance is what pops')}">${t('Squint')}</button>
        <button class="btn sm" data-shuf>${t('Shuffle')}</button><button class="btn sm" data-where ${T.mine.length ? '' : 'disabled'}>${t('Where is mine?')}</button>
        <button class="btn sm" data-x>${t('Close')}</button></div>
      <div class="ytmine">${T.mine.map((m, i) => `<span class="ytm"><img src="${esc(m.src)}" alt=""><input type="text" data-mt="${i}" value="${esc(m.title)}" placeholder="${ta('Your video title')}"><input type="text" data-mc="${i}" value="${esc(m.channel)}" placeholder="${ta('Your channel')}" class="ytmc"><button data-mrm="${i}" title="${ta('Take it out')}">✕</button></span>`).join('')}
        ${T.mine.length ? '' : `<span class="small muted">${t('Add one or more of your thumbnails (16:9) - they show up among the others. Nothing is saved: the pictures stay in this window.')}</span>`}
        <span class="grow"></span>${feedLine()}</div>${T.edit ? chanEditor() : ''}
      <div class="ytpage yt-${T.theme}${T.blur ? ' blur' : ''} ytl-${T.layout}"><div class="ythead"><span class="ytburger"><i></i><i></i><i></i></span><span class="ytlogo"><i></i>YouTube</span>
          <span class="ytq"><span>${esc(q) || t('Search')}</span><i></i></span><span class="ytme">${avatar((T.mine[0] || {}).channel || '?', 0)}</span></div>
        <div class="ytbody yt-${T.layout}">${VIEWS[T.layout]()}</div></div>`;
    const inp = $('input[type=file]', o);
    inp.onchange = () => { [...inp.files].forEach(f => T.mine.push({src: URL.createObjectURL(f), title: f.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '), channel: T.me || t('You'), url: true})); inp.value = ''; draw(); };
    const mk = $('.ytmade', o); if (mk) mk.onchange = () => { const m = T.made[+mk.value]; if (m) T.mine.push({src: fileUrl(m.img), title: m.title, channel: T.me || t('You')}); draw(); };
    const ss = $('.ytset', o); if (ss) ss.onchange = () => { T.set = ss.value; draw(); };
    const gf = $('[data-getfeed]', o); if (gf) gf.onclick = getFeed;
    const ce = $('[data-chans]', o); if (ce) ce.onclick = () => { T.edit = !T.edit; draw(); };
    const cs = $('[data-chsave]', o); if (cs) cs.onclick = async () => {
      try { const r = await api('/api/thumbfeed/channels', {channels: $('.ytchans textarea', o).value.split('\n')});
        T.big.channels = r.channels; T.edit = false; getFeed(); } catch (e) { toast(e.message, 'err'); } };
    const cr = $('[data-chreset]', o); if (cr) cr.onclick = async () => {
      try { const r = await api('/api/thumbfeed/channels', {channels: []}); T.big.channels = r.channels; draw(); } catch (e) { toast(e.message, 'err'); } };
    $$('[data-lay]', o).forEach(b => b.onclick = () => { T.layout = b.dataset.lay; draw(); });
    $$('[data-th]', o).forEach(b => b.onclick = () => { T.theme = b.dataset.th; draw(); });
    $('[data-blur]', o).onclick = () => { T.blur = !T.blur; draw(); };
    $('[data-shuf]', o).onclick = () => { T.seed++; draw(); };
    $('[data-where]', o).onclick = () => { $$('.ytpic.mine', o).forEach(p => { p.classList.add('flash'); setTimeout(() => p.classList.remove('flash'), 1600); }); };
    $('[data-x]', o).onclick = close;
    const retitle = debounce(() => draw(), 600);
    $$('[data-mt]', o).forEach(x => x.oninput = () => { T.mine[+x.dataset.mt].title = x.value; retitle(); });
    $$('[data-mc]', o).forEach(x => x.oninput = () => { T.mine[+x.dataset.mc].channel = x.value; retitle(); });
    $$('[data-mrm]', o).forEach(b => b.onclick = () => { const [m] = T.mine.splice(+b.dataset.mrm, 1); if (m.url) URL.revokeObjectURL(m.src); draw(); });
    o.ondragover = e => e.preventDefault();
    o.ondrop = e => { e.preventDefault(); [...e.dataTransfer.files].filter(f => /^image\//.test(f.type) || /\.(heic|avif)$/i.test(f.name))
      .forEach(f => T.mine.push({src: URL.createObjectURL(f), title: f.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '), channel: T.me || t('You'), url: true})); draw(); };
  };
  // big channels' newest videos: what the feed holds, Get the newest videos (the job thumb_feed, followed here), Channels…
  const feedLine = () => { const B = T.big || {};
    return T.busy ? `<span class="small amber">${t('Getting the newest videos of big channels…')}</span>`
      : `<span class="small muted">${B.count ? t('{n} videos of big channels · {when}', {n: B.count, when: esc(B.fetched || '')}) : t('No videos of big channels yet')}</span>
        ${!B.count || B.stale ? `<button class="btn sm pri" data-getfeed title="${ta('Lists the newest videos of big channels and downloads their thumbnails - no video is downloaded')}">${t('Get the newest videos')}</button>` : ''}
        <button class="btn sm ghost" data-chans>${t('Channels…')}</button>`; };
  const chanEditor = () => `<div class="ytchans"><span class="small muted">${t('The channels the feed comes from, one per line (@handle or a channel link):')}</span>
      <textarea rows="6">${esc((T.big.channels || []).join('\n'))}</textarea><div class="row"><button class="btn sm pri" data-chsave>${t('Save and get their videos')}</button>
      <button class="btn sm ghost" data-chreset>${t('Back to the usual ones')}</button></div></div>`;
  const load = async () => { const r = await api('/api/thumbtest'); T.pool = r.pool || []; T.made = r.made || []; T.sets = r.sets || []; T.big = r.big || {}; return r; };
  const getFeed = async () => {
    let j;
    try { j = await api('/api/jobs', {kind: 'thumb_feed', args: {}, queue: true}); } catch (e) { toast(e.message, 'err'); return; }
    T.busy = true; draw();
    for (;;) {
      await new Promise(r => setTimeout(r, 2000));
      if (!o.isConnected) return;
      let s; try { s = await api(`/api/jobs/${j.id}?since=0`); } catch (e) { continue; }
      if (['running', 'queued', 'cancelling'].includes(s.status)) continue;
      T.busy = false;
      if (s.status !== 'done') toast(t('Could not get the newest videos: {why}', {why: (s.log || []).slice(-1)[0] || s.status}), 'err');
      try { await load(); if (T.big.count) T.set = '_big'; } catch (e) { /* the old feed */ }
      draw(); return;
    }
  };
  const key = e => { if (e.key === 'Escape' && !/^(INPUT|SELECT|TEXTAREA)$/.test((document.activeElement || {}).tagName)) { e.preventDefault(); e.stopPropagation(); close(); } };
  const close = () => { T.mine.forEach(m => m.url && URL.revokeObjectURL(m.src)); o.remove(); window.removeEventListener('keydown', key, true); };
  window.addEventListener('keydown', key, true);
  document.body.append(o);
  o.innerHTML = `<div class="loading">${t('Loading…')}</div>`;
  Promise.all([load(), api('/api/settings').catch(() => ({}))]).then(([r, S]) => {
    T.me = ((S.settings || {}).author || '').replace(/-/g, ' ');
    T.set = T.big.count || !T.sets.length ? '_big' : '';
    draw();
    if (!T.big.count || T.big.stale) getFeed();                    // the first look: fetch them at once
  }).catch(e => { toast(e.message, 'err'); close(); });
}
// a picture the user picked or dropped -> the set (a raw body, like Film it's uploads; the server copies it in)
function uploadThumb(set, file) {
  return fetch(`/api/thumbs/${encodeURIComponent(set)}/upload?name=${encodeURIComponent(file.name)}`,
    {method: 'POST', headers: {'X-ML-Token': TOKEN, 'Content-Type': 'application/octet-stream'}, body: file})
    .then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok || j.error) throw new Error(j.error || r.statusText); return j; });
}
async function addThumbsModal(pre = {}) {
  const ST = await api('/api/settings'), yt = ST.tools.find(x => x.name === 'yt-dlp') || {};
  const st = {from: 'channel', n: '15', order: 'newest'}, files = [];
  modal(`<h2>${pre.set ? t('Add more thumbnails') : t('Add thumbnails')}</h2>
    <div class="small muted" style="margin-top:-4px">${t("Only the pictures, their titles and views are kept - no video is downloaded, and they stay on this PC. Then Claude finds what they have in common: the text, the font's style, the colours, the structure.")}</div>
    ${pre.set ? '' : `<div class="avstep"><b>1</b><span>${t('Name the set')}</span></div><input type="text" id="tsname" placeholder="${ta('e.g. MrBeast')}" maxlength="60" style="max-width:320px">`}
    <div class="avstep"><b>${pre.set ? 1 : 2}</b><span>${t('From where?')}</span></div>
    <div class="seg" id="tsfrom"><button data-v="channel">${t('A channel or playlist')}</button><button data-v="links">${t('Some videos')}</button><button data-v="files">${t('Pictures you have')}</button></div>
    <div class="tsf" data-f="channel"><input type="text" id="tsurl" placeholder="https://www.youtube.com/@MrBeast" style="width:100%">
      <div class="row small" style="margin-top:8px">${t('start with')} <div class="seg" id="tsn">${['10', '15', '20', '30'].map(v => `<button data-v="${v}">${v}</button>`).join('')}</div>
        <div class="seg" id="tsord"><button data-v="newest">${t('the newest|thumbnails')}</button><button data-v="views">${t('the most viewed|thumbnails')}</button></div></div>
      <div class="small muted" style="margin-top:6px">${t("MotionLab lists the whole channel (a few seconds) - add more from the set's page whenever you want. Claude reads them 15 to a sheet, so a bigger set takes Claude longer.")}</div></div>
    <div class="tsf" data-f="links"><textarea id="tslinks" rows="4" placeholder="${ta('One video link per line')}" style="width:100%"></textarea></div>
    <div class="tsf" data-f="files"><label class="tsdrop" id="tsdrop"><input type="file" id="tsfiles" accept=".jpg,.jpeg,.png,.webp" multiple hidden>
      <span>${t('Drop pictures here or <b>choose them</b> (.jpg .png .webp) - copies go into the set, your files stay where they are')}</span></label><div class="small muted" id="tsflist"></div></div>
    ${yt.found ? '' : `<div class="small amber" style="margin-top:6px">${t('Links need the downloader (yt-dlp): Settings → Programs. Your own pictures work without it.')}</div>`}
    <div class="row" style="margin-top:14px"><button class="btn pri big" id="tsgo" disabled><svg class="i"><use href="#i-thumb"/></svg>${t('Add the thumbnails')}</button><span class="small muted" id="tssum"></span></div>`, el => {
    const nameOf = () => pre.set || setSlug($('#tsname', el).value);
    const links = () => $('#tslinks', el).value.split(/\s+/).map(x => x.trim()).filter(Boolean);
    const upd = () => {
      $$('.tsf', el).forEach(x => x.hidden = x.dataset.f !== st.from);
      const url = $('#tsurl', el).value.trim(), L = links();
      const ready = nameOf() && (st.from === 'channel' ? /^https?:\/\/\S+$/i.test(url) && yt.found
        : st.from === 'links' ? L.length && L.every(u => /^https?:\/\/\S+$/i.test(u)) && yt.found : files.length);
      $('#tsgo', el).disabled = !ready;
      $('#tssum', el).textContent = !nameOf() ? t('Name the set first.') : st.from === 'files' ? (files.length ? plural(files.length, 'picture') : '') : '';
      $('#tsflist', el).textContent = files.map(f => f.name).join(' · ');
    };
    spSeg(el, '#tsfrom', st, 'from', upd); spSeg(el, '#tsn', st, 'n'); spSeg(el, '#tsord', st, 'order');
    ['#tsurl', '#tslinks'].forEach(s => $(s, el).oninput = upd);
    const nm = $('#tsname', el); if (nm) { nm.oninput = upd; nm.focus(); }
    const addF = list => { for (const f of list) if (/\.(jpe?g|png|webp)$/i.test(f.name) && !files.some(x => x.name === f.name && x.size === f.size)) files.push(f); upd(); };
    $('#tsfiles', el).onchange = e => { addF(e.target.files); e.target.value = ''; };
    const dz = $('#tsdrop', el);
    dz.ondragover = e => { e.preventDefault(); dz.classList.add('on'); };
    dz.ondragleave = () => dz.classList.remove('on');
    dz.ondrop = e => { e.preventDefault(); dz.classList.remove('on'); addF(e.dataTransfer.files); };
    $('#tsgo', el).onclick = async () => {
      const b = $('#tsgo', el), set = nameOf(), label = pre.set ? '' : $('#tsname', el).value.trim();
      b.disabled = true;
      try {
        if (st.from === 'files') {
          for (let i = 0; i < files.length; i++) { $('#tssum', el).textContent = t('copying {i} of {n}…', {i: i + 1, n: files.length}); await uploadThumb(set, files[i]); }
          closeModal(); toast(tn(files.length, '{n} picture added and measured', '{n} pictures added and measured'), 'ok');
          location.hash = '#/thumbs/' + encodeURIComponent(set);
          return;
        }
        const args = st.from === 'channel' ? {set, url: $('#tsurl', el).value.trim(), n: +st.n, order: st.order, label} : {set, urls: links()};
        await api('/api/jobs', {kind: st.from === 'channel' ? 'thumbs_fetch' : 'thumbs_links', args, queue: true});
        closeModal(); ping();
        toast(t('Getting the thumbnails - the set shows in the Analyser when they are in'), 'ok');
        if (location.hash !== '#/analyze/thumbs') location.hash = '#/analyze/thumbs'; else route();
      } catch (e) { toast(e.message, 'err'); b.disabled = false; }
    };
    upd();
  }, 'wide');
}
// one set (the user, 2026-10-15: "make 'What they have in common' a dropdown or pop up so they dont take up all space
// of the page ... i also want to look at the thumbnails while reviewing them"): the pictures in the main column; beside
// them a side panel with Claude's patterns that stays in view while the pictures scroll and folds away (◂ / ▸) - a
// click on a pattern lights up its example pictures; under the pictures the lab's own numbers, folded and labelled
// "MotionLab · no Claude" (the user: "be clear that it is only MotionLab NOT Claude"). Since 2026-10-18 the side panel
// is the one review panel (reviewPanel): Is Claude right? per pattern + a note, the count live, Send it to Claude =
// the patterns again with your verdicts (the skill reads verdicts.json first)
let TS_FOLD = false, TS_STOP = null;
async function pageThumbs(main, name) {
  const S = await api('/api/thumbs/' + encodeURIComponent(name));
  const ch = S.channel;                                // the whole channel listed once (0.4.5): its size, what is left
  const st = S.style, V = S.verdicts || {}, items = S.items || [], sm = S.summary || {}, enc = encodeURIComponent(S.name);
  const nf = v => numLoc(Number(v));
  const pats = (st && st.patterns) || [], f = (st && st.font) || {};
  // 0.4.6: the font, measured - the words Claude listed (style.json "texts") against the font library, by shape
  const FM = S.fontmatch, pct = x => Math.round((x || 0) * 100) + ' %';
  const pick = String(((st || {}).for_make || {}).font || (f.closest || [])[0] || '');     // Claude's first choice
  const guess = FM && pick && (FM.ranking || []).find(r => pick.startsWith(r.family));
  const fmRow = !st ? '' : FM && FM.best ? kvRow(t('Font, measured'), `<span class="mlchip sm" title="${ta('MotionLab compared the words on the pictures with every font it has, letter by letter - Claude only said where the words are')}">MotionLab</span>
      <b>${esc(FM.best.family)}</b> ${esc(FM.best.weight)} <span class="muted">· ${t('matches {pct} over {texts}, the best on {n}', {pct: pct(FM.best.score), texts: plural(FM.best.items, 'text'), n: FM.best.first_on})}</span>
      ${FM.best.runner_up ? `<div class="small muted">${t('then {font} {pct}', {font: esc(FM.best.runner_up.family), pct: pct(FM.best.runner_up.score)})}${guess && guess.family !== FM.best.family ? ' · ' + t("Claude's guess {font} {pct}", {font: esc(guess.family), pct: pct(guess.score)}) : ''}</div>` : ''}
      <button class="btn sm ghost" id="tsfm" title="${ta('again, e.g. after you added a font (about 2 seconds, no Claude)')}">${t('Measure again')}</button>`)
    : (st.texts || []).length ? kvRow(t('Font, measured'), `<button class="btn sm" id="tsfm" title="${ta('the words Claude listed against every font MotionLab has, letter by letter (about 2 seconds, no Claude)')}">${t('Measure the font')}</button>`) : '';
  // what Claude found besides the patterns (under the panel's rows): the font, measured and named, colours, words, structure
  const facts = !st ? '' : `<div class="kv tskv">
        ${fmRow}
        ${f.style ? kvRow(FM && FM.best ? t("Font's style") : t('Font'), `${esc(f.style)}${(f.closest || []).length ? ` <span class="dim">- ${t('closest: {fonts}', {fonts: f.closest.map(esc).join(', ')})}</span>` : ''}${f.sure === false ? ` <span class="dim">${t('(a guess from the pictures)')}</span>` : ''}`) : ''}
        ${(st.colours || []).filter(hexOk).length ? kvRow(t('Colours'), st.colours.filter(hexOk).map(c => `<span class="swatch" style="background:${c}" title="${c}"></span>`).join('')) : ''}
        ${st.words ? kvRow(t('Words'), `${t('{avg} on average, at most {max}', {avg: numStr(st.words.median ?? '?'), max: numStr(st.words.max ?? '?')})}${st.words.case ? ' · ' + esc(st.words.case) : ''}`) : ''}
        ${(st.structures || []).length ? kvRow(t('Structure'), st.structures.map(s => `${esc(s.name)} (${esc(s.count)})`).join(' · ')) : ''}</div>
      <div class="small muted" style="margin-top:10px">${t('Use it in a video: <i>Ready to post</i> → Make a thumbnail yourself → <b>In the style of {name}</b>.', {name: esc(S.label || S.name)})}</div>`;
  const side = st ? '' : `<div class="row sp tsside-h"><h2>${t('What they have in common')}</h2><span class="clchip">Claude</span>
        <button class="btn sm ghost icon" id="tsfold" title="${ta('Fold it away')}">◂</button></div>
      <div class="small muted">${t("Claude has not looked at this set yet. It reads the numbered pictures and names what repeats - the text, the font's style, the colours, the structure, the faces - so <i>Ready to post</i> can make your thumbnails in this style.")}</div>`;
  const many = plural(items.length, 'thumbnail');
  main.innerHTML = `<div class="head"><div><div class="crumb"><a href="#/analyze/thumbs">${t('Analyser')}</a> / ${t('thumbnail set')}</div><h1>${esc(S.label || S.name)}</h1>
      <div class="sub">${ch && ch.total ? t('{thumbnails} of the {total} videos of {who}', {thumbnails: many, total: numStr(ch.total), who: esc(ch.who || t('the channel'))})
        : (S.source || {}).url ? t('{thumbnails} from {url}', {thumbnails: many, url: esc(S.source.url)}) : many}${S.updated ? ` · ${esc(whenStr(S.updated))}` : ''}</div></div>
      <div class="row">${delBtn('thumbs', S.name, '#/analyze/thumbs', t('Delete'))}</div></div>
    <div class="toprow">${claudeBtn(`/analyze-reference thumbs ${S.name}`, st ? t('Find the patterns again') : t('Find the patterns with Claude'), 'review', `thumbs ${S.name}`, st ? 'big tsfind' : 'pri big')}
      ${ch && ch.left !== 0 ? `<button class="btn big" id="tsnext" title="${ta('The next ones of {who} that are not in the set yet', {who: ch.who || t('the channel')})}"><svg class="i"><use href="#i-download"/></svg>${t('More from the channel')}${ch.left ? ` <span class="small muted">· ${tn(ch.left, '{n} left', '{n} left')}</span>` : ''}</button>` : ''}
      <button class="btn${ch && ch.left !== 0 ? '' : ' big'}" id="tsmore"><svg class="i"><use href="#i-thumb"/></svg>${t('Add more')}</button>
      <span class="grow"></span><button class="btn ghost" id="tsopen"${TS_FOLD ? '' : ' hidden'}>${t('What they have in common')} ▸</button></div>
    <div id="tsprog"></div>
    <div class="tslayout${TS_FOLD ? ' folded' : ''}">
      <div class="tsmain">
        <details class="panel tsmeas"><summary><h2>${t('Measured by MotionLab')}</h2><span class="mlchip" title="${ta("the app's own numbers, measured from the pictures - Claude was not involved")}">${t('MotionLab · no Claude')}</span>
          <span class="small muted">${t('colours, brightness, faces, where the text sits - numbers only')}</span></summary>
          ${(sm.colours || []).length ? `<div class="row" style="gap:6px;margin:10px 0 6px">${sm.colours.filter(c => hexOk(c.hex)).map(c => `<span class="swatch big" style="background:${c.hex}" title="${esc(tn(c.pictures, '{word} {hex} - in {n} pictures', '{word} {hex} - in {n} pictures', {word: t(c.word || ''), hex: c.hex}))}"></span>`).join('')}</div>` : ''}
          <ul class="tslines">${(S.lines || []).filter(l => !/^Claude's style|^Font, measured/.test(l)).map(l => `<li>${esc(l)}</li>`).join('')}</ul></details>
        <div class="row tssort"><span class="small muted">${t('Sort')}</span><div class="seg" id="tssort">${TS_SORTS.map(([k, l]) => `<button data-v="${k}">${l}</button>`).join('')}</div>
          <span class="grow"></span>${ch ? `<button class="btn sm ghost" id="tsrefresh" title="${ta('The channel listed again (seconds, nothing downloaded): the newest views, the dates, the lengths')}">${t('Update the views and dates')}</button>` : ''}</div>
        <div class="tsgrid">${tsSorted(items, TS_SORT).map(it => `<figure class="tscell" data-n="${it.n}"><img src="${fileUrl(it.path)}" loading="lazy" alt="">
          <figcaption><div class="tsct"><b>#${it.n}</b> ${esc(it.title || '')}</div>
            <div class="tscd">${[it.views != null ? `<span title="${esc(tn(it.views, '{n} views', '{n} views', {n: nf(it.views)}))}">${tn(it.views, '{n} views', '{n} views', {n: compactNum(it.views)})}</span>` : '',
              it.outperformer != null ? `<span class="${it.outperformer >= 1 ? 'ok' : ''}" title="${ta("views ÷ the channel's followers")}">${numStr(it.outperformer)}x</span>` : '',
              it.upload_date ? `<span title="${it.date_approx ? ta('about - YouTube only says how long ago') : ta('published')}">${dayWords(it.upload_date, it.date_approx)}</span>` : '',
              it.duration != null ? `<span title="${ta("the video's length")}">${lenOf(it.duration)}</span>` : ''].filter(Boolean).join('<i>·</i>') || `<span class="dim">${t('your picture')}</span>`}</div></figcaption>
          <button class="btn sm ghost icon tsrm" data-n="${it.n}" title="${ta('Take #{n} out of the set', {n: it.n})}">✕</button></figure>`).join('')}</div>
      </div>
      <aside class="${st ? '' : 'panel '}tsside" id="tsside">${side}</aside>
    </div>`;
  // a pattern lights up its example pictures (the current row of the panel; a second click lets it go)
  const light = pid => {
    const p = pats.find(x => x.id === pid), ex = new Set(p ? (p.examples || []).map(String) : []);
    $$('.tscell', main).forEach(c => { c.classList.toggle('hl', ex.has(c.dataset.n)); c.classList.toggle('dimmed', !!p && !ex.has(c.dataset.n)); });
    const first = p && $(`.tscell[data-n="${[...ex][0]}"]`, main);
    if (first) first.scrollIntoView({block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  };
  const post = rvQueue();
  if (st) reviewPanel($('#tsside', main), {
    title: `${t('What they have in common')} <span class="clchip" title="${ta('written by Claude from the numbered pictures')}">Claude</span>`,
    head: `<button class="btn sm ghost icon" id="tsfold" title="${ta('Fold it away - the pictures take the whole width')}">◂</button>`,
    top: st.summary ? `<details class="tssum"><summary class="small muted">${t('In short')} <span class="dim">· ${t('click to read')}</span></summary><p>${esc(st.summary)}</p></details>` : '',
    sections: [{id: 'patterns', ask: t('Is Claude right?'), intro: t('Click a pattern to light up its pictures, then say if it is really there.'), scale: 'claims', note: 'line',
      items: () => pats.map(p => ({id: p.id, label: `<span class="fchip sm">${esc(p.kind || '')}</span> <b>${esc(p.what || '')}</b>`,
        sub: `${esc(p.how_many || '')}${(p.examples || []).length ? ` · #${p.examples.map(esc).join(' #')}` : ''}`})),
      get: pid => V[pid] || {},
      set: (pid, a) => {                            // verdicts.json, one home - the note too since 2026-10-18
        const note = a.note.trim(), body = {patterns: {[pid]: {v: a.v, note}}};
        if (a.v || note) V[pid] = {v: a.v, note}; else delete V[pid];
        return post(() => api(`/api/thumbs/${enc}/verdicts`, body));
      },
      empty: t('Claude named no pattern in this set.')}],
    extra: {panel: facts}, start: false, deselect: true, onMove: (s, pid) => light(pid),
    send: {hint: t('Claude looks at the patterns again with your verdicts: it keeps the ones you marked correct and fixes or drops the rest.'),
      cmd: `/analyze-reference thumbs ${S.name}`, task: 'review', name: `thumbs ${S.name}`}});
  const lay = $('.tslayout', main);
  const fold = on => { TS_FOLD = on; lay.classList.toggle('folded', on); $('#tsopen', main).hidden = !on; };
  $('#tsfold', main).onclick = () => fold(true);
  $('#tsopen', main).onclick = () => fold(false);
  $('#tsmore', main).onclick = () => addThumbsModal({set: S.name});
  const sortSt = {sort: TS_SORT};
  spSeg(main, '#tssort', sortSt, 'sort', () => {        // the cards move; nothing is asked again
    TS_SORT = sortSt.sort;
    const grid = $('.tsgrid', main), cell = Object.fromEntries($$('.tscell', grid).map(c => [c.dataset.n, c]));
    tsSorted(items, TS_SORT).forEach(it => cell[it.n] && grid.appendChild(cell[it.n]));
  });
  const rf = $('#tsrefresh', main);
  if (rf) rf.onclick = async () => { rf.disabled = true;
    try { await api('/api/jobs', {kind: 'thumbs_refresh', args: {set: S.name}, queue: true}); ping(); } catch (e) { toast(e.message, 'err'); rf.disabled = false; } };
  const nx = $('#tsnext', main); if (nx) nx.onclick = () => moreThumbsModal(S, () => pageThumbs(main, S.name));
  const fmb = $('#tsfm', main);
  if (fmb) fmb.onclick = async () => { fmb.disabled = true;
    try { await api('/api/jobs', {kind: 'thumbs_fontmatch', args: {set: S.name}, queue: true}); ping(); } catch (e) { toast(e.message, 'err'); fmb.disabled = false; } };
  if (TS_STOP) TS_STOP();                             // the page's own progress: getting more, measuring - then redraw
  TS_STOP = progressPanel($('#tsprog', main), () => pageThumbs(main, S.name), THUMBS_JOBS, j => (j.args || {}).set === S.name);
  onCleanup(() => { if (TS_STOP) { TS_STOP(); TS_STOP = null; } });
  $$('.tsrm', main).forEach(b => b.onclick = async () => {
    try { await api(`/api/thumbs/${enc}/remove`, {n: +b.dataset.n}); pageThumbs(main, S.name); } catch (e) { toast(e.message, 'err'); }
  });
}
// More from the channel (the user, 2026-10-15: "if i have 100 thumbnails available for clavero or 150 for mrbeast and
// i already got 10, 20 i could choose to download other 20/30 batch"): the next n not in the set - the newest or the
// most viewed - from the listing the set keeps (asked for again when a day old); job thumbs_more
function moreThumbsModal(S, after) {
  const ch = S.channel, known = ch.left != null, st = {n: String(known ? Math.min(20, ch.left) : 20), order: 'newest'};
  const sizes = known ? [10, 20, 30, 50].filter(v => v < ch.left).map(String).concat([String(Math.min(ch.left, 100))]) : ['10', '20', '30', '50'];
  modal(`<h2>${t('More from {name}', {name: esc(ch.who || S.label || S.name)})}</h2>
    <div class="small muted" style="margin-top:-4px">${known ? t("{in_set} of the channel's {total} videos are in this set - {left} left.", {in_set: numStr(ch.in_set), total: numStr(ch.total), left: numStr(ch.left)}) : t('{n} are in this set - MotionLab lists the whole channel first (a few seconds).', {n: numStr(ch.in_set)})} ${t('Only their thumbnails, titles and views - no video.')}</div>
    <div class="avstep"><b>1</b><span>${t('How many?')}</span></div><div class="seg" id="tmn">${[...new Set(sizes)].map(v => `<button data-v="${v}">${known && +v === ch.left ? t('all {n}', {n: v}) : v}</button>`).join('')}</div>
    <div class="avstep"><b>2</b><span>${t('Which ones?')}</span></div>
    <div class="seg" id="tmo"><button data-v="newest">${t('the newest not in the set')}</button><button data-v="views">${t('the most viewed not in the set')}</button></div>
    <div class="small muted" id="tmsum" style="margin-top:12px"></div>
    <div class="row" style="margin-top:12px"><button class="btn pri big" id="tmgo"><svg class="i"><use href="#i-download"/></svg>${t('Add them')}</button></div>`, el => {
    const upd = () => { const total = (S.items || []).length + +st.n, sheets = Math.ceil(total / 15);
      $('#tmsum', el).innerHTML = t('The set will have <b>{total}</b> thumbnails - {sheets} for Claude when it finds the patterns again.', {total: numStr(total), sheets: plural(sheets, 'sheet')}); };
    spSeg(el, '#tmn', st, 'n', upd); spSeg(el, '#tmo', st, 'order', upd); upd();
    $('#tmgo', el).onclick = async () => {
      $('#tmgo', el).disabled = true;
      try { await api('/api/jobs', {kind: 'thumbs_more', args: {set: S.name, n: +st.n, order: st.order}, queue: true});
        closeModal(); ping(); toast(tn(+st.n, 'Getting {n} more thumbnails', 'Getting {n} more thumbnails'), 'ok'); after(); }
      catch (e) { toast(e.message, 'err'); $('#tmgo', el).disabled = false; }
    };
  });
}
// ---- scripts & prompts (2026-10-18, the user: "it should also be able to analize propmpts ... make sure it is able
// to handle batches or multiple at the same time, imagine i wanted to analize 10 prompts at the same time i could and
// it wouldnt allucinate"): a text set = analysis\texts\<set> (motionlab\textsets.py) around texts that live in the
// prompt library. MotionLab numbers and measures them; Claude checks one at a time and a tool checks every quote
// against the text (prompts.verify_check) - how far it got is read from the set's files, never from Claude's words
const TX_MAX = 20;
const TX_KINDS = ['shot', 'image', 'hook', 'script', 'brief'];
// a kind's count in words (2026-10-19, Spanish: tn() per kind, the English as before: "2 video prompts", "1 hook")
const TX_WORD = {shot: n => tn(n, '{n} video prompt', '{n} video prompts'), image: n => tn(n, '{n} image prompt', '{n} image prompts'),
  hook: n => tn(n, '{n} hook', '{n} hooks'), script: n => tn(n, '{n} talking script', '{n} talking scripts'), brief: n => tn(n, '{n} brief', '{n} briefs')};
const txKinds = k => Object.entries(k || {}).sort((a, b) => b[1] - a[1]).map(([x, n]) => TX_WORD[x] ? TX_WORD[x](n) : `${n} ${x}${n === 1 ? '' : 's'}`).join(' · ');
// whose they are (the dialog's question): Prepare lists only the user's own scripts (the analysed creators' stay in
// their set and the prompt library)
const TX_WHO = {tested: t('Your own - your scripts also show in Prepare, every text in the prompt library.'),
  creator: t("Someone else's - kept on this PC, in this set and the prompt library (Prepare lists only yours)."),
  found: t("Where they came from is not known - like a creator's, Prepare leaves them out.")};
function textSetCard(s) {
  const when = strTime(s.updated), left = Math.max(0, s.count - s.checked);
  const badge = !s.count ? '' : !s.checked ? `<span class="pbadge todo" title="${ta('Claude has not checked them yet')}">${t('not checked by Claude')}</span>`
    : left ? `<span class="pbadge todo" title="${ta('the others wait for Claude')}">${t('Claude checked {n} of {total}', {n: s.checked, total: s.count})}</span>`
    : `<span class="pbadge" title="${ta('every text checked - every word Claude quotes was found in its text')}">${t('Claude checked all')}</span>`;
  return `<div class="card pcard txcard">${newTag(`tx:${s.name}@${Math.round(s.created || 0)}`, s.created)}<a class="clink" href="#/texts/${encodeURIComponent(s.name)}">
    <div class="ppic txpic">${s.first ? `<span class="txq">“${esc(s.first)}”</span>` : '<svg class="ic"><use href="#i-texts"/></svg>'}
      <span class="pbadges">${badge}</span>${when ? `<span class="pwhen">${esc(whenWords(when))}</span>` : ''}</div>
    <div class="cb"><span class="ct">${esc(s.label)}</span><div class="small">${txKinds(s.kinds) || plural(s.count, 'text')}${s.to_sort ? ` · <span class="amber">${t('{files} for Claude to read', {files: plural(s.to_sort, 'file')})}</span>` : ''}</div></div></a>
    <div class="pfacts"><span class="fchip sm">${t('Scripts & prompts')}</span>${s.has_patterns ? `<span class="small ok">${t('✓ patterns found')}</span>` : ''}</div>
    ${left || s.to_sort ? `<div class="cact"><span class="small fnl grow">${s.checked ? t('{n} of {total} checked by Claude', {n: s.checked, total: s.count}) : t('Next: Claude checks each one, part by part')}</span>${claudeBtn(s.prompt, s.checked ? t('Continue with Claude') : t('Check them with Claude'), 'review', `texts ${s.name}`, 'sm pri')}</div>` : ''}
    <span class="pdel">${delBtn('texts', s.name)}</span></div>`;
}
// Add scripts & prompts: paste them (a line of only --- between two) or drop files; MotionLab numbers them at once
// (POST /api/texts/split - nothing is saved yet) and the kind of each can be changed; then whose they are, and Claude's
// check now (one window for all) or later. pre = {set, label, count, who, creator, after} for the set page's Add more
async function addTextsModal(pre = {}) {
  const [ST, EST] = await Promise.all([api('/api/settings'), api('/api/estimate').catch(() => ({}))]);
  const cl = ST.tools.find(x => x.name === 'claude') || {};
  const room = pre.set ? Math.max(0, TX_MAX - (pre.count || 0)) : TX_MAX;
  const st = {who: pre.who || 'tested'}, files = [], kinds = {};
  let P = {items: [], unread: [], new: 0};
  modal(`<h2>${pre.set ? t('Add to {name}', {name: esc(pre.label || pre.set)}) : t('Add scripts & prompts')}</h2>
    <div class="small muted" style="margin-top:-4px">${pre.set ? t('Talking scripts, hooks, prompts for AI video and image tools, briefs - up to {n} more in this set.', {n: room}) : t('Talking scripts, hooks, prompts for AI video and image tools, briefs - up to {n} at a time.', {n: room})}
      ${t('MotionLab saves each one word for word and numbers it; Claude then checks them one at a time, part by part - and MotionLab makes sure every word it quotes is really in the text.')}</div>
    ${pre.set ? '' : `<div class="avstep"><b>1</b><span>${t('Name the set')}</span>${optTag(t('the first words when empty'))}</div>
      <input type="text" id="txname" placeholder="${ta('e.g. Seedance prompts I like')}" maxlength="60" style="max-width:360px">`}
    <div class="avstep"><b>${pre.set ? 1 : 2}</b><span>${t('The texts')}</span><span class="small muted">${t('several? a line with only --- between them')}</span></div>
    <textarea id="txpaste" rows="8" style="width:100%" spellcheck="false" placeholder="${ta('Paste a script or a prompt here…\n---\n…and the next one')}"></textarea>
    <label class="tsdrop" id="txdrop" style="margin-top:8px"><input type="file" id="txfiles" accept=".txt,.md,.docx,.pdf" multiple hidden>
      <span>${t('…or drop files here or <b>choose them</b> (.txt .md .docx .pdf) - a file is one text, unless it has lines of ---')}</span></label>
    <div class="txprev" id="txprev"></div>
    <div class="avstep"><b>${pre.set ? 2 : 3}</b><span>${t('Whose are they?')}</span></div>
    <div class="seg" id="txwho"><button data-v="tested">${t('Mine')}</button><button data-v="creator">${t("A creator's")}</button><button data-v="found">${t('Found somewhere')}</button></div>
    <input type="text" id="txcr" placeholder="${ta('their name and / or a link')}" value="${esc(pre.creator || '')}" style="width:100%;max-width:520px;margin-top:8px" hidden>
    <div class="small muted" id="txwhoh" style="margin-top:6px"></div>
    <div class="avstep"><b>${pre.set ? 3 : 4}</b><span>${t("Claude's check")}</span></div>
    <label class="chk avclaude"><input type="radio" name="txc" value="1" ${cl.found ? 'checked' : 'disabled'}><span>${t("<b>Claude checks them now</b> (recommended) - one Claude Code window, one text at a time: each part clear, vague or missing in the text's own words, then what they have in common.")}${cl.found ? '' : ` <span class="bad">${t('Claude Code was not found - Settings.')}</span>`}
      <span class="small muted" id="txest"></span></span></label>
    <label class="chk avclaude"><input type="radio" name="txc" value="0" ${cl.found ? '' : 'checked'}><span>${t("<b>Only save them</b> - check them later from the set's page.")}</span></label>
    <div class="row" style="margin-top:14px"><button class="btn pri big" id="txgo" disabled><svg class="i"><use href="#i-texts"/></svg>${t('Add them')}</button><span class="small muted" id="txsum"></span></div>`, el => {
    const paste = $('#txpaste', el), prev = $('#txprev', el);
    const source = () => {
      if (st.who !== 'creator') return {type: st.who};
      const w = $('#txcr', el).value.trim(), link = (w.match(/https?:\/\/\S+/) || [''])[0];
      return {type: 'creator', creator: w.replace(link, '').replace(/[\s,-]+$/, '').trim(), link};
    };
    const live = x => !x.dup && !x.in_set;
    const draw = () => {
      prev.innerHTML = P.items.map(x => `<div class="txrow${x.problem && live(x) ? ' bad' : live(x) ? '' : ' dup'}"><b class="txn">#${x.i}</b>
          <select data-sha="${esc(x.sha)}" title="${esc(x.kind_why || '')}"${x.known || !live(x) ? ' disabled' : ''}>${TX_KINDS.map(k => `<option value="${k}"${k === x.kind ? ' selected' : ''}>${esc(KSHORT[k])}</option>`).join('')}</select>
          <span class="grow txpv" title="${esc(x.preview)}">${esc(x.preview)}</span>
          <span class="small muted">${plural(x.words, 'word')}${x.from && x.from.file ? ` · ${esc(x.from.file)}` : ''}</span>
          ${x.dup ? `<span class="small amber">${t('the same as {n} - added once', {n: esc(x.dup)})}</span>` : x.in_set ? `<span class="small amber">${t('in the set already ({n})', {n: esc(x.in_set)})}</span>`
            : x.known ? `<span class="small ok" title="${ta('the same words are in your prompt library already - that one is used, not a copy')}">${t('in your library')}</span>` : ''}
          ${x.problem && live(x) ? `<span class="small bad">${esc(x.problem)}</span>` : ''}</div>`).join('')
        + (P.unread || []).map(u => `<div class="txrow"><b class="txn">·</b><span class="grow txpv" title="${ta(u.why || '')}">${esc(u.file)}</span><span class="small amber">${t('Claude reads it')}</span></div>`).join('');
      $$('select[data-sha]', prev).forEach(s => s.onchange = () => { kinds[s.dataset.sha] = s.value; refresh(); });
      const n = P.new || 0, bad = P.items.some(x => x.problem && live(x)), un = (P.unread || []).length;
      const known = P.items.filter(x => x.known && live(x)).length, b = $('#txgo', el);
      b.disabled = (!n && !un) || n > room || bad;
      b.innerHTML = `<svg class="i"><use href="#i-texts"/></svg>${n > 1 ? t('Add these {n}', {n}) : n === 1 ? t('Add it') : un ? tn(un, 'Add the file', 'Add the files') : t('Add them')}`;
      $('#txsum', el).innerHTML = n > room ? `<span class="bad">${pre.set ? t('at most {n} more in this set', {n: room}) : t('at most {n} at a time', {n: room})}</span>`
        : bad ? `<span class="bad">${t('a text marked red cannot be checked - fix it or take it out')}</span>`
        : n || un ? [n && tn(n, '{n} text numbered', '{n} texts numbered'), known && t('{n} from your library', {n: known}), un && t('{files} for Claude to read', {files: plural(un, 'file')})].filter(Boolean).join(' · ')
        : t('Paste a script or a prompt, or drop a file.');
      $('#txest', el).innerHTML = ' ' + estWords(EST.texts, n, 'text') + '.';
    };
    let seq = 0;
    const refresh = async () => {
      const my = ++seq, text = paste.value;
      if (!text.trim() && !files.length) { P = {items: [], unread: [], new: 0}; draw(); return; }
      try {
        const r = await api('/api/texts/split', {text, files: files.map(f => f.file), kinds, source: source(), set: pre.set || ''});
        if (my === seq) { P = r; draw(); }
      } catch (e) { if (my === seq) { prev.innerHTML = `<div class="small bad">${esc(e.message)}</div>`; $('#txgo', el).disabled = true; } }
    };
    paste.oninput = debounce(refresh, 350);
    const addF = async list => {
      for (const f of [...list]) {
        if (!/\.(txt|md|docx|pdf)$/i.test(f.name)) { toast(t('{name}: a .txt, .md, .docx or .pdf file', {name: f.name}), 'err'); continue; }
        if (f.size > 30e6) { toast(t('{name}: files up to 30 MB', {name: f.name}), 'err'); continue; }
        try { const r = await api('/api/prompts/file', {name: f.name, data: b64(await f.arrayBuffer())}); if (!files.some(x => x.file === r.file)) files.push(r); }
        catch (e) { toast(e.message, 'err'); }
      }
      refresh();
    };
    $('#txfiles', el).onchange = e => { addF(e.target.files); e.target.value = ''; };
    const dz = $('#txdrop', el);
    dz.ondragover = e => { e.preventDefault(); dz.classList.add('on'); };
    dz.ondragleave = () => dz.classList.remove('on');
    dz.ondrop = e => { e.preventDefault(); dz.classList.remove('on'); addF(e.dataTransfer.files); };
    const whoH = () => { $('#txcr', el).hidden = st.who !== 'creator'; $('#txwhoh', el).textContent = TX_WHO[st.who]; };
    spSeg(el, '#txwho', st, 'who', () => { whoH(); if (st.who === 'creator') $('#txcr', el).focus(); });
    whoH();
    $('#txgo', el).onclick = async () => {
      const b = $('#txgo', el), claude = ($('input[name=txc]:checked', el) || {}).value === '1';
      b.disabled = true;
      const body = {text: paste.value, files: files.map(f => f.file), kinds, source: source()};
      try {
        const r = pre.set ? await api(`/api/texts/${encodeURIComponent(pre.set)}/add`, body)
          : await api('/api/texts/new', {...body, label: $('#txname', el).value.trim()});
        closeModal();
        toast(tn(r.added + r.reused, '{n} text numbered in {set}', '{n} texts numbered in {set}', {set: r.label}) + (r.to_sort ? ' · ' + t('{files} for Claude to read', {files: plural(r.to_sort, 'file')}) : ''), 'ok');
        if (claude) openClaude(r.command, 'review', `texts ${r.set}`);
        if (pre.after) pre.after();
        else if (location.hash !== '#/analyze/texts') location.hash = '#/analyze/texts'; else route();
      } catch (e) { toast(e.message, 'err'); b.disabled = false; }
    };
    (pre.set ? paste : $('#txname', el)).focus();
    draw();
  }, 'wide');
}
// a text on its card: the first words - or, with a pattern lit, the part around the words it quotes, marked (spans =
// the tool's "at": the text's own characters, so the mark cannot drift)
function txExcerpt(text, spans) {
  const t = String(text || '');
  if (!spans || !spans.length) { const s = t.trim().replace(/\s+/g, ' '); return esc(s.length > 260 ? s.slice(0, 257) + '…' : s); }
  const sp = spans.slice().sort((x, y) => x[0] - y[0]);
  const a = Math.max(0, sp[0][0] - 80), b = Math.min(t.length, Math.max(sp[0][1] + 80, Math.min(sp[sp.length - 1][1] + 40, sp[0][0] + 520)));
  let out = a > 0 ? '…' : '', pos = a;
  for (const [s, e] of sp) { if (s < pos || e > b) continue; out += esc(t.slice(pos, s)) + `<mark class="tq">${esc(t.slice(s, e))}</mark>`; pos = e; }
  return out + esc(t.slice(pos, b)) + (b < t.length ? '…' : '');
}
function txCell(it) {
  const r = it.rec, f = it.facts || {};
  if (!r) return `<figure class="txcell gone" data-n="${it.n}"><div class="txct"><b>#${it.n}</b></div><div class="small muted">${t('Deleted from your prompt library.')}</div>
    <button class="btn sm ghost icon tsrm" data-n="${it.n}" title="${ta('Take #{n} out of the set', {n: it.n})}">✕</button></figure>`;
  const c = r.counts || {}, sc = f.script;
  const chk = it.checked ? `<span class="pill clear" title="${ta('parts Claude found clear')}">✓ ${c.clear || 0}</span><span class="pill vague" title="${ta('vague|parts')}">~ ${c.vague || 0}</span><span class="pill missing" title="${ta('missing|parts')}">✗ ${c.missing || 0}</span>${r.stars != null ? pstars(r.stars) : ''}`
    : it.stale ? `<span class="amber" title="${ta('its kind changed after Claude checked it')}">${t('checked as another kind')}</span>` : `<span class="amber">${t('not checked yet')}</span>`;
  const rate = r.rating ? `<span class="vr ${esc(r.rating)}" title="${ta('what it made - your rating')}">${r.rating === 'ok' ? t('OK') : r.rating === 'good' ? t('Good') : r.rating === 'bad' ? t('Bad') : esc(r.rating[0].toUpperCase() + r.rating.slice(1))}</span>` : '';
  return `<figure class="txcell" data-n="${it.n}" data-id="${esc(it.id)}" tabindex="0" title="${ta("Open it: the text, Claude's check part by part, your verdicts")}">
    <div class="txct"><b>#${it.n}</b><span class="kbadge k-${esc(it.kind)}" title="${esc(it.kind_why || '')}">${esc(KSHORT[it.kind] || it.kind)}</span>${r.source === 'creator' ? `<span class="small dim">${esc(r.creator || t("someone else's"))}</span>` : ''}</div>
    <b class="txtitle">${esc(r.title || f.title || '')}</b>
    <div class="txex">${txExcerpt(it.text)}</div>
    <div class="txcd"><span>${plural(f.words || 0, 'word')}${sc && sc.seconds ? ` · ≈ ${fmtSecs(sc.seconds)}` : ''}</span>${chk}${rate}</div>
    <button class="btn sm ghost icon tsrm" data-n="${it.n}" title="${ta('Take #{n} out of the set - it stays in your prompt library', {n: it.n})}">✕</button></figure>`;
}
const txSig = S => JSON.stringify([S.state.checked, S.state.left, S.state.patterns, (S.patterns || {}).date, (S.items || []).length, S.updated]);
// one set (#/texts/<set>), laid out like a thumbnail set: the texts in the main column - the lab's own numbers above
// them, folded ("MotionLab · no Claude") - and Claude's patterns in the review panel (reviewPanel, the one review
// pattern - 2026-10-19, as on a thumbnail set); a pattern lights up its texts and marks the words each example quotes;
// a card opens its prompt (Claude's check part by part). While Claude works on this set (the heartbeat's live line
// names it), the cards follow every 4 s
let TX_FOLD = false, TX_POLL = null;
async function pageTexts(main, name) {
  const S = await api('/api/texts/' + encodeURIComponent(name));
  const st = S.state, items = S.items || [], P = S.patterns, V = S.verdicts || {}, enc = encodeURIComponent(S.name), src = S.source || {};
  const pats = (P && P.patterns) || [];
  // a pattern's kind (textsets.PATTERN_KINDS) as the page says it; the kind itself stays the id
  const PKIND = {hook: t('hook|pattern kind'), structure: t('structure|pattern kind'), wording: t('wording|pattern kind'),
    camera: t('camera|pattern kind'), look: t('look|pattern kind'), length: t('length|pattern kind'), cta: t('cta|pattern kind'),
    voice: t('voice|pattern kind'), format: t('format|pattern kind'), other: t('other|pattern kind')};
  const byN = Object.fromEntries(items.map(it => [String(it.n), it])), label = `texts ${S.name}`;
  const go = !st.checked ? claudeBtn(st.prompt, t('Check them with Claude'), 'review', label, 'pri big')
    : st.left.length || st.to_sort.length || (st.items >= 3 && st.patterns !== 'ok')
      ? claudeBtn(st.prompt, t('Continue with Claude') + (st.left.length ? ' · ' + tn(st.left.length, '{n} left', '{n} left') : ''), 'review', label, 'pri big')
      : claudeBtn(st.prompt, t('Check them again'), 'review', label, 'big tsfind');
  const how = st.done ? `<span class="small ok">${t('✓ every text checked - every word Claude quotes was found in its text')}</span>`
    : st.to_sort.length ? `<span class="small amber">${t('{files} for Claude to read first: {names}', {files: plural(st.to_sort.length, 'file'), names: esc(st.to_sort.join(', '))})}</span>`
    : st.left.length && st.checked ? `<span class="small muted">${t('not checked yet: #{list}', {list: st.left.join(' #')})}</span>`
    : !st.left.length && st.items >= 3 && st.patterns !== 'ok' ? `<span class="small muted">${t('next: Claude names what they have in common')}</span>` : '';
  const claudeChip = `<span class="clchip" title="${ta('Claude names it; MotionLab finds every example it quotes in its text and counts them')}">Claude</span>`;
  const foldBtn = `<button class="btn sm ghost icon" id="txfold" title="${ta('Fold it away - the texts take the whole width')}">◂</button>`;
  // no patterns yet: the side says what Claude does there; with patterns it is the review panel (below)
  const side = P ? '' : `<div class="row sp tsside-h"><h2>${t('What they have in common')}</h2>${claudeChip}${foldBtn}</div>
    <div class="small muted">${st.items < 2 ? t('With 2 texts or more, Claude names what they have in common.')
      : t('Claude has not named what they have in common yet. Once each text is checked, it names what repeats - the hook, the structure, the wording, the camera, the look - and MotionLab finds every example it quotes in its text and counts them.')}</div>`;
  main.innerHTML = `<div class="head"><div><div class="crumb"><a href="#/analyze/texts">${t('Analyser')}</a> / ${t('scripts & prompts')}</div><h1>${esc(S.label || S.name)}</h1>
      <div class="sub">${txKinds((S.summary || {}).kinds) || plural(st.items, 'text')} · ${t('Claude checked {n} of {total}', {n: st.checked, total: st.items})}${S.updated ? ` · ${esc(whenStr(S.updated))}` : ''}</div></div>
      <div class="row">${delBtn('texts', S.name, '#/analyze/texts', t('Delete'))}</div></div>
    <div class="toprow">${go}
      <button class="btn" id="txmore"${st.items >= TX_MAX ? ` disabled title="${ta('A set holds up to {n} texts', {n: TX_MAX})}"` : ''}><svg class="i"><use href="#i-texts"/></svg>${t('Add more')}</button>
      ${how}${st.disputed.length ? `<span class="small amber">${t('you marked parts of #{list} wrong or partly - Claude checks them again with your notes', {list: st.disputed.join(' #')})}</span>` : ''}
      <span class="grow"></span><button class="btn ghost" id="txopen"${TX_FOLD ? '' : ' hidden'}>${t('What they have in common')} ▸</button></div>
    <div class="tslayout${TX_FOLD ? ' folded' : ''}">
      <div class="tsmain">
        <details class="panel tsmeas"><summary><h2>${t('Measured by MotionLab')}</h2><span class="mlchip" title="${ta('counted from the words - Claude was not involved')}">${t('MotionLab · no Claude')}</span>
          <span class="small muted">${t('kinds, length, the words they share, twins - counted, not read')}</span></summary>
          <ul class="tslines">${(S.lines || []).map(l => `<li>${esc(l)}</li>`).join('')}</ul></details>
        <div class="txgrid">${items.map(txCell).join('')}</div>
      </div>
      <aside class="${P ? '' : 'panel '}tsside" id="txside">${side}</aside>
    </div>`;
  const redraw = async () => {                          // the same page again, where it was (not if the user went on)
    if (location.hash.split('?')[0] !== '#/texts/' + enc) return;
    if (rp) { await rp.flush(); rp.destroy(); }         // a note being typed is saved first
    const y = main.scrollTop; await pageTexts(main, S.name); main.scrollTop = y;
  };
  // a pattern (the panel's current row; a second click lets it go) lights up its texts and marks the words each of its
  // examples quotes
  const light = pid => {
    const p = pid ? pats.find(x => x.id === pid) : null, at = {};
    (p ? p.examples || [] : []).forEach(e => { (at[e.n] = at[e.n] || []).push(...(e.at || [])); });
    const on = new Set((p ? p.items || (p.examples || []).map(x => x.n) : []).map(String));
    $$('.txcell', main).forEach(c => {
      const hit = on.has(c.dataset.n), it = byN[c.dataset.n], ex = $('.txex', c);
      c.classList.toggle('hl', hit); c.classList.toggle('dimmed', !!p && !hit);
      if (ex && it) ex.innerHTML = txExcerpt(it.text, hit ? at[c.dataset.n] : null);
    });
    const first = p && $('.txcell.hl', main);
    if (first) first.scrollIntoView({block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  };
  const post = rvQueue();
  const rp = !P ? null : reviewPanel($('#txside', main), {
    title: t('What they have in common') + ' ' + claudeChip, head: foldBtn,
    top: P.summary ? `<details class="tssum"><summary class="small muted">${t('In short')} <span class="dim">· ${t('click to read')}</span></summary><p>${esc(P.summary)}</p></details>` : '',
    stale: st.patterns === 'stale' ? t('The set changed since Claude found these - Continue with Claude looks again.') : '',
    sections: [{id: 'patterns', ask: t('Is Claude right?'), intro: t('Click a pattern to light up its texts and the words it quotes, then say if it is really there.'), scale: 'claims', note: 'line',
      items: () => pats.map(p => { const ns = p.items || [...new Set((p.examples || []).map(x => x.n))];
        // how_many = the tool's "k of N" (textsets.py); said in the page's language when it is exactly that
        const hm = p.how_many || '', kof = p.k != null && p.of != null && hm === `${p.k} of ${p.of}`;
        return {id: p.id, label: `<span class="fchip sm">${esc(PKIND[p.kind] || p.kind || '')}</span> <b>${esc(p.what || '')}</b>`,
          sub: `<span title="${ta('counted by MotionLab from the examples it found in the texts')}">${kof ? t('{n} of {total}', {n: p.k, total: p.of}) : esc(hm)}</span>${ns.length ? ` · #${ns.map(esc).join(' #')}` : ''}`}; }),
      get: pid => V[pid] || {},
      set: (pid, a) => {                            // the set's verdicts.json (one home), the note too
        const note = a.note.trim();
        if (a.v || note) V[pid] = {v: a.v, note}; else delete V[pid];
        return post(() => api(`/api/texts/${enc}/verdicts`, {patterns: {[pid]: {v: a.v, note}}}));
      },
      empty: t('Claude named no pattern in this set.')}],
    start: false, deselect: true, onMove: (s, pid) => light(pid),
    send: {hint: t('Claude finishes what is left, then looks at the patterns again with your verdicts: it keeps the ones you marked correct, fixes the partly ones by your note and drops or redoes the wrong ones.'),
      cmd: st.prompt, task: 'review', name: label}});
  const lay = $('.tslayout', main);
  const fold = on => { TX_FOLD = on; lay.classList.toggle('folded', on); $('#txopen', main).hidden = !on; };
  $('#txfold', main).onclick = () => fold(true);
  $('#txopen', main).onclick = () => fold(false);
  $('#txmore', main).onclick = () => addTextsModal({set: S.name, label: S.label, count: st.items, after: redraw,
    who: src.type === 'creator' ? (src.creator || src.link ? 'creator' : 'found') : 'tested', creator: [src.creator, src.link].filter(Boolean).join(' ')});
  // a card = its prompt (the review area adds Previous / Next through ctx.ids and the quoted words lit from "at")
  const ctx = {set: S.name, ids: items.filter(it => it.rec).map(it => it.id), R: null,
    reload: async () => { ctx.R = await api('/api/prompts'); }, draw: () => redraw()};
  $$('.txcell[data-id]', main).forEach(c => {
    const open = async () => { try { if (!ctx.R) await ctx.reload(); promptModal(c.dataset.id, ctx); } catch (e) { toast(e.message, 'err'); } };
    c.onclick = e => { if (!e.target.closest('.tsrm')) open(); };
    c.onkeydown = e => { if (e.key === 'Enter' && e.target === c) open(); };
  });
  $$('.tsrm', main).forEach(b => b.onclick = async e => {
    e.stopPropagation();
    try { await api(`/api/texts/${enc}/remove`, {n: +b.dataset.n}); toast(t('#{n} is out of the set - it stays in your prompt library', {n: b.dataset.n}), 'ok'); redraw(); }
    catch (err) { toast(err.message, 'err'); }
  });
  if (TX_POLL) clearInterval(TX_POLL);
  let busy = LIVE.some(x => x.texts === S.name);
  const sig = txSig(S);
  TX_POLL = setInterval(async () => {
    const now = LIVE.some(x => x.texts === S.name);
    if (!now && !busy) return;
    busy = now;                                         // one more look after Claude's turn ends
    try { if (txSig(await api('/api/texts/' + enc)) !== sig) redraw(); } catch (e) { /* the next tick */ }
  }, 4000);
  onCleanup(() => { if (TX_POLL) { clearInterval(TX_POLL); TX_POLL = null; } });
}
function refCard(r) {
  const fl = r.flow, when = strTime(r.generated), P = r.pacing || {}, fmt = ((r.format || {}).label || '').split(' · ')[0];   // the shape only: the length is shown
  return `<div class="card pcard refcard ${fl.next ? 'n-' + fl.next : 'n-done'}">${newTag(`r:${r.name}@${Math.round(r.done_t || 0)}`, r.done_t)}<a class="clink" href="#/ref/${encodeURIComponent(r.name)}">
    <div class="ppic">${r.thumb ? `<img src="${fileUrl(r.thumb)}" loading="lazy" alt="">` : '<svg class="ic"><use href="#i-analyze"/></svg>'}
      <span class="pbadges">${fl.next === 'claude' ? `<span class="pbadge todo" title="${ta('Claude has not checked its effects yet')}">${t('not checked by Claude')}</span>` : ''}</span>
      ${when ? `<span class="pwhen" title="${ta('analysed {when}', {when: r.generated})}">${esc(whenWords(when))}</span>` : ''}</div>
    <div class="cb"><span class="ct"${r.label && r.label !== r.title ? ` title="${esc(r.title)}"` : ''}>${esc(r.label || r.title)}</span><div class="small">${[lenWords(r.frames, r.fps), r.category ? esc(t(r.category_label || '')) : '', fmt ? `<span class="muted">${esc(t(fmt))}</span>` : ''].filter(Boolean).join(' · ')}</div></div></a>
    <div class="pfacts"><span>${P.cuts_per_min != null ? t('<b>{n}</b> cuts/min', {n: numStr(P.cuts_per_min)}) + ' · ' : ''}${tn(r.events, '<b>{n}</b> effect', '<b>{n}</b> effects')}</span>${focusChip(r.focus)}</div>
    <div class="cact"><span class="small fnl grow ${fl.next ? '' : 'ok'}">${esc(flowNext(fl))}</span>${flowAction(r, fl)}</div>
    <span class="pdel">${delBtn('reference', r.name)}</span></div>`;
}
// the Analyser (2026-10-18, the user: "improve the "analyser" ... create the big 3 buttons similar to prepare section
// but for "videos" "thumnbails" "scripts""): three ways like Prepare's, then what is running / left / waiting, then one
// tab per kind with its count - a kind is known before clicking and nothing important sits under a list (the user,
// 2026-10-15); an empty lab = the three ways (no emptyHero). #/analyze = Videos, #/analyze/videos is the same
const AN_TABS = [['videos', t('Videos'), 'videos', '#/analyze'], ['thumbs', t('Thumbnails'), 'thumb', '#/analyze/thumbs'],
                 ['texts', t('Scripts & prompts'), 'texts', '#/analyze/texts']];
async function pageRefs(main, tab) {
  tab = AN_TABS.some(x => x[0] === tab) ? tab : 'videos';
  let tests = false, cat = '', tag = '', foc = '';
  let stopProgress = null;
  onCleanup(() => stopProgress && stopProgress());
  const draw = async () => {
    const [all, wait, BAT, SETS, TXS] = await Promise.all([api('/api/references' + (tests ? '?tests=1' : '')), api('/api/waiting').catch(() => []),
      api('/api/batches?kind=review').catch(() => []), api('/api/thumbs').catch(() => []), api('/api/texts').catch(() => [])]);
    const cats = [...new Map(all.filter(r => r.category).map(r => [r.category, r.category_label])).entries()];
    const tags = [...new Set(all.flatMap(r => r.tags || []))].sort();
    const refs = all.filter(r => (!cat || r.category === cat) && (!tag || (r.tags || []).includes(tag)) && (!foc || r.focus === foc))
      .sort((a, b) => strTime(b.generated) - strTime(a.generated));        // newest analysis first (0.4.3.5)
    const wv = wait.filter(w => !w.photo && !w.audio).length;
    const none = !all.length && !wait.length && !SETS.length && !TXS.length;
    // each way's foot: what is there and what is left for Claude - only when its kind has something
    const vLeft = all.filter(r => (r.flow || {}).next === 'claude').length, sLeft = SETS.filter(s => !s.has_style).length;
    const nThumbs = SETS.reduce((a, s) => a + (s.count || 0), 0), nTexts = TXS.reduce((a, s) => a + (s.count || 0), 0);
    const tLeft = TXS.reduce((a, s) => a + Math.max(0, (s.count || 0) - (s.checked || 0)), 0);
    const feet = {videos: all.length ? tn(all.length, '{n} video analysed', '{n} videos analysed') + (vLeft ? ' · ' + t('{n} not checked by Claude yet', {n: vLeft}) : '') : '',
      thumbs: SETS.length ? `${plural(SETS.length, 'set')} · ${plural(nThumbs, 'thumbnail')}${sLeft ? ' · ' + t('{n} without patterns yet', {n: sLeft}) : ''}` : '',
      texts: TXS.length ? `${plural(TXS.length, 'set')} · ${tn(nTexts, '{n} script & prompts', '{n} scripts & prompts')}${tLeft ? ' · ' + t('{n} not checked yet', {n: tLeft}) : ''}` : ''};
    const counts = {videos: all.length, thumbs: SETS.length, texts: TXS.length}, anyFoot = Object.values(feet).some(Boolean);
    const way = (k, icon, title, text, btns) => `<div class="gway${!none && tab === k ? ' on' : ''}"><div class="row"><svg class="ic"><use href="#i-${icon}"/></svg><h2>${title}</h2></div>
        <p>${text}</p><div class="row">${btns}</div>${feet[k] ? `<a class="gway-foot" href="${AN_TABS.find(x => x[0] === k)[3]}">${feet[k]} →</a>`
          : anyFoot ? '<span class="gway-foot blank" aria-hidden="true">&nbsp;</span>' : ''}</div>`;     // keeps the buttons in line
    const testsBox = `<span class="grow"></span><label class="chk small dim"><input type="checkbox" id="tests" ${tests ? 'checked' : ''}> ${t('show the test videos')}</label>`;
    const list = tab === 'thumbs' ? (SETS.length ? `<div class="cards pcards">${SETS.map(setCard).join('')}</div>`
        : `<div class="pcempty">${t('Thumbnail sets land here - <i>Add thumbnails</i> above: a channel, some videos or your pictures.')}</div>`)
      : tab === 'texts' ? (TXS.length ? `<div class="cards pcards">${TXS.map(textSetCard).join('')}</div>`
        : `<div class="pcempty">${t('Your sets of scripts and prompts land here - <i>Add scripts or prompts</i> above.')}</div>`)
      : `<div class="row frow">${all.length ? `<select id="ffoc" class="ffil"><option value="">${t('Every focus')}</option>${Object.entries(FOCUS_SHORT).map(([k, l]) => `<option value="${k}" ${k === foc ? 'selected' : ''}>${l} (${all.filter(r => r.focus === k).length})</option>`).join('')}</select>
          <select id="fcat" class="ffil"><option value="">${t('All categories ({n})', {n: all.length})}</option>${cats.map(([k, l]) => `<option value="${k}" ${k === cat ? 'selected' : ''}>${esc(t(l || ''))} (${all.filter(r => r.category === k).length})</option>`).join('')}</select>
          ${tags.length ? `<select id="ftag" class="ffil"><option value="">${t('All tags')}</option>${tags.map(g => `<option ${g === tag ? 'selected' : ''}>${esc(g)}</option>`).join('')}</select>` : ''}` : ''}
          ${testsBox}</div>
        ${refs.length ? `<div class="cards pcards">${refs.map(refCard).join('')}</div>`
          : all.length ? `<div class="empty">${t('No reference in this category.')}</div>` : `<div class="pcempty">${t('The videos you analyse land here - <i>Add videos</i> above.')}</div>`}`;
    main.innerHTML = `<div class="head"><div><h1>${t('Analyser')}</h1><div class="sub">${t('Videos, thumbnails, scripts and prompts you like - measured by MotionLab, explained by Claude, remembered for your own videos.')}</div></div></div>
      <div class="gways g3">
        ${way('videos', 'videos', t('Videos'), t('Links or video files, up to {n} at a time. MotionLab finds every cut, effect and beat; Claude names them and writes what makes each one work.', {n: AV_MAX}),
          `<button class="btn pri" id="an"><svg class="i"><use href="#i-analyze"/></svg>${t('Add videos')}</button><button class="btn ghost" id="dl" title="${ta('Download a video or a song (MP3) from a link without analysing it - e.g. music for an edit')}"><svg class="i"><use href="#i-download"/></svg>${t('Download from link')}</button>`)}
        ${way('thumbs', 'thumb', t('Thumbnails'), t('A channel, some videos or your own pictures - only the pictures, no video. Claude finds what they have in common: the text, the font, the colours, the structure.'),
          `<button class="btn pri" id="tadd"><svg class="i"><use href="#i-thumb"/></svg>${t('Add thumbnails')}</button><button class="btn ghost" id="ttest" title="${ta('See your thumbnail on a YouTube-like home page, next to the newest videos of big creators - does it pop?')}"><svg class="i"><use href="#i-play"/></svg>${t('Preview your thumbnail')}</button>`)}
        ${way('texts', 'texts', t('Scripts & prompts'), t('Paste or attach up to {n} - prompts for AI video and image tools, talking scripts, hooks. Claude checks each one on its own, part by part, then names what they have in common.', {n: TX_MAX}),
          `<button class="btn pri" id="txadd"><svg class="i"><use href="#i-texts"/></svg>${t('Add scripts or prompts')}</button>`)}</div>
      <div id="avprog"></div>${batchRows(BAT)}
      ${wait.length ? `<button class="wbar" id="wbar"><svg class="i"><use href="#i-download"/></svg><span class="grow">${wv ? tn(wv, '<b>{n} downloaded video</b> waits to be analysed', '<b>{n} downloaded videos</b> wait to be analysed') : tn(wait.length, '<b>{n} download</b> not analysed', '<b>{n} downloads</b> not analysed')}</span><span class="wgo">${t('Show them →')}</span></button>` : ''}
      ${none ? `<div class="row frow">${testsBox}</div>`
        : `<div class="tabs antabs">${AN_TABS.map(([k, l, ic, h]) => `<a href="${h}" class="${tab === k ? 'on' : ''}"><svg class="i"><use href="#i-${ic}"/></svg>${l} <span class="dim">${counts[k]}</span></a>`).join('')}</div>
          <div id="antab">${list}</div>`}`;
    $('#an', main).onclick = () => addVideosModal();
    $('#tadd', main).onclick = () => addThumbsModal();
    $('#ttest', main).onclick = () => thumbTest();
    $('#txadd', main).onclick = () => addTextsModal();
    $('#dl', main).onclick = downloadModal;
    wireBatchRows(main, draw);
    const wb = $('#wbar', main); if (wb) wb.onclick = () => waitingModal(wait);
    const tb = $('#tests', main); if (tb) tb.onchange = e => { tests = e.target.checked; draw(); };   // the Videos tab / an empty lab only
    const ff = $('#ffoc', main); if (ff) ff.onchange = e => { foc = e.target.value; draw(); };
    const fc = $('#fcat', main); if (fc) fc.onchange = e => { cat = e.target.value; draw(); };
    if (stopProgress) stopProgress();
    stopProgress = progressPanel($('#avprog', main), () => draw(), ['download', 'analyze', ...THUMBS_JOBS]);
    const ft = $('#ftag', main); if (ft) ft.onchange = e => { tag = e.target.value; draw(); };
  };
  await draw();
}

// one analysis (the user's layout of 2026-10-06/07; since 2026-10-18 the one review pattern, the user: "it needs to look
// the same ... if im either reviewing a script in prepare, reviewing a video analyzed or an edit"): the header, the
// workflow strip, the full-width frame-accurate player + two timelines, then the tabs. On Effects and on Possible
// misses & sound the thing being judged is on the left (the effect card, the end card / the miss's three frames, the
// sound question) and the review panel on the right (reviewPanel: Is Claude right? per effect with the list's filters;
// the sound row and the possible misses, red until answered). Every key stays: 1 2 3, J K N, Correct moves on, Partly /
// Wrong open the note, Ctrl+Enter moves on, the end card after the last effect. The verdicts save WHOLE 450 ms after
// the last change through the same route (verdicts.json, one home); the timelines' verdict line and the strip follow.
async function pageRef(main, name, selId, openMisses, openReview) {
  const R = await api('/api/reference/' + encodeURIComponent(name));
  const fps = R.video.fps, N = R.video.frames, evs = R.events, NM = R.near_misses || [];
  const byId = Object.fromEntries(evs.map(e => [e.id, e]));
  const S = {events: R.verdicts.events || {}, cuts: R.verdicts.cuts || {}, misses: R.verdicts.misses || {}, missed: R.verdicts.missed || '',
             sound: R.verdicts.sound || null};
  const sndDone = () => !!(S.sound && S.sound.amount);     // 0.4.2: "sound effects in this video?" - Claude cannot hear
  const vOf = id => (S.events[id] || {}).v || '';
  const mOf = f => (S.misses[String(f)] || {}).v || '';
  let cur = byId[selId] || evs.find(e => !e.false_alarm && !vOf(e.id)) || evs.find(e => !e.false_alarm) || evs[0];
  const fams = [...new Set(evs.map(e => e.family))].sort();
  // the review's fixed words as the page says them (review_rules.md: origin post / camera / unclear, confidence high /
  // medium / low; the lab's easing phrases, detect.py); any other wording is Claude's own, shown as it is
  const WORDS = {origin: {post: t('post|origin'), camera: t('camera|origin'), unclear: t('unclear|origin')},
    confidence: {high: t('high|confidence'), medium: t('medium|confidence'), low: t('low|confidence')},
    easing: {'n/a': t('n/a|easing'), 'instant (1 frame)': t('instant (1 frame)'), 'accelerating (slow start)': t('accelerating (slow start)'),
      'decelerating (slow end)': t('decelerating (slow end)'), 'linear (constant speed)': t('linear (constant speed)'),
      'S-curve (slow start and slow end)': t('S-curve (slow start and slow end)')}};
  const said = (f, x) => esc(WORDS[f][x] || x);
  const nfa = evs.filter(e => e.false_alarm).length;
  const pref = (k, d) => { try { const v = localStorage.getItem('ml.' + k); return v === null ? d : v; } catch (e) { return d; } };
  const setPref = (k, v) => { try { localStorage.setItem('ml.' + k, v); } catch (e) { /* private window */ } };
  let sound = pref('previewSound', '0') === '1', rate = +pref('previewRate', '1') || 1;
  let shown = evs, tab = openMisses ? 'misses' : selId || openReview ? 'review' : 'overview', PE = null, PM = null;
  const missedBtn = `<button type="button" class="btn sm" data-missed>${t('Missed effects / general notes…')}</button>`;
  main.innerHTML = `
  <div class="head"><div><div class="crumb"><a href="#/analyze">${t('Analyser')}</a> / ${t('video')}</div><h1${R.label && R.label !== R.title ? ` title="${esc(R.title)}"` : ''}>${esc(R.label || R.title)}</h1>
    <div class="sub">${focusChip(R.focus || '')}${R.focus ? '' : `<span class="fchip sm" title="${ta('analysed before 0.4')}">${t('focus not set')}</span>`} <span class="tag">${esc(t(R.category_label || ''))}</span> ${(R.tags || []).map(g => `<span class="tag dim">${esc(g)}</span> `).join('')}<a href="#" id="editmeta" class="small">${t('edit')}</a>
      ${R.url ? ` · <a href="${esc(R.url)}" target="_blank" rel="noopener">${esc(R.platform || t('source'))}</a>` : ''} · ${R.video.width}×${R.video.height} · ${fps} fps · ${t('{n} frames (f0–{last}, 00:00:00:00 – {end})', {n: N, last: N - 1, end: R.video.end_tc})}${R.audio.bpm ? ` · ${dec(R.audio.bpm, 1)} BPM` : ''}
      · ${t('{n} effects, {cuts} hard cuts', {n: evs.length, cuts: R.cuts.length})} · ${t('analysed {when}', {when: esc(R.generated || '')})}${R.source_unchanged ? ' · ' + t('source unchanged ✓') : ''}</div>
    ${R.pacing ? `<div class="small pacing">${t('Pacing: <b>{cpm}</b> cuts/min · shots avg <b>{avg} s</b> (median {med} s) · <b>{hook}</b> cut(s) in the first 3 s · <b>{epm}</b> effects/min',
      {cpm: numStr(R.pacing.cuts_per_min ?? '–'), avg: numStr(R.pacing.avg_shot_s ?? '–'), med: numStr(R.pacing.median_shot_s ?? '–'), hook: numStr(R.pacing.hook_cuts_3s), epm: numStr(R.pacing.effects_per_min ?? '–')})}${R.pacing.cuts_on_beat_pct != null ? ' · ' + t('{pct} % of plain cuts on the beat', {pct: numStr(R.pacing.cuts_on_beat_pct)}) : ''}</div>` : ''}</div>
    <div class="row"><button class="btn cl" id="recreate" title="${ta('Claude edits your own clips like this video')}"><svg class="i"><use href="#i-edit"/></svg>${t('Edit my clips like this…')}</button>
      ${R.report ? `<button class="btn" data-open="${esc(R.report)}">${t('Open full report')}</button>` : ''}
      <button class="btn" data-open="${esc('analysis/' + R.name)}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button>${delBtn('reference', R.name, '#/analyze', ' ' + t('Delete'))}</div></div>
  <div id="flow">${flowStrip(R, R.flow)}</div>
  <div class="rtabs" id="rtabs"><button class="rtab" data-tab="overview">${t('Overview')}</button><button class="rtab" data-tab="review">${t('Effects')} <span class="cnt" id="cnt-review"></span></button>
    <button class="rtab misstab" data-tab="misses">${NM.length ? t('Possible misses & sound') : t('Sound effects')} <span class="cnt" id="cnt-misses"></span></button>
    <button class="rtab" data-tab="content" title="${ta('what the video says and how it performs')}">${t('What it says')}</button></div>
  <div class="watch">
    <div id="player"></div>
    <div class="tl" id="tl1"><canvas height="100"></canvas></div>
    <div class="tl" id="tl2"><canvas height="84"></canvas></div>
    <div class="hint legend">${t('Top: the whole video · below: 60 frames each side of the playhead (red line) · bars = effects (colour = type, line under = your verdict) · white line = hard cut · <b class="bad">red ▲</b> = possible miss · ▼ = music drop · ticks = beats (tall = bar start)')} ·
      ${t('keys: <span class="kbd">←</span><span class="kbd">→</span> frame, <span class="kbd">Shift</span> ten, <span class="kbd">Space</span> play, <span class="kbd">J</span><span class="kbd">K</span> previous / next effect, <span class="kbd">N</span> next without verdict, <span class="kbd">1</span><span class="kbd">2</span><span class="kbd">3</span> correct / partly / wrong')}</div>
  </div>
  <div class="rvtab" id="tab-review"><div class="rvlayout${evs.length ? '' : ' solo'}"><div class="rvthing"><div class="rcard panel" id="detail"></div></div><aside id="rvp-fx"${evs.length ? '' : ' hidden'}></aside></div></div>
  <div class="missarea" id="tab-misses" hidden>
    ${NM.length ? `<div class="missintro">${t("<b>Possible misses are not effects from the list.</b> They are sudden changes in the picture that no effect and no cut explains - places where the lab may have missed an effect. Most are nothing, but only you can say. For each one: look at the frames (before · at · after - click one to show it in the player), read Claude's check, then answer it beside.")}</div>` : ''}
    <div class="rvlayout"><div class="rvthing" id="missthing"></div><aside id="rvp-miss"></aside></div></div>
  <div class="contentarea" id="tab-content" hidden></div>
  <div class="overview" id="tab-overview" hidden></div>`;

  const P = R.video.play ? new Player($('#player'), R.video.play, fps, N) : null;
  if (!P) $('#player').innerHTML = `<div class="empty">${t('The source video is not inside the lab folder, so it cannot be played here.')}</div>`;
  const tlOpts = {verdict: vOf, missDone: f => !!mOf(f), onSelect: e => { showTab('review'); select(e, true); },
                  onSeek: f => P && P.seek(f), onMiss: m => { showTab('misses', true); focusMiss(m.frame); }};
  const T1 = new Timeline($('#tl1'), R, tlOpts);
  const T2 = new Timeline($('#tl2'), R, {...tlOpts, zoom: 60});
  if (P) P.on(f => { T1.setPlay(f); T2.setPlay(f); });

  // the verdicts: the WHOLE state through the same route, 450 ms after the last change (as before); Send saves at once
  // first. One save at a time (the newest state goes last); both panels say saved ✓ / NOT saved.
  let saveT = 0, waiting = [], dirty = false, saving = Promise.resolve();
  const status = ok => [PE, PM].forEach(p => p && (ok == null ? p.saving() : p.saved(ok)));
  const refreshFlow = debounce(async () => {             // the step strip follows your verdicts
    try { const NR = await api('/api/reference/' + encodeURIComponent(name)); $('#flow').innerHTML = flowStrip(NR, NR.flow); } catch (e) { /* keep the old one */ }
  }, 1500);
  const saveNow = () => (saving = saving.then(async () => {
    clearTimeout(saveT); saveT = 0;
    const done = waiting; waiting = [];
    let ok = true;
    if (dirty) {
      dirty = false;
      try { await api(`/api/reference/${encodeURIComponent(name)}/verdicts`, S); refreshFlow(); }
      catch (e) { ok = false; dirty = true; toast(t('Could not save: {error}', {error: e.message}), 'err'); }
      status(ok);
    }
    done.forEach(r => r(ok));
    return ok;
  }));
  const save = () => { dirty = true; status(null); clearTimeout(saveT); saveT = setTimeout(saveNow, 450); return new Promise(r => waiting.push(r)); };
  const progress = () => {                               // the tabs' badges
    const cr = $('#cnt-review', main), cm = $('#cnt-misses', main);
    if (!cr) return;                                     // the page was left (a note saved on the way out)
    const real = evs.filter(e => !e.false_alarm), n = real.filter(e => vOf(e.id)).length, open = NM.filter(m => !mOf(m.frame)).length + (sndDone() ? 0 : 1);
    cr.textContent = n >= real.length ? t('all done ✓') : tn(real.length - n, '{n} left', '{n} left'); cr.classList.toggle('ok', n >= real.length);
    if (cm) { cm.textContent = !open ? t('all answered ✓') : NM.length ? t('{n} to check', {n: open}) : t('to answer'); cm.closest('.rtab').classList.toggle('open', open > 0); }
  };
  const changed = () => { const p = save(); progress(); [PE, PM].forEach(x => x && x.redraw()); T1.draw(); T2.draw(); return p; };
  // the effect card (left): the preview with frame + timecode burned in, What happens + Measured evidence open, In depth
  // and the Frame list folded (the user's notes of 2026-10-06/07)
  const detail = () => {
    const e = cur, n = e.end - e.start + 1, i = shown.indexOf(e);
    const el = $('#detail');
    el.innerHTML = `<div class="rbody"><div class="rhead"><div class="evhead"><span class="id">${e.id}</span><span class="ty">${esc(t(e.label || ''))}</span>${chip(e.family)}</div>
        <span class="small muted">${i >= 0 ? t('{n} of {total}', {n: i + 1, total: shown.length}) : ''}</span></div>
      ${e.relabelled ? `<div class="relab">${t('first guess <s>{label}</s> · renamed by Claude', {label: esc(t(e.auto_label || ''))})}</div>` : ''}
      ${!e.reviewed ? `<div class="small warnline">${t('Not checked by Claude yet: the name is a guess.')}</div>` : ''}
      ${e.false_alarm ? `<div class="bad small">${t('a false alarm (not an edit effect) - a verdict is optional')}</div>` : ''}
      ${e.preview ? `<div class="pvbox"><video class="pv" src="${fileUrl(e.preview)}" autoplay loop playsinline ${sound ? '' : 'muted'}></video>
        <div class="pvbar"><span class="small muted">${t('loop {range} · frame + timecode in the picture', {range: e.preview_range ? `f${e.preview_range[0]}–${e.preview_range[1]}` : ''})}</span><div class="grow"></div>
          ${[0.25, 0.5, 1].map(r => `<button class="btn sm rate ${r === rate ? 'on' : ''}" data-pr="${r}">${r === 1 ? '1×' : r === 0.5 ? '½' : '¼'}</button>`).join('')}
          <label class="chk small"><input type="checkbox" id="pvsnd" ${sound ? 'checked' : ''}> ${t('sound')}</label>
          <button class="btn sm" id="inbig" title="${ta('play it in the big player above')}">${t('▶ big player')}</button></div></div>` : ''}
      <div class="kv" style="margin-top:8px"><b>${t('Frames')}</b><span>${frange(e.start, e.end, fps)}</span><b>${t('Length')}</b><span>${tn(n, '{n} frame ({s} s)', '{n} frames ({s} s)', {s: dec(n / fps, 2)})}</span></div>
      <h3>${t('What happens')}</h3><div class="what">${linkify(e.what)}</div>
      ${e.evidence.length ? `<h3>${t('Measured evidence')}</h3><ul class="small" style="margin:0;padding-left:18px;color:#c9c9d0">${e.evidence.map(x => `<li>${linkify(x)}</li>`).join('')}</ul>` : ''}
      <details class="fold"><summary>${t('In depth: timing, easing, origin and how to rebuild it')}</summary><div class="in"><div class="kv">
        ${e.timing ? `<b>${t('Timing')}</b><span>${esc(e.timing)}</span>` : ''}${e.easing ? `<b>${t('Easing')}</b><span>${said('easing', e.easing)}</span>` : ''}
        ${e.origin ? `<b>${t('Made|how it was made')}</b><span>${said('origin', e.origin)}</span>` : ''}${e.confidence ? `<b>${t('Confidence')}</b><span>${said('confidence', e.confidence)}</span>` : ''}
        ${e.stacked && e.stacked.length ? `<b>${t('Also')}</b><span>${esc(e.stacked.join(', '))}</span>` : ''}</div>
        ${e.rebuild ? `<h3>${t('How to rebuild it in Resolve')}</h3><div class="what">${linkify(e.rebuild)}</div>` : ''}</div></details>
      <details class="fold"><summary>${tn(e.sheets.length, 'Frame list ({n} contact sheet)', 'Frame list ({n} contact sheets)')}</summary><div class="in">
        <div class="sheets" style="margin-top:8px">${e.sheets.map((s, k) => `<img src="${fileUrl(s)}" data-i="${k}" loading="lazy" alt="">`).join('')}</div></div></details></div>`;
    const pv = $('.pv', el);
    if (pv) {
      pv.playbackRate = rate; pv.addEventListener('loadedmetadata', () => { pv.playbackRate = rate; });
      $$('[data-pr]', el).forEach(b => b.onclick = () => { rate = +b.dataset.pr; setPref('previewRate', rate); pv.playbackRate = rate; $$('[data-pr]', el).forEach(x => x.classList.toggle('on', x === b)); });
      $('#pvsnd', el).onchange = ev => { sound = ev.target.checked; setPref('previewSound', sound ? '1' : '0'); pv.muted = !sound; };
      $('#inbig', el).onclick = () => { if (P) { P.setLoop(true); P.playRange(e.start, Math.max(e.end, e.start + 2)); $('.watch').scrollIntoView({behavior: 'smooth', block: 'start'}); } };
    }
    $$('.sheets img', el).forEach(img => img.onclick = () => lightbox(e.sheets.map((s, k) => ({src: s, cap: t('{id} {label} · sheet {n}', {id: e.id, label: t(e.label || ''), n: k + 1})})), +img.dataset.i));
    $$('[data-seek]', el).forEach(a => a.onclick = ev => { ev.preventDefault(); if (P) { P.v.pause(); P.seek(+a.dataset.seek); } });
  };
  const endCard = () => {                                 // after the last effect: what is left to do
    const real = evs.filter(e => !e.false_alarm), n = real.filter(e => vOf(e.id)).length, open = NM.filter(m => !mOf(m.frame)).length;
    $('#detail').innerHTML = `<div class="endcard"><h2>${n >= real.length ? t('Every effect has your verdict ✓') : t('That was the last effect in the list')}</h2>
      <div class="muted">${t('{n} / {total} effects with your verdict.', {n, total: real.length})}</div>
      ${open ? `<div class="missline">${tn(open, 'Still to check: <b>{n} possible miss</b> - changes in the picture that no effect explains.', 'Still to check: <b>{n} possible misses</b> - changes in the picture that no effect explains.')}</div>
        <button class="btn missbtn" data-tabgo="misses">${t('Check the possible misses')}</button>` : ''}
      ${sndDone() ? '' : `<div class="missline">${t('Still to answer: <b>sound effects in this video</b> - Claude cannot hear, only you can say.')}</div>
        ${open ? '' : `<button class="btn missbtn" data-tabgo="misses">${t('Answer it')}</button>`}`}
      <div style="margin-top:14px">${t('Then send everything to Claude: it turns your verdicts into lessons.')}</div>
      <div class="row" style="margin-top:8px"><button class="btn pri" data-feedback="${esc(name)}"><svg class="i"><use href="#i-claude"/></svg>${t('Send it to Claude')}</button>
        ${n < real.length ? `<button class="btn" id="endopen">${t('Go to the next effect without a verdict')}</button>` : ''}<button class="btn ghost" id="endback">${t('◀ Back to the list')}</button></div></div>`;
    const eb = $('#endback'); if (eb) eb.onclick = () => select(cur, true);
    const eo = $('#endopen'); if (eo) eo.onclick = () => { if (PE) PE.nextOpen(); };
  };
  const select = (e, seek) => {                           // an effect on the left; the panel marks its row
    cur = e; T1.sel = T2.sel = e.id;
    history.replaceState(null, '', `#/ref/${encodeURIComponent(name)}?e=${e.id}`);
    if (PE) { PE.redraw(); PE.select('effects', e.id); }
    detail(); T1.draw(); T2.draw();
    if (seek && P) { P.range = [e.start, e.end]; P.v.pause(); P.seek(e.start); }
  };
  // ------------------------------------------- possible misses & sound effects (0.4.2: Claude cannot hear) - the left side
  const drawMissThing = (sec, id, seek) => {
    const box = $('#missthing', main); if (!box) return;
    if (sec === 'misses') {
      const m = NM.find(x => String(x.frame) === String(id)); if (!m) return;
      const v = mOf(m.frame);
      box.innerHTML = `<div class="panel miss ${v === 'effect' ? 'm-effect' : v ? 'm-done' : 'm-open'}"><div class="row sp"><span class="mstate">${v === 'effect' ? t('★ an effect') : v === 'none' ? t('✓ not an effect') : t('● to check')}</span>
          <a href="#" class="fr" data-seek="${m.frame}">${ftc(m.frame, fps)}</a></div>
        <h3 style="margin:2px 0 0">${t('Possible miss')}</h3>
        <div class="f3">${m.frames.map((f, k) => `<figure><img src="${fileUrl(f)}" data-f="${m.frame - 1 + k}" title="${ta('f{f} ({tc}) - click to show it in the player', {f: m.frame - 1 + k, tc: tc(m.frame - 1 + k, fps)})}" alt=""><figcaption>${[t('before'), t('at|the frame of the change'), t('after')][k] || ''} · f${m.frame - 1 + k}</figcaption></figure>`).join('')}</div>
        <div class="small muted">${esc(m.why)}</div>
        ${m.checked ? `<div class="claudechk">${t('<b>Claude checked:</b> {text}', {text: linkify(m.checked)})}</div>` : `<div class="small dim">${t('Claude has not checked this one yet.')}</div>`}
        <div class="small muted">${t("Answer it beside: <b>✓ Not an effect</b> (key 1) or <b>★ It's an effect</b> (key 2) - then say what it is.")}</div></div>`;
      $$('img[data-f]', box).forEach(img => img.onclick = () => { if (P) { P.v.pause(); P.seek(+img.dataset.f); } });
      $$('[data-seek]', box).forEach(a => a.onclick = ev => { ev.preventDefault(); if (P) { P.v.pause(); P.seek(+a.dataset.seek); } });
      if (seek && P) { P.v.pause(); P.seek(m.frame); }
      return;
    }
    const a = (S.sound || {}).amount || '';
    box.innerHTML = `<div class="panel miss ${a ? 'm-done' : 'm-open'}"><div class="row sp"><span class="mstate">${a ? t('✓ answered') : t('● to answer')}</span>
        <span class="small muted">${t('Claude cannot hear - only you can say')}</span></div>
      <h3 style="margin:2px 0 0">${t('Sound effects in this video')}</h3>
      <div class="small muted">${t('Whooshes, hits, risers, clicks, pops - sounds added on top of the music or the voice. Play the video above with sound on, then answer beside: <b>None</b>, <b>Some</b> or <b>Many</b> (keys 1 2 3) - and where.')}</div></div>`;
  };
  const missNow = () => { const c = PM && PM.cur(); if (c) drawMissThing(c.sec, c.id, false); };     // after an answer
  const focusMiss = f => { if (PM) PM.select('misses', String(f)); drawMissThing('misses', f, true); };
  // ------------------------------------------- the review panels (reviewPanel)
  const effRow = e => { const lib = (S.events[e.id] || {}).library;
    return {id: e.id, optional: !!e.false_alarm, sub: frange(e.start, e.end, fps),
      label: `<span class="mono amber">${e.id}</span> <i class="sw" style="background:${FAM[e.family] || '#888'}"></i>${esc(t(e.label || ''))}${e.relabelled ? ` <span class="relab" title="${ta('renamed by Claude')}">✎</span>` : ''}${lib ? ` <span class="amber" title="${ta('wanted in the library')}">★</span>` : ''}${e.false_alarm ? ` <span class="small dim">${t('false alarm')}</span>` : ''}`}; };
  const effItems = () => {                               // the list's filters (the current effect always stays)
    const q = (($('#q', main) || {}).value || '').toLowerCase(), ff = ($('#ff', main) || {}).value || '', fv = ($('#fv', main) || {}).value || '';
    const fa = !!($('#showfa', main) || {}).checked, keep = e => !!cur && e.id === cur.id;
    const shownLabel = e => { const s = t(e.label || ''); return s !== e.label ? s + ' ' : ''; };     // the label as the page says it
    const list = evs.filter(e => (fa || !e.false_alarm || keep(e)) && (!ff || e.family === ff)
      && (!fv || keep(e) || (fv === 'none' ? !vOf(e.id) : fv === 'relab' ? e.relabelled : vOf(e.id) === fv))
      && (!q || (e.id + ' ' + e.label + ' ' + shownLabel(e) + e.what + ' ' + ((S.events[e.id] || {}).note || '')).toLowerCase().includes(q)));
    shown = list.length ? list : evs;
    return list.map(effRow);
  };
  const anyAnswer = () => Object.values(S.events).some(x => x && (x.v || (x.note || '').trim() || x.library))
    || Object.values(S.misses).some(x => x && (x.v || (x.note || '').trim())) || sndDone() || !!((S.sound || {}).where || '').trim() || !!(S.missed || '').trim();
  const allDone = () => evs.every(e => e.false_alarm || vOf(e.id)) && NM.every(m => mOf(m.frame)) && sndDone();
  const send = () => ({hint: t('Claude turns your verdicts into lessons and better thresholds for the next video, checks again what you marked wrong or partly, and tells you what changed.'),
    ready: anyAnswer, glow: allDone, go: async () => { if (await saveNow()) await sendFeedback(name); },
    more: `<a href="#" data-fbcopy title="${ta('the text Claude gets, to paste it yourself')}">${t('Copy what Claude gets')}</a>`});
  if (evs.length) PE = reviewPanel($('#rvp-fx', main), {
    filters: `<div class="filters"><input type="search" id="q" placeholder="${ta('Search effects, notes…')}">
        <select id="ff"><option value="">${t('All types')}</option>${fams.map(f => `<option value="${esc(f)}">${esc(t(f))}</option>`).join('')}</select>
        <select id="fv"><option value="">${t('All verdicts')}</option><option value="none">${t('No verdict yet')}</option><option value="correct">${t('Correct')}</option>
          <option value="partly">${t('Partly')}</option><option value="wrong">${t('Wrong')}</option><option value="relab">${t('Renamed by Claude')}</option></select>
        ${nfa ? `<label class="chk small"><input type="checkbox" id="showfa"> ${tn(nfa, 'show the {n} false alarms', 'show the {n} false alarms')} <span class="dim">${t('(optional)')}</span></label>` : ''}</div>`,
    sections: [{id: 'effects', ask: t('Is Claude right?'), intro: t('Claude\'s name and description of each effect'), scale: 'claims', items: effItems, all: () => evs.map(effRow),
      get: id => S.events[id] || {},
      set: (id, a) => { const st = S.events[id] = S.events[id] || {}; st.v = a.v; st.note = a.note; return changed(); },
      hint: v => v === 'partly' || v === 'wrong' ? t('What is wrong? e.g. “it\'s a zoom, not a flash; it starts at f340” - then K or Ctrl+Enter for the next effect') : t('Note (optional): what is right or wrong?'),
      empty: t('No effect matches.')}],
    extra: {item: (s, id) => `<label class="chk small"><input type="checkbox" data-lib ${(S.events[id] || {}).library ? 'checked' : ''}> ${t('I want this effect in my library')}</label>`,
            panel: `<div class="row rvacts">${missedBtn}${nfa ? `<button type="button" class="btn sm ghost" data-agreefa title="${ta('optional: tells Claude its “not an effect” calls were right')}">${t('Agree with all false alarms')}</button>` : ''}</div>`},
    start: cur ? {sec: 'effects', id: cur.id} : false,
    onMove: (s, id, first) => { if (byId[id]) select(byId[id], !first); }, onEnd: endCard, send: send()});
  PM = reviewPanel($('#rvp-miss', main), {
    sections: [
      {id: 'sound', ask: t('Sound effects in this video?'), intro: t('Claude cannot hear - only you can say'), scale: 'sound', note: 'line',
        items: () => [{id: 'sound', red: true, label: `<b>${t('Sound effects in this video')}</b>`, sub: t('whooshes, hits, risers, clicks, pops')}],
        get: () => ({v: (S.sound || {}).amount || '', note: (S.sound || {}).where || ''}),
        set: (id, a) => { S.sound = {...(S.sound || {}), amount: a.v, where: a.note}; const p = changed(); missNow(); return p; },
        hint: v => v === 'none' ? t('Anything else about the sound? (optional)') : t('Where? (optional) e.g. “a whoosh on every cut, a hit on each title, a riser before the drop at f300”')},
      ...(NM.length ? [{id: 'misses', ask: t('Possible misses: is it an effect?'), intro: t('a change in the picture that no effect and no cut explains'), scale: 'miss', note: 'line',
        items: () => NM.map(m => ({id: String(m.frame), red: true, label: ftc(m.frame, fps), sub: esc(m.why.length > 90 ? m.why.slice(0, 88) + '…' : m.why)})),
        get: id => S.misses[id] || {},
        set: (id, a) => { const st = S.misses[id] = S.misses[id] || {}; st.v = a.v; st.note = a.note; const p = changed(); missNow(); return p; },
        hint: v => v === 'effect' ? t('What is it? e.g. “a clock pops in, no fade”') : t('Note (optional)')}] : [])],
    extra: {panel: `<div class="row rvacts">${missedBtn}</div>`},
    onMove: (s, id, first) => drawMissThing(s, id, !first), send: send()});
  const showTab = (tb, scroll = false) => {
    tab = tb;
    $$('#rtabs .rtab').forEach(b => b.classList.toggle('on', b.dataset.tab === tb));
    $('#tab-review').hidden = tb !== 'review'; $('#tab-misses').hidden = tb !== 'misses';
    $('#tab-content').hidden = tb !== 'content'; $('#tab-overview').hidden = tb !== 'overview';
    $('.watch', main).hidden = tb === 'overview';          // the Overview needs no player (it pauses)
    if (tb === 'overview' && P) P.v.pause();
    if (tb === 'content' && !$('#tab-content').dataset.done) contentTab($('#tab-content'), R, P);
    if (tb === 'overview' && !$('#tab-overview').dataset.done) overviewTab($('#tab-overview'), R, showTab);
    const pn = tb === 'review' ? PE : tb === 'misses' ? PM : null, c = pn && pn.cur();
    if (c) pn.select(c.sec, c.id);                        // its current row in view, now that the panel shows
    if (scroll) $('#rtabs').scrollIntoView({behavior: 'smooth', block: 'start'});
  };
  $$('#rtabs .rtab').forEach(b => b.onclick = () => showTab(b.dataset.tab, true));
  ['#q', '#ff', '#fv', '#showfa'].forEach(s => { const x = $(s, main); if (x) x.addEventListener('input', () => PE && PE.redraw()); });
  if (PE) PE.el.addEventListener('change', ev => {         // the library tick on the current effect (the panel's item extra)
    const li = ev.target.matches('[data-lib]') && ev.target.closest('.rvrow');
    if (li) { (S.events[li.dataset.id] = S.events[li.dataset.id] || {}).library = ev.target.checked; changed(); }
  });
  const missedModal = () => modal(`<h2>${t('Missed effects / general notes')}</h2>
    <p class="hint">${t('Anything the analysis missed or got wrong overall. Mention frames or timecodes, e.g. “speed ramp around f1210 / 00:00:48:10”. The red possible misses have their own answers (tab “Possible misses”).')}</p>
    <textarea id="mt" rows="10">${esc(S.missed)}</textarea><div class="row" style="margin-top:10px"><button class="btn pri" id="mok">${t('Save')}</button></div>`, el => {
    $('#mok', el).onclick = () => { S.missed = $('#mt', el).value; changed(); closeModal(); };
  });
  const copyFb = async () => {                            // the raw text Claude gets (no file written)
    if (!(await saveNow())) return;
    try { copy((await api('/api/feedback/' + encodeURIComponent(name))).text); } catch (e) { toast(e.message, 'err'); }
  };
  const onClick = ev => {
    const tg = ev.target;
    if (tg.closest('[data-missed]')) { ev.preventDefault(); missedModal(); return; }
    if (tg.closest('[data-agreefa]')) {
      ev.preventDefault();
      evs.filter(e => e.false_alarm).forEach(e => { const st = S.events[e.id] = S.events[e.id] || {}; if (!st.v) st.v = 'correct'; });
      changed(); detail(); toast(t('All false alarms marked as correctly dismissed'), 'ok'); return;
    }
    if (tg.closest('[data-fbcopy]')) { ev.preventDefault(); copyFb(); return; }
    if (tg.closest('[data-feedback]')) {                   // the strip's and the end card's Send it to Claude: save first
      ev.preventDefault(); ev.stopPropagation(); saveNow().then(ok => { if (ok) sendFeedback(name); }); return;
    }
    const g = tg.closest('[data-tabgo]'); if (g) { ev.preventDefault(); showTab(g.dataset.tabgo, true); }
  };
  main.addEventListener('click', onClick); onCleanup(() => main.removeEventListener('click', onClick));
  $('#recreate').onclick = () => newEdit({from: 'reference', pick: R.name});
  $('#editmeta', main).onclick = e => { e.preventDefault(); metaModal(R); };
  KEYS = e => {                                          // the player's keys; 1 2 3, J K N belong to the panel on screen
    if (e.target.matches('input, textarea, select')) return;
    const k = e.key;
    if (P && (k === 'ArrowLeft' || k === 'ArrowRight')) { P.step((k === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? 10 : 1)); e.preventDefault(); }
    else if (P && k === ' ') { P.toggle(); e.preventDefault(); }
    else if (P && k === 'Home') { P.seek(0); e.preventDefault(); }
  };
  progress(); showTab(tab);
  // a video without effects (a talking head: only cuts) has nothing to select
  if (!evs.length) $('#detail').innerHTML = `<div class="empty">${t('No effects in this video - only plain cuts (the Overview has its rhythm). Nothing to check here.')}</div>`;
  if (P && selId && cur) P.seek(cur.start);
  if (tab === 'misses') setTimeout(() => $('#rtabs').scrollIntoView({block: 'start'}), 50);
}

// ============================================================================================ projects
// one card per video (the user, 2026-10-15: "the blocks are so big and show random info - it should at least show a
// preview of some render; clips, footage, versions / renders / in Resolve are good but very unorganized"): the newest
// render's picture (it plays, muted, while the pointer is on it) with the date of that render, the name, its length;
// the clips (or Generate's icon: made from zero) and the user's rating - or "Not reviewed yet" when the newest render
// has no rating yet (the user, the same day: "remove 1 version 1 render; remind the person"); newest render first
const RATE = {good: ['ok', t('Good')], ok: ['amber', t('OK')], bad: ['bad', t('Bad')]};
// the months as the language shortens them: Oct · oct (a date = "12 Oct 2025" / "12 oct 2025")
const MONTHS = LANG === 'en' ? ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  : Array.from({length: 12}, (_, i) => new Intl.DateTimeFormat(LANG, {month: 'short'}).format(new Date(2026, i, 15)).replace(/\.$/, ''));
// a time (seconds since 1970) in words: today 01:37 / yesterday 18:20 / 3 days ago / 12 Oct (+ the year if not this one);
// day = a date without a time: today / yesterday
const whenWords = (ts, day = false) => {
  if (!ts) return '';
  const d = new Date(ts * 1000), now = new Date(), d0 = x => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const n = Math.round((d0(now) - d0(d)) / 864e5), hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  return n <= 0 ? (day ? t('today') : t('today {hm}', {hm})) : n === 1 ? (day ? t('yesterday') : t('yesterday {hm}', {hm}))
    : n < 7 ? t('{n} days ago', {n})
    : `${d.getDate()} ${MONTHS[d.getMonth()]}${d.getFullYear() !== now.getFullYear() ? ' ' + d.getFullYear() : ''}`;
};
// the lab's own date strings ("2026-10-15", "2026-10-15 14:07", ISO): with a time = whenWords, a day only = without one
const strTime = s => { const m = /^(\d{4})-(\d\d)-(\d\d)(?:[ T](\d\d):(\d\d))?/.exec(String(s || ''));
  return m ? new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0)).getTime() / 1000 : 0; };
const whenStr = s => { const ts = strTime(s); return ts ? whenWords(ts, !/[ T]\d\d:\d\d/.test(s)) : ''; };
const pname = p => p.label || p.name;       // the name the app shows (Rename); the folder keeps its own
const genChip = () => `<span class="pgen" title="${ta('Made from zero (Generator) - no clips of your own')}"><svg class="i"><use href="#i-generate"/></svg>${t('Generated')}</span>`;
const reviewChip = (p, L) => !L ? '' : p.reviewed ? (rateChip(p.rating) || `<span class="prate ok" title="${ta('you rated its parts (How did it turn out?)')}">${t('Reviewed')}</span>`)
  : `<span class="prate todo" title="${p.rating ? ta('your rating ({rating}) was for an older render', {rating: RATE[p.rating] ? RATE[p.rating][1] : p.rating})
    : ta('How did it turn out? - rate it on its Review tab')}">${t('Not reviewed yet')}</span>`;
const picUrl = pc => !pc ? '' : pc.image ? fileUrl(pc.image) : `/api/thumb?video=${encodeURIComponent(pc.video)}&f=${pc.f}&fps=${pc.fps}`;
const lenWords = (frames, fps) => { if (!frames || !fps) return ''; const s = frames / fps;
  return s >= 60 ? `${Math.floor(s / 60)}:${pad(Math.round(s % 60))} min` : `${Math.round(s)} s`; };
const shapeWord = (w, h) => !w || !h ? '' : w > h * 1.1 ? t('horizontal') : h > w * 1.1 ? t('vertical') : t('square');
const rateChip = r => rvChip('result', r, t('your overall rating (How did it turn out?)'));     // the review's own chip (2026-10-18)
function projCard(p) {
  const L = p.latest, href = '#/project/' + encodeURIComponent(p.name), pc = p.picture;
  const now = L ? lenWords(L.frames, L.fps) || t('rendered') : p.plans.length ? `<span class="amber">${t('not rendered yet')}</span>` : `<span class="muted">${p.generated ? t('not made yet') : t('no edit yet')}</span>`;
  const fr = pc && pc.video ? `f${pc.f} (${tc(pc.f, pc.fps)})` : '';
  return `<div class="card pcard">${newTag(`p:${p.name}@${Math.round(p.done_t || 0)}`, p.done_t)}<a class="clink" href="${href}">
    <div class="ppic"${L ? ` data-v="${esc(L.rel)}" data-t="${pc && pc.video === L.rel ? (pc.f + 0.5) / pc.fps : 0}"` : ''}>${pc ? `<img src="${picUrl(pc)}" loading="lazy" alt=""
      ${pc.video ? `title="${L && pc.video === L.rel ? ta('{frame} of the newest render', {frame: fr}) : fr}"` : ''}>` : `<svg class="ic"><use href="#i-${p.generated ? 'generate' : 'edit'}"/></svg>`}
      <span class="pbadges">${p.title ? `<span class="pbadge" title="${ta('title, thumbnails and description are ready')}">${t('ready to post')}</span>` : ''}${p.resolve.length ? `<span class="pbadge r" title="${ta('also built as a DaVinci Resolve project')}">Resolve</span>` : ''}</span>
      <span class="pwhen" title="${L ? ta('the newest render: {date}', {date: L.modified}) : ta('made {when}', {when: whenWords(p.created)})}">${L ? esc(whenWords(L.mtime)) : t('made {when}', {when: esc(whenWords(p.created))})}</span>${L ? '<span class="pplay">▶</span>' : ''}</div>
    <div class="cb"><span class="ct">${esc(pname(p))}</span><div class="small">${now}</div></div></a>
    <div class="pfacts"><span>${p.clips ? `${tn(p.clips, '<b>{n}</b> clip', '<b>{n}</b> clips')} · ${bytes(p.footage_bytes)}` : p.generated ? genChip() : `<span class="muted">${t('no clips yet')}</span>`}</span>
      ${reviewChip(p, L)}</div>
    <span class="pdel"><button class="btn sm ghost icon" data-ren="${esc(p.name)}" title="${ta('Rename…')}"><svg class="i"><use href="#i-pen"/></svg></button>${delBtn('project', p.name)}</span></div>`;
}
// Rename (the user, 2026-10-15: "I can't rename my edits?"): the name the app shows - build\project.json "label";
// the folder keeps its name, so the clips, the edits and a Resolve project still find everything
function renameModal(p) {
  modal(`<h2>${t('Rename')}</h2><div class="small muted" style="margin-top:-4px">${t('The name MotionLab shows for this video. Its folder stays “{folder}”, so your clips, edits and Resolve still find everything.', {folder: esc(p.name)})}</div>
    <input type="text" id="rnname" value="${esc(pname(p))}" maxlength="80" style="width:100%;margin-top:14px">
    <div class="row" style="margin-top:14px"><button class="btn pri" id="rnok">${t('Save')}</button><button class="btn" id="rnno">${t('Cancel')}</button>
      ${p.label ? `<span class="grow"></span><a href="#" class="small" id="rnback">${t('Back to “{name}”', {name: esc(p.name)})}</a>` : ''}</div>`, el => {
    const inp = $('#rnname', el); inp.focus(); inp.select();
    const save = async label => {
      try { await api(`/api/project/${encodeURIComponent(p.name)}/rename`, {label}); closeModal(); toast(t('Renamed'), 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    };
    $('#rnok', el).onclick = () => { const v = inp.value.trim(); if (!v) { inp.focus(); return; } save(v); };
    inp.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); $('#rnok', el).click(); } };
    $('#rnno', el).onclick = closeModal;
    const bk = $('#rnback', el); if (bk) bk.onclick = e => { e.preventDefault(); save(''); };
  });
}
// a video made from zero shows in the Generator only, until the user moves it to the Editor (0.4.3.5)
const inGenerator = p => !!p.generated && !p.in_editor;
async function pageProjects(main) {
  const [all, BAT] = await Promise.all([api('/api/projects'), api('/api/batches?kind=recreate').catch(() => [])]);
  const ps = all.filter(p => !inGenerator(p)).sort((a, b) => (b.sort_t || 0) - (a.sort_t || 0));
  const cv = big => `<button class="btn pri${big ? ' big' : ''}" id="cvnew"><svg class="i"><use href="#i-edit"/></svg>${t('New edit')}</button>`;
  const many = ps.filter(p => p.clips).length >= 2;
  main.innerHTML = `<div class="head"><div><h1>${t('Editor')}</h1><div class="sub">${t('Your clips, cut like videos you analysed, the way you say - or from a prompt.')}</div></div></div>
    ${ps.length ? `<div class="toprow">${cv(true)}${many ? `<button class="btn ghost big" id="bkedit" title="${ta('One style for several of your videos - quick drafts, or one Claude window for all of them')}"><svg class="i"><use href="#i-videos"/></svg>${t('Edit several videos')}</button>` : ''}<span class="grow"></span><button class="btn" data-open="projects" title="${ta('the folder with all your videos')}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button></div>` : ''}
    ${batchRows(BAT)}
    ${ps.length ? `<div class="cards pcards">${ps.map(projCard).join('')}</div>`
      : emptyHero('edit', t('Make your first edit'), t('Your clips and a style - up to three videos you analysed, or your own words. A quick draft takes minutes; Claude makes it great.'), cv(true))}`;
  $('#cvnew', main).onclick = () => newEdit();
  const bk = $('#bkedit', main); if (bk) bk.onclick = () => bulkEditModal();
  wireBatchRows(main, () => pageProjects(main));
  wirePcards(main, ps);
}
// ---- Bulk (0.4.5, the user: "bulk analyze thumbnails, videos, and also bulk edit stuff or generate"): a batch that
// Claude has not finished (its window stopped - a limit, closed) waits here with *Continue the batch* (the skill skips
// what is done); ✕ forgets it (the videos stay as they are)
function batchRows(B) {
  return (B || []).map(b => {
    const v = {done: b.done.length, videos: plural(b.items.length, 'video'), when: esc(whenStr(b.created)), left: plural(b.left.length, 'video')};
    return `<div class="bkrow"><svg class="i"><use href="#i-claude"/></svg><span class="grow">${b.kind === 'review'
      ? t('<b>Claude checked {done} of {videos}</b> of the batch from {when} - {left} left', v)
      : t('<b>Claude edited {done} of {videos}</b> of the batch from {when} - {left} left', v)}</span>
    ${claudeBtn(b.prompt, t('Continue the batch'), b.task, `batch of ${b.left.length}`, 'sm pri')}<button class="btn sm ghost" data-bkforget="${esc(b.id)}" title="${ta('Forget this batch (the videos stay as they are)')}">✕</button></div>`;
  }).join('');
}
function wireBatchRows(main, redraw) {
  $$('[data-bkforget]', main).forEach(x => x.onclick = async () => {
    try { await api('/api/batches/forget', {id: x.dataset.bkforget}); redraw(); } catch (e) { toast(e.message, 'err'); }
  });
}
// Editor > Edit several videos (0.4.5): 2-10 of your videos, one style (up to 3 analysed videos, or presets + your
// words), optional length / format; then a quick draft each (queued jobs, no Claude) or ONE Claude window for all
// (/recreate-video batch <id>) - Claude's usual time per edit on this PC said first
async function bulkEditModal() {
  const [ps, S, OPT, EST] = await Promise.all([api('/api/projects'), loadStyles(), api('/api/edit/options'), api('/api/estimate').catch(() => ({}))]);
  const vids = ps.filter(p => !inGenerator(p) && p.clips).sort((a, b) => (b.sort_t || 0) - (a.sort_t || 0));
  const st = {how: 'style', like: [], presets: [], length: '', format: ''};
  modal(`<h2>${t('Edit several videos the same way')}</h2>
    <div class="avstep"><b>1</b><span>${t('Which videos?')}</span><span class="small muted">${t('2 to {max} - each keeps its own clips and the song in its folder', {max: AV_MAX})}</span></div>
    <div class="avfiles" id="bkv">${vids.map(p => `<label class="avfile"><input type="checkbox" value="${esc(p.name)}"><span class="grow">${esc(pname(p))}</span><span class="small dim">${plural(p.clips, 'clip')}${p.renders && p.renders.length ? ' · ' + t('edited before') : ''}</span></label>`).join('')}</div>
    <div class="avstep"><b>2</b><span>${t('In which style?')}</span></div>
    <div class="seg" id="bkhow"><button data-v="style">${t('Like videos you analysed')}</button><button data-v="words">${t('The way you say')}</button></div>
    <div id="bkstyle" style="margin-top:8px"></div>
    <div id="bkwords" hidden style="margin-top:8px"><div class="gpre">${OPT.presets.map(x => `<button class="fchip" data-p="${esc(x.id)}" title="${esc(t(x.help))}">${esc(t(x.label))}</button>`).join('')}</div>
      <textarea id="bkwant" rows="2" placeholder="${ta('…and / or in your words, e.g. fast cuts on the beat, captions word by word')}" style="margin-top:8px"></textarea></div>
    <div class="nestep opt" style="margin-top:12px"><b>3</b>${t('Length and format')} ${optTag()}</div>
    <div class="nedet"><label>${t('Length')}</label><div class="seg" id="bklen">${[['', t('Auto')], ['15', '15 s'], ['30', '30 s'], ['45', '45 s'], ['60', '1 min']].map(([v, l]) => `<button data-v="${v}">${l}</button>`).join('')}</div>
      <label>${t('Format')}</label><div class="seg" id="bkfmt">${[['', t('Auto')], ['vertical', t('Vertical 9:16')], ['horizontal', t('Horizontal 16:9')], ['square', t('Square')]].map(([v, l]) => `<button data-v="${v}">${l}</button>`).join('')}</div></div>
    <div class="row" style="margin-top:16px"><button class="btn big" id="bkdraft" disabled>${t('Quick drafts now')}</button>
      <button class="btn pri big" id="bkclaude" disabled><svg class="i"><use href="#i-claude"/></svg>${t('Make them with Claude')}</button></div>
    <div class="small muted" id="bksum" style="margin-top:8px"></div>`, el => {
    const picked = () => $$('#bkv input:checked', el).map(x => x.value);
    const upd = () => {
      const n = picked().length, styled = st.how === 'style' ? st.like.length > 0 : st.presets.length > 0 || $('#bkwant', el).value.trim();
      const ok = n >= 2 && n <= AV_MAX && styled;
      $('#bkdraft', el).disabled = $('#bkclaude', el).disabled = !ok;
      $('#bkstyle', el).hidden = st.how !== 'style'; $('#bkwords', el).hidden = st.how !== 'words';
      $('#bksum', el).innerHTML = n < 2 ? t('Pick at least two videos.') : n > AV_MAX ? t('At most {n} at a time.', {n: AV_MAX}) : !styled ? t('Pick a style.')
        : t('<b>Quick drafts</b>: a first edit of each in minutes, made by rules - no Claude. <b>With Claude</b>: one window edits them one after another - {time}.', {time: estWords(EST.recreate, n, 'edit')});
    };
    spSeg(el, '#bkhow', st, 'how', upd); spSeg(el, '#bklen', st, 'length'); spSeg(el, '#bkfmt', st, 'format');
    stylePicker($('#bkstyle', el), st, {S, purpose: 'edit', max: OPT.max_refs, onChange: upd});
    $$('[data-p]', el).forEach(b => b.onclick = () => {
      const i = st.presets.indexOf(b.dataset.p);
      if (i >= 0) st.presets.splice(i, 1); else st.presets.push(b.dataset.p);
      b.classList.toggle('on', i < 0); upd();
    });
    $('#bkv', el).onchange = upd; $('#bkwant', el).oninput = upd;
    const go = async mode => {
      $('#bkdraft', el).disabled = $('#bkclaude', el).disabled = true;
      try {
        const r = await api('/api/edit/batch', {projects: picked(), mode, request: {how: st.how, like: st.how === 'style' ? st.like : [],
          presets: st.how === 'words' ? st.presets : [], want: st.how === 'words' ? $('#bkwant', el).value : '', length_s: st.length || null,
          format: st.format || null, sound: 'auto', resolve: false}});
        closeModal();
        if (mode === 'claude') openClaude(r.prompt, 'recreate', r.label);
        else { ping(); toast(t('{drafts} on the way - one after another', {drafts: plural(r.jobs.length, 'quick draft')}), 'ok'); }
        route();
      } catch (e) { toast(e.message, 'err'); upd(); }
    };
    $('#bkdraft', el).onclick = () => go('drafts');
    $('#bkclaude', el).onclick = () => go('claude');
    upd();
  }, 'wide');
}
// the video cards' Rename pencils + the render playing while the pointer is on its picture (Editor, Generator)
function wirePcards(main, ps) {
  $$('[data-ren]', main).forEach(b => b.onclick = e => { e.preventDefault(); renameModal(ps.find(x => x.name === b.dataset.ren)); });
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  $$('.ppic[data-v]', main).forEach(box => {          // the render plays while the pointer is on its picture
    box.onmouseenter = () => {
      if ($('video', box)) return;
      const v = document.createElement('video');
      Object.assign(v, {muted: true, loop: true, playsInline: true, preload: 'auto'});
      v.onloadedmetadata = () => { v.currentTime = +box.dataset.t || 0; v.play().catch(() => {}); };
      v.onplaying = () => box.classList.add('playing');
      v.src = fileUrl(box.dataset.v); box.appendChild(v);
    };
    box.onmouseleave = () => { const v = $('video', box); box.classList.remove('playing');
      if (v) { v.pause(); v.removeAttribute('src'); v.load(); v.remove(); } };
  });
}

// ---- Editor > New edit: a pop-up of steps (2026-10-22, the user: "the edit a video is our most powerful tool so we
// kinda need to expand to give Claude the most options and customability ... simplicity and clarity rather than having
// everything in a single section"; after a page that day: "still make it a pop up as before? and just show section per
// section, make the sidebar steps with numbers isntead of letters, and make a line go through them so the user know
// where to go", in the look of their mock-up new_edit_section.html; then: "a little preview when we have selected
// clips ... manage them? delete ... there is too much text and it clutters the vision of the user ... less text and
// more colors, icons and more distinct"). One step on screen at a time - 1 Clips (the clips as pictures), 2 Text (what
// it is about | the words on screen, a script or brief from Prepare), 3 References (picture cards), 4 Style, 5 Sound,
// 6 Final (length, format, the summary, Claude's time) - Back / Next in the footer; on the left the steps on a line:
// done = a tick and the short answer, the one on screen = Now, the line gold up to it (a click jumps there). Words
// only where a picture or an icon cannot say it; the rest in tooltips. Only the clips are needed: what is left on Auto
// is Claude's call. One function per step draws it, writes ne.st and may return a refresh (run on every change);
// neRows = what was picked, read by the steps and the summary. Saved as build\edit_request.json + build\edit_brief.md
// (POST /api/project/<p>/edit_request, motionlab\editreq.py): Claude (/recreate-video request <p>) and the quick draft
// read it. Was a four-step dialog (0.4 - 0.5.1, createVideoModal).
const NE_STEPS = [   // [id, the name on the left, the step's title, its icon + colour in the summary]
  ['clips', t('Clips'), t('Choose your clips'), 'i-videos', '--amber'],
  ['text', t('Text'), t('Give Claude context'), 'i-pen', '--cyan'],
  ['refs', t('References'), t('Add references'), 'i-refs', '--pink'],
  ['style', t('Style'), t('Pick the style'), 'i-palette', '--violet'],
  ['sound', t('Sound'), t('How does it sound?'), 'i-music', '--green'],
  ['final', t('Final'), t('Last details'), 'i-clock', '--amber']];
const neIcon = (id, colour = '') => `<svg class="i"${colour ? ` style="color:var(${colour})"` : ''}><use href="#${id}"/></svg>`;
const neTalk = id => /^(script|hook)-/.test(id || '');          // a talking script / hook: the user films it
async function newEdit(pre = {}) {    // pre = {project, from: 'reference' | 'prompt', pick}
  let S, PRM, ps, OPT;
  try { [S, PRM, ps, OPT] = await Promise.all([loadStyles(), api('/api/prompts'), api('/api/projects'), api('/api/edit/options')]); }
  catch (e) { toast(e.message, 'err'); return; }
  const pick = pre.from === 'prompt' ? pre.pick || '' : '';
  const st = {src: pre.project && ps.some(x => x.name === pre.project) ? 'old' : ps.length ? '' : 'new', project: pre.project || '', newp: '',
              about: '', onscreen: '', prompt: pick, like: pre.from === 'reference' && pre.pick ? [pre.pick] : [], exact: false,
              where: '', type: '', rhythm: '', moods: [], captions: '', presets: [], want: '', palette: [],
              sound: neTalk(pick) ? 'talk' : 'auto', sfx: '', kinds: [], snotes: '', length: '', format: '', resolve: false,
              photos: {}};
  const ne = {S, PRM, ps, OPT, st, cur: 0};
  ne.proj = () => st.src === 'old' ? st.project : st.src === 'new' ? st.newp : '';
  ne.P = () => ps.find(x => x.name === ne.proj());
  const N = NE_STEPS.length;
  modal(`<div class="nemw"><div class="nehd"><h2>${t('New edit')}</h2><p>${t('Your clips, edited the way you want. They are only read, never changed.')}</p></div>
    <nav class="nenav">${NE_STEPS.map(([id, name], i) => `<button data-go="${id}"${id === 'clips' ? '' : ' class="opt"'}><b>${i + 1}</b><span>${name}<small></small></span></button>`).join('')}</nav>
    <div class="nepanes">${NE_STEPS.map(([id, , title]) => `<section class="nesec" id="ne-${id}" hidden><h2 class="nest">${title}${id === 'clips' ? '' : optTag()}<span class="nestx"></span></h2><div class="nesecb"></div></section>`).join('')}</div>
    <div class="nefoot"><span class="small muted" id="nepos"></span>
      <label class="neres" id="neresl" hidden><input type="checkbox" id="neres"><span><b>${t('Also build it as a DaVinci Resolve project')}</b><span>${t('the same edit as a timeline you can keep editing by hand')}</span></span></label>
      <button class="btn" id="neback">${t('← Back')}</button><button class="btn pri" id="nenext"></button>
      <button class="btn" id="cvdraft" disabled><svg class="i"><use href="#i-generate"/></svg>${t('Quick draft now')}</button>
      <button class="btn pri" id="cvgo" disabled><svg class="i"><use href="#i-claude"/></svg>${t('Make it with Claude')}</button></div></div>`, el => {
    ne.el = el;
    const draw = {clips: neClips, text: neText, refs: neRefs, style: neStyle, sound: neSound, final: neFinal};
    const refresh = [];
    ne.changed = () => refresh.forEach(f => f());
    NE_STEPS.forEach(([id]) => { const f = draw[id]($(`#ne-${id} .nesecb`, el), ne); if (f) refresh.push(f); });
    refresh.push(() => neNav(el, ne));
    const go = id => {
      const i = NE_STEPS.findIndex(s => s[0] === id); if (i < 0) return;
      const last = i === N - 1;
      ne.cur = i;
      NE_STEPS.forEach(([sid], j) => { $(`#ne-${sid}`, el).hidden = j !== i; });
      $('.nepanes', el).scrollTop = 0;
      $('#nepos', el).textContent = t('Step {n} of {total}', {n: i + 1, total: N});
      $('#nepos', el).hidden = last; $('#neresl', el).hidden = !last;
      $('#neback', el).hidden = !i;
      $('#nenext', el).hidden = last; if (!last) $('#nenext', el).textContent = `${t('Next: {step}', {step: NE_STEPS[i + 1][1]})} →`;
      $('#cvgo', el).hidden = $('#cvdraft', el).hidden = !last;
      neNav(el, ne);
    };
    $$('.nenav button', el).forEach(b => b.onclick = () => go(b.dataset.go));
    $('#neback', el).onclick = () => go(NE_STEPS[ne.cur - 1][0]);
    $('#nenext', el).onclick = () => go(NE_STEPS[ne.cur + 1][0]);
    $('#neres', el).onchange = e => { st.resolve = e.target.checked; ne.changed(); };
    const save = () => api(`/api/project/${encodeURIComponent(ne.proj())}/edit_request`, neBody(st));
    $('#cvgo', el).onclick = async () => {
      try { const pj = ne.proj(), r = await save();
        openClaude(r.command, 'recreate', `${r.request.how} → ${pj}`); closeModal(); location.hash = '#/project/' + encodeURIComponent(pj); }
      catch (e) { toast(e.message, 'err'); }
    };
    $('#cvdraft', el).onclick = async () => {
      try { const pj = ne.proj(); await save();
        await api('/api/jobs', {kind: 'draft', args: {project: pj}, queue: true});
        toast(t('The quick draft is on its way - it shows up here when it is ready'), 'ok'); closeModal(); location.hash = '#/project/' + encodeURIComponent(pj); }
      catch (e) { toast(e.message, 'err'); }
    };
    ne.go = go;
    ne.changed(); go('clips');
  }, 'wide nemodal');
}

// 1. Clips: the clips of a video they already have ("old") or new clips copied into a new video ("new", st.newp once
// made) - the two wide cards of 2026-10-16 (the user: "choose between an old video clip or new clips, intuitive and
// distinct") - then the video's clips as pictures (GET /api/project/<p>'s sources, a frame each by /api/thumb): a click
// plays one in the PC's player, the bin moves one to the Recycle Bin after a yes here (the app's delete route, a file
// in the video's folder: trash.plan_file - the user's click, never Claude's), the + tile (or a drop) copies more in;
// the folder's songs as chips under them. ne.addFiles = the copy, also used by 5's *Add a song…*.
// 2026-10-24 (a friend's asks): *Add a folder…* (or a folder dropped - sub-folders too, clipsFromDrop / clipNames),
// never a Mac's / iPhone's ._ files (isJunk), photos as photos (a PHOTO badge, its own picture, how long it shows -
// st.photos -> edit_request "photos"), and the new video's name stays editable (POST .../rename = its label).
function neClips(box, ne) {
  const {st, ps} = ne;
  ne.clips = {};                     // per video: its clips as the server lists them (loaded once, again after a change)
  box.innerHTML = `<div class="cvchoice nesrc">
      <button class="cvopt" data-src="old" ${ps.length ? '' : 'disabled'}><svg class="ic"><use href="#i-videos"/></svg><b>${t('Clips you already have')}</b>
        <span>${ps.length ? plural(ps.length, 'video') : t('No video yet - start with new clips')}</span></button>
      <button class="cvopt" data-src="new"><svg class="ic"><use href="#i-upload"/></svg><b>${t('New clips')}</b><span>${t('From your PC - copied in')}</span></button></div>
    <div class="nesrcrow" id="nesrc-old" hidden>${neIcon('i-videos', '--amber')}<select id="cvp">${ps.map(x => `<option value="${esc(x.name)}">${esc(pname(x))} (${plural(x.clips, 'clip')})</option>`).join('')}</select>
      <span class="small muted" id="necount"></span><button class="btn sm ghost" id="nefold" title="${ta("the video's folder: your clips and everything made from them")}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button></div>
    <div class="nesrcrow" id="nesrc-new" hidden>${neIcon('i-pen', '--amber')}<input type="text" id="cvname" placeholder="${ta('Name the video, e.g. cooking vlog 1')}" title="${ta('Leave it empty to name it after the first clip.')}"></div>
    <div id="neclips"></div><div id="nerm"></div><div id="cvfiles"></div>`;
  const sel = $('#cvp', box), name = $('#cvname', box), rel = (pj, f) => `projects/${pj}/${f}`;
  if (st.src === 'old') sel.value = st.project; else st.project = sel.value;
  const load = async pj => {
    ne.clips[pj] = 'loading';
    let list = [];
    try { list = (await api('/api/project/' + encodeURIComponent(pj))).sources.filter(s => s.exists !== false); } catch (e) { toast(e.message, 'err'); }
    ne.clips[pj] = list;
    const P = ps.find(x => x.name === pj), o = [...sel.options].find(x => x.value === pj);
    if (P) { P.clips = list.length; if (o) o.textContent = `${pname(P)} (${plural(P.clips, 'clip')})`; }   // the count the list shows, kept true
    ne.changed();
  };
  const PH_S = [3, 5, 8];                             // a photo's length in the edit: a click on its pill goes round these
  const phS = n => (st.photos[n] || {}).seconds || 5;
  const tile = (pj, c) => { const ph = c.photo || PHOTO_EXT.test(c.name);
    return `<div class="neclip${ph ? ' photo' : ''}" title="${esc(c.name)}">
      <button class="neclipv" data-play="${esc(c.name)}" title="${ph ? ta('Open the photo') : ta('Play it')}"><img src="/api/thumb?video=${encodeURIComponent(rel(pj, c.name))}&f=${ph ? 0 : 12}&fps=25" loading="lazy" alt="" onerror="this.remove()">
        <svg class="i"><use href="#${ph ? 'i-thumb' : 'i-play'}"/></svg>${ph ? `<b class="nephoto">${t('PHOTO')}</b>` : c.duration_s ? `<i>${ytOf(c.duration_s, 1)}</i>` : ''}</button>
      <span class="neclipn">${esc(c.name)}</span>
      ${ph ? `<button class="nephs" data-phs="${esc(c.name)}" title="${ta('The longest the photo shows in the edit - click to change')}">${t('{n} s', {n: phS(c.name)})}</button>` : ''}
      <button class="neclipx" data-rm="${esc(c.name)}" title="${ta('Delete… (to the Recycle Bin)')}"><svg class="i"><use href="#i-trash"/></svg></button></div>`; };
  let drawn = '';
  const paint = () => {
    const pj = ne.proj(), P = ne.P(), songs = (P || {}).songs || [];
    $$('.nesrc .cvopt', box).forEach(b => b.classList.toggle('on', b.dataset.src === st.src));
    $('#nesrc-old', box).hidden = st.src !== 'old'; $('#nesrc-new', box).hidden = st.src !== 'new';
    name.title = st.newp ? t('The name MotionLab shows for this video - change it whenever you like') : t('Leave it empty to name it after the first clip.');
    let C = pj ? ne.clips[pj] : [];
    if (pj && C === undefined) { load(pj); C = ne.clips[pj]; }
    const key = JSON.stringify([st.src, pj, C, songs, st.photos]);
    if (key === drawn) return;                         // the grid only when its clips change (not on every key typed)
    drawn = key;
    const el = $('#neclips', box), clips = Array.isArray(C) ? C : [];
    $('#necount', box).textContent = P ? [plural(clips.length, 'clip'), songs.length ? plural(songs.length, 'song') : ''].filter(Boolean).join(' · ') : '';
    $('#nefold', box).dataset.open = 'projects/' + pj;
    if (!st.src) { el.innerHTML = ''; return; }
    const big = !clips.length;
    el.innerHTML = C === 'loading' ? `<div class="small muted">${t('Loading…')}</div>` : `<div class="neclips${big ? ' empty' : ''}">${clips.map(c => tile(pj, c)).join('')}
        <label class="neadd${big ? ' big' : ''}" data-add="files"><input type="file" multiple hidden accept="${CLIP_ACCEPT}">${neIcon('i-plus')}
          <b>${big ? t('Drop your clips here') : t('Add clips…')}</b>${big ? `<span>${t('videos, photos or a whole folder - or click to choose them')}</span>` : ''}</label>
        <label class="neadd neaddf${big ? ' big' : ''}" data-add="folder" title="${ta('Every video, photo and song in a folder, its sub-folders too')}"><input type="file" hidden webkitdirectory multiple>${neIcon('i-folder')}
          <b>${t('Add a folder…')}</b>${big ? `<span>${t('sub-folders too')}</span>` : ''}</label></div>
      ${songs.length ? `<div class="nesongs">${songs.map(s => `<span class="nesong">${neIcon('i-music')}${esc(s)}<button class="neclipx" data-rm="${esc(s)}" title="${ta('Delete… (to the Recycle Bin)')}"><svg class="i"><use href="#i-trash"/></svg></button></span>`).join('')}</div>` : ''}`;
    const inp = $('[data-add=files] input', el), dir = $('[data-add=folder] input', el);
    if (inp) inp.onchange = () => { ne.addFiles([...inp.files]); inp.value = ''; };
    if (dir) dir.onchange = () => { ne.addFiles([...dir.files].map(f => ({file: f, path: f.webkitRelativePath || f.name})), undefined, true); dir.value = ''; };
    const grid = $('.neclips', el);
    if (grid) {
      grid.ondragover = e => { e.preventDefault(); grid.classList.add('on'); };
      grid.ondragleave = () => grid.classList.remove('on');
      grid.ondrop = async e => { e.preventDefault(); grid.classList.remove('on');
        try { const r = await clipsFromDrop(e.dataTransfer); ne.addFiles(r.files, undefined, r.folders); }
        catch (err) { toast(err.message, 'err'); } };
    }
    $$('[data-play]', el).forEach(b => b.onclick = () => api('/api/open', {path: rel(pj, b.dataset.play)}).catch(e => toast(e.message, 'err')));
    $$('[data-rm]', el).forEach(b => b.onclick = () => remove(b.dataset.rm));
    $$('[data-phs]', el).forEach(b => b.onclick = () => { const n = b.dataset.phs, s = PH_S[(PH_S.indexOf(phS(n)) + 1) % PH_S.length];
      st.photos[n] = {...(st.photos[n] || {}), seconds: s}; ne.changed(); });
  };
  // the bin: what the Delete dialog would say (GET /api/delete), here in the step - a pop-up over this one would lose it
  const remove = async file => {
    const pj = ne.proj(), r = rel(pj, file), host = $('#nerm', box);
    let pl;
    try { pl = await api(`/api/delete?kind=file&name=${encodeURIComponent(r)}`); } catch (e) { toast(e.message, 'err'); return; }
    const it = pl.items[0];
    host.innerHTML = `<div class="nerm"><svg class="i"><use href="#i-trash"/></svg><div class="grow"><b>${t('Remove {name}?', {name: esc(file)})}</b>
        <div class="small muted">${t('It goes to the Windows Recycle Bin - you can restore it from there.')} · ${bytes(it.bytes)}</div>
        ${it.warn.map(w => `<div class="small warnline">⚠ ${esc(t(w))}</div>`).join('')}</div>
      <button class="btn del" id="nermgo">${t('Move to the Recycle Bin')}</button><button class="btn" id="nermno">${t('Cancel')}</button></div>`;
    $('#nermno', host).onclick = () => { host.innerHTML = ''; };
    $('#nermgo', host).onclick = async () => {
      $('#nermgo', host).disabled = true;
      try {
        const res = await api('/api/delete', {kind: 'file', name: r, keys: pl.items.filter(x => x.default).map(x => x.key)});   // + a photo's old still-video copy
        if (res.failed.length) { host.innerHTML = `<div class="nerm"><span class="bad">${esc(t(res.failed[0].why))}</span></div>`; return; }
        host.innerHTML = ''; delete st.photos[file];
        toast(t('Moved to the Recycle Bin ({size}): {list}', {size: bytes(res.bytes), list: res.moved.join(', ')}), 'ok');
        const P = ne.P();
        if (P && (P.songs || []).includes(file)) { P.songs = P.songs.filter(s => s !== file); if (st.sound === 'music:' + file) st.sound = 'auto'; }
        delete ne.clips[pj];
        ne.changed();
      } catch (e) { toast(e.message, 'err'); $('#nermgo', host).disabled = false; }
    };
  };
  sel.onchange = () => { st.project = sel.value; $('#cvfiles', box).innerHTML = $('#nerm', box).innerHTML = ''; ne.changed(); };
  // the new video's name: before its folder exists it names the folder; after, it is the name MotionLab shows (the
  // folder keeps its own - the clips stay where they are), saved on Enter or when the field is left
  const rename = async () => {
    const v = name.value.trim(), P = ne.P();
    if (!st.newp || !P || !v || v === pname(P)) return;
    try { const r = await api(`/api/project/${encodeURIComponent(st.newp)}/rename`, {label: v});
      P.label = r.label || null; name.value = pname(P);
      const o = [...sel.options].find(x => x.value === st.newp); if (o) o.textContent = t('{name} (new)', {name: pname(P)});
      toast(t('Name saved: {name}', {name: pname(P)}), 'ok'); }
    catch (e) { toast(e.message, 'err'); }
  };
  name.onchange = rename;
  name.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); rename(); } };
  $$('.nesrc .cvopt', box).forEach(b => b.onclick = () => { if (st.busy || st.src === b.dataset.src) return;
    st.src = b.dataset.src; $('#cvfiles', box).innerHTML = $('#nerm', box).innerHTML = ''; ne.changed(); });
  // picked or dropped files -> the video's folder (a new video is made first, named by the user or after the first clip)
  // list = Files, or {file, path} from a folder (folder = true: the toast says what it found)
  ne.addFiles = async (list, rows = $('#cvfiles', box), folder = false) => {
    const all = [...list].map(x => x instanceof File ? {file: x, path: x.name} : x);
    const {clips: files, skipped} = clipNames(all);
    const odd = all.filter(x => !isJunk(x.file.name, x.path) && !CLIP_EXT.test(x.file.name));
    if (folder) toast(files.length ? tn(files.length, '{n} clip found in the folder', '{n} clips found in the folder')
      : t('No video, photo or sound files in that folder'), files.length ? 'ok' : 'err');
    else if (odd.length) toast(t('{files}: not a video, a photo or a sound file', {files: odd.map(x => x.file.name).join(', ')}), 'err');
    if (skipped && !folder && !odd.length) toast(t('Hidden files a Mac or an iPhone leaves next to clips were left out'));
    if (!files.length || st.busy) return;
    if (!st.src) { toast(t('First pick where your clips come from (1. Clips)'), 'err'); ne.go('clips'); return; }
    st.busy = true;
    try {
      if (st.src === 'new' && !st.newp) {
        let nm = name.value.trim();
        const top = folder && (all.find(x => x.path.includes('/')) || {}).path;           // a folder: named after it
        if (!nm) { const base = folderName(top ? top.split('/')[0] : files[0].name.replace(/\.[^.]+$/, '')); nm = base;
          for (let i = 2; ps.some(x => x.name.toLowerCase() === nm.toLowerCase()); i++) nm = `${base} ${i}`; }
        const r = await api('/api/projects/new', {name: nm});
        ps.unshift({name: r.name, label: null, clips: 0, songs: []}); st.newp = name.value = r.name;
        sel.insertAdjacentHTML('afterbegin', `<option value="${esc(r.name)}">${t('{name} (new)', {name: esc(r.name)})}</option>`);
      }
      const pj = ne.proj(), P = ne.P();
      for (const {file: f, name: nm} of files) {
        const row = document.createElement('div'); row.className = 'fifile';
        row.innerHTML = `<span class="grow">${esc(nm)} <span class="small muted">${bytes(f.size)}</span></span><span class="fibar"><i></i></span><span class="small" data-s>${t('copying…')}</span>`;
        rows.append(row);
        try {
          const r = await uploadClip(pj, f, neTalk(st.prompt) ? st.prompt : '', v => { $('.fibar i', row).style.width = `${Math.round(v * 100)}%`; }, nm);
          $('.fibar i', row).style.width = '100%'; row.classList.add('ok');
          $('[data-s]', row).textContent = r.kept ? t('already there') : r.file !== nm ? t('copied as {name} ✓', {name: r.file}) : t('copied ✓');
          if (!r.kept) { if (/\.(mp3|m4a|wav|aac|flac|ogg)$/i.test(nm)) (P.songs = P.songs || []).push(r.file); else P.clips++; }
        } catch (e) { row.classList.add('err'); $('[data-s]', row).textContent = e.message; }
      }
      delete ne.clips[pj];                             // listed again: the new clips show as pictures
      setTimeout(() => $$('.fifile.ok', rows).forEach(x => x.remove()), 2500);
    } catch (e) { toast(e.message, 'err'); }
    st.busy = false; ne.changed();
  };
  return paint;
}

// 2. Text: what Claude follows - what it is about | the words on screen as written (side by side), a script or brief
// from Prepare / the prompt library (the list, the picked one read beside it)
function neText(box, ne) {
  const {st, PRM} = ne, KL = Object.fromEntries(PRM.kinds.map(k => [k.id, k.label]));
  const items = PRM.items.filter(x => ['brief', 'script', 'hook'].includes(x.kind));
  const badge = x => `<span class="kbadge k-${esc(x.kind)}">${esc(t(KL[x.kind] || x.kind))}</span>`;
  box.innerHTML = `<div class="netwo"><div class="nef"><label for="neabout">${neIcon('i-pen', '--cyan')}${t('What is the video about?')}</label>
        <textarea id="neabout" rows="4" placeholder="${ta('e.g. a day at the climbing gym with my friends - funny, it ends with me finally reaching the top')}">${esc(st.about)}</textarea></div>
      <div class="nef"><label for="neons">${neIcon('i-type', '--pink')}${t('Text on screen')}</label>
        <textarea id="neons" rows="4" placeholder="${ta('One per line - e.g. DAY 1 OF 30')}">${esc(st.onscreen)}</textarea></div></div>
    <div class="nef"><label>${neIcon('i-scriptok', '--green')}${t('A script or brief from Prepare')}</label>
      <div class="nepick"><div class="nelist"><div class="nelq"><input type="search" id="cvq" placeholder="${ta('Search your scripts and briefs…')}"></div><div class="cvlist" id="cvpl"></div></div>
        <div class="neprev" id="neprev"></div></div></div>`;
  $('#neabout', box).oninput = e => { st.about = e.target.value; ne.changed(); };
  $('#neons', box).oninput = e => { st.onscreen = e.target.value; ne.changed(); };
  const prev = () => { const x = items.find(i => i.id === st.prompt);
    $('#neprev', box).innerHTML = x ? `<div class="row sp"><b>${esc(x.title || x.title_auto || x.id)}</b>${badge(x)}</div>
      <p class="neptext">${esc(x.text.slice(0, 480))}${x.text.length > 480 ? '…' : ''}</p>` : `<div class="neprev0">${neIcon('i-sparkle', '--amber')}<span>${t('Nothing picked - Claude works from your notes and your clips.')}</span></div>`; };
  const drawPrompts = q => {
    const row = x => `<label class="cvitem${x.id === st.prompt ? ' on' : ''}"><input type="radio" name="cvr" value="${esc(x.id)}" ${x.id === st.prompt ? 'checked' : ''}>
      <b class="grow">${esc(x.title || x.title_auto || x.id)}</b>${badge(x)}</label>`;
    const hits = items.filter(x => !q || [x.id, x.title, x.text, ...(x.tags || [])].join(' ').toLowerCase().includes(q)).slice(0, 60);
    $('#cvpl', box).innerHTML = items.length ? `<label class="cvitem${st.prompt ? '' : ' on'}"><input type="radio" name="cvr" value="" ${st.prompt ? '' : 'checked'}><b class="grow">${t('None')}</b></label>`
        + (hits.map(row).join('') || `<div class="empty">${t('No prompt matches.')}</div>`)
      : `<div class="empty">${t('No brief, script or hook yet - <a href="#/prompts" onclick="closeModal()">Prompts</a>.')}</div>`;
    $$('input[name=cvr]', box).forEach(r => r.onchange = () => {
      st.prompt = r.value; $$('#cvpl .cvitem', box).forEach(x => x.classList.toggle('on', $('input', x).checked));
      if (neTalk(st.prompt) && st.sound === 'auto') st.sound = 'talk';
      prev(); ne.changed(); });
  };
  $('#cvq', box).oninput = debounce(e => drawPrompts(e.target.value.trim().toLowerCase()), 150);
  drawPrompts(''); prev();
}

// 3. References: this PC's analysed videos as picture cards (up to OPT.max_refs, the count by the title) - their style,
// or an exact copy of one (two cards under them)
function neRefs(box, ne) {
  const {st, OPT} = ne, max = OPT.max_refs, vids = ownVideos(ne.S);
  let q = '';
  box.innerHTML = `${vids.length > 8 ? `<input type="search" class="nerq" placeholder="${ta('Search…')}">` : ''}<div class="nerefs"></div><div id="neexact"></div>`;
  const count = $('.nestx', box.closest('.nesec'));
  const exact = () => {               // an exact copy needs one video analysed on this PC (every picked one is)
    const one = st.like.length === 1 && vids.some(v => v.key === st.like[0]);
    if (!one) st.exact = false;
    $('#neexact', box).innerHTML = st.like.length ? `<div class="neexact">
      <button class="necard nexo${st.exact ? '' : ' on'}" data-x="0"><svg class="ic"><use href="#i-palette"/></svg><span><b>${st.like.length > 1 ? t('In their style') : t('In its style')}</b><span>${t('your music, your length')}</span></span></button>
      <button class="necard nexo${st.exact ? ' on' : ''}" data-x="1" ${one ? '' : `disabled title="${ta('(one video analysed on this PC)')}"`}><svg class="ic"><use href="#i-copy"/></svg><span><b>${t('An exact copy')}</b><span>${t('the same song and cuts, with your clips')}</span></span></button></div>` : '';
    $$('.nexo', box).forEach(b => b.onclick = () => { st.exact = b.dataset.x === '1'; exact(); ne.changed(); });
  };
  const draw = () => {
    const keys = new Set(vids.map(v => v.key));
    const list = [...st.like.filter(k => !keys.has(k)).map(k => ({key: k, label: k})), ...vids]       // picked elsewhere (a test video)
      .filter(v => !q || [v.label, v.title, v.key, v.by, v.platform, v.category_label].join(' ').toLowerCase().includes(q));
    // a card = its picture, its length and its name (2026-10-22: "i dont care about the cuts per min stuff, maybe just
    // show duration and thats it"); the length = the end of its format label ("Horizontal · 2:35")
    $('.nerefs', box).innerHTML = vids.length ? list.map(v => { const on = st.like.includes(v.key), full = !on && st.like.length >= max,
      dur = (String(v.format || '').split(' · ')[1] || '').trim();
      return `<button class="necard neref${on ? ' on' : ''}" data-k="${esc(v.key)}" ${full ? 'disabled' : ''} title="${esc(v.line || v.summary || v.label || v.key)}">
        <span class="nerefp">${v.picture ? `<img src="${fileUrl(v.picture)}" loading="lazy" alt="">` : ''}${dur ? `<i>${esc(dur)}</i>` : ''}</span>
        <b>${esc(v.label || v.title || v.key)}</b></button>`; }).join('')
        || `<div class="small muted">${t('No video matches.')}</div>`
      : `<div class="empty">${t('No video analysed on this PC yet - add one in the <a href="#/analyze" onclick="closeModal()">Analyser</a>.')}</div>`;
    count.innerHTML = `<b>${st.like.length}</b> / ${max}`;
    $$('.neref', box).forEach(b => b.onclick = () => { const k = b.dataset.k;
      st.like = st.like.includes(k) ? st.like.filter(x => x !== k) : [...st.like, k].slice(0, max); draw(); exact(); ne.changed(); });
  };
  const qi = $('.nerq', box);
  if (qi) qi.oninput = debounce(() => { q = qi.value.trim().toLowerCase(); draw(); }, 150);
  draw(); exact();
}

// one question's answers as pills: one answer (an Auto pill first; a second click clears) or several (st[key] a list,
// o.max; o.auto false = no Auto pill, nothing picked is Auto); o.help = where the picked answers' help goes (also each
// pill's tooltip); o.top = only that many answers (o.first
// first, then the table's order; a picked one always shows) and a "+N" pill for the rest (2026-10-22: "reduce the
// questions A LOT, to 4-5 options if possible and a '+' sign if u want to answer more")
function neChips(box, items, st, key, o = {}) {
  const many = Array.isArray(st[key]);
  const first = o.first || [], order = [...first.map(id => items.find(x => x.id === id)).filter(Boolean), ...items.filter(x => !first.includes(x.id))];
  let open = !o.top;
  const draw = () => {
    const picked = x => many ? st[key].includes(x.id) : st[key] === x.id;
    const shown = open ? order : order.filter((x, i) => i < o.top || picked(x)), more = order.length - shown.length;
    box.innerHTML = (many || o.auto === false ? '' : `<button class="nech${st[key] ? '' : ' on'}" data-v="">${t('Auto')}</button>`) + shown.map(x => {
      const on = picked(x), full = many && !on && o.max && st[key].length >= o.max;
      return `<button class="nech${on ? ' on' : ''}" data-v="${esc(x.id)}" ${full ? 'disabled' : ''} ${x.help ? `title="${esc(t(x.help))}"` : ''}>${esc(t(x.label))}</button>`; }).join('')
      + (more ? `<button class="nech nemore" title="${ta('Show all')}">+${more}</button>` : '');
    if (o.help) o.help.textContent = items.filter(x => x.help && picked(x)).map(x => many ? `${t(x.label)}: ${t(x.help)}` : t(x.help)).join(' · ');
    const m = $('.nemore', box); if (m) m.onclick = () => { open = true; draw(); };
    $$('button[data-v]', box).forEach(b => b.onclick = () => { const v = b.dataset.v;
      if (many) st[key] = st[key].includes(v) ? st[key].filter(x => x !== v) : [...st[key], v];
      else st[key] = st[key] === v ? '' : v;
      draw(); if (o.onChange) o.onChange(); });
  };
  draw();
}

// 4. Style (2026-10-22: "first make a row for the A ready-made style, then show the questions ... reduce ... to 4-5
// options ... and a '+' ... show the color palette without having to scroll down ... make it more big"): the ready-made
// styles in one row (their rhythm as bars: a shot each, the wider the longer; what each is = its tooltip), the
// questions as one compact card (the question on the left, at most 4 answers + "+N" on the right; where, the type, the
// rhythm, the mood, captions, the feel in their words), then the colour palette for titles, captions and graphics as
// big cards
const NE_Q = {where: ['i-pin', '--cyan'], type: ['i-film', '--violet'], rhythm: ['i-zap', '--amber'], moods: ['i-smile', '--pink'], captions: ['i-cc', '--green']};
const NE_FIRST = {type: ['vlog', 'ad', 'music_video', 'tutorial']};     // the kinds of video the user makes most, first
// the bars stay grey (2026-10-22: "dont put colors in ready-made style cuz that is for general feel of video" - colour
// is the palette's job, below)
const neBars = (r, hue = '#9a9aa6') => {
  const m = (r || {}).median_shot_s; if (!m) return '';
  const lo = r.p10_shot_s || m * 0.7, hi = r.p90_shot_s || m * 1.4, seq = [m, hi, lo, m, lo, hi, m, lo, hi, m, lo, m];
  const out = []; let sum = 0;
  for (let i = 0; sum < 9 && i < 40; i++) { const s = seq[i % seq.length]; sum += s;
    out.push(`<i style="flex-grow:${s.toFixed(2)};background:${hue};opacity:${[1, 0.72, 0.5][i % 3]}"></i>`); }
  return `<span class="nebars" title="${ta('Each bar is a shot - the wider, the longer it lasts')}">${out.join('')}</span>`;
};
function neStyle(box, ne) {
  const {st, OPT} = ne;
  const qs = [['where', t('Where was it filmed?'), OPT.where], ['type', t('Type of video'), OPT.types], ['rhythm', t('Rhythm'), OPT.rhythm],
              ['moods', t('Mood'), OPT.moods, OPT.max_moods], ['captions', t('Captions'), OPT.captions]];
  box.innerHTML = `<div class="nelab">${neIcon('i-sparkle', '--amber')}${t('A ready-made style')}</div>
    <div class="nepre">${OPT.presets.map(p => `<button class="nep${st.presets.includes(p.id) ? ' on' : ''}" data-p="${esc(p.id)}" title="${esc(t(p.help))}"><b>${esc(t(p.label))}</b>${neBars(p.rhythm)}</button>`).join('')}</div>
    <div class="neqs">${qs.map(([k, q, , max]) => `<div class="neqr"><label>${neIcon(...NE_Q[k])}${q}${max ? ` <span>${t('up to {n}', {n: max})}</span>` : ''}</label><div class="nechips" data-q="${k}"></div></div>`).join('')}
      <div class="neqr"><label for="newant">${neIcon('i-pen', '--amber')}${t('The feel in your words')}</label>
        <textarea id="newant" rows="1" placeholder="${ta('e.g. a hook in the first second, 3 s cuts, very fast paced, bold captions word by word, slow zooms while I talk')}">${esc(st.want)}</textarea></div></div>
    <div class="nelab nepalh"><span title="${ta('for titles, captions and graphics - none picked = Claude takes it from your clips and references')}">${neIcon('i-palette', '--pink')}${t('Colour palette')}</span><div class="nepal" id="nemine"></div></div>
    <div id="nepal"></div>`;
  qs.forEach(([k, , items, max]) => neChips($(`[data-q=${k}]`, box), items, st, k, {max, top: 4, auto: false, first: NE_FIRST[k], onChange: ne.changed}));
  $$('.nep', box).forEach(b => b.onclick = () => {
    const id = b.dataset.p; st.presets = st.presets.includes(id) ? st.presets.filter(x => x !== id) : [...st.presets, id];
    b.classList.toggle('on', st.presets.includes(id));
    const tk = OPT.presets.find(p => p.id === id);
    if (tk && tk.talk && st.presets.includes(id)) st.sound = 'talk';
    ne.changed(); });
  $('#newant', box).oninput = e => { st.want = e.target.value; ne.changed(); };
  nePalette($('#nepal', box), ne, $('#nemine', box));
}

// the palette: Auto or a ready-made one as big cards (a strip of its colours each) in box, the colours themselves as big
// swatches to change in mine, beside the palette's title (up to OPT.max_colours, the first = the main accent); none = Auto
function nePalette(box, ne, mine) {
  const {st, OPT} = ne;
  const same = cs => cs.length === st.palette.length && cs.every((c, i) => c.toUpperCase() === st.palette[i]);
  const draw = () => {
    box.innerHTML = `<div class="nepals"><button class="nepl${st.palette.length ? '' : ' on'}" data-clear title="${ta('Auto - Claude picks')}"><span class="nestrip auto">${neIcon('i-sparkle')}</span><span>${t('Auto')}</span></button>
        ${OPT.palettes.map(p => `<button class="nepl${same(p.colours) ? ' on' : ''}" data-p="${esc(p.id)}"><span class="nestrip">${p.colours.map(c => `<i style="background:${esc(c)}"></i>`).join('')}</span><span>${esc(t(p.label))}</span></button>`).join('')}</div>`;
    mine.innerHTML = `${st.palette.map((c, i) => `<span class="nesw"><input type="color" value="${esc(c.toLowerCase())}" data-i="${i}" title="${esc(c)}"><button class="nesx" data-x="${i}" title="${ta('Remove')}">✕</button></span>`).join('')}
        ${st.palette.length < OPT.max_colours ? `<button class="btn sm" data-add>${t('+ Add a colour')}</button>` : ''}`;
    $$('input[type=color]', mine).forEach(c => {
      c.oninput = () => { st.palette[+c.dataset.i] = c.value.toUpperCase(); ne.changed(); };
      c.onchange = draw; });
    $$('[data-x]', mine).forEach(b => b.onclick = () => { st.palette.splice(+b.dataset.x, 1); draw(); ne.changed(); });
    const add = $('[data-add]', mine);
    if (add) add.onclick = () => { st.palette.push(st.palette.length ? '#FFFFFF' : '#FF2D55'); draw(); ne.changed(); };
    const clear = $('[data-clear]', box);
    if (clear) clear.onclick = () => { st.palette = []; draw(); ne.changed(); };
    $$('[data-p]', box).forEach(b => b.onclick = () => { st.palette = OPT.palettes.find(p => p.id === b.dataset.p).colours.map(c => c.toUpperCase()); draw(); ne.changed(); });
  };
  draw();
}

// 5. Sound: the music as four cards (Auto, a song - the folder's or a downloaded one, picked under them -, the clips'
// own sound, talking), how many sound effects (a card each, with a strip of how often one plays) and which kinds
// (motionlab\sfx.py's cue kinds, grouped), notes. Its refresh = the songs again (one added, another video, a talking
// script picked).
function neSound(box, ne) {
  const {st, OPT} = ne;
  const MUSIC = [['auto', 'i-sparkle', t('Auto'), t("the folder's song, if any")], ['music', 'i-music', t('A song'), ''],
                 ['clips', 'i-film', t("The clips' own sound"), t('as filmed')], ['talk', 'i-mic', t('Talking'), t('pauses cut')]];
  const TICKS = {none: 0, few: 3, some: 6, many: 11};
  const amounts = [{id: '', label: t('Auto'), help: t('Claude decides')}, ...OPT.sfx_amount.map(x => ({id: x.id, label: t(x.label), help: t(x.help)}))];
  const strip = id => `<span class="netrk${id ? '' : ' auto'}">${Array.from({length: 12}, (_, i) =>
    `<i${id && Math.floor((i + 1) * TICKS[id] / 12) > Math.floor(i * TICKS[id] / 12) ? ' class="on"' : ''}></i>`).join('')}</span>`;
  box.innerHTML = `<div class="neq"><label>${neIcon('i-music', '--violet')}${t('Music')}</label>
      <div class="nemus">${MUSIC.map(([v, ic, l, s]) => `<button class="necard nemc" data-m="${v}" ${v === 'auto' ? `title="${ta('Automatic - the song in the folder if there is one')}"` : ''}><svg class="ic"><use href="#${ic}"/></svg><b>${l}</b><span data-ms="${v}">${s}</span></button>`).join('')}</div>
      <div class="nesongrow" id="nesongrow" hidden><select id="nesnd"></select>
        <label class="btn sm" id="nesong" title="${ta('Copies a song into this video - the original stays where it is')}"><svg class="i"><use href="#i-upload"/></svg>${t('Add a song…')}<input type="file" hidden accept="audio/*,.mp3,.m4a,.wav,.aac,.flac,.ogg"></label></div>
      <div id="nesongf"></div></div>
    <div class="neq"><label>${neIcon('i-volume', '--amber')}${t('Sound effects')}</label>
      <div class="nesfx">${amounts.map(a => `<button class="necard nesfxc" data-a="${esc(a.id)}"><b>${esc(a.label)}</b><span>${esc(a.help)}</span>${strip(a.id)}</button>`).join('')}</div></div>
    <div class="neq" id="nekinds"><label>${neIcon('i-zap', '--pink')}${t('Which kinds')}</label><div class="nechips" data-q="kinds"></div><div class="nechelp" data-h="kinds"></div></div>
    <div class="nef"><label for="nesnotes">${neIcon('i-pen', '--cyan')}${t('Notes on sound')}</label>
      <textarea id="nesnotes" rows="2" placeholder="${ta('e.g. a big hit when the logo appears, keep my voice clear over the music')}">${esc(st.snotes)}</textarea></div>`;
  const sel = $('#nesnd', box), songIn = $('#nesong input', box);
  const fill = () => {
    const songs = (ne.P() || {}).songs || [];
    sel.innerHTML = `${songs.length ? `<optgroup label="${ta("In this video's folder")}">${songs.map(s => `<option value="music:${esc(s)}">${esc(s)}</option>`).join('')}</optgroup>` : ''}
      ${OPT.songs.length ? `<optgroup label="${ta('Downloaded songs')}">${OPT.songs.map(s => `<option value="music:${esc(s.rel)}">${esc(s.name)}</option>`).join('')}</optgroup>` : ''}`;
    if (st.sound.startsWith('music:') && ![...sel.options].some(o => o.value === st.sound)) st.sound = sel.options.length ? sel.options[0].value : 'auto';
    const mode = st.sound.startsWith('music:') ? 'music' : st.sound;
    if (mode === 'music') sel.value = st.sound;
    $$('.nemc', box).forEach(b => b.classList.toggle('on', b.dataset.m === mode));
    $('[data-ms=music]', box).textContent = mode === 'music' ? st.sound.slice(6).split('/').pop() : sel.options.length ? t('Pick a song') : t('Add a song…');
    $('#nesongrow', box).hidden = mode !== 'music';
    $$('.nesfxc', box).forEach(b => b.classList.toggle('on', b.dataset.a === st.sfx));
    $('#nekinds', box).hidden = st.sfx === 'none';
  };
  $$('.nemc', box).forEach(b => b.onclick = () => { const m = b.dataset.m;
    if (m !== 'music') st.sound = m;
    else if (!st.sound.startsWith('music:')) { if (!sel.options.length) { songIn.click(); return; } st.sound = sel.options[0].value; }
    ne.changed(); });
  sel.onchange = () => { st.sound = sel.value; ne.changed(); };
  songIn.onchange = async () => { const f = [...songIn.files]; songIn.value = '';
    await ne.addFiles(f, $('#nesongf', box));
    const songs = (ne.P() || {}).songs || [], s = f[0] && (songs.includes(f[0].name) ? f[0].name : songs[songs.length - 1]);
    if (s) { st.sound = 'music:' + s; ne.changed(); } };
  $$('.nesfxc', box).forEach(b => b.onclick = () => { st.sfx = b.dataset.a; ne.changed(); });
  neChips($('[data-q=kinds]', box), OPT.sfx_kinds, st, 'kinds', {help: $('[data-h=kinds]', box), onChange: ne.changed});
  $('#nesnotes', box).oninput = e => { st.snotes = e.target.value; ne.changed(); };
  return fill;
}

// 6. Final: the length, the format (a card each, its shape drawn), then the summary - every step in one table, a click
// on one goes back to it - and Claude's time as one chip. Its refresh also sets the footer's two buttons (what they do
// = their tooltip; only a missing clip is said here).
function neFinal(box, ne) {
  const {st, OPT} = ne;
  const lens = [['', t('Auto')], ['15', '15 s'], ['30', '30 s'], ['45', '45 s'], ['60', '1 min'], ['90', '1:30 min']];
  const fmts = [['', t('Auto'), t("your clips' own shape")], ['vertical', t('Vertical 9:16'), 'TikTok · Reels · Shorts'],
                ['horizontal', t('Horizontal 16:9'), 'YouTube'], ['square', t('Square 1:1'), t('a feed post')]];
  box.innerHTML = `<div class="neq"><label>${neIcon('i-clock', '--cyan')}${t('Length')}</label><div class="nechips" id="nelen">${lens.map(([v, l]) => `<button class="nech" data-v="${v}">${l}</button>`).join('')}
      <input type="number" id="nelenx" min="3" max="900" step="1" placeholder="${ta('or seconds')}"></div></div>
    <div class="neq"><label>${neIcon('i-videos', '--violet')}${t('Format')}</label>
      <div class="nefmts">${fmts.map(([v, l, s]) => `<button class="necard nefmt" data-f="${v}"><i class="neshape ${v || 'auto'}"></i><span><b>${l}</b><span>${s}</span></span></button>`).join('')}</div></div>
    <div class="neq"><label>${neIcon('i-clipboard', '--green')}${t('Summary')}</label><div class="nesum" id="nesumc"></div></div>
    <div class="nefinb"><span class="neest" id="neest"></span><span class="small amber" id="neneed"></span></div>`;
  const seg = $('#nelen', box), other = $('#nelenx', box);
  const paint = () => {
    $$('[data-v]', seg).forEach(b => b.classList.toggle('on', b.dataset.v === st.length));
    if (lens.some(([v]) => v === st.length)) other.value = '';
    $$('[data-f]', box).forEach(b => b.classList.toggle('on', b.dataset.f === st.format));
  };
  $$('[data-v]', seg).forEach(b => b.onclick = () => { st.length = b.dataset.v; paint(); ne.changed(); });
  other.oninput = () => { const v = Math.round(+other.value); st.length = v >= 3 && v <= 900 ? String(v) : ''; paint(); ne.changed(); };
  $$('[data-f]', box).forEach(b => b.onclick = () => { st.format = b.dataset.f; paint(); ne.changed(); });
  paint();
  return () => {
    const R = neRows(ne), P = ne.P(), clips = !!(P && P.clips);
    $('#nesumc', box).innerHTML = NE_STEPS.map(([id, name, , ic, col]) => { const set = (R[id] || []).filter(r => !r.auto);
      return `<button class="nesumr${id === 'clips' && !clips ? ' need' : ''}" data-go="${id}">${neIcon(ic, col)}<span>${name}</span><span class="nesv">${set.length ? set.map(r => `<span title="${esc(r.k)}">${r.v}</span>`).join(' · ')
        : `<em>${id === 'clips' ? t('Pick your clips first') : t('Auto')}</em>`}</span></button>`; }).join('');
    $$('#nesumc [data-go]', box).forEach(b => b.onclick = () => ne.go(b.dataset.go));
    const m = st.length ? Math.round(+st.length * OPT.min_per_s) : 0, est = $('#neest', box);
    est.innerHTML = `<svg class="i"><use href="#i-clock"/></svg><span>${m ? t('About <b>{time}</b> of Claude', {time: m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${pad(m % 60)} min`})
      : t('Pick a length to see how long Claude may take')}</span>`;
    est.title = t('We count about {n} min of Claude per second of video.', {n: numStr(OPT.min_per_s)});
    const exactOk = !st.exact || st.like.length === 1;
    const style = st.like.length || st.presets.length || st.want.trim() || st.rhythm || neTalk(st.prompt);
    const go = $('#cvgo', ne.el), dr = $('#cvdraft', ne.el);
    go.disabled = !(clips && exactOk); dr.disabled = !(clips && !st.exact && style);
    go.title = clips ? t('Claude plans it with you, step by step') : t('First your clips (1)');
    dr.title = st.exact ? t('An exact copy is made by Claude') : style || !clips
      ? t('A first version in a few minutes, by rules - no Claude. Watch it, then let Claude make it better.')
      : t('The quick draft needs a style: a reference (3), a rhythm or a ready-made style (4), or your words');
    $('#neneed', box).textContent = clips ? '' : t('First your clips (1)');
  };
}

// what was picked, per step: [{k: the question, v: the answer as html, s: a short plain answer for the steps on the left,
// auto}] - the steps and the summary both read it, so they never disagree
function neRows(ne) {
  const {st, OPT, PRM} = ne, P = ne.P();
  const lab = (list, id) => { const x = (list || []).find(o => o.id === id); return x ? t(x.label) : id; };
  const plain = v => String(v).replace(/<[^>]+>/g, '').replace(/&(amp|lt|gt|quot|#39);/g, (m, e) => ({amp: '&', lt: '<', gt: '>', quot: '"', '#39': "'"}[e]));
  const row = (k, v, s = '', auto = false) => ({k, v, s: s || plain(v), auto});     // s goes in as text, v as html
  const pr = st.prompt && PRM.items.find(x => x.id === st.prompt);
  const names = st.like.map(k => { const v = ownVideos(ne.S).find(x => x.key === k); return v ? v.label || v.title || k : k; });
  const snd = st.sound.startsWith('music:') ? st.sound.slice(6).split('/').pop() : {auto: t('Automatic'), clips: t("The clips' own sound"), talk: t('Talking')}[st.sound];
  const lines = st.onscreen.split('\n').filter(x => x.trim());
  return {
    clips: P ? [row(t('Video'), esc(pname(P)), pname(P)), row(t('Clips'), P.clips ? plural(P.clips, 'clip') : `<span class="amber">${t('no clips yet')}</span>`)] : [],
    text: [st.about.trim() && row(t('What it is about'), esc(st.about.trim().slice(0, 140)) + (st.about.trim().length > 140 ? '…' : ''), t('notes')),
      lines.length && row(t('Text on screen'), lines.map(esc).join(' · '), plural(lines.length, 'line')),
      pr && row(t('Script or brief'), esc(pr.title || pr.title_auto || pr.id), t('a script'))].filter(Boolean),
    refs: [st.like.length && row(st.exact ? t('An exact copy of') : t('In the style of'), names.map(esc).join(', '), plural(st.like.length, 'video'))].filter(Boolean),
    style: [st.where && row(t('Filmed'), lab(OPT.where, st.where)), st.type && row(t('Type of video'), lab(OPT.types, st.type)),
      st.rhythm && row(t('Rhythm'), lab(OPT.rhythm, st.rhythm)), st.moods.length && row(t('Mood'), st.moods.map(m => lab(OPT.moods, m)).join(', ')),
      st.captions && row(t('Captions'), lab(OPT.captions, st.captions)),
      st.presets.length && row(t('Ready-made'), st.presets.map(p => lab(OPT.presets, p)).join(', ')),
      st.want.trim() && row(t('In your words'), esc(st.want.trim().slice(0, 140)), t('your words')),
      st.palette.length && row(t('Palette'), st.palette.map(c => `<i class="nedot" style="background:${esc(c)}"></i>`).join(''), plural(st.palette.length, 'colour'))].filter(Boolean),
    sound: [row(t('Music'), esc(snd), '', st.sound === 'auto'), row(t('Sound effects'), st.sfx ? lab(OPT.sfx_amount, st.sfx) : t('Auto'), '', !st.sfx),
      st.kinds.length && st.sfx !== 'none' && row(t('Kinds'), st.kinds.map(k => lab(OPT.sfx_kinds, k)).join(', ')),
      st.snotes.trim() && row(t('Notes'), esc(st.snotes.trim().slice(0, 140)), t('notes'))].filter(Boolean),
    final: [row(t('Length'), st.length ? `${st.length} s` : t('Auto'), '', !st.length),
      row(t('Format'), st.format ? {vertical: t('Vertical 9:16'), horizontal: t('Horizontal 16:9'), square: t('Square 1:1')}[st.format] : t('Auto'), '', !st.format),
      st.resolve && row('DaVinci Resolve', t('yes, a project too'))].filter(Boolean)};
}
// the steps on the left: before the one on screen = a tick and the short answer (Auto when nothing was picked), the one
// on screen = a gold ring and Now, the rest their number (dashed = optional) and their answer once something is picked;
// red = no clips; .rchn = the line down to the next step is gold (that step is reached)
function neNav(el, ne) {
  const R = neRows(ne), clips = !!(ne.P() || {}).clips;
  $$('.nenav button', el).forEach((b, i) => {
    const id = b.dataset.go, s = (R[id] || []).filter(r => !r.auto).map(r => r.s), on = i === ne.cur, need = id === 'clips' && !clips && !on, done = i < ne.cur && !need;
    b.classList.toggle('on', on); b.classList.toggle('done', done); b.classList.toggle('need', need); b.classList.toggle('rchn', i < ne.cur);
    $('b', b).textContent = done ? '✓' : i + 1;
    $('small', b).textContent = on ? t('Now|step') : need ? t('pick your clips') : s.length ? s.slice(0, 3).join(' · ') : done ? t('Auto') : '';
  });
}

const neBody = st => ({like: st.like, exact: st.exact, prompt: st.prompt, about: st.about, on_screen: st.onscreen, presets: st.presets, want: st.want,
  style: {where: st.where, type: st.type, rhythm: st.rhythm, moods: st.moods, captions: st.captions, palette: st.palette},
  sfx: {amount: st.sfx, kinds: st.kinds, notes: st.snotes}, length_s: st.length || null, format: st.format || null,
  music: st.sound.startsWith('music:') ? st.sound.slice(6) : '', sound: st.sound.startsWith('music:') ? 'music' : st.sound, resolve: st.resolve,
  photos: st.photos || {}});

// ---- Edit > a video (the user, 2026-10-15: "when I first click I want to see a thumbnail or the last render so I know
// in which video I am, instead of How did it turn out? or random information shot in my face; then the two buttons -
// not feeling right? review it and improve it (a new Review section with How did it turn out?) or start over; happy
// with it = the Publish part under the video, no Publish tab; Your footage its own tab"). Tabs: Overview (the newest
// render + an index of the page, the two buttons, Ready to post) | Review (a player + How did it turn out?) | Versions
// (edit versions + renders) | Footage | Graphics | Timing check and Resolve & library only when the video has them.
// The 0.4.3 addresses #/project/<p>/renders and /publish still work.
async function pageProject(main, name, tab = 'overview') {
  const P = await api('/api/project/' + encodeURIComponent(name));
  if (tab === 'renders') tab = 'versions';
  const toPub = tab === 'publish';
  if (toPub) tab = 'overview';
  const nClips = P.sources.length, foot = P.sources.reduce((a, s) => a + (s.size || 0), 0);
  const tabs = [['overview', t('Overview')], ...(P.renders.length || (P.outcome || {}).aspects || tab === 'review' ? [['review', t('Review')]] : []), ['versions', `${t('Versions')}${P.plans.length ? ` (${P.plans.length})` : ''}`],
                ...(nClips ? [['footage', `${t('Footage')} (${nClips})`]] : []),
                ['graphics', `${t('Graphics')}${P.overlays && P.overlays.length ? ` (${P.overlays.length})` : ''}`],
                ...(P.verifies.length || tab === 'timing' ? [['timing', t('Timing check|tab')]] : []),
                ...(P.resolve.length || tab === 'resolve' ? [['resolve', t('Resolve & library')]] : [])];
  const R0 = newestFirst(P)[0];
  // 0.4.3.5 (the user: "do not duplicate info like that"): a video made from zero lives in the Generator - its page
  // too - until the user moves it to the Editor
  const gen = inGenerator(P), home = gen ? ['#/generate', t('Generator')] : ['#/edit', t('Editor')];
  if (gen) { $$('#side a[data-nav]').forEach(a => a.classList.toggle('on', a.dataset.nav === 'generate')); document.body.dataset.page = 'generate'; }
  const facts = [nClips ? `${plural(nClips, 'clip')} · ${bytes(foot)}` : P.generated ? genChip() : t('no clips yet'),
                 ...(R0 ? [t('newest render {when}', {when: esc(whenWords(R0.mtime))})] : [])];
  main.innerHTML = `<div class="head"><div><div class="crumb"><a href="${home[0]}">${home[1]}</a> /</div><h1>${esc(pname(P))}</h1>
    <div class="sub">${facts.join(' · ')}<button class="btn sm ghost hfold" data-open="${esc('projects/' + P.name)}" title="${ta("the video's folder: your clips and everything made from them")}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button>
      ${P.generated && !gen ? `<button class="btn sm ghost" id="pjback" title="${ta('Show it in the Generator again (not in the Editor)')}">${t('Back to the Generator')}</button>` : ''}</div></div>
    <div class="row">${gen ? `<button class="btn pri" id="pjmove" title="${ta('Edit it like your own clips - cuts, captions, music. It then shows in the Editor instead of here.')}"><svg class="i"><use href="#i-edit"/></svg>${t('Move to the Editor')}</button>`
        : `<button class="btn pri" id="pjnew"><svg class="i"><use href="#i-edit"/></svg>${t('New edit…')}</button>`}
      <button class="btn" id="pjren"><svg class="i"><use href="#i-pen"/></svg>${t('Rename')}</button>${delBtn('project', P.name, home[0], ' ' + t('Delete'))}</div></div>
    <div id="pjprog"></div>
    <div class="tabs">${tabs.map(([k, l]) => `<a href="#/project/${encodeURIComponent(name)}/${k}" class="${k === tab ? 'on' : ''}">${l}</a>`).join('')}</div>
    <div id="tab"></div>`;
  const move = async editor => {
    try { await api(`/api/project/${encodeURIComponent(P.name)}/move`, {editor}); toast(editor ? t('Moved to the Editor') : t('Back in the Generator'), 'ok'); route(); }
    catch (e) { toast(e.message, 'err'); }
  };
  if (gen) $('#pjmove').onclick = () => move(true); else $('#pjnew').onclick = () => newEdit({project: P.name});
  const bk = $('#pjback'); if (bk) bk.onclick = () => move(false);
  $('#pjren').onclick = () => renameModal(P);
  const stopProg = progressPanel($('#pjprog'), () => { if (location.hash.startsWith('#/project/' + encodeURIComponent(name))) route(); },
                                 ['draft', ...THUMB_JOBS], j => (j.args || {}).project === P.name);
  onCleanup(stopProg);
  const el = $('#tab');
  if (tab === 'review') return projReview(el, P);
  if (tab === 'versions') return projVersions(el, P);
  if (tab === 'footage') return projFootage(el, P);
  if (tab === 'graphics') return projGraphics(el, P);
  if (tab === 'timing') return projTiming(el, P);
  if (tab === 'resolve') return projResolve(el, P);
  return projOverview(el, P, toPub);
}

// renders: the newest first; a render's rate / length = its plan's (the server adds ffprobe's for one without a plan)
const renderLabel = r => /^v\d+$/.test(r.version) ? `${esc(r.version)}${r.kind === 'resolve' ? ' · Resolve' : ''}` : esc(r.version.replace(/_/g, ' '));
const newestFirst = P => P.renders.slice().sort((a, b) => (b.mtime || 0) - (a.mtime || 0));
const planOfRender = (P, r) => P.plans.find(p => p.name && r.name.replace(/\.mp4$/i, '') === p.name)      // zz_v2.mp4 <- plan_v2
  || P.plans.find(p => p.version === r.version) || {};
const renderFps = (P, r) => r.fps || planOfRender(P, r).fps || (P.plans[0] || {}).fps || 25;
const renderFrames = (P, r) => r.frames || planOfRender(P, r).frames || null;
const posterUrl = (P, r) => { const fps = renderFps(P, r), n = renderFrames(P, r);       // a third in: frame 0 is often black
  return `/api/thumb?video=${encodeURIComponent(r.rel)}&f=${n ? Math.floor(n * 0.3) : Math.round(fps)}&fps=${fps}`; };
const stopPlayer = pl => { if (pl) { pl.gone = true; pl.v.pause(); pl.v.removeAttribute('src'); pl.v.load(); } };
// one render at a time; more than one = a row of buttons to switch (v2 · v1 · v1 · Resolve)
function renderPicker(box, P, onPick) {
  const R = newestFirst(P);
  box.innerHTML = R.length > 1 ? `<div class="seg rpick">${R.map((r, i) => `<button data-i="${i}" title="${ta('rendered {when}', {when: r.modified})}">${renderLabel(r)}</button>`).join('')}</div>` : '';
  const seg = $('.rpick', box);
  const pick = i => { if (seg) $$('button', seg).forEach((b, j) => b.classList.toggle('on', j === i)); onPick(R[i]); };
  if (seg) $$('button', seg).forEach(b => b.onclick = () => pick(+b.dataset.i));
  if (R.length) pick(0);
  return R;
}
// a made_from video by name (data.project refs, 2026-10-18): this PC's = a link to its analysis, a friend's = the chip
const madeRef = r => r.author ? `${esc(r.label)} ${sharedChip(r.author, r.shared)}`
  : r.analysis ? `<a href="#/ref/${encodeURIComponent(r.analysis)}">${esc(r.label)}</a>` : esc(r.label);
// the stored words of "words" (presets' labels joined by ", ": a piece the catalogue has is translated, the user's own
// words stay as typed) and "generated" (data.py's two fixed texts) shown in the page's language
const madeFromWords = P => (P.made_from || []).map(x => { const link = `<a href="#/prompts/${esc(x.id)}">${esc(x.title || x.id)}</a>`;
  return x.kind === 'reference'
  ? t('an exact copy of {video}', {video: x.refs ? x.refs.map(madeRef).join(', ') : `<a href="#/ref/${encodeURIComponent(x.id)}">${esc(x.id)}</a>`})
  : x.kind === 'style' ? t('the style of {videos}', {videos: x.refs ? x.refs.map(madeRef).join(', ') : esc(x.id)})
  : x.kind === 'words' ? t('your words ({words})', {words: esc(String(x.id ?? '').split(', ').map(w => typeof I18N[w] === 'string' ? t(w) : w).join(', '))})
  : x.kind === 'generated' ? t('made from zero ({what})', {what: esc(x.id === 'a motion-graphics video' ? t('a motion-graphics video')
    : /^AI video tools(: |$)/.test(x.id || '') ? t('AI video tools') + x.id.slice(14) : x.id)})
  : x.prompt_kind === 'script' ? t('the script {link}', {link}) : x.prompt_kind === 'hook' ? t('the hook {link}', {link}) : t('the prompt {link}', {link}); });
const setNext = async (P, v) => { P.outcome = await api(`/api/project/${encodeURIComponent(P.name)}/outcome`, {next: v}); };
// *Start over* = a different feel, never a v2 of a feel the user did not want (outcome.json "next", 0.4.2)
async function startOver(P) {
  try { if ((P.outcome || {}).next !== 'start_over') await setNext(P, 'start_over'); }
  catch (e) { toast(e.message, 'err'); return; }
  newEdit({project: P.name});
}
// *Finish it with Claude* (2026-10-24, the user: "when i go to quick draft now, and the draft is done like what should
// i use next? ... it worked good and actually made some good cuts and transitions but then what? how do i tell him to
// go next step which is some motion graphics and stuff?"): a quick draft = the cuts; this = the layers on top of them.
// The tiles start from New edit's answers (project() "asked") or this version's last finish; saved as outcome.json
// "next": "finish" + "finish" {add, words, from} -> /recreate-video finish <p> (the words never pass through cmd)
const FINISH_ADD = [['graphics', 'i-motion', t('Motion graphics'), t('titles, text and graphics from your Motion Graphics templates')],
  ['captions', 'i-cc', t('Captions'), t('what is said, on screen')],
  ['sfx', 'i-volume', t('Sound effects'), t('whooshes, pops and hits on the moves')],
  ['colour', 'i-palette', t('Colour'), t('one colour look over the whole video')]];
function finishModal(P, from, done) {
  const a = P.asked || {}, last = (P.outcome || {}).finish, again = last && last.from === from;
  const on = new Set(again ? last.add : ['graphics', ...(a.captions === 'none' || !(a.captions || a.talk) ? [] : ['captions']), ...(a.sfx === 'none' ? [] : ['sfx'])]);
  const keep = [t('Pacing & cuts'), t('Effects & transitions'), t('Sound & music')];
  modal(`<h2>${t('Finish it with Claude')}</h2>
    <div class="finrow"><b class="finlab">${t('Stays')}</b><div class="finkeep">${keep.map(k => `<span>✓ ${esc(k)}</span>`).join('')}</div></div>
    <div class="finrow"><b class="finlab">${t('Claude adds')}</b><div class="finadd">${FINISH_ADD.map(([k, ic, l, h]) =>
      `<button class="fintile${on.has(k) ? ' on' : ''}" data-k="${k}" title="${esc(h)}">${neIcon(ic)}<b>${esc(l)}</b></button>`).join('')}</div></div>
    <textarea id="finwords" rows="2" placeholder="${ta('In your words (optional) - e.g. a big title at the hook, the key point in a pill beside my head')}">${esc(again ? last.words : '')}</textarea>
    <div class="row finfoot"><button class="btn pri big" id="fingo" title="${ta('{version} stays as it is - Claude makes the next version on top of it', {version: from || t('the draft')})}"><svg class="i"><use href="#i-claude"/></svg>${t('Finish it with Claude')}</button></div>`, el => {
    const go = $('#fingo', el), words = $('#finwords', el);
    const upd = () => { go.disabled = !on.size && !words.value.trim(); };
    $$('.fintile', el).forEach(b => b.onclick = () => { const k = b.dataset.k; if (on.has(k)) on.delete(k); else on.add(k); b.classList.toggle('on', on.has(k)); upd(); });
    words.oninput = upd;
    go.onclick = async () => {
      go.disabled = true;
      try { P.outcome = await api(`/api/project/${encodeURIComponent(P.name)}/outcome`, {next: 'finish',
          finish: {add: FINISH_ADD.map(x => x[0]).filter(k => on.has(k)), words: words.value.trim(), from}});
        openClaude(`/recreate-video finish ${P.name}`, 'recreate', P.name); closeModal(); if (done) done(); }
      catch (e) { toast(e.message, 'err'); upd(); }
    };
    upd();
  }, 'finmodal');
}

function projOverview(el, P, toPub = false) {
  const R = newestFirst(P), nx = (P.outcome || {}).next || null, enc = encodeURIComponent(P.name);
  const draft = R.length > 0 && planOfRender(P, R[0]).made_by === 'draft_edit.py';     // the newest = a quick draft
  if (!P.plans.length && !R.length) {
    const scr = (P.made_from || []).filter(x => x.kind === 'prompt' && /^(script|hook)-/.test(x.id)).pop();
    el.innerHTML = P.generated
      ? emptyHero('generate', t('Not made yet'), t('Claude makes this video from zero - its first render plays here when it is ready.'), `<a class="btn big" href="#/generate">${t('Generator')}</a>`)
      : scr ? emptyHero('edit', t('Filmed - now edit it'), t('From the script “{title}”. {clips} The pauses cut, captions, the text and B-roll where the script says.', {title: esc(scr.title || scr.id), clips: nClipsWords(P)}),
          `<button class="btn pri big" id="ovnew"><svg class="i"><use href="#i-edit"/></svg>${t('Edit it…')}</button>`)
      : emptyHero('edit', t('No edit yet'), t('{clips} Cut them like videos you analysed, the way you say, or from a script.', {clips: nClipsWords(P)}),
          `<button class="btn pri big" id="ovnew"><svg class="i"><use href="#i-edit"/></svg>${t('New edit…')}</button>`);
    const b = $('#ovnew', el); if (b) b.onclick = () => scr ? newEdit({project: P.name, from: 'prompt', pick: scr.id}) : newEdit({project: P.name});
    return;
  }
  const mf = madeFromWords(P);
  // under the player, one line: which render, its length, format and when (the frames + timecode on hover)
  const meta = r => { const pl = planOfRender(P, r), fps = renderFps(P, r), n = renderFrames(P, r);
    return `<span title="${n ? `f0–${n - 1} (${tc(0, fps)} – ${tc(n - 1, fps)})` : ''}">${[renderLabel(r) + (pl.made_by === 'draft_edit.py' ? ' · ' + t('quick draft') : pl.version ? ' · ' + t('by Claude') : ''),
      n ? `${lenWords(n, fps)} · ${fps} fps` : `${fps} fps`, r.width ? `${shapeWord(r.width, r.height)} ${r.width}×${r.height}` : '',
      t('rendered {when}', {when: esc(whenWords(r.mtime))})].filter(Boolean).join(' · ')}</span>`; };
  el.innerHTML = `<div class="liveline" data-live="${esc(P.name)}" data-name="${esc(pname(P))}" hidden></div>
    <div class="pvhero"><div class="pvmain"><div id="pvpl"></div>
      <div class="pvmeta"><div id="pvpick"></div><span class="small" id="pvkv"></span><span class="grow"></span>${R.length ? `<button class="btn sm ghost" id="pvopen">${t('Open in player')}</button>` : ''}</div>
      ${mf.length ? `<div class="small muted pvmade">${t('Made from {list}', {list: mf.join(', ')})}</div>` : ''}</div>
      <nav class="panel pvindex" id="pvidx"></nav></div>
    ${R.length ? `<div class="pvnext">
        ${draft ? `<button class="onx fin${nx === 'finish' ? ' on' : ''}" data-go="finish"><span class="oic"><svg class="i"><use href="#i-sparkle"/></svg></span>
          <span class="otx"><b>${t('Happy with the cuts? Finish it with Claude')}</b><span>${t('the cuts and transitions stay - Claude adds motion graphics, captions, sound effects')}</span></span><span class="oar">→</span></button>` : ''}
        <button class="onx fix${nx === 'fix' ? ' on' : ''}" data-go="fix"><span class="oic"><svg class="i"><use href="#i-scriptok"/></svg></span>
          <span class="otx"><b>${t('Something not right? Review it and improve it')}</b><span>${t('rate each part beside the video - Claude makes the next version from your ratings')}</span></span><span class="oar">→</span></button>
        <button class="onx over${nx === 'start_over' ? ' on' : ''}" data-go="start_over"><span class="oic"><svg class="i"><use href="#i-restart"/></svg></span>
          <span class="otx"><b>${t('Start over')}</b><span>${t('a different feel - a new edit with these clips, not a new version of this one')}</span></span><span class="oar">→</span></button></div>
      ${reviewSummary(P)}${nx ? `<div class="small muted" style="margin-top:4px">${t('You chose: {what} · <a href="#" id="pvclr">undo</a>', {what: nx === 'fix' ? t('improve this version') : nx === 'finish' ? t('finish it with Claude') : t('start over with a different feel')})}</div>` : ''}` : ''}
    <div id="pubsec"></div>
    <div id="tooksec"></div>`;
  liveLine(LIVE);
  tookPanel($('#tooksec', el), 'project', P.name, P);
  const pub = R.length || P.publish;
  drawIndex($('#pvidx', el), P, pub, null);
  if (!R.length) {                                   // planned, not rendered yet (a quick draft or Claude is on it)
    const pl = P.plans[P.plans.length - 1];
    $('#pvpl', el).innerHTML = `<div class="pvnone">${P.picture ? `<img src="${picUrl(P.picture)}" alt="">` : ''}<div><b>${t('Not rendered yet')}</b>
      <div class="small muted">${t('A quick draft or Claude renders it - it plays here when it is ready.')}</div></div></div>`;
    $('#pvkv', el).innerHTML = `${esc(pl.version)}${pl.made_by === 'draft_edit.py' ? ' · ' + t('quick draft') : ' · ' + t('by Claude')}${pl.frames ? ` · ${lenWords(pl.frames, pl.fps)} · ${pl.fps} fps` : ''}`;
  }
  let pl = null, cur = null;
  renderPicker($('#pvpick', el), P, r => {
    stopPlayer(pl); cur = r;
    pl = new Player($('#pvpl', el), r.rel, renderFps(P, r), renderFrames(P, r));
    pl.v.poster = posterUrl(P, r);
    $('#pvkv', el).innerHTML = meta(r);
  });
  const op = $('#pvopen', el); if (op) op.onclick = () => openPath(cur.rel);
  $$('[data-go]', el).forEach(b => b.onclick = async () => {
    if (b.dataset.go === 'start_over') return startOver(P);
    if (b.dataset.go === 'finish') return finishModal(P, R[0].version || '', () => projOverview(el, P));
    try { if (nx !== 'fix') await setNext(P, 'fix'); } catch (e) { toast(e.message, 'err'); return; }
    location.hash = `#/project/${enc}/review`;
  });
  const clr = $('#pvclr', el);
  if (clr) clr.onclick = async e => { e.preventDefault(); try { await setNext(P, null); toast(t('Removed'), 'ok'); projOverview(el, P); } catch (err) { toast(err.message, 'err'); } };
  if (pub) projPublish($('#pubsec', el), P).then(() => {
    if (toPub) $('#pubsec', el).scrollIntoView({block: 'start'});
  });
}
// the side panel: where everything about this video is (the user, 2026-10-15: "the sidebar graphics_preview,
// caption_preview has no purpose - an index-like set of buttons pointing to the other sections: thumbnail, title...").
// Ready to post's parts scroll on this page, the others open their tab; each says how far it is (I = the publish info,
// null while it loads)
function drawIndex(box, P, pub, I) {
  const enc = encodeURIComponent(P.name), pk = (I || {}).package || {}, th = pk.thumbnails || [];
  const ctr = Object.keys(((P.outcome || {}).packaging || {}).ctr || {}).length, R0 = newestFirst(P)[0];
  const st = (ok, yes, no) => I ? `<span class="pvs ${ok ? 'ok' : 'dim'}">${ok ? '✓ ' + yes : no}</span>` : '';
  const n = (v, w) => `<span class="pvs dim">${v ? plural(v, w) : t('none|count')}</span>`;
  const item = (to, ic, label, s, tab = '') => `<a class="pvi" href="${tab ? `#/project/${enc}/${tab}` : '#'}"${tab ? '' : ` data-to="${to}"`}>
    <svg class="i"><use href="#${ic}"/></svg><span class="grow">${label}</span>${s}</a>`;
  const A = (P.outcome || {}).aspects || {}, ov = (A.overall || {}).rating, TK = TOOK[P.name];
  Object.assign(box, {_P: P, _pub: pub, _I: I});       // What it took redraws it when its numbers arrive
  box.innerHTML = `${pub ? `<div class="pvih">${t('Ready to post')}</div>
    ${item('pb-title', 'i-prompts', t('Title'), st(pk.title, t('chosen|title'), t('not yet')))}
    ${item('pb-thumbs', 'i-thumb', t('Thumbnails'), st(th.length, th.map(x => esc(x.id)).join(' · '), t('not yet')))}
    ${item('pb-desc', 'i-news', t('Description & chapters'), st((pk.description || {}).text, t('saved|description'), t('not yet')))}
    ${item('pb-after', 'i-jobs', t('After posting'), st(ctr, t('clicks saved'), t('once it is up')))}` : ''}
    ${item('pb-took', 'i-clock', t('What it took'), TK ? `<span class="pvs dim">${TK.rows.length ? t('{time} of Claude', {time: minWords(TK.total.claude_minutes)}) : t('nothing yet')}</span>` : '')}
    <div class="pvih">${t('This video')}</div>
    ${R0 ? item('', 'i-scriptok', t('Review'), P.reviewed ? `<span class="pvs">${rateChip(ov) || `<span class="ok">${t('✓ reviewed')}</span>`}</span>` : `<span class="pvs"><span class="prate todo">${t('not reviewed yet')}</span></span>`, 'review') : ''}
    ${item('', 'i-library', t('Graphics'), n((P.overlays || []).length, 'graphic'), 'graphics')}
    ${item('', 'i-videos', t('Versions'), n(P.plans.length || P.renders.length, P.plans.length ? 'version' : 'render'), 'versions')}
    ${P.sources.length ? item('', 'i-edit', t('Footage'), n(P.sources.length, 'clip'), 'footage') : ''}
    ${P.verifies.length ? item('', 'i-analyze', t('Timing check'), '', 'timing') : ''}
    ${P.resolve.length ? item('', 'i-update', t('Resolve & library'), '', 'resolve') : ''}`;
  $$('[data-to]', box).forEach(a => a.onclick = e => {
    e.preventDefault();
    const to = document.getElementById(a.dataset.to) || $('#pubsec');
    if (to) { if (to.tagName === 'DETAILS') to.open = true; to.scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'}); }
  });
}
const reIndex = (P, I) => { const ix = $('#pvidx'); if (ix) drawIndex(ix, P, true, I); };   // after Ready to post (re)draws

// ---- What it took (0.4.4, the user: "a new section below 'ready to post' ... called 'What it took' ... the entire
// process kinda like a timeline from up to top ... (Prepare Transcript) X minutes it took claude ... X tokens with this
// model (Opus 5.5 xhigh e.g) ... TOTAL SPENT"): Claude's minutes and tokens per step, read from Claude Code's own logs
// on this PC (motionlab\usage.py - read-only, nothing is sent to Claude Code) + the app's jobs since 0.4.4.
// GET /api/took/<project|analysis|prompt>/<name>; the Overview of a video and of an analysis.
const TOOK = {};                                     // video folder -> its numbers (the index line)
// a time as the clock shows it (the user, 2026-10-15: "what is 1.4 min? 1:40? or 1:25?"): 45 s · 1:54 min · 1 h 05 min.
// Time only - no tokens on the page (the user, the same night: "scrap that idea ... just say the time it took")
const minWords = m => { const s = Math.max(1, Math.round((m || 0) * 60));
  return s < 60 ? `${s} s` : s < 3600 ? `${Math.floor(s / 60)}:${pad(s % 60)} min` : `${Math.floor(s / 3600)} h ${pad(Math.round(s % 3600 / 60))} min`; };
async function tookPanel(box, kind, name, P) {
  if (!box) return;
  let D;
  try { D = await api(`/api/took/${kind}/${encodeURIComponent(name)}`); } catch (e) { box.innerHTML = ''; return; }
  if (!box.isConnected) return;
  if (kind === 'project') { TOOK[name] = D; const ix = $('#pvidx'); if (ix && ix._P) drawIndex(ix, ix._P, ix._pub, ix._I); }
  const T = D.total, rows = D.rows;
  const dt = ts => { const d = new Date(ts * 1000); return `${d.getDate()} ${MONTHS[d.getMonth()]} ${pad(d.getHours())}:${pad(d.getMinutes())}`; };
  // a step's name (data.py TASK_STEP / JOB_STEP: their words by key), " (in a batch)" apart so both translate
  const stepW = s => { s = String(s ?? ''); const m = /^(.+) \(in a batch\)$/.exec(s); return m ? t('{step} (in a batch)', {step: t(m[1])}) : t(s); };
  const R0 = P ? newestFirst(P)[0] : null, len = R0 ? lenWords(renderFrames(P, R0), renderFps(P, R0)) : '';
  const head = `<div class="row sp"><h2>${t('What it took')}</h2><span class="small muted">${t("Claude's time for every step - read from Claude Code's own logs on this PC, nothing is sent anywhere")}</span></div>`;
  if (!rows.length) {
    box.innerHTML = `<div class="panel took" id="pb-took">${head}<div class="small muted">${!D.logs ? t("Claude Code's logs for this folder are not on this PC.")
      : kind === 'prompt' ? t('Nothing counted yet. The Claude windows MotionLab opens for this script show up here.')
      : kind === 'project' ? t("Nothing counted yet. The Claude windows MotionLab opens for this video show up here - with the script it was filmed from and the lab's jobs.")
      : t('Nothing counted yet. The Claude windows MotionLab opens for this video show up here.')}</div></div>`;
    return;
  }
  const row = x => x.kind === 'job'
    ? `<li class="tk job"><i class="tkdot"></i><div><div class="tkh"><b>${esc(stepW(x.step))}</b></div>
        <div class="tkm">${dt(x.t0)} · <b>${minWords(x.minutes)}</b> · ${t('a lab job, no Claude')}</div></div></li>`
    : `<li class="tk"><i class="tkdot"></i><div><div class="tkh"><b>${esc(stepW(x.step))}</b>${x.what ? ` <span class="muted">“${esc(x.what)}”</span>` : ''}</div>
        <div class="tkm">${dt(x.t0)} · <b>${minWords(x.minutes)}</b>${x.measured ? '' : `<span class="dim" title="${ta('Claude Code wrote no turn time for it (stopped or interrupted): from its first to its last answer')}"> ${t('(about)')}</span>`}
          ${x.wait_minutes >= 0.05 ? `<span title="${ta("While the lab's tools ran (renders, checks) - the rest is Claude thinking and writing")}"> · ${t('{time} waiting on the lab', {time: minWords(x.wait_minutes)})}</span>` : ''}
          · ${esc(x.model || t('model not in the log'))}${x.effort ? ' · ' + esc(x.effort) : ''}${x.rounds > 1 ? ` · ${tn(x.rounds, '{n} round', '{n} rounds')}` : ''}${x.helpers.length ? `<span title="${esc(x.helpers.map(h => `${h.description || h.type} - ${h.model}`).join('\n'))}"> · ${plural(x.helpers.length, 'helper')}</span>` : ''}</div></div></li>`;
  const took = T.job_minutes ? t('<b>{claude}</b> of Claude and <b>{jobs}</b> of lab jobs', {claude: minWords(T.claude_minutes), jobs: minWords(T.job_minutes)})
    : t('<b>{time}</b> of Claude', {time: minWords(T.claude_minutes)});
  const early = !D.jobs_since || rows[0].t0 < D.jobs_since;
  box.innerHTML = `<div class="panel took" id="pb-took">${head}
    <ol class="tkline">${rows.map(row).join('')}</ol>
    <div class="tktot"><span class="tkk">${t('Total')}</span><span>${t('<b>{time}</b> of Claude', {time: minWords(T.claude_minutes)})}</span>${T.job_minutes ? `<span>${t('<b>{time}</b> of lab jobs', {time: minWords(T.job_minutes)})}</span>` : ''}
      <span class="dim">${plural(T.windows, 'Claude window')}${T.models.length ? ' · ' + T.models.map(esc).join(', ') : ''}</span></div>
    <div class="tksay">${kind === 'project' ? (len ? t('This {length} video took {took}.', {length: len, took}) : t('This video took {took}.', {took}))
      : kind === 'analysis' ? t('Checking this video took {took}.', {took}) : t('It took {took}.', {took})}</div>
    ${D.other.rounds ? `<details class="tkmore"><summary>${tn(D.other.rounds, 'Not counted: {n} other request in the same Claude windows ({time})',
      'Not counted: {n} other requests in the same Claude windows ({time})', {time: minWords(D.other.minutes)})}</summary>
      <div class="small muted">${kind === 'analysis' ? t('Things you asked in the same window that were not this check - left out of the total.')
        : t("Things you asked in the same window that were not this video's steps - left out of the total.")}</div>
      <ul class="tkother">${D.other.prompts.map(o => `<li>“${esc(o.prompt)}” · ${minWords(o.minutes)}</li>`).join('')}</ul></details>` : ''}
    ${kind !== 'prompt' && early ? `<div class="small dim tknote">${t("The lab's own jobs (quick drafts, thumbnails, renders the app runs) are counted from MotionLab 0.4.4 on.")}</div>` : ''}</div>`;
}
// "● Claude is working on <video> · 12 min · 1.2 M tokens · reading the contact sheets" (0.4.4, the user: "minimalistic,
// straight to the point, do not overuse pc resources and 100% sure it doesn't use extra tokens"): the heartbeat carries
// it (server.live_claude: only the Claude windows MotionLab opened, only the bytes their logs grew by); gone when the
// turn ends. One line in the sidebar + one on that video's Overview.
let LIVE = [];
function liveLine(L) {
  LIVE = L;
  const s = $('#side-live'), x = L[0];
  if (s) {
    s.hidden = !x;
    if (x) {
      s.href = x.project ? `#/project/${encodeURIComponent(x.project)}` : x.analysis ? `#/ref/${encodeURIComponent(x.analysis)}`
        : x.texts ? '#/texts/' + encodeURIComponent(x.texts) : '#/jobs';
      s.innerHTML = `<i class="lvdot"></i><span><b>${t('Claude is working')}</b><small>${minWords(x.minutes)}${x.batch ? ` · ${t('{done} of {total} done', {done: x.batch.done, total: x.batch.total})}` : ''}${L.length > 1 ? ` · ${t('{n} more', {n: L.length - 1})}` : ''}${x.step ? ` · ${esc(t(x.step))}` : ''}</small></span>`;
      s.title = L.map(y => t('Claude is working on {what} · {time} · {model} · {step}', {what: y.project || y.analysis || y.label || t('a task'),
        time: minWords(y.minutes), model: [y.model, y.effort].filter(Boolean).join(' '), step: t(y.step)})).join('\n');
    }
  }
  $$('[data-live]').forEach(b => {
    const y = L.find(z => z.project === b.dataset.live || z.analysis === b.dataset.live);
    b.hidden = !y;
    if (y) b.innerHTML = `<i class="lvdot"></i><span>${t('Claude is working on <b>{name}</b>', {name: esc(b.dataset.name || b.dataset.live)})} · ${minWords(y.minutes)}${y.step ? ` · ${esc(t(y.step))}` : ''}</span>`;
  });
}
const nClipsWords = P => P.sources.length ? tn(P.sources.length, '{n} clip ready.', '{n} clips ready.') : t('Copy your clips into its folder first (Folder, above).');
// the Overview's one line about the review so far: the parts rated (the details: Review)
function reviewSummary(P) {
  const A = (P.outcome || {}).aspects || {};
  const rated = ASPECTS.filter(([k]) => RATE[(A[k] || {}).rating]);
  if (!rated.length) return '';
  const parts = rated.map(([k, l]) => `${esc(l)} ${rvChip('result', A[k].rating)}`).join(' · '), link = `#/project/${encodeURIComponent(P.name)}/review`;
  return `<div class="small pvrev">${P.reviewed === false ? t('Your review <span class="amber">(of an older render)</span>: {parts} - <a href="{link}">open the review →</a>', {parts, link})
    : t('Your review: {parts} - <a href="{link}">open the review →</a>', {parts, link})}</div>`;
}

// ---- Review: the render on the left, the review panel beside it (the user, 2026-10-15: "in the side bar, it's easier
// to review and look for changes"; 2026-10-18: the one review pattern) - How did it turn out? per part, Overall first
// (Good / OK / Bad + a note, each part saved as you go -> outcome.json "aspects"), then Send it to Claude = the next
// version from your review: /recreate-video improve, a video made from zero /generate-video improve (the skill that
// built it). The notes on moments (0.4.2) left the page on 2026-10-15; saved ones stay in outcome.json "moments".
function projReview(el, P) {
  const R = newestFirst(P), gen = inGenerator(P), nx = (P.outcome || {}).next || null, enc = encodeURIComponent(P.name);
  const A = () => (P.outcome || {}).aspects || {};
  el.innerHTML = `<div class="rvlayout"><div class="rvthing">${R.length ? '<div id="rvpick" style="margin-bottom:8px"></div><div id="rvpl"></div>'
      : `<div class="empty">${t('No render yet - a review starts with watching it.')}</div>`}
      <div class="hint" style="margin-top:10px">${t('Watch it and rate it beside it - Overall first, then the parts that matter - with a note on what to keep or change. Claude reads it when it makes the next version, and keeps what you rated good.')}</div></div>
    <aside id="rvp-out"></aside></div>`;
  let pl = null;
  if (R.length) renderPicker($('#rvpick', el), P, r => {
    stopPlayer(pl);
    pl = new Player($('#rvpl', el), r.rel, renderFps(P, r), renderFrames(P, r));
    pl.v.poster = posterUrl(P, r);
  });
  const post = rvQueue(), over = nx === 'start_over';
  const more = over ? (gen ? `${t('<b>You chose to start over</b> - Claude makes it again from the plan, in another feel.')} <a href="#" data-rvfix>${t('Improve this one instead')}</a>`
      : `${t('<b>You chose to start over</b> - a different feel, not a new version of this one.')} <button type="button" class="btn sm" data-rvnew><svg class="i"><use href="#i-edit"/></svg>${t('New edit with these clips…')}</button> <a href="#" data-rvfix>${t('Improve this one instead')}</a>`)
    : `<a href="#" data-rvover>${t('Not the right feel at all? Start over')}</a>`;
  const pn = reviewPanel($('#rvp-out', el), {
    sections: [{id: 'aspects', ask: t('How did it turn out?'), intro: t('Overall first - then the parts that matter'), scale: 'result', note: 'line',
      items: () => [...ASPECTS.filter(a => a[0] === 'overall'), ...ASPECTS.filter(a => a[0] !== 'overall')]
        .map(([k, l]) => ({id: k, label: k === 'overall' ? `<b>${esc(l)}</b>` : esc(l), optional: k !== 'overall'})),
      get: k => { const a = A()[k] || {}; return {v: a.rating || '', note: a.note || ''}; },
      set: (k, a) => {                               // one part per save, as before (data.save_outcome keeps every other key)
        const O = P.outcome = P.outcome || {}, one = {rating: a.v || null, note: a.note.trim()};
        O.aspects = {...(O.aspects || {}), [k]: one};
        P.reviewed = Object.values(O.aspects).some(x => x && x.rating);
        return post(async () => { const r = await api(`/api/project/${enc}/outcome`, {aspects: {[k]: one}}); P.outcome = {...r, aspects: P.outcome.aspects}; });
      },
      hint: v => v === 'ok' || v === 'bad' ? t('What should change? (saved as you type)') : t('What to keep or change (optional)')}],
    stale: () => P.reviewed === false && Object.keys(A()).length ? t('These ratings were for an older render - rate this one.') : '',
    send: {hint: () => {                             // 0.5.3 (E2): which parts the next version changes
      if (over && gen) return t('Claude starts it over from the plan, in a different feel - this one stays.');
      const ch = ASPECTS.filter(([k]) => k !== 'overall' && ['ok', 'bad'].includes((A()[k] || {}).rating)).map(([, l]) => esc(l));
      return t('Claude makes the next version from your review - this one stays.')
        + (ch.length ? ' ' + t('It changes <b>{parts}</b> and keeps the rest.', {parts: ch.join(', ')}) : '');
    },
      cmd: gen ? `/generate-video improve ${P.name}` : `/recreate-video improve ${P.name}`, task: gen ? 'generate' : 'recreate', name: P.name, more,
      go: async () => { if (!(over && gen) && nx !== 'fix') { try { await setNext(P, 'fix'); } catch (e) { /* the review is saved: Claude reads it anyway */ } } }}});
  const again = () => { stopPlayer(pl); projReview(el, P); };
  const choose = async v => { try { await pn.flush(); await setNext(P, v); again(); } catch (err) { toast(err.message, 'err'); } };
  const ov = $('[data-rvover]', el);
  if (ov) ov.onclick = e => { e.preventDefault(); if (gen) choose('start_over'); else startOver(P).then(again); };
  const nw = $('[data-rvnew]', el); if (nw) nw.onclick = () => newEdit({project: P.name});
  const fx = $('[data-rvfix]', el); if (fx) fx.onclick = e => { e.preventDefault(); choose('fix'); };
}
// 0.4.3, after posting: the click-through rate per thumbnail (A / B / C, read in YouTube Studio - MotionLab never logs
// in) and the video's link -> outcome.json "packaging"; Claude repeats what won (/write-title reads it). Since 2026-10-15 at
// the end of Ready to post (the Overview).
function packagingBox(P) {
  const pg = (P.outcome || {}).packaging || {}, ctr = pg.ctr || {};
  const ids = [...new Set(['A', 'B', 'C', ...Object.keys(ctr)])].sort();
  const got = Object.entries(ctr).sort((a, b) => b[1] - a[1]);
  return `<div class="panel pbsec opack" id="pb-after"><div class="row sp"><h2>${t('After posting: which thumbnail got clicked')}</h2><span class="small muted">${t('the click-through rate from YouTube Studio - MotionLab never logs in to your accounts')}</span></div>
    <div class="row" style="margin-top:6px">${ids.map(k => `<label class="small octrl">${k} <input type="text" inputmode="decimal" class="octr" data-id="${k}" value="${esc(ctr[k] == null ? '' : numStr(ctr[k]))}" placeholder="–"> %</label>`).join('')}
      <input type="url" class="olink" value="${esc(pg.link || '')}" placeholder="${ta("the video's link (https://…)")}"><button class="btn sm" id="opsave">${t('Save')}</button></div>
    ${got.length > 1 ? `<div class="small" style="margin-top:6px">${t('<b class="ok">{id}</b> got the most clicks ({ctr} %) - Claude makes the next thumbnails more like it.', {id: esc(got[0][0]), ctr: numStr(got[0][1])})}</div>` : ''}
    ${pg.link ? `<div class="small" style="margin-top:4px"><a href="${esc(pg.link)}" target="_blank" rel="noopener">${t('Open the posted video')}</a>${pg.updated ? ` <span class="dim">· ${t('saved {date}', {date: esc(pg.updated)})}</span>` : ''}</div>` : ''}</div>`;
}
function wirePackaging(el, P) {
  const ops = $('#opsave', el);
  if (ops) ops.onclick = async () => {
    const ctr = Object.fromEntries($$('.octr', el).map(i => [i.dataset.id, i.value.trim()]));
    try {
      P.outcome = await api(`/api/project/${encodeURIComponent(P.name)}/outcome`, {packaging: {ctr, link: $('.olink', el).value.trim()}});
      toast(t('Saved'), 'ok');
      const box = $('.opack', el); box.outerHTML = packagingBox(P); wirePackaging(el, P);
    } catch (e) { toast(e.message, 'err'); }
  };
}

// ---- Versions: every edit version (how each was made) and its renders, the side-by-sides with the reference
function projVersions(el, P) {
  const R = newestFirst(P), enc = encodeURIComponent(P.name);
  el.innerHTML = `<div class="hint" style="margin-bottom:12px">${t('Every version of this edit and its renders. A new version never replaces an old one. Rate the newest on the <a href="{link}">Review</a> tab.', {link: `#/project/${enc}/review`})}</div>
    <div class="panel"><h2>${t('Edit versions')}</h2><table class="t"><thead><tr><th>${t('Version')}</th><th>${t('Length')}</th><th>${t('Made|version')}</th><th class="num">${t('Layers')}</th></tr></thead><tbody>
    ${P.plans.slice().reverse().map(p => `<tr><td class="mono amber">${esc(p.version)}</td><td>${t('{frames} frames · {range} · {fps} fps', {frames: p.frames, range: frange(0, p.frames - 1, p.fps), fps: p.fps})}</td>
      <td class="small">${p.made_by === 'draft_edit.py' ? `${p.style ? t('quick draft: {style}', {style: esc(p.style)}) : t('quick draft')}${p.notes ? ` · <a href="#" data-open="${esc(p.notes)}">${t('notes')}</a>` : ''}` : `<span class="muted">${t('by Claude')}</span>`}</td>
      <td class="num">${p.layers}</td></tr>`).join('') || `<tr><td colspan="4" class="muted">${t('none yet - <b>New edit…</b> above')}</td></tr>`}</tbody></table>
    ${P.edit_scripts.length ? `<div class="small muted" style="margin-top:8px">${t('Edit scripts: {list}', {list: P.edit_scripts.map(s => `<a href="#" data-open="${esc(s)}" data-reveal>${esc(s.split('/').pop())}</a>`).join(', ')})}</div>` : ''}</div>
    <h3>${t('Renders')}</h3>
    ${R.length ? `<div class="grid g2">${R.map((r, i) => `<div class="panel"><div class="row sp"><h2>${renderLabel(r)} <span class="small muted">${r.kind === 'resolve' ? t('from DaVinci Resolve') : t('lab render')}</span></h2>
      <span class="small muted">${esc(r.name)} · ${bytes(r.size)} · ${esc(r.modified)}</span></div><div id="pl${i}"></div>
      <div class="row" style="margin-top:8px"><button class="btn sm" data-open="${esc(r.rel)}">${t('Open in player')}</button><button class="btn sm" data-open="${esc(r.rel)}" data-reveal>${t('Show in folder')}</button>
        <div class="grow"></div>${delBtn('file', r.rel, '', ' ' + t('Delete'))}</div></div>`).join('')}</div>` : `<div class="empty">${t('No renders yet.')}</div>`}
    ${P.compares.length ? `<h3>${t('Side by side with the reference')}</h3>
    <div class="grid g2">${P.compares.map((r, i) => `<div class="panel"><div class="row sp" style="margin-bottom:6px"><span class="small muted">${esc(r.name)} · ${bytes(r.size)}</span>${delBtn('file', r.rel, '', ' ' + t('Delete'))}</div><div id="cp${i}"></div></div>`).join('')}</div>` : ''}`;
  R.forEach((r, i) => new Player($('#pl' + i, el), r.rel, renderFps(P, r), renderFrames(P, r)));
  const fps0 = (P.plans[0] || {}).fps || 25, n0 = (P.plans[0] || {}).frames;
  P.compares.forEach((r, i) => new Player($('#cp' + i, el), r.rel, fps0, n0));
}

// ---- Footage: the user's clips (read-only) + the storyboards (one frame per second of every clip)
function projFootage(el, P) {
  el.innerHTML = `<div class="row sp" style="margin-bottom:12px"><div class="hint">${t("Your clips - only read, never changed. Copy more into the video's folder; the next edit can use them.")}</div>
      <button class="btn sm" data-open="${esc('projects/' + P.name)}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button></div>
    <div class="panel"><table class="t"><thead><tr><th>${t('ID')}</th><th>${t('File')}</th><th>${t('Format')}</th><th class="num">${t('Length')}</th><th class="num">${t('Size')}</th></tr></thead><tbody>
    ${P.sources.map(s => `<tr><td class="mono amber">${s.id || '–'}</td><td>${esc(s.name)}${s.exists ? '' : ` <span class="bad">${t('missing|file')}</span>`}</td>
      <td class="small muted">${s.photo ? `<b class="nephoto inl">${t('PHOTO')}</b>${s.resolution ? ' ' + esc(s.resolution) : ''}` : s.resolution ? `${esc(s.resolution)} · ${s.fps || '?'} fps` : t('measured when an edit uses it')}</td>
      <td class="num">${s.duration_s ? dec(s.duration_s, 1) + ' s' : '–'}</td><td class="num">${bytes(s.size)}</td></tr>`).join('')}</tbody></table></div>
    ${P.boards.length ? `<h3>${t('Storyboards (one frame per second of every clip)')}</h3>
    <div class="sheets" style="grid-template-columns:repeat(3,1fr)">${P.boards.map((b, i) => `<img src="${fileUrl(b)}" data-i="${i}" loading="lazy">`).join('')}</div>` : ''}`;
  $$('.sheets img', el).forEach(img => img.onclick = () => lightbox(P.boards.map(b => ({src: b})), +img.dataset.i));
}

// ---- Edit > a video > Publish (0.4.3): the ready-to-post package in build\publish\ - the title, thumbnails A / B / C
// (16:9 + the 9:16 cover, each checked: tools\thumbnail.py), the description with chapters, hashtags (tools\publish.py).
// The app reads package.json (GET /api/project/<p>/publish), runs the thumbnail jobs and calls publish.write
// (POST .../publish); Claude does all of it with /write-title package <p>
const THUMB_JOBS = ['thumb_candidates', 'thumb_make', 'thumb_render', 'thumb_check'];
const PUBST = {};                 // per video: the *do it yourself* choices survive the redraw when a job ends
const CHECK_WORDS = {readability: t('Readable on a phone'), words: t('2-4 words'), text_size: t('Text size'), contrast: t('Contrast'),
  subject: t('Face size'), look: t('Brightness and colour vs your niche'), safe_zone: t('Clear of the apps\' buttons and crops'),
  file_size: t('File size'), title_length: t('Title length on a phone'), title_repeat: t('Adds to the title'), promise: t('The title\'s promise in the first 3 s')};
const CK = {PASS: ['✓', 'ok'], WARN: ['~', 'amber'], FAIL: ['✗', 'bad'], SKIP: ['–', 'dim']};
// x.text = thumbnail.py's sentence, stored in package.json in English: a fixed one shows in Spanish by key (_by_key)
const ckLine = x => { const [ic, cls] = CK[x.status] || ['•', ''], txt = esc(t(x.text ?? ''));
  return `<li><b class="${cls}" title="${esc(x.status)}">${ic}</b><span><b>${esc(CHECK_WORDS[x.rule] || x.rule)}</b>${x.value != null ? ` <span class="ckv">${esc(x.value)}</span>` : ''}
    <span class="muted">${x.status === 'SKIP' ? t('not measured - {text}', {text: txt}) : txt}</span></span></li>`; };
const ckSum = res => res ? `<span class="ckres ${(CK[res] || [])[1] || ''}">${res === 'PASS' ? t('✓ passes') : res === 'WARN' ? t('~ could be better') : res === 'FAIL' ? t('✗ needs a fix') : esc(res)}</span>` : '';
function ckBlock(tm) {
  const c = tm.check || {};
  if (!c['16x9']) return `<div class="small muted">${c.stale ? t('Changed since the last check - <b>Check them</b> above.') : t('Not checked yet - <b>Check them</b> above.')}</div>`;
  return [['16x9', 'YouTube 16:9'], ['9x16', t('Cover 9:16')]].map(([k, l]) => {
    const L = c[k] || [], bad = L.filter(x => x.status === 'FAIL' || x.status === 'WARN');
    return `<div class="ckbox"><div class="row sp"><b class="small">${l}</b><span class="small">${['PASS', 'WARN', 'FAIL', 'SKIP'].map(s => { const n = L.filter(x => x.status === s).length;
        return n ? `<span class="${CK[s][1]}">${CK[s][0]} ${n}</span>` : ''; }).join(' ')}</span></div>
      ${bad.length ? `<ul class="cklist">${bad.map(ckLine).join('')}</ul>` : ''}
      <details><summary class="small muted">${tn(L.length, 'All {n} rules', 'All {n} rules')}</summary><ul class="cklist">${L.map(ckLine).join('')}</ul></details></div>`; }).join('')
    + `<div class="small dim">${c.title ? t('checked {date} with the title “{title}”', {date: esc(c.date || ''), title: esc(c.title)}) : t('checked {date}', {date: esc(c.date || '')})}</div>`;
}
const ytOf = (f, fps) => { const s = Math.floor(f / fps + 1e-9); return s >= 3600 ? `${Math.floor(s / 3600)}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}` : `${Math.floor(s / 60)}:${pad(s % 60)}`; };
async function projPublish(el, P) {
  const I = await api(`/api/project/${encodeURIComponent(P.name)}/publish`);
  const pk = I.package || {}, th = pk.thumbnails || [], cand = pk.candidates || {}, items = cand.items || [];
  const S = PUBST[P.name] = PUBST[P.name] || {words: '', template: 'outline', id: '', pick: null, self: false, from: 'clips'};
  const fps = I.fps || (pk.chapters || {}).fps || 30;
  const url = `/api/project/${encodeURIComponent(P.name)}/publish`;
  const claude = (cls = 'pri') => claudeBtn(`/write-title package ${P.name}`, t('Make it with Claude'), 'title', P.name, cls);
  const empty = !I.exists && !I.records.length && !S.self;
  // since 2026-10-15 on the Overview, under the video (the user: "if we are happy with the edit the next row ... the publish
  // tab should not exist and be moved down to the preview video in the overview tab")
  const head = `<div class="pvsech"><svg class="i"><use href="#i-thumb"/></svg><div><h2>${t('Happy with it? Ready to post')}</h2>
    <div class="small muted">${t('The title, thumbnails for YouTube and the vertical cover, the description with chapters and hashtags - checked before you post.')}</div></div></div>`;
  if (empty) {
    el.innerHTML = `${head}<div class="panel pbsec pbempty">${claudeBtn(`/write-title package ${P.name}`, t('Make the package with Claude'), 'title', P.name, 'pri big')}
      <span class="small muted">${t('Claude picks the moments, makes and checks three thumbnails and writes the words.')}</span><a href="#" class="small" id="pbself">${t('or do it yourself')}</a></div>
      ${packagingBox(P)}`;
    $('#pbself', el).onclick = e => { e.preventDefault(); S.self = true; projPublish(el, P); };
    wirePackaging(el, P); reIndex(P, I);
    return I;
  }
  // the titles to choose from: the package's own, then the linked title records' (Prepare > Title & thumbnail first)
  const choices = (pk.titles || []).map(x => ({...x}));
  I.records.forEach(r => (r.titles || []).forEach(x => { if (!choices.some(c => c.text === x.text)) choices.push({...x, from: r.id}); }));
  const title = pk.title || '', chs = ((pk.chapters || {}).items || []).map(c => ({f: c.f, name: c.name}));
  const desc = pk.description || {}, tags = pk.hashtags || {};
  if (!S.id) S.id = ['A', 'B', 'C'].find(x => !th.some(y => y.id === x)) || 'A';
  const runJob = async (kind, args) => {
    try { const j = await api('/api/jobs', {kind, args: {project: P.name, ...args}, queue: true});
      toast(j.status === 'queued' ? t('Waiting its turn: {title}', {title: j.title}) : t('Started: {title}', {title: j.title}), 'ok'); ping(); route(); }
    catch (e) { toast(e.message, 'err'); }
  };
  const concept = I.records.flatMap(r => r.concepts || []);
  // the title, the thumbnails and making one yourself = one glowing box (the user, 2026-10-15: "all in one so the person
  // isn't thrown around on where everything is")
  el.innerHTML = `${head}<div class="toprow">${claude()}
      <span class="small muted">${t('Claude picks the moments, makes and checks the thumbnails and writes the words. Or do any part yourself below.')}</span></div>
    <div class="panel pbsec pbpack"><div class="pbpart" id="pb-title"><div class="row sp"><h2>${t('Title')}</h2>${title ?`<span class="row" style="gap:6px">${tchars(title.length)}<button class="btn sm" data-cp="title"><svg class="i"><use href="#i-clipboard"/></svg>${t('Copy')}</button></span>` : ''}</div>
      ${title ? `<div class="pbtitle">${esc(title)}</div>` : `<div class="small muted">${t('No title yet - pick one below or type your own.')}</div>`}
      ${choices.length ? `<details class="pbchoices"${title ? '' : ' open'}><summary class="small">${tn(choices.length, '{n} title to choose from', '{n} titles to choose from')}</summary>
        <div class="ttlist">${choices.map((c, i) => `<div class="ttrow${c.text === title ? ' chosen' : ''}"><div class="grow"><b class="ttx">${esc(c.text)}</b>
          <div class="small">${c.pattern ? `<span class="ttpat">${esc(c.pattern)}</span> ` : ''}${tchars(c.chars || c.text.length)}</div></div>
          ${c.text === title ? `<span class="tag done">${t('chosen|title')}</span>` : `<button class="btn sm" data-pick="${i}">${t('Use this')}</button>`}</div>`).join('')}</div></details>` : ''}
      <div class="row" style="margin-top:8px"><input type="text" id="pbown" placeholder="${ta('or type your own title')}" maxlength="100" style="flex:1;min-width:260px"><span class="small muted" id="pbownn"></span><button class="btn sm" id="pbownok">${t('Save title')}</button></div></div>
    <div class="pbpart" id="pb-thumbs"><div class="row sp"><h2>${t('Thumbnails')}</h2><span class="row" style="gap:6px">${th.length ? `<button class="btn sm" id="pbcheck" title="${title ? ta('with the title') : ta('no title yet: the title rules are skipped')}">${t('Check them')}</button>` : ''}</span></div>
      ${th.length ? `<div class="pbthumbs">${th.map(tm => { const ph = (tm.photos || [])[0] || {}, v = tm.v ? `?v=${tm.v}` : '';
        return `<div class="pbthumb" data-t="${esc(tm.id)}"><div class="row sp"><span class="row" style="gap:8px"><span class="tid">${esc(tm.id)}</span><b>${esc(tm.words || '')}</b>
            <span class="small muted">${esc(tm.template || '')}${ph.frame != null ? ` · ${ph.clip ? esc(ph.clip) + ' ' : ''}${ftc(ph.frame, ph.fps || 25)}` : ph.image || ph.file ? ` · ${t('your picture')}` : ''}</span></span>${ckSum((tm.check || {}).result)}</div>
          <div class="pbimgs"><figure><img src="${fileUrl(tm.files['16x9'])}${v}" data-lb="16x9" alt=""><figcaption>YouTube 16:9</figcaption></figure>
            <figure class="tall"><img src="${fileUrl(tm.files['9x16'])}${v}" data-lb="9x16" alt=""><figcaption>${t('Cover 9:16')}</figcaption></figure>
            ${tm.files['9x16_crops'] ? `<figure class="crops"><img src="${fileUrl(tm.files['9x16_crops'])}${v}" data-lb="9x16_crops" alt=""><figcaption>${t('How the apps crop it')}</figcaption></figure>` : ''}</div>
          <div class="pbck">${ckBlock(tm)}</div>
          <div class="row" style="margin-top:8px">${tm.settings.length ? `<button class="btn sm" data-tset>${t('Change it…')}</button>` : ''}<button class="btn sm" data-trender>${t('Render again')}</button>
            <button class="btn sm ghost" data-open="${esc(tm.files['16x9'])}" data-reveal>${t('Show in folder')}</button></div></div>`; }).join('')}</div>`
        : `<div class="small muted">${t("No thumbnails yet - Claude makes three (A, B, C) for YouTube's own test, or make one yourself below.")}${I.face_detector ? '' : ' ' + t('Face sizes are not measured on this PC (the face finder is not installed).')}</div>`}</div>
    <details class="pbpart pbself" id="pb-self"${th.length && !S.pick ? '' : ' open'}><summary><h2>${t('Make a thumbnail yourself')}</h2></summary>
      <div class="nestep"><b>1</b>${t('The picture')}</div>
      <div class="row"><button class="btn" id="pbcand"><svg class="i"><use href="#i-analyze"/></svg>${t('Find good moments')}</button>
        ${I.render && I.clips ? `<div class="seg" id="pbfrom"><button data-v="clips">${t('in your clips')}</button><button data-v="render">${t('in the finished video')}</button></div>` : ''}
        <span class="small muted">${t('or')}</span><label class="btn ghost">${t('Use a picture you made…')}<input type="file" id="pbimg" accept=".jpg,.jpeg,.png,.webp" hidden></label>
        <span class="small muted">${t('The image prompt: <a href="#" id="pbai">write it with Claude</a> (Prompts → Image), make it on the site, bring the picture here.')}</span></div>
      ${items.length || I.images.length ? `<div class="pbtiles">${items.map(c => `<button class="pbtile${S.pick && S.pick.c === c.id ? ' on' : ''}" data-c="${esc(c.id)}" title="${ta('score {score}', {score: numStr(c.score)})}${c.face != null ? ` · ${ta('face {face} % of the height', {face: Math.round(c.face * 100)})}` : ''}">
          <img src="${fileUrl(c.png)}" loading="lazy" alt=""><span>${esc(c.clip)} ${ftc(c.frame, c.fps)}</span></button>`).join('')}
        ${I.images.map(m => `<button class="pbtile${S.pick && S.pick.image === m.path ? ' on' : ''}" data-img="${esc(m.path)}" title="${esc(m.name)}"><img src="${fileUrl(m.rel)}" loading="lazy" alt=""><span>${t('your picture')}</span></button>`).join('')}</div>
        ${cand.made ? `<div class="small dim">${cand.from === 'render' ? t('moments found {date} in the finished video', {date: esc(cand.made)}) : t('moments found {date} in the clips', {date: esc(cand.made)})}${cand.face_detector ? '' : ` · ${t('faces not measured')}`}</div>` : ''}` : ''}
      <div class="nestep"><b>2</b>${t('The words and the design')}</div>
      <div class="nedet spf"><label>${t('2-4 words')}</label><div class="row"><input type="text" id="pbwords" value="${esc(S.words)}" maxlength="60" placeholder="${ta('e.g. NO STUDIO')}" style="width:260px"><span class="small" id="pbwn"></span></div>
        ${concept.length ? `<label></label><div class="row small">${t('Your ideas: {list}', {list: concept.map(c => `<button class="fchip sm" data-w="${esc(c.words || '')}" title="${esc(c.sketch || '')}">${esc(c.id)}: ${esc(c.words || '')}</button>`).join('')})}</div>` : ''}
        ${(I.styles || []).length ? `<label>${t('In the style of')}</label><div class="seg" id="pbsty"><button data-v="">${t('no set')}</button>${I.styles.map(s => `<button data-v="${esc(s.name)}" title="${esc(s.font ? tn(s.count, 'the patterns Claude found in {n} thumbnails: the design, the colours, the font - {font} ({how})', 'the patterns Claude found in {n} thumbnails: the design, the colours, the font - {font} ({how})', {font: s.font.family, how: s.font.from === 'measured' ? t('measured|font') : t("Claude's pick")})
          : tn(s.count, 'the patterns Claude found in {n} thumbnails: the design, the colours, the font', 'the patterns Claude found in {n} thumbnails: the design, the colours, the font'))}">${esc(s.label)}</button>`).join('')}</div>` : ''}
        <label>${t('Design')}</label><div class="seg" id="pbtpl">${S.style ? `<button data-v="" title="${ta("the design the set's structure fits")}">${t("the set's")}</button>` : ''}${(I.templates.length ? I.templates : [{name: 'outline'}]).map(d => `<button data-v="${esc(d.name)}" title="${ta(d.what || '')}">${esc(d.name)}</button>`).join('')}</div>
        <label>${t('Thumbnail')}</label><div class="row"><div class="seg" id="pbid">${['A', 'B', 'C'].map(x => `<button data-v="${x}">${x}</button>`).join('')}</div><span class="small muted" id="pbidh"></span></div></div>
      <div class="row" style="margin-top:12px"><button class="btn pri" id="pbmake">${t('Make it')}</button><span class="small muted" id="pbpick"></span></div></details></div>
    <div class="panel pbsec" id="pb-desc"><div class="row sp"><h2>${t('Description')}</h2><span class="row" style="gap:6px">${desc.text ? `<button class="btn sm" data-cp="desc"><svg class="i"><use href="#i-clipboard"/></svg>${t('Copy the description')}</button>` : ''}${tags.line ? `<button class="btn sm" data-cp="tags"><svg class="i"><use href="#i-clipboard"/></svg>${t('Copy the hashtags')}</button>` : ''}</span></div>
      <label class="small muted">${t('Your words (the chapters and hashtags are added under them)')}</label>
      <textarea id="pbbody" rows="4" style="width:100%" placeholder="${ta('what the video is, in two or three lines')}">${esc(desc.body || '')}</textarea>
      <div class="row sp" style="margin-top:10px"><b>${t('Chapters')}</b><span class="row" style="gap:6px"><span class="small muted">${t('suggest from')}</span><button class="btn sm" data-sug="plan" ${I.plan ? '' : `disabled title="${ta('no edit yet')}"`}>${t('the edit')}</button><button class="btn sm" data-sug="transcript">${t('what is said')}</button></span></div>
      <div class="small muted">${I.frames ? t("YouTube wants the first at 0:00, at least three, each 10 seconds or longer. The frame is the finished video's, f0–{last} at {fps} fps.", {last: I.frames - 1, fps})
        : t("YouTube wants the first at 0:00, at least three, each 10 seconds or longer. The frame is the finished video's.")}</div>
      <table class="t pbch"><thead><tr><th>YouTube</th><th>${t('Frame')}</th><th>${t('Timecode')}</th><th>${t('Name')}</th><th></th></tr></thead><tbody id="pbchs"></tbody></table>
      <button class="btn sm ghost" id="pbadd">${t('+ Add a chapter')}</button>
      <div class="nedet spf" style="margin-top:10px"><label>${t('Hashtags')}</label><input type="text" id="pbtags" value="${esc(tags.line || '')}" placeholder="${ta('#music #filmmaking - the first three show by the title')}" style="max-width:560px"></div>
      <div class="row" style="margin-top:12px"><button class="btn pri" id="pbsave">${t('Save the description')}</button><span class="small muted">${desc.updated ? t('saved {date}', {date: esc(String(desc.updated).replace('T', ' ').slice(0, 16))}) : ''}</span></div>
      <ul class="cklist" id="pbchecks">${(desc.checks || []).filter(c => c.status !== 'PASS').map(c => `<li><b class="${(CK[c.status] || [])[1]}">${(CK[c.status] || ['•'])[0]}</b><span><b>${esc(t(c.part ?? ''))}</b>: ${esc(t(c.rule ?? ''))} <span class="muted">${esc(t(c.detail ?? ''))}</span></span></li>`).join('')}</ul></div>
    ${packagingBox(P)}`;
  wirePackaging(el, P);
  // ---- title
  const own = $('#pbown', el), ownN = $('#pbownn', el);
  own.oninput = () => { ownN.innerHTML = own.value.trim() ? tchars(own.value.trim().length) : ''; };
  const saveTitle = async (text, from = '') => {
    try { const r = await api(url, {title: text, titles_from: (pk.titles || []).length ? '' : from});
      if (!r.ok) { toast(r.checks.filter(c => c.status === 'FAIL').map(c => `${t(c.rule)}: ${t(c.detail)}`).join(' · '), 'err'); return; }
      toast(t('Title saved'), 'ok'); projPublish(el, P); }
    catch (e) { toast(e.message, 'err'); }
  };
  $$('[data-pick]', el).forEach(b => b.onclick = () => { const c = choices[+b.dataset.pick]; saveTitle(c.text, c.from && /^title-/.test(c.from) ? c.from : ''); });
  $('#pbownok', el).onclick = () => { const v = own.value.trim(); if (!v) { own.focus(); return; } saveTitle(v, (I.records[0] || {}).id || ''); };
  $$('[data-cp]', el).forEach(b => b.onclick = () => copy(b.dataset.cp === 'title' ? title : b.dataset.cp === 'desc' ? desc.text : tags.line));
  // ---- thumbnails
  const chk = $('#pbcheck', el); if (chk) chk.onclick = () => runJob('thumb_check', {title});
  $$('.pbthumb', el).forEach(card => {
    const tm = th.find(x => x.id === card.dataset.t);
    $$('[data-lb]', card).forEach(img => img.onclick = () => {
      const L = th.flatMap(x => [['16x9', 'YouTube 16:9'], ['9x16', t('cover 9:16')], ['9x16_crops', t('how the apps crop the cover')]].filter(([k]) => x.files[k]).map(([k, l]) => ({src: x.files[k], cap: `${x.id} · ${l}`})));
      lightbox(L, Math.max(0, L.findIndex(x => x.src === tm.files[img.dataset.lb])));
    });
    $('[data-trender]', card).onclick = () => runJob('thumb_render', {id: tm.id});
    const ts = $('[data-tset]', card);
    if (ts) ts.onclick = () => modal(`<h2>${t('Thumbnail {id}: {words}', {id: esc(tm.id), words: esc(tm.words || '')})}</h2>
      <div class="small muted" style="margin-top:-4px">${t('Change the words, colours, size or where the photo sits, then render it again (about 15 seconds).')}</div>
      <div class="gset" style="margin-top:12px">${tm.settings.map(s => `<label title="${esc(s.id)}">${esc(s.label ? t(s.label) : s.id)}</label><div>${gsetInput(s)}</div>`).join('')}</div>
      <div class="row" style="margin-top:14px"><button class="btn pri" id="tsgo">${t('Save and render again')}</button><button class="btn" id="tsno">${t('Cancel')}</button></div>`, m => {
      $('#tsno', m).onclick = closeModal;
      $('#tsgo', m).onclick = async () => {
        const values = {}; $$('[data-set]', m).forEach(i => { values[i.dataset.set] = gsetValue(i); });
        try { await api(`/api/project/${encodeURIComponent(P.name)}/thumb`, {id: tm.id, values}); closeModal(); runJob('thumb_render', {id: tm.id}); }
        catch (e) { toast(e.message, 'err'); }
      };
    });
  });
  // ---- do it yourself
  const fb = $('#pbfrom', el);
  if (fb) { const paint = () => $$('button', fb).forEach(x => x.classList.toggle('on', x.dataset.v === S.from)); $$('button', fb).forEach(x => x.onclick = () => { S.from = x.dataset.v; paint(); }); paint(); }
  $('#pbcand', el).onclick = () => runJob('thumb_candidates', {render: !!fb && S.from === 'render'});
  $('#pbai', el).onclick = e => { e.preventDefault(); aiPromptsModal('image'); };
  const pickLine = () => {
    const c = S.pick && S.pick.c && items.find(x => x.id === S.pick.c);
    $('#pbpick', el).innerHTML = c ? t('from {clip} {frame} · about 15 seconds', {clip: esc(c.clip), frame: ftc(c.frame, c.fps)}) : S.pick && S.pick.image ? t('from your picture · about 15 seconds') : t('pick a moment or a picture first');
    const n = $('#pbwords', el).value.trim().split(/\s+/).filter(Boolean).length;
    $('#pbwn', el).innerHTML = !n ? '' : n >= 2 && n <= 4 ? `<span class="ok">${t('{n} words ✓', {n})}</span>` : `<span class="amber">${tn(n, '{n} word - 2-4 read best on a phone', '{n} words - 2-4 read best on a phone')}</span>`;
    $('#pbidh', el).textContent = th.some(y => y.id === S.id) ? t('replaces thumbnail {id}', {id: S.id}) : '';
    $('#pbmake', el).textContent = t('Make thumbnail {id}', {id: S.id});
  };
  $$('.pbtile', el).forEach(b => b.onclick = () => {
    S.pick = b.dataset.c ? {c: b.dataset.c} : {image: b.dataset.img};
    $$('.pbtile', el).forEach(x => x.classList.toggle('on', x === b)); pickLine();
  });
  $('#pbwords', el).oninput = e => { S.words = e.target.value; pickLine(); };
  $$('[data-w]', el).forEach(b => b.onclick = () => { $('#pbwords', el).value = S.words = b.dataset.w; pickLine(); });
  const seg = (id, key) => { const b = $(id, el); const paint = () => $$('button', b).forEach(x => x.classList.toggle('on', x.dataset.v === S[key]));
    $$('button', b).forEach(x => x.onclick = () => { S[key] = x.dataset.v; paint(); pickLine(); }); paint(); };
  seg('#pbtpl', 'template'); seg('#pbid', 'id');
  const sty = $('#pbsty', el);                        // 0.4.5: a thumbnail set's style -> the set's design by default
  if (sty) { const paint = () => $$('button', sty).forEach(x => x.classList.toggle('on', x.dataset.v === (S.style || '')));
    $$('button', sty).forEach(x => x.onclick = () => { S.style = x.dataset.v; S.template = S.style ? '' : 'outline'; projPublish(el, P); });
    paint(); }
  pickLine();
  $('#pbimg', el).onchange = async e => {
    const f = e.target.files[0]; e.target.value = '';
    if (!f) return;
    if (f.size > 30e6) { toast(t('Pictures up to 30 MB'), 'err'); return; }
    try { const r = await api(`/api/project/${encodeURIComponent(P.name)}/publish/image`, {name: f.name, data: b64(await f.arrayBuffer())});
      S.pick = {image: r.path}; toast(t('Picture added - type the words and make it'), 'ok'); projPublish(el, P); }
    catch (err) { toast(err.message, 'err'); }
  };
  $('#pbmake', el).onclick = () => {
    const words = $('#pbwords', el).value.trim();
    if (!S.pick) { toast(t('Pick a moment or a picture first'), 'err'); return; }
    if (!words) { $('#pbwords', el).focus(); toast(t('Type the 2-4 words for the thumbnail'), 'err'); return; }
    const c = S.pick.c && items.find(x => x.id === S.pick.c);
    runJob('thumb_make', {id: S.id, words, template: S.template, ...(S.style ? {style: S.style} : {}), ...(c ? {frame: c.frame, clip: c.clip} : {image: S.pick.image})});
  };
  // ---- description: chapters (YouTube time + frame + timecode), hashtags, the words
  let rows = chs.slice();
  const tb = $('#pbchs', el);
  const drawRows = (hints = {}) => {
    tb.innerHTML = rows.map((c, i) => `<tr data-i="${i}"><td class="mono">${ytOf(c.f, fps)}</td>
      <td><input type="number" class="chf" min="0" value="${c.f}" style="width:90px"></td><td class="tc">${tc(c.f, fps)}</td>
      <td><input type="text" class="chn" value="${esc(c.name)}" placeholder="${esc(hints[c.f] || t('a name'))}" style="width:100%"></td>
      <td><button class="btn sm ghost" data-chdel title="${ta('Remove this chapter')}">✕</button></td></tr>`).join('')
      || `<tr><td colspan="5" class="muted small">${t('No chapters - suggest them from the edit, or add them.')}</td></tr>`;
    $$('tr[data-i]', tb).forEach(tr => {
      const i = +tr.dataset.i;
      $('.chf', tr).oninput = e => { rows[i].f = Math.max(0, parseInt(e.target.value, 10) || 0); tr.cells[0].textContent = ytOf(rows[i].f, fps); tr.cells[2].textContent = tc(rows[i].f, fps); };
      $('.chn', tr).oninput = e => { rows[i].name = e.target.value; };
      $('[data-chdel]', tr).onclick = () => { rows.splice(i, 1); drawRows(hints); };
    });
  };
  drawRows();
  $('#pbadd', el).onclick = () => { const last = rows.length ? rows[rows.length - 1].f : -Math.round(10 * fps); rows.push({f: last + Math.round(10 * fps), name: ''}); drawRows(); };
  $$('[data-sug]', el).forEach(b => b.onclick = async () => {
    try {
      const C = await api(`/api/project/${encodeURIComponent(P.name)}/chapters?from=${b.dataset.sug}`);
      const hints = Object.fromEntries(C.points.map(x => [x.f, x.hint || '']));
      const old = Object.fromEntries(rows.map(r => [r.f, r.name]));
      rows = (C.suggested || []).map(f => ({f, name: old[f] || ''}));
      drawRows(hints);
      toast(tn(rows.length, '{n} chapter suggested - name each one, then save', '{n} chapters suggested - name each one, then save') + ((C.warnings || []).length ? ' · ' + C.warnings.join(' ') : ''), 'ok');
    } catch (e) { toast(e.message, 'err'); }
  });
  $('#pbsave', el).onclick = async () => {
    if (!title) { toast(t('Pick or type the title first (above)'), 'err'); own.focus(); return; }
    rows.sort((a, b) => a.f - b.f);
    try {
      const r = await api(url, {title, body: $('#pbbody', el).value, hashtags: $('#pbtags', el).value, chapters: rows.map(c => [c.f, c.name.trim()])});
      if (!r.ok) {
        $('#pbchecks', el).innerHTML = r.checks.filter(c => c.status !== 'PASS').map(c => `<li><b class="${(CK[c.status] || [])[1]}">${(CK[c.status] || ['•'])[0]}</b><span><b>${esc(t(c.part ?? ''))}</b>: ${esc(t(c.rule ?? ''))} <span class="muted">${esc(t(c.detail ?? ''))}</span></span></li>`).join('');
        toast(t('Not saved - fix what is marked ✗ below'), 'err'); return;
      }
      toast(t('Description saved'), 'ok'); projPublish(el, P);
    } catch (e) { toast(e.message, 'err'); }
  };
  reIndex(P, I);
  return I;
}

// ---- Videos > Graphics (0.3.2): the video's HTML graphics (tools\overlay.py): settings, render, save to the library
// 0.4.6: the font library (the lab's fonts folder) - a font setting lists every bundled family by what it suits, the
// Windows fonts older graphics used after them, and shows the picked one in a preview line (/fonts.css loads a family
// only when something shows it)
let FONTS = null;
const FONT_GROUPS = {yours: t('Your fonts (this PC only)'), 'heavy condensed': t('Heavy and narrow'), 'heavy wide': t('Heavy and wide'), 'friendly / rounded': t('Friendly, rounded'),
  'playful display': t('Playful'), 'handwritten / marker': t('Handwritten'), 'serif display': t('Serif'), 'clean text': t('Clean text'),
  'tech / mono': t('Tech'), other: t('Other|font group')};
const isFontSet = s => s.type === 'enum' && (s.id === 'font' || /_font$/.test(s.id));
const fontCss = f => `font-family:'${String(f).replace(/['"\\<>]/g, '')}', sans-serif`;
function fontOptions(s) {
  const v = s.value, opt = (val, label, tip) => `<option value="${esc(val)}" ${val === v ? 'selected' : ''} style="${fontCss(val)}"${tip ? ` title="${esc(tip)}"` : ''}>${esc(label)}</option>`;
  const declared = (s.options || []).map(o => o.value);
  if (!FONTS) return (s.options || []).map(o => opt(o.value, t(o.label ?? ''))).join('');
  const groups = {};
  FONTS.families.forEach(f => { (groups[f.group] = groups[f.group] || []).push(f); });
  const known = new Set([...FONTS.families.map(f => f.family), ...FONTS.windows]);
  const extra = declared.filter(x => !known.has(x));
  return Object.entries(groups).map(([g, L]) => `<optgroup label="${esc(FONT_GROUPS[g] || g)}">${L.map(f => opt(f.family, f.family, f.own ? t('your own font - on this PC only') : t('free font ({licence}), comes with MotionLab', {licence: f.licence}))).join('')}</optgroup>`).join('')
    + `<optgroup label="${ta('Windows only (another PC may draw them differently)')}">${FONTS.windows.map(w => opt(w, w)).join('')}</optgroup>`
    + (extra.length ? `<optgroup label="${ta('In this graphic')}">${extra.map(x => opt(x, x)).join('')}</optgroup>` : '');
}
const fontPreview = v => `<div class="fprev" style="${fontCss(v)}" title="${ta('how this font looks')}">${t('Aa Bb 0123 - the quick brown fox')}</div>`;
document.addEventListener('change', e => {
  const tg = e.target;
  if (tg.matches && tg.matches('select[data-font]') && tg.nextElementSibling && tg.nextElementSibling.classList.contains('fprev')) tg.nextElementSibling.style.cssText = fontCss(tg.value);
});
api('/api/fonts').then(f => {
  FONTS = f;
  $$('select[data-font]').forEach(sel => { const v = sel.value; sel.innerHTML = fontOptions({id: sel.dataset.set, type: 'enum', value: v, options: [...sel.options].map(o => ({value: o.value, label: o.textContent}))}); });
}).catch(() => {});

// the logo library (logos\, tools\logos.py, 2026-10-16): a logo setting (id logo / logos / *_logo / *_logos) gets *Pick a
// logo…*, a text setting whose label shows ":name:" gets *+ Logo* (it writes ":youtube:"); both open the picker under the
// field (not a dialog: the template's own dialog keeps its values). The live previews load the logos the values name.
let LOGOS = null;
const LOGO_GROUPS = {social: t('Social & video'), ai: t('AI tools'), creative: t('Creative apps'), dev: t('Code'), work: t('Work & money'), web: t('Browsers & systems'), other: t('Other|logo group')};
const LOGO_STYLES = [['', t('Auto - fits the background')], ['color', t('In its colours')], ['mono', t('One colour')], ['wordmark', t('The name written out')]];
const LOGO_VARIANT = {color: t('its colours'), mono: t('one colour - takes any colour'), wordmark: t('the name written out'), 'color-dark': t('its colours, for a dark background'), 'wordmark-dark': t('the name, for a dark background')};
const isLogoSet = s => s.type === 'string' && (/^logos?$/.test(s.id) || /_logos?$/.test(s.id));
const logoText = s => s.type === 'string' && !isLogoSet(s) && /:[a-z][a-z0-9-]*:/.test(s.label || '');
const logoSrc = (lg, v) => fileUrl(`logos/${lg.id}/${v && lg.variants[v] ? v : lg.default}.svg`);
const logoLoad = () => LOGOS ? Promise.resolve(LOGOS) : api('/api/logos').then(d => (LOGOS = d));
const logoFind = (L, q) => { const w = q.toLowerCase().split(/\s+/).filter(Boolean);
  return L.filter(lg => w.every(x => `${lg.id} ${lg.name.toLowerCase()} ${lg.words.join(' ')} ${lg.group}`.includes(x))); };
const logoTile = (lg, v, cls = '') => { const k = v && lg.variants[v] ? v : lg.default;
  return `<span class="lgimg${lg.variants[k].on === 'dark' ? ' dk' : ''} ${cls}"><img src="${logoSrc(lg, k)}" alt="" loading="lazy"></span>`; };
// the logo names in a graphic's values - a live preview loads just those ("a|b/mono" in a logo setting, ":a:" in a text)
function logoIds(vals) {
  const ids = new Set();
  Object.values(vals || {}).forEach(v => {
    if (typeof v !== 'string') return;
    v.split('|').forEach(x => { const m = /^\s*:?([a-z0-9][a-z0-9-]*)(?:\/[a-z0-9-]+)?:?\s*$/i.exec(x); if (m) ids.add(m[1].toLowerCase()); });
    for (const m of v.matchAll(/:([a-z0-9][a-z0-9-]*)(?:\/[a-z0-9-]+)?:/gi)) ids.add(m[1].toLowerCase());
  });
  return [...ids].slice(0, 200);
}
document.addEventListener('click', e => {
  const b = e.target.closest && e.target.closest('[data-logopick]');
  if (!b) return;
  e.preventDefault();
  const host = b.closest('.lgin'), inp = $('input[data-set]', host), was = host._pop && host._pop.isConnected;
  $$('.lgpop').forEach(x => x.remove());
  if (!was) logoPicker(host, inp, b.dataset.logopick);
});
['keyup', 'click', 'focus'].forEach(ev => document.addEventListener(ev, e => {            // where a text's logo goes
  const t = e.target;
  if (t && t.matches && t.matches('input[data-logohow]')) t.dataset.caret = t.selectionStart ?? '';
}, true));
async function logoPicker(host, inp, mode) {
  const pop = document.createElement('div');
  pop.className = 'lgpop';
  pop.innerHTML = `<div class="small muted">${t('Loading the logos…')}</div>`;
  const cell = host.parentElement;                 // in a settings form: a row of its own, as wide as the form
  (cell && cell.parentElement && cell.parentElement.classList.contains('gset') ? cell : host).after(pop);
  host._pop = pop;
  let D;
  try { D = await logoLoad(); } catch (e) { pop.innerHTML = `<div class="small bad">${esc(e.message)}</div>`; return; }
  let q = '', g = '', st = '';
  pop.innerHTML = `<div class="row" style="gap:6px"><input type="search" class="lgq" placeholder="${ta('Search: youtube, editing, ai…')}" style="flex:1;min-width:0">
      <select class="lgst" title="${ta('Which version')}">${LOGO_STYLES.map(([k, l]) => `<option value="${k}">${esc(l)}</option>`).join('')}</select>
      <button type="button" class="btn sm lgx" title="${ta('Close')}">✕</button></div>
    <div class="row lgg">${[['', t('All|logos')], ...Object.keys(D.groups || {}).map(k => [k, LOGO_GROUPS[k] || k])].map(([k, l]) => `<button type="button" class="fchip sm${k ? '' : ' on'}" data-g="${esc(k)}">${esc(l)}</button>`).join('')}</div>
    <div class="lggrid"></div>
    <div class="small dim">${mode === 'many' ? t('Click several: each one joins the list.') : mode === 'text' ? t('It goes in written like :youtube: - the graphic draws the logo there.') : t('A click puts it in.')} ${t('Logos are trademarks of their owners: use them to name the products your video is about.')}</div>`;
  const grid = $('.lggrid', pop);
  const draw = () => {
    const L = logoFind(D.logos.filter(lg => !g || lg.group === g), q);
    grid.innerHTML = L.map(lg => { const has = !st || lg.variants[st];
      return `<button type="button" class="lgb${has ? '' : ' off'}" data-lg="${esc(lg.id)}" title="${has ? esc(lg.name) : ta('{name} - it has no such version: the usual one', {name: lg.name})}">${logoTile(lg, has ? st : '')}<span>${esc(lg.name)}</span></button>`; }).join('')
      || `<div class="small muted">${t('No logo fits those words.')}</div>`;
  };
  draw();
  const qi = $('.lgq', pop);
  qi.oninput = () => { q = qi.value; draw(); };
  $('.lgst', pop).onchange = e => { st = e.target.value; draw(); };
  $('.lgx', pop).onclick = () => pop.remove();
  $$('[data-g]', pop).forEach(b => b.onclick = () => { g = b.dataset.g; $$('[data-g]', pop).forEach(x => x.classList.toggle('on', x === b)); draw(); });
  grid.onclick = e => {
    const b = e.target.closest('[data-lg]');
    if (!b) return;
    const lg = D.logos.find(x => x.id === b.dataset.lg), val = st && lg.variants[st] ? `${lg.id}/${st}` : lg.id;
    if (mode === 'one') inp.value = val;
    else if (mode === 'many') { const L = inp.value.split('|').map(x => x.trim()).filter(Boolean); if (!L.includes(val)) L.push(val); inp.value = L.join('|'); }
    else {
      const tok = `:${val}:`, v = inp.value, how = inp.dataset.logohow, c = inp.dataset.caret === undefined || inp.dataset.caret === '' ? null : Number(inp.dataset.caret);
      if (how === 'swap' && (v.trim().length <= 3 || /^\s*:[a-z0-9/-]+:\s*$/i.test(v))) inp.value = tok;     // letters / an emoji / a logo -> this logo
      else if (how === 'first' && c == null) inp.value = tok + ' ' + v.replace(/^\s*:[a-z0-9/-]+:\s*/i, '');
      else if (c == null) inp.value = v ? `${v}${how === 'list' ? '|' : ' '}${tok}` : tok;
      else { const a = v.slice(0, c), z = v.slice(c);
        inp.value = a + (a && !/[\s|]$/.test(a) ? ' ' : '') + tok + (z && !/^[\s|:]/.test(z) ? ' ' : '') + z; }
      inp.dataset.caret = '';
    }
    inp.dispatchEvent(new Event('input', {bubbles: true}));
    inp.dispatchEvent(new Event('change', {bubbles: true}));
    if (mode !== 'many') pop.remove();
  };
  qi.focus();
}

function gsetInput(s) {
  const a = `data-set="${esc(s.id)}" data-type="${esc(s.type)}"`, v = s.value;
  if (isFontSet(s)) return `<select ${a} data-font>${fontOptions(s)}</select>${fontPreview(v)}`;
  if (isLogoSet(s)) return `<div class="lgin"><input type="text" ${a} value="${esc(v)}" placeholder="youtube, figma/mono…"><button type="button" class="btn sm" data-logopick="${/s$/.test(s.id) ? 'many' : 'one'}">${t('Pick a logo…')}</button></div>`;
  if (logoText(s)) return `<div class="lgin"><input type="text" ${a} value="${esc(v)}" data-logohow="${/\| between/.test(s.label) ? 'list' : /first/.test(s.label) ? 'first' : 'swap'}"><button type="button" class="btn sm" data-logopick="text" title="${ta('Put a logo of the library in this text')}">${t('+ Logo')}</button></div>`;
  if (s.type === 'color') return `<input type="color" ${a} value="${esc(v)}">`;
  if (s.type === 'boolean') return `<input type="checkbox" ${a} ${v ? 'checked' : ''}>`;
  // an option's label = the template's own words (overlay.json / index.html, English): shown in Spanish by key (_by_key)
  if (s.type === 'enum') return `<select ${a}>${(s.options || []).map(o => `<option value="${esc(o.value)}" ${o.value === v ? 'selected' : ''}>${esc(t(o.label ?? ''))}</option>`).join('')}</select>`;
  if (s.type === 'number') return `<input type="number" ${a} value="${esc(v)}"${s.min != null ? ` min="${s.min}"` : ''}${s.max != null ? ` max="${s.max}"` : ''} step="${s.step ?? 'any'}">`;
  return `<input type="text" ${a} value="${esc(v)}">`;
}
const gsetValue = i => i.dataset.type === 'boolean' ? i.checked : i.dataset.type === 'number' ? Number(i.value) : i.value;

// 0.4.6: a graphic drawn live in the page - its own HTML + GSAP in a frame, the settings as they are in the form (no
// HyperFrames, no render, no Claude): a change shows at once; the slider and ▶ move through its frames. The rendered
// picture stays the fallback when the graphic does not run here (no window.__timelines.main).
function livePreview(box, o, getValues) {
  const W = o.width || 1920, H = o.height || 1080, fps = o.fps || 25, N = Math.max(1, o.frames || 1);
  const sc = Math.min((box.clientWidth || 300) / W, 560 / H);
  const base = '/files/' + String(o.folder).replace(/\\/g, '/').split('/').map(encodeURIComponent).join('/') + '/';
  box.innerHTML = `<div class="glv" style="width:${Math.round(W * sc)}px;height:${Math.round(H * sc)}px"><iframe title="${ta('live preview')}" style="width:${W}px;height:${H}px;transform:scale(${sc})"></iframe></div>
    <div class="glvbar"><button class="btn sm" data-lvp title="${ta('play / pause')}">▶</button><input type="range" min="0" max="${N - 1}" value="0" data-lvr><span class="small mono" data-lvf></span></div>
    <div class="small muted">${t('Live preview: a change shows here at once, before you save or render.')}</div>`;
  const fr = $('iframe', box), rng = $('[data-lvr]', box), lab = $('[data-lvf]', box), play = $('[data-lvp]', box);
  let html = null, f = null, tl = null, raf = 0, t0 = 0, f0 = 0, timer = 0;
  const show = () => { lab.innerHTML = ftc(f, fps); rng.value = f; if (tl) try { tl.seek(f / fps, false); } catch (e) { /* the graphic's own error */ } };
  const stop = () => { cancelAnimationFrame(raf); raf = 0; play.textContent = '▶'; };
  const fail = () => { stop(); box.innerHTML = gthumb(o) + `<div class="small muted">${t('No live preview for this graphic - render it to see a change.')}</div>`; };
  fr.onload = () => {
    const w = fr.contentWindow;
    let tries = 0;
    const ready = () => {
      tl = w && w.__timelines && w.__timelines.main;
      // a look-aware template registers its timeline once its fonts are in (after load): wait up to 3 s for it
      if (!tl) return ++tries < 30 ? setTimeout(ready, 100) : fail();
      if (f == null) {                            // start where something shows: the first caption, else a third in
        const cue = w.CAPTIONS && w.CAPTIONS.cues && w.CAPTIONS.cues[0];
        f = cue ? Math.min(N - 1, Math.round((cue.f0 + cue.f1) / 2)) : Math.floor(N * 0.3);
      }
      show();
      if (w.document.fonts) w.document.fonts.ready.then(show);
    };
    ready();
  };
  const load = async () => {
    try { html = html || await (await fetch(base + 'index.html', {cache: 'no-store'})).text(); } catch (e) { return fail(); }
    const V0 = getValues(), vals = JSON.stringify(V0).replace(/</g, '\\u003c'), lgs = encodeURIComponent(logoIds(V0).join(','));
    fr.srcdoc = html.replace(/<head[^>]*>/i, m => `${m}<base href="${base}"><link rel="stylesheet" href="/fonts.css"><script src="/logos.js?b=${lgs}"><\/script><script>window.__hyperframes = {getVariables: () => (${vals})};<\/script>`);
  };
  rng.oninput = () => { stop(); f = Number(rng.value); show(); };
  play.onclick = () => {
    if (raf) return stop();
    if (f >= N - 1) f = 0;
    play.textContent = '❚❚'; t0 = performance.now(); f0 = f;
    const step = now => { f = Math.min(N - 1, f0 + Math.floor((now - t0) / 1000 * fps)); show(); if (f < N - 1) raf = requestAnimationFrame(step); else stop(); };
    raf = requestAnimationFrame(step);
  };
  load();
  return {refresh: () => { clearTimeout(timer); timer = setTimeout(load, 120); }, stop};
}

// 0.4.6: a graphic's ready-made looks (Classic | Clean box ...): one click sets them; captions made before their
// example had looks take its newest design first (the words and settings stay)
const lookRow = o => {
  const L = (o.looks || {}).looks || {}, ids = Object.keys(L);
  if (!ids.length) return '';
  const on = ids.find(k => L[k].active);
  return `<div class="glooks"><span class="small muted">${t('Look')}</span><div class="seg">${ids.map(k => `<button data-look="${esc(k)}" class="${k === on ? 'on' : ''}" title="${esc(t(L[k].what || ''))}">${esc(t(L[k].label ?? ''))}</button>`).join('')}</div>
    <span class="small muted">${o.looks.upgrade ? t('picking one also brings these captions to the newest design - your words and settings stay') : on ? '' : t('your own settings')}</span></div>`;
};
const gthumb = g => g.thumb ? `<img src="${fileUrl(g.thumb)}?v=${g.thumb_v}" alt="" loading="lazy">` : `<div class="muted small">${t('no picture yet')}</div>`;

function projGraphics(el, P) {
  const O = P.overlays || [];
  const top = `<div class="row sp" style="margin-bottom:12px"><div class="hint">${t('Titles, clocks, captions and other graphics, rendered as see-through clips for your video and for DaVinci Resolve. Change a setting, Save, then Render - it renders on this PC, no Claude and no tokens; the picture shows the result when it is done.')}</div>
    <button class="btn sm" id="gcap">${t('Captions…')}</button></div>`;
  if (!O.length) {
    el.innerHTML = top + `<div class="empty">${t('No graphics in this video yet. Make captions from a subtitle file, or ask Claude for a new one when you recreate a video.')}</div>`;
    captionsBtn(el, P);
    return;
  }
  // where the captions' words came from, as captions.load names it in overlay.json: "SRT file" / "VTT file" (by key)
  // or "lab transcript (<source>, <kind>)"
  const capWhat = w => { const m = /^lab transcript \((.*)\)$/.exec(w || ''); return m ? t('lab transcript ({how})', {how: m[1]}) : t(w || ''); };
  el.innerHTML = top + `
    <div class="col">${O.map(o => {
      const st = o.current ? `<span class="ok">${t('rendered ✓')}</span> <span class="muted">${esc(o.rendered_at)}</span>`
        : o.rendered ? `<span class="amber">${t('settings changed: render it again')}</span>` : `<span class="amber">${t('not rendered yet')}</span>`;
      return `<div class="gcard" data-g="${esc(o.name)}"><div class="gside"><div class="gthumb">${gthumb(o)}</div></div>
        <div><div class="row sp"><b style="font-size:15px">${esc(o.name)}</b><span class="small muted">${t('{frames} frames {range} · {width}×{height} · {fps} fps', {frames: o.frames, range: frange(0, o.frames - 1, o.fps), width: o.width, height: o.height, fps: o.fps})}</span></div>
          <div class="small" style="margin:4px 0 10px">${st} · ${o.used_in.length ? t('in the edit: {versions}', {versions: o.used_in.map(esc).join(', ')}) : `<span class="muted">${t('not in an edit version yet')}</span>`}</div>
          ${o.captions ? `<div class="small" style="margin:-4px 0 10px">${t('Captions: {lines}, {words} from the {what}', {lines: plural(o.captions.cues, 'line'), words: plural(o.captions.words, 'word'), what: esc(capWhat(o.captions.what))})}${o.captions.estimated ? ` · <span class="amber">${t('word times estimated (the file has one time per line)')}</span>` : ''}</div>` : ''}
          ${o.problem ? `<div class="bad small">${esc(o.problem)}</div>` : ''}
          ${lookRow(o)}
          ${o.settings.length ? `<div class="gset">${o.settings.map(s => `<label title="${esc(s.id)}">${esc(t(s.label || s.id || ''))}</label><div>${gsetInput(s)}</div>`).join('')}</div>`
            : `<div class="muted small">${t('This graphic has no settings yet (Claude can add them: text, colours, timing).')}</div>`}
          <div class="row" style="margin-top:10px">${o.settings.length ? `<button class="btn sm" data-gsave disabled>${t('Save settings')}</button>` : ''}
            <button class="btn sm ${o.current ? '' : 'pri'}" data-grender>${t('Render')}</button>
            <button class="btn sm" data-glib ${o.current ? '' : `disabled title="${ta('render it first')}"`}>${t('Save to library…')}</button>
            ${o.srt ? `<button class="btn sm" data-open="${esc(o.srt)}" data-reveal title="${ta("the same captions as subtitles: import it into DaVinci Resolve's subtitle track and correct them there")}">${t('Subtitles for Resolve (.srt)')}</button>` : ''}
            <button class="btn sm" data-open="${esc(o.folder)}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button></div>
          <div class="row" style="margin-top:8px"><span class="small muted">DaVinci Resolve:</span>
            <button class="btn sm" data-gclip ${o.rendered ? '' : 'disabled'} title="${ta("a numbered copy of this render to drag into Resolve's media pool - Resolve locks the files it uses, so the graphic itself stays free to render again")}">${t('Clip for Resolve (.mov)')}</button>
            <button class="btn sm" data-gswap ${o.rendered ? '' : 'disabled'} title="${ta('after a new render: replaces this graphic in the project open in Resolve - position, length, size, opacity and blend mode on your timeline stay')}">${t('Swap in DaVinci Resolve')}</button></div>
          <pre class="log" hidden></pre></div></div>`;
    }).join('')}</div>`;
  captionsBtn(el, P);
  $$('.gcard', el).forEach(card => {
    const name = card.dataset.g, pre = $('pre.log', card), save = $('[data-gsave]', card);
    const o = O.find(x => x.name === name);
    const formValues = () => { const v = {}; o.settings.forEach(s => { v[s.id] = s.value; }); $$('[data-set]', card).forEach(i => { v[i.dataset.set] = gsetValue(i); }); return v; };
    const live = o.settings.length && !o.problem ? livePreview($('.gside', card), o, formValues) : null;
    if (live) CLEAN.push(live.stop);
    $$('[data-set]', card).forEach(i => { i.oninput = i.onchange = () => { if (save) save.disabled = false; if (live) live.refresh(); }; });
    $$('[data-look]', card).forEach(b => b.onclick = async () => {
      try {
        await api(`/api/project/${encodeURIComponent(P.name)}/overlay`, {overlay: name, preset: b.dataset.look});
        toast(t('{name}: the look “{look}” - render it to use it in the video', {name, look: b.textContent}), 'ok'); route();
      } catch (e) { toast(e.message, 'err'); }
    });
    if (save) save.onclick = async () => {
      const values = {};
      $$('[data-set]', card).forEach(i => { values[i.dataset.set] = gsetValue(i); });
      try { await api(`/api/project/${encodeURIComponent(P.name)}/overlay`, {overlay: name, values}); toast(t('{name}: settings saved - render it to see them', {name}), 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    };
    const run = async (kind, args, btn, then) => {
      if (save && !save.disabled) { toast(t('Save the settings first'), 'err'); return; }
      const j = await startJob(kind, {project: P.name, overlay: name, ...args}, false);
      if (!j) return;
      btn.disabled = true; pre.hidden = false; pre.textContent = '';
      followJob(j.id, pre, jj => {
        toast(`${jj.title}: ${t(jj.status)}`, jj.status === 'done' ? 'ok' : 'err');
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
    $('[data-glib]', card).onclick = e => modal(`<h2>${t('Save “{name}” to the graphics library', {name: esc(name)})}</h2>
      <div class="small muted">${t('The library keeps its HTML, its settings as they are now and the rendered clip. Every video can use it (Library → Graphics), and you can drag the clip into a Power Bin in DaVinci Resolve.')}</div>
      <div class="row" style="margin-top:12px"><label>${t('Name')} <input id="glname" value="${esc(name)}" style="width:220px"></label>
        <label class="chk"><input type="checkbox" id="glrep"> ${t('replace one with that name')}</label></div>
      <div class="row" style="margin-top:12px"><button class="btn pri" id="glgo">${t('Save to library')}</button></div>`, m => {
      $('#glgo', m).onclick = () => { const nm = $('#glname', m).value.trim(), rep = $('#glrep', m).checked; closeModal(); run('overlay_save', {name: nm, replace: rep}, e.target); };
    });
  });
}

function captionsBtn(el, P) {
  // captions from a video's own words (speech to text, faster-whisper) or from a subtitle file (.srt / .vtt)
  const b = $('#gcap', el);
  if (!b) return;
  const SPc = P.speech || {}, media = P.media || [];
  b.onclick = () => modal(`<h2>${t('Captions')}</h2>
    <div class="small muted">${t("Styled captions timed to the words (change the style afterwards on this tab) and the same captions as an .srt for DaVinci Resolve's subtitle track. Your files are only read.")}</div>
    <div class="col" style="margin-top:12px">
      <label class="chk"><input type="radio" name="gcsrc" value="video" ${SPc.available && media.length ? 'checked' : 'disabled'}> ${t('<b>From the words in a video</b> (speech to text, on this PC)')}</label>
      <div class="col" id="gcvid" style="margin-left:24px">${SPc.available ? (media.length ? `
        <label>${t('Video')} <select id="gcm">${media.map(m => `<option value="${esc(m.path)}">${esc(m.label)}</option>`).join('')}</select></label>
        <div class="hint">${t('Pick the render of your edit, so the captions follow its cuts - or one of your clips.')}</div>
        <label>${t('Names and words it might not know')} <input id="gcnames" placeholder="${ta('e.g. MotionLab, 4AM, Nemzzz, DaVinci Resolve')}"></label>
        <label>${t('Model')} <select id="gcmod"><option value="small">${t('small - the most accurate')}</option><option value="base">${t('base - lighter, for slow laptops (ignores the names)')}</option></select></label>`
        : `<div class="hint">${t('This video has no render or clip yet.')}</div>`)
        : `<div class="hint">${t('Speech to text is not installed yet: <a href="#/settings">Settings → Programs → Speech to text → Install</a> (one time, about 520 MB).')}</div>`}</div>
      <label class="chk"><input type="radio" name="gcsrc" value="file" ${SPc.available && media.length ? '' : 'checked'} ${P.plans.length ? '' : 'disabled'}> ${P.plans.length ? t("<b>From a subtitle file</b> (.srt / .vtt from YouTube, CapCut, Resolve's “Create Subtitles from Audio”)")
        : t("<b>From a subtitle file</b> (.srt / .vtt from YouTube, CapCut, Resolve's “Create Subtitles from Audio”) - needs an edit version (its size, rate and length)")}</label>
      <div style="margin-left:24px"><input id="gcf" placeholder="${ta('C:\\...\\my video.srt')}"></div>
      <label>${t('Name')} <input id="gcn" value="captions" style="width:200px"></label></div>
    <div class="hint" style="margin-top:6px">${t('The same name again replaces the words of those captions and keeps their style.')}</div>
    <div class="row" style="margin-top:12px"><button class="btn pri" id="gcgo">${t('Make the captions')}</button><span id="gcmsg" class="small"></span></div><pre class="log" hidden></pre>`, m => {
    $('#gcgo', m).onclick = async () => {
      const go = $('#gcgo', m), src = ($('input[name=gcsrc]:checked', m) || {}).value;
      if (!src) { toast(t('Pick where the words come from'), 'err'); return; }
      const args = {project: P.name, name: $('#gcn', m).value.trim()};
      if (src === 'video') Object.assign(args, {file: $('#gcm', m).value, names: $('#gcnames', m).value.trim(), model: $('#gcmod', m).value});
      else args.file = $('#gcf', m).value.trim();
      const j = await startJob('overlay_captions', args, false);
      if (!j) return;
      go.disabled = true; const pre = $('pre.log', m); pre.hidden = false;
      followJob(j.id, pre, jj => {
        if (jj.status === 'done') { closeModal(); route(); }
        else { $('#gcmsg', m).innerHTML = `<span class="bad">${t('did not work - see the log')}</span>`; go.disabled = false; }
      });
    };
  });
}

function projTiming(el, P) {
  const what = `<div class="hint" style="margin-bottom:12px">${t('For an exact copy of a reference: does your render change picture on the same frames as the reference - every cut, flash and pop-in Claude picked from it? ✓ = on the same frame, ✗ = missed (Claude fixes those). The small number = how much the picture changed there (0-255).')}</div>`;
  if (!P.verifies.length) { el.innerHTML = what + `<div class="empty">${t('No timing check for this video - Claude makes one when it copies a reference frame by frame.')}</div>`; return; }
  const fps = (P.plans[0] || {}).fps || 25, keys = P.verifies[0].rows;
  el.innerHTML = `${what}<div class="panel"><h2>${t("Does the render change picture on the reference's key frames?")}</h2>
    <div class="row" style="margin-bottom:10px">${P.verifies.map(v => `<div class="stat"><div class="n">${v.hits}<span class="muted" style="font-size:16px"> / ${v.keys}</span></div>
      <div class="l">${t('{name} · brightness correlation {corr}', {name: esc(v.name), corr: numStr(v.luma_corr)})}</div>
      <button class="btn sm" style="margin-top:6px" data-run="${esc(v.name)}">${t('Run again')}</button></div>`).join('')}</div>
    <table class="t"><thead><tr><th>${t('Frame')}</th><th>${t('Timecode')}</th><th>${t('What happens in the reference')}</th>${P.verifies.map(v => `<th>${esc(v.name)}</th>`).join('')}</tr></thead><tbody>
    ${keys.map((k, i) => `<tr><td class="fr">f${k.frame}</td><td class="tc">${tc(k.frame, fps)}</td><td>${esc(k.what)}</td>
      ${P.verifies.map(v => { const r = v.rows[i] || {}; return `<td>${r.our_hit ? `<span class="ok">${t('✓ same frame')}</span>` : `<span class="bad">${t('✗ missed')}</span>`} <span class="small dim">${numStr(r.our_change ?? '')}</span></td>`; }).join('')}</tr>`).join('')}
    </tbody></table></div>`;
  $$('[data-run]', el).forEach(b => b.onclick = () => startJob('verify_timing', {project: P.name, render: b.dataset.run}));
}

function projResolve(el, P) {
  const what = `<div class="hint" style="margin-bottom:12px">${t('The same edit as a DaVinci Resolve project you can keep editing by hand. <b>Check-up</b> = is the timeline still what the lab built; <b>What did I change by hand?</b> = your changes in Resolve, so the next version keeps them; <b>Effects in this rebuild</b> = tick the ones to keep in your library (Claude saves each as a Fusion effect for every later video).')}</div>`;
  if (!P.resolve.length) { el.innerHTML = what + `<div class="empty">${t('No DaVinci Resolve version of this video yet - tick "then build it as a DaVinci Resolve project" in New edit.')}</div>`; return; }
  const fps = (P.plans[0] || {}).fps || 25;
  const render = P.renders.find(r => r.kind === 'resolve') || P.renders[0];
  const picks = Object.assign({}, P.library_picks || {});
  const savePicks = debounce(async () => {
    try { await api(`/api/project/${encodeURIComponent(P.name)}/picks`, {picks}); $('#psaved').textContent = t('saved ✓'); }
    catch (e) { toast(e.message, 'err'); }
  }, 400);
  el.innerHTML = what + P.resolve.map((R, ri) => {
    const d = R.drift, f = d ? d.findings : [];
    const byUnit = {};
    f.forEach(x => (byUnit[x.unit] = byUnit[x.unit] || []).push(x));
    return `<div class="grid g2"><div class="panel"><h2>${t('Timeline')} <span class="amber">${esc(R.timeline)}</span></h2>
      <div class="kv"><b>${t('Project')}</b><span>${esc(R.project)} (Resolve)</span><b>${t('Built from')}</b><span>${t('{units} pieces: {clips} Edit-page clips, {comps} Fusion comps, {luts} grade LUTs, {tracks} video tracks', {units: R.units, clips: R.clips, comps: R.comps, luts: R.luts, tracks: R.tracks})}</span>
        <b>${t('Backup')}</b><span>${R.drp ? `<a href="#" data-open="${esc(R.drp)}" data-reveal>${esc(R.drp.split('/').pop())}</a>` : '–'}</span>
        <b>${t('Report')}</b><span>${R.report ? `<a href="#" class="showrep" data-rep="${esc(R.report)}">${t('option 2 report')}</a>` : '–'}</span></div>
      <div class="row" style="margin-top:12px"><button class="btn" data-job="resolve_doctor">${t('Check-up')}</button>
        <button class="btn" data-job="resolve_diff">${t('What did I change by hand?')}</button><span class="hint">${t('needs Resolve running')}</span></div>
      <pre class="log" id="rlog${ri}" hidden></pre></div>
      <div class="panel"><h2>${t('Changed by hand in Resolve')}</h2>${d ? `<div class="small muted" style="margin-bottom:8px">${t('last checked {when}', {when: esc(d.checked)})}</div>
        ${f.length ? Object.entries(byUnit).map(([u, xs]) => `<div style="margin-bottom:10px"><b class="amber">${esc(u)}</b>
          <span class="small muted">V${xs[0].track} · ${frange(xs[0].start, xs[0].end, fps)}</span>
          <ul class="small" style="margin:4px 0">${xs.map(x => `<li>${esc(x.what)}: <span class="muted">${t('lab')}</span> ${esc(x.lab)} <span class="muted">${t('→ now')}</span> <b>${esc(x.live)}</b></li>`).join('')}</ul></div>`).join('')
          : `<div class="ok">${t('Nothing: the timeline is exactly what the lab built.')}</div>`}
        ${R.edits.length ? `<div class="small muted">${t('Your edited comps are kept as text: {files}', {files: R.edits.map(p => `<a href="#" data-open="${esc(p)}" data-reveal>${esc(p.split('/').pop())}</a>`).join(', ')})}</div>` : ''}`
        : `<div class="muted">${t('Not checked yet: click “What did I change by hand?”.')}</div>`}</div></div>
      <div class="row sp" style="margin:18px 0 8px"><div><h2 style="margin:0">${t('Effects in this rebuild')}</h2>
        <div class="hint">${t('Tick the effects you want saved in your library (a Fusion macro + a recipe each). Claude does the saving in Resolve; this is your list.')}</div></div>
        <span id="psaved" class="small muted">${P.picks_updated ? t('saved {when}', {when: esc(P.picks_updated)}) : ''}</span></div>
      <div class="col">${R.effects.map(g => {
        const u0 = g.units[0], mid = Math.round((u0.start + u0.end) / 2), pk = picks[g.title] || {};
        return `<div class="fx ${pk.pick ? 'picked' : ''}" data-fx="${esc(g.title)}">
          ${render ? `<img loading="lazy" src="/api/thumb?video=${encodeURIComponent(render.rel)}&f=${mid}&fps=${fps}" title="${ta('f{frame} ({tc}) in {render}', {frame: mid, tc: tc(mid, fps), render: render.name})}">` : '<div></div>'}
          <div><div class="row sp"><b style="font-size:15px">${esc(t(g.title))}</b><label class="chk"><input type="checkbox" data-pick ${pk.pick ? 'checked' : ''}> ${t('save to library')}</label></div>
          <div class="small" style="margin:3px 0 6px">${esc(t(g.what || ''))}</div>
          <div class="units">${g.units.map(u => `${esc(u.name)} ${u.track ? `V${u.track}` : ''} ${frange(u.start, u.end, fps)}`).join(' · ')}</div>
          <textarea data-note rows="2" placeholder="${ta('Anything to change before saving? e.g. “sparks need bright heads”')}" style="margin-top:8px">${esc(pk.note || '')}</textarea></div></div>`;
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
      toast(`${jj.title}: ${t(jj.status)}`, jj.status === 'done' ? 'ok' : 'err');
      if (b.dataset.job === 'resolve_diff') api('/api/project/' + encodeURIComponent(P.name)).then(NP => { Object.assign(P, NP); });
    });
  });
  $$('.fx', el).forEach(box => {
    const k = box.dataset.fx;
    $('[data-pick]', box).onchange = e => { (picks[k] = picks[k] || {}).pick = e.target.checked; box.classList.toggle('picked', e.target.checked); $('#psaved').textContent = t('saving…'); savePicks(); };
    $('[data-note]', box).oninput = e => { (picks[k] = picks[k] || {}).note = e.target.value; $('#psaved').textContent = t('saving…'); savePicks(); };
  });
  $$('.fx img', el).forEach(img => { img.onclick = () => { const lb = $('#lightbox'); $('img', lb).src = img.src; $('.lbcap', lb).textContent = img.title; lb.hidden = false; }; });
  $$('.showrep', el).forEach(a => a.onclick = async e => {
    e.preventDefault();
    const box = $('#repbox'); const rep = await api('/api/text?path=' + encodeURIComponent(a.dataset.rep));
    box.innerHTML = md(rep.text); box.hidden = false; box.scrollIntoView({behavior: 'smooth'});
  });
}

// ============================================================================================ Claude's memory
// (0.4, the user: "once analysed it is stored in the database / mind of Claude, so when I edit or generate it can use
// those effects and that knowledge") - one place: every analysed video's style, every effect seen and how it was made,
// the lessons, the saved graphics and effects, sharing with friends; one search over all of it. Claude reads the same
// as knowledge\local\memory.md (knowledge.memory_index) before an edit or a prompt.
// 2026-10-18 (the user: "make the share knowledge a more distinct section in the claudes memory"): Share with friends
// became Shared knowledge (#/memory/shared; #/memory/learned and #/knowledge lead there) - its own icon and count.
// 2026-10-22 (the user: "1) Graphics and saved effects 2) Effects 3) Videos - I dont understand what those sections do, I
// have never used and when i go inside is just a bunch of text AI-written and for AI ... u can just remove those
// sections"): Overview, Lessons, Shared knowledge. Claude still reads all of it (memory.md); the saved graphics and
// Resolve effects stay in library\.
const MEM_TABS = [['overview', t('Overview')], ['lessons', t('Lessons')], ['shared', t('Shared knowledge')]];
async function pageMemory(main, tab = 'overview') {
  if (!MEM_TABS.some(([k]) => k === tab)) tab = 'overview';
  main.innerHTML = `<div class="head"><div><h1>${t("Claude's memory")}</h1><div class="sub">${t('What Claude learned from your videos and your ratings - it reads this before it edits or generates for you.')}</div></div></div>
    <div class="tabs">${MEM_TABS.map(([k, l]) => `<a href="#/memory/${k}" class="${k === tab ? 'on' : ''}${k === 'shared' ? ' tsh' : ''}">${k === 'shared'
      ? `<svg class="i"><use href="#i-shared"/></svg>${l}<b class="shn" id="shtabn" hidden></b>` : l}</a>`).join('')}</div>
    <div id="memtab"></div>`;
  const el = $('#memtab', main);
  if (tab === 'shared') return memShared(el);
  const M = await api('/api/memory');
  memTabCount(M);
  return ({overview: memOverview, lessons: memLessons})[tab](el, M);
}
// the Shared knowledge tab's count: what came from friends (their videos + their lessons waiting for a review)
function memTabCount(M, K) {
  const b = $('#shtabn'); if (!b) return;
  const n = K ? K.friends.reduce((a, g) => a + g.cards.length + g.incoming.reduce((s, x) => s + x.lessons.length, 0), 0)
    : (M.stats.friends || 0) + Object.values(M.stats.incoming || {}).reduce((a, x) => a + x, 0);
  b.hidden = !n; b.textContent = n;
  b.closest('a').title = n ? t('{things} your friends shared - their videos and lessons', {things: plural(n, 'thing')}) : '';
}
const lessonText = t => String(t || '').replace(/^- \[[^\]]+\]\s*/, '');
// 0.4.2: the user's ratings of all their videos (How did it turn out?) as rules for every new video - a part rated bad
// once stays a default (knowledge.ratings / ratings_lines; memory.md starts with the same rules)
const RKIND = {bad: ['bad', t('Rule for every new video')], ok: ['amber', t('Could be better')], good: ['ok', t('Keep doing it')]};
function memRules(M) {
  const R = M.ratings || {}, parts = R.parts || [];
  const RW = {bad: t('bad|rating'), ok: t('OK|rating'), good: t('good|rating')};       // the rating's word in a count
  const cnt = c => ['bad', 'ok', 'good'].filter(r => c[r]).map(r => `${RW[r]} ${c[r]}×`).join(' · ');
  // a rule as knowledge.ratings words it: a fixed text (by key), or a bad part's rule + "(it worked: rated good in <video>)"
  const rule = r => { const m = /^(.*) \(it worked: rated good in (.+)\)$/.exec(r || '');
    return m ? t('{rule} (it worked: rated good in {video})', {rule: t(m[1]), video: m[2]}) : t(r || ''); };
  return `<div class="panel mrules" style="margin-top:14px"><div class="row sp"><h2><span class="mstar" aria-hidden="true">📌</span>${t('Your ratings → rules for every new video')}<span class="mrimp">${t('Claude reads these first')}</span></h2>
      <span class="small muted">${R.videos ? t('from {videos}', {videos: plural(R.videos, 'rated video')}) : ''}</span></div>
    ${parts.length ? `<div class="small muted" style="margin-bottom:8px">${t('What you rated in <b>How did it turn out?</b> (Editor → a video). A part you rated bad once stays a rule for every later edit and generated video - Claude reads these first.')}</div>
      ${parts.filter(x => x.kind === 'bad' || x.kind === 'ok' && (x.notes || []).length).map(x => `<div class="mrule"><span class="mrk ${RKIND[x.kind][0]}">${RKIND[x.kind][1]}</span>
        <div><b>${esc(t(x.label || ''))}</b> <span class="small muted">${t('rated {counts}', {counts: cnt(x.counts || {})})}</span>
        <div class="small">→ ${esc(rule(x.rule))}</div>${(x.notes || []).map(q => `<div class="small muted">“${esc(q.note)}” - ${esc(q.video)}</div>`).join('')}</div></div>`).join('')}
      ${[['ok', t('Fine, not great')], ['good', t('Keep doing it')]].map(([k, l]) => { const xs = parts.filter(x => x.kind === k && !(k === 'ok' && (x.notes || []).length));
        return xs.length ? `<div class="mrule"><span class="mrk ${RKIND[k][0]}">${l}</span><div class="small">${xs.map(x => `<b>${esc(t(x.label || ''))}</b> <span class="muted">(${cnt(x.counts || {})})</span>`).join(' · ')}</div></div>` : ''; }).join('')}`
      : `<div class="small muted">${t('Nothing rated yet. When a video of yours is done, open it in the <a href="#/edit">Editor</a> and tell Claude how it turned out (sound, colour, graphics…): a part you rate bad becomes a rule for every new video.')}</div>`}</div>`;
}
function memOverview(el, M) {
  const S = M.stats, MK = (M.lessons || {}).making || {shared: [], local: []};
  const mk = (MK.shared || []).length + (MK.local || []).length;
  const tile = (n, l, href, tip = '') => `<a class="stat card" href="${href}" title="${esc(tip)}"><div class="n">${n}</div><div class="l">${l}</div></a>`;
  const waiting = Object.values(S.incoming || {}).reduce((a, x) => a + x, 0), authors = S.authors || [];
  // what came from friends, as one sentence (the server names an unnamed friend "a friend")
  const who = esc(authors.map(a => a === 'a friend' ? t('a friend') : a).join(', ') || t('friends'));
  const fv = {videos: plural(S.friends || 0, 'video'), lessons: plural(waiting, 'lesson'), authors: who};
  const fromFriends = S.friends && waiting ? t('{videos} and {lessons} waiting for a review from {authors}', fv)
    : S.friends ? t('{videos} from {authors}', fv) : waiting ? t('{lessons} waiting for a review from {authors}', fv) : t('Nothing from friends yet');
  el.innerHTML = `<div class="mstats">
      ${tile(S.friends ? S.mine : S.videos, t('videos analysed'), '#/analyze')}
      ${tile(S.lessons + mk, t('lessons'), '#/memory/lessons', mk ? t('{analysing} on analysing, {making} on making videos', {analysing: S.lessons, making: mk}) : '')}
      ${tile(M.prompts || 0, t('prompts'), '#/prompts')}
      <a class="stat card shtile" href="#/memory/shared"><svg class="ic"><use href="#i-shared"/></svg><div class="grow"><b>${t('Shared knowledge')}</b>
        <div class="small muted">${t('{what} · what you share with them, and what you keep on this PC', {what: fromFriends})}</div></div><span class="muted">→</span></a></div>
    ${memRules(M)}
    <div class="panel" style="margin-top:14px"><h2>${t('How Claude uses it')}</h2><ul class="small mhow">
        <li>${t("<b>When you edit</b> your clips like a video, Claude reads that video's style - rhythm, the hook, captions, signature effects, transitions, colour - and how its effects were made.")}</li>
        <li>${t('<b>When you generate</b>, Claude writes the prompts in the style of the videos you name, with the structure of your best-rated prompts.')}</li>
        <li>${t('<b>When it analyses</b> a new video, the lessons from your verdicts decide how effects are judged.')}</li></ul>
        <div class="row" style="margin-top:8px"><button class="btn sm" data-open="${esc((M.memory_md || '').replace(/\\/g, '/'))}">${t('What Claude reads (memory.md)')}</button><button class="btn sm ghost" id="mreb">${t('Rebuild it')}</button></div></div>
    ${M.videos.length ? '' : emptyHero('memory', t('Claude learns from the videos you analyse'), t("Analyse a video you like - its style, effects and Claude's breakdown land here, ready for your edits."), `<a class="btn pri big" href="#/analyze">${t('Analyze a video')}</a>`)}`;
  $('#mreb', el).onclick = async () => { try { await api('/api/knowledge/summary', {}); toast(t('Rebuilt what Claude reads'), 'ok'); } catch (e) { toast(e.message, 'err'); } };
}
// a lesson; a reviewed rule a friend shared ("from <author> <id>" in its note) carries the shared chip
const lessonItem = x => `<div class="panel mles"><span class="tag">${esc(x.id)}</span>${x.from ? ' ' + sharedChip(x.from) : ''} ${esc(lessonText(x.text))}</div>`;
function memLessons(el, M) {
  const L = M.lessons, MK = L.making || {shared: [], local: []}, item = lessonItem;
  const inc = k => (L.incoming || []).filter(x => (x.kind || 'analysis') === k);
  // friends' lessons waiting for a review, per friend (no file names): "from tekeo · 11 lessons · 16 Oct"
  const incLine = xs => xs.length ? `<h3>${t('From friends, waiting for a review')}</h3>${xs.map(x => `<div class="small mlinc">${sharedChip(x.author, x.when)}
      ${plural(x.lessons, 'lesson')}${x.when ? ` <span class="dim">· ${t('shared {day}', {day: esc(shDay(x.when))})}</span>` : ''} <span class="dim">· ${t('not rules yet - <a href="#/memory/shared">see them</a>')}</span></div>`).join('')}` : '';
  // the two kinds (0.4.2): analysing videos (L###, lessons.md of /analyze-reference) and making videos (M###, /recreate-video)
  el.innerHTML = `<div class="grid g2 mlkinds"><div>
      <h2>${t('Analysing videos')}</h2><div class="small muted" style="margin-bottom:10px">${t("How Claude judges and names effects - written from your verdicts and feedback (and your friends', after a review).")}</div>
      <h3>${t('From this PC ({n})', {n: L.local.length})}</h3>${L.local.map(item).join('') || `<div class="small dim">${t('None yet - give verdicts on a video, then Send it to Claude.')}</div>`}
      <h3><svg class="i shic"><use href="#i-shared"/></svg>${t('Shared rules ({n})', {n: L.shared.length})}</h3>${L.shared.map(item).join('') || `<div class="small dim">${t('None.|lessons')}</div>`}
      ${incLine(inc('analysis'))}</div>
    <div><h2>${t('Making videos')}</h2><div class="small muted" style="margin-bottom:10px">${t('How Claude edits and generates - learned from rebuilding videos and from how they turned out. Read before every edit and generated video.')}</div>
      <h3>${t('From this PC ({n})', {n: (MK.local || []).length})}</h3>${(MK.local || []).map(item).join('') || `<div class="small dim">${t('None yet - they come from your ratings and notes on your videos.')}</div>`}
      <h3><svg class="i shic"><use href="#i-shared"/></svg>${t('Shared rules ({n})', {n: (MK.shared || []).length})}</h3>${(MK.shared || []).map(item).join('') || `<div class="small dim">${t('None.|lessons')}</div>`}
      ${incLine(inc('making'))}</div></div>
    ${(L.incoming || []).length ? `<div class="row" style="margin-top:12px">${claudeBtn('Review the incoming lessons in knowledge\\incoming\\ (see Reviewing incoming lessons in the analyze-reference skill; the *-making.md files are lessons on making videos for .claude\\skills\\recreate-video\\lessons.md) and merge the good ones', t('Review them in Claude Code'), 'lessons')}</div>` : ''}`;
}
// ============================================================================================ prompts (0.4)
// the prompt library: proven prompts per kind, split into their structure; Claude writes new ones like them
// (/write-prompt). One file per prompt in knowledge\local\prompts\ - the ratings live there too.
const PSRC = {tested: t('tested by you'), creator: t('creator'), written: t('written by Claude')};
// what a prompt is for (its tags): the page filters by it, /write-prompt copies examples made for the same thing first
const PURPOSES = ['vlog', 'talking head', 'music video', 'ad / product', 'cinematic b-roll', 'transitions', 'sfx',
                  'captions', 'motion graphics', 'colour', 'tutorial', 'storytelling'];
const ASPECTS = [['sound', t('Sound & music')], ['sfx', t('SFX')], ['colour', t('Colour')], ['captions', t('Captions')],
                 ['graphics', t('Motion graphics')], ['effects', t('Effects & transitions')], ['pacing', t('Pacing & cuts')], ['packaging', t('Title & thumbnail')],
                 ['overall', t('Overall')]];
const KSHORT = {shot: t('Video shot'), image: t('Image'), hook: t('Hook'), script: t('Talking script'), brief: t('Brief for Claude'), title: t('Title & thumbnail')};
// the parts Claude checks (prompts.SLOTS), in plain words
const SLOT_LABEL = {references: t('Uploads (what each is for)'), keep: t('What stays the same'), change: t('What changes'), subject: t('Subject'),
  action: t('Action'), setting: t('Setting|place'), camera: t('Camera'), lens: t('Lens'), light: t('Light|lighting'), look: 'Look', motion: t('Motion'),
  beats: t('Timing (beats)'), audio: t('Sound'), 'length / aspect': t('Length & format'), avoid: t('What to avoid'), composition: t('Composition'),
  materials: t('Materials'), pattern: t('Kind of hook'), 'opening line': t('First line|spoken'), 'on screen': t('On screen'), promise: t('Promise'),
  hook: t('Hook'), problem: t('Problem'), points: t('Main points'), 're-hooks': t('Re-hooks'), proof: t('Proof'), payoff: t('Payoff'),
  'call to action': t('Call to action'),
  'format & length': t('Long or short, length & format'), 'story & hook': t('Story & hook'), 'feel / style': t('Feel & style reference'),
  footage: t('Footage & b-roll'), 'order & structure': t('Order & structure'), 'pacing & cuts': t('Pacing & cuts'), colour: t('Colour grading'),
  music: t('Music'), sfx: 'SFX', 'motion graphics': t('Motion graphics'), transitions: t('Transitions'), 'captions & text': t('Captions & text'),
  effects: t('Effects (zooms, speed ramps, shake)'), 'voice & audio': t('Voice & audio clean-up'), ending: t('Ending & call to action'),
  deliverable: t('Where it ends up'), 'questions first': t('Questions to ask you first'),
  titles: t('Titles'), thumbnail: t('Thumbnail ideas'), 'words on it': t('Words on the thumbnail'), 'shot to film': t('Shot to film'), colours: t('Colours')};
const slotLabel = s => SLOT_LABEL[s] || (s ? s[0].toUpperCase() + s.slice(1) : '');
const STAT = {clear: ['✓', t('clear|part')], vague: ['~', t('vague|part')], missing: ['✗', t('missing|part')]};
// a brief's check in the order a video is made (prompts.SLOTS["brief"]): the plan, the edit, sound, look, finish
const BRIEF_GROUPS = [[t('The plan'), ['format & length', 'story & hook', 'feel / style', 'footage', 'order & structure']],
  [t('The edit'), ['pacing & cuts', 'transitions', 'effects']], [t('Sound'), ['voice & audio', 'music', 'sfx']],
  [t('Look & text'), ['colour', 'motion graphics', 'captions & text']], [t('Finish|steps'), ['ending', 'deliverable', 'questions first']]];
const RUN = {brief: t('Run it - make the video'), script: t('Film it'), hook: t('Use current version in a video'), shot: t('Run it on the site'), image: t('Run it on the site'),
  title: t('Use a title for a video')};
const pstars = n => `<span class="stars" title="${ta("Claude's review of the prompt: {n} of 5", {n})}">${'★'.repeat(n)}<span class="off">${'★'.repeat(5 - n)}</span></span>`;
const ptitle = p => p.title || (p.title_auto === 'Untitled prompt' ? t('Untitled prompt') : p.title_auto) || p.text.trim().split(/\s+/).slice(0, 8).join(' ') + (p.text.trim().split(/\s+/).length > 8 ? '…' : '');
// what a prompt needs, in two words: the tool / model, and what you bring (your clips, a photo, you on camera)
// a site or app outside MotionLab that the prompt runs on (an account, credits, a setup): the "Needs another tool" filter
const TOOLS = /higgsfield|invideo|kling|runway|pika|luma|hailuo|minimax|sora|veo|midjourney|nano ?banana|gpt[- ]?image|chatgpt|dall-?e|seedance|flux|leonardo|ideogram|krea|capcut|hedra|heygen|elevenlabs|suno|wan ?2/i;
function ptool(p) {
  if (p.model && TOOLS.test(p.model)) return p.model;
  if (p.kind !== 'shot' && p.kind !== 'image') return '';
  if (p.model) return p.model;
  const m = (p.text || '').match(TOOLS);
  return m ? m[0][0].toUpperCase() + m[0].slice(1) : p.kind === 'shot' ? t('an AI video tool') : t('an AI image tool');
}
const ptoolChip = p => { const tool = ptool(p);
  return tool ? `<span class="pgneed pgtool" title="${ta('Runs on {tool} - a separate tool (an account, credits or a setup)', {tool})}">${esc(tool)}</span>` : ''; };
// what you bring: your clips, a photo, you on camera - or nothing (text only)
function pneeds(p) {
  const txt = p.text || '', refs = ((p.structure || []).find(x => x.slot === 'references') || {}).text || '';
  const out = [];
  if (p.kind === 'brief') out.push(t('your clips'));
  else if (p.kind === 'script' || p.kind === 'hook') out.push(t('you on camera'));
  else if (p.kind === 'title') out.push(t('shots to film'));
  else {
    const both = txt + ' ' + refs;
    if (/@video\d*|source clip|tripod clip|your (clip|video|footage)|upload(ed)? (a |your )?(clip|video)|video[- ]to[- ]video/i.test(both)) out.push(t('your clip'));
    else if (/@image\d*|reference (image|photo|picture)|your (photo|picture|selfie)|upload(ed)? (a |your )?(photo|image|picture)|image[- ]to[- ]video|start frame/i.test(both)) out.push(t('your photo'));
    else out.push(t('text only'));
  }
  return out;
}
const pcategory = p => (p.tags || []).find(x => PURPOSES.includes(x)) || (p.tags || [])[0] || '';
const pcatWord = c => PURPOSES.includes(c) ? t(c) : c;    // shown: a purpose in the app's language, the user's own tag as typed
const pexUrl = (R, f) => fileUrl(`${R.folder}/examples/${f}`);
const pexMedia = (R, f, cls = '') => /\.(mp4|webm)$/i.test(f)
  ? `<video class="${cls}" src="${pexUrl(R, f)}#t=0.5" preload="metadata" muted playsinline></video>` : `<img class="${cls}" src="${pexUrl(R, f)}" loading="lazy" alt="">`;
function psource(p) {
  const s = p.source || {};
  return s.type === 'creator' ? `<span class="tag">${esc(s.creator || t('creator'))}</span>${s.link ? ` <a href="${esc(s.link)}" target="_blank" rel="noopener" class="small">${t('link')}</a>` : ''}${s.file ? ` <span class="small dim" title="${ta('the file it came from')}">${esc(s.file)}</span>` : ''}`
    : `<span class="tag${s.type === 'tested' ? ' done' : ''}">${esc(isTalk(p) && s.type === 'tested' ? t('yours') : PSRC[s.type] || s.type)}</span>${p.made_from && p.made_from.length ? ` <span class="small muted">${t('from {prompts}', {prompts: p.made_from.map(x => `<a href="#" data-goto="${esc(x)}">${esc(x)}</a>`).join(', ')})}</span>` : ''}`;
}
const pusedLine = u => { const proj = `<a href="#/project/${encodeURIComponent(u.project)}">${esc(u.project)}</a>`;
  return `<div class="small pused">${Object.keys(u.aspects || {}).length
    ? t('Used in {project}: {ratings}', {project: proj, ratings: ASPECTS.filter(([k]) => (u.aspects[k] || {}).rating).map(([k, l]) => `${esc(l)} ${rvChip('result', u.aspects[k].rating)}`).join(' · ')})
    : t('Used in {project} - <span class="muted">not rated yet (the video\'s Review: “How did it turn out?”)</span>', {project: proj})}</div>`; };
function pstyleBlock(p, R) {                           // after 0.3.4: "al estilo de Clavero" = a reference you analysed, measured
  const SR = R.styles || {};
  if (!STYLE_KINDS.includes(p.kind)) return '';
  const linked = p.style_refs || [], sug = (R.suggest || {})[p.id] || [];
  const one = n => { const s = SR[n];
    return `<div class="psref">${s && s.thumb ? `<img src="${fileUrl(s.thumb)}" loading="lazy" alt="">` : '<span></span>'}
      <div><a href="#/ref/${encodeURIComponent(n)}"><b>${esc(s ? s.label || s.title : n)}</b></a>${s && (s.by || s.uploader) ? ` <span class="small muted">${t('by {name}', {name: esc(s.by || s.uploader)})}</span>` : ''}
        <div class="small">${s ? esc(s.line) : `<span class="bad">${t('not analysed on this PC any more')}</span>`}</div></div>
      <button class="btn sm ghost" data-sdel="${esc(n)}" title="${ta('Unlink - Claude no longer copies its style')}">✕</button></div>`; };
  if (!linked.length && !sug.length && !Object.keys(SR).length) return '';
  return `<div class="pstyle"><div class="row"><span class="psl">${t('Style like')}</span>${linked.length ? '' : `<span class="small muted">${t('a video you analysed - Claude copies its measured pacing, effects and look')}</span>`}
      <span class="grow"></span><button class="btn sm ghost" data-spick>+ ${linked.length ? t('another reference') : t('pick from your references')}</button></div>
    ${linked.map(one).join('')}
    ${sug.map(x => `<div class="pssug small"><span>${t('Found in your references: <b>{name}</b>', {name: esc((SR[x.name] || {}).title || x.name)})} <span class="muted">(${esc(x.why)})</span></span>
      <button class="btn sm" data-suse="${esc(x.name)}">${t('Use its style')}</button></div>`).join('')}
    ${linked.length ? `<div class="small muted">${t('Claude reads its measured style when it checks, optimizes or runs this prompt - click <b>Optimize with Claude</b> to write it into the prompt.')}</div>` : ''}</div>`;
}
// a part needs work: Claude found it vague / missing (or gave it no status), or the user wants something there or
// said Claude's check of it is not right
const pIsWork = (p, x) => x.status === 'vague' || x.status === 'missing' || !x.status || !!((p.wishes || {})[x.slot] || '').trim()
  || ['partly', 'wrong'].includes((p.verdicts || {})[x.slot]);
const pCheckOrder = p => {                             // the parts in the cards' order (a brief's in its groups)
  const st = p.structure || [];
  if (p.kind !== 'brief') return st;
  const out = BRIEF_GROUPS.flatMap(([, sl]) => sl.flatMap(s => st.filter(x => x.slot === s)));
  return [...out, ...st.filter(x => !out.includes(x))];
};
// a part's quoted words marked in the text: at = [[start, end], ...], character offsets the lab found (Python's:
// code points, so the text is cut by code points here too - an emoji is one)
const pquoteHtml = (text, at) => {
  const cp = Array.from(String(text || '')), sp = (at || []).filter(x => Array.isArray(x) && x.length === 2)
    .map(([a, b]) => [Math.max(0, a | 0), Math.min(cp.length, b | 0)]).filter(([a, b]) => a < b).sort((x, y) => x[0] - y[0]);
  let out = '', i = 0;
  for (const [a, b] of sp) { if (a < i) continue; out += esc(cp.slice(i, a).join('')) + `<mark class="tq">${esc(cp.slice(a, b).join(''))}</mark>`; i = b; }
  return out + esc(cp.slice(i).join(''));
};
// the check's parts as review rows (Is Claude right?): Claude's status shown, the user's verdict + what they want
const pCheckRow = x => { const [ic, lab] = STAT[x.status] || ['•', ''];
  return {id: x.slot, label: `<span class="rvcl st-${esc(x.status || 'plain')}"><i class="cdot">${ic}</i></span><b>${esc(slotLabel(x.slot))}</b>`,
    sub: lab ? t('Claude: {status}', {status: lab}) : t('Claude gave it no status')}; };
// Claude's check (the Checks tab of a prompt's dialog, read-only since 2026-10-18): the stars, how many parts are
// clear / vague / missing, Claude's verdict, then the text itself with the part under review marked (2026-10-22, the
// user: "when i go into the "your review" page i cant see all the text thats being highlighted or the section itself").
// Each part's tip is on its row of the review panel beside (`pcheckTip`) - no second list of the parts.
function pcheckHead(p, R) {
  const rv = p.review || {}, st = p.structure || [], checked = st.some(x => x.status);
  const slots = (R.kinds.find(k => k.id === p.kind) || {slots: []}).slots;
  const sk = p.skipped && typeof p.skipped === 'object' && !Array.isArray(p.skipped) ? Object.entries(p.skipped) : [];
  if (!st.length && rv.stars == null) return `<div class="pchk none"><div class="pchk-h"><h3>${t("Claude's check")}</h3></div>
    <p>${isTalk(p) ? t('Claude reviews each part of this script - what is <b class="ok">clear</b>, <b class="amber">vague</b> or <b class="bad">missing</b>, with a tip for each - and writes an improved version: <b>Send it to Claude</b>, beside. This one stays as it is.')
      : t('Claude reviews each part of this prompt - what is <b class="ok">clear</b>, <b class="amber">vague</b> or <b class="bad">missing</b>, with a tip for each - and writes an improved version: <b>Send it to Claude</b>, beside. This one stays as it is.')}</p>
    <div class="pchips">${slots.map(s => `<span class="pgneed">${esc(slotLabel(s))}</span>`).join('')}</div></div>`;
  const n = k => st.filter(x => x.status === k).length;
  return `<div class="pchk"><div class="pchk-h"><h3>${t("Claude's check")}</h3>${rv.stars != null ? pstars(rv.stars) : ''}</div>
    ${checked ? `<div class="pchk-sum"><span class="pill clear">${tn(n('clear'), '✓ {n} clear', '✓ {n} clear')}</span><span class="pill vague">${tn(n('vague'), '~ {n} vague', '~ {n} vague')}</span><span class="pill missing">${tn(n('missing'), '✗ {n} missing', '✗ {n} missing')}</span></div>` : ''}
    ${rv.why || rv.fix ? `<div class="pchk-verdict">${rv.why ? `<p>${esc(rv.why)}</p>` : ''}${rv.fix ? `<p class="fix"><b>${t('Most important:')}</b> ${esc(rv.fix)}</p>` : ''}</div>` : ''}
    ${sk.length ? `<details class="cskip"><summary class="small muted">${isTalk(p) ? t('Not part of this script') : t('Not part of this prompt')} <span class="dim">(${sk.length})</span></summary>
      <ul class="small">${sk.map(([s, why]) => `<li><b>${esc(slotLabel(s))}</b> <span class="muted">- ${esc(why)}</span></li>`).join('')}</ul></details>` : ''}</div>`;
}
// a part's tip on its review row: Claude's tip; the quote itself when it cannot be marked in the text (no `at`)
const pcheckTip = (p, x) => { const checked = (p.structure || []).some(y => y.status), marked = (x.at || []).length;
  return `<div class="rvtip st-${esc(x.status || 'plain')}">${!x.text ? `<i>${isTalk(p) ? t('Not in your script') : t('Not in your prompt')}</i>`
    : marked ? '' : `<div>“${esc(x.text)}”${checked ? ` <span class="cunver" title="${ta('Claude checked it before MotionLab looked its quoted words up in your text')}">${t('not verified - check it again')}</span>` : ''}</div>`}
    ${x.tip ? `<div class="cpart-tip"><b>${t('Tip')}</b> ${esc(x.tip)}</div>` : ''}</div>`; };
// a script's steps on its card (Film it): every one it reached - filmed, edited, posted (the user, 0.4.3.5: "a tag
// like Filmed as well as Edited")
const pstage = (p, R) => { if (p.kind !== 'script') return ''; const u = ((R || {}).used || {})[p.id] || [];
  const {st} = scriptRoad(u);
  return ['filmed', 'edited', 'posted'].filter(k => st[k]).map(k => `<span class="pgstage ${k}">✓ ${{filmed: t('Filmed'), edited: t('Edited'), posted: t('Posted')}[k]}</span>`).join(''); };
// one prompt as a card (the prompt library's grid, Generate's latest prompts): kind, category, title, needs, rating
function promptCard(p, R) {
  const res = (p.result || {}).rating, rv = p.review || {}, ex = (p.examples || [])[0], cat = pcategory(p);
  const rating = res ? rvChip('result', res, t('what it made - your rating'))
    : rv.stars != null ? pstars(rv.stars) : p.kind === 'title' && (p.structure || []).some(x => x.status) ? `<span class="small ok">${t('checked by Claude')}</span>`
    : `<span class="small amber">${t('not checked yet')}</span>`;
  return `<button class="pgc k-${esc(p.kind)}" data-id="${esc(p.id)}" title="${ta('{kind} · {id} - click to open', {kind: KSHORT[p.kind] || p.kind, id: p.id})}">${newTag(pkey(p), p.created)}
    ${ex ? `<span class="pgthumb">${pexMedia(R, ex)}</span>` : ''}
    <span class="pgtop"><span class="kbadge k-${esc(p.kind)}">${esc(KSHORT[p.kind] || p.kind)}</span>${cat ? `<span class="pgcat">${esc(pcatWord(cat))}</span>` : ''}${pstage(p, R)}
      ${p.updated || p.added ? `<span class="pgwhen" title="${p.updated && p.updated !== p.added ? ta('saved {added} · changed {updated}', {added: p.added || '', updated: p.updated}) : ta('saved {date}', {date: p.added || p.updated})}">${esc(whenStr(p.updated || p.added))}</span>` : ''}</span>
    <b class="pgtitle">${esc(ptitle(p))}</b>
    <span class="pgfoot"><span class="pgneeds">${ptoolChip(p)}${pneeds(p).map(x => `<span class="pgneed">${esc(x)}</span>`).join('')}</span>${rating}</span></button>`;
}
// ============================================================================================ prepare
// Prepare's cards (0.4.3.5): a script shows its first spoken line, its length and how far it got (+ Film it); a
// title record shows the best title and its thumbnail ideas as small 16:9 tiles - two looks for two different things
const spokenLines = t => String(t || '').split('\n').map(l => l.replace(/\[[^\]]*\]/g, '').replace(/^\s*(said|says|dice)\s*:\s*/i, '').trim())
  .filter(l => l && !/^[A-Z0-9][A-Z0-9 &/+'’-]*(\([^)]*\))?\s*:?$/.test(l));      // no headings ("HOOK (0-3 s)"), no [notes]
function scriptCard(p, R) {
  const L = spokenLines(p.text), words = L.join(' ').split(/\s+/).filter(Boolean).length, hook = L[0] || '';
  const res = (p.result || {}).rating, rv = p.review || {}, cat = pcategory(p);
  const rating = res ? rvChip('result', res, t('what it made - your rating')) : rv.stars != null ? pstars(rv.stars) : '';
  // filmed and edited already: Film it stays (to film it again) but faded, not the card's main button
  const done = p.kind === 'script' && scriptRoad(((R || {}).used || {})[p.id] || []).st.edited;
  return `<div class="spc k-${esc(p.kind)}" data-id="${esc(p.id)}" tabindex="0" title="${ta('Open it: the script, the check, your rating')}">${newTag(pkey(p), p.created)}
    <div class="spc-top"><span class="spk">${p.kind === 'hook' ? t('Hook') : t('Talking script')}</span>${cat ? `<span class="pgcat">${esc(pcatWord(cat))}</span>` : ''}<span class="pgwhen">${esc(whenStr(p.updated || p.added))}</span><span class="pcact"><button class="btn sm ghost icon" data-pren="${esc(p.id)}" title="${ta('Rename…')}"><svg class="i"><use href="#i-pen"/></svg></button><button class="btn sm ghost icon" data-pdelc="${esc(p.id)}" title="${ta('Delete… (to the Recycle Bin)')}"><svg class="i"><use href="#i-trash"/></svg></button></span></div>
    <b class="spc-title">${esc(ptitle(p))}</b>
    ${hook ? `<div class="spc-hook">“${esc(hook.length > 140 ? hook.slice(0, 137) + '…' : hook)}”</div>` : ''}
    ${p.kind === 'script' ? `<div class="spc-meta"><span class="small muted">${tn(words, '≈ {time} · {n} words', '≈ {time} · {n} words', {time: fmtSecs(words / 150 * 60)})}</span>
      <div class="spc-tags">${pstage(p, R) || `<span class="small dim">${t('not filmed yet')}</span>`}</div></div>` : ''}
    ${spcEnd(tookLine(p, R), p.kind === 'script' ? `<button class="btn sm ${done ? 'spc-done' : 'pri'}" data-film="${esc(p.id)}"${done ? ` title="${ta('Already filmed and edited - film it again')}"` : ''}>▶ ${t('Film it')}</button>` : '', rating)}</div>`;
}
// What it took (0.4.4): Claude's time to write it (its request) or improve it, from GET /api/prompts "took"
const tookLine = (p, R) => { const tk = ((R || {}).took || {})[p.id];
  return tk ? `<div class="spc-took" title="${ta("Claude's time for it, from Claude Code's logs on this PC")}"><svg class="i"><use href="#i-clock"/></svg>${t('Claude wrote it in {time}', {time: minWords(tk.minutes)})}</div>` : ''; };
// a card's bottom (the user, 2026-10-15: "keep structure ... 'Claude wrote in...' always on top of the film it", then
// "a fixed place for the stars (bottom right) and the film it button to bottom left"): pushed to the card's bottom
// whatever is above it - the time first, under it one row: the button on the left, the rating on the right - the same
// place on every card of a row
const spcEnd = (took, btn, rating = '') => took || btn || rating ? `<div class="spc-end">${took}${btn || rating
  ? `<div class="spc-act">${btn}<span class="grow"></span>${rating}</div>` : ''}</div>` : '';
function titleCard(p, R) {
  const ts = p.titles || [], cs = p.concepts || [], best = p.chosen || (ts[0] || {}).text || '';
  return `<div class="ttc" data-id="${esc(p.id)}" tabindex="0" title="${ta('Open it: every title, the thumbnail ideas, the hook')}">${newTag(pkey(p), p.created)}
    <div class="spc-top"><span class="spk">${t('Titles & thumbnails')}</span><span class="pgwhen">${esc(whenStr(p.updated || p.added))}</span><span class="pcact"><button class="btn sm ghost icon" data-pren="${esc(p.id)}" title="${ta('Rename…')}"><svg class="i"><use href="#i-pen"/></svg></button><button class="btn sm ghost icon" data-pdelc="${esc(p.id)}" title="${ta('Delete… (to the Recycle Bin)')}"><svg class="i"><use href="#i-trash"/></svg></button></span></div>
    <b class="spc-title">${esc(ptitle(p))}</b>
    ${best ? `<div class="ttc-best">“${esc(best)}”${p.chosen ? ` <span class="small ok">${t('your pick')}</span>` : ''}</div>` : ''}
    ${cs.length ? `<div class="ttc-thumbs">${cs.slice(0, 3).map(c => `<span class="ttc-th" title="${esc(c.sketch || '')}"><b>${esc(c.words || '')}</b><i>${esc(c.id || '')}</i></span>`).join('')}</div>` : ''}
    <div class="spc-foot"><span class="small muted">${plural(ts.length, 'title')} · ${plural(cs.length, 'thumbnail idea')}${p.hook ? ' · ' + t('the hook') : ''}</span><span class="grow"></span>
      ${p.project ? `<span class="pgstage edited" title="${ta('linked to this video')}">${t('for {project}', {project: esc(p.project)})}</span>` : `<span class="small dim">${t('not used yet')}</span>`}</div>
    ${spcEnd(tookLine(p, R), '', rvChip('result', (p.result || {}).rating, t('how it did - your rating')))}</div>`;
}
// Prepare (the user, 2026-10-14: "prepare a video (transcript oriented): improve a script you have - rewrite it with
// more potential to go viral - or generate one from zero from a few questions; hooks, structure"): what you say on
// camera. The scripts live in the prompt library (kind script / hook, so rating, Style like and Film it work as
// for any prompt); the two dialogs save a request (script.py: knowledge\local\prompts\requests\) and open Claude
// with /write-script (its guidelines.md = the viral rules). The script check (POST /api/script/check) needs no Claude.
const isTalk = p => p.kind === 'script' || p.kind === 'hook';
// a script / hook goes to /write-script (the viral-script guidelines), any other prompt to /write-prompt
const optCmd = p => isTalk(p) ? `/write-script improve ${p.id}` : `/write-prompt optimize ${p.id}`;
const chkCmd = p => isTalk(p) ? `/write-script check ${p.id}` : `/write-prompt analyse ${p.id}`;
const optTask = p => isTalk(p) ? 'script' : 'prompt';
const SP_LENGTHS = [['15', '15 s'], ['30', '30 s'], ['45', '45 s'], ['60', '1 min'], ['90', '1:30'], ['180', '3 min'], ['600', '10 min']];
const SC_MARK = {ok: ['✓', 'ok'], warn: ['~', 'amber'], bad: ['✗', 'bad']};
const fmtSecs = s => s < 90 ? `${Math.round(s)} s` : `${Math.floor(s / 60)}:${pad(Math.round(s % 60))} min`;
function scriptCheckHtml(c) {                         // the script check: n of 11, the length, one line per rule
  if (!c || !c.words) return `<div class="small dim">${t('The check runs as you type: the hook, the length, dead seconds, fillers, the call to action.')}</div>`;
  const cls = c.passed >= c.total - 1 ? 'ok' : c.passed >= c.total / 2 ? 'amber' : 'bad';
  return `<div class="scsum"><b class="scscore ${cls}">${c.passed}<small>/${c.total}</small></b>
      <span>${tn(c.words, '<b>≈ {time}</b> · {n} words', '<b>≈ {time}</b> · {n} words', {time: fmtSecs(c.seconds)})}<br><span class="small muted">${t('at {wpm} words a minute ({from})', {wpm: c.wpm, from: esc(c.rate_from)})}</span></span></div>
    <ul class="sclist">${c.checks.map(x => `<li><b class="${SC_MARK[x.status][1]}">${SC_MARK[x.status][0]}</b><span><b>${esc(t(x.label))}</b> <span class="muted">${esc(x.detail)}</span></span></li>`).join('')}</ul>`;
}
// the same check on a script's Checks tab (2026-10-22, less text): the score, a coloured chip per rule (what it found
// in its tooltip) and a line only for the rules that did not pass
function scriptCheckChips(c) {
  if (!c || !c.words) return '';
  const cls = c.passed >= c.total - 1 ? 'ok' : c.passed >= c.total / 2 ? 'amber' : 'bad';
  return `<div class="scsum"><b class="scscore ${cls}">${c.passed}<small>/${c.total}</small></b>
      <span title="${ta('at {wpm} words a minute ({from})', {wpm: c.wpm, from: c.rate_from})}">${tn(c.words, '<b>≈ {time}</b> · {n} words', '<b>≈ {time}</b> · {n} words', {time: fmtSecs(c.seconds)})}</span></div>
    <div class="scchips">${c.checks.map(x => `<span class="scchip ${SC_MARK[x.status][1]}" title="${esc(x.detail)}">${SC_MARK[x.status][0]} ${esc(t(x.label))}</span>`).join('')}</div>
    ${c.checks.filter(x => x.status !== 'ok').map(x => `<div class="scbad ${SC_MARK[x.status][1]}"><b>${esc(t(x.label))}</b> ${esc(x.detail)}</div>`).join('')}`;
}
// what to film, before the words (2026-10-22, the user: "add some structure to know what to film before going into the
// script? like assets or the general rhythm of the video"): from the script's cue cards (GET /api/script/cards, the
// ones Film it shows) the parts as a bar of their seconds (the heading's "(3-7 s)", else its words at 150 a minute),
// the shots to film and the words on screen, each in its part's colour. {bar, side}, both empty when there is nothing.
const FILM_TAG = /^(B-?ROLL|VISUAL|SHOT|PLANO|CAM|CAMERA|CÁMARA)$/, SCREEN_TAG = /^(TEXT|TEXTO|ON[- ]?SCREEN|CAPTION|TITLE|TÍTULO)$/;
const PART_HUE = [[/hook|gancho/i, 'var(--amber)'], [/cta|call|llamada/i, 'var(--pink)'], [/payoff|outro|end|cierre|final/i, 'var(--green)']];
const PART_CYCLE = ['var(--blue)', 'var(--violet)', 'var(--cyan)'];
function filmPlan(C) {
  const parts = ((C || {}).parts || []).filter(x => x.lines.length || x.notes.length);
  let k = 0;
  const P = parts.map((x, i) => {
    const m = /\(\s*(\d+(?:[.,]\d+)?)\s*s?\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*s\s*\)/i.exec(x.head || '');
    const words = x.lines.join(' ').replace(/\[[^\]]*\]/g, ' ').split(/\s+/).filter(Boolean).length;
    const secs = m ? Math.max(0.5, parseFloat(m[2].replace(',', '.')) - parseFloat(m[1].replace(',', '.'))) : words / 150 * 60;
    const name = (x.head || '').replace(/\([^)]*\)/g, '').replace(/[\s:–-]+$/, '').trim() || t('Part {n}', {n: i + 1});
    const hue = (PART_HUE.find(([re]) => re.test(name)) || [null, PART_CYCLE[k++ % PART_CYCLE.length]])[1];
    return {name, secs, hue, notes: x.notes.filter(n => n.text)};
  });
  const total = P.reduce((a, x) => a + x.secs, 0);
  const shots = P.flatMap(x => x.notes.filter(n => FILM_TAG.test(n.tag)).map(n => ({...n, x})));
  const words = P.flatMap(x => x.notes.filter(n => SCREEN_TAG.test(n.tag)).map(n => ({...n, x})));
  const bar = P.length > 1 ? `<div class="srhy"><div class="srhy-h"><svg class="i"><use href="#i-clock"/></svg><b>${t('Rhythm')}</b><span class="small muted">${fmtSecs(total)}</span></div>
    <div class="srh">${P.map(x => `<span style="--ph:${x.hue};flex-grow:${Math.max(x.secs, total / 40).toFixed(2)}" title="${esc(x.name)} · ${fmtSecs(x.secs)}"><b>${esc(x.name)}</b><i>${fmtSecs(x.secs)}</i></span>`).join('')}</div></div>` : '';
  const one = n => `<li class="sshot" style="--ph:${n.x.hue}" title="${esc(n.text)}"><small>${esc(n.x.name)}</small><span>${esc(n.text)}</span></li>`;
  const side = shots.length || words.length ? `<aside class="stofilm">
    ${shots.length ? `<h4><svg class="i"><use href="#i-film"/></svg>${t('Shots to film')}<span class="pmtb">${shots.length}</span></h4><ol class="sshots">${shots.map(one).join('')}</ol>` : ''}
    ${words.length ? `<h4><svg class="i"><use href="#i-type"/></svg>${t('Text on screen')}<span class="pmtb">${words.length}</span></h4><div class="swords">${words.map(n => `<span style="--ph:${n.x.hue}" title="${esc(n.x.name)}">${esc(n.text)}</span>`).join('')}</div>` : ''}</aside>` : '';
  return {bar, side};
}
// ---- shared knowledge (2026-10-18, the user: "associate a distinct icon to the shared knowledge and if something every
// came from shared knowledge it would appear as a reminder"): the lime badge on everything a friend shared - its
// videos, effects, verdicts, lessons, the card dialog, Made from, Home. what = when it was shared ("2026-10-16 15:28")
// or what it is ("a lesson"); the shared contract other parts of the app may call (typeof sharedChip === 'function')
const shDay = s => { const m = /^(\d{4})-(\d\d)-(\d\d)/.exec(String(s || ''));
  return m ? `${+m[3]} ${MONTHS[+m[2] - 1]}${+m[1] !== new Date().getFullYear() ? ' ' + m[1] : ''}` : ''; };
function sharedChip(author, what = '') {
  const who = author || t('a friend'), d = shDay(what);
  const tip = d ? ta('Shared knowledge from {who} - it came with an update on {day}; analysed on their PC', {who, day: d})
    : what ? ta('Shared by {who} through MotionLab ({what}) - not analysed on this PC', {who, what})
    : ta('Shared by {who} through MotionLab - not analysed on this PC', {who});
  return `<span class="shchip" title="${tip}"><svg class="i"><use href="#i-shared"/></svg>${t('from {who}', {who: esc(who)})}</span>`;
}
// the analysed videos of THIS PC for a style picker, each {key, title, label, picture, line, by, platform, format,
// category_label, focus, talk_pct, cuts_per_min, checked}: from GET /api/styles, or GET /api/memory on an older server
// (its local videos only - friends' cards are never offered in a picker). o.talk = the talking ones first.
function ownVideos(M, o = {}) {
  const out = ((M && M.videos) || []).filter(v => v.key || (v.origin === 'local' && v.analysis)).map(v => v.key ? v : {
    key: v.analysis, title: v.title, label: v.label || v.title, picture: null, by: v.by || '', platform: v.platform || '',
    line: Object.values(v.lines || {}).filter(Boolean).join(' · '), format: v.format, category_label: v.category_label,
    focus: v.focus, talk_pct: null, cuts_per_min: (v.pacing || {}).cuts_per_min, checked: !!v.summary, summary: v.summary || ''});
  return o.talk ? out.slice().sort((a, b) => ((b.talk_pct ?? 50) >= 30) - ((a.talk_pct ?? 50) >= 30)) : out;
}
async function loadStyles() {
  try { return await api('/api/styles'); }
  catch (e) {                                         // a server older than this page (API_LEVEL 29): no route yet
    if (!/not found|404/i.test(e.message)) throw e;
    const M = await api('/api/memory');
    return {videos: ownVideos(M), prompts: [], max: 3};
  }
}
// ONE "In the style of" picker everywhere (the user, 2026-10-18: the old chips said "Video by yp.motionstudio ...
// NEMZZZ - 4AM [OFFICIAL VIDEO] [VLDJ_-wrwj8]" - "normal people or my friends wouldnt know what that is? so it would be
// fine to only look in style of "prompts" or "videos" they already analize"): this PC's analysed videos with their
// picture and readable name and - in Prepare (o.prompts) - the scripts and hooks of the prompt library. st.like = the
// picked analysis folders (style.find keys), st.likePrompts = the picked prompt ids. o = {S: loadStyles(), purpose:
// talk | title | edit | graphics | ai, max, prompts, onChange}.
function stylePicker(box, st, o = {}) {
  const S = o.S || {}, max = o.max || S.max || 3, talk = o.purpose === 'talk';
  const vids = ownVideos(S, {talk}), prs = o.prompts ? (S.prompts || []) : [];
  st.like = st.like || []; st.likePrompts = st.likePrompts || [];
  let q = '';
  const has = (...xs) => !q || xs.join(' ').toLowerCase().includes(q);
  const vrow = v => { const on = st.like.includes(v.key), full = !on && st.like.length >= max, low = talk && v.talk_pct != null && v.talk_pct < 30;
    return `<label class="cvitem${on ? ' on' : ''}${full ? ' off' : ''}${low ? ' stplow' : ''}" title="${esc(v.line || v.summary || '')}"><input type="checkbox" data-g="v" value="${esc(v.key)}" ${on ? 'checked' : ''} ${full ? 'disabled' : ''}>
      ${v.picture ? `<img src="${fileUrl(v.picture)}" loading="lazy" alt="">` : '<span class="cvnoimg"></span>'}
      <span class="grow"><b>${esc(v.label || v.title || v.key)}</b> ${focusChip(v.focus)}
        ${v.by || v.platform ? `<span class="small muted stpl">${[v.by ? t('by {name}', {name: esc(v.by)}) : '', esc(v.platform || '')].filter(Boolean).join(' · ')}</span>` : ''}
        <span class="small muted stpl">${[esc((v.format || '').split(' · ').map((x, i) => i ? x : t(x)).join(' · ')), esc(t(v.category_label || '')), talk ? (v.talk_pct != null ? t('talking {pct} %', {pct: Math.round(v.talk_pct)}) : '')
          : v.cuts_per_min != null ? tn(v.cuts_per_min, '{n} cuts/min', '{n} cuts/min') : '', v.checked ? t('checked by Claude') : t('not checked by Claude yet')].filter(Boolean).join(' · ')}${low ? ' · ' + t('too little talking to measure its pace') : ''}</span></span></label>`; };
  const prow = p => { const on = st.likePrompts.includes(p.id), full = !on && st.likePrompts.length >= max;
    return `<label class="cvitem stpp${on ? ' on' : ''}${full ? ' off' : ''}"><input type="checkbox" data-g="p" value="${esc(p.id)}" ${on ? 'checked' : ''} ${full ? 'disabled' : ''}>
      <span class="stpk k-${esc(p.kind)}">${p.kind === 'hook' ? t('Hook') : t('Script')}</span>
      <span class="grow"><b>${esc(p.title || p.id)}</b> <span class="tag">${esc(p.source)}</span>${p.rating === 'good' ? ` <span class="ok small">${t('rated good')}</span>` : p.stars != null ? ` <span class="stars small" title="${ta("Claude's check")}">${'★'.repeat(p.stars)}</span>` : ''}
        ${p.first ? `<span class="small muted stpl">“${esc(p.first)}”</span>` : ''}</span></label>`; };
  const draw = () => {
    const keys = new Set(vids.map(v => v.key));
    const extra = st.like.filter(k => !keys.has(k)).map(k => ({key: k, label: k}));    // picked elsewhere (a test video)
    const vs = [...extra, ...vids].filter(v => has(v.label, v.title, v.key, v.by, v.platform, v.category_label, v.summary, LANG === 'en' ? '' : t(v.category_label || '')));
    const ps = prs.filter(p => has(p.title, p.first, p.source, p.kind));
    $('.stplist', box).innerHTML = (prs.length ? `<div class="stpg">${t('Videos you analysed')} <span class="dim">${vids.length}</span></div>` : '')
      + (vids.length || extra.length ? vs.map(vrow).join('') || `<div class="small dim stpe">${t('No video matches.')}</div>`
        : `<div class="small dim stpe">${t('No video analysed on this PC yet - add one in the <a href="#/analyze" onclick="closeModal()">Analyser</a>.')}</div>`)
      + (prs.length ? `<div class="stpg">${t('Scripts & hooks')} <span class="dim">${prs.length}</span></div>${ps.map(prow).join('') || `<div class="small dim stpe">${t('No script matches.')}</div>`}` : '');
    const picked = [st.like.length ? plural(st.like.length, 'video') : '', st.likePrompts.length ? plural(st.likePrompts.length, prs.some(p => p.kind === 'hook') ? 'script / hook' : 'script') : ''].filter(Boolean);
    $('.stpn', box).textContent = picked.length ? ' · ' + t('{what} picked', {what: picked.join(' + ')}) : '';
    $$('input', $('.stplist', box)).forEach(c => c.onchange = () => {
      const k = c.dataset.g === 'p' ? 'likePrompts' : 'like';
      st[k] = c.checked ? [...st[k], c.value].slice(0, max) : st[k].filter(x => x !== c.value);
      draw(); (o.onChange || (() => {}))();
    });
  };
  box.innerHTML = `<div class="stp"><div class="row sp stph"><span class="small muted">${prs.length ? t('Up to {n} of each', {n: max}) : t('Up to {n}', {n: max})}<b class="stpn"></b></span>
      ${vids.length + prs.length > 4 ? `<input type="search" class="stpq" placeholder="${ta('Search…')}">` : ''}</div><div class="cvlist stplist"></div></div>`;
  const qi = $('.stpq', box);
  if (qi) qi.oninput = debounce(() => { q = qi.value.trim().toLowerCase(); draw(); }, 150);
  draw();
}
function spSeg(el, id, st, key, onChange = () => {}) {
  const b = $(id, el); const paint = () => $$('button', b).forEach(x => x.classList.toggle('on', x.dataset.v === st[key]));
  $$('button', b).forEach(x => x.onclick = () => { st[key] = x.dataset.v; paint(); onChange(); }); paint();
}
async function pagePrepare(main) {
  const ctx = {};
  const load = async () => { await api('/api/script/tidy', {}).catch(() => {});      // an improved script replaces its paste
    [ctx.R, ctx.Q] = await Promise.all([api('/api/prompts'), api('/api/script/requests')]); };
  await load();
  const draw = () => {
    const R = ctx.R, Q = ctx.Q, byId = Object.fromEntries(R.items.map(p => [p.id, p]));
    // only the user's own (2026-10-18): the scripts of creators analysed in the Analyser stay in their set + the library
    // Improve my script (2026-10-24, a friend's ask): the pasted script is not a card of its own while Claude works on
    // it - it shows under Waiting for Claude as "improving…" - and the server moves it to the Recycle Bin once the new
    // version is saved (data.tidy_improved): one card, the improved one, with NEW
    const improving = new Set(Q.items.filter(r => r.kind === 'improve' && r.replace && !(r.made || []).length).map(r => r.script));
    const mine = R.items.filter(p => (isTalk(p) || p.kind === 'title') && (p.source || {}).type !== 'creator' && !improving.has(p.id)).sort((a, b) => (b.updated || b.added || '').localeCompare(a.updated || a.added || '') || b.id.localeCompare(a.id));
    const waiting = Q.items.filter(r => !(r.made || []).length && (r.kind === 'new' || r.kind === 'title' || byId[r.script])).slice(0, 8);
    const scripts = mine.filter(isTalk), titles = mine.filter(p => p.kind === 'title');
    // the old structure (the user, round 3): the two big ways for scripts, a slim row for a title / thumbnail only,
    // what waits for Claude, then the list in two halves - talking scripts | titles & thumbnails, each its own cards
    main.innerHTML = `<div class="head"><div><h1>${t('Prepare')}</h1><div class="sub">${t('Before you film: what you say on camera and what people click on - a hook in the first 3 seconds, a title the video keeps.')}</div></div>
        ${mine.length ? `<div class="row"><a class="btn" href="#/prompts">${t('Prompt library')}</a></div>` : ''}</div>
      <div class="gways">
        <div class="gway"><div class="row"><svg class="ic"><use href="#i-scriptok"/></svg><h2>${t('Improve my script')}</h2></div>
          <p>${t('Paste the script you have. MotionLab checks it on the spot - the hook, the length, dead seconds, fillers, the call to action. Then Claude marks every part (clear, vague or missing) and rewrites it in your voice: a stronger hook, nothing that makes people scroll away.')}</p>
          <div class="row"><button class="btn pri" id="sp-imp"><svg class="i"><use href="#i-claude"/></svg>${t('Improve a script')}</button></div>
          <div class="small muted">${t('Claude saves one improved version - it takes the place of the one you paste (that one goes to the Recycle Bin).')}</div></div>
        <div class="gway"><div class="row"><svg class="ic"><use href="#i-prepare"/></svg><h2>${t('Write one from zero')}</h2></div>
          <p>${t('Answer a few questions - what it is about, who it is for, what they get, your story. Claude writes three hooks and the whole script, timed to your length, with what goes on screen - in the style of talking videos you analysed.')}</p>
          <div class="row"><button class="btn pri" id="sp-new"><svg class="i"><use href="#i-claude"/></svg>${t('Write a script with Claude')}</button></div>
          <div class="small muted">${t('Then film it and bring the clips to the <a href="#/edit">Editor</a>.')}</div></div></div>
      <div class="tfrow"><svg class="i tfic" aria-hidden="true"><use href="#i-thumb"/></svg><div class="grow"><b>${t('Only need a title or thumbnail?')}</b>
          <div class="small muted">${t('If you already have a video ready and are still missing a powerful title or thumbnail, create it with Claude.')}</div></div>
        <button class="btn" id="sp-title"><svg class="i"><use href="#i-claude"/></svg>${t('Create it with Claude')}</button></div>
      ${waiting.length ? `<h3 style="margin:22px 0 8px">${t('Waiting for Claude')}</h3><div class="spwait">${waiting.map(r => {
        const what = r.kind === 'new' || r.kind === 'title' ? `<b>${esc(r.topic.split('\n')[0].slice(0, 90))}</b> <span class="muted">· ${r.kind === 'title' ? t('titles and thumbnail ideas') : t('a script from zero')}</span>`
          : `<b>${esc(ptitle(byId[r.script]))}</b> <span class="muted">· ${r.replace ? `<span class="spinning">${t('improving…')}</span>` : t('improve it')}</span>`;
        const cmd = r.kind === 'new' ? `/write-script request ${r.id}` : r.kind === 'title' ? `/write-title request ${r.id}` : `/write-script improve ${r.script}`;
        return `<div class="spw"><span class="grow">${what} <span class="small dim">${esc(whenStr(r.date))}</span></span>
          ${claudeBtn(cmd, t('Open in Claude Code again'), r.kind === 'title' ? 'title' : 'script', r.id)}<button class="btn sm ghost" data-forget="${esc(r.id)}" title="${r.kind === 'improve' ? ta('Forget this request (your script stays)') : ta('Forget this request')}">✕</button></div>`; }).join('')}</div>` : ''}
      ${mine.length ? `<div class="preplist">
        <section class="plcol pl-script"><h3 class="plh"><svg class="i plic" aria-hidden="true"><use href="#i-mic"/></svg>${t('Talking scripts')} <span class="pcn">${scripts.length}</span></h3>
          ${scripts.length ? `<div class="spcards">${scripts.map(x => scriptCard(x, R)).join('')}</div>` : `<div class="pcempty">${t('No script yet - improve yours or write one from zero, above.')}</div>`}</section>
        <section class="plcol pl-title"><h3 class="plh"><svg class="i plic" aria-hidden="true"><use href="#i-thumb"/></svg>${t('Titles & thumbnails')} <span class="pcn">${titles.length}</span></h3>
          ${titles.length ? `<div class="ttcards">${titles.map(x => titleCard(x, R)).join('')}</div>` : `<div class="pcempty">${t('No titles yet - <i>Only need a title or thumbnail?</i> above.')}</div>`}</section></div>` : ''}`;
    $('#sp-imp', main).onclick = () => scriptImproveModal(ctx);
    $('#sp-new', main).onclick = () => scriptNewModal(ctx);
    $('#sp-title', main).onclick = () => titleForVideoModal(ctx);
    $$('.spc, .ttc', main).forEach(c => {
      c.onclick = e => { if (!e.target.closest('[data-film], .pcact')) promptModal(c.dataset.id, ctx); };
      c.onkeydown = e => { if (e.key === 'Enter' && e.target === c) promptModal(c.dataset.id, ctx); };
    });
    $$('[data-film]', main).forEach(b => b.onclick = () => filmItModal(byId[b.dataset.film]));
    $$('[data-pren]', main).forEach(b => b.onclick = () => renamePromptModal(byId[b.dataset.pren], ctx));
    $$('[data-pdelc]', main).forEach(b => b.onclick = () => delPromptModal(byId[b.dataset.pdelc]));
    $$('[data-forget]', main).forEach(b => b.onclick = async () => {
      try { await api('/api/script/forget', {id: b.dataset.forget}); toast(t('Forgotten'), 'ok'); await ctx.reload(); }
      catch (e) { toast(e.message, 'err'); }
    });
  };
  ctx.draw = draw;
  ctx.reload = async () => { await load(); draw(); };
  draw();
}
// Prepare > Improve my script: paste (or attach) it, the check while you type, what you want -> the prompt library
// (kind script, yours) + a request -> Claude Code /write-script improve <id>
async function scriptImproveModal(ctx, pre = {}) {
  const S = await loadStyles();
  const st = {like: [], likePrompts: [], length: '', where: '', file: ''};
  modal(`<h2>${t('Improve my script')}</h2>
    <div class="small muted" style="margin-top:-4px">${t('Paste it the way you would say it. The check on the right needs no Claude; Claude then checks every part and writes a better version that takes its place.')}</div>
    <div class="spgrid"><div>
      <div class="nestep"><b>1</b>${t('Your script')}</div>
      <textarea id="stext" rows="13" style="width:100%" placeholder="${ta('Paste your script here…\n\nNotes for the camera can go in brackets: [TEXT: 3 mistakes] [B-ROLL: my desk]')}">${esc(pre.text || '')}</textarea>
      <div class="row" style="margin-top:6px"><label class="btn sm ghost">${t('Attach a file (.txt, .md, .docx)')}<input type="file" id="sfile" accept=".txt,.md,.docx" hidden></label><span class="small muted" id="sfname"></span></div>
      <div class="nestep opt"><b>2</b>${t('What you want')} ${optTag()}</div>
      <div class="nedet spf"><label>${t('Where it goes')}</label><div class="seg" id="swhere"><button data-v="">${t('Claude picks')}</button><button data-v="vertical">TikTok · Reels · Shorts</button><button data-v="youtube">YouTube</button></div>
        <label>${t('Length')}</label><div class="seg" id="slen"><button data-v="">${t('Keep its length')}</button>${SP_LENGTHS.map(([v, l]) => `<button data-v="${v}">${l}</button>`).join('')}</div>
        <label>${t('Anything else')}</label><input type="text" id="swant" placeholder="${ta('e.g. more energy, less about me, end with my course')}" style="max-width:460px"></div>
      <div class="nestep opt"><b>3</b>${t('In the style of')} ${optTag(t('talking videos you analysed or scripts of yours: their pace and structure'))}</div>
      <div id="sstp"></div>
    </div><div class="spcheck"><div class="row sp"><h3 style="margin:0">${t('The check')}</h3><span class="small muted">${t('instant · no Claude')}</span></div><div id="schk"></div></div></div>
    <div class="row" style="margin-top:16px"><button class="btn pri big" id="sgo"><svg class="i"><use href="#i-claude"/></svg>${t('Improve it with Claude')}</button>
      <span class="small muted">${t('Claude Code opens in a new window: it checks every part, then writes the new version - you find it here under Prepare.')}</span></div>`, el => {
    const txt = $('#stext', el);
    const run = debounce(async () => {
      try { $('#schk', el).innerHTML = scriptCheckHtml(await api('/api/script/check', {text: txt.value, length_s: st.length || null, like: st.like})); }
      catch (e) { $('#schk', el).innerHTML = `<div class="small bad">${esc(e.message)}</div>`; }
    }, 300);
    spSeg(el, '#swhere', st, 'where'); spSeg(el, '#slen', st, 'length', run);
    stylePicker($('#sstp', el), st, {S, purpose: 'talk', prompts: true, onChange: run});
    txt.oninput = run; run(); txt.focus();
    $('#sfile', el).onchange = async e => {
      const f = e.target.files[0]; e.target.value = '';
      if (!f) return;
      if (f.size > 30e6) { toast(t('Files up to 30 MB'), 'err'); return; }
      try {
        const r = await api('/api/prompts/file', {name: f.name, data: b64(await f.arrayBuffer())});
        if (!r.text) { toast(t('{name}: no text found in it', {name: f.name}), 'err'); return; }
        txt.value = r.text; st.file = r.file; $('#sfname', el).textContent = r.file; run();
      } catch (err) { toast(err.message, 'err'); }
    };
    $('#sgo', el).onclick = async () => {
      try {
        const r = await api('/api/script/improve', {text: txt.value, file: st.file, where: st.where, length_s: st.length || null,
                                                    want: $('#swant', el).value, like: st.like, like_prompts: st.likePrompts});
        openClaude(r.command, 'script', r.script.id);
        closeModal();
        if (location.hash === '#/prepare' && ctx && ctx.reload) await ctx.reload(); else location.hash = '#/prepare';
      } catch (e) { toast(e.message, 'err'); }
    };
  }, 'wide');
}
// Prepare > Write one from zero: the questions -> a request -> Claude Code /write-script request <id>
async function scriptNewModal(ctx, pre = {}) {
  const [S, Q] = await Promise.all([loadStyles(), api('/api/script/requests')]);
  const st = {like: [], likePrompts: [], length: '30', where: 'vertical', tone: '', cta: '', lang: ''};
  modal(`<h2>${t('Write a script from zero')}</h2>
    <div class="small muted" style="margin-top:-4px">${t('The more you tell, the more it sounds like you. Only the first question is needed - Claude asks for what is missing.')}</div>
    <div class="nestep"><b>1</b>${t('The idea')}</div>
    <div class="nedet spq"><label>${t('What is it about?')}</label><textarea id="qtopic" rows="2" placeholder="${ta('e.g. how I edit a talking video in 20 minutes on my phone')}">${esc(pre.topic || '')}</textarea>
      <label>${t('Who is it for?')}</label><input type="text" id="qaud" placeholder="${ta('e.g. small creators who film on their phone and hate editing')}">
      <label>${t('What do they get by the end?')}</label><input type="text" id="qtake" placeholder="${ta('e.g. a 3-step routine they can copy today')}"></div>
    <div class="nestep opt"><b>2</b>${t('Your angle')} ${optTag(t('the best hooks come from here'))}</div>
    <div class="nedet spq"><label>${t('Your story, result or opinion')}</label><textarea id="qangle" rows="2" placeholder="${ta('e.g. I went from 200 to 40,000 views in two months doing this - I used to spend 3 hours per video')}"></textarea>
      <label>${t('Must-say points')}</label><textarea id="qpoints" rows="2" placeholder="${ta('one per line, in any order')}"></textarea></div>
    <div class="nestep opt"><b>3</b>${t('Format')} ${optTag(t('a 30 s short unless you change it'))}</div>
    <div class="nedet spf"><label>${t('Where it goes')}</label><div class="seg" id="qwhere"><button data-v="vertical">TikTok · Reels · Shorts</button><button data-v="youtube">YouTube</button><button data-v="">${t('Claude picks')}</button></div>
      <label>${t('Length')}</label><div class="seg" id="qlen">${SP_LENGTHS.map(([v, l]) => `<button data-v="${v}">${l}</button>`).join('')}</div>
      <label>${t('Tone')}</label><div class="seg" id="qtone"><button data-v="">${t('Claude picks')}</button>${Object.entries(Q.tones).map(([k, l]) => `<button data-v="${k}">${esc(t(l))}</button>`).join('')}</div>
      <label>${t('Ask at the end')}</label><div class="row"><div class="seg" id="qcta"><button data-v="">${t('Claude picks')}</button>${Object.entries(Q.ctas).map(([k, l]) => `<button data-v="${k}">${esc(t(l))}</button>`).join('')}</div></div>
      <label></label><input type="text" id="qctat" placeholder="${ta('optional - e.g. comment GUIDE and I send you my presets')}" style="max-width:460px">
      <label>${t('Language')}</label><div class="seg" id="qlang"><button data-v="">${t('The one I write in')}</button>${Object.entries(Q.langs).map(([k, l]) => `<button data-v="${k}">${esc(l)}</button>`).join('')}</div></div>
    <div class="nestep opt"><b>4</b>${t('In the style of')} ${optTag(t('talking videos you analysed or scripts of yours'))}</div>
    <div id="qstp"></div>
    <div class="nedet spf" style="margin-top:10px"><label>${t('Anything else')}</label><input type="text" id="qextra" placeholder="${ta('optional - e.g. no swearing, mention my course at the end')}" style="max-width:460px"></div>
    <div class="row" style="margin-top:16px"><button class="btn pri big" id="qgo"><svg class="i"><use href="#i-claude"/></svg>${t('Write it with Claude')}</button>
      <span class="small muted">${t('Claude Code opens in a new window with your answers: three hooks, then the script - you find it here under Prepare.')}</span></div>`, el => {
    for (const [id, key] of [['#qwhere', 'where'], ['#qlen', 'length'], ['#qtone', 'tone'], ['#qcta', 'cta'], ['#qlang', 'lang']]) spSeg(el, id, st, key);
    stylePicker($('#qstp', el), st, {S, purpose: 'talk', prompts: true});
    $('#qtopic', el).focus();
    $('#qgo', el).onclick = async () => {
      const topic = $('#qtopic', el).value.trim();
      if (!topic) { toast(t('Say what the video is about first'), 'err'); $('#qtopic', el).focus(); return; }
      try {
        const r = await api('/api/script/request', {topic, audience: $('#qaud', el).value, takeaway: $('#qtake', el).value,
          angle: $('#qangle', el).value, points: $('#qpoints', el).value, length_s: st.length || null, where: st.where,
          tone: st.tone, cta: st.cta, cta_text: $('#qctat', el).value, lang: st.lang, like: st.like, like_prompts: st.likePrompts,
          extra: $('#qextra', el).value});
        openClaude(r.command, 'script', r.request.id);
        closeModal();
        if (location.hash === '#/prepare' && ctx && ctx.reload) await ctx.reload(); else location.hash = '#/prepare';
      } catch (e) { toast(e.message, 'err'); }
    };
  }, 'wide');
}

// Prepare > Only need a title or thumbnail? (round 3 of 0.4.3.5, the user: "if you already have a video ready and are
// still missing a powerful title or thumbnail, review it with Claude"): pick the video -> its Ready to post + Claude
// (/write-title package <p>); a video not in MotionLab (or not filmed yet) -> the questions (titleFirstModal)
async function titleForVideoModal(ctx) {
  const ps = (await api('/api/projects')).filter(x => x.latest).sort((a, b) => (b.sort_t || 0) - (a.sort_t || 0));
  if (!ps.length) return titleFirstModal(ctx);
  modal(`<h2>${t('Only need a title or thumbnail?')}</h2>
    <div class="small muted" style="margin-top:-4px">${t('Pick the video. Claude looks at what it says and shows, then writes the title, thumbnails A / B / C, the description and the hashtags - you find them under the video\'s <b>Ready to post</b>.')}</div>
    <div class="tfpick">${ps.map(x => `<button class="tfv" data-p="${esc(x.name)}"><span class="tfvpic">${x.picture ? `<img src="${picUrl(x.picture)}" loading="lazy" alt="">` : ''}</span>
      <b>${esc(pname(x))}</b><span class="small muted">${[lenWords(x.latest.frames, x.latest.fps), whenWords(x.latest.mtime)].filter(Boolean).map(esc).join(' · ')}${x.title ? ` · <span class="ok">${t('has a title')}</span>` : ''}</span></button>`).join('')}</div>
    <div class="row" style="margin-top:14px"><span class="small muted">${t('Not in MotionLab, or not filmed yet?')}</span><button class="btn sm" id="tfq">${t('Answer a few questions instead')}</button></div>`, el => {
    $$('.tfv', el).forEach(b => b.onclick = () => {
      const n = b.dataset.p;
      closeModal(); location.hash = `#/project/${encodeURIComponent(n)}/publish`;
      setTimeout(() => openClaude(`/write-title package ${n}`, 'title', n), 300);
    });
    $('#tfq', el).onclick = () => { titleFirstModal(ctx); modalBack(() => titleForVideoModal(ctx)); };
  }, 'wide');
}
// Prepare > Title & thumbnail first (0.4.3): the packaging before filming - the answers -> a request (kind title) ->
// Claude Code /write-title request <id> -> a title record in the prompt library (titles, thumbnail ideas, the hook)
const TF_ORIENT = p => { const h = p.includes('youtube'), v = p.some(x => x !== 'youtube'); return h && v ? 'both' : h ? 'horizontal' : v ? 'vertical' : ''; };
async function titleFirstModal(ctx, pre = {}) {
  const [S, Q] = await Promise.all([loadStyles(), api('/api/script/requests')]);
  const st = {like: [], likePrompts: [], plats: ['youtube'], orient: 'horizontal', own: false, lang: ''};
  modal(`<h2>${t('Title & thumbnail first')}</h2>
    <div class="small muted" style="margin-top:-4px">${t('Only the first question is needed. The rest makes the titles yours - Claude asks for what is missing.')}</div>
    <div class="nestep"><b>1</b>${t('The video')}</div>
    <div class="nedet spq"><label>${t('What is it about?')}</label><textarea id="ttopic" rows="2" placeholder="${ta('e.g. I filmed a music video in my bedroom at 4AM')}">${esc(pre.topic || '')}</textarea>
      <label>${t('Who is it for?')}</label><input type="text" id="tview" placeholder="${ta('e.g. people who make music videos with one camera')}">
      <label>${t('Your angle')}</label><textarea id="tangle" rows="2" placeholder="${ta('your story, a number or an opinion - e.g. no budget, one lamp, done in one night')}"></textarea></div>
    <div class="nestep opt"><b>2</b>${t('Where it goes')} ${optTag(t('YouTube unless you change it'))}</div>
    <div class="nedet spf"><label>${t('Platforms')}</label><div class="row" id="tplat">${Object.entries(Q.platforms || {}).map(([k, l]) => `<label class="chk"><input type="checkbox" value="${k}" ${st.plats.includes(k) ? 'checked' : ''}> ${esc(t(l))}</label>`).join('')}</div>
      <label>${t('Thumbnail')}</label><div><div class="seg" id="torient">${Object.entries(Q.orientations || {}).map(([k, l]) => `<button data-v="${k}">${esc(t(l))}</button>`).join('')}</div>
        <div class="small muted" id="torh" style="margin-top:4px"></div></div>
      <label>${t('Language')}</label><div class="seg" id="tlang"><button data-v="">${t('The one I write in')}</button>${Object.entries(Q.langs).map(([k, l]) => `<button data-v="${k}">${esc(l)}</button>`).join('')}</div></div>
    <div class="nestep opt"><b>3</b>${t('In the style of')} ${optTag(t('videos you analysed - how their titles and thumbnails look - or scripts of yours'))}</div>
    <div id="tstp"></div>
    <div class="nedet spf" style="margin-top:10px"><label>${t('Anything else')}</label><input type="text" id="tnotes" placeholder="${ta('optional - e.g. no clickbait, keep my channel\'s red')}" style="max-width:460px"></div>
    <div class="row" style="margin-top:16px"><button class="btn pri big" id="tgo"><svg class="i"><use href="#i-claude"/></svg>${t('Write them with Claude')}</button>
      <span class="small muted">${t('Claude Code opens in a new window with your answers: titles, thumbnail ideas and the hook - you find them here under Prepare.')}</span></div>`, el => {
    const ob = $('#torient', el);
    const paint = () => {
      $$('button', ob).forEach(x => x.classList.toggle('on', x.dataset.v === st.orient));
      $('#torh', el).textContent = st.own ? t('your choice') : st.orient ? t('from the platforms - click to change') : t('pick a platform');
    };
    $$('#tplat input', el).forEach(i => i.onchange = () => {
      st.plats = $$('#tplat input:checked', el).map(x => x.value);
      if (!st.own) st.orient = TF_ORIENT(st.plats);
      paint();
    });
    $$('button', ob).forEach(b => b.onclick = () => { st.orient = b.dataset.v; st.own = true; paint(); });
    paint();
    spSeg(el, '#tlang', st, 'lang');
    stylePicker($('#tstp', el), st, {S, purpose: 'title', prompts: true});
    $('#ttopic', el).focus();
    $('#tgo', el).onclick = async () => {
      const topic = $('#ttopic', el).value.trim();
      if (!topic) { toast(t('Say what the video is about first'), 'err'); $('#ttopic', el).focus(); return; }
      try {
        const r = await api('/api/title/request', {topic, viewer: $('#tview', el).value, angle: $('#tangle', el).value, platforms: st.plats,
          orientation: st.orient, language: st.lang, style_refs: st.like, like_prompts: st.likePrompts, notes: $('#tnotes', el).value});
        openClaude(r.command, 'title', r.request.id);
        closeModal();
        if (location.hash === '#/prepare' && ctx && ctx.reload) await ctx.reload(); else location.hash = '#/prepare';
      } catch (e) { toast(e.message, 'err'); }
    };
  }, 'wide');
}

// Generate (0.4): a video from zero - prompts for AI video and image tools (Claude writes them, you paste them into the
// tool and bring the clips to Edit) or a motion-graphics video; the prompt library is one click away
async function pageGenerate(main) {
  const [R, G, ps] = await Promise.all([api('/api/prompts'), api('/api/generate/options'), api('/api/projects')]);
  const recent = [...R.items].sort((a, b) => (b.updated || b.added || '').localeCompare(a.updated || a.added || '') || b.id.localeCompare(a.id)).slice(0, 6);
  const made = ps.filter(inGenerator).sort((a, b) => (b.sort_t || 0) - (a.sort_t || 0));   // made from zero, newest first
  main.innerHTML = `<div class="head"><div><h1>${t('Generator')}</h1><div class="sub">${t('A video from zero - no clips of your own needed.')}</div></div>
      <div class="row"><a class="btn" href="#/prompts">${t('Prompt library ({n})', {n: R.items.length})}</a></div></div>
    <div class="gways">
      <div class="gway"><div class="row"><svg class="ic"><use href="#i-library"/></svg><h2>${t('A motion-graphics video')}</h2></div>
        <p>${t('Kinetic text, titles, numbers, shapes and charts - built by Claude from your <a href="#/motion">Motion Graphics</a> templates as HTML and rendered to a video (HyperFrames), timed to your song. Every text, colour and timing stays editable afterwards.')}</p>
        <div class="row"><button class="btn pri" id="ggfx"${G.hyperframes ? '' : ' disabled'}><svg class="i"><use href="#i-claude"/></svg>${t('Make a motion-graphics video')}</button>
          <a class="btn ghost" href="#/motion">${t('Motion templates')}</a></div>
        <div class="small ${G.hyperframes ? 'muted' : 'amber'}">${G.hyperframes ? t('Claude writes it with you, then renders it - you watch it in the Editor.')
          : G.node ? t('Needs HyperFrames first - <a href="#/settings">Settings → Programs</a> installs it.')
          : t('Needs Node.js and HyperFrames first - <a href="#/settings">Settings → Programs</a> installs it.')}</div></div>
      <div class="gway"><div class="row"><svg class="ic"><use href="#i-generate"/></svg><h2>${t('With AI video tools')}</h2></div>
        <p>${t('Higgsfield, Seedance, Kling, Runway, Veo, Sora, InVideo… Tell Claude your idea: it plans the shots and writes every prompt - in the structure that worked best in your library, in the style of videos you analysed. You generate them on the tool\'s site, then the <a href="#/edit">Editor</a> cuts them.')}</p>
        <div class="row"><button class="btn pri" id="gai"><svg class="i"><use href="#i-claude"/></svg>${t('Generate a video with Claude and other tools')}</button>
          <button class="btn ghost" id="gen-one">${t('Just one prompt')}</button></div>
        <div class="small muted">${t('Nothing is paid here - the tool\'s own plan or credits pay for the clips.')}</div></div></div>
    ${made.length ? `<div class="row sp" style="margin-top:20px"><h3 style="margin:0">${t('Made from zero')}</h3></div>
      <div class="cards pcards" style="margin-top:8px">${made.map(projCard).join('')}</div>` : ''}
    ${recent.length ? `<div class="row sp" style="margin-top:20px"><h3 style="margin:0">${t('Your latest prompts')}</h3><a class="small" href="#/prompts">${tn(R.items.length, 'all {n} →', 'all {n} →')}</a></div>
      <div class="pgrid" style="margin-top:8px">${recent.map(p => promptCard(p, R)).join('')}</div>` : ''}`;
  $('#ggfx', main).onclick = () => generateModal('graphics');
  $('#gai', main).onclick = () => generateModal('ai');
  $('#gen-one', main).onclick = () => aiPromptsModal();     // not #gone: the heartbeat removes that one (its warning)
  $$('.pgc', main).forEach(c => c.onclick = () => { location.hash = '#/prompts/' + c.dataset.id; });
  wirePcards(main, ps);
}

// ---- Generate (0.4, the user: "generate a video from zero - mostly with external tools like Higgsfield, InVideo... or a
// whole motion-graphics video with HyperFrames"): one dialog for both ways -> POST /api/generate/request (the video's
// folder + build\generate_request.json) -> Claude Code /generate-video request <name>
async function generateModal(kind, pre = {}) {
  const [G, S, ps, MG] = await Promise.all([api('/api/generate/options'), loadStyles(), api('/api/projects'),
    kind === 'graphics' ? api('/api/motion').catch(() => ({library: []})) : {library: []}]);
  const gfx = kind === 'graphics', st = {like: [], length: gfx ? '30' : '30', format: '', music: '', tpl: [...(pre.templates || [])]};
  const taken = new Set(ps.map(x => x.name.toLowerCase())), base = gfx ? 'motion graphic' : 'ai video';
  let k = 1; while (taken.has(`${base} ${k}`)) k++;
  const n0 = `${base} ${k}`;                          // a free name: an existing video is never taken over
  modal(`<h2>${gfx ? t('A motion-graphics video') : t('A video for AI video tools')}</h2>
    <div class="small muted" style="margin-top:-4px">${gfx ? t('Claude writes it as HTML (HyperFrames) with you and renders it to a video - every text and colour stays editable.')
      : t('Claude plans the shots and writes every prompt into your prompt library - you generate the clips on the tool\'s site.')}</div>
    <div class="nestep"><b>1</b>${t('What is it about?')}</div>
    <textarea id="gwant" rows="3" style="width:100%" placeholder="${gfx ? ta('e.g. a 30 s reel announcing my new course: the problem, 3 things it teaches, the price, sign up - bold, fast, on the beat')
      : ta('e.g. a 20 s cinematic ad for my coffee brand: morning light, slow pours, steam, the cup in hands, the logo at the end')}">${esc(pre.want || '')}</textarea>
    ${gfx ? `<div class="small muted" style="margin:10px 0 4px">${t('The words on screen')} ${optTag(t('one per line, in order'))}</div>
      <textarea id="gtext" rows="4" style="width:100%" placeholder="${ta('Stop scrolling.\n3 things nobody tells you\n…')}"></textarea>`
      : `<div class="row" style="margin-top:10px"><label class="small">${t('Tool')} <select id="gtool"><option value="">${t('- Claude asks -')}</option>${G.tools.map(x => `<option>${esc(x)}</option>`).join('')}<option value="other">${t('another…')}</option></select></label>
        <input type="text" id="gtool2" placeholder="${ta('which tool?')}" hidden style="max-width:220px"></div>`}
    <div class="nestep opt"><b>2</b>${t('In the style of')} ${optTag(t('up to 3 videos you analysed'))}</div>
    <div id="gstp"></div>
    ${gfx && MG.library.length ? `<div class="nestep opt"><b>3</b>${t('Motion templates')} ${optTag(t('Claude builds the scenes from these'))}</div>
      <div class="gtpl" id="gtpl"></div><div class="small muted" id="gtplw" style="margin-top:4px"></div>` : ''}
    <div class="nestep opt"><b>${gfx && MG.library.length ? 4 : 3}</b>${gfx ? t('Length, format, song, look') : t('Length, format')} ${optTag(t('30 s, Claude picks the format unless you change it'))}</div>
    <div class="nedet"><label>${t('Length')}</label><div class="seg" id="glen">${[['15', '15 s'], ['30', '30 s'], ['45', '45 s'], ['60', '1 min'], ['90', '1:30']].map(([v, l]) => `<button data-v="${v}">${l}</button>`).join('')}</div>
      <label>${t('Format')}</label><div class="seg" id="gfmt">${[['', t('Claude picks')], ['vertical', t('Vertical 9:16')], ['horizontal', t('Horizontal 16:9')], ['square', t('Square')]].map(([v, l]) => `<button data-v="${v}">${l}</button>`).join('')}</div>
      ${gfx ? `<label>${t('Song')}</label><div class="row" style="gap:8px"><select id="gsong" style="max-width:420px"><option value="">${t('no song / I put one in the folder later')}</option>${G.songs.map(x => `<option value="${esc(x.rel)}">${esc(x.name)}</option>`).join('')}</select>
        ${G.last_song ? `<button class="fchip" id="glast" title="${ta(G.songs.find(x => x.rel === G.last_song)?.name || '')}">${t('The song from last time')}</button>` : ''}</div>
      ${(G.looks || []).length ? `<label>${t('Look')}</label><div class="seg" id="glook">${[['', t('Claude picks')], ...G.looks.map(lk => [lk.id, t(lk.name), lk.palette]), ['surprise', t('Surprise me')]].map(([v, l, pal]) => `<button data-v="${esc(v)}">${pal ? pal.map(c => `<span class="lkdot" style="background:${esc(c)}"></span>`).join('') : ''}${esc(l)}</button>`).join('')}</div>` : ''}
      <label>${t('Colours')}</label><input type="text" id="gcol" placeholder="${ta('optional - e.g. black, white and my orange #ff6a00; font: Inter')}" style="max-width:420px">` : ''}</div>
    <div class="nestep"><b>${gfx && MG.library.length ? 5 : 4}</b>${t('Its name')}</div>
    <div class="row"><input type="text" id="gname" value="${esc(pre.name || n0)}" style="max-width:320px"><span class="small muted">${t('a folder in projects - a logo or a song you put there, Claude can use')}</span></div>
    <div class="row" style="margin-top:16px"><button class="btn pri big" id="ggo"><svg class="i"><use href="#i-claude"/></svg>${gfx ? t('Make it with Claude') : t('Plan it with Claude')}</button>
      <span class="small muted">${gfx ? t('Claude shows you the scenes first, then renders it. It can take an hour or more.') : t('Claude shows you the shot list first, then writes the prompts.')}</span></div>`, el => {
    const seg = (id, key) => { const b = $(id, el); const paint = () => $$('button', b).forEach(x => x.classList.toggle('on', x.dataset.v === st[key]));
      $$('button', b).forEach(x => x.onclick = () => { st[key] = x.dataset.v; paint(); }); paint(); };
    seg('#glen', 'length'); seg('#gfmt', 'format');
    st.look = '';
    if ($('#glook', el)) seg('#glook', 'look');
    if ($('#glast', el)) $('#glast', el).onclick = () => { $('#gsong', el).value = G.last_song; };
    stylePicker($('#gstp', el), st, {S, purpose: gfx ? 'graphics' : 'ai', onChange: () => tplDraw()});
    // 0.5.0: the Motion Graphics templates that fit the words (GET /api/motion/pick, while typing): the picked ones
    // (a click) are what Claude must use; none picked + no style video = Claude starts from the suggested ones
    let sug = [], all = false;
    const tplDraw = () => {
      const box = $('#gtpl', el);
      if (!box) return;
      const byId = Object.fromEntries(MG.library.map(tp => [tp.id, tp]));
      const ids = all ? MG.library.map(tp => tp.id) : [...new Set([...st.tpl, ...sug.filter(s => s.score > 0).map(s => s.id)])];
      box.innerHTML = ids.map(id => byId[id]).filter(Boolean).map(tp => `<button class="fchip${st.tpl.includes(tp.id) ? ' on' : ''}${!st.tpl.includes(tp.id) && sug.some(s => s.id === tp.id && s.score > 0) ? ' sug' : ''}" data-t="${esc(tp.id)}" title="${ta(tp.what || '')}">${esc(t(tp.name))}</button>`).join('')
        + `<button class="fchip sm ghostc" id="gtplall">${all ? t('fewer') : t('all {n}…', {n: MG.library.length})}</button>`;
      const blind = !st.like.length;
      $('#gtplw', el).innerHTML = st.tpl.length ? tn(st.tpl.length, 'Claude uses {n} picked template and adds what they do not cover.', 'Claude uses {n} picked templates and adds what they do not cover.')
        : blind ? (sug.some(s => s.score > 0) ? t('None picked: Claude starts from the suggested ones (dashed) - the ones that fit your words.') : t('None picked: Claude picks the templates that fit what you write above.'))
        : t('None picked: Claude follows the style video(s) and uses a template where it fits.');
      $$('[data-t]', box).forEach(b => b.onclick = () => {
        const id = b.dataset.t;
        st.tpl = st.tpl.includes(id) ? st.tpl.filter(x => x !== id) : st.tpl.length < 12 ? [...st.tpl, id] : st.tpl;
        tplDraw();
      });
      $('#gtplall', box).onclick = () => { all = !all; tplDraw(); };
    };
    const tplSuggest = debounce(async () => {
      const w = $('#gwant', el).value + ' ' + ($('#gtext', el) ? $('#gtext', el).value : '');
      try { sug = w.trim() ? (await api('/api/motion/pick?n=6&want=' + encodeURIComponent(w))).picks : []; } catch (e) { sug = []; }
      tplDraw();
    }, 350);
    if ($('#gtpl', el)) { tplDraw(); $('#gwant', el).addEventListener('input', tplSuggest); if ($('#gtext', el)) $('#gtext', el).addEventListener('input', tplSuggest); if ($('#gwant', el).value) tplSuggest(); }
    if ($('#gtool', el)) $('#gtool', el).onchange = e => { $('#gtool2', el).hidden = e.target.value !== 'other'; };
    $('#gwant', el).focus();
    $('#ggo', el).onclick = async () => {
      const want = $('#gwant', el).value.trim();
      if (!want) { toast(t('Say what the video is about first'), 'err'); $('#gwant', el).focus(); return; }
      const tool = $('#gtool', el) ? ($('#gtool', el).value === 'other' ? $('#gtool2', el).value : $('#gtool', el).value) : '';
      try {
        const r = await api('/api/generate/request', {kind, name: $('#gname', el).value, want, text: $('#gtext', el) ? $('#gtext', el).value : '',
          like: st.like, length_s: st.length || null, format: st.format || null, music: $('#gsong', el) ? $('#gsong', el).value : '',
          tool, colours: $('#gcol', el) ? $('#gcol', el).value : '', templates: gfx ? st.tpl : [], look: gfx ? st.look : ''});
        openClaude(r.command, 'generate', r.project);
        closeModal(); location.hash = '#/project/' + encodeURIComponent(r.project);
      } catch (e) { toast(e.message, 'err'); }
    };
  }, 'wide');
}
// ============================================================================================ Motion Graphics (0.5.0)
// the user (2026-10-16): "turn the Swishy reference clips (in the refs folder) I captured into a reusable Motion
// Graphics library, add a Motion Graphics section to the sidebar, and make Generate use those templates as well when
// generating blindly". GET /api/motion = data.motion(): the library = MotionLab's own HyperFrames templates
// (tools\overlays\motion\<id>: settings, picture, the clips each was learned from) + the packs of captured clips
// (analysis\templates\<pack>: measured with no Claude, Claude's cards). A template goes into a video like any graphic
// (job overlay_new, sized like the video's edit) or into the Generator (generate_request.json "templates").
const MKIND = {text: t('Text'), numbers: t('Numbers'), charts: t('Charts'), lists: t('Lists'), ui: t('Buttons & UI'), chat: t('Chat'),
  social: t('Social'), music: t('Music'), logo: t('Logo'), photos: t('Photos'), places: t('Places'), background: t('Backgrounds'), transitions: t('Transitions'),
  lower_thirds: t('Lower thirds'), callouts: t('Call-outs'), broadcast: t('News & broadcast'), promo: t('Promo & sale')};
const mkind = k => MKIND[k] || k;
const MSTATUS = [['', t('All|clips')], ['built', t('Rebuilt')], ['p1', t('Next to rebuild')], ['p2', t('Later')], ['p3', t('Style only')]];
const mclipStatus = it => it.built.length ? 'built' : it.still ? 'still' : 'p' + ((it.card || {}).rebuild || 2);
const MSTATUS_WORD = {built: t('rebuilt'), still: t('a still capture'), p1: t('next to rebuild'), p2: t('later'), p3: t('style only')};
const mdefaults = t => { const v = {}; (t.settings || []).forEach(s => { v[s.id] = s.default; }); return v; };
async function pageMotion(main, tab, open) {
  const [M, LGD] = await Promise.all([api('/api/motion'), logoLoad().catch(() => ({logos: [], groups: {}}))]);
  tab = ['learned', 'logos'].includes(tab) ? tab : 'templates';
  const L = M.library, clips = M.packs.flatMap(p => p.items.map(it => ({...it, pack: p.pack})));
  const todo = clips.filter(it => mclipStatus(it) === 'p1' || mclipStatus(it) === 'p2');   // the skill does 1s first
  main.innerHTML = `<div class="head"><div><h1>${t('Motion Graphics')}</h1><div class="sub">${t('Designed motion to reuse - learned from pro template clips, or made for what creators use most, as MotionLab\'s own graphics. Change the words and colours, put one in a video, or let the Generator build a video from them.')}</div></div>
      ${todo.length && M.packs.length ? `<div class="row">${claudeBtn(`/generate-video templates ${M.packs[0].pack}`, tn(Math.min(todo.length, 8), 'Rebuild the next {n} with Claude', 'Rebuild the next {n} with Claude'), 'generate', 'templates', 'cl')}</div>` : ''}</div>
    <div class="tabs"><a href="#/motion" class="${tab === 'templates' ? 'on' : ''}">${t('Templates')} <span class="dim">${L.length}</span></a>
      <a href="#/motion/learned" class="${tab === 'learned' ? 'on' : ''}">${t('Learned from')} <span class="dim">${clips.length}</span></a>
      <a href="#/motion/logos" class="${tab === 'logos' ? 'on' : ''}">${t('Logos')} <span class="dim">${LGD.logos.length}</span></a></div>
    <div id="mgbody"></div>`;
  const body = $('#mgbody', main);
  if (tab === 'templates') motionTemplates(body, M, L, clips);
  else if (tab === 'logos') motionLogos(body, M, LGD);
  else motionClips(body, M, clips);
  if (open) { const tp = L.find(x => x.id === open); if (tp) motionModal(tp, M); }
}
function motionTemplates(body, M, L, clips) {
  if (!L.length) {
    body.innerHTML = emptyHero('motion', t('No templates yet'), t('Templates are rebuilt from the clips under “Learned from” - Claude rebuilds them in batches.'), '');
    return;
  }
  let kf = '';
  try { kf = localStorage.getItem('ml.mkind') || ''; } catch (e) { /* all */ }
  const draw = () => {
    const ks = [...new Set(L.map(tp => tp.kind))];
    if (kf && !ks.includes(kf)) kf = '';
    body.innerHTML = `<div class="hint" style="margin-bottom:10px">${t('Click one to play it and try your own words. Most were learned from the clips they name - their timing, eases and layout measured; the MotionLab originals fill the kinds template sites offer most (lower thirds, transitions, call-outs...). All are MotionLab\'s own graphics: free to use in any video.')}</div>
      <div class="row pfilters">${[['', t('All|templates')], ...ks.map(k => [k, mkind(k)])].map(([k, l]) => `<button class="fchip${k === kf ? ' on' : ''}" data-k="${esc(k)}">${esc(l)} <span class="dim">${k ? L.filter(tp => tp.kind === k).length : L.length}</span></button>`).join('')}</div>
      <div class="mggrid">${L.filter(tp => !kf || tp.kind === kf).map(tp => `<div class="mgc" data-id="${esc(tp.id)}" tabindex="0">${newTag(`m:${tp.id}@${Math.round(tp.created || 0)}`, tp.created)}
        <div class="mgpic">${tp.thumb ? `<img src="${fileUrl(tp.thumb)}?v=${tp.thumb_v}" alt="" loading="lazy">` : `<span class="dim small">${t('no picture yet')}</span>`}</div>
        <div class="row sp" style="margin-top:8px"><b>${esc(t(tp.name))}</b><span class="chip">${esc(mkind(tp.kind))}</span></div>
        <div class="small muted mgwhat">${esc(t(tp.what || ''))}</div>
        <div class="small dim">${dec(tp.frames / tp.fps, 1)} s · ${(tp.sources || []).length ? tn(tp.sources.length, 'learned from {n} clip', 'learned from {n} clips') : t('MotionLab original')}</div></div>`).join('')}</div>`;
    $$('[data-k]', body).forEach(b => b.onclick = () => { kf = b.dataset.k; try { localStorage.setItem('ml.mkind', kf); } catch (e) { /* not kept */ } draw(); });
    $$('.mgc', body).forEach(c => c.onclick = c.onkeydown = e => { if (e.type === 'keydown' && e.key !== 'Enter') return; motionModal(L.find(tp => tp.id === c.dataset.id), M); });
  };
  draw();
}
// Motion Graphics > Logos (the logo library, 2026-10-16): every logo with its versions; + picks several for a logo wall
let LG_PICKED = [];
function motionLogos(body, M, D) {
  if (!D.logos.length) {
    body.innerHTML = emptyHero('motion', t('No logos yet'), t('Put SVG logos in refs\\logos (one folder per logo) and ask Claude to add them to the library.'), '');
    return;
  }
  const wall = (M.library || []).find(tp => tp.id === 'logo-wall');
  let q = '', g = '';
  body.innerHTML = `<div class="hint" style="margin-bottom:10px">${t('Real logos of apps, platforms and AI tools for your graphics - sharp at any size, in their own colours or in one colour of yours. In a graphic\'s settings, <b>Pick a logo…</b> puts one in; in a text, write it like <code>:youtube:</code>. They are trademarks of their owners: use them to name the products a video is about.')}</div>
    <div class="lgtray" id="lgtray"></div>
    <div class="row" style="gap:8px;margin:10px 0;flex-wrap:wrap"><input type="search" id="lgq" placeholder="${ta('Search: youtube, editing, ai…')}" style="width:240px">
      <div class="row pfilters" style="margin:0">${[['', t('All|logos')], ...Object.keys(D.groups || {}).map(k => [k, LOGO_GROUPS[k] || k])].map(([k, l]) => `<button class="fchip${k ? '' : ' on'}" data-g="${esc(k)}">${esc(l)} <span class="dim">${k ? D.logos.filter(x => x.group === k).length : D.logos.length}</span></button>`).join('')}</div></div>
    <div class="lggrid big" id="lgall"></div>`;
  const tray = $('#lgtray', body), grid = $('#lgall', body);
  const name = id => (D.logos.find(x => x.id === id) || {name: id}).name;
  const drawTray = () => {
    tray.innerHTML = LG_PICKED.length ? `<span class="small muted">${t('Picked')}</span> ${LG_PICKED.map(id => `<span class="tag lgtag">${esc(name(id))}<button data-unpick="${esc(id)}" title="${ta('Take it out')}">✕</button></span>`).join('')}
      ${wall ? `<button class="btn pri sm" id="lgwall">${t('Make a logo wall with them')}</button>` : ''}<button class="btn sm" id="lgcopy" title="${ta('For a text setting')}">${t('Copy as :logos:')}</button><button class="btn sm" id="lgclr">${t('Clear')}</button>`
      : `<span class="small muted">${t('Pick several with <b>+</b> to make a logo wall from them.')}</span>`;
    $$('[data-unpick]', tray).forEach(b => b.onclick = () => { LG_PICKED = LG_PICKED.filter(x => x !== b.dataset.unpick); drawTray(); drawGrid(); });
    if ($('#lgwall', tray)) $('#lgwall', tray).onclick = () => motionModal(wall, M, {logos: LG_PICKED.join('|'), title: ''});
    if ($('#lgcopy', tray)) $('#lgcopy', tray).onclick = () => copy(LG_PICKED.map(id => `:${id}:`).join(' '));
    if ($('#lgclr', tray)) $('#lgclr', tray).onclick = () => { LG_PICKED = []; drawTray(); drawGrid(); };
  };
  const drawGrid = () => {
    const L = logoFind(D.logos.filter(lg => !g || lg.group === g), q);
    grid.innerHTML = L.map(lg => { const on = LG_PICKED.includes(lg.id);
      return `<div class="mgc lgc${on ? ' on' : ''}" data-id="${esc(lg.id)}" tabindex="0"><button class="lgadd" data-add="${esc(lg.id)}" title="${on ? ta('Picked - click to take it out') : ta('Pick it for a logo wall')}">${on ? '✓' : '+'}</button>
        ${logoTile(lg, '')}<div style="margin-top:6px"><b>${esc(lg.name)}</b></div><div class="small dim">${esc(LOGO_GROUPS[lg.group] || lg.group)} · ${plural(Object.keys(lg.variants).length, 'version')}</div></div>`; }).join('')
      || `<div class="small muted">${t('No logo fits those words.')}</div>`;
  };
  grid.onclick = grid.onkeydown = e => {
    if (e.type === 'keydown' && e.key !== 'Enter') return;
    const a = e.target.closest('[data-add]');
    if (a) { e.stopPropagation(); LG_PICKED = LG_PICKED.includes(a.dataset.add) ? LG_PICKED.filter(x => x !== a.dataset.add) : [...LG_PICKED, a.dataset.add].slice(0, 12); drawTray(); drawGrid(); return; }
    const c = e.target.closest('.lgc');
    if (c) logoModal(D.logos.find(x => x.id === c.dataset.id), () => { drawTray(); drawGrid(); });
  };
  const qi = $('#lgq', body);
  qi.oninput = () => { q = qi.value; drawGrid(); };
  $$('[data-g]', body).forEach(b => b.onclick = () => { g = b.dataset.g; $$('[data-g]', body).forEach(x => x.classList.toggle('on', x === b)); drawGrid(); });
  drawTray();
  drawGrid();
}
function logoModal(lg, after) {
  const vs = Object.keys(lg.variants);
  modal(`<div class="row" style="gap:10px;padding-right:28px"><h2 style="margin:0">${esc(lg.name)}</h2><span class="chip">${esc(LOGO_GROUPS[lg.group] || lg.group)}</span></div>
    <p class="small muted" style="margin:6px 0 12px">${t('In a logo setting write <code>{id}</code> - the graphic picks the version that stands out on its background - or one version below. In a text write <code>:{id}:</code>.', {id: esc(lg.id)})}</p>
    <div class="lgvars">${vs.map(v => `<div class="lgvar"><div class="lgpair"><span class="lgimg"><img src="${logoSrc(lg, v)}" alt=""></span><span class="lgimg dk"><img src="${logoSrc(lg, v)}" alt=""></span></div>
      <div class="small"><b>${esc(v)}</b> <span class="muted">- ${esc(LOGO_VARIANT[v] || v)}</span></div>
      <div class="row" style="gap:6px;margin-top:4px"><code class="small">${esc(lg.id)}/${esc(v)}</code><button class="btn sm" data-copy="${esc(lg.id)}/${esc(v)}">${t('Copy')}</button></div></div>`).join('')}</div>
    <div class="row" style="margin-top:14px"><button class="btn pri" id="lgpick">${LG_PICKED.includes(lg.id) ? t('Picked for a logo wall - take it out') : t('Pick it for a logo wall')}</button><button class="btn" data-copy=":${esc(lg.id)}:">${t('Copy :{id}:', {id: esc(lg.id)})}</button></div>
    <div class="small dim" style="margin-top:10px">${t('A trademark of its owner - use it to name the product your video is about.')}</div>`, el => {
    $$('[data-copy]', el).forEach(b => b.onclick = () => copy(b.dataset.copy));
    $('#lgpick', el).onclick = () => { LG_PICKED = LG_PICKED.includes(lg.id) ? LG_PICKED.filter(x => x !== lg.id) : [...LG_PICKED, lg.id].slice(0, 12); closeModal(); after(); };
  });
}
function motionClips(body, M, clips) {
  let kf = '', sf = '';
  const kinds = [...new Set(clips.map(c => c.kind))];
  const draw = () => {
    const shown = clips.filter(c => (!kf || c.kind === kf) && (!sf || mclipStatus(c) === sf || (sf === 'p3' && c.still)));
    body.innerHTML = `<div class="hint" style="margin-bottom:10px">${t('The template clips you captured (they stay on this PC, untouched). MotionLab measured each one with no Claude - its moves with frame + timecode, the ease of each, how long it holds - and Claude wrote what it is and whether it is worth rebuilding. Hover a clip to play it.')}</div>
      <div class="row pfilters">${[['', t('All|clips')], ...kinds.map(k => [k, k.replace(/-/g, ' ')])].map(([k, l]) => `<button class="fchip${k === kf ? ' on' : ''}" data-k="${esc(k)}">${esc(l)} <span class="dim">${k ? clips.filter(c => c.kind === k).length : clips.length}</span></button>`).join('')}</div>
      <div class="row pfilters">${MSTATUS.map(([k, l]) => `<button class="fchip sm${k === sf ? ' on' : ''}" data-s="${k}">${l} <span class="dim">${k ? clips.filter(c => mclipStatus(c) === k || (k === 'p3' && c.still)).length : clips.length}</span></button>`).join('')}</div>
      <div class="mcgrid">${shown.map(c => { const s = mclipStatus(c);
        return `<div class="mcc" data-id="${esc(c.pack + '/' + c.id)}" tabindex="0">
        <div class="mcpic">${c.poster ? `<img src="${fileUrl(c.poster)}" alt="" loading="lazy" style="width:100%;height:100%;object-fit:contain;display:block">` : ''}</div>
        <div class="row sp" style="margin-top:6px"><b class="small">${esc(c.name)}</b><span class="mst mst-${s}">${MSTATUS_WORD[s]}</span></div>
        <div class="small muted mgwhat">${esc((c.card || {}).what || '')}</div>
        <div class="small dim">${dec(c.seconds, 1)} s · ${c.still ? t('no motion caught') : plural(c.moves, 'move')}${c.loops ? ` · ${t('loops')}` : ''}</div></div>`; }).join('') || `<div class="empty">${t('Nothing here.')}</div>`}</div>`;
    $$('[data-k]', body).forEach(b => b.onclick = () => { kf = b.dataset.k; draw(); });
    $$('[data-s]', body).forEach(b => b.onclick = () => { sf = b.dataset.s; draw(); });
    // a picture per card (a lazy <img>: a video's poster loads at once, for hundreds of clips), the clip itself made
    // on the first hover and kept (it goes on where it stopped, as before)
    $$('.mcc', body).forEach(card => {
      let v = null;
      if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
        card.onmouseenter = () => {
          if (!v) {
            const c = clips.find(x => x.pack + '/' + x.id === card.dataset.id);
            v = document.createElement('video');
            Object.assign(v, {muted: true, loop: true, playsInline: true, src: fileUrl(c.file)});
            if (c.poster) v.poster = fileUrl(c.poster);
            $('.mcpic', card).replaceChildren(v);
          }
          v.play().catch(() => {});
        };
        card.onmouseleave = () => { if (v) v.pause(); };
      }
      card.onclick = card.onkeydown = e => { if (e.type === 'keydown' && e.key !== 'Enter') return; motionClipModal(clips.find(c => c.pack + '/' + c.id === card.dataset.id), M); };
    });
  };
  draw();
}
// one template: its live preview (the page's own GSAP, the form's values - nothing rendered, nothing saved), what it
// is for, the clips it was learned from playing beside it; Use in a video / Make a video with it
function motionModal(tp, M, init) {
  const S = (tp.settings || []).map(s => ({...s, value: init && s.id in init ? init[s.id] : s.default}));
  modal(`<div class="mgm"><div class="mgprev" id="mgprev"></div>
    <div><div class="row" style="gap:10px;padding-right:28px"><h2 style="margin:0">${esc(t(tp.name))}</h2><span class="chip">${esc(mkind(tp.kind))}</span></div>
      <p style="margin:8px 0">${esc(t(tp.what || ''))}</p>
      ${(tp.use_for || []).length ? `<div class="small muted">${t('Good for: {tags}', {tags: tp.use_for.map(u => `<span class="tag">${esc(u)}</span>`).join(' ')})}</div>` : ''}
      ${tp.motion ? `<div class="small muted" style="margin-top:4px">${t('Motion: {motion} · {frames} frames at {fps} fps, {w}×{h} - it takes any size', {motion: esc(tp.motion), frames: tp.frames, fps: tp.fps, w: tp.width, h: tp.height})}</div>` : ''}
      <div class="row" style="margin-top:12px"><button class="btn pri" id="mguse">${t('Use in a video…')}</button><button class="btn" id="mggen"><svg class="i"><use href="#i-claude"/></svg>${t('Make a video with it')}</button></div>
      <h3>${t('Try your words')}</h3><div class="small muted" style="margin:-2px 0 6px">${t('The preview follows at once; these values go with it into a video.')}</div>
      <div class="gset">${S.map(s => `<label title="${esc(s.id)}">${esc(t(s.label || s.id))}</label><div>${gsetInput(s)}</div>`).join('')}</div>
      ${(tp.sources || []).length ? `<h3>${t('Learned from')}</h3><div class="mgsrc">${tp.sources.map(s => `<div class="mgs">${s.file ? `<video src="${fileUrl(s.file)}" muted loop autoplay playsinline></video>` : ''}
        <div class="small"><b>${esc((s.clip || '').replace(/^[\w-]+?__/, '').replace(/-/g, ' '))}</b><div class="muted">${esc(s.what || '')}</div></div></div>`).join('')}</div>`
        : `<h3>${t('A MotionLab original')}</h3><div class="small muted">${tp.origin ? t('Not learned from a clip: made for one of the template kinds creators use most ({origin}).', {origin: esc(tp.origin.split(' - ')[0])})
          : t('Not learned from a clip: made for one of the template kinds creators use most.')}</div>`}
    </div></div>`, el => {
    const vals = () => { const v = mdefaults(tp); $$('[data-set]', el).forEach(i => { v[i.dataset.set] = gsetValue(i); }); return v; };
    const live = livePreview($('#mgprev', el), tp, vals);
    const stop = live.stop;
    $$('[data-set]', el).forEach(i => { i.oninput = i.onchange = () => live.refresh(); });
    $$('.mgs video', el).forEach(v => { if (matchMedia('(prefers-reduced-motion: reduce)').matches) v.removeAttribute('autoplay'); });
    $('#mguse', el).onclick = () => { stop(); motionUseModal(tp, vals(), () => motionModal(tp, M)); };
    $('#mggen', el).onclick = () => { stop(); generateModal('graphics', {templates: [tp.id]}); };
  }, 'wide');
}
async function motionUseModal(tp, values, back) {
  const ps = (await api('/api/projects')).filter(p => !inGenerator(p) || p.plans.length);
  const changed = Object.fromEntries(Object.entries(values).filter(([k, v]) => v !== mdefaults(tp)[k]));
  // an overlay (a button, a pin, a like...) goes over the footage: see-through unless the user painted it on purpose
  if (tp.overlay && !('background' in changed) && (tp.settings || []).some(s => s.id === 'background')) changed.background = false;
  modal(`<h2>${t('Use “{name}” in a video', {name: esc(t(tp.name))})}</h2>
    <div class="small muted">${t('A copy goes into the video, sized like its edit (or {w}×{h} without one) and rendered right away; change it later on the video\'s Graphics tab.', {w: tp.width, h: tp.height})}${tp.overlay ? ' ' + t('It goes over your footage, see-through.') : ''}</div>
    ${ps.length ? `<div class="row" style="margin-top:12px"><label>${t('Video')} <select id="muv">${ps.map(p => `<option value="${esc(p.name)}">${esc(p.label || p.name)}</option>`).join('')}</select></label>
      <label>${t('Name')} <input id="mun" value="${esc(tp.id)}" style="width:200px"></label></div>
      ${Object.keys(changed).length ? `<div class="small" style="margin-top:6px">${t('With your words: {tags}', {tags: Object.entries(changed).map(([k, v]) => `<span class="tag">${esc(k)}: ${esc(String(v)).slice(0, 40)}</span>`).join(' ')})}</div>` : ''}
      <div class="row" style="margin-top:12px"><button class="btn pri" id="mugo">${t('Add and render')}</button><span id="mumsg" class="small"></span></div><pre class="log" hidden></pre>`
      : `<div class="empty" style="margin-top:12px">${t('No videos yet - start one in the Editor.')}</div>`}`, m => {
    const go = $('#mugo', m);
    if (!go) return;
    go.onclick = async () => {
      const project = $('#muv', m).value, name = $('#mun', m).value.trim();
      const j = await startJob('overlay_new', {project, graphic: tp.id, name, values: changed}, false);
      if (!j) return;
      go.disabled = true; const pre = $('pre.log', m); pre.hidden = false;
      followJob(j.id, pre, jj => {
        if (jj.status === 'done') { closeModal(); location.hash = `#/project/${encodeURIComponent(project)}/graphics`; }
        else { $('#mumsg', m).innerHTML = `<span class="bad">${t('did not work - see the log')}</span>`; go.disabled = false; }
      });
    };
  });
  modalBack(back);
}
function motionClipModal(c, M) {
  const tpl = M.library.filter(tp => c.built.includes(tp.id)), card = c.card || {};
  const pct = Math.round(100 * (c.moving_share || 0));
  const moves = c.loops ? tn(c.moves, '{n} move, moving {pct} % of the time, loops', '{n} moves, moving {pct} % of the time, loops', {pct})
    : tn(c.moves, '{n} move, moving {pct} % of the time', '{n} moves, moving {pct} % of the time', {pct});
  const eases = t('eases: {eases}', {eases: Object.entries(c.eases || {}).map(([k, n]) => `${esc(t(k))} ×${n}`).join(', ') || '-'});
  modal(`<div class="mgm"><div class="mgprev"><video src="${fileUrl(c.file)}" controls loop autoplay muted playsinline style="width:100%;max-height:560px;border-radius:8px;background:#000"></video></div>
    <div><div class="row" style="gap:10px;padding-right:28px"><h2 style="margin:0">${esc(c.name)}</h2><span class="mst mst-${mclipStatus(c)}">${MSTATUS_WORD[mclipStatus(c)]}</span></div>
      <div class="small muted" style="margin-top:4px">${t('{kind} · {frames} frames at {fps} fps ({s} s) · {w}×{h}', {kind: esc(c.kind.replace(/-/g, ' ')), frames: c.frames, fps: c.fps, s: dec(c.seconds, 2), w: c.width, h: c.height})}</div>
      ${card.what ? `<p style="margin:10px 0"><span class="clchip">Claude</span> ${esc(card.what)}</p>` : ''}
      ${(card.use_for || []).length ? `<div class="small muted">${t('Good for: {tags}', {tags: card.use_for.map(u => `<span class="tag">${esc(u)}</span>`).join(' ')})}</div>` : ''}
      ${card.note ? `<div class="small muted" style="margin-top:4px">${esc(card.note)}</div>` : ''}
      ${tpl.length ? `<div style="margin-top:10px">${t('Rebuilt as {links}', {links: tpl.map(tp => `<a href="#/motion/templates/${esc(tp.id)}">${esc(t(tp.name))}</a>`).join(', ')})}</div>` : ''}
      <h3>${t('Measured by MotionLab')} <span class="mlchip">${t('MotionLab · no Claude')}</span></h3>
      <div class="small">${c.still ? t('A still capture: the clip has fewer than 15 frames, so no motion was caught.')
        : `${moves}; ${eases}${c.alive_in_holds != null ? '; ' + t('something still moves in {pct} % of the holds', {pct: Math.round(100 * c.alive_in_holds)}) : ''}.`}</div>
      ${c.sheet ? `<div style="margin-top:8px"><img src="${fileUrl(c.sheet)}" alt="${ta('contact sheet')}" class="mgsheet" title="${ta('every move\'s start / fastest / end frame, frame + timecode - click to enlarge')}"></div>` : ''}
      ${(c.colours || {}).main ? `<div class="row" style="margin-top:8px;gap:4px">${c.colours.main.map(([h, s]) => `<span class="sw" title="${esc(h)} ${Math.round(100 * s)} %" style="width:22px;height:22px;border-radius:4px;background:${esc(h)};display:inline-block;border:1px solid var(--line2)"></span>`).join('')}</div>` : ''}
    </div></div>`, el => {
    const im = $('.mgsheet', el);
    if (im) im.onclick = () => lightbox([{src: c.sheet, cap: t('{id} - contact sheet', {id: c.id})}], 0);
  }, 'wide');
}

const PFILTERS = [['', t('All|prompts')], ['tool', t('Needs another tool')], ['own', t('No other tool')], ['todo', t('Not checked yet')]];
const pfilterOk = (p, f) => !f || (f === 'tool' ? !!ptool(p) : f === 'own' ? !ptool(p) : !p.structure && !p.review);
async function pagePrompts(main, arg) {               // every kind in one grid; a click opens the prompt
  await api('/api/script/tidy', {}).catch(() => {});     // an improved script replaces its paste (Improve my script)
  const ctx = {R: await api('/api/prompts')};
  let q = '', pf = '';
  try { pf = localStorage.getItem('ml.pfilter') || ''; } catch (e) { /* no storage: all */ }
  if (!PFILTERS.some(([k]) => k === pf)) pf = '';
  const any = ctx.R.items.length;
  main.innerHTML = `<div class="head"><div><div class="crumb"><a href="#/generate">${t('Generator')}</a> /</div><h1>${t('Prompt library')}</h1><div class="sub">${t('Briefs for Claude, prompts for AI video and image tools, hooks and scripts. Click one to open it.')}</div></div>
      ${any ? `<div class="row"><input type="search" id="pq" placeholder="${ta('Search your prompts…')}" style="width:230px"><button class="btn pri" id="padd">${t('Add prompts')}</button>
        <button class="btn" data-open="${esc(ctx.R.folder)}" data-reveal><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button></div>` : ''}</div>
    ${any ? '<div class="row pfilters" id="pfil"></div><div id="ptodo"></div>' : ''}<div id="plist" class="pgrid"></div>`;
  if (!any) {
    $('#plist', main).className = '';
    $('#plist', main).innerHTML = emptyHero('prompts', t('Keep your best prompts here'), t('Paste one you use, attach a creator\'s guide, or let Claude write one from zero. Claude checks each part and helps you improve it.'),
      `<button class="btn pri big" id="padd">${t('Add prompts')}</button>`);
    $('#padd', main).onclick = () => addPromptsModal(ctx.R);
    return;
  }
  $('#padd', main).onclick = () => addPromptsModal(ctx.R);
  const row = p => promptCard(p, ctx.R);
  const draw = () => {
    const all = ctx.R.items, list = $('#plist', main);
    $('#pfil', main).innerHTML = PFILTERS.map(([k, l]) => { const n = all.filter(p => pfilterOk(p, k)).length;
      return k && !n ? '' : `<button class="fchip${k === pf ? ' on' : ''}" data-pf="${k}">${l} <span class="dim">${n}</span></button>`; }).join('');
    $$('[data-pf]', main).forEach(b => b.onclick = () => { pf = b.dataset.pf; try { localStorage.setItem('ml.pfilter', pf); } catch (e) { /* not kept */ } draw(); });
    const todo = all.filter(p => pfilterOk(p, 'todo')).map(p => p.id);
    $('#ptodo', main).innerHTML = pf === 'todo' && todo.length ? `<div class="small muted pftodo">${t('Claude reads each one and marks what is clear, vague or missing, with a tip.')} ${todo.length === 1 ? claudeBtn(optCmd({id: todo[0], kind: todo[0].split('-')[0]}), t('Optimize with Claude'), optTask({kind: todo[0].split('-')[0]}), todo[0]) : claudeBtn(`/write-prompt analyse ${todo.join(' ')}`, t('Check these {n} with Claude', {n: todo.length}), 'prompt', 'analyse')}</div>` : '';
    const items = all.filter(p => pfilterOk(p, pf) && (!q || [p.id, p.title, p.title_auto, p.text, p.model, (p.source || {}).creator, KSHORT[p.kind], ...(p.tags || [])].join(' ').toLowerCase().includes(q)))
      .sort((a, b) => (b.updated || b.added || '').localeCompare(a.updated || a.added || '') || b.id.localeCompare(a.id));
    list.innerHTML = items.map(row).join('') || `<div class="empty">${q ? t('No prompt matches the search.') : t('Nothing here.')}</div>`;
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
// ---- Film it (2026-10-15, the user: "I record a video of me reading the script but the interface is very messy - do
// I go to Editor and select from a saved prompt? but it's not a prompt... and then where does it go?"): a script's
// road in one dialog - 1 film it (cue cards, a teleprompter, what to film besides you), 2 add the recording (copied
// into the video's folder; the original stays where it is), 3 edit it (the talking quick draft or Claude). The
// script and the video are linked (made_from.json), so its card shows Written > Filmed > Edited > Posted.
const CLIP_EXT = /\.(mp4|mov|mkv|m4v|avi|webm|mts|mxf|mp3|m4a|wav|aac|flac|ogg|jpe?g|png|webp|heic|heif|avif|bmp|tiff?|gif)$/i;
const PHOTO_EXT = /\.(jpe?g|png|webp|heic|heif|avif|bmp|tiff?|gif)$/i;     // 2026-10-24: a photo = a still shot
const CLIP_ACCEPT = 'video/*,audio/*,image/*,.mts,.mxf,.mkv,.heic,.heif,.avif';
// what a Mac / iPhone / Windows leaves next to clips (._IMG_0912.mov = 4 KB of Finder info, shown as a black clip):
// a hidden name or folder, Thumbs.db, desktop.ini - never copied in (the server refuses them too)
const isJunk = (name, path = '') => /^\./.test(name) || /^(thumbs\.db|desktop\.ini)$/i.test(name) || String(path).split('/').slice(0, -1).some(s => s.startsWith('.'));
// a folder picked (webkitdirectory) or dropped (folders inside folders too): every clip in it, in path order
// (numbers as numbers), named so two files of the same name in different folders both get in ("19 octubre_C0001.MP4")
async function clipsFromDrop(dt) {
  const entries = [...(dt.items || [])].map(i => i.webkitGetAsEntry && i.webkitGetAsEntry()).filter(Boolean);
  if (!entries.length || entries.every(e => e.isFile)) return {files: [...dt.files].map(f => ({file: f, path: f.name})), folders: false};
  const out = [];
  const walk = async (e, base) => {
    if (e.isFile) { const f = await new Promise((ok, bad) => e.file(ok, bad)); out.push({file: f, path: base + f.name}); return; }
    const rd = e.createReader();
    for (;;) {                                       // readEntries gives at most 100 at a time: until it is empty
      const batch = await new Promise((ok, bad) => rd.readEntries(ok, bad));
      if (!batch.length) break;
      for (const x of batch) await walk(x, base + e.name + '/');
    }
  };
  for (const e of entries) await walk(e, '');
  return {files: out, folders: true};
}
function clipNames(list) {                         // [{file, path}] -> the clips sorted, each with a unique name
  const L = list.filter(x => !isJunk(x.file.name, x.path) && CLIP_EXT.test(x.file.name))
    .sort((a, b) => a.path.localeCompare(b.path, undefined, {numeric: true, sensitivity: 'base'}));
  const dirs = x => x.path.split('/').slice(0, -1);
  const named = L.map(x => ({...x, name: x.file.name, up: 0}));
  for (let round = 0; round < 8; round++) {          // the same name twice: put the parent folder(s) in front
    const seen = {};
    named.forEach(x => { const k = x.name.toLowerCase(); (seen[k] = seen[k] || []).push(x); });
    const clash = Object.values(seen).filter(g => g.length > 1);
    if (!clash.length) break;
    clash.flat().forEach(x => { const d = dirs(x); if (x.up < d.length) { x.up++; x.name = [...d.slice(d.length - x.up), x.file.name].join('_'); } });
  }
  return {clips: named.map(x => ({file: x.file, name: x.name})), skipped: list.length - L.length};
}
const folderName = t => String(t || '').replace(/[^\p{L}\p{N}_.\- \[\]()&'+,]/gu, ' ').replace(/\.{2,}/g, '.')
  .replace(/\s+/g, ' ').trim().replace(/^[. ]+|[. ]+$/g, '').slice(0, 60) || 'my talking video';
// a file the user picked or dropped -> projects\<p>\ (POST, raw body; the server never overwrites a clip)
function uploadClip(project, file, prompt, onProg, name = file.name) {   // name: the clip's name in the folder
  return new Promise((ok, bad) => {
    const x = new XMLHttpRequest();
    x.open('POST', `/api/project/${encodeURIComponent(project)}/upload?name=${encodeURIComponent(name)}${prompt ? '&prompt=' + encodeURIComponent(prompt) : ''}`);
    x.setRequestHeader('X-ML-Token', TOKEN);
    x.setRequestHeader('Content-Type', 'application/octet-stream');
    x.upload.onprogress = e => { if (e.lengthComputable && onProg) onProg(e.loaded / e.total); };
    x.onload = () => { let j = null; try { j = JSON.parse(x.responseText); } catch (e) { /* not JSON */ }
      if (x.status < 300) ok(j); else bad(new Error((j && j.error) || `${x.status} ${x.statusText}`)); };
    x.onerror = () => bad(new Error(t('{name}: the copy stopped - try again', {name: file.name})));
    x.send(file);
  });
}
// the road of a script: the videos made from it (GET /api/prompts "used": clips, renders, posted)
function scriptRoad(uses) {
  const any = k => uses.some(u => k === 'posted' ? u.posted : u[k] > 0);
  const st = {written: true, filmed: any('clips'), edited: any('renders'), posted: any('posted')};
  return {st, now: ['filmed', 'edited', 'posted'].find(k => !st[k]) || ''};
}
// the teleprompter: the lines to say, big, scrolling at a speaking rate (Space = start / pause, arrows = speed)
function teleprompter(lines) {
  const o = document.createElement('div'); o.className = 'tprompt';
  o.innerHTML = `<div class="tpbar"><b id="tpst">${t('Space or click to start')}</b><span class="small muted">${t('↑ ↓ speed · ← back · Esc close')}</span><span class="grow"></span>
      <span class="small" id="tpspd"></span><button class="btn sm" data-x>${t('Close')}</button></div>
    <div class="tpview"><div class="tpline"></div><div class="tptext">${lines.map(l => `<p>${esc(l.replace(/\s*\[check\]/gi, ''))}</p>`).join('')}</div></div>`;
  document.body.append(o);
  const view = $('.tpview', o), txt = $('.tptext', o), words = Math.max(1, lines.join(' ').split(/\s+/).length);
  let wpm = 150, run = false, y = 0, last = 0;
  const show = () => { $('#tpspd', o).textContent = t('{n} words a minute', {n: wpm}); $('#tpst', o).textContent = run ? t('Space = pause') : t('Space or click to start'); };
  const loop = ts => { if (!o.isConnected) return;
    if (run && last) { y += (txt.scrollHeight / words) * wpm / 60 * (ts - last) / 1000; view.scrollTop = y; if (view.scrollTop + view.clientHeight >= view.scrollHeight - 1) run = false, show(); }
    last = ts; requestAnimationFrame(loop); };
  const close = () => { o.remove(); window.removeEventListener('keydown', key, true); };
  const key = e => { const k = e.key;
    if (k === 'Escape') close(); else if (k === ' ') { run = !run; show(); } else if (k === 'ArrowUp') { wpm = Math.min(260, wpm + 10); show(); }
    else if (k === 'ArrowDown') { wpm = Math.max(60, wpm - 10); show(); } else if (k === 'ArrowLeft') { y = Math.max(0, y - view.clientHeight / 3); view.scrollTop = y; } else return;
    e.preventDefault(); e.stopPropagation(); };
  window.addEventListener('keydown', key, true);
  view.onclick = () => { run = !run; show(); };
  view.onwheel = () => { y = view.scrollTop; };
  $('[data-x]', o).onclick = close;
  show(); requestAnimationFrame(loop);
}
// Film it (2026-10-24, the user: "keep the teleprompter and other stuff but the step 3 make it "continue in editor" and
// it pop ups the new edit section but loading the prompt and videos i loaded in the film it section"): 1 the lines and
// the teleprompter, 2 the recording copied in, 3 New edit with both loaded - the edit itself is the Editor's only
async function filmItModal(p) {
  const [C, ps, PRM] = await Promise.all([api('/api/script/cards?id=' + encodeURIComponent(p.id)), api('/api/projects'), api('/api/prompts')]);
  const uses = (PRM.used || {})[p.id] || [], parts = C.parts;
  const said = parts.flatMap(x => x.lines), notes = parts.flatMap(x => x.notes.map(n => ({...n, head: x.head})));
  const toFilm = notes.filter(n => FILM_TAG.test(n.tag) && n.text);
  const inEdit = notes.filter(n => !toFilm.includes(n) && n.text);
  const checks = parts.filter(x => x.check || x.lines.some(l => /\[check\]/i.test(l)));
  const linked = uses.map(u => u.project).filter(n => ps.some(x => x.name === n));
  const st = {project: linked[0] || '', name: folderName(ptitle(p)), busy: false};
  while (!st.project && ps.some(x => x.name.toLowerCase() === st.name.toLowerCase())) st.name = st.name.replace(/( \d+)?$/, m => ` ${(+m || 1) + 1}`);
  const chk = `<span class="tpchk">${t('check')}</span>`;
  const card = x => `<div class="ficard">${x.head ? `<div class="fihead">${esc(x.head)}</div>` : ''}${x.lines.map(l => `<p>${esc(l).replace(/\[check\]/gi, () => chk)}</p>`).join('')}</div>`;
  const noteLi = n => `<li><b>${esc(n.tag)}</b> ${esc(n.text)}${n.head ? ` <span class="small dim">· ${esc(n.head)}</span>` : ''}</li>`;
  const clipsOpt = (x, from) => from ? t('{name} ({clips}) · from this script', {name: esc(pname(x)), clips: plural(x.clips, 'clip')}) : `${esc(pname(x))} (${plural(x.clips, 'clip')})`;
  modal(`<h2>${t('Film it')}</h2><div class="small muted" style="margin-top:-4px">${t('<b>{title}</b> - you film it with your phone or camera, add the recording here, and MotionLab cuts it.', {title: esc(ptitle(p))})}</div>
    <div class="sflow sflow-in">${flowSteps(uses, false)}</div>
    <div class="nestep"><b>1</b>${t('Film it')}</div>
    <div class="fi1"><div class="ficards">${parts.map(card).join('') || `<div class="empty">${t('No lines to say in this script.')}</div>`}</div>
      <div class="fiside"><div class="row"><button class="btn pri" id="fitp"><svg class="i"><use href="#i-scriptok"/></svg>${t('Teleprompter')}</button><button class="btn" id="ficopy"><svg class="i"><use href="#i-clipboard"/></svg>${t('Copy the lines')}</button></div>
        ${checks.length ? `<div class="fichk">${t('<b>Confirm before you film</b> - the lines marked {check} are facts only you know ({parts}).', {check: chk, parts: checks.map(x => esc(x.head || t('a line'))).join(', ')})}</div>` : ''}
        ${toFilm.length ? `<h4>${t('Film these too')}</h4><ul class="filist">${toFilm.map(noteLi).join('')}</ul>` : ''}
        ${inEdit.length ? `<h4>${t('The edit adds these <span class="small muted">- nothing to film</span>')}</h4><ul class="filist dim2">${inEdit.map(noteLi).join('')}</ul>` : ''}
        <h4>${t('While you film')}</h4><ul class="filist small">
          <li>${t('Phone at eye level, the light in front of you, look into the lens.')}</li>
          <li>${t('Vertical (9:16) for TikTok, Reels and Shorts; horizontal for YouTube.')}</li>
          <li>${t('Stumbled? Pause a second and say the whole sentence again. Claude keeps the good take; the quick draft keeps every take.')}</li>
          <li>${t('One long recording or one clip per part - both work.')}</li></ul></div></div>
    <div class="nestep"><b>2</b>${t('Add your recording')}</div>
    <div class="row"><select id="fiv" style="max-width:360px">${ps.map(x => `<option value="${esc(x.name)}">${clipsOpt(x, linked.includes(x.name))}</option>`).join('')}
        <option value="">${t('+ a new video…')}</option></select>
      <input type="text" id="finame" value="${esc(st.name)}" style="max-width:280px" title="${ta('the new video\'s name')}"></div>
    <div class="fidrops"><label class="fidrop" id="fidrop"><input type="file" id="fifile" multiple hidden accept="${CLIP_ACCEPT}">
      <b>${t('Drop your recording here')}</b><span class="small muted">${t('or click to choose it - several files are fine. It is copied in; your original stays where it is.')}</span></label>
      <label class="fidrop fidropf" title="${ta('Every video, photo and song in a folder, its sub-folders too')}"><input type="file" id="fidir" hidden webkitdirectory multiple>
        <svg class="i"><use href="#i-folder"/></svg><b>${t('Add a folder…')}</b><span class="small muted">${t('sub-folders too')}</span></label></div>
    <div id="fifiles"></div>
    <div class="nestep"><b>3</b>${t('Edit it')}</div>
    <button class="ficont" id="figo" disabled title="${ta('New edit opens with your recording and this script - the style, the sound, the length and the format are picked there.')}">
      <span class="oic"><svg class="i"><use href="#i-edit"/></svg></span>
      <span class="otx"><b>${t('Continue in the Editor')}</b><span class="fiwith" id="fiwith"></span></span><span class="oar">→</span></button>
    <div class="small amber" id="fimsg" style="margin-top:8px"></div>`, el => {
    const sel = $('#fiv', el), name = $('#finame', el);
    sel.value = st.project;
    const P = () => ps.find(x => x.name === sel.value);
    const upd = () => {
      name.hidden = !!sel.value;
      const n = P() ? P().clips : 0;
      $('#figo', el).disabled = !n || st.busy;
      $('#fiwith', el).innerHTML = `${n ? `<span><svg class="i"><use href="#i-videos"/></svg>${esc(pname(P()))} · ${plural(n, 'clip')}</span>` : ''}<span><svg class="i"><use href="#i-scriptok"/></svg>${esc(ptitle(p))}</span>`;
      $('#fimsg', el).textContent = st.busy ? '' : !sel.value ? t('Add your recording first - step 2.') : !n ? t('No recording in {name} yet - step 2.', {name: pname(P())}) : '';
    };
    sel.onchange = upd;
    $('#fitp', el).onclick = () => teleprompter(said);
    $('#ficopy', el).onclick = () => copy(said.join('\n').replace(/\s*\[check\]/gi, ''));
    const add = async (list, folder = false) => {         // Files, or {file, path} from a folder
      const all = [...list].map(x => x instanceof File ? {file: x, path: x.name} : x);
      const files = clipNames(all).clips;
      const bad = all.filter(x => !isJunk(x.file.name, x.path) && !CLIP_EXT.test(x.file.name));
      if (folder) toast(files.length ? tn(files.length, '{n} clip found in the folder', '{n} clips found in the folder')
        : t('No video, photo or sound files in that folder'), files.length ? 'ok' : 'err');
      else if (bad.length) toast(t('{files}: not a video, a photo or a sound file', {files: bad.map(x => x.file.name).join(', ')}), 'err');
      if (!files.length || st.busy) return;
      st.busy = true; upd();
      const box = $('#fifiles', el);
      try {
        if (!sel.value) {                                    // the new video's folder, named after the script
          const r = await api('/api/projects/new', {name: name.value});
          const x = {name: r.name, label: null, clips: 0, songs: []}; ps.push(x);
          sel.insertAdjacentHTML('afterbegin', `<option value="${esc(r.name)}">${t('{name} (new)', {name: esc(r.name)})}</option>`); sel.value = r.name;
        }
        for (const {file: f, name: nm} of files) {
          const row = document.createElement('div'); row.className = 'fifile';
          row.innerHTML = `<span class="grow">${esc(nm)} <span class="small muted">${bytes(f.size)}</span></span><span class="fibar"><i></i></span><span class="small" data-s>${t('copying…')}</span>`;
          box.append(row);
          try {
            const r = await uploadClip(sel.value, f, p.id, v => { $('.fibar i', row).style.width = `${Math.round(v * 100)}%`; }, nm);
            $('.fibar i', row).style.width = '100%'; row.classList.add('ok');
            $('[data-s]', row).textContent = r.kept ? t('already there') : r.file !== nm ? t('copied as {name} ✓', {name: r.file}) : t('copied ✓');
            if (!r.kept && /\.(mp4|mov|mkv|m4v|avi|webm|mts|mxf)$/i.test(nm) || !r.kept && PHOTO_EXT.test(nm)) P().clips++;
          } catch (e) { row.classList.add('err'); $('[data-s]', row).textContent = e.message; }
        }
        $(`#fiv option[value="${CSS.escape(sel.value)}"]`, el).textContent = t('{name} ({clips}) · from this script', {name: pname(P()), clips: plural(P().clips, 'clip')});
      } catch (e) { toast(e.message, 'err'); }
      st.busy = false; upd();
    };
    const drop = $('#fidrop', el), inp = $('#fifile', el), dir = $('#fidir', el);
    inp.onchange = () => { add([...inp.files]); inp.value = ''; };
    dir.onchange = () => { add([...dir.files].map(f => ({file: f, path: f.webkitRelativePath || f.name})), true); dir.value = ''; };
    drop.ondragover = e => { e.preventDefault(); drop.classList.add('on'); };
    drop.ondragleave = () => drop.classList.remove('on');
    drop.ondrop = async e => { e.preventDefault(); drop.classList.remove('on');
      try { const r = await clipsFromDrop(e.dataTransfer); add(r.files, r.folders); } catch (err) { toast(err.message, 'err'); } };
    // 3 = the Editor's New edit with this video's clips and this script picked (Back = Film it again, then where
    // Film it came from)
    $('#figo', el).onclick = () => { const back = MODAL_BACK;
      newEdit({project: sel.value, from: 'prompt', pick: p.id}).then(() => modalBack(() => filmItModal(p).then(() => { if (back) modalBack(back); }))); };
    upd();
  }, 'wide');
}
// one prompt in focus: a header in the kind's colour (what it is, what it needs, Run it), five steps with the next one
// to do, then two columns - the prompt and Claude's check | your rating, what it makes, Style like, details
const PSTEPS = [['check', t('Claude checks it')], ['want', t('You say what you want')], ['opt', t('Claude improves it')],
                ['run', t('Run it')], ['rate', t('Rate the result')]];
// a script / hook has no prompt steps (the user, 0.4.3.5: "the steps are a little ambiguous so just remove them") -
// a script has its road instead (2026-10-22, the user: "id like for the "film it" to also show like a clear next step
// in the whole process"): 1 the script ✓, 2 Film it, 3 Edit it, 4 Post it on a line, the step to do lit and its button
// at the end (`scriptFlow`); under it the videos made from it, each with how far it got and a way there
const VSTAGE = [['clips', 'filmed', t('Filmed')], ['renders', 'edited', t('Edited')], ['posted', 'posted', t('Posted')]];
function talkVideos(p, R) {
  const uses = (R.used || {})[p.id] || [];
  if (!uses.length) return '';
  const head = p.kind === 'hook' ? tn(uses.length, 'Your video from this hook', 'Your videos from this hook')
    : tn(uses.length, 'Your video from this script', 'Your videos from this script');
  return `<div class="pmvids">${p.kind === 'hook' ? `<div class="pmv-h"><h3>${head}</h3></div>` : ''}
    ${uses.map(u => `<a class="pmv" href="#/project/${encodeURIComponent(u.project)}" onclick="closeModal()" title="${esc(head)}"><svg class="i"><use href="#i-edit"/></svg><b class="grow">${esc(u.label || u.project)}</b>
      ${VSTAGE.map(([k, c, l]) => (k === 'posted' ? u.posted : u[k] > 0) ? `<span class="pgstage ${c}">✓ ${l}</span>` : '').join('') || `<span class="small dim">${t('nothing filmed yet')}</span>`}
      <span class="pmv-go">${t('Open the video →')}</span></a>`).join('')}</div>`;
}
const SFLOW = [['written', t('The script'), t('Written')], ['filmed', t('Film it'), t('Filmed')], ['edited', t('Edit it'), t('Edited')], ['posted', t('Post it'), t('Posted')]];
// the road's steps on a line; live = buttons (the script's pop-up), else a picture of where it stands (Film it)
const flowSteps = (uses, live) => { const {st, now} = scriptRoad(uses), post = uses.some(u => u.renders > 0);
  const tip = {written: '', filmed: st.filmed ? t('Film it again') : '', edited: st.edited ? t('Edit it again') : '', posted: post ? t('Open Ready to post') : ''};
  return `<ol class="sflow-l">${SFLOW.map(([k, l, d], i) => { const c = st[k] ? 'done' : k === now ? 'now' : '';
    const inner = `<b>${st[k] ? '✓' : i + 1}</b><span>${l}<small>${st[k] ? d : c ? t('Next|step') : ''}</small></span>`;
    return `<li class="${c}">${live ? `<button type="button" class="sfl" data-flow="${k}"${c || (k === 'posted' && post) ? '' : ' disabled'}${tip[k] ? ` title="${esc(tip[k])}"` : ''}>${inner}</button>` : `<span class="sfl">${inner}</span>`}</li>`; }).join('')}</ol>`; };
function scriptFlow(p, R) {
  const uses = (R.used || {})[p.id] || [], {now} = scriptRoad(uses), post = uses.find(u => u.renders > 0);
  const go = {filmed: `<button class="btn pri big" data-flow="filmed">▶ ${t('Film it')}</button>`,
    edited: `<button class="btn pri big" data-flow="edited"><svg class="i"><use href="#i-edit"/></svg>${t('Edit it')}</button>`,
    posted: post ? `<button class="btn pri big" data-flow="posted"><svg class="i"><use href="#i-upload"/></svg>${t('Post it')}</button>` : ''}[now]
    || `<span class="sflow-done">✓ ${t('All done')}</span>`;
  return `<div class="sflow">${flowSteps(uses, true)}${go}</div>${talkVideos(p, R)}`;
}
function pstate(p, R) {
  const st = p.structure || [], checked = st.some(x => x.status) || (p.review || {}).stars != null;
  const versions = R.items.filter(x => (x.made_from || []).includes(p.id));
  const isOpt = !!(p.made_from || []).length && (p.source || {}).type === 'written';
  const rated = !!(p.result || {}).rating, used = ((R.used || {})[p.id] || []).length > 0;
  const better = versions.length > 0;
  const done = {check: checked || isOpt, want: isOpt || better || Object.keys(p.wishes || {}).length > 0 || Object.keys(p.verdicts || {}).length > 0,
                opt: isOpt || better,
                run: used || rated, rate: rated};
  return {done, now: PSTEPS.map(([k]) => k).find(k => !done[k]) || '', versions, isOpt};
}
async function promptModal(id, ctx) {
  // opened from a text set (the Analyser, 2026-10-18): {set, ids} - the library is read here, Previous / Next walk the set
  if (!ctx.R) { try { ctx.R = await api('/api/prompts'); } catch (e) { toast(e.message, 'err'); return; } }
  if (!ctx.reload) ctx.reload = async () => { ctx.R = await api('/api/prompts'); if (ctx.draw) ctx.draw(); };
  if (!ctx.draw) ctx.draw = () => {};
  const R = ctx.R, all = R.items, p = all.find(x => x.id === id);
  if (!p) { toast(t('{id} is not in your prompts any more', {id}), 'err'); return; }
  if (p.kind === 'title') return titleModal(p, ctx);
  const res = p.result || {}, help = R.help || {}, S = pstate(p, R), cat = pcategory(p);
  const shot = p.kind === 'shot' || p.kind === 'image', ex = p.examples || [];
  const newest = S.versions[S.versions.length - 1];
  const st = p.structure || [], checked = st.some(x => x.status), work = st.filter(x => pIsWork(p, x)).length;
  const plan = p.kind === 'script' ? filmPlan(await api('/api/script/cards?id=' + encodeURIComponent(p.id)).catch(() => null)) : {bar: '', side: ''};
  const ids = Array.isArray(ctx.ids) ? ctx.ids : null, at = ids ? ids.indexOf(p.id) : -1;
  const runBtn = (cls, attr = 'data-run') => `<button class="btn ${cls}" ${attr} title="${shot ? ta('Copies it - paste it into the site') : ta('Create a video with this prompt')}">▶ ${RUN[p.kind] || t('Run it')}</button>`;
  // the rating as the English showed it (good / OK / bad), in the user's words
  const rated = {good: t('good|rating'), ok: t('OK|rating'), bad: t('bad|rating')}[res.rating] || res.rating || '';
  const NEXT = {
    check: `<span>${t('Claude reviews each part (clear, vague or missing) and writes an improved version - this one stays.')}</span>${claudeBtn(optCmd(p), t('Optimize with Claude'), optTask(p), p.id, 'pri')}`,
    want: `<span>${t('Say if Claude is right about each part, and what you want there (beside) - or let Claude decide.')}</span><button class="btn" data-gosec="pm-rvp">${t('Show the parts')}</button>
      <button class="btn pri" data-opt><svg class="i"><use href="#i-claude"/></svg>${t('Optimize with Claude')}</button>`,
    opt: `<span>${t('Your answers are saved. Claude writes a better version - this one stays.')}</span><button class="btn pri" data-opt><svg class="i"><use href="#i-claude"/></svg>${t('Optimize with Claude')}</button>`,
    run: newest && !S.isOpt ? `<span>${t('Claude made a better version: <b>{name}</b>', {name: esc(ptitle(newest))})}</span><button class="btn pri" data-goto="${esc(newest.id)}">${t('Open it')}</button>${runBtn('', 'data-run')}`
      : `<span>${shot ? t('Ready. Copy it into the site, then come back to rate what it made.') : p.kind === 'script' ? t('Ready. Film it with your phone or camera, add the recording, and MotionLab cuts it.') : t('Ready. Create a video with it, then come back to rate it.')}</span>${runBtn('pri')}`,
    rate: `<span>${t("How did it turn out? Your rating makes Claude's next prompts better.")}</span><button class="btn pri" data-gosec="pm-rate">${t('Rate it')}</button>`,
    '': `<span>${t('Done - you rated it <b>{rating}</b>. Another take?', {rating: esc(rated)})}</span><button class="btn" data-remix><svg class="i"><use href="#i-claude"/></svg>${t('Use it, change…')}</button>`,
  };
  // three tabs (2026-10-22, the user: "make the The check and claudes check into a separte section or tab ... we clutter
  // the interface ... when we just want to go straight to the point"): the text alone (a script: its rhythm and what to
  // film beside it, no notes - "i like that its only text"), Checks = the one review pattern (2026-10-18: the measured
  // check, Claude's check and the text with the part under review marked on the left, the review panel on the right),
  // Details = what it makes, Style like, the record. Reopened for the same prompt it keeps its tab; a text set opens
  // on Checks.
  const tab0 = (ctx.pmtab && (ctx.set || ctx.pmtab.id === p.id) && ctx.pmtab.tab) || (ctx.set ? 'checks' : 'text');
  const tabBtn = (k, icon, label, badge = '') => `<button type="button" role="tab" data-pmtab="${k}"${k === tab0 ? ' class="on"' : ''}><svg class="i"><use href="#${icon}"/></svg>${label}${badge}</button>`;
  const ckBadge = () => { const w = st.filter(x => pIsWork(p, x)).length;
    return checked ? `<span class="pmtb ${w ? 'warn' : 'ok'}" title="${w ? esc(tn(w, '{n} part needs work', '{n} parts need work')) : ta('Every part is clear')}">${w || '✓'}</span>` : ''; };
  const pane = k => `data-pmpane="${k}"${k === tab0 ? '' : ' hidden'}`;
  modal(`<div class="pm2 k-${esc(p.kind)}" id="pm-top">
    <div class="pmh"><div class="pmh-main">
        <div class="pmh-tags"><button class="kbadge k-${esc(p.kind)}" data-kind title="${ta('{help} - click to change the kind', {help: t(help[p.kind] || '')})}">${esc(KSHORT[p.kind] || p.kind)} ▾</button>
          ${cat ? `<span class="pgcat">${esc(PURPOSES.includes(cat) ? t(cat) : cat)}</span>` : ''}${S.isOpt ? `<span class="tag done">${t('optimized by Claude')}</span>` : ''}
          ${ids && at >= 0 ? `<span class="pmset"><button class="btn sm ghost" data-pmset="-1"${at <= 0 ? ' disabled' : ''} title="${ta('The one before it in the set')}">◀</button><span class="small muted">${t('{n} of {total}', {n: at + 1, total: ids.length})}</span><button class="btn sm ghost" data-pmset="1"${at >= ids.length - 1 ? ' disabled' : ''} title="${ta('The next one in the set')}">▶</button></span>` : ''}</div>
        <h2 class="pmh-title">${esc(ptitle(p))}</h2>
        <div class="pmh-needs"><span class="small muted">${t('Needs')}</span>${ptoolChip(p)}${pneeds(p).map(x => `<span class="pgneed">${esc(x)}</span>`).join('')}</div></div>
      <div class="pmh-act">${p.kind === 'script' ? '' : runBtn('pri big')}<button class="btn" data-copy title="${isTalk(p) ? ta("Copies this script's text") : ta("Copies this prompt's text")}"><svg class="i"><use href="#i-clipboard"/></svg>${isTalk(p) ? t('Copy Script') : t('Copy Prompt')}</button></div></div>
    ${p.kind === 'script' ? scriptFlow(p, R) : isTalk(p) ? talkVideos(p, R) : `<div class="pmnext"><b class="pmnext-l">${S.now ? t('Next|step') : t('All done')}</b>${NEXT[S.now]}</div>`}
    <nav class="pmtabs" role="tablist">${tabBtn('text', isTalk(p) ? 'i-mic' : 'i-prompts', isTalk(p) ? t('Script|tab') : t('Prompt|tab'))}${tabBtn('checks', 'i-scriptok', t('Checks|tab'), ckBadge())}${tabBtn('more', 'i-news', t('Details'))}</nav>
    <div ${pane('text')}>${plan.bar}<div class="sgrid${plan.side ? '' : ' one'}">
        <section class="pms"><div class="pms-h"><h3>${isTalk(p) ? t('The script') : t('The prompt')}</h3></div>
          <div class="ptext2">${esc(p.text)}</div>${p.notes && !isTalk(p) ? `<div class="pnotes"><b>${t('How to use')}</b> ${esc(p.notes)}</div>` : ''}</section>${plan.side}</div></div>
    <div class="pmgrid" ${pane('checks')}><div class="pmcol">
        ${isTalk(p) ? `<section class="pms spcheck"><div class="pms-h"><h3>${t('The check')}</h3><span class="grow"></span><span class="small muted">${t('measured · no Claude')}</span></div><div id="pm-sc"><div class="small dim">${t('Checking…')}</div></div></section>` : ''}
        <section class="pms" id="pm-check">${pcheckHead(p, R)}<div class="ptext2 pmark" id="pm-ctext">${esc(p.text)}</div></section></div>
      <aside id="pm-rvp"></aside></div>
    <div class="pmcol" ${pane('more')}>
        ${p.notes && isTalk(p) ? `<details class="pms pmnotes"><summary><h3>${t("Claude's notes")}</h3></summary><div class="pnotes">${esc(p.notes)}</div></details>` : ''}
        <section class="pms"><div class="pms-h"><h3>${t('What it makes')}</h3><span class="grow"></span><label class="btn sm ghost" title="${ta("Add a screenshot or clip of what this prompt made - your own result or the creator's example. It is only kept on this PC (never shared); the first one becomes the card's picture.")}">${t('+ Add picture / clip')}<input type="file" data-exadd accept=".jpg,.jpeg,.png,.webp,.gif,.mp4,.webm" hidden></label></div>
          ${ex.length ? `<div class="pexlist">${ex.map(f => `<figure data-ex="${esc(f)}">${/\.(mp4|webm)$/i.test(f)
            ? `<video src="${pexUrl(R, f)}" controls muted loop playsinline preload="metadata"></video>` : `<img src="${pexUrl(R, f)}" alt="" loading="lazy" data-exview>`}
            <button class="btn sm ghost" data-exdel="${esc(f)}" title="${ta('Remove it (Recycle Bin)')}">✕</button></figure>`).join('')}</div>`
            : ''}<div class="small muted"${ex.length ? ' style="margin-top:6px"' : ''}>${t("Pictures or clips of what this prompt made - yours, or the creator's example - so you see at a glance what it gives and can compare versions. The first one shows on the card. Kept on this PC only.")}</div></section>
        ${pstyleBlock(p, R)}
        <section class="pms pdet"><h3>${t('Details')}</h3><div class="kv small">
          <b>${t('From')}</b><span>${psource(p)}</span>
          ${p.model ? `<b>${t('Model')}</b><span>${esc(p.model)}</span>` : ''}
          ${p.pattern ? `<b>${t('Kind of hook')}</b><span>${esc(t(p.pattern))}</span>` : ''}
          ${p.workflow ? `<b>${t('Recipe')}</b><span>${p.step ? t('{recipe} · step {n}', {recipe: esc(p.workflow), n: p.step}) : esc(p.workflow)}</span>` : ''}
          <b>${t('For')}</b><span>${(p.tags || []).map(x => `<span class="fchip sm">${esc(PURPOSES.includes(x) ? t(x) : x)}</span>`).join(' ') || `<span class="dim">${t('not set')}</span>`} <button class="btn sm ghost" data-for>${t('Edit')}</button></span>
          ${S.versions.length ? `<b>${t('Better versions')}</b><span>${S.versions.map(x => `<a href="#" data-goto="${esc(x.id)}">${esc(ptitle(x))}</a>`).join(', ')}</span>` : ''}
          <b>${t('Saved')}</b><span>${p.updated && p.updated !== p.added ? t('{added} · changed {updated}', {added: esc(p.added || ''), updated: esc(p.updated)}) : esc(p.added || '')} · <span class="mono dim">${esc(p.id)}</span></span></div>
          <div class="row" style="margin-top:10px"><button class="btn sm cl" data-remix title="${ta('Claude keeps what worked in this prompt and changes what you say')}"><svg class="i"><use href="#i-claude"/></svg>${t('Use it, change…')}</button>
            <span class="grow"></span><button class="btn sm danger" data-pdel title="${ta('Move it to the Recycle Bin')}"><svg class="i"><use href="#i-trash"/></svg>${t('Delete')}</button></div></section>
      </div></div>`, c => {
    const reopen = async () => { await ctx.reload(); promptModal(p.id, ctx); };
    if (isTalk(p)) api('/api/script/check', {text: p.text, like: p.style_refs || []})
      .then(r => { const b = $('#pm-sc', c); if (b) b.innerHTML = scriptCheckChips(r); }).catch(() => { /* the check is extra */ });
    const back = () => promptModal(p.id, ctx);
    const post = rvQueue(), txt = $('#pm-ctext', c);
    let view = checked && work && work < st.length ? 'work' : 'all', curSlot = null, hover = null;
    // the quoted words of a part marked in the text: the part under the pointer, else the current one; moving to a
    // part brings its words into view
    const showMarks = () => { const x = st.find(y => y.slot === (hover || curSlot)); txt.innerHTML = x && (x.at || []).length ? pquoteHtml(p.text, x.at) : esc(p.text); };
    const toMark = () => { const m = $('mark.tq', txt); if (m && txt.offsetParent) m.scrollIntoView({block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'}); };
    const markWork = () => { const b = $('[data-pmtab=checks] .pmtb', c), h = ckBadge(); if (b && h) b.outerHTML = h; };   // the tab's count follows the answers
    const tab = k => {
      ctx.pmtab = {id: p.id, tab: k};
      $$('[data-pmtab]', c).forEach(b => b.classList.toggle('on', b.dataset.pmtab === k));
      $$('[data-pmpane]', c).forEach(el => { el.hidden = el.dataset.pmpane !== k; });
      $('.pmtabs', c).scrollIntoView({block: 'nearest'});
      if (k === 'checks') toMark();
    };
    $$('[data-pmtab]', c).forEach(b => b.onclick = () => tab(b.dataset.pmtab));
    const sections = [];
    if (st.length) sections.push({id: 'check', ask: t('Is Claude right?'), scale: 'claims', note: 'line',
      items: () => pCheckOrder(p).filter(x => view === 'all' || pIsWork(p, x) || x.slot === curSlot).map(pCheckRow),
      all: () => st.map(x => ({id: x.slot})),
      get: slot => ({v: (p.verdicts || {})[slot] || '', note: (p.wishes || {})[slot] || ''}),
      set: (slot, a) => {                            // the record's wishes + the user's verdicts, the whole of both each time
        const w = {...(p.wishes || {})}, vd = {...(p.verdicts || {})}, note = a.note.trim();
        if (note) w[slot] = note; else delete w[slot];
        if (a.v) vd[slot] = a.v; else delete vd[slot];
        p.wishes = w; p.verdicts = vd; markWork();
        const body = {id: p.id, wishes: w, verdicts: vd};
        return post(() => api('/api/prompts/wishes', body));
      },
      hint: v => v === 'partly' || v === 'wrong' ? t('What is not right - and what you want here') : t('What you want here (optional)')});
    sections.push({id: 'result', domId: 'pm-rate', ask: t('How did it turn out?'), intro: ((R.used || {})[p.id] || []).map(pusedLine).join(''), scale: 'result',
      items: () => [{id: 'result', label: `<b>${t('What it made')}</b>`, optional: true}],
      get: () => ({v: (p.result || {}).rating || '', note: (p.result || {}).note || ''}),
      set: (k, a) => { const body = {id: p.id, rating: a.v || null, note: a.note.trim()};
        p.result = {rating: body.rating, note: body.note};
        return post(async () => { await api('/api/prompts/rate', body); ctx.draw(); }); },
      hint: () => t('A note on what it made (saved as you type)')});
    const PN = reviewPanel($('#pm-rvp', c), {dialog: true, sections,
      filters: checked && work && work < st.length ? `<div class="seg"><button data-cv="work"${view === 'work' ? ' class="on"' : ''}>${t('Needs work')} <span>${work}</span></button><button data-cv="all"${view === 'all' ? ' class="on"' : ''}>${t('All parts')} <span>${st.length}</span></button></div>` : '',
      onMove: (s, slot, first) => { curSlot = s === 'check' ? slot : null; showMarks(); if (!first) toMark(); },
      extra: {item: (s, slot) => { const x = s === 'check' && st.find(y => y.slot === slot); return x ? pcheckTip(p, x) : ''; }},
      send: {hint: isTalk(p) ? (checked ? t('Claude rewrites it from its check, your verdicts and your notes - in your voice. This one stays.') : t('Claude checks each part first, then rewrites it in your voice. This one stays.'))
          : (checked ? t('Claude writes a better version from its check, your verdicts and your notes. This one stays.') : t('Claude checks each part first, then writes a better version. This one stays.')),
        cmd: optCmd(p), task: optTask(p), name: p.id, ready: () => true,
        more: checked ? claudeBtn(chkCmd(p), t('Check it again'), optTask(p), p.id, 'sm ghost') : ''}});
    $$('[data-cv]', PN.el).forEach(b => b.onclick = () => {
      view = b.dataset.cv; $$('[data-cv]', PN.el).forEach(x => x.classList.toggle('on', x === b));
      PN.redraw();
    });
    const hov = slot => { if (slot === hover) return; hover = slot; showMarks(); };
    PN.el.addEventListener('mouseover', e => { const li = e.target.closest('.rvrow'); hov(li && li.dataset.sec === 'check' ? li.dataset.id : null); });
    PN.el.addEventListener('mouseleave', () => hov(null));
    $$('[data-pmset]', c).forEach(b => b.onclick = async () => { await PN.flush(); promptModal(ids[at + +b.dataset.pmset], ctx); });
    $('[data-copy]', c).onclick = () => copy(p.text);
    $$('[data-remix]', c).forEach(b => b.onclick = () => { remixModal(p); modalBack(back); });
    $('[data-for]', c).onclick = () => { forModal(p, reopen); modalBack(back); };
    $('[data-pdel]', c).onclick = () => { delPromptModal(p); modalBack(back); };
    $('[data-kind]', c).onclick = () => { kindModal(p, R); modalBack(back); };
    $$('[data-run]', c).forEach(b => b.onclick = () => {
      if (shot) { copy(p.text); toast(t('Copied - paste it into the site, then rate what it made here'), 'ok'); }
      else if (p.kind === 'script') filmItModal(p).then(() => modalBack(back));
      else newEdit({from: 'prompt', pick: p.id}).then(() => modalBack(back));
    });
    // a script's road: Film it, Edit it (New edit with the filmed video and this script, as Film it's step 3), Post it
    // (the video's Ready to post); the script = its tab
    $$('[data-flow]', c).forEach(b => b.onclick = () => {
      const k = b.dataset.flow, uses = (R.used || {})[p.id] || [], done = uses.find(u => u.renders > 0), filmed = uses.find(u => u.clips > 0);
      if (k === 'written') tab('text');
      else if (k === 'filmed') filmItModal(p).then(() => modalBack(back));
      else if (k === 'edited') newEdit({project: filmed ? filmed.project : '', from: 'prompt', pick: p.id}).then(() => modalBack(back));
      else if (k === 'posted' && done) { closeModal(); location.hash = `#/project/${encodeURIComponent(done.project)}/publish`; }
    });
    $$('[data-goto]', c).forEach(a => a.onclick = e => { e.preventDefault(); promptModal(a.dataset.goto, ctx); });
    $$('[data-gosec]', c).forEach(b => b.onclick = () => {
      tab('checks');                                     // the review panel lives on the Checks tab
      if (b.dataset.gosec === 'pm-rvp') {                // Show the parts: the first one without an answer, its note ready
        PN.el.scrollIntoView({behavior: 'smooth', block: 'nearest'});
        if (!PN.cur() || PN.cur().sec !== 'check') PN.nextOpen();
        setTimeout(() => PN.focusNote(), 350);
        return;
      }
      const sec = document.getElementById(b.dataset.gosec); if (!sec) return;
      sec.scrollIntoView({behavior: 'smooth', block: 'start'});
      if (b.dataset.gosec === 'pm-rate') PN.select('result', 'result');
    });
    $$('[data-opt]', c).forEach(b => b.onclick = async () => { await PN.flush(); openClaude(optCmd(p), optTask(p), p.id); });
    const setStyle = async (refs, msg) => {
      try { await api('/api/prompts/style', {id: p.id, refs}); toast(msg, 'ok'); await reopen(); }
      catch (e) { toast(e.message, 'err'); }
    };
    const exIn = $('[data-exadd]', c);
    exIn.onchange = async () => {
      for (const f of [...exIn.files]) {
        if (f.size > 30e6) { toast(t('{name}: pictures and clips up to 30 MB', {name: f.name}), 'err'); continue; }
        try { await api('/api/prompts/example', {id: p.id, name: f.name, data: b64(await f.arrayBuffer())}); }
        catch (e) { toast(e.message, 'err'); }
      }
      await reopen();
    };
    $$('[data-exdel]', c).forEach(bt => bt.onclick = async () => {
      try { await api('/api/prompts/example', {id: p.id, remove: bt.dataset.exdel}); toast(t('Removed (Recycle Bin)'), 'ok'); await reopen(); }
      catch (e) { toast(e.message, 'err'); }
    });
    $$('[data-exview]', c).forEach(im => im.onclick = () => {
      const pics = ex.filter(f => !/\.(mp4|webm)$/i.test(f));
      lightbox(pics.map(f => ({src: `${R.folder}/examples/${f}`, cap: ptitle(p)})), Math.max(0, pics.indexOf(im.closest('figure').dataset.ex)));
    });
    const linkMsg = (p.structure || []).length ? t('Linked - now click Optimize with Claude so its measured style goes into the prompt')
      : t('Linked - Claude uses its measured style when it checks this prompt');
    $$('[data-suse]', c).forEach(b => b.onclick = () => setStyle([...(p.style_refs || []), b.dataset.suse], linkMsg));
    $$('[data-sdel]', c).forEach(b => b.onclick = () => setStyle((p.style_refs || []).filter(n => n !== b.dataset.sdel), t('Unlinked')));
    const sp = $('[data-spick]', c);
    if (sp) sp.onclick = () => { styleModal(p, R, n => setStyle([...(p.style_refs || []), n], linkMsg)); modalBack(back); };
  }, 'wide');
}
// a title record (0.4.3, kind title, /write-title): the titles (pattern, characters - a phone shows about 50-60), the
// 2-3 thumbnail ideas (the words on it, the sketch, the shot to film), the hook; Copy each; *Use this title* links it
// to a video (POST /api/prompts/title: "project" + "chosen") - that video's Ready to post (its Overview) then offers its titles
const TITLE_PHONE = 60;
const tchars = n => `<span class="ttch${n > TITLE_PHONE ? ' long' : ''}" title="${n > TITLE_PHONE ? ta('A phone may cut it after about 50-60 characters - the key words go first') : ta('shows whole on a phone')}">${n > TITLE_PHONE ? tn(n, '{n} characters · may be cut', '{n} characters · may be cut') : tn(n, '{n} characters', '{n} characters')}</span>`;
function titleModal(p, ctx) {
  const R = ctx.R, ts = p.titles || [], cs = p.concepts || [];
  const req = p.request, cmd = req ? `/write-title request ${req}` : p.project ? `/write-title package ${p.project}` : '/write-title';
  const st = (p.structure || []).filter(x => x.status);
  modal(`<div class="pm2 k-title" id="pm-top">
    <div class="pmh"><div class="pmh-main">
        <div class="pmh-tags"><span class="kbadge k-title">${esc(KSHORT.title)}</span>${p.project ? `<span class="tag done">${t('for {name}', {name: esc(p.project)})}</span>` : ''}</div>
        <h2 class="pmh-title">${esc(ptitle(p))}</h2>
        <div class="pmh-needs"><span class="small muted">${[plural(ts.length, 'title'), plural(cs.length, 'thumbnail idea'), p.hook ? t('the hook') : ''].filter(Boolean).join(' · ')}</span></div></div>
      <div class="pmh-act"><button class="btn pri big" data-use="">▶ ${esc(RUN.title)}</button><button class="btn" data-copy title="${ta('Copies every title, idea and the hook')}"><svg class="i"><use href="#i-clipboard"/></svg>${t('Copy all')}</button></div></div>
    <div class="pmnext"><b class="pmnext-l">${t('Next|step')}</b>${p.project
      ? `<span>${p.chosen ? t('Linked to <b>{name}</b> - final title “{title}”. Its package: the video\'s Overview, under Ready to post.', {name: esc(p.project), title: esc(p.chosen)})
          : t('Linked to <b>{name}</b>. Its package: the video\'s Overview, under Ready to post.', {name: esc(p.project)})}</span><a class="btn pri" href="#/project/${encodeURIComponent(p.project)}/publish" onclick="closeModal()">${t('Open Ready to post')}</a>`
      : `<span>${t("Film the thumbnail shots with the rest. The script's first 3 seconds keep the title's promise.")}</span><button class="btn" data-script>${t('Write the script')}</button>`}</div>
    <div class="pmgrid"><div class="pmcol">
      <section class="pms"><div class="pms-h"><h3>${t('Titles')}</h3><span class="grow"></span><span class="small muted">${t('a phone shows about {n} characters', {n: TITLE_PHONE})}</span></div>
        <div class="ttlist">${ts.map((ti, i) => `<div class="ttrow${p.chosen === ti.text ? ' chosen' : ''}"><span class="ttn">${i + 1}</span>
          <div class="grow"><b class="ttx">${esc(ti.text)}</b><div class="small">${ti.pattern ? `<span class="ttpat">${esc(t(ti.pattern))}</span> ` : ''}${tchars(ti.chars || ti.text.length)}${p.chosen === ti.text ? ` <span class="tag done">${t('final')}</span>` : ''}${ti.note ? ` <span class="muted">· ${esc(ti.note)}</span>` : ''}</div></div>
          <button class="btn sm ghost" data-ct="${i}" title="${ta('Copy this title')}"><svg class="i"><use href="#i-clipboard"/></svg></button><button class="btn sm ghost" data-use="${i}">${t('Use this title')}</button></div>`).join('')
          || `<div class="small muted">${t('No titles yet.')}</div>`}</div></section>
      <section class="pms"><div class="pms-h"><h3>${t('Thumbnail ideas')}</h3></div>
        <div class="tcons">${cs.map((c, i) => `<div class="tcon"><div class="tcon-h"><span class="tid">${esc(c.id)}</span><b class="twords">${esc(c.words || '-')}</b>
            <span class="grow"></span>${c.title ? `<span class="small muted">${t('for title {id}', {id: esc(c.title)})}</span>` : ''}<button class="btn sm ghost" data-cw="${i}" title="${ta('Copy the words')}"><svg class="i"><use href="#i-clipboard"/></svg></button></div>
          <div class="kv small"><b>${t('Picture')}</b><span>${esc(c.sketch || '-')}</span><b>${t('Shot to film')}</b><span>${esc(c.shot || '-')}</span>${c.colours ? `<b>${t('Colours')}</b><span>${esc(c.colours)}</span>` : ''}</div></div>`).join('')
          || `<div class="small muted">${t('No thumbnail ideas yet.')}</div>`}</div></section>
      ${p.hook ? `<section class="pms"><div class="pms-h"><h3>${t('The hook - first 3 seconds')}</h3><span class="grow"></span><button class="btn sm ghost" data-ch title="${ta('Copy the hook')}"><svg class="i"><use href="#i-clipboard"/></svg>${t('Copy')}</button></div>
        <div class="ptext2">${esc(p.hook)}</div></section>` : ''}
      ${p.notes ? `<div class="pnotes"><b>${t("Claude's notes")}</b> ${esc(p.notes)}</div>` : ''}
      ${st.length ? `<section class="pms" id="pm-check"><h3>${t("Claude's check")}</h3><div class="cparts">${st.map(x => { const [ic, lab] = STAT[x.status] || ['•', ''];
        return `<div class="cpart st-${esc(x.status)}" data-slot="${esc(x.slot)}"><div class="cpart-h"><span class="cdot">${ic}</span><b>${esc(slotLabel(x.slot))}</b><span class="cstat">${lab}</span></div>
          <div class="cpart-says">${esc(x.text || '')}</div>${x.tip ? `<div class="cpart-tip"><b>${t('Tip')}</b> ${esc(x.tip)}</div>` : ''}</div>`; }).join('')}</div></section>` : ''}
      <section class="pms pdet"><h3>${t('Details')}</h3><div class="kv small">
        <b>${t('From')}</b><span>${psource(p)}</span>
        ${req ? `<b>${t('Your answers')}</b><span class="mono dim">${esc(req)}</span>` : ''}
        <b>${t('Saved')}</b><span>${p.updated && p.updated !== p.added ? t('{added} · changed {updated}', {added: esc(p.added || ''), updated: esc(p.updated)}) : esc(p.added || '')} · <span class="mono dim">${esc(p.id)}</span></span></div>
        <div class="row" style="margin-top:10px"><span class="grow"></span><button class="btn sm danger" data-pdel title="${ta('Move it to the Recycle Bin')}"><svg class="i"><use href="#i-trash"/></svg>${t('Delete')}</button></div></section></div>
    <aside id="pm-rvp"></aside></div></div>`, c => {
    const back = () => titleModal(p, ctx);
    const post = rvQueue();
    const sections = [];
    if (st.length) sections.push({id: 'check', ask: t('Is Claude right?'), intro: t('Claude\'s check of each part, on the left - the note is what you want there'), scale: 'claims', note: 'line',
      items: () => st.map(pCheckRow), get: slot => ({v: (p.verdicts || {})[slot] || '', note: (p.wishes || {})[slot] || ''}),
      set: (slot, a) => {
        const w = {...(p.wishes || {})}, vd = {...(p.verdicts || {})}, note = a.note.trim();
        if (note) w[slot] = note; else delete w[slot];
        if (a.v) vd[slot] = a.v; else delete vd[slot];
        p.wishes = w; p.verdicts = vd;
        const body = {id: p.id, wishes: w, verdicts: vd};
        return post(() => api('/api/prompts/wishes', body));
      },
      hint: v => v === 'partly' || v === 'wrong' ? t('What is not right - and what you want here') : t('What you want here (optional)')});
    sections.push({id: 'result', domId: 'pm-rate', ask: t('How did it do?'), scale: 'result',
      items: () => [{id: 'result', label: `<b>${t('The title and the thumbnail')}</b>`, optional: true}],
      get: () => ({v: (p.result || {}).rating || '', note: (p.result || {}).note || ''}),
      set: (k, a) => { const body = {id: p.id, rating: a.v || null, note: a.note.trim()};
        p.result = {rating: body.rating, note: body.note};
        return post(async () => { await api('/api/prompts/rate', body); if (ctx.draw) ctx.draw(); }); },
      hint: () => t('Which title or thumbnail won, the click-through rate… (saved as you type)')});
    reviewPanel($('#pm-rvp', c), {dialog: true, sections,
      onMove: (s, slot, first) => {
        const cur = s === 'check' ? slot : null, cards = $$('.cpart[data-slot]', c);
        cards.forEach(el => el.classList.toggle('cur', el.dataset.slot === cur));
        const card = !first && cur && cards.find(el => el.dataset.slot === cur);
        if (card) card.scrollIntoView({block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
      },
      send: {hint: t('Claude writes new titles and thumbnail ideas from your verdicts and notes. These stay.'), cmd, task: 'title', name: p.id, ready: () => true}});
    $('[data-copy]', c).onclick = () => copy(p.text);
    $$('[data-ct]', c).forEach(b => b.onclick = () => copy(ts[+b.dataset.ct].text));
    $$('[data-cw]', c).forEach(b => b.onclick = () => copy(cs[+b.dataset.cw].words || ''));
    const ch = $('[data-ch]', c); if (ch) ch.onclick = () => copy(p.hook);
    $$('[data-use]', c).forEach(b => b.onclick = () => { useTitleModal(p, ctx, b.dataset.use === '' ? (p.chosen || (ts[0] || {}).text || '') : ts[+b.dataset.use].text); modalBack(back); });
    const sc = $('[data-script]', c); if (sc) sc.onclick = () => { closeModal(); scriptNewModal(ctx, {topic: (p.chosen || (ts[0] || {}).text || p.title || '') + (p.hook ? `\n\nThe hook that keeps the title's promise: ${p.hook}` : '')}); };
    $('[data-pdel]', c).onclick = () => { delPromptModal(p); modalBack(back); };
  }, 'wide');
}
// *Use this title*: which video it is for (its Ready to post then shows these titles) and the final title
async function useTitleModal(p, ctx, text) {
  let ps;
  try { ps = await api('/api/projects'); } catch (e) { toast(e.message, 'err'); return; }
  const ts = (p.titles || []).map(x => x.text);
  modal(`<h2>${t('Use a title for a video')}</h2>
    <div class="small muted" style="margin-top:-4px">${t("The video's Ready to post (on its Overview) then offers these titles and their thumbnail ideas.")}</div>
    <div class="nestep"><b>1</b>${t('The title')}</div>
    <select id="utt" style="width:100%">${ts.map(x => `<option ${x === text ? 'selected' : ''}>${esc(x)}</option>`).join('')}${text && !ts.includes(text) ? `<option selected>${esc(text)}</option>` : ''}</select>
    <div class="nestep"><b>2</b>${t('Which video?')}</div>
    ${ps.length ? `<div class="utlist">${ps.map(x => `<label class="chk"><input type="radio" name="utp" value="${esc(x.name)}" ${x.name === p.project ? 'checked' : ''}> <b>${esc(pname(x))}</b> <span class="small muted">${x.renders.length ? plural(x.renders.length, 'render') : t('not edited yet')}</span></label>`).join('')}</div>`
      : `<div class="small muted">${t('No video yet - film it, then add the clips in the <a href="#/edit" onclick="closeModal()">Editor</a>.')}</div>`}
    <div class="row" style="margin-top:16px"><button class="btn pri" id="utgo" ${ps.length ? '' : 'disabled'}>${t('Use this title')}</button>
      ${p.project ? `<button class="btn ghost" id="utun">${t('Unlink from the video')}</button>` : ''}</div>`, el => {
    const go = async (project, chosen) => {
      try {
        await api('/api/prompts/title', {id: p.id, project, chosen});
        toast(project ? t('Linked to {name} - see its Ready to post', {name: project}) : t('Unlinked'), 'ok');
        if (ctx.reload) await ctx.reload();
        const np = (ctx.R.items || []).find(x => x.id === p.id); if (np) titleModal(np, ctx); else closeModal();
      } catch (e) { toast(e.message, 'err'); }
    };
    $('#utgo', el).onclick = () => { const r = $('input[name=utp]:checked', el); if (!r) { toast(t('Pick the video'), 'err'); return; } go(r.value, $('#utt', el).value); };
    const un = $('#utun', el); if (un) un.onclick = () => go('', '');
  });
}
const STYLE_KINDS = ['brief', 'script', 'hook'];           // prompts that make a video (prompts.STYLE_KINDS)
// pick an analysed reference whose measured style a prompt follows (the ones its words seem to mean first)
function styleModal(p, R, done) {
  const SR = R.styles || {}, sug = ((R.suggest || {})[p.id] || []).map(x => x.name), have = p.style_refs || [];
  const names = [...sug, ...Object.keys(SR).filter(n => !sug.includes(n))].filter(n => !have.includes(n) && SR[n]);
  const why = Object.fromEntries(((R.suggest || {})[p.id] || []).map(x => [x.name, x.why]));
  modal(`<h2>${t('Style like…')}</h2>
    <p class="hint">${t('A video you analysed: Claude copies what the lab measured in it - cuts per minute, shot lengths, the first 3 seconds, its effects, the beat - and looks at its frames for the colour. Not there? <a href="#/analyze">Analyser</a>: download it and analyse it first.')}</p>
    ${names.length > 6 ? `<input type="search" id="stq" placeholder="${ta('Search: title, creator…')}" style="max-width:340px">` : ''}
    <div class="cvlist" id="stl"></div>`, el => {
    const shownCat = n => { const c = SR[n].category_label || '', s = t(c); return s !== c ? [s] : []; };   // + its Spanish
    const draw = q => {
      $('#stl', el).innerHTML = names.filter(n => !q || [n, SR[n].label, SR[n].title, SR[n].by, SR[n].uploader, SR[n].category_label, ...shownCat(n)].join(' ').toLowerCase().includes(q))
        .map(n => { const s = SR[n];
          return `<button class="cvitem" data-n="${esc(n)}">${s.thumb ? `<img src="${fileUrl(s.thumb)}" loading="lazy" alt="">` : ''}<span><b>${esc(s.label || s.title)}</b>${s.by || s.uploader ? ` <span class="small muted">${t('by {name}', {name: esc(s.by || s.uploader)})}</span>` : ''}
            ${why[n] ? ` <span class="tag done">${esc(why[n])}</span>` : ''}<br><span class="small muted">${esc(t(s.category_label || ''))} · ${esc(s.line)}</span></span></button>`; }).join('')
        || `<div class="empty">${Object.keys(SR).length ? t('Nothing more to pick.') : t('No analysed video yet - <a href="#/analyze">Analyser</a>: download one and analyse it.')}</div>`;
      $$('[data-n]', el).forEach(b => b.onclick = () => { closeModal(); done(b.dataset.n); });
    };
    const q = $('#stq', el);
    if (q) { q.oninput = debounce(() => draw(q.value.trim().toLowerCase()), 150); q.focus(); }
    draw('');
  });
}
// "Use it, change...": Claude keeps what worked in a prompt (structure, wording) and changes what the user says
function remixModal(p) {
  modal(`<h2>${t('Use {id}, change…', {id: esc(p.id)})}</h2>
    <p class="hint">${t('Claude keeps what worked in {id} - its structure and wording - and changes what you write here. Leave it empty for a new one just like it.', {id: esc(p.id)})}</p>
    <pre class="ptext" style="max-height:150px">${esc(p.text)}</pre>
    <textarea id="rmx" rows="4" style="width:100%" placeholder="${ta('e.g. the same camera move, but a cooking vlog at night - 9:16, 8 seconds')}"></textarea>
    <div class="row" style="margin-top:10px"><button class="btn pri" id="rmgo"><svg class="i"><use href="#i-claude"/></svg>${t('Open in Claude Code')}</button></div>`, el => {
    $('#rmx', el).focus();
    $('#rmgo', el).onclick = async () => {            // what to change = the user's words: a request file, as above
      const c = $('#rmx', el).value.trim();
      let cmd = `/write-prompt ${p.kind} like ${p.id}`;
      if (c) {
        $('#rmgo', el).disabled = true;
        try { cmd = (await api('/api/prompts/request', {kind: p.kind, from: p.id, change: c})).command; }
        catch (e) { toast(e.message, 'err'); $('#rmgo', el).disabled = false; return; }
      }
      openClaude(cmd, 'prompt', p.id); closeModal();
    };
  });
}
function forModal(p, done) {
  const own = (p.tags || []).filter(x => !PURPOSES.includes(x));
  modal(`<h2>${t('What is {id} for?', {id: esc(p.id)})}</h2>
    <p class="hint">${t('Pick or type: the prompt library filters by it, and Claude copies examples made for the same thing first.')}</p>
    <div class="row">${PURPOSES.map(x => `<button class="fchip${(p.tags || []).includes(x) ? ' on' : ''}" data-t="${esc(x)}">${esc(t(x))}</button>`).join('')}</div>
    <input type="text" id="fown" style="margin-top:10px" placeholder="${ta('your own, comma-separated - e.g. make money online, fitness')}" value="${esc(own.join(', '))}">
    <div class="row" style="margin-top:10px"><button class="btn pri" id="fsave">${t('Save')}</button></div>`, el => {
    $$('[data-t]', el).forEach(b => b.onclick = () => b.classList.toggle('on'));
    $('#fsave', el).onclick = async () => {
      const tags = [...$$('[data-t].on', el).map(b => b.dataset.t), ...$('#fown', el).value.split(',').map(s => s.trim().toLowerCase()).filter(Boolean)];
      try { const r = await api('/api/prompts/tags', {id: p.id, tags}); p.tags = r.tags; closeModal(); toast(t('Saved'), 'ok'); done(); }
      catch (e) { toast(e.message, 'err'); }
    };
  });
}
// a prompt saved under the wrong kind (e.g. a brief for Claude saved as a talking script): it moves, with a new id
function kindModal(p, R) {
  modal(`<h2>${t('What kind of prompt is {id}?', {id: esc(p.id)})}</h2>
    <div class="kpick">${R.kinds.map(k => `<label class="kopt${k.id === p.kind ? ' on' : ''}"><input type="radio" name="kk" value="${k.id}"${k.id === p.kind ? ' checked' : ''}>
      <span class="kbadge k-${k.id}">${esc(KSHORT[k.id] || t(k.label || ''))}</span><span class="small muted">${esc(t((R.help || {})[k.id] || ''))}</span></label>`).join('')}</div>
    <p class="hint">${t("It gets a new id of that kind; Claude's next check uses the parts of that kind.")}</p>
    <div class="row" style="margin-top:10px"><button class="btn pri" id="kgo">${t('Save')}</button></div>`, el => {
    $$('input[name=kk]', el).forEach(r => r.onchange = () => $$('.kopt', el).forEach(x => x.classList.toggle('on', $('input', x).checked)));
    $('#kgo', el).onclick = async () => {
      const k = ($('input[name=kk]:checked', el) || {}).value;
      if (!k || k === p.kind) { closeModal(); return; }
      try { const r = await api('/api/prompts/kind', {id: p.id, kind: k}); closeModal(); toast(t('{id} is now {new_id}', {id: p.id, new_id: r.id}), 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    };
  });
}
// a prompt's shown name (Prepare's cards, 0.4.3.5): POST /api/prompts/rename - empty = the automatic name again
function renamePromptModal(p, ctx) {
  modal(`<h2>${t('Rename')}</h2><div class="small muted" style="margin-top:-4px">${t('The name MotionLab shows for this {kind}. Its text stays as it is.', {kind: esc((KSHORT[p.kind] || 'prompt').toLowerCase())})}</div>
    <input type="text" id="prname" value="${esc(ptitle(p))}" maxlength="120" style="width:100%;margin-top:14px">
    <div class="row" style="margin-top:14px"><button class="btn pri" id="prok">${t('Save')}</button><button class="btn" data-close>${t('Cancel')}</button></div>`, el => {
    const inp = $('#prname', el); inp.focus(); inp.select();
    $('[data-close]', el).onclick = dismissModal;
    $('#prok', el).onclick = async () => {
      const v = inp.value.trim(); if (!v) { inp.focus(); return; }
      try { await api('/api/prompts/rename', {id: p.id, title: v}); closeModal(); toast(t('Renamed'), 'ok'); if (ctx && ctx.reload) await ctx.reload(); else route(); }
      catch (e) { toast(e.message, 'err'); }
    };
    inp.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); $('#prok', el).click(); } };
  });
}
function delPromptModal(p) {
  modal(`<h2>${t('Delete {name}?', {name: esc(p.id)})}</h2>
    <p>${esc(p.title || p.text.slice(0, 160) + (p.text.length > 160 ? '…' : ''))}</p>
    <p class="hint">${t('It goes to the Windows Recycle Bin - restore it from there if you change your mind.')}</p>
    <div class="row" style="margin-top:10px"><button class="btn danger" id="pdel">${t('Delete')}</button><button class="btn" data-close>${t('Cancel')}</button></div>`, el => {
    $('[data-close]', el).onclick = dismissModal;
    $('#pdel', el).onclick = async () => {
      try { await api('/api/prompts/delete', {id: p.id}); closeModal(); toast(t('{name} moved to the Recycle Bin', {name: p.id}), 'ok'); route(); }
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
  const start = () => modal(`<h2>${t('Add prompts')}</h2>
    <div class="cvchoice">
      <button class="cvopt" data-m="have"><svg class="ic"><use href="#i-prompts"/></svg><b>${t('1. I have a prompt')}</b>
        <span>${t('Paste it or attach a file. Claude then checks it - what is clear, vague or missing - and you say what you want.')}</span></button>
      <button class="cvopt" data-m="new"><svg class="ic"><use href="#i-claude"/></svg><b>${t('2. Generate a new prompt from zero')}</b>
        <span>${t('Tell Claude what you want to make - it writes the prompt from the best examples in your library.')}</span></button></div>`, el => {
    $$('.cvopt', el).forEach(b => b.onclick = () => {           // the next step on its own screen; Back returns here
      const have = b.dataset.m === 'have';
      modal(`<h2>${have ? t('1. I have a prompt') : t('2. Generate a new prompt from zero')}</h2><div id="amode"></div>`,
        m => (have ? havePromptForm : newPromptForm)($('#amode', m), R));
      modalBack(start);
    });
  });
  start();
}
function newPromptForm(box, R, pick = '', style = '') {
  const kinds = (R.kinds || []).length ? R.kinds.map(k => k.id) : Object.keys(KSHORT);
  const first = kinds.includes(pick) ? pick : kinds[0];
  box.innerHTML = `<h3>${t('What kind of prompt?')}</h3>
    <div class="kpick">${kinds.map(k => `<label class="kopt${k === first ? ' on' : ''}"><input type="radio" name="nk" value="${k}"${k === first ? ' checked' : ''}>
      <span class="kbadge k-${k}">${esc(KSHORT[k] || k)}</span><span class="small muted">${esc(t((R.help || {})[k] || ''))}</span></label>`).join('')}</div>
    <h3>${t('What do you want to make?')}</h3>
    <textarea id="nwant" rows="5" style="width:100%" placeholder="${ta('e.g. a 10-15 min vlog of my first day in London from my Osmo Pocket 3 + Nano clips: chronological, a warm cinematic grade, whooshes on the transitions, a hook from my best line')}"></textarea>
    <div class="row" style="margin-top:8px;gap:6px"><span class="small muted">${t('For:')}</span>${PURPOSES.map(x => `<button class="fchip sm" data-t="${esc(x)}">${esc(t(x))}</button>`).join('')}</div>
    <div class="row" style="margin-top:8px"><input type="text" id="nmodel" placeholder="${ta('for which model or tool? (optional - Claude Code, Seedance 2.0, Kling 3.0, Nano Banana…)')}" style="max-width:520px"></div>
    ${Object.keys(R.styles || {}).length ? `<div class="row" id="nstyle" style="margin-top:8px"><label class="small">${t('In the style of')} <select id="nsty"><option value="">${t('- none -')}</option>${Object.entries(R.styles).map(([n, s]) =>
      `<option value="${esc(n)}">${esc(s.label || s.title)}${s.by || s.uploader ? ' - ' + esc(s.by || s.uploader) : ''}</option>`).join('')}</select></label>
      <span class="small muted">${t('a video you analysed: Claude copies its measured pacing and effects')}</span></div>` : ''}
    <div class="row" style="margin-top:12px"><button class="btn pri" id="ngo"><svg class="i"><use href="#i-claude"/></svg>${t('Generate it in Claude Code')}</button>
      <span class="small muted">${t('Claude asks what is missing, writes it, checks it and saves it here.')}</span></div>`;
  const nst = () => { const k = $('input[name=nk]:checked', box).value; if ($('#nstyle', box)) $('#nstyle', box).hidden = !STYLE_KINDS.includes(k) && !style; };
  if (style && $('#nsty', box)) $('#nsty', box).value = style;          // "like this" from an analysed video
  $$('input[name=nk]', box).forEach(r => r.onchange = () => { $$('.kopt', box).forEach(x => x.classList.toggle('on', $('input', x).checked)); nst(); });
  nst();
  $$('[data-t]', box).forEach(b => b.onclick = () => b.classList.toggle('on'));
  $('#nwant', box).focus();
  // the wish goes to Claude whole, in a request file (2026-10-19 - on the cmd line it was cut at 600 characters and
  // lost % & | < >): POST /api/prompts/request -> /write-prompt request <req-NNN>
  $('#ngo', box).onclick = async () => {
    const k = $('input[name=nk]:checked', box).value, w = $('#nwant', box).value.trim();
    const tags = $$('[data-t].on', box).map(b => b.dataset.t), m = $('#nmodel', box).value.trim();
    const sty = $('#nsty', box) && (STYLE_KINDS.includes(k) || style) ? $('#nsty', box).value : '';
    if (!w) { toast(t('Say what you want to make first'), 'err'); $('#nwant', box).focus(); return; }
    const go = $('#ngo', box); let r;
    go.disabled = true;                              // one request per click
    try { r = await api('/api/prompts/request', {kind: k, want: w, for: tags, model: m, style_refs: sty ? [sty] : []}); }
    catch (e) { toast(e.message, 'err'); go.disabled = false; return; }
    openClaude(r.command, 'prompt', 'new');
    closeModal();
  };
}
function havePromptForm(box, R) {
  const files = [];                                          // attached here: {file, rel, text}
  const kinds = (R.kinds || []).length ? R.kinds.map(k => k.id) : Object.keys(KSHORT);
  box.innerHTML = `<div class="small muted">${t('Paste a prompt, or attach a file (.txt, .md, .docx, .pdf). Several prompts? Put a line with only <code>---</code> between them, or let Claude sort the file. Your prompts stay on this PC.')}</div>
    <textarea id="ptxt" rows="12" style="width:100%;margin-top:10px" spellcheck="false" placeholder="${ta('Paste your prompt here…')}"></textarea>
    <div class="row" style="margin-top:6px"><label class="btn sm">${t('Attach a file')}
      <input type="file" id="pfile" accept=".txt,.md,.docx,.pdf" multiple hidden></label><span id="pfiles" class="small muted"></span></div>
    <div class="row" style="margin-top:10px;flex-wrap:wrap;gap:8px">
      <label class="small">${t('Kind')} <select id="pkind"><option value="">${t('guess from the text')}</option>${kinds.map(k => `<option value="${k}">${esc(KSHORT[k] || k)}</option>`).join('')}</select></label>
      <label class="small">${t('Where from')} <select id="psrc"><option value="tested">${t('mine / tested by me')}</option><option value="creator">${t("a creator's (name / link)")}</option><option value="found">${t('found somewhere')}</option></select></label>
      <input type="text" id="pwho" placeholder="${ta('creator name and/or link')}" hidden style="min-width:260px"></div>
    <div class="row" style="margin-top:8px;gap:6px"><span class="small muted">${t('For:')}</span>${PURPOSES.map(x => `<button class="fchip sm" data-t="${esc(x)}">${esc(t(x))}</button>`).join('')}</div>
    <label class="small" style="display:block;margin-top:10px"><input type="checkbox" id="prv" checked> ${t('Then let Claude check it - each part clear, vague or missing, with tips (opens Claude Code)')}</label>
    <div class="row" style="margin-top:10px"><button class="btn pri" id="psave">${t('Save')}</button>
      <button class="btn" id="psort" title="${ta('A guide or a file with several prompts, or a PDF: Claude reads it and saves every prompt in it')}">${t('Let Claude sort it')}</button>
      <span id="pres" class="small"></span></div>`;
  const el = box;
  const txt = $('#ptxt', el), kind = $('#pkind', el), src = $('#psrc', el), who = $('#pwho', el), res = $('#pres', el);
  const say = (html, cls = '') => { res.innerHTML = cls ? `<span class="${cls}">${html}</span>` : html; };
  txt.focus();
  const guess = debounce(async () => {                      // the first option shows the guess
    const typed = txt.value.trim();
    let k = '';
    try { if (typed) k = (await api('/api/prompts/guess', {text: typed})).kind; } catch (e) { /* keep "guess" */ }
    kind.options[0].textContent = k ? t('guess: {kind}', {kind: KSHORT[k] || k}) : t('guess from the text');
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
  const showFiles = () => { $('#pfiles', el).innerHTML = files.map(f => `<span class="tag">${esc(f.file)}</span>${f.text ? '' : ` <span class="amber">${t('Claude reads it')}</span>`}`).join(' '); };
  $('#pfile', el).onchange = async e => {
    for (const f of [...e.target.files]) {
      if (f.size > 30e6) { say(t('{name}: files up to 30 MB', {name: esc(f.name)}), 'bad'); continue; }
      say(t('reading {name}…', {name: esc(f.name)}));
      try {
        const r = await api('/api/prompts/file', {name: f.name, data: b64(await f.arrayBuffer())});
        files.push(r);
        if (r.text) { txt.value = (txt.value.trim() ? txt.value.trim() + '\n---\n' : '') + r.text; guess(); }
        say(r.text ? t('{name}: its text is above - <b>Save</b> keeps it as one prompt; several prompts in it? <b>Let Claude sort it</b>', {name: esc(r.file)})
          : t('{name}: the lab reads no PDFs - <b>Let Claude sort it</b> reads it and saves its prompts', {name: esc(r.file)}));
      } catch (err) { say(esc(err.message), 'bad'); }
    }
    e.target.value = ''; showFiles();
  };
  const done = (ids, kindOf) => {                            // saved: show them, maybe open Claude for the check
    say(tn(ids.length, 'Saved {n} prompt: {ids}', 'Saved {n} prompts: {ids}', {ids: ids.map(esc).join(', ')}), 'ok');
    $('#psave', el).remove(); $('#psort', el).remove();
    if ($('#prv', el).checked) openClaude(`/write-prompt analyse ${ids.join(' ')}`, 'prompt', 'analyse');
    else res.insertAdjacentHTML('beforeend', ' ' + claudeBtn(`/write-prompt analyse ${ids.join(' ')}`, t('Check them with Claude'), 'prompt', 'analyse'));
    const h = '#/prompts';                                   // the page behind the dialog shows them
    if (location.hash === h) route(); else location.hash = h;
  };
  $('#psave', el).onclick = async () => {
    if (!txt.value.trim()) { say(files.length ? t('A PDF has no text here - use <b>Let Claude sort it</b>') : t('Paste a prompt or attach a file first'), 'bad'); return; }
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
      if (!rels.length) { say(t('Paste a guide or attach a file first'), 'bad'); return; }
      const s = source(), from = s.type === 'tested' ? 'tested by me' : s.creator || s.link ? `creator ${s.creator} ${s.link}`.trim() : '';
      openClaude(`/write-prompt import ${rels.join(' ')}${kind.value ? ` - kind ${kind.value}` : ''}${from ? ` - source: ${from}` : ''}${tags().length ? ` - for: ${tags().join(', ')}` : ''}`, 'prompt', 'import');
      say(t('Claude Code opened: it reads the file(s), saves every prompt in them and checks them. The prompt library shows them when it is done.'), 'ok');
      $('#psave', el).remove(); $('#psort', el).remove();
    } catch (e) { say(esc(e.message), 'bad'); }
  };
}

// ============================================================================================ skills
// Settings > Claude skills: the project's Claude Code commands - what each does, how to type it, where the app runs it
async function pageSkills(main) {
  const S = await api('/api/skills');
  main.innerHTML = `<div class="head"><div><h1>${t('Settings')}</h1><div class="sub">${t("Claude skills: the commands you can type in Claude Code for MotionLab. The app's {icon} buttons run them for you.", {icon: '<svg class="i"><use href="#i-claude"/></svg>'})}</div></div></div>${setTabs('#/skills')}
    <div class="skgrid">${S.map(k => `<div class="panel skill${k.dev ? ' dev' : ''}"><div class="row sp"><b class="mono skname">/${esc(k.name)}</b>${k.dev ? `<span class="tag">${t('for developers')}</span>` : ''}</div>
      <div class="skbrief">${esc(t(k.brief || ''))}</div>
      <div class="skuses">${k.uses.map(u => `<div class="skuse"><code>${esc(u)}</code><button class="btn sm ghost" data-copy="${esc(u)}" title="${ta('Copy it, then paste it into Claude Code')}">${t('Copy')}</button></div>`).join('')}</div>
      <div class="row sp skfoot">${k.where ? `<span class="small muted">${t('In the app: {where}', {where: esc(t(k.where))})}</span>` : '<span></span>'}${claudeBtn('/' + k.name, t('Open in Claude Code'), k.task, k.name)}</div></div>`).join('')
      || `<div class="empty">${t('No skills in this copy of MotionLab.')}</div>`}</div>`;
  $$('[data-copy]', main).forEach(b => b.onclick = () => copy(b.dataset.copy));
}

// ============================================================================================ jobs
async function pageJobs(main, id) {
  const list = await api('/api/jobs');
  // a job's status is its id (the tag's CSS class, compared below); the page shows its words (server-app's part, by key)
  main.innerHTML = `<div class="head"><div><h1>${t('Jobs')}</h1><div class="sub">${t('What MotionLab is working on. Jobs keep running when you switch pages.')}</div></div>
    <div class="row"><button class="btn" data-k="selftest">${t('Run the self-test')}</button><button class="btn" data-k="storage">${t('Storage report')}</button></div></div>
    <div class="grid" style="grid-template-columns:minmax(0,1fr) minmax(0,1.6fr)">
      <div class="panel"><table class="t click"><thead><tr><th>#</th><th>${t('Job')}</th><th>${t('Status')}</th><th class="num">${t('Time')}</th></tr></thead><tbody>
      ${list.map(j => `<tr data-id="${j.id}" class="${+id === j.id ? 'sel' : ''}"><td class="mono">${j.id}</td><td>${esc(j.title)}<div class="small dim">${esc(j.started)}</div></td>
        <td><span class="tag ${j.status}">${esc(t(j.status))}</span>${j.status === 'failed' ? `<div>${reportBtn(j.id, 'sm ghost')}</div>` : ''}</td><td class="num">${j.status === 'queued' ? '–' : j.seconds + 's'}</td></tr>`).join('') || `<tr><td colspan="4" class="muted">${t('No jobs yet in this session.')}</td></tr>`}
      </tbody></table></div>
      <div class="panel" id="jd">${id ? '' : `<div class="muted">${t('Select a job to see its output.')}</div>`}</div></div>`;
  $$('[data-k]', main).forEach(b => b.onclick = () => startJob(b.dataset.k, {}));
  $$('tr[data-id]', main).forEach(tr => tr.onclick = () => { location.hash = '#/jobs/' + tr.dataset.id; });
  if (!id) return;
  const j = list.find(x => x.id === +id);
  if (!j) { $('#jd').innerHTML = `<div class="muted">${t('This job is not in this session.')}</div>`; return; }
  $('#jd').innerHTML = `<div class="row sp"><h2>${esc(j.title)}</h2><span class="tag ${j.status}" id="jst">${esc(t(j.status))}</span></div>
    <div class="small muted mono" style="margin-bottom:8px">${esc(j.command)}</div>
    ${j.then_claude ? `<div class="small amber" style="margin-bottom:8px"><svg class="i"><use href="#i-claude"/></svg>${t('Claude Code opens by itself when this measuring is done.')}</div>` : ''}<pre class="log" id="jlog"></pre>
    <div class="row" style="margin-top:8px"><button class="btn danger" id="jc" ${['running', 'queued'].includes(j.status) ? '' : 'hidden'}>${j.status === 'queued' ? t('Remove from the queue') : t('Stop this job')}</button>
      <span id="jrep">${j.status === 'failed' ? reportBtn(j.id) : ''}</span></div>`;
  $('#jc').onclick = async () => { if (!confirm(t('{action}?', {action: $('#jc').textContent}))) return; try { await api(`/api/jobs/${id}/cancel`, {}); } catch (e) { toast(e.message, 'err'); } };
  const shown = s => s === 'queued' ? t('waiting its turn') : t(s || '');
  followJob(+id, $('#jlog'), jj => {
    $('#jst').className = 'tag ' + jj.status; $('#jst').textContent = shown(jj.status); $('#jc').hidden = true;
    if (jj.status === 'failed') $('#jrep').innerHTML = reportBtn(jj.id);
    toast(`${jj.title}: ${t(jj.status)}`, jj.status === 'done' ? 'ok' : 'err');
  }, jj => {
    $('#jst').className = 'tag ' + jj.status; $('#jst').textContent = shown(jj.status);
    $('#jc').textContent = jj.status === 'queued' ? t('Remove from the queue') : t('Stop this job');
    $('#jc').hidden = !['running', 'queued'].includes(jj.status);
  });
}

// ============================================================================================ storage
// Settings' tabs: General (#/settings), Storage (#/storage, 0.3.3) and Claude skills (#/skills, a tab since 0.4)
const setTabs = cur => `<div class="tabs">${[['#/settings', t('General')], ['#/storage', t('Storage')], ['#/skills', t('Claude skills')]].map(([h, l]) =>
  `<a href="${h}" class="${h === cur ? 'on' : ''}">${l}</a>`).join('')}</div>`;
async function pageStorage(main) {
  main.innerHTML = `<div class="head"><div><h1>${t('Settings')}</h1></div></div>${setTabs('#/storage')}<div class="loading">${t('Measuring every folder of the lab… (a few seconds)')}</div>`;
  const S = await api('/api/storage');
  const COL = {source: '#4fb3ff', keep: '#3ecf8e', cache: '#ffc400', checks: '#ff9f43', finals: '#c56bff', env: '#5c5c66'};
  // the categories' names as storage.py says them (--what cache,checks,finals); shown in the app's language
  const CAT = {source: t('source|storage'), keep: t('keep|storage'), cache: t('cache|storage'), checks: t('checks|storage'),
               finals: t('finals|storage'), env: t('env|storage')};
  const used = S.units.reduce((a, u) => a + u.total, 0);
  const target = u => u === 'tools\\selftest' ? 'selftest' : u.split('\\').pop();
  main.innerHTML = `<div class="head"><div><h1>${t('Settings')}</h1><div class="sub">${t('Storage: MotionLab uses {used} · {free} free of {total} on this drive. Only data the lab can rebuild can be freed; your videos and everything learned are never touched.', {used: bytes(used), free: bytes(S.free_bytes), total: bytes(S.total_bytes)})}</div></div></div>${setTabs('#/storage')}
    <div class="row small" style="margin-bottom:10px">${S.cats.map(c => `<span class="chip"><i class="sw" style="background:${COL[c]}"></i>${CAT[c] || c}</span>`).join('')}
      <span class="hint">${t('source = your videos · keep = results and knowledge · cache = rebuildable · checks = comparison videos · finals = full renders')}</span></div>
    <div class="panel"><table class="t"><thead><tr><th>${t('Folder')}</th><th></th>${S.cats.map(c => `<th class="num">${CAT[c] || c}</th>`).join('')}<th class="num">${t('total')}</th><th></th></tr></thead><tbody>
    ${S.units.map(u => { const fr = S.prunable.reduce((a, c) => a + u[c], 0); return `<tr><td class="mono small">${esc(u.name)}</td>
      <td><div class="stbar">${S.cats.map(c => `<i style="width:${100 * u[c] / Math.max(1, u.total)}%;background:${COL[c]}"></i>`).join('')}</div></td>
      ${S.cats.map(c => `<td class="num small">${u[c] ? bytes(u[c]) : '–'}</td>`).join('')}<td class="num">${bytes(u.total)}</td>
      <td>${fr > 5e6 && u.name !== '.venv' ? `<button class="btn sm" data-t="${esc(target(u.name))}" data-n="${esc(u.name)}">${t('Free space…')}</button>` : ''}</td></tr>`; }).join('')}
    </tbody></table></div>
    <h3>${t('What can be freed, and how it comes back')}</h3><div class="panel"><table class="t"><tbody>
    ${S.freeable.map(f => `<tr><td class="num" style="width:90px">${bytes(f.bytes)}</td><td><b>${esc(t(f.what))}</b></td><td class="small muted">${esc(t(f.how))}</td></tr>`).join('')}</tbody></table></div>`;
  $$('[data-t]', main).forEach(b => b.onclick = () => modal(`<h2>${t('Free space: {name}', {name: esc(b.dataset.n)})}</h2>
    <p class="hint">${t('Pick what may go. First a dry run lists every file; nothing is deleted until you confirm.')}</p>
    <div class="col"><label class="chk"><input type="checkbox" value="cache" checked> ${t('cache (rebuildable data, e.g. footage caches)')}</label>
      <label class="chk"><input type="checkbox" value="checks"> ${t('checks (comparison videos, section renders)')}</label>
      <label class="chk"><input type="checkbox" value="finals"> ${t('finals (full renders)')}</label></div>
    <div class="row" style="margin-top:12px"><button class="btn" id="dry">${t('Dry run')}</button><button class="btn danger" id="real" disabled>${t('Delete these files')}</button></div>
    <pre class="log" id="plog" style="margin-top:10px" hidden></pre>`, el => {
    const what = () => $$('input[type=checkbox]:checked', el).map(x => x.value);
    $('#dry', el).onclick = async () => {
      const j = await startJob('prune', {target: b.dataset.t, what: what(), yes: false}, false); if (!j) return;
      const pre = $('#plog', el); pre.hidden = false; pre.textContent = '';
      followJob(j.id, pre, jj => { $('#real', el).disabled = jj.status !== 'done'; });
    };
    $('#real', el).onclick = async () => {
      if (!confirm(t('Delete the files listed in the dry run? They can be rebuilt, but that takes time.'))) return;
      const j = await startJob('prune', {target: b.dataset.t, what: what(), yes: true}, false); if (!j) return;
      const pre = $('#plog', el); pre.textContent = ''; $('#real', el).disabled = true;
      followJob(j.id, pre, jj => toast(t('Free space: {status}', {status: t(jj.status)}), jj.status === 'done' ? 'ok' : 'err'));
    };
  }));
}

// ============================================================================================ downloads (yt-dlp)
const FILE_RX = /^[A-Za-z]:\\.+\.(mp4|mkv|webm|mov|m4v|mp3|m4a)$/i;
// Settings > Programs: the pinned HyperFrames / GSAP vs the newest on npm (asked once a day, motionlab.upstream) and
// the upgrade test (overlay.py upgrade-test renders the examples with both versions and compares every frame)
function upstreamBox(S) {
  const U = S.upstream || {}, P = U.packages || {}, hf = P.hyperframes || {}, gs = P.gsap || {};
  if (!hf.pinned || !(S.tools.find(x => x.name === 'hyperframes') || {}).found) return '';
  const pkg = (name, p) => `${name} <b>${esc(p.pinned)}</b>${p.installed && p.installed !== p.pinned ? ` <span class="amber">${t('(installed {version} - Install again)', {version: esc(p.installed)})}</span>` : ''}${p.latest ? (p.newer
    ? ` · <span class="amber">${t('{version} on npm', {version: esc(p.latest)})}</span> <a href="${esc(p.notes)}" target="_blank" rel="noopener">${t('what changed')}</a>` : ' · ' + t('the newest')) : ''}`;
  const tst = hf.latest && (U.tests || {})[hf.latest];
  const worst = tst && tst.examples ? Math.max(...tst.examples.map(x => x.max_diff ?? 255)) : null;
  // the first message for Claude stays English (Claude commands are never translated)
  const adopt = tst && tst.pass ? `Pin HyperFrames ${tst.hyperframes}${tst.gsap !== gs.pinned ? ` and GSAP ${tst.gsap}` : ''} for MotionLab: run tools\\overlay.py pin ${tst.hyperframes}${tst.gsap !== gs.pinned ? ` --gsap ${tst.gsap}` : ''}, then selftest.py --extended and tools\\dev\\smoke.py, and add a CHANGELOG line` : '';
  const day = tst ? esc(String(tst.when || '').slice(0, 10)) : '';
  const test = !hf.newer && !gs.newer ? '' : tst ? (tst.pass
      ? `<span class="tag done">${t('tested {day}: same frames', {day})}</span> <span class="small muted">${tn(tst.examples.length, '(max {worst}/255 on {n} examples, render {times}). A MotionLab update brings it once the repo owner adopts it.', '(max {worst}/255 on {n} examples, render {times}). A MotionLab update brings it once the repo owner adopts it.', {worst, times: tst.examples.map(x => `${numStr(x.seconds_pinned)} → ${numStr(x.seconds_candidate)} s`).join(', ')})}</span> ${claudeBtn(adopt, t('Adopt it (repo owner)'), 'free', 'hyperframes')}`
      : `<span class="tag failed">${t('tested {day}: frames differ', {day})}</span> <span class="small muted">${t('{list} - MotionLab keeps {version}.', {list: tst.examples.map(x => `${esc(x.example)} ${x.error ? t('error') : x.max_diff + '/255'}`).join(' · '), version: esc(hf.pinned)})}</span>`)
      + ` <button class="btn sm" data-hftest>${t('Test again')}</button>`
    : `<button class="btn sm" data-hftest title="${ta('Installs it in a scratch folder (.app\\dev), renders the overlay examples with both versions and compares every frame - a few minutes, ~300 MB')}">${t('Test it')}</button>`;
  return `<div class="upstream small"><div><b>${t('HTML overlay packages:')}</b> ${pkg('HyperFrames', hf)} &nbsp;|&nbsp; ${pkg('GSAP', gs)}</div>
    <div class="row" style="margin-top:6px">${test}<span class="grow"></span><span class="dim">${U.checked ? t('npm checked {when}', {when: esc(U.checked.replace('T', ' ').slice(0, 16))}) : t('not checked yet')}${U.error ? ` · <span class="bad">${esc(U.error)}</span>` : ''}
      · <a href="#" id="upnpm">${t('check now')}</a></span></div>
    <div class="dim">${t('MotionLab only uses versions that passed this test; newer HyperFrames come several times a day.')}</div></div>`;
}
async function downloadModal() {
  const S = await api('/api/settings');
  const yt = S.tools.find(x => x.name === 'yt-dlp') || {};
  modal(`<h2>${t('Download from a link')}</h2>
    <p class="hint">${yt.found ? '' : `<b class="bad">${t('The downloader (yt-dlp) was not found.')}</b> ${esc(t(yt.how || ''))} · <a href="#/settings">${t('Settings')}</a><br>`}
      ${t('One video per link. Only download what you are allowed to use.')}</p>
    <input type="text" id="durl" placeholder="${ta('Paste a link - YouTube, TikTok, Instagram, Vimeo…')}">
    <div class="row" style="margin-top:10px"><select id="dpre">${S.presets.map(o => `<option value="${o.id}" ${o.id === S.settings.download_preset ? 'selected' : ''}>${esc(t(o.label))}</option>`).join('')}</select>
      <button class="btn pri" id="dgo" ${yt.found ? '' : 'disabled'}><svg class="i"><use href="#i-download"/></svg>${t('Download')}</button>
      <span id="dst" class="small muted"></span></div>
    <pre class="log" id="dlog" hidden style="max-height:240px;margin-top:10px"></pre>
    <div id="ddone" hidden style="margin-top:10px"></div>`, el => {
    const inp = $('#durl', el); inp.focus();
    inp.onkeydown = e => { if (e.key === 'Enter') $('#dgo', el).click(); };
    $('#dgo', el).onclick = async () => {
      const url = inp.value.trim();
      if (!/^https?:\/\//i.test(url)) { toast(t('Paste a full link starting with https://'), 'err'); return; }
      const j = await startJob('download', {url, preset: $('#dpre', el).value}, false);
      if (!j) return;
      $('#dgo', el).disabled = true; $('#dst', el).textContent = t('downloading…'); $('#ddone', el).hidden = true;
      const pre = $('#dlog', el); pre.hidden = false; pre.textContent = '';
      followJob(j.id, pre, done => {
        $('#dgo', el).disabled = false;
        $('#dst', el).innerHTML = done.status === 'done' ? t('done ✓') : esc(t(done.status)) + (done.status === 'failed' ? ' ' + reportBtn(done.id, 'sm ghost') : '');
        const file = pre.textContent.split('\n').map(l => l.trim()).reverse().find(l => FILE_RX.test(l));
        if (done.status !== 'done' || !file) return;
        const isVideo = !/\.(mp3|m4a)$/i.test(file);
        const rel = file.toLowerCase().startsWith(S.lab.toLowerCase() + '\\') ? file.slice(S.lab.length + 1).replace(/\\/g, '/') : '';
        const box = $('#ddone', el); box.hidden = false;
        box.innerHTML = `<div class="small">${t('Saved: {file}', {file: `<span class="mono">${esc(file)}</span>`})}</div>
          <div class="row" style="margin-top:8px">${isVideo ? `<button class="btn pri" id="dan">${t('Analyse it')}</button>` : ''}
          ${rel ? `<button class="btn" id="dop">${t('Show in folder')}</button>` : ''}</div>`;
        if (isVideo) $('#dan', el).onclick = () => { closeModal(); addVideosModal({files: [file], pick: true}); };
        if (rel) $('#dop', el).onclick = () => openPath(rel, true);
      });
    };
  });
}

// ============================================================================================ settings
// Settings > General > Language (2026-10-18, the user: "we need a spanish version of the entire app"; Spain, tú): each
// language in its own words; a click saves it and reloads the page in it. Claude's replies follow it; what Claude
// writes into the lab stays English (the user's choice, the same evening)
const langRow = S => `<div class="panel" style="margin-bottom:14px"><div class="row" style="gap:14px"><h2 style="margin:0">${t('Language')}</h2>
    <div class="seg" id="langseg">${(S.languages || [{id: 'en', label: 'English'}]).map(l => `<button data-v="${esc(l.id)}"${l.id === (S.settings.language || 'en') ? ' class="on"' : ''}>${esc(l.label)}</button>`).join('')}</div>
    <span class="small muted">${t('The app’s words and Claude’s replies. What Claude saves in MotionLab - reviews, lessons, its memory - stays in English, so what you share reads the same for your friends.')}</span></div></div>`;
async function pageSettings(main) {
  const S = await api('/api/settings');
  const st = S.settings;
  main.innerHTML = `<div class="head"><div><h1>${t('Settings')}</h1><div class="sub">${t('Programs, downloads, Claude Code and updates. Your settings stay on this PC.')}</div></div></div>${setTabs('#/settings')}
  ${langRow(S)}
  <div class="panel"><div class="row sp"><h2>${t('Programs')}</h2><button class="btn sm" id="recheck">${t('Check again')}</button></div>
    <table class="t tools"><thead><tr><th>${t('Program')}</th><th></th><th>${t('Found at')}</th><th>${t('Version')}</th><th>${t('What for · how to get it')}</th></tr></thead><tbody>
    ${S.tools.map(tl => `<tr><td><b>${esc(t(tl.label))}</b><div class="need">${esc(t(tl.need))}</div></td>
      <td class="st">${tl.found ? `<span class="tag done">${t('found')}</span>` : `<span class="tag ${tl.need === 'required' ? 'failed' : ''}">${t('missing')}</span>`}</td>
      <td class="mono small">${esc(tl.path || '–')}</td><td class="small">${esc(tl.version || '')}${tl.name === 'yt-dlp' && tl.latest ? (tl.newest
        ? `<div class="ok" title="${ta('{age} - checked {when}', {age: tl.age || '', when: String(tl.checked || '').replace('T', ' ').slice(0, 16)})}">${t('the newest version')}</div>`
        : `<div class="amber" title="${ta('checked {when}', {when: String(tl.checked || '').replace('T', ' ').slice(0, 16)})}">${t('{version} is out', {version: esc(tl.latest)})}</div>`)
      : tl.age ? `<div class="${tl.old ? 'amber' : 'dim'}" title="${tl.name === 'yt-dlp' ? ta('its version is its release date; sites like TikTok and Instagram change faster than that - the newest version could not be checked yet') : ta('its version is its release date; sites like TikTok and Instagram change faster than that')}">${esc(tl.age)}</div>` : ''}${tl.name === 'deno' && tl.found && tl.old ? `<div class="amber">${t('too old: 2.3 or newer')}</div>` : ''}</td>
      <td class="small muted">${esc(t(tl.how))}${tl.name === 'yt-dlp' && tl.found && !tl.newest ? ` <button class="btn sm${tl.old ? ' pri' : ''}" data-ytup title="${ta('Updates {what} - nothing else is installed', {what: tl.install || 'yt-dlp'})}">${t('Update yt-dlp')}</button>` : ''}${tl.name === 'deno' && (!tl.found || tl.old) ? ` <button class="btn sm" data-copy="winget install DenoLand.Deno" title="${ta('Paste it into a terminal (PowerShell), then restart MotionLab')}">${t('Copy the install command')}</button>` : ''}${tl.name === 'hyperframes' && (!tl.found || /not downloaded/.test(tl.version || ''))
        ? ((S.tools.find(x => x.name === 'node') || {}).found ? ` <button class="btn sm" data-hfinst>${t('Install')}</button>` : ` <b>${t('Install Node.js first.')}</b>`) : ''}${tl.name === 'speech' && (!tl.found || /not downloaded/.test(tl.version || ''))
        ? ` <button class="btn sm" data-spinst>${t('Install')}</button>` : ''}</td></tr>`).join('')}
    </tbody></table><pre class="log" id="ytlog" hidden style="max-height:160px;margin-top:8px"></pre>${upstreamBox(S)}</div>
  <div class="grid g2" style="margin-top:14px">
    <div class="panel"><h2>${t('Downloads (yt-dlp)')}</h2><div class="form">
      <label for="ytp">yt-dlp.exe</label><input type="text" id="ytp" value="${esc(st.ytdlp_path)}" placeholder="${ta('empty = find it automatically')}">
      <label for="pre">${t('Default format')}</label><select id="pre">${S.presets.map(o => `<option value="${o.id}" ${o.id === st.download_preset ? 'selected' : ''}>${esc(t(o.label))} → ${esc(o.folder)}</option>`).join('')}</select>
      <label for="nm">${t('File name')}</label><input type="text" id="nm" class="mono" value="${esc(st.download_name)}">
      <span></span><div class="small muted">${t('yt-dlp fields, e.g. <code>%(title).80s [%(id)s].%(ext)s</code> or <code>%(uploader)s - %(title)s.%(ext)s</code> (no folders)')}</div>
      <label>YouTube</label><div class="small">${(S.deno || {}).found ? ((S.deno.new_enough ? `<span class="ok">${t('ready')}</span>` : `<span class="amber">${t('Deno is too old')}</span>`) + ' - ' + t('Deno {version} found (YouTube downloads need it)', {version: esc(S.deno.version || '')}))
        : `<span class="amber">${t('Deno is missing')}</span> - ${t('recent yt-dlp needs it for YouTube. Install it with <code>winget install DenoLand.Deno</code> in a terminal, then restart MotionLab.')} <button class="btn sm" data-copy="winget install DenoLand.Deno">${t('Copy')}</button>`}</div>
      <label>${t('Logins')}</label><div><label class="chk"><input type="checkbox" id="dlin" ${st.download_login ? 'checked' : ''}><span>${t('Use my browser\'s login for downloads')}</span></label>
        <div class="row" style="margin:4px 0"><select id="dbr" ${st.download_login ? '' : 'disabled'}>${(S.browsers || []).map(b => `<option value="${b.id}" ${b.id === (st.download_browser || 'firefox') ? 'selected' : ''}>${esc(t(b.label))}</option>`).join('')}</select></div>
        <div class="small muted">${t('For videos that need you logged in (Instagram, Vimeo, YouTube\'s “are you a bot” check). It uses your own login from that browser, on this PC only: the downloader reads it for each download, and MotionLab keeps it nowhere and sends it nowhere. Firefox works best - Chrome and Edge lock and encrypt their logins, so with them it often fails (close the browser first).')}</div></div></div></div>
    <div class="panel"><h2>Claude Code</h2><div class="form">
      <label for="clp">claude</label><input type="text" id="clp" value="${esc(st.claude_path)}" placeholder="${ta('empty = find it automatically')}">
      <label for="clm">${t('Model')}</label><select id="clm">${(S.models || ['opus', 'fable', 'auto']).map(m => `<option value="${m}" ${(st.claude_model || 'opus') === m ? 'selected' : ''}>${esc(MODEL_WORDS[m][0])} - ${esc(MODEL_WORDS[m][1])}</option>`).join('')}</select>
      <label for="cle">${t('Effort')}</label><select id="cle"><option value="auto" ${st.claude_effort === 'auto' ? 'selected' : ''}>${t('Recommended for each task: checking a video {review}, feedback {feedback}, recreating a video {recreate}, writing prompts {prompt}, writing scripts {script}, titles and thumbnails {title}, what next {plan} (one level less on Fable)', {review: esc(S.tasks.review), feedback: esc(S.tasks.feedback), recreate: esc(S.tasks.recreate), prompt: esc(S.tasks.prompt || 'medium'), script: esc(S.tasks.script || 'high'), title: esc(S.tasks.title || 'high'), plan: esc(S.tasks.plan || 'medium')})}</option>
        ${S.efforts.map(x => `<option value="${x}" ${st.claude_effort === x ? 'selected' : ''}>${t('always {level}', {level: x})}</option>`).join('')}</select>
      <span></span><label class="chk"><input type="checkbox" id="cla" ${st.claude_ask === false ? '' : 'checked'}><span>${t('Ask me which model and effort every time a button opens Claude Code (the dialog)')}</span></label>
      <span></span><div class="small muted">${t('Opus works on every Claude plan; Fable is the strongest model for long or open-ended work (checking a video, recreating or generating one) and on Max plans has its own weekly limit. Effort = how hard Claude thinks: higher is more careful, slower, and uses more of your Claude plan; “max” is for a problem Claude got stuck on. In a running window you can still change them with <code>/model</code> and <code>/effort</code>.')}</div>
      <label>DaVinci Resolve</label><div>${(S.resolve_mcp || {}).registered
          ? `<span class="ok">${t('Claude Code can look into DaVinci Resolve')}</span> <span class="small muted">${t('(MCP {version}, this PC, safe mode on)', {version: esc(S.resolve_mcp.version || '')})}</span> <button class="btn sm" data-rmcp="resolve_mcp_remove">${t('Disconnect')}</button>`
          : `<button class="btn sm" data-rmcp="resolve_mcp_install">${t('Connect Claude Code to DaVinci Resolve (MCP)')}</button>`}
        <div class="small muted">${t('Optional, needs Resolve Studio and Node.js. Claude can then read your open project (timelines, clips, markers) in a chat; it asks before changing anything there, and the lab\'s own Resolve builder still makes the rebuilds. New chats pick it up.')}</div></div></div>
      <div class="small muted" style="margin-top:10px">${t('The review of every contact sheet, learning from your feedback and the rebuilds run in Claude Code; the app opens it in the lab folder with the exact request, so Claude starts working right away.')}</div>
      <div class="row" style="margin-top:10px">${claudeBtn('', t('Open Claude Code in the lab folder'))}<button class="btn sm" data-tips>${t('Tips for working with Claude')}</button></div></div>
  </div>
  <div class="panel" style="margin-top:14px"><h2>${ta('Sharing & updates')}</h2>
    ${updateBox(S.update, null)}
    ${((S.update || {}).kept || []).map(k => keptLine(k.name, k.files)).join('')}
    <div class="form">
      <label for="who">${t('Your name')}</label><div><input type="text" id="who" value="${esc(st.author)}" placeholder="${ta('e.g. alex (shown on what you share)')}" style="max-width:320px">
        <div class="small muted">${t('Used for “Share my knowledge” - letters, numbers and - only.')}</div></div>
      <label>GitHub</label><div class="small">${S.update && S.update.remote ? `<span class="mono">${esc(S.update.remote)}</span> · ${t('branch {branch}', {branch: esc(S.update.branch || '')})}` : `<span class="muted">${esc((S.update && S.update.error) || t('not checked yet'))}</span>`}
        ${S.update && S.update.checked ? `<div class="dim">${t('checked {when}', {when: esc(S.update.checked)})} · ${S.update.can_update ? `<b class="amber">${tn(S.update.behind, '{n} update(s) waiting', '{n} update(s) waiting')}</b>` : t('up to date')}${S.update.ahead ? ' · ' + tn(S.update.ahead, '{n} of your commits not on GitHub yet', '{n} of your commits not on GitHub yet') : ''}${testingText(S.update)}</div>` : ''}</div>
      <label>${t('Updates')}</label><div class="col" style="gap:4px">
        <label class="chk small"><input type="radio" name="upm" value="ask" ${st.update_mode === 'ask' ? 'checked' : ''}><span>${t('show the <b>Update available</b> button with what\'s new and wait for my click (recommended)')}</span></label>
        <label class="chk small"><input type="radio" name="upm" value="auto" ${st.update_mode === 'auto' ? 'checked' : ''}><span>${t('install new versions by itself when MotionLab starts, then show what\'s new')}</span></label>
        <label class="chk small"><input type="radio" name="upm" value="off" ${st.update_mode === 'off' ? 'checked' : ''}><span>${t('don\'t look for updates (<i>Check now</i> still works)')}</span></label>
        <div class="small muted">${t('An update never touches your videos, analyses, verdicts, settings or knowledge.')}</div></div>
      <span></span><div class="row"><button class="btn sm" id="upcheck">${t('Check now')}</button>${S.update && S.update.can_update ? `<button class="btn sm pri" data-update>${t('Update now')}</button>` : ''}</div>
      ${S.update && !S.update.repo ? `<label for="conn">${t('Connect to GitHub')}</label><div>${S.update.git ? `<div class="row"><input type="text" id="conn" value="${esc(S.home_repo || '')}" placeholder="${ta('https://github.com/name/MotionLab')}" style="max-width:360px"><button class="btn sm" id="connb">${t('Connect')}</button></div>
        <div class="small muted">${t('This copy was not installed with git clone. Connecting turns on updates and sharing; only the app\'s own files are replaced by the repo\'s last tested version.')}</div>`
        : `<div class="small">${t('Double-click <b>setup.bat</b> in the MotionLab folder - it installs git and connects this copy.')}</div>`}</div>` : ''}
    </div></div>
  <div class="row" style="margin-top:12px"><button class="btn pri" id="save">${t('Save settings')}</button><span id="sv" class="small muted"></span></div>
  <div class="grid g2" style="margin-top:14px">
    <div class="panel"><h2>${t('Shortcuts')}</h2><div class="small muted">${t('A “MotionLab” shortcut with the app icon, opens the app without a console window.')}</div>
      <div class="row" style="margin-top:10px"><button class="btn" data-sc="desktop">${t('Add to the Desktop')}</button><button class="btn" data-sc="startmenu">${t('Add to the Start menu')}</button></div></div>
    <div class="panel"><h2>${t('About')}</h2><div class="kv"><b>${t('Version')}</b><span>MotionLab ${esc(S.version)}</span><b>${t('Lab folder')}</b><span class="mono small">${esc(S.lab)}</span></div>
      <div class="row" style="margin-top:10px"><button class="btn" data-open=".">${t('Open the lab folder')}</button>${reportBtn('', '')}</div>
      <div class="small muted" style="margin-top:6px">${t('Something not working? <i>Report a problem</i> shows you the report first, then opens it on GitHub for you to send.')}</div></div>
  </div>`;
  $('#recheck').onclick = async e => {             // also asks again for the newest yt-dlp / HyperFrames / GSAP
    e.target.disabled = true;
    try { await api('/api/upstream/check', {}); } catch (err) { toast(err.message, 'err'); }
    route();
  };
  $$('#langseg button', main).forEach(b => b.onclick = async () => {
    if (b.classList.contains('on')) return;
    try { await api('/api/settings', {settings: {language: b.dataset.v}}); location.reload(); }
    catch (e) { toast(e.message, 'err'); }
  });
  $$('[data-copy]', main).forEach(b => b.onclick = () => copy(b.dataset.copy));
  $('#dlin').onchange = e => { $('#dbr').disabled = !e.target.checked; };
  const ytb = $('[data-ytup]', main); if (ytb) ytb.onclick = async () => {   // Update yt-dlp: a job, the result in words
    ytb.disabled = true; ytb.textContent = t('Updating…');
    const j = await startJob('ytdlp_update', {}, false);
    if (!j) { ytb.disabled = false; ytb.textContent = t('Update yt-dlp'); return; }
    const pre = $('#ytlog'); pre.hidden = false; pre.textContent = '';
    followJob(j.id, pre, jj => {
      const last = pre.textContent.trim().split('\n').pop() || jj.status;
      toast(last, jj.status === 'done' ? 'ok' : 'err');
      if (jj.status === 'done') setTimeout(route, 2500);
      else { ytb.disabled = false; ytb.textContent = t('Update yt-dlp'); pre.insertAdjacentHTML('afterend', `<div class="row">${reportBtn(jj.id)}</div>`); }
    });
  };
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
    const b = $('#upcheck'); b.disabled = true; b.textContent = t('Checking…');
    try {
      const u = await api('/api/update/check', {});
      toast(u.error ? u.error : u.can_update ? (u.kind === 'version' ? t('MotionLab {version} is available', {version: u.new_version}) : t('{changes} on GitHub', {changes: plural(u.behind, 'change')})) : t('Up to date'), u.error ? 'err' : 'ok');
      route(); ping();
    }
    catch (e) { toast(e.message, 'err'); b.disabled = false; b.textContent = t('Check now'); }
  };
  const cb = $('#connb'); if (cb) cb.onclick = async () => {
    if (!confirm(t('Connect this copy to {url}? The app\'s own files are replaced by the repo version; your data stays.', {url: $('#conn').value}))) return;
    try { const r = await api('/api/update/connect', {url: $('#conn').value}); toast(t('Connected to {remote}', {remote: r.remote}), 'ok'); route(); } catch (e) { toast(e.message, 'err'); }
  };
  $('#save').onclick = async () => {
    try {
      await api('/api/settings', {settings: {ytdlp_path: $('#ytp').value, download_preset: $('#pre').value,
                                             download_name: $('#nm').value, claude_path: $('#clp').value,
                                             claude_effort: $('#cle').value, claude_model: $('#clm').value,
                                             claude_ask: $('#cla').checked,
                                             download_login: $('#dlin').checked, download_browser: $('#dbr').value,
                                             author: $('#who').value,
                                             update_mode: ($('input[name=upm]:checked') || {}).value || 'ask'}});
      $('#sv').textContent = t('saved ✓'); toast(t('Settings saved'), 'ok'); setTimeout(route, 500);
    } catch (e) { toast(e.message, 'err'); }
  };
  $$('[data-sc]', main).forEach(b => b.onclick = async () => {
    try { const r = await api('/api/shortcut', {where: b.dataset.sc}); toast(t('Shortcut created: {path}', {path: r.path}), 'ok'); }
    catch (e) { toast(e.message, 'err'); }
  });
}

// ============================================================================================ category / tags editor
async function metaModal(R) {
  const ST = await api('/api/settings');
  modal(`<h2>${t('Category and tags')}</h2>
    <p class="hint">${t('What kind of video this is. Pacing, effects and lessons are compared within a category, and shared that way.')}</p>
    <div class="form"><label for="mcat">${t('Category')}</label><select id="mcat">${ST.categories.map(o => `<option value="${o.id}" ${o.id === R.category ? 'selected' : ''}>${esc(t(o.label))}</option>`).join('')}</select>
      <label for="mtags">${t('Tags')}</label><input type="text" id="mtags" value="${esc((R.tags || []).join(', '))}" placeholder="${ta('e.g. instagram, asmr, recipe')}"></div>
    <div class="row" style="margin-top:12px"><button class="btn pri" id="msave">${t('Save')}</button></div>`, el => {
    $('#msave', el).onclick = async () => {
      try { await api(`/api/reference/${encodeURIComponent(R.name)}/meta`, {category: $('#mcat', el).value, tags: $('#mtags', el).value}); closeModal(); toast(t('Saved'), 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    };
  });
}

// ---- Claude's memory > Shared knowledge (2026-10-18, replaces Share with friends; the user: "make the share knowledge
// a more distinct section in the claudes memory. i should be able to click it and know what is being shared or from
// where or even select what id like to share (imagine i had tests)"): What you share (every video and lesson of this
// PC with a tick - ticked = it goes with the next share, unticked = kept on this PC: POST /api/knowledge/private - a
// test-looking one starts unticked), Shared before, From friends (per friend: their videos, the lessons waiting for a
// review, the rules that came from them), Files from friends, Pacing by kind of video. Plain words: no file names,
// folder paths or the GitHub address on the page.
const fmtNum = v => v == null ? '–' : numStr(v);
// a card's format label "Vertical · 0:09": its shape word in the app's language, the length as it is
const fmtShape = s => { const [shape, ...rest] = String(s || '').split(' · '); return [t(shape), ...rest].join(' · '); };
const REVIEW_INCOMING = 'Review the incoming lessons in knowledge\\incoming\\ (see Reviewing incoming lessons in the analyze-reference skill; the *-making.md files are lessons on making videos for .claude\\skills\\recreate-video\\lessons.md) and merge the good ones';
async function memShared(main) {
  let [K, U] = await Promise.all([api('/api/knowledge'), api('/api/update').catch(() => ({}))]);
  let msg = '';                                      // the last share's result, kept across redraws
  const open = {};                                   // which folded parts are open (kept across redraws)
  const isOpen = k => open[k] ? 'open' : '';
  const sharedWhen = x => x.shared_when ? t('shared {day}', {day: esc(shDay(x.shared_when))}) : t('shared');
  const stateChip = x => !x.ticked ? `<span class="shst kept">${t('kept on this PC')}</span>${x.state !== 'new'           // shared before
      ? ` <span class="small muted">${t('already with your friends - unticking stops new changes')}</span>` : ''}`
    : x.state === 'new' ? `<span class="shst new">${t('new|share state')}</span>`
    : x.state === 'changed' ? `<span class="shst chg">${x.shared_when ? t('changed since you shared it on {day}', {day: esc(shDay(x.shared_when))}) : t('changed since you shared it')}</span>`
    : `<span class="shst done">${sharedWhen(x)}</span>`;
  const warn = x => [x.test ? `<span class="shwarn" title="${ta('Its name says it was a test - it stays on this PC unless you tick it')}">${t('looks like a test')}</span>` : '',
    (x.files || []).length ? `<span class="shwarn" title="${ta('Its text names files or folders on this PC (see the whole lesson)')}">${t('names a file on your PC - friends would see the name')}</span>` : ''].join(' ');
  const cardRow = c => `<label class="shrow${c.ticked ? '' : ' off'}"><input type="checkbox" data-kind="card" value="${esc(c.id)}" ${c.ticked ? 'checked' : ''}>
      ${c.thumb ? `<img src="${fileUrl(c.thumb)}" loading="lazy" alt="">` : '<span class="cvnoimg"></span>'}
      <span class="grow"><b>${esc(c.label)}</b>${c.by || c.platform ? ` <span class="small muted">${[c.by ? t('by {name}', {name: esc(c.by)}) : '', esc(c.platform || '')].filter(Boolean).join(' · ')}</span>` : ''}
        <span class="small muted stpl">${[esc(fmtShape(c.format)), esc(t(c.category_label || ''))].filter(Boolean).join(' · ')}</span>
        <span class="shmeta">${stateChip(c)} ${warn(c)}</span></span>
      ${c.analysis ? `<a class="btn sm ghost" href="#/ref/${encodeURIComponent(c.analysis)}">${t('Open')}</a>` : ''}</label>`;
  const lessonRow = x => { const once = x.state === 'shared';      // a lesson goes once: shared = nothing left to send
    return `<div class="shrow shles${x.ticked || once ? '' : ' off'}"><input type="checkbox" data-kind="lesson" value="${esc(x.id)}" ${x.ticked || once ? 'checked' : ''}
        ${once ? `disabled title="${ta('Already shared - a lesson goes once')}"` : ''} aria-label="${ta('Share {id}', {id: x.id})}">
      <span class="grow"><span class="tag">${esc(x.id)}</span> <span class="small muted">${x.kind === 'making' ? t('making videos') : t('analysing videos')}${x.note ? ' · ' + esc(x.note) : ''}</span>
        <div class="small">${esc(x.first)}</div>
        ${x.text !== x.first ? `<details data-k="les-${esc(x.id)}" ${isOpen('les-' + x.id)}><summary class="small muted">${t('The whole lesson')}</summary><div class="small shfull">${esc(x.text)}</div></details>` : ''}
        <span class="shmeta">${once ? `<span class="shst done">${sharedWhen(x)}</span>` : stateChip(x)} ${warn(x)}</span></span></div>`; };
  const shareRow = s => `<div class="shbf"><b>${esc(shDay(s.when) || s.when || '')}</b> <span class="small muted">${s.how === 'github' ? t('on GitHub') : s.how === 'file' ? t('as a file for a friend') : esc(s.how || '')}</span>
      <div class="small">${[...(s.names || []).map(esc), ...(s.lesson_ids || []).map(i => `<span class="tag">${esc(i)}</span>`)].join(' · ')
        || `${plural(s.cards || 0, 'video')}, ${plural(s.lessons || 0, 'lesson')}`}</div></div>`;
  const friendPanel = g => {
    const nl = g.incoming.reduce((a, x) => a + x.lessons.length, 0);
    return `<div class="shfr"><div class="row sp"><b class="shwho"><svg class="i"><use href="#i-shared"/></svg>${esc(g.author)}</b>
        <span class="small muted">${[g.cards.length ? plural(g.cards.length, 'video') : '', nl ? tn(nl, '{n} lesson waiting for a review', '{n} lessons waiting for a review') : '',
          g.rules.length ? tn(g.rules.length, '{n} rule reviewed', '{n} rules reviewed') : ''].filter(Boolean).join(' · ')}${g.last ? ' · ' + t('last shared {day}', {day: esc(shDay(g.last))}) : ''}</span></div>
      ${g.cards.map(c => `<div class="shfc"><div class="grow"><b>${esc(c.label)}</b> <span class="small muted">${[c.by ? t('by {name}', {name: esc(c.by)}) : '',
          c.url ? `<a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.platform || t('the original'))}</a>` : esc(c.platform || ''), esc(fmtShape(c.format)),
          esc(t(c.category_label || ''))].filter(Boolean).join(' · ')}</span>${c.summary ? `<div class="small muted">${esc(c.summary)}</div>` : ''}</div>
        <button class="btn sm" data-fcard="${esc(c.file)}">${t('Open')}</button></div>`).join('')}
      ${g.incoming.map(x => { const k = `inc-${g.author}-${x.when}-${x.kind}`, n = x.lessons.length;
        return `<details class="shinc" data-k="${esc(k)}" ${isOpen(k)}><summary><b>${x.kind === 'making' ? tn(n, '{n} lesson on making videos', '{n} lessons on making videos') : tn(n, '{n} lesson on analysing videos', '{n} lessons on analysing videos')}</b>
          <span class="small muted">· ${t('shared {day} · waiting for a review - not rules yet', {day: esc(shDay(x.when))})}</span></summary>
          ${x.lessons.map(l => `<div class="shil"><span class="tag">${esc(l.id)}</span> <span class="small">${esc(l.first)}</span>${l.note ? ` <span class="small dim">(${esc(l.note)})</span>` : ''}</div>`).join('')}</details>`; }).join('')}
      ${nl ? `<div class="row" style="margin-top:8px">${claudeBtn(REVIEW_INCOMING, t('Review them in Claude Code'), 'lessons')}<span class="small muted">${t('Claude keeps the concrete, checkable ones as rules for everybody and drops the rest.')}</span></div>` : ''}
      ${g.rules.length ? `<div class="small" style="margin-top:8px"><b>${t('Rules that came from {name}:', {name: esc(g.author)})}</b> ${g.rules.map(r => `<span class="tag" title="${esc(r.first)}">${esc(r.id)}</span>`).join(' ')}</div>` : ''}</div>`;
  };
  const inboxRow = x => x.error ? `<div class="shib"><span class="bad small">${t('A file that is not a MotionLab knowledge file, or is damaged - ask your friend to send it again.')}</span></div>`
    : `<div class="shib"><div class="grow">${sharedChip(x.author, x.made)} <span class="small muted">${t('made {day}', {day: esc(shDay(x.made) || x.made || '')})}</span>
        <div class="small">${[x.cards ? `${plural(x.cards, 'video')}: ${(x.names || []).map(esc).join(' · ')}` : '',
          x.lessons ? `${plural(x.lessons, 'lesson')}: ${(x.lesson_ids || []).map(i => `<span class="tag">${esc(i)}</span>`).join(' ')}` : ''].filter(Boolean).join('<br>') || t('nothing in it')}</div></div>
      <button class="btn sm pri" data-imp="${esc(x.file)}">${t('Import')}</button></div>`;
  const draw = () => {
    $$('details[data-k]', main).forEach(d => { open[d.dataset.k] = d.open; });
    const N = K.next_share || {total: 0, cards: 0, lessons: 0}, kept = K.kept || {cards: 0, lessons: 0}, mine = K.mine || {cards: [], lessons: []};
    const keptN = kept.cards + kept.lessons, me = K.author;
    main.innerHTML = `<div class="small muted shintro">${t('What MotionLab shares with your friends and what came from them - only text and numbers, never your videos, frames or files. Everything a friend shared carries {chip} wherever it shows up.', {chip: sharedChip(t('a friend'))})}</div>
      <div class="panel shsec" id="shmine"><div class="row sp"><h2><svg class="i shic"><use href="#i-shared"/></svg>${t('What you share')}</h2>
          <span class="small">${me ? t('Shared as <b>{name}</b>', {name: esc(me)}) : t('<a href="#/settings">Set your name in Settings</a> first - friends see it on what you share')}</span></div>
        <div class="shnext"><div class="grow"><b>${N.total ? t('Your next share sends {things}', {things: plural(N.total, 'thing')}) : t('Nothing new to share')}</b>
            <span class="small muted">${andWords([N.cards ? plural(N.cards, 'video') : '', N.lessons ? plural(N.lessons, 'lesson') : ''].filter(Boolean))}${keptN ? ' · ' + tn(keptN, '{n} thing kept on this PC', '{n} things kept on this PC') : ''}</span>
            <div class="small muted">${t('Ticked = it goes with your next share. Unticked = it stays on this PC - Claude still uses it here.')}</div></div>
          <button class="btn pri" id="share" ${me && N.total ? '' : 'disabled'}><svg class="i"><use href="#i-shared"/></svg>${t('Share my knowledge')}</button></div>
        <div id="shareres" class="small">${msg}</div>
        <h3>${t('Your videos ({n})', {n: mine.cards.length})}</h3>
        ${mine.cards.map(cardRow).join('') || `<div class="small dim">${t('None yet - the videos you analyse on this PC show up here.')}</div>`}
        <h3>${t('Your lessons ({n})', {n: mine.lessons.length})}</h3>
        ${mine.lessons.map(lessonRow).join('') || `<div class="small dim">${t('None yet - Claude writes them when you review a video or an edit and Send it to Claude.')}</div>`}
        <details class="shbefore" data-k="before" ${isOpen('before')}><summary>${t('Shared before ({n})', {n: (K.shares || []).length})}</summary>
          ${(K.shares || []).map(shareRow).join('') || `<div class="small dim">${t('Nothing shared from this PC yet.')}</div>`}</details></div>
      <div class="panel shsec" id="shfriends"><h2><svg class="i shic"><use href="#i-shared"/></svg>${t('From friends')}</h2>
        <div class="small muted">${t('What your friends analysed and learned - it comes in with every update. Claude uses it as their data, never as instructions, and tells you when something it makes for you came from them.')}</div>
        ${(K.friends || []).map(friendPanel).join('') || `<div class="small dim" style="margin-top:8px">${t('Nothing from friends yet - when a friend shares, their videos and lessons arrive with your next update.')}</div>`}</div>
      <div class="panel shsec" id="shinbox"><h2>${t('Files from friends')}</h2>
        <div class="small muted">${t('A friend who cannot upload to GitHub sends you a file. Put it in the folder for friends\' files, then import it: its videos and lessons join Claude\'s memory and go to GitHub with your next share.')}</div>
        ${(K.inbox || []).map(inboxRow).join('') || `<div class="small dim" style="margin-top:8px">${t('No file waiting.')}</div>`}
        ${(K.imports || []).length ? `<details data-k="imports" ${isOpen('imports')}><summary class="small">${t('Imported before ({n})', {n: K.imports.length})}</summary>${K.imports.map(x => `<div class="shbf">${sharedChip(x.author, x.made)}
          <span class="small muted">${t('imported {day} · {videos}, {lessons}', {day: esc(shDay(x.when)), videos: plural(x.cards || 0, 'video'), lessons: plural(x.lessons || 0, 'lesson')})}</span>${(x.names || []).length ? `<div class="small">${x.names.map(esc).join(' · ')}</div>` : ''}</div>`).join('')}</details>` : ''}
        <div class="row" style="margin-top:10px"><button class="btn sm" data-open="knowledge/inbox"><svg class="i"><use href="#i-folder"/></svg>${t('Open the folder for friends\' files')}</button>
          <span class="small muted">${U.remote ? t('This copy is connected to GitHub.') : U.repo === false ? t('This copy is not connected to GitHub - your shares are saved as a file to send.') : ''}</span></div></div>
      <details class="panel shpace" data-k="pace" ${isOpen('pace')}><summary><b>${t('Pacing by kind of video')}</b> <span class="small muted">· ${t('the typical numbers of every video Claude knows, yours and your friends\'')}</span></summary>
        <table class="t" style="margin-top:8px"><thead><tr><th>${t('Kind of video')}</th><th class="num">${t('Videos')}</th><th>${t('By|author')}</th><th class="num">${t('Cuts / min')}</th><th class="num">${t('Avg shot')}</th><th class="num">${t('Cuts in 3 s')}</th><th class="num">${t('Effects / min')}</th><th class="num">${t('On beat')}</th><th>${t('Effects seen most')}</th></tr></thead><tbody>
          ${(K.categories || []).map(c => `<tr><td><b>${esc(t(c.label))}</b></td><td class="num">${numStr(c.references)}</td><td class="small">${esc(c.authors.join(', '))}</td>
            <td class="num">${fmtNum(c.cuts_per_min)}</td><td class="num">${c.avg_shot_s == null ? '–' : numStr(c.avg_shot_s) + ' s'}</td><td class="num">${fmtNum(c.hook_cuts_3s)}</td><td class="num">${fmtNum(c.effects_per_min)}</td>
            <td class="num">${c.cuts_on_beat_pct == null ? '–' : numStr(c.cuts_on_beat_pct) + ' %'}</td><td class="small muted">${Object.entries(c.families).slice(0, 4).map(([f, n]) => `${esc(t(f))} ${numStr(n)}`).join(' · ')}</td></tr>`).join('')
            || `<tr><td colspan="9" class="dim">${t('No videos yet - analyse one (Analyser).')}</td></tr>`}</tbody></table></details>`;
    memTabCount(null, K);
    $$('input[data-kind]', main).forEach(c => c.onchange = async () => {     // a tick: shared next time / kept here
      $$('input[data-kind]', main).forEach(x => { x.disabled = true; });
      try { K = await api('/api/knowledge/private', {kind: c.dataset.kind, ids: [c.value], private: !c.checked}); }
      catch (e) { toast(e.message, 'err'); }
      draw();
    });
    $$('[data-fcard]', main).forEach(b => b.onclick = () => cardModal({_file: b.dataset.fcard}));
    $$('[data-imp]', main).forEach(b => b.onclick = async () => {
      b.disabled = true;
      try { const r = await api('/api/knowledge/import', {file: b.dataset.imp}); toast(t('Imported {videos} and {lessons} from {name}', {videos: plural(r.cards, 'video'), lessons: plural(r.lessons, 'lesson'), name: r.author}), 'ok'); K = await api('/api/knowledge'); draw(); }
      catch (e) { toast(e.message, 'err'); b.disabled = false; }
    });
    $('#share', main).onclick = async () => {
      const b = $('#share', main); b.disabled = true; b.textContent = t('Sharing…');
      try {
        const r = await api('/api/knowledge/share', {});
        const what = andWords([r.cards ? plural(r.cards, 'video') : '', r.lessons ? plural(r.lessons, 'lesson') : ''].filter(Boolean));
        if (r.pushed && r.restarting) { waitForServer(t('Shared ✓ - GitHub also had a new MotionLab version: restarting with it…')); return; }
        msg = r.nothing ? `<span class="muted">${t('Nothing new to share.')}</span>`
          : r.pushed ? `<span class="ok">${t('Shared {what} on GitHub ✓', {what: esc(what)})}</span> <span class="muted">${t('- your friends get them with their next update.')}</span>`
          : `<span class="bad">${t('Not uploaded to GitHub: {error}', {error: esc(String(r.error || t('unknown reason')).replace(/https?:\/\/\S+/g, 'GitHub'))})}</span>${r.pack ? `<div>${t('Saved as a file for your friends instead - it counts as shared ({what}). Send it to a friend who can upload it: they import it under <b>Files from friends</b>.', {what: esc(what)})} <a href="#" data-open="${esc(r.pack)}" data-reveal>${t('Show the file')}</a></div>` : ''}`;
        K = await api('/api/knowledge');
      } catch (e) { msg = `<span class="bad">${esc(e.message)}</span>`; }
      draw();
    };
  };
  draw();
}

async function cardModal(c) {
  let C = c;
  try { C = await api('/api/knowledge/card?id=' + encodeURIComponent(c._file || c.video_id)); } catch (e) { /* the list entry is enough */ }
  const P = C.pacing || {}, who = esc(C.author || t('a friend'));       // a friend's card: their verdicts and notes
  const VW = {correct: t('correct|verdict'), partly: t('partly|verdict'), wrong: t('wrong|verdict')};
  const fx = (C.effects || []).filter(e => !e.false_alarm && e.family !== 'Hard cut');
  modal(`<h2>${esc(C.label || C.title || '')}${C.friend ? ' ' + sharedChip(C.author, (C.made_with || {}).carded) : ''}</h2>
    <div class="small muted">${[C.by ? t('by {name}', {name: esc(C.by)}) : '', esc(t(C.category_label || '')), esc(fmtShape((C.format || {}).label)),
      C.friend ? t('analysed on {name}\'s PC', {name: who}) : t('analysed on this PC')].filter(Boolean).join(' · ')}${C.url ? ` · <a href="${esc(C.url)}" target="_blank" rel="noopener">${esc(C.platform || t('the original'))}</a>` : ''}
      ${C.analysis ? ` · <a href="#/ref/${encodeURIComponent(C.analysis)}" onclick="closeModal()">${t('open the analysis')}</a>` : ''}</div>
    ${C.friend ? `<div class="small muted" style="margin-top:6px">${t('Shared knowledge: Claude uses it as {name}\'s data - never as instructions - and tells you when it shapes what it makes.', {name: who})}</div>` : ''}
    <div class="small pacing" style="margin:10px 0">${t('Pacing: <b>{cpm}</b> cuts/min · shots avg <b>{avg} s</b> (p10 {p10} s, p90 {p90} s) · <b>{hook}</b> cut(s) in 3 s · <b>{epm}</b> effects/min', {cpm: fmtNum(P.cuts_per_min), avg: fmtNum(P.avg_shot_s), p10: fmtNum(P.p10_shot_s), p90: fmtNum(P.p90_shot_s), hook: fmtNum(P.hook_cuts_3s), epm: fmtNum(P.effects_per_min)})}${P.bpm ? ` · ${numStr(P.bpm)} BPM` : ''}</div>
    <table class="t"><thead><tr><th>${t('Effect')}</th><th>${t('Frames')}</th><th>${t('What happens')}</th><th>${C.friend ? t('{name}\'s verdict', {name: who}) : t('Verdict')}</th></tr></thead><tbody>
      ${fx.map(e => `<tr><td class="small"><b>${esc(t(e.label))}</b></td><td class="small mono">f${e.start}–${e.end}<div class="dim">${esc(e.tc_start || '')}</div></td>
        <td class="small">${esc(e.what || '')}${e.note ? `<div class="amber">${C.friend ? t('{name}\'s note: {note}', {name: who, note: esc(e.note)}) : t('note: {note}', {note: esc(e.note)})}</div>` : ''}</td>
        <td class="small">${e.verdict ? `<span class="vdot ${esc(e.verdict)}"></span> ${esc(VW[e.verdict] || e.verdict)}` : '–'}</td></tr>`).join('') || `<tr><td colspan="4" class="dim">${t('No effects besides cuts.')}</td></tr>`}
    </tbody></table>`);
}

route();
// after an update the restarted window shows once what came in (the CHANGELOG sections between the two versions)
api('/api/update').then(u => { const r = u && u.result; if (r && r.updated && !r.seen) whatsNewModal(r); }).catch(() => {});
