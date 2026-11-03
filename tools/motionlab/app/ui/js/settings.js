/* MotionLab app - js/settings.js: Settings, Shared knowledge's page parts, the category / tags editor.
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
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
