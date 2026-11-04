/* MotionLab app - js/video.js: Edit > a video (#/project): its page, What it took, Review.
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ---- Edit > a video (the user, 2026-10-15: "when I first click I want to see a thumbnail or the last render so I know
// in which video I am, instead of How did it turn out? or random information shot in my face; then the two buttons -
// not feeling right? review it and improve it (a new Review section with How did it turn out?) or start over; happy
// with it = the Publish part under the video, no Publish tab; Your footage its own tab"). Tabs: Overview (the newest
// render + an index of the page, the two buttons, Ready to post) | Review (a player + How did it turn out?) | Versions
// (edit versions + renders) | Footage | Graphics | Timing check and Resolve & library only when the video has them.
// The 0.4.3 addresses #/project/<p>/renders and /publish still work.
// the three ways into a video, each its own colour (2026-10-26, the user: "add some colors to accentuate the review page
// since its identical to the overview tab so we have some distinctions between the three"): Overview = the section's,
// Review = violet (Claude's colour: it hands the video to Claude), Editor = cyan (by hand) - app.css `.ptabs`, `#tab[data-t]`
const PTAB_ICON = {overview: 'i-videos', review: 'i-scriptok', editor: 'i-edit'};
async function pageProject(main, name, tab = 'overview') {
  const P = await api('/api/project/' + encodeURIComponent(name));
  if (tab === 'renders') tab = 'versions';
  if (tab === 'mini') tab = 'editor';                         // the Mini-editor's address (0.6.0 first part)
  const toPub = tab === 'publish';
  if (toPub) tab = 'overview';
  const nClips = P.sources.length, foot = P.sources.reduce((a, s) => a + (s.size || 0), 0);
  const tabs = [['overview', t('Overview')], ...(P.renders.length || (P.outcome || {}).aspects || tab === 'review' ? [['review', t('Review')]] : []),
                ...(P.plans.length || tab === 'editor' ? [['editor', t('Editor')]] : []), ['versions', `${t('Versions')}${P.plans.length ? ` (${P.plans.length})` : ''}`],
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
    <div class="tabs ptabs">${tabs.map(([k, l]) => `<a href="#/project/${encodeURIComponent(name)}/${k}" data-t="${k}" class="${k === tab ? 'on' : ''}">${PTAB_ICON[k] ? `<svg class="i"><use href="#${PTAB_ICON[k]}"/></svg>` : ''}${l}</a>`).join('')}</div>
    <div id="tab" data-t="${esc(tab)}"></div>`;
  const move = async editor => {
    try { await api(`/api/project/${encodeURIComponent(P.name)}/move`, {editor}); toast(editor ? t('Moved to the Editor') : t('Back in the Generator'), 'ok'); route(); }
    catch (e) { toast(e.message, 'err'); }
  };
  if (gen) $('#pjmove').onclick = () => move(true); else $('#pjnew').onclick = () => newEdit({project: P.name});
  const bk = $('#pjback'); if (bk) bk.onclick = () => move(false);
  $('#pjren').onclick = () => renameModal(P);
  const stopProg = progressPanel($('#pjprog'), () => { if (location.hash.startsWith('#/project/' + encodeURIComponent(name))) route(); },
                                 ['draft', 'miniedit', 'render', 'catalogue', ...THUMB_JOBS], j => (j.args || {}).project === P.name);
  onCleanup(stopProg);
  const el = $('#tab');
  if (tab === 'review') return projReview(el, P);
  if (tab === 'versions') return projVersions(el, P);
  if (tab === 'editor') return projEditor(el, P);
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
// one render at a time; more than one = a dropdown *Selected version* (newest first: v4 · newest · today 12:13 -
// 2026-10-26, the user: "it would help to have a dropdown of 'Selected version' instead of just a switch")
function renderPicker(box, P, onPick) {
  const R = newestFirst(P);
  box.innerHTML = R.length > 1 ? `<label class="rpick"><span>${t('Selected version')}</span><select>${R.map((r, i) =>
    `<option value="${i}">${renderLabel(r)}${i ? '' : ' · ' + t('newest')} · ${esc(whenWords(r.mtime))}</option>`).join('')}</select></label>` : '';
  const sel = $('.rpick select', box);
  const pick = i => { if (sel) sel.value = String(i); onPick(R[i]); };
  if (sel) sel.onchange = () => pick(+sel.value);
  if (R.length) pick(0);
  return R;
}
// a made_from video by name (data.project refs, 2026-10-18): this PC's = a link to its analysis, a friend's = the chip
const madeRef = r => r.author ? `${esc(r.label)} ${sharedChip(r.author, r.shared)}`
  : r.analysis ? `<a href="#/ref/${encodeURIComponent(r.analysis)}">${esc(r.label)}</a>`
  : r.spark ? `<a href="#/spark/${encodeURIComponent(r.spark)}">${esc(r.label)}</a>` : esc(r.label);    // a video SPARK read
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
  const on = new Set(again ? last.add : ['graphics', ...(a.captions === 'none' || !(a.captions || a.talk) ? [] : ['captions']), ...(a.sfx === 'none' || a.sfx_made ? [] : ['sfx'])]);
  const keep = [t('Pacing & cuts'), t('Effects & transitions'), t('Sound & music'), ...(a.sfx_made ? [t('Sound effects')] : [])];
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
  const pend = unrenderedPlan(P), wait = (LIVE || []).some(y => y.project === P.name);  // 2026-11-03: its shots first
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
        ${pend && !wait ? `<button class="onx shots" data-go="shots"><span class="oic"><svg class="i"><use href="#i-shots"/></svg></span>
          <span class="otx"><b>${t('{version} is not rendered yet - check its shots', {version: esc(pend.version)})}</b><span>${t('every shot as a picture: swap any, then render it')}</span></span><span class="oar">→</span></button>` : ''}
        ${draft ? `<button class="onx fin${nx === 'finish' ? ' on' : ''}" data-go="finish"><span class="oic"><svg class="i"><use href="#i-sparkle"/></svg></span>
          <span class="otx"><b>${t('Happy with the cuts? Finish it with Claude')}</b><span>${t('the cuts and transitions stay - Claude adds motion graphics, captions, sound effects')}</span></span><span class="oar">→</span></button>` : ''}
        ${P.plans.length ? `<button class="onx ed" data-go="editor"><span class="oic"><svg class="i"><use href="#i-edit"/></svg></span>
          <span class="otx"><b>${t('Change it yourself')}</b><span>${t('in the Editor: trim, move, speed, sounds and graphics - no Claude')}</span></span><span class="oar">→</span></button>` : ''}
        <button class="onx fix${nx === 'fix' ? ' on' : ''}" data-go="fix"><span class="oic"><svg class="i"><use href="#i-claude"/></svg></span>
          <span class="otx"><b>${t('Improve it with Claude')}</b><span>${t('rate each part on the Review tab - Claude makes the next version from your ratings')}</span></span><span class="oar">→</span></button></div>
      ${nx === 'start_over' ? '' : `<div class="pvover small"><a href="#" data-go="start_over">${t('Not the right feel at all? Start over with these clips')}</a></div>`}
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
      <div class="small muted">${wait ? t('A quick draft or Claude renders it - it plays here when it is ready.')
        : t('Look at every shot first - swap any you do not like - then render it.')}</div>
      ${wait ? '' : `<button class="btn pri" id="pvshots" style="margin-top:10px"><svg class="i"><use href="#i-shots"/></svg>${t('Check the shots')}</button>`}</div></div>`;
    const sb = $('#pvshots', el); if (sb) sb.onclick = () => shotsModal(P, pl.file);
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
  $$('[data-go]', el).forEach(b => b.onclick = async e => {
    e.preventDefault();
    if (b.dataset.go === 'editor') { location.hash = `#/project/${enc}/editor`; return; }
    if (b.dataset.go === 'shots') return shotsModal(P, pend.file);
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
  const item = (to, ic, label, s, tab = '') => `<a class="pvi${tab ? ' t-' + tab : ''}" href="${tab ? `#/project/${enc}/${tab}` : '#'}"${tab ? '' : ` data-to="${to}"`}>
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
    ${R0 && P.plans.length ? item('', 'i-edit', t('Editor'), `<span class="pvs dim">${(((P.outcome || {}).hand_fixes) || []).length ? tn(P.outcome.hand_fixes.length, '{n} version by hand', '{n} versions by hand') : t('change it yourself')}</span>`, 'editor') : ''}
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
// 0.5.4 (a friend's notes, 2026-10-25): an edit on a downloaded song gets a copy without it to post - the same sound is
// added in TikTok / Instagram, so the post is not muted (publish.post_copy)
function postBox(I) {
  const p = I.post;
  if (!p) return '';
  return `<div class="panel pbsec pbpost"><div class="row sp"><div class="row" style="gap:10px"><svg class="i"><use href="#i-music"/></svg><div><b>${t('To post on TikTok or Instagram')}</b>
      <div class="small muted">${t('This copy leaves out the song "{song}". Add the same sound in the app, from {at}, so your post is not muted.', {song: esc(p.song), at: esc(p.at)})}${p.sound === 'none' ? '' : ' ' + t('Your sound effects stay in it.')}</div></div></div>
    <span class="row" style="gap:6px">${p.link ? `<a class="btn sm" href="${esc(p.link)}" target="_blank" rel="noopener">${t('Open the song')}</a>` : ''}
      <button class="btn sm" data-postdir="${esc(p.rel)}"><svg class="i"><use href="#i-folder"/></svg>${t('Show in folder')}</button></span></div></div>`;
}
function wirePackaging(el, P) {
  $$('[data-postdir]', el).forEach(b => b.onclick = () => openPath(b.dataset.postdir, true));
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

// ---- The shot list (2026-11-03, docs\plans.md 0.6.1 step 3 - "a shot list with pictures before any render": the user
// swaps or approves before anything renders). A plan's shots as they will look (catalogue.shot_rows from the light cache
// - no render), each with frame + timecode, the clip catalogue's line and what to fix (`bad_k` = English keys + values,
// translated here - es.editor-1.json `_by_key`); *Swap* = another moment of the clips in its place (inside its usable
// part, the shot's length kept); nothing is saved until *Render with these shots* (none swapped = the job render, else
// the Editor's own save: the next version + its build). Without a catalogue: the shots, no swaps, *Catalogue the clips*
// (the job catalogue). GET / POST /api/project/<p>/shots, GET .../moment?m=, POST .../shots/render.
const slBad = b => t(b[0], {...(b[1] || {}), why: ((b[1] || {}).why || []).map(w => t(w)).join(', ')});
const slMeasured = m => [m.motion, m.light].filter(Boolean).map(w => t(w)).join(' · ');
const unrenderedPlan = P => { const pl = P.plans[P.plans.length - 1];          // the newest plan, when nothing shows it yet
  return pl && pl.file && !P.renders.some(r => planOfRender(P, r) === pl) ? pl : null; };
async function shotsModal(P, plan) {
  const enc = encodeURIComponent(P.name), swaps = {};
  let D = null, sel = null, busy = false;
  const flt = {fit: true, fresh: false, q: ''};
  const list = () => Object.entries(swaps).map(([shot, moment]) => ({shot, moment}));
  const load = () => list().length ? api(`/api/project/${enc}/shots`, {plan, swaps: list()})
    : api(`/api/project/${enc}/shots?plan=${encodeURIComponent(plan)}`);
  try { D = await load(); } catch (e) { toast(e.message, 'err'); return; }
  const vert = D.H > D.W, fps = D.fps, ver = (P.plans.find(p => p.file === plan) || {}).version || '';
  modal(`<div class="slm${vert ? ' vert' : ''}">
      <div class="slhead"><h2>${neIcon('i-shots', '--cyan')}${t('The shots of {version}', {version: esc(ver)})}</h2><span class="small muted" id="slsum"></span></div>
      <div class="slnote small" id="slnote" hidden></div>
      <div class="slbody"><div class="slgrid" id="slgrid"></div><aside class="slside" id="slside"></aside></div>
      <div class="slfoot"><span class="small muted" id="slcount"></span><span class="grow"></span>
        <button class="btn ghost" id="sled"><svg class="i"><use href="#i-edit"/></svg>${t('Open in the Editor')}</button>
        <button class="btn pri" id="slgo"><svg class="i"><use href="#i-play"/></svg><span></span></button></div></div>`, root => {
    const moOf = m => D.moments.find(x => x.m === m);
    const paint = () => {
      const bad = D.shots.filter(s => (s.bad_k || []).length).length, n = list().length;
      $('#slsum', root).innerHTML = [tn(D.shots.length, '{n} shot', '{n} shots'), D.frames ? lenWords(D.frames, fps) : '',
        bad ? `<span class="bad">${tn(bad, '{n} to fix', '{n} to fix')}</span>` : `<span class="good">${t('nothing to fix')}</span>`].filter(Boolean).join(' · ');
      const notes = [];
      if (!D.catalogue) notes.push(`<span>${t('Swaps need the clip catalogue: each clip looked at once, its moments and usable parts (about a minute, no Claude).')}</span>
        <button class="btn sm" id="slcat">${t('Catalogue the clips')}</button>`);
      else if (D.stale) notes.push(`<span>${t('A clip changed since the catalogue was made.')}</span><button class="btn sm" id="slcat">${t('Catalogue them again')}</button>`);
      D.graphics.forEach(g => notes.push(`<span class="bad">${g.guard ? t('A graphic cuts into the face ({share} %) from {at} - its words get clipped', {share: g.share, at: ftc(g.f, fps)})
        : t('A graphic covers the face ({share} %) from {at}', {share: g.share, at: ftc(g.f, fps)})}</span>`));
      $('#slnote', root).hidden = !notes.length; $('#slnote', root).innerHTML = notes.map(x => `<div>${x}</div>`).join('');
      const cb = $('#slcat', root);
      if (cb) cb.onclick = async () => {
        try { await api('/api/jobs', {kind: 'catalogue', args: {project: P.name}, queue: true});
          toast(t('Your clips are being catalogued - open the shots again when it is done'), 'ok'); closeModal(); }
        catch (e) { toast(e.message, 'err'); }
      };
      $('#slgrid', root).innerHTML = D.shots.map(s => { const bk = s.bad_k || [], say = s.say || {}, mo = moOf(s.moment);
        return `<div class="slcard${bk.length ? ' bad' : ''}${s.swapped ? ' sw' : ''}${sel === s.id ? ' on' : ''}" data-id="${esc(s.id)}">
          <div class="slpic"><img src="${s.img}" alt=""><b class="slno">${s.k}</b>${bk.length ? '<i class="slbadge">!</i>' : ''}${s.swapped ? `<i class="slswt">${t('swapped')}</i>` : ''}</div>
          <div class="sltc small" title="${esc(frange(s.s, s.e, fps).replace(/<[^>]+>/g, ''))}">${ftc(s.s, fps)} · <span class="nowrap">${dec((s.e - s.s + 1) / fps)}&nbsp;s</span></div>
          <div class="slwhat" title="${esc(s.name)}">${say.what ? esc(say.what) : `<span class="muted">${s.take ? t('your talking take') : mo ? esc(slMeasured(mo)) : t('not in the catalogue')}</span>`}</div>
          ${bk.length ? `<ul class="slbad small">${bk.map(b => `<li>${esc(slBad(b))}</li>`).join('')}</ul>` : ''}
          <div class="slact">${s.take ? `<span class="small muted">${t('your voice - it stays')}</span>` : !D.catalogue ? ''
            : s.swapped ? `<button class="btn sm ghost" data-undo="${esc(s.id)}">${t('Undo')}</button><button class="btn sm" data-swap="${esc(s.id)}"><svg class="i"><use href="#i-swap"/></svg>${t('Another')}</button>`
            : `<button class="btn sm${bk.length ? ' pri' : ''}" data-swap="${esc(s.id)}"><svg class="i"><use href="#i-swap"/></svg>${t('Swap')}</button>`}</div></div>`; }).join('');
      $$('[data-swap]', root).forEach(b => b.onclick = () => { sel = b.dataset.swap; paint(); });
      $$('[data-undo]', root).forEach(b => b.onclick = () => { delete swaps[b.dataset.undo]; redo(); });
      $('#slcount', root).textContent = n ? tn(n, '{n} shot swapped', '{n} shots swapped') : t('Nothing swapped yet');
      $('#sled', root).hidden = n > 0;                      // (the swaps live here until the render)
      $('#slgo span', root).textContent = n ? t('Render with these shots') : t('Looks good - render it');
      $('#slgo', root).disabled = busy;
      side();
    };
    const side = () => {
      const box = $('#slside', root), s = sel && D.shots.find(x => x.id === sel);
      if (!s) { box.innerHTML = `<div class="slempty">${neIcon('i-swap', '--cyan')}<b>${t('Swap a shot')}</b>
          <span class="small muted">${D.catalogue ? t('Press Swap on a shot: the other moments of your clips that fit it show here.') : t('Catalogue the clips first (above).')}</span></div>`; return; }
      const used = {};
      D.shots.forEach(x => { if (x.moment) (used[x.moment] = used[x.moment] || []).push(x.k); });
      const near = new Set([D.shots[s.k - 2], D.shots[s.k]].filter(Boolean).map(x => (moOf(x.moment) || {}).group).filter(Boolean));
      const q = flt.q.trim().toLowerCase();
      const ms = D.moments.filter(m => m.m !== s.moment && (!flt.fit || m.usable >= s.need) && (!flt.fresh || !used[m.m])
          && (!q || [m.name, ...(m.say ? [m.say.what, m.say.where, ...(m.say.tags || [])] : [])].join(' ').toLowerCase().includes(q)))
        .map((m, i) => ({m, i, alike: near.has(m.group), u: used[m.m]}))
        .sort((a, b) => (a.alike - b.alike) || (!!a.u - !!b.u) || (!a.m.say - !b.m.say) || (a.i - b.i));
      box.innerHTML = `<div class="slsh"><b>${t('Shot {n}: swap it for', {n: s.k})}</b><span class="small muted">${dec(s.need / fps)} s ${t('of a clip')}</span>
          <button class="btn sm ghost" id="slclose" title="${ta('Close')}">✕</button></div>
        <div class="slflt"><button class="nech${flt.fit ? ' on' : ''}" data-f="fit" title="${ta('a usable part at least as long as the shot')}">${t('Long enough')}</button>
          <button class="nech${flt.fresh ? ' on' : ''}" data-f="fresh">${t('Not used yet')}</button>
          <input type="search" id="slq" placeholder="${ta('Find: sky, street, a clip…')}" value="${esc(flt.q)}"></div>
        <div class="small muted">${tn(ms.length, '{n} moment', '{n} moments')}</div>
        <div class="slmos">${ms.slice(0, 160).map(({m, alike, u}) => `<button class="slmo${alike ? ' alike' : ''}" data-m="${esc(m.m)}" title="${esc(m.name)} · ${esc(frange(m.a, m.b, m.fps).replace(/<[^>]+>/g, ''))}">
            <img loading="lazy" src="/api/project/${enc}/moment?m=${encodeURIComponent(m.m)}" alt="">
            <span>${m.say ? esc(m.say.what) : `<span class="muted">${esc(slMeasured(m))}</span>`}</span>
            <small>${dec(m.usable / m.fps)} s${u ? ` · ${t('in shot {k}', {k: u.join(', ')})}` : ''}${alike ? ` · <b class="amber">${t('looks like its neighbour')}</b>` : ''}</small></button>`).join('')}
          ${ms.length > 160 ? `<div class="small muted">${t('{n} more - find them with a word', {n: ms.length - 160})}</div>` : ''}
          ${!ms.length ? `<div class="small muted">${flt.fit ? t('None long enough - untick Long enough to see shorter ones (the shot then runs past them).') : t('Nothing found')}</div>` : ''}</div>`;
      $('#slclose', box).onclick = () => { sel = null; paint(); };
      $$('[data-f]', box).forEach(b => b.onclick = () => { flt[b.dataset.f] = !flt[b.dataset.f]; side(); });
      const qi = $('#slq', box);
      qi.oninput = debounce(() => { flt.q = qi.value; side(); const n2 = $('#slq', root); n2.focus(); n2.setSelectionRange(n2.value.length, n2.value.length); }, 250);
      $$('[data-m]', box).forEach(b => b.onclick = () => { swaps[s.id] = b.dataset.m; redo(); });
    };
    const redo = async () => {
      if (busy) return;
      busy = true; $('#slgo', root).disabled = true;
      try { D = await load(); }
      catch (e) { toast(e.message, 'err'); if (sel && swaps[sel]) delete swaps[sel]; }
      busy = false; paint();
    };
    $('#sled', root).onclick = () => { closeModal(); location.hash = `#/project/${enc}/editor`; };
    $('#slgo', root).onclick = async () => {
      if (busy) return;
      busy = true; $('#slgo', root).disabled = true;
      try { await api(`/api/project/${enc}/shots/render`, {plan, swaps: list()});
        toast(list().length ? t('Your swaps are saved as the next version - it plays here when it is rendered') : t('Rendering - it plays here when it is ready'), 'ok');
        closeModal(); route(true); }
      catch (e) { toast(e.message, 'err'); busy = false; $('#slgo', root).disabled = false; }
    };
    paint();
  }, 'wide slmodal');
}

// ---- Versions: every edit version (how each was made) and its renders, the side-by-sides with the reference
