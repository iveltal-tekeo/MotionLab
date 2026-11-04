/* MotionLab app - js/prepare.js: Prepare (#/prepare), Shared knowledge's pieces, the Generator (#/generate).
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
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
// category_label, focus, talk_pct, cuts_per_min, checked, spark, spark_only}: from GET /api/styles, or GET /api/memory
// on an older server (its local videos only - friends' cards are never offered in a picker). o.talk = the talking ones
// first; o.spark = also the videos only SPARK read (2026-11-03: their structure and pacing - the edit and Prepare
// pickers; never My Brand's look or the Generator, which take effects / transitions / colour)
function ownVideos(M, o = {}) {
  const out = ((M && M.videos) || []).filter(v => (v.key || (v.origin === 'local' && v.analysis)) && (o.spark || !v.spark_only)).map(v => v.key ? v : {
    key: v.analysis, title: v.title, label: v.label || v.title, picture: null, by: v.by || '', platform: v.platform || '',
    line: Object.values(v.lines || {}).filter(Boolean).join(' · '), format: v.format, category_label: v.category_label,
    focus: v.focus, talk_pct: null, cuts_per_min: (v.pacing || {}).cuts_per_min, checked: !!v.summary, summary: v.summary || ''});
  return o.talk ? out.slice().sort((a, b) => ((b.talk_pct ?? 50) >= 30) - ((a.talk_pct ?? 50) >= 30)) : out;
}
// the gold SPARK chip on a reference SPARK read (2026-11-03): only = SPARK alone read it (its hook, structure and
// pacing - no effects); else the video's effects analysis has a SPARK too, and it goes with it
function sparkRefChip(only) {
  const tip = only ? ta('Read by SPARK: its hook, structure and pacing - no effects measured')
    : ta('Its SPARK goes with it: the hook, the structure and the pacing');
  return `<span class="refspk" title="${tip}"><svg class="i"><use href="#i-sparkle"/></svg>SPARK</span>`;
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
  const vids = ownVideos(S, {talk, spark: ['edit', 'talk', 'title'].includes(o.purpose)}), prs = o.prompts ? (S.prompts || []) : [];
  st.like = st.like || []; st.likePrompts = st.likePrompts || [];
  let q = '';
  const has = (...xs) => !q || xs.join(' ').toLowerCase().includes(q);
  const vrow = v => { const on = st.like.includes(v.key), full = !on && st.like.length >= max, low = talk && v.talk_pct != null && v.talk_pct < 30;
    return `<label class="cvitem${on ? ' on' : ''}${full ? ' off' : ''}${low ? ' stplow' : ''}" title="${esc(v.line || v.summary || '')}"><input type="checkbox" data-g="v" value="${esc(v.key)}" ${on ? 'checked' : ''} ${full ? 'disabled' : ''}>
      ${v.picture ? `<img src="${fileUrl(v.picture)}" loading="lazy" alt="">` : '<span class="cvnoimg"></span>'}
      <span class="grow"><b>${esc(v.label || v.title || v.key)}</b> ${focusChip(v.focus)}${v.spark ? ' ' + sparkRefChip(v.spark_only) : ''}
        ${v.by || v.platform ? `<span class="small muted stpl">${[v.by ? t('by {name}', {name: esc(v.by)}) : '', esc(v.platform || '')].filter(Boolean).join(' · ')}</span>` : ''}
        <span class="small muted stpl">${[esc((v.format || '').split(' · ').map((x, i) => i ? x : t(x)).join(' · ')), esc(t(v.category_label || '')), talk ? (v.talk_pct != null ? t('talking {pct} %', {pct: Math.round(v.talk_pct)}) : '')
          : v.cuts_per_min != null ? tn(v.cuts_per_min, '{n} cuts/min', '{n} cuts/min') : '', v.spark_only ? t('its structure and pacing') : v.checked ? t('checked by Claude') : t('not checked by Claude yet')].filter(Boolean).join(' · ')}${low ? ' · ' + t('too little talking to measure its pace') : ''}</span></span></label>`; };
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
    <div class="brandrow" id="sbrand"></div>
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
                                                    want: $('#swant', el).value, like: st.like, like_prompts: st.likePrompts,
                                                    brand: brandOn(el, '#sbrand')});
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
    <div class="brandrow" id="qbrand"></div>
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
          extra: $('#qextra', el).value, brand: brandOn(el, '#qbrand')});
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
    <div class="brandrow" id="tbrand"></div>
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
          orientation: st.orient, language: st.lang, style_refs: st.like, like_prompts: st.likePrompts, notes: $('#tnotes', el).value,
          brand: brandOn(el, '#tbrand')});
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
    <div class="brandrow" id="gbrand"></div>
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
          tool, colours: $('#gcol', el) ? $('#gcol', el).value : '', templates: gfx ? st.tpl : [], look: gfx ? st.look : '',
          brand: brandOn(el, '#gbrand')});
        openClaude(r.command, 'generate', r.project);
        closeModal(); location.hash = '#/project/' + encodeURIComponent(r.project);
      } catch (e) { toast(e.message, 'err'); }
    };
  }, 'wide');
}
