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
    strip: all("#strip div[data-beat]").length,
    rows: all("#beats tr[data-beat]").map((tr) => ({
      beat: tr.dataset.beat, layout: val(q("select[name=layout]", tr)), value: val(q("input[name=value]", tr)),
      note: val(q("textarea[name=note]", tr)), changed: tr.classList.contains("changed")})),
    marks: Object.fromEntries(all("#beats span.word[data-w]").map((s) => [s.dataset.w, s.getAttribute("data-mark")])),
    needs: val(q("#needs")),
    directions: all("#directions section.direction[data-id]").map((s) => ({
      id: s.dataset.id, picked: s.classList.contains("picked"),
      checked: !!q("input[type=radio][name=pick]:checked", s), note: val(q("textarea[name=note]", s))})),
    sketches: all("#sketches article.sketch[data-id]").map((a) => ({id: a.dataset.id, note: val(q("textarea[name=note]", a))})),
    note: val(q("#note")),
    send: q("#send") ? {disabled: q("#send").disabled, loading: !!q("#send [data-loading]")} : null,
    lock: q("#lock") ? {disabled: q("#lock").disabled} : null,
    locked: !!q("#directions") && q("#directions").classList.contains("locked"),
    localStorage: localStorage.length,
  };
}

(async () => {
  const [pup, chrome, jobPath] = process.argv.slice(2);
  const job = JSON.parse(fs.readFileSync(jobPath, "utf8"));
  const {default: puppeteer} = await import(pathToFileURL(pup).href);
  const browser = await puppeteer.launch({executablePath: chrome, headless: "shell", args: ["--no-sandbox"],
                                          userDataDir: job.userDataDir});
  const out = {reads: [], errors: []};
  let page, step = "start";
  try {
    page = await browser.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (e) => out.errors.push(String(e)));
    for (const [i, a] of job.actions.entries()) {
      step = `action ${i} ${JSON.stringify(a)}`;
      if (a.do === "goto") {
        await page.goto(a.url || job.url, {waitUntil: "load"});
        await page.waitForSelector("#status[data-state]");
      } else if (a.do === "wait") {
        await page.waitForSelector(a.sel, {visible: !!a.visible});
      } else if (a.do === "select") {
        await page.select(a.sel, a.value);
      } else if (a.do === "type") {
        await page.focus(a.sel);
        await page.keyboard.down("Control");
        await page.keyboard.press("KeyA");
        await page.keyboard.up("Control");
        await page.keyboard.press("Backspace");
        await page.type(a.sel, a.text);
      } else if (a.do === "click") {   // centre it first, as a person would: the fixed Send bar covers the bottom
        if (a.sel === "#send") await page.waitForSelector("#send:not([disabled])");
        await page.$eval(a.sel, (e) => e.scrollIntoView({block: "center"}));
        await page.click(a.sel);
      } else if (a.do === "slider") {   // G2-c: move the actual Tweakpane slider with the pointer
        await page.$eval(a.sel, e => e.scrollIntoView({block: "center"}));
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
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(String((e && e.stack) || e)); process.exit(1); });
