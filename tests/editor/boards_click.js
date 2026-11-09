// node tests/editor/boards_click.js <puppeteer-core.js> <chrome> <job.json>
// Drives the Cut Board, the Tweak Board and the test hub for boards_test.py. job = {base, userDataDir, actions:[...]}:
//   {do: "goto", path, wait?, waitFn?}   open base + path, then wait for a selector and/or a JS expression
//   {do: "frame", sel, wait?, waitFn?}   switch every later action into the iframe at sel
//   {do: "top"}                          back to the top page
//   {do: "click", sel}                   centre it, then click (inside the current frame)
//   {do: "domclick", sel}                the element's own click(), immune to layout shifts under the pointer
//   {do: "press", key, ctrl?, shift?}    one key press with modifiers
//   {do: "set", sel, value}              set an input's value, fire "input" and "change"
//   {do: "seek", t}                      the page's <video id="v"> to t seconds (waits for its metadata and the seek)
//   {do: "waitFn", js}                   wait for a JS expression in the current frame
//   {do: "waitText", sel, re}            wait for the element's text to match re; a "FAILED" text fails the run
//   {do: "waitState", board, js}         poll /videos/<reel>/<board>.state.json until js (s => ...) holds
//   {do: "eval", js}                     push the value of a JS expression (awaited) onto reads
//   {do: "sleep", ms}
// Prints {reads, errors, requests} as JSON: every request URL the page made, from any frame. On a timeout or an
// error: also {error} and exit code 1.
"use strict";
const fs = require("fs");
const {pathToFileURL} = require("url");

(async () => {
  const [pup, chrome, jobPath] = process.argv.slice(2);
  const job = JSON.parse(fs.readFileSync(jobPath, "utf8"));
  const {default: puppeteer} = await import(pathToFileURL(pup).href);
  const browser = await puppeteer.launch({executablePath: chrome, headless: "shell", args: ["--no-sandbox"],
                                          userDataDir: job.userDataDir, defaultViewport: {width: 1300, height: 1000}});
  const out = {reads: [], errors: [], requests: []};
  let page, ctx, step = "start";
  const settle = async (a) => {
    if (a.wait) await ctx.waitForSelector(a.wait);
    if (a.waitFn) await ctx.waitForFunction(a.waitFn, {polling: 100});
  };
  try {
    page = await browser.newPage();
    page.setDefaultTimeout(20000);
    page.on("pageerror", (e) => out.errors.push(String(e)));
    page.on("request", (r) => out.requests.push(r.url()));
    ctx = page;
    for (const [i, a] of job.actions.entries()) {
      step = `action ${i} ${JSON.stringify(a)}`;
      if (a.do === "goto") {
        await page.goto(job.base + a.path, {waitUntil: "load"});
        ctx = page;
        await settle(a);
      } else if (a.do === "frame") {
        const h = await page.waitForSelector(a.sel);
        ctx = await h.contentFrame();
        await settle(a);
      } else if (a.do === "top") {
        ctx = page;
      } else if (a.do === "click") {
        await ctx.$eval(a.sel, (e) => {
          for (let p=e.parentElement; p; p=p.parentElement) if (p.matches("details.advanced-controls")) p.open=true;
          e.scrollIntoView({block: "center"});
        });
        await ctx.click(a.sel);
      } else if (a.do === "domclick") {
        await ctx.$eval(a.sel, (e) => e.click());
      } else if (a.do === "press") {
        if (a.ctrl) await page.keyboard.down("Control");
        if (a.shift) await page.keyboard.down("Shift");
        await page.keyboard.press(a.key);
        if (a.shift) await page.keyboard.up("Shift");
        if (a.ctrl) await page.keyboard.up("Control");
      } else if (a.do === "slider") {   // G2-c: exercise the real Tweakpane pointer control
        await ctx.$eval(a.sel, e => {
          for (let p=e.parentElement; p; p=p.parentElement) if (p.matches("details.advanced-controls")) p.open=true;
          e.scrollIntoView({block: "center"});
        });
        const bounds = await (await ctx.$(a.sel)).boundingBox();
        await page.mouse.move(bounds.x + bounds.width * 0.25, bounds.y + bounds.height / 2);
        await page.mouse.down();
        await page.mouse.move(bounds.x + bounds.width * a.fraction, bounds.y + bounds.height / 2, {steps: 8});
        await page.mouse.up();
      } else if (a.do === "set") {
        await ctx.$eval(a.sel, (e, v) => {
          e.value = String(v);
          e.dispatchEvent(new Event("input", {bubbles: true}));
          e.dispatchEvent(new Event("change", {bubbles: true}));
        }, a.value);
      } else if (a.do === "seek") {
        await ctx.evaluate(async (t) => {
          const v = document.getElementById("v");
          if (v.readyState < 1) await new Promise((r) => v.addEventListener("loadedmetadata", r, {once: true}));
          const done = new Promise((r) => v.addEventListener("seeked", r, {once: true}));
          v.currentTime = t;
          await done;
        }, a.t);
      } else if (a.do === "waitFn") {
        await ctx.waitForFunction(a.js, {polling: 100});
      } else if (a.do === "waitText") {
        await ctx.waitForFunction((s, re) => {
          const e = document.querySelector(s);
          return e && new RegExp(re).test(e.textContent);
        }, {polling: 100}, a.sel, a.re);
        const txt = await ctx.$eval(a.sel, (e) => e.textContent);
        if (/FAILED/.test(txt)) throw new Error(txt);
      } else if (a.do === "waitState") {
        const ok = new Function("s", "return (" + a.js + ");");   // test-only: the predicate comes from the test's own job file
        const until = Date.now() + 15000;
        for (;;) {
          const s = await ctx.evaluate(async (b) => {
            const reel = new URLSearchParams(location.search).get("reel");
            const r = await fetch("/videos/" + encodeURIComponent(reel) + "/" + b + ".state.json", {cache: "no-store"});
            return r.ok ? r.json() : null;
          }, a.board);
          if (s && ok(s)) break;
          if (Date.now() > until) throw new Error("the saved state never matched " + a.js + ": " + JSON.stringify(s).slice(0, 400));
          await new Promise((r) => setTimeout(r, 150));
        }
      } else if (a.do === "eval") {
        out.reads.push(await ctx.evaluate(a.js));
      } else if (a.do === "sleep") {
        await new Promise((r) => setTimeout(r, a.ms));
      } else {
        throw new Error("unknown action");
      }
    }
  } catch (e) {
    out.error = `${step}: ${e.message}`;
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(String((e && e.stack) || e)); process.exit(1); });
