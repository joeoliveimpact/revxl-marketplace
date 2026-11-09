// Lane-only browser proof; controls_test.py launches this through the hub harness's heavy_lock.
"use strict";
const fs = require("fs"), assert = require("assert"), {pathToFileURL} = require("url");
const boards = {
  "cut-board": ["[data-pick]", "#send", "[data-play]", "[data-drop]", "[data-all]", "[data-note]", "#reset"],
  "tweak-board": ["[data-text]", "#send", "[data-add=cut]", "[data-add=tight]", "[data-add=loose]", "[data-add=note]", "[data-del]", "[data-play]"],
  "sound-board": ["#cuebody select", "#send", "#play", "#rew", "#suggest", "#vvol", "#vmute", "#mfree", "#mown", "#bedsel", "#bedvol", "#rejall", "#reset", "#cuebody input[type=range]", "#cuebody td:last-child button"],
  "beat-map": ["#beats select[name=layout]", "#send", "#edit-style", "#word-punches", "#camera-move", "#needs", "#beats textarea[name=note]", "select[name=broll]", ".add-scene"],
  "sketches": ["#directions input[type=radio]", "#lock", "#send", "#note", "[data-slot]", ".add-scene", ".remove-scene"],
  "grade-board": ["#rail figure", "#send", "#strength", "#suggest", "#frames button"],
  "look-picker": ["#looks button", "#send", "#none", "#replay", "#make-default"],
  "cover-picker": ["#candidates button", "#send", "#title"],
  "trials": ["#versions video", "#send", "#watch-opening", "#muted", "#choice-t1", "#note-t1"]
};
const fine = {
  "cut-board": ["#gapdef", "#speed", "#beat", "[data-shot]"],
  "tweak-board": ["#zoom", "#speed", "[data-step]", "[data-type]", "[data-nudge]", "[data-tohead]", "[data-ms]", "#long-quiet", "#fine-tune"],
  "sound-board": ["[data-j]", "#lat", "#bedcarve", "#carvestrength", "#bedduck", "#bentry", "#bexit", "#boffset", "#bsync", "#bsnap", "#bfin", "#bfout", "#bstopadd", "#cuebody input[type=number]", "#cuebody .nudge", "#cuebody .endtog"],
  "beat-map": ["#punch-scale", "#opening-settle", "#follow-cam", "#punch-shape", "#open-loops", "#reminder-holds", "select[name=broll-fit]", "input[name=broll-start]"],
  "sketches": ["[data-param]", "#storyboard", "#fine-tune"],
  "grade-board": ["#wipe", "#holdB", "#toggleAB", "#sheetBtn", "#corr input", "#tune input"],
  "look-picker": ["#layouts", "#mark-look", "#under-small-overlays", "#line-breaks", "#echo-suppression", "#loud-emphasis", "#accent"],
  "cover-picker": ["#embed"], "trials": []
};

(async () => {
  const [pup, chrome, jobPath] = process.argv.slice(2), job = JSON.parse(fs.readFileSync(jobPath, "utf8"));
  const {default: puppeteer} = await import(pathToFileURL(pup).href);
  const browser = await puppeteer.launch({executablePath: chrome, headless: "shell", args: ["--no-sandbox"],
    userDataDir: job.userDataDir, defaultViewport: {width: 1500, height: 1100}});
  const errors = [], requests = [], checked = [];
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(20000);
    page.on("pageerror", e => errors.push(String(e.stack || e)));
    page.on("request", r => requests.push(r.url()));
    await page.goto(job.base + "/editor/hub/?reel=reel-01", {waitUntil: "load"});
    await page.waitForFunction("window.Hub?.ready && window.BoardClient?.controls");
    await page.evaluate(() => BoardClient.controls.ready);
    assert.strictEqual(await page.$eval("#controls", e => e.value), job.mode);
    for (const selector of ["#adjust", "#request-detail"])
      assert.ok(await page.$eval(selector, e => !!e.closest("details.advanced-controls")), selector + " must be advanced");
    const folds = async (context, mode, label) => {
      await context.waitForFunction(mode => window.BoardClient?.controls?.mode() === mode &&
        [...document.querySelectorAll("details.advanced-controls")].every(e => e.open === (mode === "advanced")), {}, mode);
      const count = await context.$$eval("details.advanced-controls", list => list.length);
      assert.ok(label === "trials" ? count === 0 : count > 0, label + ": expected disclosure count");
    };
    const everyday = async (context, selectors, label) => {
      for (const selector of selectors) {
        const visible = await context.$eval(selector, e => e.checkVisibility() && !e.closest("details.advanced-controls"));
        assert.ok(visible, label + ": everyday control hidden: " + selector);
      }
    };
    const flip = async (frame, mode) => {
      const before = await page.evaluate(async () => {
        const r = await fetch("/videos/reel-01/hub-requests.json", {cache: "no-store"});
        return r.ok ? await r.json() : [];
      });
      await frame.evaluate(() => { window.controlsDocument = "same document"; });
      await page.select("#controls", mode);
      await folds(page, mode, "hub"); await folds(frame, mode, "frame");
      await page.waitForFunction("Hub.pending===0");
      assert.strictEqual(await frame.evaluate(() => window.controlsDocument), "same document", "iframe reloaded");
      const after = await page.evaluate(async () => (await fetch("/videos/reel-01/hub-requests.json", {cache: "no-store"})).json());
      assert.strictEqual(after.length, before.length + 1, "exactly one persisted request per flip");
      assert.deepStrictEqual(after.slice(0, -1), before, "earlier requests preserved");
      const last = after.at(-1);
      assert.deepStrictEqual(Object.keys(last).sort(), ["at", "kind", "value"]);
      assert.strictEqual(last.kind, "controls");
      assert.strictEqual(last.value, mode);
      assert.strictEqual(new Date(last.at).toISOString(), last.at, "controls request has ISO time");
    };
    for (const [board, selectors] of Object.entries(boards)) {
      // A frame click (grade) can leave the hub scrolled so the sticky header covers the tabs.
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.click("#tab-" + board);
      await page.waitForFunction(b => document.querySelector("#panel iframe")?.getAttribute("src")?.startsWith("/editor/" + b + "/"), {}, board)
        .catch(async () => assert.fail(board + ": tab did not open its board; panel: " +
          await page.$eval("#panel", e => e.innerHTML.slice(0, 300))));
      const frame = await (await page.$("#panel iframe")).contentFrame();
      // Look strength only exists once a look is picked (hub_test case_grade picks "warm" the same way).
      if (board === "grade-board") await (await frame.waitForSelector('#rail figure[data-look="warm"]')).click();
      for (const selector of selectors) await frame.waitForSelector(selector);
      for (const selector of fine[board]) {
        // Module scripts (e.g. the sketches fine-tune) move their static panel in after load: wait, then assert.
        await frame.waitForFunction(s => !!document.querySelector(s)?.closest("details.advanced-controls"), {timeout: 10000}, selector)
          .catch(() => assert.fail(board + ": fine control exposed: " + selector));
      }
      await frame.waitForFunction("window.BoardClient?.controls");
      await frame.evaluate(() => BoardClient.controls.ready);
      await folds(frame, job.mode, board);
      await everyday(frame, selectors, board);
      if (job.mode === "simple") {
        if (board !== "trials") {
          // A hand-opened section changes neither the global setting nor another section.
          const kept = await frame.evaluate(async () => {
            const s = document.querySelector("details.advanced-controls"), tick = () => new Promise(r => setTimeout(r, 100));
            s.open = true; await tick();
            // Every re-apply path short of a mode change: storage event, direct apply, DOM mutation.
            window.dispatchEvent(new StorageEvent("storage", {key: "editor-controls"}));
            BoardClient.controls.apply();
            document.body.append(document.createElement("span")); await tick();
            return s.open && BoardClient.controls.mode() === "simple" &&
              [...document.querySelectorAll("details.advanced-controls")].filter(e => e.open).length === 1;
          });
          assert.ok(kept, board + ": hand-opened section not kept (or others opened) without a mode change");
          assert.strictEqual(await page.$eval("#controls", e => e.value), "simple");
        }
        // Trials has no sections, but still participates in the global mode.
        if (board === "trials") {
          await page.select("#controls", "advanced");
          await page.waitForFunction("Hub.pending===0");
          await page.select("#controls", "simple");
          await page.waitForFunction("Hub.pending===0");
        } else { await flip(frame, "advanced"); await flip(frame, "simple"); }
        await everyday(frame, selectors, board);
      }
      checked.push(board);
    }
    // After reload the config wins over stale storage; a query remains a test-only override.
    for (const [url, stored] of [["/editor/hub/?reel=reel-01", "advanced"], ["/editor/hub/?reel=reel-01&controls=advanced", null]]) {
      await page.evaluate(v => v ? localStorage.setItem("editor-controls", v) : localStorage.removeItem("editor-controls"), stored);
      await page.goto(job.base + url, {waitUntil: "load"});
      await page.waitForFunction("window.Hub?.ready && window.BoardClient?.controls");
      await page.evaluate(() => BoardClient.controls.ready);
      assert.strictEqual(await page.$eval("#controls", e => e.value), url.includes("controls=advanced") ? "advanced" : job.mode, "switch after reload: " + url);
    }
    await page.evaluate(() => localStorage.removeItem("editor-controls"));
    assert.deepStrictEqual(errors, [], "page errors");
    assert.ok(requests.every(u => u.startsWith(job.base + "/") || /^(data:|blob:|about:)/.test(u)), "external request");
    console.log(JSON.stringify({mode: job.mode, checked, errors}));
  } finally { await browser.close(); }
})().catch(e => { console.error(e.stack); process.exit(1); });
