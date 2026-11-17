// Exact seek-state proof using the editor's installed Puppeteer and Chrome (no downloads).
const {readFileSync} = require('fs');
const {pathToFileURL} = require('url');

async function main() {
  const [puppeteerPath, chrome, html, variables, sid, frame, rate] = process.argv.slice(2);
  const {default: puppeteer} = await import(pathToFileURL(puppeteerPath).href);
  const fill = JSON.parse(readFileSync(variables, 'utf8'));
  const browser = await puppeteer.launch({executablePath: chrome, headless: 'shell',
    args: ['--no-sandbox', '--allow-file-access-from-files'],
    defaultViewport: {width: 1080, height: 1920, deviceScaleFactor: 1}});
  try {
    async function snapshot(sequential) {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      await page.setRequestInterception(true);
      page.on('request', request => {
        if (/^https?:/i.test(request.url())) {
          errors.push('network request: ' + request.url());
          request.abort();
        } else request.continue();
      });
      try {
        await page.evaluateOnNewDocument(values => {
          window.__hyperframes = {getVariables: () => ({...values})};
        }, fill);
        await page.goto(pathToFileURL(html).href, {waitUntil: 'load'});
        await page.waitForFunction(id => !!window.__timelines?.[id], {}, sid);
        const size = await page.evaluate(id => {
          const root = document.querySelector(`[data-composition-id="${id}"]`);
          return {width: Number(root.dataset.width), height: Number(root.dataset.height)};
        }, sid);
        await page.setViewport({...size, deviceScaleFactor: 1});
        await page.evaluate(async id => {
          await document.fonts.ready;
          window.__timelines[id].pause();
          window.gsap.ticker.sleep();
        }, sid);
        // Match the GSAP frame adapter: pause, then seek with callbacks enabled.
        // Yield between frames, allowing hidden clock/callback dependence to surface.
        for (let f = sequential ? 0 : Number(frame); f <= Number(frame); f++) {
          await page.evaluate(async (id, seconds) => {
            window.__timelines[id].pause().seek(seconds, false);
            await new Promise(resolve => requestAnimationFrame(resolve));
            document.documentElement.getBoundingClientRect();
          }, sid, f / Number(rate));
        }
        if (errors.length) throw new Error(errors.join('; '));
        return await page.evaluate(() => Array.from(document.querySelectorAll('*'), (el, i) => {
          const computed = getComputedStyle(el);
          const state = {element: `${el.localName}${el.id ? '#' + el.id : ''} (element ${i})`,
            style: el.getAttribute('style'), transform: computed.transform,
            opacity: computed.opacity, visibility: computed.visibility, textContent: el.textContent};
          // All SVG attributes includes geometry, paths, paint, viewBox and animated attribute targets.
          if (el.namespaceURI === 'http://www.w3.org/2000/svg') {
            for (const attr of Array.from(el.attributes).sort((a, b) => a.name.localeCompare(b.name))) {
              state['svg.' + attr.name] = attr.value;
            }
          }
          return state;
        }));
      } finally {
        await page.close();
      }
    }
    const straight = await snapshot(true);
    const jump = await snapshot(false);
    process.stdout.write(JSON.stringify({straight, jump}));
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
