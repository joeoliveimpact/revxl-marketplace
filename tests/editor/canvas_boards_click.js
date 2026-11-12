// node tests/editor/canvas_boards_click.js <puppeteer-core.js> <chrome> <job.json>
// Drives the Beat Map and Sketches boards for canvas_boards_test.py. job = {url, userDataDir, actions:[...]}:
//   {do: "goto", url?}            open url (default job.url), wait for #status[data-state]
//   {do: "wait", sel, visible?}   wait for a selector
//   {do: "select", sel, value}    page.select (fires change)
//   {do: "type", sel, text}       clear with Ctrl+A, Backspace, then page.type
//   {do: "click", sel}
//   {do: "waitState", state, change?}  wait for #status[data-state=<state>]; change: first give the page up
//                                 to 1 s to leave its current state (so a stale "saved" can't pass)
//   {do: "read"}                  push the DOM facts below onto reads
//   {do: "readJson", path}        snapshot a saved JSON file after a completed save
//   {do: "readExists", path}      snapshot whether a file exists
// Prints {reads, errors} as JSON. On a timeout or error: also {error, last} and exit code 1.
"use strict";
const fs = require("fs");
const {pathToFileURL} = require("url");

function readPage() {
  const q = (s, r) => (r || document).querySelector(s);
  const all = (s) => [...document.querySelectorAll(s)];
  const val = (el) => (el ? el.value : null);
  const st = q("#status");
  return {
    empty: !!q("#empty") && q("#empty").checkVisibility(),
    status: st ? {state: st.getAttribute("data-state"), text: st.textContent.trim()} : null,
    timeline: all("#timeline .tl-beat").map(e => ({beat:e.dataset.beat, number:q('.tl-number', e).textContent,
      time:q('.tl-time', e).textContent, label:e.getAttribute('aria-label'), sketch:q('[role=img]', e).getAttribute('aria-label'),
      current:e.getAttribute('aria-current'), flagged:!!q('.flag-dot', e)})),
    timelineRole: q('#timeline')?.getAttribute('role'),
    strongBeats: all('#timeline .strong-beat-mark').map(e => ({time:e.dataset.timeS,
      role:e.getAttribute('role'), hidden:e.getAttribute('aria-hidden'), title:e.title,
      label:e.getAttribute('aria-label'), owner:e.closest('button').getAttribute('aria-label')})),
    focus: q('#focus-h')?.textContent,
    focusText: q('#focus')?.textContent,
    reason: q('.flag-reason')?.textContent || null,
    progress: q('#review-progress')?.textContent,
    active: document.activeElement?.id,
    activeBeat: document.activeElement?.matches('.tl-beat') ? document.activeElement.dataset.beat : null,
    moreOpen: q('#more')?.open,
    punchinNote: q('#punchin-layout-note') ? !q('#punchin-layout-note').hidden : null,
    rows: all("#focus[data-beat]").map((tr) => ({
      beat: tr.dataset.beat, layout: q('.layout-choice[aria-pressed=true]', tr)?.dataset.layout, value: val(q("input[name=value]", tr)),
      valueInvalid: q('input[name=value]', tr)?.getAttribute('aria-invalid'),
      valueError: q('input[name=value] + .err', tr)?.checkVisibility(),
      brollStart: val(q('input[name=broll-start]', tr)),
      brollInvalid: q('input[name=broll-start]', tr)?.getAttribute('aria-invalid'),
      brollError: q('.broll-controls .err', tr)?.checkVisibility(),
      note: val(q("textarea[name=note]", tr)), changed: tr.classList.contains("changed")})),
    marks: Object.fromEntries(all("#focus span.word[data-w]").map((s) => [s.dataset.w, s.getAttribute("data-mark")])),
    needs: val(q("#needs")),
    reminder: q('#reminder-enabled') ? {
      enabled: q('#reminder-enabled').checked, label: q('#reminder-enabled').parentElement.textContent.trim(),
      keyword: val(q('#reminder-keyword')), at: val(q('#reminder-at')), hold: val(q('#reminder-hold')),
      hint: q('#reminder-pick-note') && !q('#reminder-pick-note').hidden ? q('#reminder-pick-note').textContent : '',
      outside: q('#reminder-note') && !q('#reminder-note').hidden ? q('#reminder-note').textContent : '',
    } : null,
    scenes: all('.scene-controls').map(e => ({beat:e.dataset.beat,
      choices:[...e.querySelectorAll('.scene-choice')].map(c=>({id:c.dataset.scene, disabled:c.disabled, text:c.textContent}))})),
    directions: all("#directions section.direction[data-id]").map((s) => ({
      id: s.dataset.id, picked: s.classList.contains("picked"),
      checked: !!q("input[type=radio][name=pick]:checked", s), note: val(q("textarea[name=note]", s))})),
    sketches: all("#sketches article.sketch[data-id]").map((a) => ({id: a.dataset.id, note: val(q("textarea[name=note]", a))})),
    note: val(q("#note")),
    send: q("#send") ? {disabled: q("#send").disabled, loading: !!q("#send [data-loading]")} : null,
    lock: q("#lock") ? {disabled: q("#lock").disabled} : null,
    locked: !!q("#directions") && q("#directions").classList.contains("locked"),
    localStorage: localStorage.length,
    focusLayout: q('#focus .focus-columns') ? (() => {
      const rect = s => {
        const r = q(s).getBoundingClientRect();
        return {left:r.left, right:r.right, top:r.top, bottom:r.bottom, width:r.width};
      };
      return {sketch:rect('#focus .focus-sketch .sketch'), meta:rect('#focus .focus-meta'),
        columns:rect('#focus .focus-columns'),
        pickerBottom:rect('#focus .layout-picker').bottom + scrollY,
        usableHeight:q('.bar').getBoundingClientRect().top,
        rest:[...q('#focus .focus-content').children].filter(e => !e.matches('.focus-meta') && e.checkVisibility())
          .map(e => { const r=e.getBoundingClientRect(); return {left:r.left, right:r.right, top:r.top}; })};
    })() : null,
    narrow: {
      width: innerWidth, pageFits: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      notesVisible: all('#focus textarea[name=note]').every(e => {
        const r=e.getBoundingClientRect(); return r.width > 0 && r.left >= 0 && r.right <= innerWidth;
      }),
    },
  };
}

(async () => {
  const [pup, chrome, jobPath] = process.argv.slice(2);
  const job = JSON.parse(fs.readFileSync(jobPath, "utf8"));
  const {default: puppeteer} = await import(pathToFileURL(pup).href);
  const browser = await puppeteer.launch({executablePath: chrome, headless: "shell", args: ["--no-sandbox"],
                                          userDataDir: job.userDataDir, defaultViewport: job.viewport || {width: 800, height: 600}});
  const out = {reads: [], errors: []};
  let page, step = "start";
  try {
    page = await browser.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (e) => out.errors.push(String(e)));
    async function reveal(sel) {
      await page.$eval(sel, e => {
        for (let p=e.parentElement; p; p=p.parentElement)
          if (p.matches('details.advanced-controls, details.more-controls')) p.open=true;
      });
    }
    for (const [i, a] of job.actions.entries()) {
      step = `action ${i} ${JSON.stringify(a)}`;
      if (a.do === "goto") {
        await page.goto(a.url || job.url, {waitUntil: "load"});
        await page.waitForSelector("#status[data-state]");
      } else if (a.do === "wait") {
        await page.waitForSelector(a.sel, {visible: !!a.visible});
      } else if (a.do === "select") {
        await reveal(a.sel);
        await page.select(a.sel, a.value);
      } else if (a.do === "type") {
        await reveal(a.sel);
        await page.focus(a.sel);
        await page.keyboard.down("Control");
        await page.keyboard.press("KeyA");
        await page.keyboard.up("Control");
        await page.keyboard.press("Backspace");
        await page.type(a.sel, a.text);
      } else if (a.do === "click") {   // centre it first, as a person would: the fixed Send bar covers the bottom
        if (a.sel === "#send") await page.waitForSelector("#send:not([disabled])");
        await page.$eval(a.sel, (e) => {
          for (let p=e.parentElement; p; p=p.parentElement)
            if (p.matches("details.advanced-controls, details.more-controls") && !(e.matches('summary') && e.parentElement === p)) p.open=true;
          e.scrollIntoView({block: "center"});
        });
        await page.click(a.sel);
      } else if (a.do === "slider") {   // G2-c: move the actual Tweakpane slider with the pointer
        await page.$eval(a.sel, e => {
          for (let p=e.parentElement; p; p=p.parentElement) if (p.matches("details.advanced-controls")) p.open=true;
          e.scrollIntoView({block: "center"});
        });
        const bounds = await (await page.$(a.sel)).boundingBox();
        await page.mouse.move(bounds.x + bounds.width * 0.25, bounds.y + bounds.height / 2);
        await page.mouse.down();
        await page.mouse.move(bounds.x + bounds.width * a.fraction, bounds.y + bounds.height / 2, {steps: 8});
        await page.mouse.up();
      } else if (a.do === "waitState") {
        const sel = `#status[data-state="${a.state}"]`;
        if (a.change)
          await page.waitForFunction((s) => !document.querySelector(s), {timeout: 1000, polling: "mutation"}, sel)
            .catch(() => {});
        await page.waitForSelector(sel);
      } else if (a.do === "read") {
        out.reads.push(await page.evaluate(readPage));
      } else if (a.do === "readJson") {
        out.reads.push({json:JSON.parse(fs.readFileSync(a.path, 'utf8'))});
      } else if (a.do === "readExists") {
        out.reads.push({exists:fs.existsSync(a.path)});
      } else if (a.do === "key") {
        if (a.sel) await page.focus(a.sel);
        await page.keyboard.press(a.key);
      } else if (a.do === "viewport") {
        await page.setViewport({width:a.width, height:a.height});
      } else if (a.do === "clearSeen") {
        await page.evaluate(() => {
          for (const key of Object.keys(localStorage)) if (key.startsWith('beat-map-seen:')) localStorage.removeItem(key);
        });
      } else if (a.do === "keyboardReview") {
        const reached = new Set();
        await page.focus('#timeline .tl-beat');
        for (let n=0; n<300; n++) {
          const kind = await page.evaluate(() => {
            const e = document.activeElement;
            if (e.matches('.tl-beat')) return 'timeline';
            if (e.matches('.layout-choice')) return 'layout';
            if (e.matches('#more > summary')) return 'more';
            if (e.id === 'edit-style') return 'style';
            return e.id;
          });
          reached.add(kind);
          if (['timeline','layout','more','prev-beat','ok-beat','style','needs','send'].every(k => reached.has(k))) break;
          await page.keyboard.press('Tab');
        }
        if (!['timeline','layout','more','prev-beat','ok-beat','style','needs','send'].every(k => reached.has(k)))
          throw new Error('Tab missed review controls: ' + [...reached].join(','));
        const order = [...reached];
        if (!(order.indexOf('more') < order.indexOf('style') && order.indexOf('style') < order.indexOf('needs') &&
              order.indexOf('needs') < order.indexOf('send')))
          throw new Error('Tab order must reach focus, style, needs, Send: ' + order.join(','));
      } else {
        throw new Error("unknown action");
      }
    }
  } catch (e) {
    out.error = `${step}: ${e.message}`;
    try { out.last = await page.evaluate(readPage); } catch (e2) { /* page gone */ }
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
  if (out.errors.length) { out.error = out.error || 'page errors: ' + out.errors.join('; '); process.exitCode = 1; }
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(String((e && e.stack) || e)); process.exit(1); });
