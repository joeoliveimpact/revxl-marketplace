// node tests/editor/review_page_click.js <cut-review.html> <puppeteer-core dir> <chrome>
// Opens the review page from disk (file://) in headless Chrome, clicks the first row of the cut list
// and the widest red mark on the bar, and prints JSON: the rows, the seek each click made, page errors,
// and whether both video sources exist on disk. first_cut_test.py asserts on it.
"use strict";
const fs = require("fs");
const path = require("path");
const {pathToFileURL, fileURLToPath} = require("url");

(async () => {
  const [page_, pup, chrome] = process.argv.slice(2);
  const {default: puppeteer} = await import(pathToFileURL(path.join(pup, "lib", "puppeteer", "puppeteer-core.js")).href);
  const browser = await puppeteer.launch({executablePath: chrome, headless: "shell",
                                          args: ["--no-sandbox"]});
  const out = {errors: []};
  try {
    const page = await browser.newPage();
    page.on("pageerror", (e) => out.errors.push(String(e)));
    await page.goto(pathToFileURL(path.resolve(page_)).href, {waitUntil: "load"});
    out.rows = await page.$$eval("#rows tr", (rs) => rs.map((r) => ({start: +r.dataset.start, at: +r.dataset.at,
                                                                     len: parseFloat(r.cells[3].textContent)})));
    out.srcs = await page.$$eval("video", (vs) => vs.map((v) => new URL(v.getAttribute("src"), location.href).href));
    out.srcExists = out.srcs.map((u) => fs.existsSync(fileURLToPath(u)));
    const seekAfter = async (sel) => {
      await page.click(sel);
      return page.evaluate(() => ({raw: document.getElementById("raw").currentTime,
                                   cut: document.getElementById("cut").currentTime}));
    };
    out.rowClick = await seekAfter("#rows tr:first-child");
    out.markWidest = await page.$$eval("#bar .cut", (ms) => {
      let best = 0;
      ms.forEach((m, i) => { if (parseFloat(m.style.width) > parseFloat(ms[best].style.width)) best = i; });
      ms.forEach((m, i) => m.toggleAttribute("data-widest", i === best));
      return ms.length;
    });
    out.markClick = await seekAfter("#bar .cut[data-widest]");
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(String(e && e.stack || e)); process.exit(1); });
