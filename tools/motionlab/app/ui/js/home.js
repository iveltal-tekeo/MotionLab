/* MotionLab app - js/home.js: Home (the ways in), Add videos, the workflow of a reference, Delete (the Recycle Bin).
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
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
// GET /api/estimate without waiting for it (2026-11-03, the user: "the add button in the analyze section ... is not
// working"): it reads every Claude Code log on this PC - 6 s on a freshly started server - and the dialogs that waited
// for it opened that much later, looking broken. They open at once and `then(est)` draws the line when it comes ({} =
// none); a dialog closed by then is left alone (each checks its own line is still there).
function estLater(then) {
  api('/api/estimate').catch(() => ({})).then(e => then(e || {}));
}
// *Browse…* in the Analyser's add dialogs - Analyze videos, Take notes, SPARK (2026-11-03, the user: "i just want to be
// able to analyze local videos"): Windows' own Open dialog, opened by the server (POST /api/pick/videos {for}) - a page
// never learns a file's place; each video picked goes to add(path), then done(); the button busy meanwhile
async function pickVideos(btn, purpose, add, done) {
  if (!btn || btn.disabled) return;
  const was = btn.innerHTML;
  btn.disabled = true; btn.textContent = t('Pick them in the window that opened…');
  try {
    const r = await api('/api/pick/videos', {for: purpose});
    if (!btn.isConnected) return;                            // (the dialog was closed meanwhile)
    r.paths.forEach(add);
    if (r.skipped) toast(tn(r.skipped, '{n} file is not a video - left out', '{n} files are not videos - left out'));
    done();
  } catch (e) { toast(e.message, 'err'); }
  finally { if (btn.isConnected) { btn.disabled = false; btn.innerHTML = was; } }
}
// the Browse… button of those dialogs (its id: <prefix>browse), left of the path box
const browseBtn = id => `<button class="btn sm pri" id="${id}" title="${ta('Pick videos anywhere on this PC - they stay where they are')}"><svg class="i"><use href="#i-folder"/></svg>${t('Browse…')}</button>`;
async function addVideosModal(pre = {}) {
  const [cands, ST] = await Promise.all([api('/api/candidates'), api('/api/settings')]);
  let EST = null;                                   // Claude's usual time: drawn when it comes (estLater)
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
    <div class="row" style="margin-top:6px">${browseBtn('avbrowse')}
      <input type="text" id="avpath" placeholder="${ta('…or the full path of a video elsewhere, e.g. C:\\Videos\\clip.mp4')}" style="flex:1"><button class="btn sm" id="avadd" title="${ta('Adds the path in the box - with the box empty, it opens Browse')}">${t('Add')}</button></div>
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
      $('#avest', el).innerHTML = EST ? ' ' + estWords(EST.review, n) + '.' : '';
    };
    estLater(e => { EST = e; if ($('#avest', el)) upd(); });
    $('#avl', el).oninput = upd;
    $('#avfiles', el).onchange = upd;
    $$('input[name=avf]', el).forEach(r => r.onchange = () => { focus = r.value; $$('.avmode', el).forEach(x => x.classList.toggle('on', $('input', x).checked)); upd(); });
    const addPath = v => {                          // a video into the list, ticked (one already there is ticked again)
      const box = $('#avfiles', el), had = $$('input', box).find(x => x.value === v);
      if (had) { had.checked = true; return; }
      const none = box.querySelector(':scope > .dim');        // ("No videos in refs yet" - not a row's size, which
      if (none) none.remove();                               // is .dim too: the old test emptied the whole list)
      box.insertAdjacentHTML('afterbegin', fileRow({path: v, name: v, size: null, analysed: false}));
      box.querySelector('input').checked = true;
    };
    // *Browse…* (2026-11-03, the user: "or the full path of a video elsewhere ... i still click Add there and it does
    // not open"): the videos picked join the list ticked, the files stay where they are (pickVideos)
    const browse = () => pickVideos($('#avbrowse', el), 'analyse', addPath, upd);
    $('#avbrowse', el).onclick = browse;
    $('#avadd', el).onclick = () => {
      const v = $('#avpath', el).value.trim().replace(/^"|"$/g, '');
      if (!v) return browse();                                 // (an empty box: the picker)
      addPath(v); $('#avpath', el).value = ''; upd();
    };
    $('#avgo', el).onclick = async () => {
      const b = $('#avgo', el); b.disabled = true;
      try {
        const r = await api('/api/analyze/batch', {links: links(), files: files(), focus, category: $('#avcat', el).value,
          tags: $('#avtags', el).value, claude: ($('input[name=avc]:checked', el) || {}).value === '1', redetect: $('#avre', el).checked});
        closeModal(); ping();
        toast(tn(r.jobs.length, 'Analysing {n} video - follow them in the Analyser', 'Analysing {n} videos - follow them in the Analyser'), 'ok');
        if (location.hash !== '#/analyze/videos') location.hash = '#/analyze/videos'; else route();
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
