// node tests/editor/sound_board_click.js <puppeteer-core.js> <chrome> <job.json>
// Drives the Sound Board for sound_board_test.py. job = {url, userDataDir, actions:[...]}:
//   {do: "goto"}                  open job.url, wait for the cue rows
//   {do: "frame", sel}            click nothing; switch every later action into the iframe at sel, wait for its cue rows
//   {do: "click", sel}            centre it, then click (inside the current frame)
//   {do: "dialog", accept}        answer every later confirm() with OK (true) or Cancel (false)
//   {do: "gain", row, db}         drag-equivalent on a cue's volume slider: set it, fire "input"
//   {do: "set", sel, value}       set any input's value, fire "input" then "change"
//   {do: "waitFor", sel}          wait until sel exists; {do: "waitNone", sel} wait until it doesn't
//   {do: "waitSaved"}             wait for "Saved ..." in the save status (not pending, not an error)
//   {do: "waitSent"}              wait for the Send message; an error message fails the run
//   {do: "sleep", ms}
//   {do: "read"}                  push the board's rows + status lines onto reads
//   {do: "fetchState"}            push /videos/<reel>/sound-board.state.json (null on 404) onto reads
//   {do: "eval", js}              evaluate the expression js in the current frame, push its value onto reads
//   {do: "waitTrue", js}          wait until the expression js is truthy in the current frame
// Prints {reads, errors, dialogs} as JSON. On a timeout or error: also {error, last} and exit code 1.
"use strict";
const fs = require("fs");
const {pathToFileURL} = require("url");

function readBoard() {
  const t = (s) => { const e = document.querySelector(s); return e ? e.textContent.trim() : null; };
  return {
    rows: [...document.querySelectorAll("#cuebody tr.cuerow")].map((tr) => ({
      beat: tr.querySelector(".beat").firstChild.textContent.trim(),
      state: tr.classList.contains("keep") ? "keep" : tr.classList.contains("rej") ? "rej" : null,
      gain: tr.querySelector("input[type=range]").value,
      time: tr.querySelector("input[type=number]").value,
      tips: [...tr.querySelectorAll(".tip")].map((d) => d.textContent.trim())})),
    savest: t("#savest"), sendmsg: t("#sendmsg"), counts: t("#counts"),
    gone: !!document.getElementById("board-server-gone"),
    music: document.getElementById("musiclist") && {
      lines: [...document.querySelectorAll("#musiclist .mline")].map((l) => l.textContent.trim()),
      empty: document.getElementById("musiclist").textContent.trim(),
      bed: document.getElementById("bedsel").value, vol: document.getElementById("bedvol").value,
      duck: document.getElementById("bedduck").value, entry: document.getElementById("bentry").value,
      offset: document.getElementById("boffset").value,
      gainDb: typeof bedGainDb === "function" ? bedGainDb() : null,   // the gain the bed preview plays at
      ticks: [...document.querySelectorAll("#musiclist input.mrights")].map((c) => c.checked),
      request: [...document.querySelectorAll("#mfree.on, #mown.on")].map((b) => b.id),
      note: t("#mreqnote"),
      sync: {checked: document.getElementById("bsync").checked, disabled: document.getElementById("bsync").disabled,
             note: t("#bsyncnote"), snapDisabled: document.getElementById("bsnap").disabled},
      beatTicks: document.querySelectorAll("#tl .btick").length},
  };
}

(async () => {
  const [pup, chrome, jobPath] = process.argv.slice(2);
  const job = JSON.parse(fs.readFileSync(jobPath, "utf8"));
  const {default: puppeteer} = await import(pathToFileURL(pup).href);
  const browser = await puppeteer.launch({executablePath: chrome, headless: "shell", args: ["--no-sandbox"],
                                          userDataDir: job.userDataDir, defaultViewport: {width: 1300, height: 1000}});
  const out = {reads: [], errors: [], dialogs: []};
  let page, ctx, step = "start", accept = false;
  try {
    page = await browser.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (e) => out.errors.push(String(e)));
    page.on("dialog", (d) => { out.dialogs.push(d.message()); (accept ? d.accept() : d.dismiss()).catch(() => {}); });
    ctx = page;
    for (const [i, a] of job.actions.entries()) {
      step = `action ${i} ${JSON.stringify(a)}`;
      if (a.do === "goto") {
        await page.goto(job.url, {waitUntil: "load"});
        ctx = page;
        if (!a.noRows) await page.waitForSelector("#cuebody tr.cuerow");
      } else if (a.do === "frame") {
        const h = await page.waitForSelector(a.sel);
        ctx = await h.contentFrame();
        await ctx.waitForSelector("#cuebody tr.cuerow");
      } else if (a.do === "click") {
        await ctx.$eval(a.sel, (e) => e.scrollIntoView({block: "center"}));
        await ctx.click(a.sel);
      } else if (a.do === "dialog") {
        accept = !!a.accept;
      } else if (a.do === "gain") {
        await ctx.$eval(`#cuebody tr.cuerow:nth-child(${a.row}) input[type=range]`, (e, db) => {
          e.value = String(db); e.dispatchEvent(new Event("input", {bubbles: true}));
        }, a.db);
      } else if (a.do === "set") {
        await ctx.$eval(a.sel, (e, v) => {
          e.value = String(v); e.dispatchEvent(new Event("input", {bubbles: true})); e.dispatchEvent(new Event("change", {bubbles: true}));
        }, a.value);
      } else if (a.do === "waitFor") {
        await ctx.waitForSelector(a.sel);
      } else if (a.do === "waitNone") {
        await ctx.waitForFunction((s) => !document.querySelector(s), {polling: 100}, a.sel);
      } else if (a.do === "waitSaved") {
        await ctx.waitForFunction(() => {
          const s = document.querySelector("#savest");
          return s && s.className === "" && s.textContent.startsWith("Saved");
        }, {polling: 100});
      } else if (a.do === "waitSent") {
        await ctx.waitForFunction(() => /written to|SEND FAILED/.test(document.querySelector("#sendmsg").textContent),
                                  {polling: 100});
        const msg = await ctx.$eval("#sendmsg", (e) => e.textContent);
        if (msg.includes("SEND FAILED")) throw new Error(msg);
      } else if (a.do === "sleep") {
        await new Promise((r) => setTimeout(r, a.ms));
      } else if (a.do === "read") {
        out.reads.push(await ctx.evaluate(readBoard));
      } else if (a.do === "fetchState") {
        out.reads.push(await ctx.evaluate(async () => {
          const reel = new URLSearchParams(location.search).get("reel");
          const r = await fetch("/videos/" + encodeURIComponent(reel) + "/sound-board.state.json", {cache: "no-store"});
          return r.ok ? r.json() : null;
        }));
      } else if (a.do === "eval") {
        out.reads.push(await ctx.evaluate(a.js));
      } else if (a.do === "waitTrue") {
        await ctx.waitForFunction(a.js, {polling: 100});
      } else {
        throw new Error("unknown action");
      }
    }
  } catch (e) {
    out.error = `${step}: ${e.message}`;
    try { out.last = await ctx.evaluate(readBoard); } catch (e2) { /* page gone */ }
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(String((e && e.stack) || e)); process.exit(1); });
