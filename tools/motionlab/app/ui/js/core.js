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
  $('.mbody', m).innerHTML = html; m.hidden = false; $('.mbox', m).scrollTop = 0;
  $$('.brandrow', m).forEach(brandToggle);          // 0.6.0: a dialog's "For my brand" switch (drawn before init reads it)
  if (init) init($('.mbody', m));
}
function modalBack(fn) {               // call right after modal(): a "Back" to the dialog this one came from
  MODAL_BACK = fn;
  const b = document.createElement('button'); b.className = 'btn sm ghost mback'; b.textContent = t('← Back'); b.onclick = dismissModal;
  $('#modal .mbody').prepend(b);
}
let MU_AUDIO = null, MU_PLAYING = '';              // Music's player (closeModal stops it)
function closeModal() { MODAL_BACK = null; muStop(); $('#modal').hidden = true; $('#modal .mbody').innerHTML = ''; }
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
// More (2026-10-25, the user: "a menu thingy or three dots that expands and appears 'jobs and settings'"): opens
// Jobs and Settings in place; remembered; open by itself on those two pages
function sideMore(open) {
  $('#side-menu').hidden = !open; $('#side-more').setAttribute('aria-expanded', String(open));
  $('#side-more').classList.toggle('on', open);
  try { localStorage.setItem('ml.navMore', open ? '1' : ''); } catch (e) { /* storage blocked */ }
}
$('#side-more').onclick = () => sideMore($('#side-menu').hidden);
try { if (localStorage.getItem('ml.navMore')) sideMore(true); } catch (e) { /* storage blocked */ }
try { $('#brandnew').hidden = !!localStorage.getItem('ml.brandSeen'); } catch (e) { /* storage blocked: no chip */ }   // 0.6.0
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
const ALIASES = {'#/refs': '#/analyze/videos', '#/analyze/flux': '#/analyze/videos', '#/analyze/index': '#/analyze/notes', '#/analyze/content': '#/analyze/spark', '#/analyser': '#/analyze', '#/generator': '#/generate', '#/projects': '#/edit', '#/editor': '#/edit', '#/knowledge': '#/memory/shared', '#/library': '#/memory',
                 '#/memory/learned': '#/memory/shared'};     // 2026-10-18: Share with friends -> Shared knowledge
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
    if (nav === 'jobs' || nav === 'settings') sideMore(true);   // the open page's row stays in sight
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
const LIVE_PAGES = [[/^#?\/?$/, 'home'], [/^#\/analyze(?:\/(?:videos|spark|notes|thumbs|texts))?$/, 'analyze'], [/^#\/edit$/, 'projects'],
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

// heartbeat: keeps the server alive while the window is open; shows jobs + Resolve; notices updates / restarts
const PAGE_VERSION = (document.querySelector('meta[name=ml-version]') || {}).content || '';
let SERVER_BOOT = 0;                                       // the server's start as the first ping gave it (ping)
const API_LEVEL = 63;      // the server functions this page needs (server.API_LEVEL)
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
    // the server was started again since this window opened (the PC slept, MotionLab.bat again): the same version, but
    // a new session token - every button of this window was refused. Loaded again it has the new one (2026-11-10
    // review); a server from before that sends no "boot" - nothing to compare
    if (p.boot) { if (SERVER_BOOT && p.boot !== SERVER_BOOT) { location.reload(); return; } SERVER_BOOT = p.boot; }
    sideUpdate(p);
    liveLine(p.claude || []);
    $('#jobcount').textContent = p.running || '';
    $('#jobdot').textContent = p.running || '';                // the same count on More while it is closed
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
