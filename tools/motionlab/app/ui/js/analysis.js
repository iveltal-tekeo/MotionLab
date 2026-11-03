/* MotionLab app - js/analysis.js: SPARK (#/spark) and one analysis (#/ref).
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ---- SPARK (the Analyser's second way, 2026-10-30; the plan: docs\plans.md 0.6.5 *SPARK - why a video worked*, the
// user: "start working on the SPARK content creation section on the analyser"). analysis\spark\<name>\ -
// motionlab\spark.py; Claude = /spark. One fixed rubric for every video, each point Measured (a number of the lab's
// table) / Claude's judgement (a quote that plays its moment, a frame it shows) / Unknown, the numbers against the
// creator's usual (a lookup the user starts, kept on this PC), what the video cannot explain, take-aways
const SP_RUBRIC = {idea: t('The idea and who it is for'), packaging: t('The packaging promise'), hook: t('The hook (0-3 s)'),
  payoff: t('The promise kept'), loops: t('Open loops and re-hooks'), pacing: t('Structure and pacing'), emotion: t('Emotion'),
  send: t('Why people would send it'), comment: t('Why people would comment'), craft: t('Craft'), ending: t('The ending'), context: t('Context')};
const SP_HOOK = {question: t('A question'), bold_claim: t('A bold or contrarian claim'), result_first: t('The result first'),
  curiosity: t('A curiosity gap'), story: t('A story starts'), problem: t('A problem or a pain'), promise: t('A promise of how'),
  list: t('A list or a number'), visual: t('A picture or a mood first'), callout: t('It calls out the viewer'), trend: t('A trend or a sound'),
  other: t('Other|hook')};
const SP_LABEL = {measured: [t('Measured'), t('Rests on a number MotionLab measured or looked up')],
  judgement: [t("Claude's judgement"), t("Claude's reading of the video's own words and pictures")], unknown: [t('Unknown'), t('The video cannot tell')]};
const SP_RESULT = {outlier: t('An outlier'), above: t('Above its usual'), usual: t('About its usual'), below: t('Below its usual'), unknown: t('Usual unknown')};
const SP_NUM = {views: t('views'), likes: t('likes'), comments: t('comments'), shares: t('shares'), saves: t('saves'), followers: t('followers'),
  likes_per_1k: t('likes per 1,000 views'), comments_per_1k: t('comments per 1,000 views'), shares_per_1k: t('shares per 1,000 views'),
  saves_per_1k: t('saves per 1,000 views'), views_per_follower: t('views per follower'), usual_views: t("the creator's usual views"),
  outlier: t("against the creator's usual"), days_online: t('days online'), views_per_day: t('views per day'), duration_s: t('length'),
  shots: t('shots'), cuts_per_min: t('cuts per minute'), median_shot_s: t('median shot'), first_cut_s: t('first cut'),
  hook_cuts: t('cuts in the first 3 s'), hook_words: t('words in the first 3 s'), hook_text: t('text on screen in the first 3 s'),
  words_per_min: t('words per minute'), talk_pct: t('talked'), text_pct: t('text on screen (rough)'),
  creator_cuts_per_min: t("the creator's usual cuts per minute"), thumb_faces: t('faces on the thumbnail'),
  thumb_face_pct: t("the face's height on the thumbnail"), thumb_text_pct: t("the letters' height on the thumbnail"),
  thumb_brightness: t('thumbnail brightness'), thumb_saturation: t('thumbnail saturation'),
  ret_3s: t('still watching at 3 s'), ret_10s: t('still watching at 10 s'), ret_end: t('still watching at the end'),
  ret_drop: t('left in the steepest 3 seconds'), ret_usual_3s: t('your usual at 3 s'), ret_usual_10s: t('your usual at 10 s')};
const SP_UNIT = {views_per_follower: 'x', outlier: 'x', duration_s: 's', median_shot_s: 's', first_cut_s: 's', talk_pct: '%', text_pct: '%',
  hook_text: 'yes/no', thumb_face_pct: '%', thumb_text_pct: '%', thumb_saturation: '%',
  ret_3s: '%', ret_10s: '%', ret_end: '%', ret_drop: '%', ret_usual_3s: '%', ret_usual_10s: '%'};
// why the creator's usual is unknown (numbers.json usual_why as a code - motionlab\spark.py WHY_CODES)
const SP_WHY = {instagram: t("Instagram shows other videos' numbers only to a signed-in account - unknown"),
  no_channel: t('The video names no channel'), platform: t("The creator's list is not read on this platform"),
  failed: t("The creator's list could not be read - try again later"), empty: t("The creator's list gave no view counts"),
  not_in_list: t("It is not among the creator's newest videos"), too_few: t('Too few comparable videos (at least 5)'),
  no_link: t('No link known - add the video with its link to look its numbers up')};
const spVal = (v, unit) => v == null ? '–' : unit === 'yes/no' ? (v ? '✓' : '✗')
  : numLoc(typeof v === 'number' && !Number.isInteger(v) ? Math.round(v * 100) / 100 : v) + (unit === 'x' ? '×' : unit === '%' ? ' %' : unit === 's' ? ' s' : '');
const spNum = (k, v) => `<span class="spnc" title="${esc(SP_NUM[k] || k)}"><b>${spVal(v, SP_UNIT[k])}</b> ${esc(SP_NUM[k] || k)}</span>`;
const spResChip = (r, o) => `<span class="spres ${r || 'unknown'}" title="${ta("views against the creator's usual (the median of their videos around it)")}">${SP_RESULT[r || 'unknown']}${o != null ? ` · ${spVal(o, 'x')}` : ''}</span>`;
function sparkCard(s) {
  const when = strTime(s.created), P = s.spark;
  const st = s.status === 'ready' ? `<span class="small fnl grow ok">${t('✓ Ready')}</span>`
    : s.status === 'claude' ? `<span class="small fnl grow">${t('Waiting for Claude')}</span>${claudeBtn('/spark ' + s.name, t('Write it'), 'spark', s.name)}`
    : `<span class="small fnl grow bad">${t('No words or frames found')}</span>`;
  return `<div class="card pcard ncard spcardl"><a class="clink" href="#/spark/${encodeURIComponent(s.name)}">
    <div class="ppic">${s.thumb ? `<img src="${fileUrl(s.thumb)}" loading="lazy" alt="">` : mascot('spark', {size: 72, animated: false})}
      <span class="pbadges">${s.status === 'claude' ? `<span class="pbadge todo">${t('not written yet')}</span>` : ''}</span>
      ${when ? `<span class="pwhen" title="${esc(s.created || '')}">${esc(whenWords(when))}</span>` : ''}</div>
    <div class="cb"><span class="ct"${s.title && s.title !== s.label ? ` title="${esc(s.title)}"` : ''}>${esc(P && P.title || s.label)}</span><div class="small">${[lenWords(s.frames, s.fps), esc(s.uploader || ''), esc(s.platform || '')].filter(Boolean).join(' · ')}</div></div></a>
    ${P && P.verdict ? `<div class="small muted ntl2">${esc(P.verdict)}</div>` : ''}
    <div class="pfacts">${spResChip(s.result, s.outlier)}${s.views != null ? `<span class="small dim">${tn(s.views, '{n} view', '{n} views')}</span>` : ''}</div>
    <div class="cact">${st}</div>
    <span class="pdel">${delBtn('spark', s.name)}</span></div>`;
}
// SPARK from another page (an analysis, a video's notes): its page when it has one, else a button that opens the dialog
const sparkLink = (sp, video) => sp ? `<a class="btn" href="#/spark/${encodeURIComponent(sp.name)}" title="${ta("Why this video worked: its hook, its story and its numbers against the creator's usual")}"><svg class="i"><use href="#i-sparkle"/></svg>${sp.status === 'ready' ? t('Why it worked') : t('SPARK - waiting for Claude')}</a>`
  : video ? `<button class="btn" data-spark="${esc(video)}" title="${ta("Why this video worked: its hook, its story and its numbers against the creator's usual")}"><svg class="i"><use href="#i-sparkle"/></svg>${t('Analyze with SPARK')}</button>` : '';
const sparkWire = main => $$('[data-spark]', main).forEach(b => b.onclick = () => addSparkModal([b.dataset.spark]));
// Analyze with SPARK: links (downloaded up to 1080p - its frames are read) and / or videos already here, what the
// user wants to know, then by default ONE Claude window writes them all when the last one is ready
async function addSparkModal(pre = [], links = []) {         // links: filled in (Content agency's own videos)
  const [cands, ST] = await Promise.all([api('/api/candidates'), api('/api/settings')]);
  const cl = ST.tools.find(x => x.name === 'claude') || {}, yt = ST.tools.find(x => x.name === 'yt-dlp') || {};
  const fileRow = (c, on) => `<label class="avfile"><input type="checkbox" value="${esc(c.path)}"${on ? ' checked' : ''}>
    <span class="grow">${esc(c.name)}</span><span class="small dim">${c.size != null ? bytes(c.size) : ''}</span></label>`;
  const preRows = pre.filter(p => !cands.some(c => c.path === p)).map(p => fileRow({path: p, name: p, size: null}, true)).join('');
  modal(`<h2>${mascot('spark', {size: 40, animated: false})} ${t('Why did it work? (SPARK)')}</h2>
    <div class="avstep"><b>1</b><span>${t('Which videos?')}</span><span class="small muted">${t('up to {n} at a time - links are downloaded up to 1080p', {n: AV_MAX})}</span></div>
    <textarea id="spl" rows="3" placeholder="${ta('Paste links, one per line - YouTube, TikTok, Instagram, Vimeo…')}">${esc(links.join('\n'))}</textarea>
    ${yt.found ? '' : `<div class="small amber">${t('Links need the downloader (yt-dlp): <a href="#/settings" onclick="closeModal()">Settings → Programs</a>. Files work without it.')}</div>`}
    <div class="small muted" style="margin:8px 0 4px">${t('or pick videos you already have (in the refs folder):')}</div>
    <div class="avfiles" id="spfiles">${preRows}${cands.map(c => fileRow(c, pre.includes(c.path))).join('') || (preRows ? '' : `<div class="small dim">${t('No videos in refs yet - paste a link, or the path of a video below.')}</div>`)}</div>
    <div class="row" style="margin-top:6px"><input type="text" id="sppath" placeholder="${ta('…or the full path of a video elsewhere, e.g. C:\\Videos\\clip.mp4')}" style="flex:1"><button class="btn sm" id="spaddp">${t('Add')}</button></div>
    <div class="avstep opt"><b>2</b><span>${t('What do you want to know?')}</span>${optTag()}</div>
    <input type="text" id="spask" maxlength="1000" style="width:100%" placeholder="${ta('e.g. why it got so many views, what I can copy for my channel, why the comments exploded…')}">
    <div class="avstep"><b>3</b><span>${t("Claude's write-up")}</span></div>
    <label class="chk avclaude"><input type="radio" name="spc" value="1" ${cl.found ? 'checked' : 'disabled'}><span>${t('<b>Claude writes it when the video is ready</b> (recommended) - one Claude Code window for all of them, nothing for you to correct.')}${cl.found ? '' : ` <span class="bad">${t('Claude Code was not found - Settings.')}</span>`}</span></label>
    <label class="chk avclaude"><input type="radio" name="spc" value="0" ${cl.found ? '' : 'checked'}><span>${t("<b>Only measure it and look up the numbers</b> - ask Claude later from each video's page.")}</span></label>
    <div class="small muted" style="margin-top:8px">${t("MotionLab looks up each video's numbers and its creator's other videos once, when you start - they stay on this PC.")}</div>
    <details class="fold" style="margin-top:10px"><summary>${t('More options')}</summary><div class="in"><div class="form">
      <label for="sptags">${t('Tags')} ${optTag()}</label><input type="text" id="sptags" placeholder="${ta('e.g. music, hooks, my niche')}"></div></div></details>
    <div class="row" style="margin-top:14px"><button class="btn pri big" id="spgo" disabled><svg class="i"><use href="#i-sparkle"/></svg>${t('Analyze with SPARK')}</button>
      <span id="spsum" class="small muted"></span></div>`, el => {
    const links = () => $('#spl', el).value.split(/\s+/).map(x => x.trim()).filter(Boolean);
    const files = () => $$('#spfiles input:checked', el).map(x => x.value);
    const upd = () => {
      const L = links(), F = files(), n = L.length + F.length, bad = L.filter(u => !/^https?:\/\/\S+$/i.test(u));
      $('#spgo', el).disabled = !n || n > AV_MAX || bad.length > 0 || (L.length && !yt.found);
      $('#spsum', el).innerHTML = bad.length ? `<span class="bad">${t('not a link: {link}', {link: esc(bad[0])})}</span>` : n > AV_MAX ? `<span class="bad">${t('at most {n} at a time', {n: AV_MAX})}</span>`
        : n ? [L.length ? tn(L.length, '{n} link (downloaded first)', '{n} links (downloaded first)') : '', F.length ? plural(F.length, 'file') : ''].filter(Boolean).join(' + ') : t('Paste a link or pick a video.');
    };
    $('#spl', el).oninput = upd;
    $('#spfiles', el).onchange = upd;
    $('#spaddp', el).onclick = () => {
      const v = $('#sppath', el).value.trim().replace(/^"|"$/g, '');
      if (!v) return;
      const box = $('#spfiles', el);
      const empty = box.querySelector('div.small.dim'); if (empty) empty.remove();
      box.insertAdjacentHTML('afterbegin', fileRow({path: v, name: v, size: null}, true));
      $('#sppath', el).value = ''; upd();
    };
    $('#spgo', el).onclick = async () => {
      const b = $('#spgo', el); b.disabled = true;
      try {
        const r = await api('/api/spark/batch', {links: links(), files: files(), ask: $('#spask', el).value, tags: $('#sptags', el).value,
          claude: ($('input[name=spc]:checked', el) || {}).value === '1'});
        closeModal(); ping();
        toast(tn(r.jobs.length, 'SPARK is reading {n} video - follow it in the Analyser', 'SPARK is reading {n} videos - follow them in the Analyser'), 'ok');
        if (location.hash !== '#/analyze/spark') location.hash = '#/analyze/spark'; else route();
      } catch (e) { toast(e.message, 'err'); b.disabled = false; }
    };
    if (!pre.length && !links.length) $('#spl', el).focus();
    upd();
  }, 'wide');
}
// one video's SPARK (#/spark/<name>): on the left the verdict and its result against the creator's usual, the numbers
// (measured by MotionLab, no Claude), the 12 points as cards - each labelled, its evidence chips play the moment - what
// the video cannot explain and what to take for your videos; on the right the video, its words, the first and last 3 s
// and a frame per shot. Every time = frame + timecode
async function pageSpark(main, name, atF) {
  let R = await api('/api/spark/' + encodeURIComponent(name));
  let timer = 0, numWait = 0;
  onCleanup(() => { clearTimeout(timer); clearTimeout(numWait); });
  const draw = () => {
    const P = R.report, fps = R.fps, NB = R.numbers || {}, U = R.usual;
    const fmt = R.format || {};
    const head = `<div class="head"><div><div class="crumb"><a href="#/analyze">${t('Analyser')}</a> / <a href="#/analyze/spark">SPARK</a> / ${t('why it worked')}</div>
        <div class="mtitle mhost">${mascot('spark', {size: 46})}<h1${R.title && R.title !== R.label ? ` title="${esc(R.title)}"` : ''}>${esc(P && P.title || R.label)}</h1></div>
        <div class="sub">${[R.url ? `<a href="${esc(R.url)}" target="_blank" rel="noopener">${esc(R.platform || t('source'))}</a>` : '', esc(R.uploader || ''), lenWords(R.frames, fps),
          `${numStr(fps)} fps`, (R.tags || []).map(g => `<span class="tag dim">${esc(g)}</span>`).join(' ')].filter(Boolean).join(' · ')}</div></div>
      <div class="row">${P ? `<button class="btn" id="spdl"><svg class="i"><use href="#i-download"/></svg>${t('Download (.md)')}</button>` : ''}
        ${R.url ? `<button class="btn" id="spnum" title="${ta('Views keep changing: one more lookup of this video and its creator\'s list')}"><svg class="i"><use href="#i-update"/></svg>${t('Look the numbers up again')}</button>` : ''}
        ${R.ways && R.ways.flux ? `<a class="btn" href="#/ref/${encodeURIComponent(R.ways.flux)}" title="${ta('Its effects, analysed by FLUX')}"><svg class="i"><use href="#i-film"/></svg>FLUX</a>` : ''}
        ${R.ways && R.ways.notes ? `<a class="btn" href="#/note/${encodeURIComponent(R.ways.notes)}" title="${ta('Its notes, written by INDEX')}"><svg class="i"><use href="#i-pen"/></svg>INDEX</a>` : ''}
        <button class="btn" data-open="${esc(R.folder)}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button>
        ${delBtn('spark', R.name, '#/analyze/spark', ' ' + t('Delete'))}</div></div>`;
    const ask = R.ask ? `<div class="small muted nask">${t('You asked: {what}', {what: esc(R.ask)})}</div>` : '';
    // the numbers - MotionLab's, before and without Claude
    const big = Math.max(NB.views || 0, NB.usual_views || 0) || 1;
    const bar = (lab, v, cls) => `<div class="spbar ${cls}"><span class="spbl">${lab}</span><span class="spbt"><i style="width:${Math.max(1, v / big * 100).toFixed(1)}%"></i></span><b>${numLoc(v)}</b></div>`;
    const usualWhy = R.usual_code ? (SP_WHY[R.usual_code] || '') : '';
    const usualBox = U ? `<details class="fold spusual"><summary>${t('How the usual was found')}</summary><div class="in small">
        <p>${U.mode === 'dates' ? t('The median views of the {n} videos the creator posted nearest its upload date.', {n: U.n}) : t('The median views of the {n} videos the creator posted just before and after it.', {n: U.n})}</p>
        ${U.left_out ? `<p class="dim">${tn(U.left_out, '{n} video left out: posted on the other side of 24 August 2026, when YouTube began counting a view the moment a video starts to play.', '{n} videos left out: posted on the other side of 24 August 2026, when YouTube began counting a view the moment a video starts to play.')}</p>` : ''}
        ${U.near_rule ? `<p class="dim">${t("Posted close to YouTube's new view count (24 August 2026) and the list gives no dates - some videos around it may count views the other way.")}</p>` : ''}
        ${U.rounded ? `<p class="dim">${t("YouTube's list rounds views (149K) and gives only approximate months.")}</p>` : ''}
        <table class="sptab">${(U.videos || []).map(x => `<tr><td>${esc(x.title || x.id)}</td><td class="num">${numLoc(x.views)}</td><td class="dim">${esc(x.when || '')}</td></tr>`).join('')}</table></div></details>` : '';
    const nums = NB.views != null || NB.shots != null ? `<div class="panel spnums"><div class="sph"><h2>${t('Its numbers')}</h2><span class="mlchip" title="${ta("the app's own numbers, measured and looked up - Claude was not involved")}">${t('MotionLab · no Claude')}</span>
        ${R.fetched ? `<span class="small dim">${t('looked up {when}', {when: esc(whenStr(R.fetched) || R.fetched)})}</span>` : ''}</div>
      ${NB.views != null ? `<div class="spbars">${bar(t('This video'), NB.views, 'me')}${NB.usual_views != null ? bar(t("The creator's usual"), NB.usual_views, 'u') : ''}</div>
        ${NB.usual_views == null && usualWhy ? `<div class="small dim">${t("The creator's usual: {why}", {why: esc(usualWhy)})}</div>` : ''}` : ''}
      <div class="spncs">${(NB.views == null ? ['likes', 'comments', 'shares', 'saves', 'followers'] : ['likes_per_1k', 'comments_per_1k', 'shares_per_1k', 'saves_per_1k', 'views_per_follower', 'views_per_day']).filter(k => NB[k] != null).map(k => spNum(k, NB[k])).join('')}</div>
      <div class="spncs dimmed">${['shots', 'cuts_per_min', 'median_shot_s', 'hook_cuts', 'hook_words', 'hook_text', 'words_per_min', 'talk_pct'].filter(k => NB[k] != null).map(k => spNum(k, NB[k])).join('')}</div>
      ${usualBox}</div>` : '';
    // 2026-11-02: your own video - where people left (your retention graph, traced by MotionLab), the steepest drops at
    // their frames with the words said there; a click plays the moment
    const RT = R.retention;
    const retBox = RT ? `<div class="panel sprt" id="sprt"><div class="sph"><h2><svg class="i"><use href="#i-retention"/></svg>${t('Where people left')}</h2>
          <span class="mlchip" title="${ta('read by MotionLab from your screenshot of the graph - Claude was not involved')}">${t('MotionLab · no Claude')}</span>
          <span class="small dim">${t('your retention graph, read {when}', {when: esc(whenStr(RT.traced) || RT.traced || '')})}</span><span class="grow"></span>
          <button class="btn sm ghost" id="sprtch">${t('Change')}</button></div>
        ${RT.mismatch ? `<div class="small amber">${t('The graph is {a} s long and this video {b} s - another cut, or the end line is off. Its numbers are not used until they match.', {a: numLoc(RT.end_s), b: numLoc(Math.round((RT.duration_s || 0) * 10) / 10)})}</div>` : ''}
        <div class="rtwrap" id="rtwrap" title="${ta('Click to play that moment')}">${retSvg(RT.points || [], RT.end_s, {w: 600, h: 150, drops: RT.drops, play: true})}</div>
        <div class="spncs">${['ret_3s', 'ret_10s', 'ret_end', 'ret_usual_3s', 'ret_usual_10s'].filter(k => NB[k] != null).map(k => spNum(k, NB[k])).join('')}</div>
        ${(RT.drops || []).length ? `<div class="rtdrops">${RT.drops.map((d, i) => `<a href="#" class="rtdropr${i ? '' : ' first'}" data-f="${d.f}">
            <span class="ntc">${esc(d.at_label)} – ${esc(d.end_label)}</span><b>−${numLoc(Math.round(d.loss))} %</b>
            <span class="small">${d.words ? `“${esc(d.words)}”` : `<i class="dim">${t('nothing said')}</i>`}</span></a>`).join('')}</div>` : ''}
        <div class="small dim">${t('Red = the steepest drops: the share of those still watching who left within 3 seconds. A drop shows where people left, not why; seconds MotionLab could not read stay unknown.')}</div></div>`
      : R.own && R.post_key ? `<div class="panel sprt"><div class="sph"><h2><svg class="i"><use href="#i-retention"/></svg>${t('Where people left')}</h2></div>
          <div class="small muted">${t('This is your video: add a screenshot of its retention graph and SPARK lines the drops up with the words and the shots.')}</div>
          <div class="row" style="margin-top:8px"><button class="btn" id="sprtch">${t('Add your retention graph')}</button></div></div>` : '';
    let left;
    if (!P) {
      left = `<div class="panel nwait mhost">${mascot('spark', {size: 76})}<h2>${t('Claude has not written it yet')}</h2>
        <div class="small muted">${t('MotionLab has the words, the numbers and a frame of every shot - Claude explains them with one checklist for every video.')}</div>
        ${(R.issues || []).map(x => `<div class="small dim" style="margin-top:4px">${esc(x)}</div>`).join('')}
        <div class="row" style="margin-top:12px">${claudeBtn('/spark ' + R.name, t('Write it with Claude'), 'spark', R.name, 'cl')}</div></div>${ask}${nums}${retBox}`;
    } else {
      const evc = (e, key) => e.type === 'number' ? spNum(e.key, e.value)
        : `${nTime(e.at, fps, e.quote || '', e.replayed)}${e.type === 'shown' ? `<span class="small dim spsh">${t('(on screen)')}</span>` : ''}${key === 'payoff' && e.share != null ? `<span class="small dim spsh">${t('{n} % in', {n: e.share})}</span>` : ''}`;
      const card = p => `<div class="spcard ${p.label}" id="sp-${p.key}"><div class="spch"><span class="splab ${p.label}" title="${esc(SP_LABEL[p.label][1])}">${SP_LABEL[p.label][0]}</span>
          <h3>${SP_RUBRIC[p.key] || esc(p.key)}</h3>${p.key === 'hook' && P.hook_type ? `<span class="sphook">${SP_HOOK[P.hook_type] || esc(P.hook_type)}</span>` : ''}</div>
        <p>${esc(p.text)}</p>${(p.evidence || []).length ? `<div class="spev">${p.evidence.map(e => evc(e, p.key)).join('')}</div>` : ''}</div>`;
      const nk = l => P.rubric.filter(p => p.label === l).length;
      left = `<div class="spverd"><div class="sptop">${spResChip(P.result, NB.outlier)}<span class="sphook">${t('Hook')}: ${SP_HOOK[P.hook_type] || esc(P.hook_type || '')}</span></div>
          <p class="spv">${esc(P.verdict)}</p>
          <div class="small dim">${t('{m} measured · {j} Claude\'s judgement · {u} unknown', {m: nk('measured'), j: nk('judgement'), u: nk('unknown')})}</div></div>
        ${ask}${nums}${retBox}
        <h2 class="nh">${t('Why it worked')} <span class="ncount">${P.rubric.length}</span></h2>
        <div class="sprub">${P.rubric.map(card).join('')}</div>
        <div class="panel spnx"><h2>${t('Not explained')}</h2><p>${esc(P.not_explained)}</p>
          <div class="small dim">${t('What the video itself cannot account for - a hit is partly timing, luck and who shared it.')}</div></div>
        <h2 class="nh">${t('For your videos')} <span class="ncount">${P.takeaways.length}</span></h2>
        <ol class="sptake">${P.takeaways.map(x => `<li><span>${esc(x.text)}</span>${x.from ? ` <a href="#" class="small dim" data-go="sp-${x.from}">${SP_RUBRIC[x.from] || ''}</a>` : ''}</li>`).join('')}</ol>
        <div class="small dim nfoot">${t('Written by Claude · {when} · every point is tied to the video\'s words, a frame it shows or a number MotionLab measured', {when: esc(whenStr(P.made) || P.made || '')})}
          · ${claudeBtn('/spark ' + R.name, t('Write it again'), 'spark', R.name, 'sm ghost')}</div>`;
    }
    const player = R.video_rel ? `<video id="spvid" controls preload="metadata" src="${fileUrl(R.video_rel)}"></video>`
      : `<div class="nnovid">${R.thumb ? `<img src="${fileUrl(R.thumb)}" alt="">` : ''}<div class="small muted">${R.video_there ? t('This video sits outside the lab folder, so it plays in its own folder only.') : t('The video was deleted - its SPARK stays.')}</div></div>`;
    const strips = Object.entries(R.strips || {});
    main.innerHTML = `${head}<div class="ngrid"><div class="nnotes">${left}</div>
      <div class="nside">${player}
        <div class="ntabs"><button data-nt="ends" class="on">${t('First and last 3 s')}</button><button data-nt="words">${t('Transcript')}</button>${R.sheets.length ? `<button data-nt="shots">${t('Shots')}</button>` : ''}</div>
        <div data-np="ends">${strips.map(([k, s]) => `<div class="small dim">${k === 'hook' ? t('The first 3 s') : t('The last 3 s')}</div><img class="spstrip" src="${fileUrl(s)}" data-strip="${k}" loading="lazy" alt="">`).join('') || `<div class="small muted">${t('No pictures.')}</div>`}</div>
        <div data-np="words" hidden>${R.lines.length ? `<input type="search" id="spq" placeholder="${ta('Search the words…')}" style="width:100%">
            <div class="nlines" id="splines">${R.lines.map((l, i) => `<div class="nline" data-i="${i}" data-f="${l.start}"><span class="ntc">f${l.start} (${tc(l.start, fps)})</span> ${esc(l.text)}</div>`).join('')}</div>`
          : `<div class="small muted">${t('No words in this video.')}</div>`}</div>
        <div data-np="shots" hidden><div class="nsheets">${R.sheets.map((s, i) => `<img src="${fileUrl(s)}" data-i="${i}" loading="lazy" alt="">`).join('')}</div></div>
      </div></div>`;
    const vid = $('#spvid', main);
    const seek = f => { if (!vid) return; vid.currentTime = (+f + 0.5) / fps; vid.play().catch(() => {}); };
    $('.ngrid', main).addEventListener('click', e => {
      const g = e.target.closest('[data-go]');
      if (g) { e.preventDefault(); const x = document.getElementById(g.dataset.go); if (x) { x.scrollIntoView({behavior: 'smooth', block: 'center'}); x.classList.add('flash'); setTimeout(() => x.classList.remove('flash'), 1200); } return; }
      const a = e.target.closest('.ntime, .nline, .rtdropr');
      if (!a) return;
      e.preventDefault(); seek(a.dataset.f);
    });
    if (vid && atF != null) vid.addEventListener('loadedmetadata', () => seek(atF), {once: true});
    // where people left: a click on the curve plays that second; the playhead follows the video
    const rsvg = $('#rtwrap svg', main);
    if (rsvg) {
      const end = +rsvg.dataset.end, pad = +rsvg.dataset.pad, w = +rsvg.dataset.w, line = $('.rtplay', rsvg);
      rsvg.onclick = e => { const r = rsvg.getBoundingClientRect(), s = clamp(((e.clientX - r.left) / r.width * w - pad) / (w - 2 * pad) * end, 0, end);
        seek(Math.min(R.frames - 1, Math.round(s * fps))); };
      if (vid && line) vid.addEventListener('timeupdate', () => { const x = (pad + (w - 2 * pad) * Math.min(1, vid.currentTime / end)).toFixed(1);
        line.setAttribute('x1', x); line.setAttribute('x2', x); });
    }
    const rch = $('#sprtch', main);
    if (rch) rch.onclick = () => retentionModal({key: R.post_key, url: R.url, title: R.title || R.label, duration: R.duration_s,
      platform: String(R.post_key || '').split(':')[0], entry: RT ? {image: RT.image, axes: RT.axes, colour: RT.colour} : null},
      async () => { try { R = await api('/api/spark/' + encodeURIComponent(name)); draw(); } catch (e) { toast(e.message, 'err'); } });
    $$('.ntabs button', main).forEach(b => b.onclick = () => {
      $$('.ntabs button', main).forEach(x => x.classList.toggle('on', x === b));
      $$('[data-np]', main).forEach(p => { p.hidden = p.dataset.np !== b.dataset.nt; });
    });
    $$('.nsheets img', main).forEach(im => im.onclick = () => lightbox(R.sheets.map((s, i) => ({src: s, cap: t('A frame of every shot, sheet {n}', {n: i + 1})})), +im.dataset.i));
    $$('.spstrip', main).forEach(im => im.onclick = () => lightbox(strips.map(([k, s]) => ({src: s, cap: k === 'hook' ? t('The first 3 s') : t('The last 3 s')})), strips.findIndex(x => x[0] === im.dataset.strip)));
    const q = $('#spq', main), lines = $$('.nline', main);
    if (q) q.oninput = () => { const s = q.value.toLowerCase(); lines.forEach((d, i) => { d.hidden = !!s && !R.lines[i].text.toLowerCase().includes(s); }); };
    const dl = $('#spdl', main);
    if (dl) dl.onclick = async () => {
      try {
        const r = await api(`/api/spark/${encodeURIComponent(R.name)}/md`);
        const a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([r.text], {type: 'text/markdown;charset=utf-8'})); a.download = r.file;
        document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
        toast(t('Downloaded: {file}', {file: r.file}), 'ok');
      } catch (e) { toast(e.message, 'err'); }
    };
    const nb = $('#spnum', main);
    if (nb) nb.onclick = async () => {
      nb.disabled = true;
      try {
        await api(`/api/spark/${encodeURIComponent(R.name)}/numbers`, {});
        toast(t('Looking the numbers up again - they show here when they are in'), 'ok');
        const was = R.fetched;
        const look = (k) => { numWait = setTimeout(async () => {
          try { const NR = await api('/api/spark/' + encodeURIComponent(name)); if (NR.fetched !== was) { R = NR; draw(); return; } } catch (e) { /* again */ }
          if (k < 40) look(k + 1); }, 3000); };
        look(0);
      } catch (e) { toast(e.message, 'err'); nb.disabled = false; }
    };
  };
  draw();
  const wait = () => { if (R.report) return; timer = setTimeout(async () => {      // waiting for Claude: look every 5 s
    try { const NR = await api('/api/spark/' + encodeURIComponent(name)); if (NR.report) { R = NR; draw(); } } catch (e) { /* again */ }
    wait(); }, 5000); };
  wait();
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
  <div class="head"><div><div class="crumb"><a href="#/analyze">${t('Analyser')}</a> / <a href="#/analyze/videos">FLUX</a> / ${t('video')}</div><div class="mtitle mhost">${mascot('flux', {size: 46})}<h1${R.label && R.label !== R.title ? ` title="${esc(R.title)}"` : ''}>${esc(R.label || R.title)}</h1></div>
    <div class="sub">${focusChip(R.focus || '')}${R.focus ? '' : `<span class="fchip sm" title="${ta('analysed before 0.4')}">${t('focus not set')}</span>`} <span class="tag">${esc(t(R.category_label || ''))}</span> ${(R.tags || []).map(g => `<span class="tag dim">${esc(g)}</span> `).join('')}<a href="#" id="editmeta" class="small">${t('edit')}</a>
      ${R.url ? ` · <a href="${esc(R.url)}" target="_blank" rel="noopener">${esc(R.platform || t('source'))}</a>` : ''} · ${R.video.width}×${R.video.height} · ${fps} fps · ${t('{n} frames (f0–{last}, 00:00:00:00 – {end})', {n: N, last: N - 1, end: R.video.end_tc})}${R.audio.bpm ? ` · ${dec(R.audio.bpm, 1)} BPM` : ''}
      · ${t('{n} effects, {cuts} hard cuts', {n: evs.length, cuts: R.cuts.length})} · ${t('analysed {when}', {when: esc(R.generated || '')})}${R.source_unchanged ? ' · ' + t('source unchanged ✓') : ''}</div>
    ${R.pacing ? `<div class="small pacing">${t('Pacing: <b>{cpm}</b> cuts/min · shots avg <b>{avg} s</b> (median {med} s) · <b>{hook}</b> cut(s) in the first 3 s · <b>{epm}</b> effects/min',
      {cpm: numStr(R.pacing.cuts_per_min ?? '–'), avg: numStr(R.pacing.avg_shot_s ?? '–'), med: numStr(R.pacing.median_shot_s ?? '–'), hook: numStr(R.pacing.hook_cuts_3s), epm: numStr(R.pacing.effects_per_min ?? '–')})}${R.pacing.cuts_on_beat_pct != null ? ' · ' + t('{pct} % of plain cuts on the beat', {pct: numStr(R.pacing.cuts_on_beat_pct)}) : ''}</div>` : ''}</div>
    <div class="row"><button class="btn cl" id="recreate" title="${ta('Claude edits your own clips like this video')}"><svg class="i"><use href="#i-edit"/></svg>${t('Edit my clips like this…')}</button>
      ${sparkLink(R.spark, R.source)}
      ${R.report ? `<button class="btn" data-open="${esc(R.report)}">${t('Open full report')}</button>` : ''}
      <button class="btn" data-open="${esc('analysis/' + R.name)}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button>${delBtn('reference', R.name, '#/analyze/videos', ' ' + t('Delete'))}</div></div>
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
  sparkWire(main);
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
