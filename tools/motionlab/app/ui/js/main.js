/* MotionLab app - js/main.js: the app starts here, after every other file has run.
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';

// the pages and their addresses (from core.js: the table names every page's function, so it is built after
// they all exist; route() reads it)
const PAGES = [
  [/^#?\/?$/, pageHome, 'home'], [/^#\/analyze(?:\/(videos|spark|notes|thumbs|texts))?$/, pageRefs, 'analyze'],
  [/^#\/note\/([^/?]+)(?:\/(\d+))?$/, pageNote, 'analyze'], [/^#\/spark\/([^/?]+)(?:\/(\d+))?$/, pageSpark, 'analyze'], [/^#\/notes-combined\/([^/?]+)$/, pageCombined, 'analyze'],
  [/^#\/texts\/([^/?]+)$/, pageTexts, 'analyze'],
  [/^#\/ref\/([^/?]+)(?:\?(?:e=(\w+)|(misses)|(verdicts)))?$/, pageRef, 'analyze'], [/^#\/edit$/, pageProjects, 'edit'],
  [/^#\/thumbs\/([^/?]+)$/, pageThumbs, 'analyze'],
  [/^#\/project\/([^/]+)(?:\/(\w+))?$/, pageProject, 'edit'], [/^#\/prepare$/, pagePrepare, 'prepare'],
  [/^#\/generate$/, pageGenerate, 'generate'], [/^#\/motion(?:\/(\w+))?(?:\/([\w-]+))?$/, pageMotion, 'motion'],
  [/^#\/prompts(?:\/([\w-]+))?$/, pagePrompts, 'generate'], [/^#\/memory(?:\/(\w+))?$/, pageMemory, 'memory'],
  [/^#\/brand(?:\/(style|catalogue))?$/, pageBrand, 'brand'], [/^#\/agency(?:\/(videos|tests|learn|month))?$/, pageAgency, 'agency'],
  [/^#\/jobs(?:\/(\d+))?$/, pageJobs, 'jobs'], [/^#\/storage$/, pageStorage, 'settings'],
  [/^#\/settings$/, pageSettings, 'settings'], [/^#\/skills$/, pageSkills, 'settings']];

// the live pages and the heartbeat (from core.js; ping() calls Home's and the Editor's functions)
setInterval(liveTick, 5000);
setInterval(ping, 4000); ping();

// the font list for every font picker (from video-publish.js; it reads My Brand's fonts)
Promise.all([api('/api/fonts'), Promise.resolve().then(brandData)]).then(([f]) => {   // brandData after the script ran (BRAND_DATA)
  FONTS = f;
  $$('select[data-font]').forEach(sel => { const v = sel.value; sel.innerHTML = fontOptions({id: sel.dataset.set, type: 'enum', value: v, options: [...sel.options].map(o => ({value: o.value, label: o.textContent}))}); });
}).catch(() => {});

// the first page, and what an open window follows from the start (from the end of app.js)
route();
// My Brand's website import (0.6.0): one still running is followed from any page; one not imported yet = the dot
api('/api/jobs').then(list => { const j = (list || []).find(x => x.kind === 'brand_import' && ['running', 'queued'].includes(x.status));
  if (j) brandImpWatch(j.id); }).catch(() => {});
brandPendPaint();
// after an update the restarted window shows once what came in (the CHANGELOG sections between the two versions)
api('/api/update').then(u => { const r = u && u.result; if (r && r.updated && !r.seen) whatsNewModal(r); }).catch(() => {});
