/* MotionLab app - js/memory.js: Claude's memory (#/memory).
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
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
      ${tile(S.friends ? S.mine : S.videos, t('videos analysed'), '#/analyze/videos')}
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
