/* MotionLab app - js/prompts.js: Film it, the prompt library's pop-ups, Title & thumbnail.
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
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
// 0.6.1 (vertical framing, step 7): how to film so both shapes work - a horizontal picture, you in the middle from the
// chest up, your eyes on its upper third, the vertical crop MotionLab takes from it; the rest in five short rows
const FI_FRAME = `<svg class="fifrsvg" viewBox="0 0 160 92" aria-hidden="true"><rect class="fr" x="2" y="2" width="156" height="88" rx="4"/>
  <path class="g" d="M2 60.7 H158"/><path class="eye" d="M2 31.3 H158"/><circle class="p" cx="80" cy="35" r="11"/>
  <path class="p" d="M50 90 Q52 56 80 51 Q108 56 110 90 Z"/><rect class="v" x="55.25" y="2" width="49.5" height="88" rx="2"/>
  <text x="152" y="13" text-anchor="end">16:9</text><text x="80" y="85" text-anchor="middle">9:16</text></svg>`;
const FI_CHECKS = () => [['i-target', t('The lens at eye level - look into it'), t('Not from below: a lens under your chin looks up at you.')],
  ['i-pin', t('Your eyes on the upper third'), t('The top line of a 3 x 3 grid - most phones and cameras can show one.')],
  ['i-users', t('From mid-chest up, about 1 m away'), t('About an arm and a half: your face close, your hands still in the picture.')],
  ['i-sparkle', t('Face a window'), t('Soft daylight in front of you - never a window behind you.')],
  ['i-film', t('Only vertical? Film vertical. Both shapes? Horizontal, 4K, you in the middle'),
    t('MotionLab frames the vertical video from the horizontal one - with you in the middle and in 4K it stays sharp.')]];

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
        <h4>${t('Before you film')}</h4>
        <div class="fiframe">${FI_FRAME}<ul class="fichecks">${FI_CHECKS().map(([ic, l, tip]) => `<li title="${esc(tip)}"><svg class="i"><use href="#${ic}"/></svg><span>${l}</span></li>`).join('')}</ul></div>
        <h4>${t('While you film')}</h4><ul class="filist small">
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
