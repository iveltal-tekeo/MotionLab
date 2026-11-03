/* MotionLab app - js/brand.js: My Brand (#/brand).
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ============================================================================================ my brand
// 0.6.0 (Content agency; the look = the user's mock-up, slide 10): what Claude knows about the brand -
// knowledge\local\brand.json through GET / POST /api/brand (motionlab\brand.py checks every save). Two columns of
// cards: the goal on social media (pills + the user's words), the audience (chips), the identity (the name and what
// the brand does, the logo, colours, fonts), the tone of voice | the website (+ Import from your website), your pages,
// the catalogue (a row a product: picture, name, what it is, its link, price, a "use in videos" switch). Each change
// saves itself 0.5 s after the last key ("saved ✓" in the band); the website on Enter / leaving the field (a
// half-typed address would be refused), a page's link only once it is that platform's page.
const BRAND_GOALS = [['sell', 'Sell'], ['personal_brand', 'Personal brand'], ['community', 'Build a community'], ['inform', 'Inform']];
const BRAND_TONES = ['Close|tone', 'Direct', 'Funny', 'Expert', 'Calm', 'Bold', 'Inspiring', 'Premium'];
const BRAND_TABS = [['overview', t('Overview'), 'i-home'], ['style', t('Style'), 'i-palette'], ['catalogue', t('Catalogue'), 'i-bag']];
// a colour's job (= brand.COLOUR_ROLES; the import's screenshot palette gives them)
const BRAND_ROLES = [['background', t('Background')], ['text', t('Text')], ['accent', t('Accent')], ['neutral', t('Neutral')]];
// logo versions (2026-10-26, 3f = brand.LOGO_KINDS): light = the one for dark backgrounds, dark = for light ones; where
// videos put the logo (brand.LOGO_WHERE; '' = Claude's call)
const BRAND_LOGOS = [['light', t('On dark'), t('Your logo for dark backgrounds - usually white or light')],
  ['dark', t('On light'), t('Your logo for light backgrounds - usually dark')],
  ['icon', t('Icon only'), t('The mark alone, without the name - for a corner of the video')]];
const BRAND_LOGO_WHERE = [['', t('Auto')], ['end', t('End card')], ['corner', t('End card + corner')], ['none', t('Nowhere')]];
// the signature end card (2026-10-26, 5c = brand.END_STYLES): '' = Claude's call, else a Motion Graphics template
const BRAND_ENDS = [['', t('Auto'), ''], ['logo', t('Logo'), 'logo-reveal'], ['title', t('Title'), 'title-card'], ['channel', t('Channel|end card'), 'end-screen']];
// does it read (3f, = brand.contrast / READ_TEXT 4.5 / READ_BIG 3): the WCAG contrast of two #rrggbb colours
const brandLum = h => { const c = [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16) / 255).map(v => v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
const brandContrast = (a, b) => { const [hi, lo] = [brandLum(a), brandLum(b)].sort((p, q) => q - p); return Math.round((hi + 0.05) / (lo + 0.05) * 10) / 10; };
// My Brand as the page and the import's pop-up use it: every part there, also in a brand.json older than a part
function brandNorm(B) {
  B.goal = B.goal || {picks: [], words: ''}; B.audience = B.audience || [];
  B.identity = B.identity || {colours: [], voice: ''}; B.identity.colours = B.identity.colours || [];
  B.site = B.site || {url: '', read: null}; B.catalogue = B.catalogue || [];
  B.identity.fonts = B.identity.fonts || {heading: '', body: ''}; B.pages = B.pages || []; B.name = B.name || ''; B.about = B.about || '';
  B.look = B.look || {like: []}; B.glossary = B.glossary || []; B.pillars = B.pillars || [];
  const tn0 = B.identity.tone || {};
  B.identity.tone = {dims: {casual: null, funny: null, cheeky: null, excited: null, ...(tn0.dims || {})}, use: tn0.use || [], avoid: tn0.avoid || [], lines: tn0.lines || []};
  B.identity.captions = {look: '', font: '', case: '', color: '', highlight: '', motion: '', position: '', box: null, words: 0, size: '', ...(B.identity.captions || {})};
  B.identity.logos = {light: '', dark: '', icon: '', ...(B.identity.logos || {})}; B.identity.logo_where = B.identity.logo_where || '';
  B.end_card = {style: '', line: '', sound: '', ...(B.end_card || {})}; B.identity.sound_logo = B.identity.sound_logo || '';
  return B;
}
// Import from your website runs as a job (2026-10-25): BRAND_IMP follows it from any page - the bar and its stage
// under the big button (when My Brand is open), a toast when it ends elsewhere; what it found waits (brandPendPaint)
const BRAND_IMP_STAGE = {home: t('Reading your home page'), pages: t('Reading your pages'), styles: t('Reading your colours and fonts'),
  shop: t('Looking for your shop'), fonts: t('Getting your fonts'), logos: t('Getting your logo'), screen: t('Looking at your page'),
  pictures: t('Getting the products\' pictures'),
  done: t('Almost done')};
let BRAND_IMP = null;                                    // {id, pct, stage} while an import job runs
let BRAND_UNDO = false;                                  // My Brand was just reset: "Bring it back" until the next change
function brandImpPaint() {
  const b = $('#brimp'), bar = $('#brprog'), st = $('#brimpst');
  if (!b) return;
  const on = !!BRAND_IMP;
  b.disabled = on; b.classList.toggle('busy', on); bar.hidden = !on;
  if (on) { $('i', bar).style.width = Math.max(3, BRAND_IMP.pct) + '%';
    st.textContent = `${BRAND_IMP_STAGE[BRAND_IMP.stage] || t('Reading your website…')} · ${Math.round(BRAND_IMP.pct)} %`; }
  else st.textContent = st.dataset.idle || '';
}
async function brandImpWatch(id) {
  if (BRAND_IMP && BRAND_IMP.id === id) return;
  BRAND_IMP = {id, pct: 2, stage: 'home'}; brandImpPaint();
  let since = 0, last = '';
  for (;;) {
    await new Promise(r => setTimeout(r, 900));
    let s; try { s = await api(`/api/jobs/${id}?since=${since}`); } catch (e) { continue; }
    const lines = (s.log || []).map(l => String(l).trim()).filter(Boolean);
    since += (s.log || []).length;
    const pr = lines.map(l => /^progress (\d+(?:\.\d+)?) (\w+)/.exec(l)).filter(Boolean).pop();
    if (pr) Object.assign(BRAND_IMP, {pct: +pr[1], stage: pr[2]});
    last = lines.filter(l => !l.startsWith('progress ')).pop() || last;
    if (['running', 'queued', 'cancelling'].includes(s.status)) { brandImpPaint(); continue; }
    BRAND_IMP = null; brandImpPaint();
    if (s.status !== 'done') { toast(t('Could not read your website: {why}', {why: (last || s.status).replace(/^ERROR: /, '')}), 'err'); return; }
    BRAND_DATA = null;
    if (/^#\/brand/.test(location.hash)) {
      try { const [F, B] = await Promise.all([api('/api/brand/import'), api('/api/brand')]); brImportModal(F, brandNorm(B)); }
      catch (e) { toast(e.message, 'err'); }
    } else toast(t('Your website is read - open My Brand to see what was found'), 'ok');
    brandPendPaint();
    return;
  }
}
// what the last import found and nobody imported or put aside yet: a banner on My Brand + a dot on its sidebar row
async function brandPendPaint() {
  let F, B;
  try { [F, B] = await Promise.all([api('/api/brand/import'), api('/api/brand')]); } catch (e) { return; }
  let aside = '';
  try { aside = localStorage.getItem('ml.brandImpAside') || ''; } catch (e) { /* storage blocked */ }
  const pend = !!(F && F.at && F.at !== (B.site || {}).read && F.at !== aside);
  const dot = $('#brandimp'); if (dot) dot.hidden = !pend;
  const ban = $('#brpend');
  if (!ban) return;
  ban.hidden = !pend;
  if (!pend) return;
  const n = (F.products || []).length;
  ban.innerHTML = `<svg class="i"><use href="#i-download"/></svg><span><b>${t('Your website was read {when}', {when: whenStr(F.at)})}</b>
      <span class="small muted">${[F.name ? esc(F.name) : '', n ? tn(n, '{n} product', '{n} products') : '', (F.logos || []).length ? t('a logo') : '',
        (F.colours || []).length ? tn(F.colours.length, '{n} colour', '{n} colours') : ''].filter(Boolean).join(' · ')}</span></span>
    <button class="btn pri sm" id="brpgo">${t('See what was found')}</button><button class="brx" id="brpx" title="${ta('Put it aside')}">×</button>`;
  $('#brpgo', ban).onclick = () => brImportModal(F, brandNorm(B));
  $('#brpx', ban).onclick = () => { try { localStorage.setItem('ml.brandImpAside', F.at); } catch (e) { /* storage blocked */ } brandPendPaint(); };
}
const BRAND_PAGES = {youtube: 'YouTube', tiktok: 'TikTok', instagram: 'Instagram', x: 'X', linkedin: 'LinkedIn',
                     facebook: 'Facebook', threads: 'Threads', twitch: 'Twitch'};      // = brand.PLATFORMS
const BRAND_PAGE_RX = Object.fromEntries(Object.entries({                          // = siteread.SOCIAL
  youtube: String.raw`(?:www\.|m\.)?youtube\.com/(?:@[\w.-]+|c/[\w.-]+|channel/[\w-]+|user/[\w.-]+)`,
  tiktok: String.raw`(?:www\.)?tiktok\.com/@[\w.-]+`, instagram: String.raw`(?:www\.)?instagram\.com/[\w.]+`,
  x: String.raw`(?:www\.)?(?:x|twitter)\.com/\w+`, linkedin: String.raw`(?:[a-z]{2,3}\.)?linkedin\.com/(?:company|in)/[\w.-]+`,
  facebook: String.raw`(?:www\.|m\.)?facebook\.com/[\w.-]+`, threads: String.raw`(?:www\.)?threads\.(?:net|com)/@[\w.]+`,
  twitch: String.raw`(?:www\.)?twitch\.tv/\w+`}).map(([k, v]) => [k, new RegExp(String.raw`^(https?://)?` + v, 'i')]));
const brandPgLogo = p => `<img class="brpgl" src="/files/logos/${p}/color.svg" alt="${esc(BRAND_PAGES[p] || p)}">`;
// the captions graphic's two ready looks (= tools\overlays\examples\captions\presets.json, the numbers the preview
// needs; y = y_upright, the height on a 9:16 video) and brand.CAPTION_Y
const CAPTION_LOOK = {
  classic: {font: 'Archivo Black', weight: 800, size: 72, upper: true, color: '#ffffff', hl: '#ffd400', outline: 6, box: false,
            boxc: 'rgba(0,0,0,.6)', motion: 'highlight', y: 78},
  clean_box: {font: 'Poppins', weight: 600, size: 56, upper: false, color: '#ffffff', hl: '#5ce1e6', outline: 0, box: true,
              boxc: 'rgba(12,14,20,.62)', motion: 'highlight', y: 70},
  keyword: {font: 'Inter', weight: 700, size: 44, upper: true, color: '#ffffff', hl: '#ffd400', outline: 3, box: false,
            boxc: 'rgba(0,0,0,.6)', motion: 'keyword', y: 64, kfont: 'Instrument Serif', kscale: 2.6}};
const CAPTION_POS = {bottom: 72, middle: 50, top: 20};
const CAP_SIZE = {s: 0.8, m: 1, l: 1.25, xl: 1.5};       // = brand.CAPTION_SIZE (the look's own size x this)

// Import from your website, before anything comes in (2026-10-25, the user: "before importing make a pop up with all
// the info gotten and how it would be imported like if it got 10 products from the website it would show you it will
// import those 10 products into the products category with the respective price and you can check if u want that or
// not and other info as well (while finally checking if that info is already in the my brand section to not add
// duplicates)"): a section per kind, each saying where it goes; what My Brand already holds is marked and cannot be
// ticked; what would replace something the user set (their logo, name, fonts, a page's link) starts unticked
function brImportModal(F, B) {
  if (!F || !F.url) { toast(t('Nothing was found - try the import again'), 'err'); return; }
  const low = s => String(s || '').trim().toLowerCase(), bare = u => low(u).replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '');
  const P = F.products || [], C = F.colours || [], L = F.logos || [], FO = F.fonts || [], PG = F.pages || [];
  const cols = new Set(B.identity.colours.map(c => c.hex.toLowerCase())), prods = new Set(B.catalogue.map(p => low(p.name)));
  const pageOf = p => B.pages.find(x => x.platform === p.platform && x.url);
  const dup = {name: !!F.name && low(B.name) === low(F.name), about: !!F.about && low(B.about) === low(F.about),
               col: c => cols.has(c.hex), prod: p => prods.has(low(p.name)), page: p => !!pageOf(p) && bare(pageOf(p).url) === bare(p.url)};
  const room = Math.max(0, 6 - B.identity.colours.length);
  // a font = the library's, or a free Google font the import downloaded (it comes into the user's fonts when picked)
  const fname = f => f.library || (f.google ? f.family : '');
  const libs = [...new Set(FO.map(fname).filter(Boolean))];
  const gface = (f, i) => f.google ? f.google.weights.map(w => `@font-face { font-family: 'bimg${i}'; font-weight: ${w};
    src: url('${fileUrl(`${f.google.dir}/${f.family.replace(/ /g, '')}-${w}.ttf`)}'); }`).join('\n') : '';
  const pk = {name: !!F.name && !B.name, about: !!F.about && !B.about, text: !!F.text_blocks,
    logo: B.identity.logo ? '' : ((L.find(l => l.kind !== 'share') || L[0] || {}).file || ''),
    // colours: none ticked when My Brand has some; else the background, the text and the accents (the screenshot's
    // palette), or the first four (the CSS' most used, no roles)
    colours: B.identity.colours.length ? [] : C.filter(c => !dup.col(c) && (c.role ? c.role !== 'neutral' : true))
      .slice(0, Math.min(C.some(c => c.role) ? 6 : 4, room)).map(c => c.hex),
    fonts: {heading: B.identity.fonts.heading ? '' : libs[0] || '', body: B.identity.fonts.body ? '' : libs[1] || libs[0] || ''},
    pages: PG.filter(p => !pageOf(p)).map(p => p.platform),
    products: P.map((p, i) => dup.prod(p) ? -1 : i).filter(i => i >= 0)};
  const fresh = (F.name && !dup.name) || (F.about && !dup.about) || L.length || C.some(c => !dup.col(c)) || libs.length
    || PG.some(p => !dup.page(p)) || P.some(p => !dup.prod(p)) || F.text_blocks;
  const already = `<span class="bimdup">${t('already in My Brand')}</span>`;
  const sec = (key, icon, col, title, to, body, extra = '') => `<div class="bimsec" data-sec="${key}"><div class="bimh">${`<svg class="ic" style="color: var(${col})"><use href="#${icon}"/></svg>`}<b>${title}</b>
      <span class="bimto">→ ${to}</span><span class="bimn" data-n="${key}"></span>${extra}</div>${body}</div>`;
  const ck = (attr, on, off = false) => `<input type="checkbox" ${attr}${on ? ' checked' : ''}${off ? ' disabled' : ''}>`;
  const fileSrc = f => fileUrl(f);
  const html = `<h2>${t('From your website')} <span class="muted">${esc(F.site || '')}</span></h2>
    <div class="small muted">${fresh ? t('Tick what goes into My Brand - nothing comes in until you press Add.') : t('Everything found is already in My Brand.')}
      ${tn((F.pages_read || []).length, 'Read {n} page.', 'Read {n} pages.')}</div>
    ${F.name || F.about ? sec('words', 'i-palette', '--pink', t('Name and description'), t('Brand identity'),
      `<div class="bimrows">${F.name ? `<label class="bimrow${dup.name ? ' dup' : ''}">${ck('data-k="name"', pk.name, dup.name)}<b>${esc(F.name)}</b>${dup.name ? already : B.name ? `<span class="bimrep">${t('replaces “{old}”', {old: esc(B.name)})}</span>` : ''}</label>` : ''}
        ${F.about ? `<label class="bimrow${dup.about ? ' dup' : ''}">${ck('data-k="about"', pk.about, dup.about)}<span>${esc(F.about)}</span>${dup.about ? already : B.about ? `<span class="bimrep">${t('replaces what you wrote')}</span>` : ''}</label>` : ''}</div>`) : ''}
    ${F.text_blocks ? sec('text', 'i-texts', '--cyan', t('What your website says'), t('Claude reads it for facts'),
      `<label class="bimrow">${ck('data-k="text"', pk.text)}<span>${tn(F.text_blocks, 'Keep its {n} part for Claude', 'Keep its {n} parts for Claude')}
        <span class="small muted">${t('services, prices, who you are - never your voice')}</span></span></label>
       <pre class="bimtext">${esc(F.text.slice(0, 1500))}${F.text.length > 1500 ? '\n…' : ''}</pre>`) : ''}
    ${L.length ? sec('logo', 'i-brand', '--pink', t('Logo'), t('Brand identity'),
      `<div class="bimlogos">${L.map(l => `<label class="bimlogo">${`<input type="radio" name="bimlogo" value="${esc(l.file)}"${pk.logo === l.file ? ' checked' : ''}>`}<span class="bimli"><img src="${fileSrc(l.file)}" alt=""></span>
          <small>${l.kind === 'share' ? t('share picture') : l.kind === 'icon' ? t('site icon') : t('logo')}</small></label>`).join('')}
        <label class="bimlogo"><input type="radio" name="bimlogo" value=""${pk.logo ? '' : ' checked'}><span class="bimli none">${t('None')}</span><small>${B.identity.logo ? t('keep mine') : '&nbsp;'}</small></label></div>`) : ''}
    ${C.length ? sec('colours', 'i-palette', '--pink', t('Colours'), t('Brand identity'),
      `<div class="bimcolw">${F.screenshot ? `<img class="bimshot" src="${fileUrl(F.screenshot)}" alt="" title="${ta('Your page as a visitor sees it - the colours are taken from it')}">` : ''}
       <div class="bimcols">${C.map(c => `<label class="bimcol${dup.col(c) ? ' dup' : ''}">${ck(`data-col="${esc(c.hex)}"`, pk.colours.includes(c.hex), dup.col(c))}<span class="bimsw" style="background: ${esc(c.hex)}"></span>
          <span class="bimct"><span class="mono small">${esc(c.hex)}</span><span class="bimcr">${[c.role ? (BRAND_ROLES.find(r => r[0] === c.role) || [, c.role])[1] : '',
            c.share != null ? t('{pct} % of the page', {pct: numStr(c.share)}) : c.from === 'logo' ? t('in your logo') : c.theme ? t('the site\'s colour') : ''].filter(Boolean).join(' · ')}</span></span>
          ${dup.col(c) ? already : ''}</label>`).join('')}</div></div>
        ${room < C.filter(c => !dup.col(c)).length ? `<div class="small muted">${t('My Brand holds 6 colours - {n} more fit.', {n: room})}</div>` : ''}`) : ''}
    ${FO.length ? sec('fonts', 'i-type', '--violet', t('Fonts'), t('Brand identity'),
      `<style>${FO.map(gface).join('\n')}</style><div class="bimfonts">${FO.map((f, i) => fname(f) ? `<div class="bimfont"><span class="bimfn" style="font-family: '${esc(f.library || 'bimg' + i)}'">${esc(f.family)}</span>
          ${['heading', 'body'].map(k => `<label class="bimrole${B.identity.fonts[k] === fname(f) ? ' dup' : ''}"><input type="radio" name="bimf-${k}" value="${esc(fname(f))}"${pk.fonts[k] === fname(f) ? ' checked' : ''}>${k === 'heading' ? t('Titles') : t('Body text')}</label>`).join('')}
          ${f.library ? '' : `<span class="bimtag" title="${ta('Free to use ({licence}): picked for titles or body text, it is added to your fonts on this PC', {licence: f.google.licence})}">${t('a free Google font - comes into your fonts')}</span>`}</div>`
        : `<div class="bimfont off"><span class="bimfn">${esc(f.family)}</span><span class="small muted">${t('not a free Google font - it may need a licence')}</span></div>`).join('')}</div>`) : ''}
    ${PG.length ? sec('pages', 'i-link', '--cyan', t('Your pages'), t('Your pages'),
      `<div class="bimrows">${PG.map(p => `<label class="bimrow${dup.page(p) ? ' dup' : ''}">${ck(`data-page="${esc(p.platform)}"`, pk.pages.includes(p.platform), dup.page(p))}<span class="brpgt">${brandPgLogo(p.platform)}</span>
          <span>${esc(BRAND_PAGES[p.platform] || p.platform)} <b>${esc(p.handle || '')}</b></span>${dup.page(p) ? already : pageOf(p) ? `<span class="bimrep">${t('replaces {old}', {old: esc(bare(pageOf(p).url))})}</span>` : ''}</label>`).join('')}</div>`) : ''}
    ${sec('products', 'i-bag', '--amber', t('Products'), t('Catalogue'), P.length
      ? `<div class="bimprods">${P.map((p, i) => `<label class="bimp${dup.prod(p) ? ' dup' : ''}">${ck(`data-prod="${i}"`, pk.products.includes(i), dup.prod(p))}
          <span class="bimpi">${p.image ? `<img src="${fileSrc(p.image)}" alt="">` : '<svg class="i"><use href="#i-box"/></svg>'}</span>
          <span class="bimpt"><b>${esc(p.name)}</b>${p.price ? `<span class="bimpp">${esc(p.price)}</span>` : `<span class="small muted">${t('no price found')}</span>`}
            ${p.what ? `<span class="bimpw">${esc(p.what)}</span>` : ''}${dup.prod(p) ? already : ''}</span></label>`).join('')}</div>`
      : `<div class="small muted">${t('No shop found on this site - add your products in the Catalogue by hand.')}</div>`,
      P.some(p => !dup.prod(p)) ? `<button class="btn sm ghost" id="bimall">${t('All / none')}</button>` : '')}
    <div class="row bimfoot"><button class="btn pri" id="bimgo"></button><button class="btn ghost" id="bimno">${t('Cancel')}</button></div>`;
  modal(html, box => {
    const read = () => {
      pk.name = !!$('[data-k=name]:checked', box); pk.about = !!$('[data-k=about]:checked', box); pk.text = !!$('[data-k=text]:checked', box);
      pk.logo = ($('input[name=bimlogo]:checked', box) || {}).value || '';
      pk.colours = $$('[data-col]:checked', box).map(c => c.dataset.col);
      pk.fonts = {heading: ($('input[name=bimf-heading]:checked', box) || {}).value || '', body: ($('input[name=bimf-body]:checked', box) || {}).value || ''};
      pk.pages = $$('[data-page]:checked', box).map(c => c.dataset.page);
      pk.products = $$('[data-prod]:checked', box).map(c => +c.dataset.prod);
    };
    const count = () => {
      read();
      const fonts = ['heading', 'body'].filter(k => pk.fonts[k] && pk.fonts[k] !== B.identity.fonts[k]).length;
      const n = {words: +pk.name + +pk.about + +pk.text, logo: +!!pk.logo, colours: pk.colours.length, fonts, pages: pk.pages.length, products: pk.products.length};
      $$('[data-n]', box).forEach(s => { const k = s.dataset.n; s.textContent = k === 'products' && P.length ? t('{n} of {m} ticked', {n: n.products, m: P.length}) : ''; });
      const all = Object.values(n).reduce((a, b) => a + b, 0), go = $('#bimgo', box);
      go.textContent = all ? tn(all, 'Add {n} thing to My Brand', 'Add {n} things to My Brand') : t('Nothing ticked');
      go.disabled = !all;
      // colours: no more than fit
      const left = room - pk.colours.length;
      $$('[data-col]', box).forEach(c => { if (!c.checked && !c.closest('.dup')) c.disabled = left <= 0; });
    };
    box.addEventListener('change', count);
    // a font's role: a second click on the ticked one lets it go (a radio cannot be unticked by itself)
    $$('.bimrole input', box).forEach(r => {
      r.dataset.was = r.checked ? '1' : '';
      r.onclick = () => {
        if (r.dataset.was) r.checked = false;
        $$(`input[name=${r.name}]`, box).forEach(o => { o.dataset.was = o.checked ? '1' : ''; });
        count();
      };
    });
    const all = $('#bimall', box);
    if (all) all.onclick = () => { const cs = $$('[data-prod]:not(:disabled)', box), on = cs.some(c => !c.checked); cs.forEach(c => { c.checked = on; }); count(); };
    $('#bimno', box).onclick = closeModal;
    $('#bimgo', box).onclick = async () => {
      read();
      const go = $('#bimgo', box); go.disabled = true;
      try {
        await api('/api/brand/import', {picks: pk});
        if (FO.some(f => !f.library && f.google && Object.values(pk.fonts).includes(f.family))) {   // a font came into the library
          const l = $('link[href^="/fonts.css"]'); if (l) l.href = '/fonts.css?v=' + Date.now();
        }
        BRAND_DATA = null; closeModal(); toast(t('Added to My Brand'), 'ok'); route();
      } catch (e) { toast(e.message, 'err'); go.disabled = false; }
    };
    count();
  }, 'wide bimmodal');
}
async function pageBrand(main, tabArg) {
  try { localStorage.setItem('ml.brandSeen', '1'); } catch (e) { /* private window */ }
  $('#brandnew').hidden = true;
  const [B, FONTS] = await Promise.all([api('/api/brand').then(brandNorm), api('/api/fonts').then(r => r.families.map(f => f.family), () => [])]);
  let timer = null, queue = Promise.resolve(), endPending = false;   // endPending: the end card waits for the Style tab
  const say = (txt, cls) => { const s = $('#brsaved', main); if (s) { s.className = 'small ' + cls; s.textContent = txt; } };
  const save = (now = false) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const body = JSON.parse(JSON.stringify(B));
      if (BRAND_UNDO) { BRAND_UNDO = false; const u = $('#brundo', main); if (u) u.hidden = true; }   // a change: no undo of the reset
      paintGlance();
      queue = queue.then(() => api('/api/brand', body).then(r => { BRAND_DATA = LOGOS = null; say(t('saved ✓'), 'ok'); endSaved(r); },
                                                             e => { say(t('NOT saved'), 'bad'); toast(e.message, 'err'); }));
    }, now ? 0 : 500);
  };
  const icon = (id, col) => `<svg class="ic" style="color: var(${col})"><use href="#${id}"/></svg>`;
  const x = title => `<button class="brx" title="${ta(title)}">×</button>`;
  // three tabs (2026-10-25, the user: "create some tabs for the my brand page ... i dont want to be scrolling", "a tab
  // called Style that can have the brand identity, tone of voice and captions stuff", "in the overview ... the website,
  // goal, target, pages... (with some videos previewing maybe)"): all drawn once, a tab shows its pane - no reload, so a
  // change typed a moment ago is never lost; the address follows (replaceState: no hashchange, no redraw)
  const tab0 = BRAND_TABS.some(([k]) => k === tabArg) ? tabArg : 'overview';
  main.innerHTML = `<div class="head"><div><h1>${t('My Brand')}</h1><div class="sub">${t('What Claude knows about your brand. It uses it in Prepare, the Editor and Motion Graphics.')}</div></div>
      <span id="brsaved" class="small muted"></span>
      <button class="btn sm ghost brreset" id="brundo"${BRAND_UNDO ? '' : ' hidden'}><svg class="i"><use href="#i-restart"/></svg>${t('Bring it back')}</button>
      <button class="btn sm ghost brreset" id="brreset" title="${ta('Clears everything on this page to try from zero - a copy is kept')}"><svg class="i"><use href="#i-trash"/></svg>${t('Start from zero')}</button></div>
    <div class="tabs brtabs">${BRAND_TABS.map(([k, l, ic]) => `<a href="#/brand${k === 'overview' ? '' : '/' + k}" data-tab="${k}"><svg class="i"><use href="#${ic}"/></svg>${l}${k === 'catalogue' ? ` <span class="dim" id="brcatn"></span>` : ''}</a>`).join('')}</div>
    <div class="brpend" id="brpend" hidden></div>
    <div class="brpane" data-pane="overview"><div class="panel brglance" id="brglance"></div><div class="brgrid"><div class="brcol">
      <div class="panel brcard brweb"><h2>${icon('i-globe', '--green')}${t('Your website')}</h2>
        <input type="url" id="brurl" maxlength="300" placeholder="${ta('yourbrand.com')}">
        <button class="btn pri brimpbig" id="brimp" title="${ta('Reads your website: a shop\'s catalogue with prices and descriptions, your logo, colours, fonts and pages. You tick what goes in.')}"><svg class="i"><use href="#i-download"/></svg><span>${t('Import from your website')}</span></button>
        <div class="brprog" id="brprog" hidden><i></i></div>
        <div class="small muted brnote" id="brimpst"></div></div>
      <div class="panel brcard"><h2>${icon('i-target', '--pink')}${t('Goal on social media')}</h2>
        <div class="brpills" id="brgoals">${BRAND_GOALS.map(([id, l]) => `<button class="brpill" data-g="${id}">${t(l)}</button>`).join('')}</div>
        <input type="text" id="brwords" maxlength="400" placeholder="${ta('In your words, e.g. full transparency: show how it is made and who is behind it')}"></div>
    </div><div class="brcol">
      <div class="panel brcard"><h2>${icon('i-users', '--cyan')}${t('Target audience')}</h2><div class="brpills" id="braud"></div></div>
      <div class="panel brcard"><h2>${icon('i-link', '--cyan')}${t('Your pages')}</h2>
        <div id="brpages"></div><div class="brpgadd" id="brpgadd"></div></div>
      <div class="panel brcard"><h2>${icon('i-target', '--amber')}${t('Content pillars')}</h2>
        <div class="small muted brnote">${t('The 3 to 6 themes you post about - each post on the Content agency calendar gets one.')}</div>
        <div id="brpils"></div><button class="btn sm" id="brpiladd"><svg class="i"><use href="#i-plus"/></svg>${t('Add a pillar')}</button></div>
    </div></div>
      <div class="panel brcard"><h2>${icon('i-film', '--amber')}${t('Your latest videos on MotionLab')}<a class="brside small" href="#/edit">${t('All in the Editor')} →</a></h2>
        <div class="brvids" id="brmine"></div></div></div>
    <div class="brpane" data-pane="style" hidden><div class="brgrid"><div class="brcol">
      <div class="panel brcard"><h2>${icon('i-palette', '--pink')}${t('Brand identity')}</h2>
        <div class="brsub">${t('Name')}</div>
        <input type="text" id="brname" maxlength="80" placeholder="${ta('Your brand\'s name')}">
        <textarea id="brabout" rows="2" maxlength="300" placeholder="${ta('What your brand does, in a line')}"></textarea>
        <div class="brsub">${t('Logo')}</div>
        <div class="brlogos"><label class="brlogo" title="${ta('Your logo - a PNG, JPG, WebP or SVG picture. Click to pick it.')}"><input type="file" accept=".png,.jpg,.jpeg,.webp,.svg" hidden>
          <span class="brlogoi" id="brlogoi"></span><span class="small muted">${t('Click to pick your logo - a PNG, JPG, WebP or SVG picture')}</span></label>
          <div class="brlvs">${BRAND_LOGOS.map(([k, l, tip]) => `<div class="brlv" data-k="${k}"><label class="brlogo" title="${esc(tip)}"><input type="file" accept=".png,.jpg,.jpeg,.webp,.svg" hidden>
            <span class="brlogoi brlvi ${k}"></span><span class="small muted">${l}</span></label>${x('Remove')}</div>`).join('')}</div></div>
        <div class="brsub">${t('Where your logo goes in videos')}</div>
        <div class="brpills" id="brlwhere">${BRAND_LOGO_WHERE.map(([k, l]) => `<button class="brpill" data-k="${k}">${l}</button>`).join('')}</div>
        <div class="brsub">${t('Colours')}</div>
        <div class="brcolours" id="brcols"></div>
        <div class="brread" id="brread"></div>
        <div class="brsub">${t('Fonts')}</div>
        <div class="brfonts" id="brfonts"></div></div>
      <div class="panel brcard"><h2>${icon('i-type', '--cyan')}${t('Names and words')}</h2>
        <div class="small muted brnote">${t('Spelled exactly like this in captions, scripts and titles - never translated.')}</div>
        <div class="brpills" id="brgloss"></div></div>
      <div class="panel brcard"><h2>${icon('i-film', '--pink')}${t('Your end card')}</h2>
        <div class="small muted brnote">${t('How your videos end - your logo, colours, fonts and website. Always last, never before the hook.')}</div>
        <div class="brends" id="brends">${BRAND_ENDS.map(([k, l, tid]) => `<button class="brend1" data-k="${k}">${tid
          ? `<img src="/files/tools/overlays/motion/${tid}/thumb.png" alt="" loading="lazy">` : `<span class="brendauto">${neIcon('i-sparkle')}</span>`}<span>${l}</span></button>`).join('')}</div>
        <div class="brendrow"><input type="text" id="brendline" maxlength="60" placeholder="${ta('Your sign-off, e.g. Book your shoot')}"><div class="brendprev" id="brendprev"></div></div>
        <div class="brsub">${t('Its sound')}</div><div class="brsnd" id="brsnd"></div></div>
    </div><div class="brcol">
      <div class="panel brcard"><h2>${icon('i-mic', '--violet')}${t('Tone of voice')}</h2>
        <div class="brpills" id="brtones">${BRAND_TONES.map(w => `<button class="brpill" data-w="${esc(t(w))}">${t(w)}</button>`).join('')}</div>
        <textarea id="brvoice" rows="2" maxlength="300" placeholder="${ta('In your words, e.g. close and direct, a bit of humour, never formal')}"></textarea>
        <div class="small muted brnote">${t('How Claude writes your scripts, your titles and every word on screen.')}</div>
        <div class="brsub">${t('How you sound')}</div><div class="brdims" id="brdims"></div>
        <div class="brsub">${t('Words you use')}</div><div class="brpills" id="bruse"></div>
        <div class="brsub">${t('Words you never use')}</div><div class="brpills" id="bravoid"></div>
        <div class="brsub">${t('Lines that sound like you')}</div>
        <textarea id="brlines" rows="3" maxlength="900" placeholder="${ta('One per line, up to 5 - a hook or a sentence you would really say on camera')}"></textarea>
        <div class="brsub">${t('What worked for you')}</div><div class="brworked" id="brworked"></div></div>
      <div class="panel brcard"><h2>${icon('i-cc', '--green')}${t('Captions')}<button class="btn sm ghost brside" id="brcapclr">${t('Back to the look\'s own')}</button></h2>
        <div class="brcap"><div class="brcapc" id="brcapc"></div><div class="brcapv"><div class="brphone" id="brphone"><div class="brcapl" id="brcapl"></div></div></div></div></div>
    </div></div>
      <div class="panel brcard brmood" id="brmood"><h2>${icon('i-thumb', '--pink')}${t('Your mood board')}<span class="brside" id="brmoodn"></span></h2>
        <div class="small muted brnote">${t('Pictures you love the look of - saved from Pinterest or Instagram, screenshots, photos. Claude matches their light, colours and feel in your graphics and thumbnails.')}</div>
        <div class="brmoodw"><div class="brmoodg" id="brmoodg"></div><div class="brmoodc" id="brmoodc"></div></div></div>
      <div class="panel brcard brlookc"><h2>${icon('i-film', '--amber')}${t('Your editing look')}<span class="brside" id="brlookn"></span></h2>
        <div class="small muted brnote">${t('Up to 3 videos you analysed: how your videos are cut - pacing, transitions, grade. New edit offers them first.')}</div>
        <input type="search" id="brlookq" placeholder="${ta('Search…')}" hidden><div class="brvids" id="brlook"></div></div></div>
    <div class="brpane" data-pane="catalogue" hidden>
      <div class="brcatbar"><button class="btn pri" id="bradd"><svg class="i"><use href="#i-plus"/></svg>${t('Add a product')}</button>
        <span class="small muted" id="brcatsum"></span><input type="search" id="brcatq" placeholder="${ta('Search…')}" hidden>
        <span class="brcathint">${icon('i-sparkle', '--violet')}${t('Claude can put the product, its price and the website in a motion graphic.')}</span></div>
      <div class="brprods" id="brprods"></div></div>`;
  // the mood board (0.6.0 step 7): pictures copied into the brand's folder and measured - the style card beside them;
  // its colours one click from the brand's colours (the page's own copy, saved as any change here)
  const moodCard = MD => {
    const g = $('#brmoodg', main), c = $('#brmoodc', main), C = MD.card;
    $('#brmoodn', main).textContent = MD.items.length ? `${MD.items.length} / ${MD.max}` : '';
    g.innerHTML = MD.items.map(it => `<div class="brmood1"><img src="${fileUrl(it.src)}" alt="" loading="lazy"><button class="brx" data-mx="${it.n}" title="${ta('Take it off the board')}">✕</button></div>`).join('')
      + (MD.items.length < MD.max ? `<label class="brmoodadd" title="${ta('Or drop pictures on the board')}">${neIcon('i-plus', '--pink')}<span>${t('Add pictures')}</span><input type="file" id="brmoodin" hidden multiple accept=".jpg,.jpeg,.png,.webp"></label>` : '');
    const have = new Set(B.identity.colours.map(x => x.hex.toLowerCase()));
    c.innerHTML = !C ? `<div class="small muted">${t('Add a few pictures: MotionLab reads their light, colours, contrast and room, and Claude follows them.')}</div>`
      : `<div class="brsub">${t('What MotionLab sees')}</div><div class="brpills">${C.words.map(w => `<span class="chip">${esc(t(w))}</span>`).join('')}</div>
        <div class="brsub">${t('Its colours')}</div><div class="brmoodcols">${C.colours.map(x => `<button class="brmoodcol${have.has(x.hex.toLowerCase()) ? ' on' : ''}" data-mc="${esc(x.hex)}" title="${ta('Add it to your brand colours')}"><i style="background:${esc(x.hex)}"></i><span>${esc(x.hex)}</span></button>`).join('')}</div>
        <div class="small muted">${[C.faces ? t('people in {n} of {of}', {n: C.faces.with, of: C.faces.of}) : '', C.text ? t('words on {n} of {of}', {n: C.text.with, of: C.text.of}) : ''].filter(Boolean).join(' · ')}</div>`;
    $$('[data-mx]', g).forEach(b => b.onclick = async () => { try { moodCard(await api('/api/brand/mood/remove', {n: +b.dataset.mx})); } catch (e) { toast(e.message, 'err'); } });
    $$('[data-mc]', c).forEach(b => b.onclick = () => { const h = b.dataset.mc;
      if (B.identity.colours.some(x => x.hex.toLowerCase() === h.toLowerCase())) return;
      if (B.identity.colours.length >= 6) { toast(t('Your brand has 6 colours - remove one first'), 'err'); return; }
      B.identity.colours.push({hex: h, name: ''}); paintCols(); save(); moodCard(MD); });
    const up = async files => { let st = MD;
      for (const f of [...files].filter(f => /\.(jpe?g|png|webp)$/i.test(f.name))) {
        try { st = await new Promise((ok, bad) => { const x = new XMLHttpRequest();
          x.open('POST', `/api/brand/mood/upload?name=${encodeURIComponent(f.name)}`); x.setRequestHeader('X-ML-Token', TOKEN);
          x.setRequestHeader('Content-Type', 'application/octet-stream');
          x.onload = () => { let j = null; try { j = JSON.parse(x.responseText); } catch (e) { /* not JSON */ } if (x.status < 300) ok(j); else bad(new Error((j && j.error) || x.status)); };
          x.onerror = () => bad(new Error(t('{name}: the copy stopped - try again', {name: f.name}))); x.send(f); });
          moodCard(st); } catch (e) { toast(e.message, 'err'); } } };
    const inp = $('#brmoodin', g);
    if (inp) inp.onchange = () => { const f = [...inp.files]; inp.value = ''; up(f); };
    const box = $('#brmood', main);
    box.ondragover = e => { e.preventDefault(); box.classList.add('drop'); };
    box.ondragleave = () => box.classList.remove('drop');
    box.ondrop = e => { e.preventDefault(); box.classList.remove('drop'); up(e.dataTransfer.files); };
  };
  api('/api/brand/mood').then(moodCard).catch(() => {});
  // Start from zero (2026-10-25, the user: "a button to reset all data for my brand (when u want to reset to try from
  // zero)"): asked first; brand.reset keeps a copy -> *Bring it back* until the next change; the last import's finds
  // are put aside too (a clean slate - Import from your website reads it again)
  $('#brreset', main).onclick = () => modal(`<h2>${t('Start My Brand from zero?')}</h2>
      <p>${t('Everything on My Brand is cleared: the name, goal, audience, logo, colours, fonts, tone of voice, captions, editing look, pages and catalogue. A copy is kept, so you can bring it back right after.')}</p>
      <div class="row" style="margin-top:14px"><button class="btn danger" id="brrgo">${t('Clear everything')}</button><button class="btn ghost" id="brrno">${t('Cancel')}</button></div>`, m => {
    $('#brrno', m).onclick = closeModal;
    $('#brrgo', m).onclick = async () => {
      try {
        clearTimeout(timer); await queue;
        await api('/api/brand/reset', {});
        const F = await api('/api/brand/import').catch(() => ({}));
        if (F && F.at) { try { localStorage.setItem('ml.brandImpAside', F.at); } catch (e) { /* storage blocked */ } }
        BRAND_DATA = null; BRAND_UNDO = true; closeModal(); toast(t('My Brand is empty again - a copy was kept'), 'ok'); route();
      } catch (e) { toast(e.message, 'err'); }
    };
  });
  $('#brundo', main).onclick = async () => {
    try { clearTimeout(timer); await queue; await api('/api/brand/reset', {undo: true});
      BRAND_DATA = null; BRAND_UNDO = false; toast(t('My Brand is back as it was'), 'ok'); route(); }
    catch (e) { toast(e.message, 'err'); }
  };
  const showTab = k => {
    $$('.brtabs a', main).forEach(a => a.classList.toggle('on', a.dataset.tab === k));
    $$('.brpane', main).forEach(p => { p.hidden = p.dataset.pane !== k; });
    if (k === 'overview') paintGlance();
    if (k === 'style' && endPending) paintEnd();
  };
  // the Overview's brand at a glance (2026-10-25, the user's pick "Overview at a glance + videos"): what For my brand
  // gives Claude - the logo, the name in its title font, what it does in its body font, colours, fonts, tone, pages,
  // products; drawn when the Overview shows and after a save
  function paintGlance() {
    const g = $('#brglance', main); if (!g) return;
    const I = B.identity, logo = I.logo ? brandLogoSrc(I.logo, B.updated) : '', head = I.fonts.heading, body = I.fonts.body;
    const prods = B.catalogue.filter(p => p.name.trim()), inv = prods.filter(p => p.use !== false).length;
    const tones = (I.voice || '').split(',').map(s => s.trim()).filter(Boolean).slice(0, 4), pages = B.pages.filter(p => p.url);
    g.innerHTML = !brandFilled(B) ? `<div class="brglempty">${icon('i-brand', '--pink')}<span><b>${t('Your brand at a glance')}</b>
        <span class="small muted">${t('Fill it in on Style and Catalogue - or import it from your website, just below.')}</span></span></div>`
      : `<div class="brgl"><span class="brgllogo">${logo ? `<img src="${logo}" alt="">` : `<b>${esc((B.name || '?')[0].toUpperCase())}</b>`}</span>
        <div class="brglt"><b class="brgln"${head ? ` style="font-family: '${esc(head)}'"` : ''}>${esc(B.name || t('Your brand'))}</b>
          ${B.about ? `<span class="brgla"${body ? ` style="font-family: '${esc(body)}'"` : ''}>${esc(B.about)}</span>` : ''}
          <span class="brglrow">${I.colours.length ? `<span class="brgldots">${I.colours.map(c => `<i style="background: ${esc(c.hex)}" title="${esc(c.name || c.hex)}"></i>`).join('')}</span>` : ''}
            ${head || body ? `<span class="brglf">${icon('i-type', '--cyan')}${esc([head, body].filter(Boolean).join(' · '))}</span>` : ''}
            ${tones.length ? `<span class="brglf">${icon('i-mic', '--violet')}${esc(tones.join(', '))}</span>` : ''}
            ${pages.length ? `<span class="brglpg">${pages.map(p => brandPgLogo(p.platform)).join('')}</span>` : ''}
            ${prods.length ? `<span class="brglf">${icon('i-bag', '--amber')}${tn(prods.length, '{n} product', '{n} products')} · ${t('{n} in videos', {n: inv})}</span>` : ''}</span></div>
        <div class="brglside"><span class="small muted">${t('What For my brand gives Claude')}</span>
          <button class="btn sm" id="brgledit">${icon('i-palette', '--pink')}${t('Edit the style')}</button></div></div>`;
    const ed = $('#brgledit', g);
    if (ed) ed.onclick = () => { showTab('style'); history.replaceState(null, '', '#/brand/style'); };
  }
  $$('.brtabs a', main).forEach(a => a.onclick = e => {
    e.preventDefault(); showTab(a.dataset.tab); history.replaceState(null, '', a.getAttribute('href'));
  });
  showTab(tab0);
  // the goal: pills (any number) + the user's words
  const paintGoals = () => $$('#brgoals .brpill', main).forEach(b => b.classList.toggle('on', B.goal.picks.includes(b.dataset.g)));
  $$('#brgoals .brpill', main).forEach(b => b.onclick = () => {
    const g = b.dataset.g;
    B.goal.picks = B.goal.picks.includes(g) ? B.goal.picks.filter(v => v !== g) : [...B.goal.picks, g];
    paintGoals(); save();
  });
  paintGoals();
  const words = $('#brwords', main);
  words.value = B.goal.words || '';
  words.oninput = () => { B.goal.words = words.value; save(); };
  // the audience: chips, + one more typed in (Enter or leaving the field adds it)
  const paintAud = (focus = false) => {
    const box = $('#braud', main);
    box.innerHTML = B.audience.map(a => `<span class="brpill on brchip">${esc(a)}${x('Remove')}</span>`).join('')
      + (B.audience.length < 12 ? `<span class="braddin"><svg class="i"><use href="#i-plus"/></svg><input type="text" maxlength="80" placeholder="${ta('Add: who is it for?')}"></span>` : '');
    $$('.brx', box).forEach((b, i) => b.onclick = () => { B.audience.splice(i, 1); paintAud(); save(); });
    const inp = $('.braddin input', box);
    if (!inp) return;
    const add = () => { const v = inp.value.trim(); if (!v) return; inp.value = ''; B.audience.push(v); paintAud(true); save(); };
    inp.onkeydown = e => { if (e.key === 'Enter') add(); };
    inp.onblur = add;
    if (focus) inp.focus();
  };
  paintAud();
  // the identity, top to bottom (2026-10-25, the user: "expand on the brand identity section from up to down instead
  // of table with columns? i want to also be able to put colors as hexadecimal"): the logo, then up to 6 colours - a
  // row each: the swatch (= the colour picker), its hex code typed (#2eaa5c or #2a5), its name
  const paintCols = () => {
    const box = $('#brcols', main);
    box.innerHTML = B.identity.colours.map(c => `<div class="brcol1"><label class="brswatch" style="background: ${esc(c.hex)}"><input type="color" value="${esc(c.hex)}"></label>
        <input type="text" class="brhex mono" maxlength="7" spellcheck="false" value="${esc(c.hex)}" title="${ta('The colour as a hex code, e.g. #2eaa5c')}">
        <input type="text" class="brghost brcn" maxlength="40" value="${esc(c.name)}" placeholder="${ta('Colour name')}">
        <select class="brrole" title="${ta('What this colour is for in your videos')}"><option value="">${t('Any use')}</option>${BRAND_ROLES.map(([r, l]) => `<option value="${r}"${c.role === r ? ' selected' : ''}>${l}</option>`).join('')}</select>${x('Remove')}</div>`).join('')
      + (B.identity.colours.length < 6 ? `<button class="btn sm ghost" id="brcoladd"><svg class="i"><use href="#i-plus"/></svg>${t('Add a colour')}</button>` : '');
    $$('.brcol1', box).forEach((row, i) => {
      const c = B.identity.colours[i], hex = $('.brhex', row), pick = $('input[type=color]', row);
      const set = h => { c.hex = h; $('.brswatch', row).style.background = h; pick.value = h; paintRead(); save(); };
      pick.oninput = e => { hex.value = e.target.value; hex.classList.remove('bad'); set(e.target.value); };
      hex.oninput = () => {
        const m = hex.value.trim().match(/^#?([0-9a-f]{3}|[0-9a-f]{6})$/i);
        hex.classList.toggle('bad', !m);
        if (m) set('#' + (m[1].length === 3 ? [...m[1]].map(ch => ch + ch).join('') : m[1]).toLowerCase());
      };
      hex.onblur = () => { if (!hex.classList.contains('bad')) hex.value = c.hex; };
      $('.brcn', row).oninput = e => { c.name = e.target.value; save(); };
      $('.brrole', row).onchange = e => { c.role = e.target.value; paintRead(); save(); };
      $('.brx', row).onclick = () => { B.identity.colours.splice(i, 1); paintCols(); save(); };
    });
    const add = $('#brcoladd', box);
    if (add) add.onclick = () => { B.identity.colours.push({hex: '#ff6fae', name: ''}); paintCols(); save(); };
    paintRead();
  };
  // does it read (3f): each text / accent colour on each background colour - a tile in those colours, its contrast
  const paintRead = () => {
    const cols = B.identity.colours, bgs = cols.filter(c => c.role === 'background');
    const pairs = cols.filter(c => c.role === 'text' || c.role === 'accent').flatMap(c => bgs.map(bg => ({c, bg, r: brandContrast(c.hex, bg.hex)})));
    $('#brread', main).innerHTML = pairs.length ? `<div class="brsub">${t('Does it read?')}</div><div class="brreadl">${pairs.map(({c, bg, r}) => {
      const ok = r >= (c.role === 'text' ? 4.5 : 3);
      return `<span class="brrd${ok ? '' : ' bad'}" title="${esc(ok ? t('Reads well') : t('Hard to read - on this background Claude uses white or black instead'))}">
        <span class="brrds" style="background: ${esc(bg.hex)}; color: ${esc(c.hex)}">Aa</span><span><b>${dec(r)}:1 ${ok ? '✓' : '⚠'}</b><small>${c.role === 'text' ? t('Text') : t('Accent')}</small></span></span>`;
    }).join('')}</div>` : '';
  };
  paintCols();
  // the name and what the brand does (2026-10-25: Import from your website fills them too)
  const nm = $('#brname', main), ab = $('#brabout', main);
  nm.value = B.name; ab.value = B.about;
  nm.oninput = () => { B.name = nm.value; save(); };
  ab.oninput = () => { B.about = ab.value; save(); };
  // the fonts: titles and body text from the lab's font library (/fonts.css loads them), a line written in each
  const paintFonts = () => {
    const box = $('#brfonts', main);
    box.innerHTML = [['heading', t('Titles')], ['body', t('Body text')]].map(([k, l]) => `<div class="brfont"><span class="brfl">${l}</span>
        <select data-k="${k}"><option value="">${t('Auto - Claude picks')}</option>${FONTS.map(f => `<option${B.identity.fonts[k] === f ? ' selected' : ''}>${esc(f)}</option>`).join('')}</select>
        <span class="brfs" style="font-family: '${esc(B.identity.fonts[k] || 'inherit')}'">${esc(B.name || 'Aa Bb')} 123</span></div>`).join('');
    $$('select', box).forEach(s => s.onchange = () => { B.identity.fonts[s.dataset.k] = s.value; paintFonts(); save(); });
  };
  paintFonts();
  // the logo: a picture the user picks, copied to knowledge\local\brand\ (brand.save_logo checks it)
  const paintLogo = () => {
    const lg = B.identity.logo;
    $('#brlogoi', main).innerHTML = lg ? `<img src="${brandLogoSrc(lg, Date.now())}" alt="">` : '<svg class="i"><use href="#i-plus"/></svg>';
  };
  paintLogo();
  brandBand(main, B);
  $('.brlogo input', main).onchange = async e => {
    const f = e.target.files[0]; e.target.value = '';
    if (!f) return;
    if (f.size > 5e6) { toast(t('a logo up to 5 MB'), 'err'); return; }
    try {
      const r = await api('/api/brand/logo', {name: f.name, data: b64(await f.arrayBuffer())});
      B.identity.logo = (r.identity || {}).logo || ''; BRAND_DATA = LOGOS = null;
      paintLogo(); brandBand(main, {...r, updated: Date.now()}); say(t('saved ✓'), 'ok'); endSaved(r);
    } catch (err) { toast(err.message, 'err'); }
  };
  // the logo's versions (3f): on dark, on light, the icon alone - each its own tile (brand.save_logo kind), × = not used
  // (the file stays); where videos put the logo = one of four pills
  const paintLogos = () => {
    BRAND_LOGOS.forEach(([k]) => {
      const f = B.identity.logos[k], el = $(`.brlv[data-k="${k}"]`, main);
      $('.brlogoi', el).innerHTML = f ? `<img src="${brandLogoSrc(f, Date.now())}" alt="">` : '<svg class="i"><use href="#i-plus"/></svg>';
      $('.brx', el).hidden = !f;
    });
    $$('#brlwhere .brpill', main).forEach(b => b.classList.toggle('on', b.dataset.k === B.identity.logo_where));
  };
  paintLogos();
  $$('.brlv', main).forEach(el => {
    const k = el.dataset.k;
    $('input', el).onchange = async e => {
      const f = e.target.files[0]; e.target.value = '';
      if (!f) return;
      if (f.size > 5e6) { toast(t('a logo up to 5 MB'), 'err'); return; }
      try {
        const r = await api('/api/brand/logo', {name: f.name, data: b64(await f.arrayBuffer()), kind: k});
        B.identity.logos = {...B.identity.logos, ...((r.identity || {}).logos || {})}; BRAND_DATA = LOGOS = null;
        paintLogos(); say(t('saved ✓'), 'ok'); endSaved(r);
      } catch (err) { toast(err.message, 'err'); }
    };
    $('.brx', el).onclick = () => { B.identity.logos[k] = ''; paintLogos(); save(); };
  });
  $$('#brlwhere .brpill', main).forEach(b => b.onclick = () => { B.identity.logo_where = b.dataset.k; paintLogos(); save(); });
  // the signature end card (5c): Auto or a template, the sign-off line, and a live preview of the card as the server
  // fills it from My Brand (GET / POST /api/brand "_end" = brand.end_card(preview=True)); drawn once the Style tab shows
  let endLib = null, endTpl = null, endLive = null;
  async function paintEnd() {
    $$('#brends .brend1', main).forEach(b => b.classList.toggle('on', b.dataset.k === B.end_card.style));
    const box = $('#brendprev', main), E = B._end;
    if (!$('#brends', main).offsetParent) { endPending = true; return; }   // the Style tab hidden (the box hides when empty)
    endPending = false;
    if (!E) { if (endLive) endLive.stop(); endLive = null; endTpl = null; box.innerHTML = ''; return; }
    if (!endTpl || endTpl.id !== E.template) {
      endLib = endLib || await api('/api/motion').then(M => M.library || [], () => []);
      if (endLive) endLive.stop();
      endLive = null; endTpl = endLib.find(x => x.id === E.template) || null;
    }
    if (!endTpl) { box.innerHTML = ''; return; }
    if (endLive) endLive.refresh();
    else endLive = livePreview(box, endTpl, () => ({...mdefaults(endTpl), ...((B._end || {}).values || {})}));
  }
  function endSaved(r) {                                 // a save's answer: the card again when it changed
    if (!r || !('_end' in r) || JSON.stringify(r._end) === JSON.stringify(B._end)) return;
    B._end = r._end; paintEnd();
  }
  // what worked (3j): the hooks, endings and titles of what the user rated good (brand.worked, GET /api/brand
  // "_worked") - read only, each opens its prompt; none yet = where to rate
  const W = B._worked || {}, wk = [['hooks', t('Hook')], ['ctas', t('Ending')], ['titles', t('Title')]]
    .flatMap(([k, l]) => (W[k] || []).map(x => ({l, ...x})));
  $('#brworked', main).innerHTML = wk.length
    ? wk.map(x => `<a class="brwk" href="#/prompts/${encodeURIComponent(x.from)}"><small>${x.l}</small><span>${esc(x.text)}</span></a>`).join('')
    : `<div class="small muted">${t('Rate your scripts, titles and videos - the hooks and endings of the good ones show here, and Claude follows them.')}</div>`;
  // its sound (0.6.0 step 10): the template's own sound effects, or the brand's sound logo - made by ElevenLabs from
  // the user's words (a job: brand.py sound-logo) or a file they pick; the server owns the file (brand.save)
  let sndV = Date.now();
  const paintSound = () => {
    const has = !!B.identity.sound_logo, on = has && B.end_card.sound === 'logo', box = $('#brsnd', main);
    box.innerHTML = `<div class="brpills"><button class="brpill${on ? '' : ' on'}" data-snd="">${t("The template's own sounds")}</button>
        ${has ? `<button class="brpill${on ? ' on' : ''}" data-snd="logo"><span data-mhear="brand-sound" role="button" title="${ta('Listen')}">${MU_PLAYING === 'brand-sound' ? '❚❚' : '▶'}</span> ${t('Your sound logo')}</button>` : ''}</div>
      <div class="row brsndmk"><input type="text" id="brsndtxt" maxlength="400" value="${esc(B._sound_words || '')}" title="${ta('What it should sound like - ElevenLabs makes it from these words')}">
        <button class="btn sm" id="brsndgo"><svg class="i"><use href="#i-sparkle"/></svg>${has ? t('Make another') : t('Make one')}</button>
        <label class="btn sm"><svg class="i"><use href="#i-upload"/></svg>${t('Use a file…')}<input type="file" id="brsndf" hidden accept="audio/*,.wav,.mp3,.m4a,.ogg,.flac"></label></div>
      <div class="small muted" id="brsndst">${t('A short sound under your logo, the same at the end of every video. ElevenLabs makes it from your words (about 20 credits - your key from Motion Graphics > Sounds), or use your own file.')}</div>
      <pre class="log" id="brsndlog" hidden></pre>`;
    $$('[data-snd]', box).forEach(b => b.onclick = e => { if (e.target.closest('[data-mhear]')) return; B.end_card.sound = b.dataset.snd; paintSound(); save(true); });
    const hb = $('[data-mhear]', box);
    if (hb) hb.onclick = e => { e.stopPropagation(); muHear('brand-sound', hb, '/api/brand/sound_logo?v=' + sndV); };
    const fresh = r => { B.identity.sound_logo = (r.identity || {}).sound_logo || ''; B.end_card.sound = (r.end_card || {}).sound || '';
      sndV = Date.now(); paintSound(); endSaved(r); };
    $('#brsndgo', box).onclick = async () => {
      const text = $('#brsndtxt', box).value.trim(), pre = $('#brsndlog', box);
      if (text.length < 8) { toast(t('describe the sound logo in a few words'), 'err'); return; }
      $('#brsndgo', box).disabled = true; pre.hidden = false; $('#brsndst', box).textContent = t('Making it…');
      try { const j = await api('/api/brand/sound_logo/make', {text});
        followJob(j.id, pre, async r => { if (r.status === 'done') { fresh(await api('/api/brand')); toast(t('Your sound logo is ready - press ▶ to hear it'), 'ok'); }
          else { $('#brsndst', box).textContent = t('It did not finish - see the lines above.'); $('#brsndgo', box).disabled = false; } });
      } catch (e) { toast(e.message, 'err'); $('#brsndgo', box).disabled = false; }
    };
    $('#brsndf', box).onchange = async e => { const f = e.target.files[0]; e.target.value = ''; if (!f) return;
      try { const r = await new Promise((ok, bad) => { const x = new XMLHttpRequest();
          x.open('POST', `/api/brand/sound_logo?name=${encodeURIComponent(f.name)}`);
          x.setRequestHeader('X-ML-Token', TOKEN); x.setRequestHeader('Content-Type', 'application/octet-stream');
          x.onload = () => { let j = null; try { j = JSON.parse(x.responseText); } catch (er) { /* not JSON */ }
            if (x.status < 300) ok(j); else bad(new Error((j && j.error) || `${x.status}`)); };
          x.onerror = () => bad(new Error(t('{name}: the copy stopped - try again', {name: f.name}))); x.send(f); });
        fresh(r); say(t('saved ✓'), 'ok');
      } catch (er) { toast(er.message, 'err'); } };
  };
  paintSound();
  $$('#brends .brend1', main).forEach(b => b.onclick = () => { B.end_card.style = b.dataset.k; paintEnd(); save(true); });
  const endLine = $('#brendline', main);
  endLine.value = B.end_card.line || '';
  endLine.oninput = () => { B.end_card.line = endLine.value; save(); };
  paintEnd();
  // the tone of voice, a card of its own (2026-10-25, the user: "the tone of voice section needs to have more presence
  // as well because i didnt even realize its there"): quick words that add / take themselves out of the text, + the text
  const voice = $('#brvoice', main);
  voice.value = B.identity.voice || '';
  const toneWords = v => v.split(',').map(s => s.trim()).filter(Boolean);
  const paintTones = () => { const have = toneWords(voice.value).map(s => s.toLowerCase());
    $$('#brtones .brpill', main).forEach(b => b.classList.toggle('on', have.includes(b.dataset.w.toLowerCase()))); };
  $$('#brtones .brpill', main).forEach(b => b.onclick = () => {
    const w = b.dataset.w, list = toneWords(voice.value), i = list.findIndex(s => s.toLowerCase() === w.toLowerCase());
    if (i >= 0) list.splice(i, 1); else list.push(w);
    voice.value = list.join(', '); B.identity.voice = voice.value; paintTones(); save();
  });
  voice.oninput = () => { B.identity.voice = voice.value; paintTones(); save(); };
  // the voice in your own words (2026-10-26, the research's 3b): four sliders as five dots each (a second click = not
  // set), words you use / never use as chips, lines that sound like you - Claude imitates and checks against them
  const TN = B.identity.tone;
  const DIMS = [['casual', t('formal'), t('casual')], ['funny', t('serious'), t('funny')], ['cheeky', t('respectful'), t('cheeky')], ['excited', t('calm'), t('excited')]];
  const paintDims = () => {
    $('#brdims', main).innerHTML = DIMS.map(([k, lo, hi]) => `<div class="brdim"><span>${lo}</span><span class="brdimd">${[0, 1, 2, 3, 4].map(i =>
      `<button class="${TN.dims[k] === i ? 'on' : ''}${TN.dims[k] != null && i < TN.dims[k] ? ' trail' : ''}" data-k="${k}" data-v="${i}" title="${esc(lo)} ↔ ${esc(hi)}"></button>`).join('')}</span><span>${hi}</span></div>`).join('');
    $$('#brdims button', main).forEach(b => b.onclick = () => { const k = b.dataset.k, v = +b.dataset.v;
      TN.dims[k] = TN.dims[k] === v ? null : v; paintDims(); save(); });
  };
  paintDims();
  const chipList = (sel, arr, ph) => {
    const draw = (focus = false) => {
      const box = $(sel, main);
      box.innerHTML = arr.map(w => `<span class="brpill on brchip">${esc(w)}${x('Remove')}</span>`).join('')
        + (arr.length < 20 ? `<span class="braddin"><svg class="i"><use href="#i-plus"/></svg><input type="text" maxlength="40" placeholder="${esc(ph)}"></span>` : '');
      $$('.brx', box).forEach((b, i) => b.onclick = () => { arr.splice(i, 1); draw(); save(); });
      const inp = $('.braddin input', box);
      if (!inp) return;
      const add = () => { const v = inp.value.trim(); if (!v) return; inp.value = '';
        if (!arr.some(w => w.toLowerCase() === v.toLowerCase())) arr.push(v); draw(true); save(); };
      inp.onkeydown = e => { if (e.key === 'Enter') add(); };
      inp.onblur = add;
      if (focus) inp.focus();
    };
    draw();
  };
  chipList('#bruse', TN.use, t('Add a word you say'));
  chipList('#bravoid', TN.avoid, t('Add a word you never say'));
  const lines = $('#brlines', main);
  lines.value = TN.lines.join('\n');
  lines.oninput = () => { TN.lines = lines.value.split('\n').map(s => s.trim()).filter(Boolean).slice(0, 5); save(); };
  paintTones();
  // the website: saved when the address is finished
  const url = $('#brurl', main);
  url.value = (B.site.url || '').replace(/^https:\/\//, '');
  url.onchange = () => { B.site.url = url.value.trim(); save(true); };
  // Import from your website (2026-10-25, the user: "an option besides the 'your website' with a download icon that
  // 'imports data from your website' so if its a shop website it will pull the catalog data, descriptions, logos"):
  // the job brand_import (tools\brand.py import) reads the site, then brImportModal shows what it found and where each
  // thing would go - the user ticks what comes in
  // (2026-10-25, the user: "make the import from your website button a littel bit bigger ... add a progress bar and
  // make it so that if the job finishes while u are in another page u can still come back and import the info"): a
  // big button; the job is followed by brandImpWatch from anywhere (the bar + the stage under it); what it found waits
  // in the banner above the tabs (brandPendPaint) until it is imported or put aside
  const imp = $('#brimp', main), ist = $('#brimpst', main);
  ist.dataset.idle = B.site.read ? t('Imported {when} - import again to bring in what changed', {when: whenStr(B.site.read)})
    : t('Brings in your catalogue with prices and descriptions, your logo, colours, fonts and pages - you tick what goes in.');
  imp.onclick = async () => {
    const u = url.value.trim();
    if (!u) { toast(t('Type your website first'), 'err'); url.focus(); return; }
    B.site.url = u;
    try { await api('/api/brand', JSON.parse(JSON.stringify(B))); BRAND_DATA = null; } catch (e) { toast(e.message, 'err'); return; }
    let j;
    try { j = await api('/api/jobs', {kind: 'brand_import', args: {}, queue: true}); } catch (e) { toast(e.message, 'err'); return; }
    brandImpWatch(j.id);
  };
  brandImpPaint();
  if (!BRAND_IMP) api('/api/jobs').then(list => {                // an import started before (the app reloaded): follow it
    const j = (list || []).find(x => x.kind === 'brand_import' && ['running', 'queued', 'cancelling'].includes(x.status));
    if (j) brandImpWatch(j.id);
  }).catch(() => {});
  brandPendPaint();
  // your pages (2026-10-25): a row a platform - its logo, the link, a call to action; the link is checked as typed
  // (BRAND_PAGE_RX = siteread.SOCIAL) and saved only when it is that platform's page
  const paintPages = () => {
    const box = $('#brpages', main), add = $('#brpgadd', main);
    box.innerHTML = B.pages.map(pg => `<div class="brpage"><span class="brpgt">${brandPgLogo(pg.platform)}</span>
        <span class="brpt"><input type="url" class="brghost brpgu" maxlength="300" value="${esc(pg.url)}" placeholder="${ta('Link to your {platform} page', {platform: BRAND_PAGES[pg.platform]})}">
          <input type="text" class="brghost brpgc" maxlength="120" value="${esc(pg.cta || '')}" placeholder="${ta('Call to action, e.g. follow for a new video every week')}"></span>${x('Remove')}</div>`).join('');
    const free = Object.keys(BRAND_PAGES).filter(p => !B.pages.some(x => x.platform === p));
    add.innerHTML = free.length ? `<span class="small muted">${B.pages.length ? t('Add a page') : t('Add your pages: where you post')}</span>
      ${free.map(p => `<button class="brpgb" data-p="${p}" title="${esc(BRAND_PAGES[p])}">${brandPgLogo(p)}</button>`).join('')}` : '';
    $$('.brpage', box).forEach((row, i) => {
      const pg = B.pages[i], u = $('.brpgu', row);
      u.oninput = () => {
        const v = u.value.trim(), okv = !v || BRAND_PAGE_RX[pg.platform].test(v);
        u.classList.toggle('bad', !okv);
        if (okv) { pg.url = v; save(); }
      };
      $('.brpgc', row).oninput = e => { pg.cta = e.target.value; save(); };
      $('.brx', row).onclick = () => { B.pages.splice(i, 1); paintPages(); save(); };
    });
    $$('.brpgb', add).forEach(b => b.onclick = () => {
      B.pages.push({platform: b.dataset.p, url: '', cta: ''}); paintPages();
      const us = $$('.brpgu', box); if (us.length) us[us.length - 1].focus();
    });
  };
  paintPages();
  // content pillars (2026-10-26, the research's 3h): a row each - the theme, what it is, a recurring series (optional)
  const paintPils = (focus = false) => {
    const box = $('#brpils', main);
    box.innerHTML = B.pillars.map(p => `<div class="brpil"><span class="brpt"><input type="text" class="brghost brpln" maxlength="60" value="${esc(p.name)}" placeholder="${ta('e.g. Behind the scenes')}">
        <input type="text" class="brghost brplw" maxlength="160" value="${esc(p.what || '')}" placeholder="${ta('What it is about')}">
        <input type="text" class="brghost brpls" maxlength="80" value="${esc(p.series || '')}" placeholder="${ta('A series, if any - e.g. Day N on set')}"></span>${x('Remove')}</div>`).join('');
    $$('.brpil', box).forEach((row, i) => { const p = B.pillars[i];
      $('.brpln', row).oninput = e => { p.name = e.target.value; save(); };
      $('.brplw', row).oninput = e => { p.what = e.target.value; save(); };
      $('.brpls', row).oninput = e => { p.series = e.target.value; save(); };
      $('.brx', row).onclick = () => { B.pillars.splice(i, 1); paintPils(); save(); }; });
    $('#brpiladd', main).hidden = B.pillars.length >= 6;
    if (focus) { const n = $$('.brpln', box); if (n.length) n[n.length - 1].focus(); }
  };
  paintPils();
  $('#brpiladd', main).onclick = () => { B.pillars.push({name: '', what: '', series: ''}); paintPils(true); };
  // names and words (2026-10-25, the user's pick "Glossary"): spelled exactly in captions, scripts and titles; a word
  // + how it is said (optional); Enter adds it
  const paintGloss = (focus = false) => {
    const box = $('#brgloss', main);
    box.innerHTML = B.glossary.map(g => `<span class="brpill on brchip"><b>${esc(g.word)}</b>${g.say ? `<small>${t('said “{say}”', {say: esc(g.say)})}</small>` : ''}${x('Remove')}</span>`).join('')
      + (B.glossary.length < 60 ? `<span class="braddin brgladd"><svg class="i"><use href="#i-plus"/></svg><input type="text" class="brgw" maxlength="40" placeholder="${ta('Add a name or word')}">
          <input type="text" class="brgs" maxlength="60" placeholder="${ta('said like (optional)')}"></span>` : '');
    $$('.brx', box).forEach((b, i) => b.onclick = () => { B.glossary.splice(i, 1); paintGloss(); save(); });
    const w = $('.brgw', box), s = $('.brgs', box);
    if (!w) return;
    const add = () => { const v = w.value.trim(); if (!v) return;
      if (!B.glossary.some(g => g.word.toLowerCase() === v.toLowerCase())) B.glossary.push({word: v, say: s.value.trim()});
      paintGloss(true); save(); };
    [w, s].forEach(inp => inp.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); add(); } });
    if (focus) w.focus();
  };
  paintGloss();
  // your latest videos (the Overview; the user, 2026-10-25: "should only appear videos u marked as 'for my brand' when
  // creating them"): this PC's videos made For my brand, with a render, the newest first - a click opens it
  api('/api/projects').then(ps => {
    const box = $('#brmine', main); if (!box) return;
    const vids = (ps || []).filter(p => p.latest && p.for_brand).sort((a, b) => b.sort_t - a.sort_t).slice(0, 10);
    box.innerHTML = vids.length ? vids.map(p => `<a class="brvid" href="#/project/${encodeURIComponent(p.name)}">
        <span class="nerefp">${p.picture ? `<img src="${picUrl(p.picture)}" loading="lazy" alt="">` : ''}<i>${esc(lenWords(p.latest.frames, p.latest.fps) || '')}</i></span>
        <b>${esc(pname(p))}</b><span class="small muted">${esc(whenWords(p.latest.mtime))}</span></a>`).join('')
      : `<div class="small muted">${t('No videos made For my brand yet - tick For my brand when you make one (New edit, the Generator).')}</div>`;
  }).catch(() => {});
  // the caption style (2026-10-25, the user's pick from the research: "captions are on every short"): a ready look +
  // the brand's choices on top, a live 9:16 preview (the look's numbers = the captions graphic's presets.json);
  // `overlay.py captions --brand` makes them so (Claude's briefs, Graphics > Captions)
  const CP = B.identity.captions;
  const eff = () => { const L = CAPTION_LOOK[CP.look || 'classic'];
    return {font: CP.font || L.font, weight: L.weight, upper: CP.case ? CP.case === 'upper' : L.upper, color: CP.color || L.color,
            hl: CP.highlight || L.hl, motion: L.motion === 'keyword' ? 'keyword' : CP.motion || L.motion, kfont: L.kfont, kscale: L.kscale,
            y: CP.position ? CAPTION_POS[CP.position] : L.y,
            box: CP.box != null ? CP.box : L.box, outline: L.outline, size: L.size * (CAP_SIZE[CP.size] || 1), boxc: L.boxc,
            words: +CP.words || 0}; };
  const pills = (key, opts) => `<div class="brpills">${opts.map(([v, l]) => `<button class="brpill" data-ck="${key}" data-cv="${v}">${l}</button>`).join('')}</div>`;
  const swatch = key => `<span class="brcapsw"><label class="brswatch" data-csw="${key}"><input type="color" data-cc="${key}"></label>
      <span class="brcapdots">${B.identity.colours.map(c => `<i data-cdot="${key}" data-hex="${esc(c.hex)}" style="background:${esc(c.hex)}" title="${esc(c.name || c.hex)}"></i>`).join('')}</span></span>`;
  $('#brcapc', main).innerHTML = `
    <div class="brcrow"><span class="brfl">${t('Look')}</span>${pills('look', [['classic', t('Classic')], ['clean_box', t('Clean box')], ['keyword', t('Keyword')]])}</div>
    <div class="brcrow"><span class="brfl">${t('Font')}</span><select id="brcapf"><option value="">${t('The look\'s own')}</option>${FONTS.map(f => `<option>${esc(f)}</option>`).join('')}</select></div>
    <div class="brcrow"><span class="brfl">${t('Letters')}</span>${pills('case', [['upper', t('CAPITALS')], ['sentence', t('Sentence case')]])}</div>
    <div class="brcrow"><span class="brfl">${t('Colours')}</span><span class="brcapcols"><span><span class="small muted">${t('Text')}</span>${swatch('color')}</span>
      <span><span class="small muted">${t('Spoken word')}</span>${swatch('highlight')}</span></span></div>
    <div class="brcrow"><span class="brfl">${t('Motion')}</span>${pills('motion', [['highlight', t('Word lights up')], ['pop', t('Words pop in')], ['line', t('Whole line')]])}</div>
    <div class="brcrow"><span class="brfl">${t('Position')}</span>${pills('position', [['top', t('Top')], ['middle', t('Middle')], ['bottom', t('Bottom')]])}</div>
    <div class="brcrow"><span class="brfl">${t('Words per line')}</span>${pills('words', [1, 2, 3, 4, 6].map(n => [String(n), String(n)]))}</div>
    <div class="brcrow"><span class="brfl">${t('Size')}</span>${pills('size', [['s', t('Small')], ['m', t('Medium')], ['l', t('Large')], ['xl', t('Huge')]])}</div>
    <div class="brcrow"><span class="brfl">${t('Box behind')}</span><label class="brsw"><input type="checkbox" id="brcapbox"><i></i></label></div>`;
  const capWords = (B.name ? `${B.name} - ${t('This is how your captions look')}` : t('This is how your captions look')).split(/\s+/);
  let capI = 0;
  const paintCap = () => {
    const e = eff(), box = $('#brcapc', main), sc = 240 / 1080, l = $('#brcapl', main);
    $$('[data-ck]', box).forEach(b => b.classList.toggle('on', String(CP[b.dataset.ck] || '') === b.dataset.cv));
    $('#brcapf', box).value = CP.font || '';
    $('#brcapbox', box).checked = e.box;
    ['color', 'highlight'].forEach(k => { const h = k === 'color' ? e.color : e.hl;
      $(`[data-csw=${k}]`, box).style.background = h; $(`[data-cc=${k}]`, box).value = h;
      $$(`[data-cdot=${k}]`, box).forEach(d => d.classList.toggle('on', d.dataset.hex === (CP[k] || ''))); });
    $('#brcapclr', main).hidden = !Object.values(CP).some(v => v !== '' && v != null && v !== 0);
    Object.assign(l.style, {top: e.y + '%', fontFamily: `'${e.font}'`, fontWeight: e.weight, fontSize: (e.size * sc).toFixed(1) + 'px',
      textTransform: e.upper ? 'uppercase' : 'none', color: e.color, WebkitTextStroke: e.outline ? `${(e.outline * sc * 2).toFixed(1)}px #000` : '0',
      background: e.box ? e.boxc : 'transparent', padding: e.box ? '4px 8px' : '0'});
    const n = e.words || capWords.length, at = capI % capWords.length, from = Math.floor(at / n) * n;   // words a line (3c)
    if (e.motion === 'keyword') {                          // the Keyword look: small words, the longest one big under them
      const ws = capWords.slice(from, from + Math.max(2, Math.min(n, 3))), k = ws.reduce((b, w, i) => w.length >= ws[b].length ? i : b, 0);
      l.innerHTML = `<span>${ws.filter((_, i) => i !== k).map(esc).join(' ')}</span><br><span style="font-family:'${esc(e.kfont)}',Georgia,serif;font-style:italic;font-weight:400;text-transform:none;color:${esc(e.hl)};font-size:${(e.size * e.kscale * sc).toFixed(1)}px;line-height:1">${esc(ws[k])}</span>`;
      return;
    }
    l.innerHTML = capWords.map((w, i) => i < from || i >= from + n ? '' : `<span class="${e.motion === 'highlight' && i === capI % capWords.length ? 'hl' : ''}${e.motion === 'pop' && i > capI % capWords.length ? ' gone' : ''}"
      style="${e.motion === 'highlight' && i === capI % capWords.length ? `color:${e.hl}` : ''}">${esc(!e.upper && !i ? w[0].toUpperCase() + w.slice(1) : w)}</span>`).filter(Boolean).join(' ');
  };
  const setCap = (k, v) => { CP[k] = v; paintCap(); save(); };
  $$('#brcapc [data-ck]', main).forEach(b => b.onclick = () => setCap(b.dataset.ck, String(CP[b.dataset.ck] || '') === b.dataset.cv ? '' : b.dataset.cv));
  $('#brcapf', main).onchange = e => setCap('font', e.target.value);
  $('#brcapbox', main).onchange = e => setCap('box', e.target.checked);
  $$('#brcapc [data-cc]', main).forEach(c => c.oninput = () => setCap(c.dataset.cc, c.value.toLowerCase()));
  $$('#brcapc [data-cdot]', main).forEach(d => d.onclick = () => setCap(d.dataset.cdot, CP[d.dataset.cdot] === d.dataset.hex ? '' : d.dataset.hex));
  $('#brcapclr', main).onclick = () => { Object.assign(CP, {look: '', font: '', case: '', color: '', highlight: '', motion: '', position: '', box: null, words: 0, size: ''}); paintCap(); save(); };
  paintCap();
  const capTimer = setInterval(() => { if (!$('#brcapl', main)) { clearInterval(capTimer); return; } capI++; paintCap(); }, 520);
  onCleanup(() => clearInterval(capTimer));
  // your editing look (2026-10-25, the user's pick from the research; on the Overview "with some videos previewing"):
  // this PC's analysed videos as a strip of picture cards, the picked ones first, up to 3
  loadStyles().then(S => {
    const vids = ownVideos(S), box = $('#brlook', main), qi = $('#brlookq', main);
    vids.sort((a, b) => B.look.like.includes(b.key) - B.look.like.includes(a.key));
    let q = '';
    qi.hidden = vids.length <= 8;
    const draw = () => {
      $('#brlookn', main).textContent = `${B.look.like.length} / 3`;
      const list = vids.filter(v => !q || [v.label, v.title, v.key, v.by, v.platform].join(' ').toLowerCase().includes(q));
      box.innerHTML = vids.length ? list.map(v => { const on = B.look.like.includes(v.key), full = !on && B.look.like.length >= 3,
        dur = (String(v.format || '').split(' · ')[1] || '').trim();
        return `<button class="brvid${on ? ' on' : ''}" data-k="${esc(v.key)}" ${full ? 'disabled' : ''} title="${esc(v.line || v.summary || v.label || v.key)}">
          <span class="nerefp">${v.picture ? `<img src="${fileUrl(v.picture)}" loading="lazy" alt="">` : ''}${dur ? `<i>${esc(dur)}</i>` : ''}${on ? '<em>✓</em>' : ''}</span>
          <b>${esc(v.label || v.title || v.key)}</b></button>`; }).join('') || `<div class="small muted">${t('No video matches.')}</div>`
        : `<div class="small muted">${t('No video analysed on this PC yet - add one in the <a href="#/analyze" onclick="closeModal()">Analyser</a>.')}</div>`;
      $$('.brvid', box).forEach(b => b.onclick = () => { const k = b.dataset.k;
        B.look.like = B.look.like.includes(k) ? B.look.like.filter(x => x !== k) : [...B.look.like, k].slice(0, 3); draw(); save(); });
    };
    qi.oninput = debounce(() => { q = qi.value.trim().toLowerCase(); draw(); }, 150);
    draw();
  }).catch(() => { /* the card stays empty */ });
  // the catalogue (2026-10-25, the user: "the 'add a product' in the catalogue should be at the top for convinience and
  // make the catalogeu section more cool, like why does it say 'cataloge' if im already on a tab called 'catalogue'"):
  // the tab is the title; on top Add a product (the new one comes first), the count and a search; the products as
  // cards - the picture (a click picks one), name, what it is, price, the link, "In videos"; a product needs a name
  // (one without is not kept)
  const nextId = () => 'p' + (Math.max(0, ...B.catalogue.map(p => +String(p.id || '').slice(1) || 0)) + 1);
  // a product's facts and media (5b, 2026-10-26: "so Claude never invents a feature or a price"): its key benefit, the
  // claims it may make (each with its proof), the ones never to make, screenshots / short screen recordings (POST
  // /api/brand/product_media = brand.save_product_media; × = not used, the file stays) - a dialog; Back = the catalogue
  const prodCount = p => { const n = (p.benefit ? 1 : 0) + (p.claims || []).length + (p.never || []).length, m = (p.media || []).length;
    return n || m ? ` <span class="brpcn">${[n && plural(n, 'fact'), m && plural(m, 'file')].filter(Boolean).join(' · ')}</span>` : ''; };
  const prodFacts = p => {
    p.claims = p.claims || []; p.never = p.never || []; p.media = p.media || [];
    modal(`<div class="brfacts"><h2>${esc(p.name)}</h2>
      <div class="brsub">${t('Key benefit')}</div>
      <input type="text" id="pfben" maxlength="120" value="${esc(p.benefit || '')}" placeholder="${ta('The one thing it does for the viewer, e.g. A music video shot like a film in one day')}">
      <div class="brsub">${t('Claims Claude may make')}</div><div id="pfclaims"></div>
      <div class="brsub">${t('Never claim')}</div><div class="brpills" id="pfnever"></div>
      <div class="brsub">${t('Screenshots and recordings')}</div><div class="pfmedia" id="pfmedia"></div></div>`, el => {
      $('#pfben', el).oninput = e => { p.benefit = e.target.value; save(); };
      const paintClaims = (focus = false) => {
        const box = $('#pfclaims', el);
        box.innerHTML = p.claims.map((c, i) => `<div class="pfclaim" data-i="${i}"><input type="text" class="pfct" maxlength="120" value="${esc(c.text)}" placeholder="${ta('A claim, e.g. Delivered in 7 days')}">
            <input type="text" class="pfcp" maxlength="160" value="${esc(c.proof || '')}" placeholder="${ta('Its proof, e.g. every 2026 order shipped in 7 days')}">${x('Remove')}</div>`).join('')
          + (p.claims.length < 5 ? `<button class="btn sm ghost" id="pfcadd"><svg class="i"><use href="#i-plus"/></svg>${t('Add a claim')}</button>` : '');
        $$('.pfclaim', box).forEach(row => { const c = p.claims[+row.dataset.i];
          $('.pfct', row).oninput = e => { c.text = e.target.value; save(); };
          $('.pfcp', row).oninput = e => { c.proof = e.target.value; save(); };
          $('.brx', row).onclick = () => { p.claims.splice(+row.dataset.i, 1); paintClaims(); save(); }; });
        const add = $('#pfcadd', box);
        if (add) add.onclick = () => { p.claims.push({text: '', proof: ''}); paintClaims(true); };
        if (focus) { const all = $$('.pfct', box); if (all.length) all[all.length - 1].focus(); }
      };
      paintClaims();
      const paintNever = (focus = false) => {
        const box = $('#pfnever', el);
        box.innerHTML = p.never.map(w => `<span class="brpill on brchip">${esc(w)}${x('Remove')}</span>`).join('')
          + (p.never.length < 6 ? `<input type="text" class="brghost brpillin" maxlength="80" placeholder="${ta('e.g. the best in Spain')}">` : '');
        $$('.brchip', box).forEach((c, i) => { $('.brx', c).onclick = () => { p.never.splice(i, 1); paintNever(); save(); }; });
        const inp = $('.brpillin', box);
        if (inp) {
          const add = () => { const v = inp.value.trim(); if (v && !p.never.includes(v)) { p.never.push(v); save(); } paintNever(true); };
          inp.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); add(); } };
          inp.onblur = () => { if (inp.value.trim()) add(); };
          if (focus) inp.focus();
        }
      };
      paintNever();
      const paintMedia = () => {
        const box = $('#pfmedia', el);
        box.innerHTML = p.media.map((m, i) => `<span class="pfm" data-i="${i}">${/\.(mp4|mov|webm)$/i.test(m)
            ? `<video src="${fileUrl(m)}" muted loop playsinline preload="metadata"></video>` : `<img src="${fileUrl(m)}" alt="">`}${x('Remove')}</span>`).join('')
          + (p.media.length < 6 ? `<label class="pfm add" title="${ta('A screenshot (PNG, JPG, WebP) or a short screen recording (MP4, MOV, WebM, up to 30 MB)')}"><input type="file" accept=".png,.jpg,.jpeg,.webp,.mp4,.mov,.webm" hidden><svg class="i"><use href="#i-plus"/></svg></label>` : '');
        $$('.pfm[data-i]', box).forEach(s => { $('.brx', s).onclick = () => { p.media.splice(+s.dataset.i, 1); paintMedia(); save(); };
          const v = $('video', s); if (v) { s.onmouseenter = () => v.play().catch(() => {}); s.onmouseleave = () => v.pause(); } });
        const inp = $('.pfm.add input', box);
        if (inp) inp.onchange = async e => {
          const f = e.target.files[0]; e.target.value = '';
          if (!f) return;
          if (f.size > 30e6) { toast(t('a recording up to {n} MB', {n: 30}), 'err'); return; }
          try {
            clearTimeout(timer); await queue;
            await api('/api/brand', JSON.parse(JSON.stringify(B)));          // the product's facts on disk first
            const r = await api('/api/brand/product_media', {id: p.id, name: f.name, data: b64(await f.arrayBuffer())});
            p.media = ((r.catalogue || []).find(q => q.id === p.id) || {}).media || p.media; BRAND_DATA = null;
            paintMedia(); say(t('saved ✓'), 'ok');
          } catch (err) { toast(err.message, 'err'); }
        };
      };
      paintMedia();
    });
    modalBack(() => paintProds());
  };
  let cq = '';
  const catN = () => {
    const n = B.catalogue.length, on = B.catalogue.filter(p => p.use !== false && p.name.trim()).length;
    $('#brcatn', main).textContent = n || '';
    $('#brcatsum', main).textContent = n ? `${tn(n, '{n} product', '{n} products')} · ${t('{n} in videos', {n: on})}` : '';
    $('#brcatq', main).hidden = n <= 8;
  };
  const paintProds = (focus = null) => {
    const box = $('#brprods', main);
    const shown = B.catalogue.map((p, i) => [p, i]).filter(([p]) => !cq || `${p.name} ${p.what || ''} ${p.price || ''}`.toLowerCase().includes(cq));
    box.innerHTML = B.catalogue.length ? shown.map(([p, i]) => `<div class="brpc${p.use === false ? ' off' : ''}" data-i="${i}">
        <label class="brpcimg" title="${ta('Click to pick its picture - a PNG, JPG, WebP or SVG picture')}"><input type="file" accept=".png,.jpg,.jpeg,.webp,.svg" hidden>
          ${p.image ? `<img src="${fileUrl(p.image)}?v=${esc(B.updated || '')}" alt="">` : `<span class="brpcph"><svg class="i"><use href="#i-box"/></svg><small>${t('Add a picture')}</small></span>`}</label>
        ${x('Remove')}
        <div class="brpcb"><input type="text" class="brghost brpn" maxlength="80" value="${esc(p.name)}" placeholder="${ta('Product name')}">
          <input type="text" class="brghost brpw" maxlength="160" value="${esc(p.what || '')}" placeholder="${ta('What it is')}">
          ${p.url ? `<a class="brplink" href="${esc(p.url)}" target="_blank" rel="noopener" title="${esc(p.url)}">${esc(p.url.replace(/^https?:\/\/(www\.)?/, ''))}</a>` : ''}
          <div class="brpcf"><input type="text" class="brghost brpp" maxlength="24" value="${esc(p.price || '')}" placeholder="${ta('Price')}">
            <label class="brpcuse" title="${ta('Claude may use it in your videos')}"><span>${t('In videos')}</span><span class="brsw"><input type="checkbox"${p.use !== false ? ' checked' : ''}><i></i></span></label></div>
          <div class="brpcx"><input type="text" class="brghost brpromo" maxlength="40" value="${esc(p.promo || '')}" placeholder="${ta('Promo code')}">
            <label class="brpcad" title="${ta('A paid partnership - Claude says it is an ad, on screen and in words')}"><input type="checkbox"${p.sponsored ? ' checked' : ''}>${t('Paid partnership')}</label></div>
          <button class="btn sm ghost brpcmore" title="${ta('What Claude may say about it, what it must never claim, and your screenshots or recordings of it')}"><svg class="i"><use href="#i-clipboard"/></svg>${t('Facts & media')}${prodCount(p)}</button></div></div>`).join('')
        || `<div class="small muted brnone">${t('No product matches.')}</div>`
      : `<div class="brcatempty"><svg class="i"><use href="#i-bag"/></svg><b>${t('No products yet')}</b>
          <span class="small muted">${t('Add the ones Claude may show in your videos - or import them from your website (Overview).')}</span></div>`;
    $$('.brpc', box).forEach(card => {
      const i = +card.dataset.i, p = B.catalogue[i];
      $('.brpn', card).oninput = e => { p.name = e.target.value; catN(); save(); };
      $('.brpw', card).oninput = e => { p.what = e.target.value; save(); };
      $('.brpp', card).oninput = e => { p.price = e.target.value; save(); };
      $('.brpcuse input', card).onchange = e => { p.use = e.target.checked; card.classList.toggle('off', !p.use); catN(); save(); };
      $('.brpromo', card).oninput = e => { p.promo = e.target.value; save(); };
      $('.brpcad input', card).onchange = e => { p.sponsored = e.target.checked; save(); };
      $('.brx', card).onclick = () => { B.catalogue.splice(i, 1); paintProds(); catN(); save(); };
      $('.brpcmore', card).onclick = () => {
        if (!p.name.trim()) { toast(t('Give the product a name first'), 'err'); return; }
        prodFacts(p);
      };
      $('.brpcimg input', card).onchange = async e => {        // its picture: saved as its own file, checked like the logo
        const f = e.target.files[0]; e.target.value = '';
        if (!f) return;
        if (f.size > 5e6) { toast(t('a picture up to 5 MB'), 'err'); return; }
        try {
          clearTimeout(timer); await queue;
          if (!p.name.trim()) { toast(t('Give the product a name first'), 'err'); return; }
          await api('/api/brand', JSON.parse(JSON.stringify(B)));            // the product exists on disk first
          const r = await api('/api/brand/product_image', {id: p.id, name: f.name, data: b64(await f.arrayBuffer())});
          p.image = ((r.catalogue || []).find(x => x.id === p.id) || {}).image || ''; B.updated = r.updated; BRAND_DATA = null;
          paintProds(); say(t('saved ✓'), 'ok');
        } catch (err) { toast(err.message, 'err'); }
      };
    });
    if (focus != null) { const n = $(`.brpc[data-i="${focus}"] .brpn`, box); if (n) n.focus(); }
  };
  paintProds();
  catN();
  $('#brcatq', main).oninput = debounce(e => { cq = e.target.value.trim().toLowerCase(); paintProds(); }, 150);
  $('#bradd', main).onclick = () => {
    if (B.catalogue.length >= 200) return;
    B.catalogue.unshift({id: nextId(), name: '', what: '', price: '', use: true});   // the new one first
    cq = ''; $('#brcatq', main).value = '';
    paintProds(0); catN();
  };
}
