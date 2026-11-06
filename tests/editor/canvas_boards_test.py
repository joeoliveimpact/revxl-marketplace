"""S6a done-test: the Beat Map and Sketches boards end to end, plus the ways they must refuse.

  EDITOR_SE_HOME=<state> python -X utf8 -I tests/editor/canvas_boards_test.py

<state> is an installed editor state folder (node, chrome-headless-shell, puppeteer-core); it is only read.
Prints one "✓ <case>" / "✗ <case>: <why>" line per case, then "N passed, M failed". Exit 0 only when all pass.
The browser work runs through canvas_boards_click.js (puppeteer-core, headless shell, a fresh profile per browser).
"""
import base64, contextlib, copy, datetime, http.client, io, json, os, shutil, socket, subprocess, sys, tempfile, threading
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
DOCTOR = PLUGIN / "skills/editor-doctor/scripts"
CANVAS = PLUGIN / "skills/reel-canvas-build/scripts"
sys.path.insert(0, str(PLUGIN / "skills/_shared"))
sys.path.insert(0, str(DOCTOR))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import check_deps  # noqa: E402  (writes editor.config.json the way the doctor does)

SERVER = DOCTOR / "board_server.py"
SEED = CANVAS / "make_beat_map.py"
SCHEMA = CANVAS / "beat_schema.py"
CLICK = Path(__file__).resolve().parent / "canvas_boards_click.js"
PNG_1X1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP438AAAAQBAYDFKhhdAAAAAElFTkSuQmCC")
WORDS = ["Three", "big", "wins", "for", "your", "next", "reel", "today.",
         "First,", "cut", "the", "silence.", "Then", "follow", "for", "more."]
FPS, TOTAL_F = 30, 270
PLAN = {"beats": [{"w0": 0, "w1": 3, "layout": "full", "shows": "the title", "why": "the opening line"},
                  {"w0": 4, "w1": 7, "layout": "full"},
                  {"w0": 8, "w1": 11, "layout": "stack", "why": "two steps"},
                  {"w0": 9, "w1": 10, "layout": "overlay", "value": 2, "shows": "a counter", "why": "a number"},
                  {"w0": 12, "w1": 15, "layout": "pip"}],
        "word_marks": [{"w": 0, "mark": "num"}, {"w": 13, "mark": "cta"}],
        "needs": ""}
D1, D2 = "d_bold", "d_calm"

# Kept here because this work order permits no change to canvas_boards_click.js.
# Uses the same puppeteer install, run(), fixture and board server as the existing cases.
SCENE_BROWSER = r"""
const fs = require('fs'), {pathToFileURL} = require('url');
(async () => {
  const [pup, chrome, jobPath] = process.argv.slice(1);
  const job = JSON.parse(fs.readFileSync(jobPath, 'utf8'));
  const {default: puppeteer} = await import(pathToFileURL(pup).href);
  const browser = await puppeteer.launch({executablePath: chrome, headless: 'shell',
    args: ['--no-sandbox'], userDataDir: job.userDataDir});
  const errors = [];
  let step = 'open';
  const need = (ok, why) => { if (!ok) throw new Error(why); };
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(15000);
    page.on('pageerror', e => errors.push(String(e)));
    async function open() {
      await page.goto(job.url, {waitUntil: 'load'});
      await page.waitForSelector('.tabs[data-built]');
      await page.click('#tab-sketches');
      const handle = await page.waitForSelector('iframe');
      const frame = await handle.contentFrame();
      await frame.waitForSelector('#status[data-state=saved], #status[data-state=sent]');
      return frame;
    }
    let frame = await open();
    async function click(selector) {
      await frame.$eval(selector, e => {
        e.scrollIntoView({block:'center'});
        // A fixed footer inside the 900px fixture also needs the outer page to scroll.
        parent.scrollBy(0, window.frameElement.getBoundingClientRect().top + e.getBoundingClientRect().top - parent.innerHeight / 2);
      });
      try { await frame.click(selector); }
      catch (e) {
        const geometry = await frame.$eval(selector, e => ({rect:e.getBoundingClientRect().toJSON(),
          innerHeight, parentHeight:parent.innerHeight, iframe:window.frameElement.getBoundingClientRect().toJSON(),
          parentScroll:parent.scrollY, disabled:e.disabled}));
        throw new Error(e.message + ': ' + JSON.stringify(geometry));
      }
    }
    const row = '.scene-controls[data-beat="b_001"]';
    const input = row + ' textarea[data-slot="text"]';
    step = 'open picker'; await click(row + ' .add-scene');
    await frame.waitForSelector(row + ' .scene-choice[data-scene="callout"]');
    need(await frame.$eval(row + ' .scene-choice', e => !e.disabled), 'suggested scenes must be first');
    need(await frame.$eval(row + ' .scene-choice[data-scene="counter"]', e => e.disabled &&
      e.textContent.includes("doesn't fit this beat's words or length")), 'unfit scene must explain why');
    await frame.waitForFunction(s => [...document.querySelectorAll(s + ' img')].every(i => i.complete && i.naturalWidth), {}, row);
    step = 'pick callout'; await click(row + ' .scene-choice[data-scene="callout"]');
    need(await frame.$eval(input, e => e.value) === 'Three big wins for', 'suggestion was not prefilled');
    await frame.evaluate(skip => { window.__testSkipSceneMaxChars = skip; }, job.skipGuard);
    async function type(text) {
      await frame.focus(input);
      await page.keyboard.down('Control'); await page.keyboard.press('KeyA'); await page.keyboard.up('Control');
      await page.keyboard.press('Backspace'); await frame.type(input, text);
    }
    await type('x'.repeat(40));
    need(await frame.$eval(input, e => e.value.length) === 32, 'overflow guard failed');
    need(await frame.$eval(row + ' .slot-count', e => e.textContent) === '32 / 32', 'live counter is wrong');
    async function send() {
      step = 'send'; await click('#send'); await frame.waitForSelector('#status[data-state=sent]');
      need(errors.length === 0, 'page errors: ' + errors.join('; '));
    }
    await send();
    need(JSON.parse(fs.readFileSync(job.selection, 'utf8')).scenes.b_001.slots.text === 'x'.repeat(32),
      'Send carried an overflow');
    await type('Edited words'); await send();
    step = 'reload'; frame = await open();
    need(await frame.$eval(input, e => e.value) === 'Edited words', 'scene was not restored');
    const sent = JSON.parse(fs.readFileSync(job.selection, 'utf8'));
    need(JSON.stringify(sent.scenes.b_001) === JSON.stringify({id:'callout', slots:{text:'Edited words'}, params:{}}),
      'sent scene shape differs');
    step = 'remove'; await click(row + ' .remove-scene'); await send();
    need(!('b_001' in JSON.parse(fs.readFileSync(job.selection, 'utf8')).scenes), 'removed scene was sent');
    step = 'enum control';
    await click(row + ' .add-scene'); await click(row + ' .scene-choice[data-scene="hook-title"]');
    await frame.select(row + ' select[data-param="entrance"]', '1'); await send();
    frame = await open();
    need(await frame.$eval(row + ' select[data-param="entrance"]', e => e.selectedOptions[0].textContent) === 'none',
      'enum param did not survive Send and reload');
    need(JSON.parse(fs.readFileSync(job.selection, 'utf8')).scenes.b_001.params.entrance === 'none', 'enum param sent incorrectly');
    await click(row + ' .remove-scene');
    step = 'number control';
    await click(row + ' .add-scene'); await click(row + ' .scene-choice[data-scene="hf-callout"]');
    const number = row + ' input[data-param="sweep"]';
    need(await frame.$eval(number, e => e.min === '0.5' && e.max === '7'), 'number bounds differ from catalog');
    const beforeInvalid = fs.readFileSync(job.selection, 'utf8');
    for (const value of ['0.1', '8']) {
      await frame.$eval(number, (e, v) => { e.value = v; e.dispatchEvent(new Event('input', {bubbles:true})); }, value);
      await click('#send'); await frame.waitForSelector('#status[data-state=error]');
      need(fs.readFileSync(job.selection, 'utf8') === beforeInvalid, 'Send accepted an out-of-range number');
    }
    await frame.$eval(number, e => { e.value = '1.5'; e.dispatchEvent(new Event('input', {bubbles:true})); });
    await send(); frame = await open();
    need(await frame.$eval(number, e => e.value) === '1.5', 'number param was not restored');
    need(JSON.parse(fs.readFileSync(job.selection, 'utf8')).scenes.b_001.params.sweep === 1.5, 'number param sent as wrong type');
    await click(row + ' .remove-scene'); await send();
    step = 'locked counter';
    const counterRow = '.scene-controls[data-beat="b_002"]';
    await click(counterRow + ' .add-scene'); await click(counterRow + ' .scene-choice[data-scene="counter"]');
    const counterValue = counterRow + ' input[data-param="value"]';
    need(await frame.$eval(counterValue, e => e.readOnly && e.value === '47'), 'counter is not locked to beat');
    need(await frame.$eval(counterRow, e => e.textContent.includes("from the beat's number")), 'counter label missing');
    await frame.evaluate(() => { doc.scenes.b_002.params.value = 48; });
    await click('#send'); await frame.waitForSelector('#status[data-state=error]');
    await frame.evaluate(() => { doc.scenes.b_002.params.value = 47; });
    await send();
    console.log(JSON.stringify({ok:true, sent, errors}));
  } catch (e) { console.log(JSON.stringify({ok:false, error:e.message, step, errors})); process.exitCode = 1; }
  finally { await browser.close(); }
})().catch(e => { console.error(String(e.stack || e)); process.exit(1); });
"""


BEATMAP_BROWSER = r"""
const fs = require('fs'), {pathToFileURL} = require('url');
(async () => {
  const [pup, chrome, jobPath] = process.argv.slice(1), job = JSON.parse(fs.readFileSync(jobPath, 'utf8'));
  const {default: puppeteer} = await import(pathToFileURL(pup).href);
  const browser = await puppeteer.launch({executablePath:chrome, headless:'shell', args:['--no-sandbox'],
    userDataDir:job.userDataDir});
  const need = (ok, why) => { if (!ok) throw new Error(why); }, errors = [];
  let step = 'open';
  try {
    const page = await browser.newPage(); page.setDefaultTimeout(15000);
    page.on('pageerror', e => errors.push(String(e)));
    async function open() {
      await page.goto(job.url, {waitUntil:'load'}); await page.waitForSelector('.tabs[data-built]');
      await page.click('#tab-beat-map');
      const frame = await (await page.waitForSelector('iframe')).contentFrame();
      await frame.waitForSelector('#status[data-state=saved], #status[data-state=sent]'); return frame;
    }
    let frame = await open();
    async function click(s) {
      await frame.$eval(s, e => { e.scrollIntoView({block:'center'});
        parent.scrollBy(0, window.frameElement.getBoundingClientRect().top + e.getBoundingClientRect().top - parent.innerHeight/2); });
      await frame.click(s);
    }
    const row = '.scene-controls[data-beat="b_001"]', input = row + ' textarea[data-slot="text"]';
    async function send() { await click('#send'); await frame.waitForSelector('#status[data-state=sent]'); }
    async function text(value) {
      await frame.$eval(input, (e, v) => { e.value = v; e.dispatchEvent(new Event('input', {bubbles:true})); }, value);
    }
    step = 'picker'; await click(row + ' .add-scene');
    need(await frame.$eval(row + ' .scene-choice', e => !e.disabled), 'suggested scenes must be first');
    need(await frame.$eval(row + ' .scene-choice[data-scene="counter"]', e => e.disabled &&
      e.textContent.includes("doesn't fit this beat's words or length")), 'unfit scene reason missing');
    await frame.waitForFunction(s => [...document.querySelectorAll(s + ' img')].every(i => i.complete && i.naturalWidth), {}, row);
    await click(row + ' .scene-choice[data-scene="callout"]');
    need(await frame.$eval(input, e => e.value) === 'Three big wins for', 'prefill missing');
    step = 'overflow'; await frame.evaluate(skip => { window.__testSkipSceneMaxChars = skip; }, job.skipGuard);
    await text('x'.repeat(40));
    need(await frame.$eval(input, e => e.value.length) === 32, 'overflow guard failed');
    need(await frame.$eval(row + ' .slot-count', e => e.textContent) === '32 / 32', 'counter wrong');
    await send(); need(JSON.parse(fs.readFileSync(job.selection,'utf8')).beats[0].scene.slots.text.length === 32,
      'overflow sent');
    // A hand-planted overflow still cannot Send, even though no input event runs the guard.
    const before = fs.readFileSync(job.selection,'utf8');
    await frame.evaluate(() => { doc.beats[0].scene.slots.text = 'x'.repeat(40); });
    await click('#send'); await frame.waitForSelector('#status[data-state=error]');
    need(fs.readFileSync(job.selection,'utf8') === before, 'Send accepted planted overflow');
    await text('Edited words'); await send();
    const sent = JSON.parse(fs.readFileSync(job.selection,'utf8'));
    need(JSON.stringify(sent.beats[0].scene) === JSON.stringify({id:'callout',slots:{text:'Edited words'},params:{}}), 'shape differs');
    step = 'restore'; frame = await open(); need(await frame.$eval(input,e=>e.value) === 'Edited words', 'restore failed');
    step = 'remove'; await click(row + ' .remove-scene'); await send();
    need(JSON.parse(fs.readFileSync(job.selection,'utf8')).beats[0].scene === null, 'remove failed');
    step = 'enum and bounds';
    await click(row + ' .add-scene'); await click(row + ' .scene-choice[data-scene="hook-title"]');
    await frame.select(row + ' select[data-param="entrance"]', '1'); await send(); frame = await open();
    need(await frame.$eval(row + ' select[data-param="entrance"]',e=>e.selectedOptions[0].textContent) === 'none',
      'enum was not restored');
    await click(row + ' .remove-scene'); await click(row + ' .add-scene');
    await click(row + ' .scene-choice[data-scene="hf-callout"]');
    const sweep = row + ' input[data-param="sweep"]', previous = fs.readFileSync(job.selection,'utf8');
    need(await frame.$eval(sweep,e=>e.min==='0.5' && e.max==='7'), 'catalog bounds missing');
    for (const value of ['0.1','8']) {
      await frame.$eval(sweep,(e,v)=>{e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));},value);
      await click('#send'); await frame.waitForSelector('#status[data-state=error]');
      need(fs.readFileSync(job.selection,'utf8')===previous, 'Send accepted bad bounds');
    }
    await frame.$eval(sweep,e=>{e.value='1.5';e.dispatchEvent(new Event('input',{bubbles:true}));});
    await send(); frame=await open(); need(await frame.$eval(sweep,e=>e.value)==='1.5', 'numeric param not restored');
    await click(row + ' .remove-scene'); await send();
    step = 'Sketches offer';
    need(await frame.$eval(row + ' .use-sketch-scene',e=>e.textContent.includes('picked in Sketches')), 'Sketches offer missing');
    await click(row + ' .use-sketch-scene'); need(await frame.$eval(input,e=>e.value) === 'From Sketches', 'Sketches fill lost');
    await send(); await click(row + ' .remove-scene');
    step = 'counter lock'; const cr = '.scene-controls[data-beat="b_002"]';
    await click(cr + ' .add-scene'); await click(cr + ' .scene-choice[data-scene="counter"]');
    const number = cr + ' input[data-param="value"]';
    need(await frame.$eval(number,e=>e.readOnly && e.value === '47'), 'counter is not locked to beat');
    need(await frame.$eval(cr,e=>e.textContent.includes("from the beat's number")), 'counter label missing');
    await frame.evaluate(() => { doc.beats.find(b=>b.id==='b_002').scene.params.value = 48; });
    await click('#send'); await frame.waitForSelector('#status[data-state=error]');
    await frame.evaluate(() => { doc.beats.find(b=>b.id==='b_002').scene.params.value = 47; });
    await send();
    // Editing the beat updates its locked scene number.
    await frame.$eval('#beats tr[data-beat="b_002"] input[name=value]', e => {
      e.value='48'; e.dispatchEvent(new Event('input',{bubbles:true})); });
    need(await frame.$eval(number,e=>e.value) === '48', 'beat edit did not update scene');
    await frame.$eval('#beats tr[data-beat="b_002"] input[name=value]', e => {
      e.value='47'; e.dispatchEvent(new Event('input',{bubbles:true})); });
    step = 'numeric compositor fixture';
    const label = cr + ' textarea[data-slot="label"]';
    await frame.$eval(label,e=> { e.value='47 people'; e.dispatchEvent(new Event('input',{bubbles:true})); }); await send();
    need(!errors.length, 'page errors: '+errors.join(';'));
    console.log(JSON.stringify({ok:true, sent, errors}));
  } catch(e) { console.log(JSON.stringify({ok:false,error:e.message,step,errors})); process.exitCode=1; }
  finally { await browser.close(); }
})().catch(e=>{console.error(String(e.stack||e));process.exit(1);});
"""


class Fail(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Fail(why)


def free_port(*taken):
    while True:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        if port not in taken:
            return port


def find_tools():
    found, missing = {}, []
    for name in ("node", "chrome"):
        try:
            found[name] = rt.tool(name)
            if not Path(found[name]).is_file():
                missing.append(name)
        except (KeyError, OSError, ValueError):
            missing.append(name)
    pup = rt.state_dir() / "hyperframes/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js"
    if not pup.is_file():
        missing.append("puppeteer-core")
    found["pup"] = str(pup)
    return found, missing


def run(args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)


def iso(v):
    try:
        datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
        return True
    except (AttributeError, TypeError, ValueError):
        return False


def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1), encoding="utf-8")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def reel_fixture(reel):
    words = [{"id": f"w_{i:04d}", "word": w, "start": round(0.1 + 0.5 * i, 3), "end": round(0.5 + 0.5 * i, 3),
              "parakeet_start": round(0.1 + 0.5 * i, 3), "status": "aligned", "score_min": 0.9}
             for i, w in enumerate(WORDS)]
    write_json(reel / "work/edit_map.cut.json", {"words": words})
    write_json(reel / "work/cuts.json", {"fps": FPS, "segments": [
        {"src_in_f": 0, "src_out_f": 120, "out_in_f": 0, "out_out_f": 120},
        {"src_in_f": 150, "src_out_f": 300, "out_in_f": 120, "out_out_f": TOTAL_F}]})
    write_json(reel / "work/plan.json", PLAN)
    for d in (D1, D2):
        (reel / f"work/sketches/{d}.png").parent.mkdir(parents=True, exist_ok=True)
        (reel / f"work/sketches/{d}.png").write_bytes(PNG_1X1)
    write_json(reel / "sketches.state.json", {
        "schema": 1, "reel": reel.name, "rough": None,
        "directions": [{"id": D1, "name": "Bold", "why": "fast cuts", "frames": [f"work/sketches/{D1}.png"], "note": ""},
                       {"id": D2, "name": "Calm", "why": "room to breathe", "frames": [f"work/sketches/{D2}.png"], "note": ""}],
        "pick": None,
        "sketches": [{"id": "s_001", "beat": "b_001", "title": "Three wins", "media": None, "note": ""},
                     {"id": "s_002", "beat": "b_002", "title": "Next reel", "media": None, "note": ""}],
        "note": "", "sent_at": None, "locked_at": None})


def scene_fill_case():
    sys.path.insert(0, str(CANVAS))
    sys.path.insert(0, str(PLUGIN / "scripts"))
    import scene_fill
    import scene_check
    words = "We helped 47 people make their next reel with clear words and useful examples today".split()
    beat = {"id": "b_001", "start_f": 0, "end_f": 120, "value": 47,
            "speech_anchor": {"w0": 0, "w1": len(words) - 1}}

    def honest(fill, b=beat, heard=words):
        spec = load(scene_check.SCENES / fill["id"] / "scene.json")
        need(not scene_check.fill_problems(fill["id"], dict(b, scene=fill), words=heard), "invalid suggestion")
        remaining = heard[b["speech_anchor"]["w0"]:b["speech_anchor"]["w1"] + 1]
        for name, slot in spec["slots"].items():
            text = fill["slots"][name]
            need(len(text) <= slot["maxChars"], "over maxChars")
            if spec["category"] in ("stat-card", "stat") and name in ("stat", "value", "number"):
                need(scene_check.said(b["value"], scene_check.numbers(text)), "stat slot lost the beat number")
                continue
            used = text.split()
            need(used == remaining[:len(used)], "slot is not a word-boundary prefix/continuation")
            remaining = remaining[len(used):]

    with tempfile.TemporaryDirectory() as tmp:
        reel = Path(tmp) / "demo"
        reel_fixture(reel)
        cat = scene_fill.catalog()
        expected = {d.name for d in scene_check.SCENES.iterdir()
                    if d.is_dir() and not scene_check.scene_problems(d)}
        need({s["id"] for s in cat} == expected, "catalog must list every shippable scene")
        for item in cat:
            spec = load(scene_check.SCENES / item["id"] / "scene.json")
            want = {k: spec[k] for k in ("id", "kind", "category", "dur")}
            want["slots"] = [{"name": n, "maxChars": s["maxChars"]} for n, s in spec["slots"].items()]
            want["params"] = [dict(name=n, **{k: p[k] for k in ("type", "min", "max", "enum", "default") if k in p})
                              for n, p in spec["params"].items()]
            want["preview"] = (scene_check.SCENES / item["id"] / "preview.png").as_posix()
            need(item == want, f"catalog differs from scene.json: {item['id']}")
            fill = scene_fill.suggest(item["id"], beat, words, FPS)
            if fill is not None:
                honest(fill)
            short = dict(beat, end_f=1)
            need(scene_fill.suggest(item["id"], short, words, FPS) is None, "short beat accepted")
            need(scene_fill.suggest(item["id"], dict(beat, end_f=9999), words, FPS) is None, "long beat accepted")
        counter = scene_fill.suggest("counter", beat, words, FPS)
        need(counter is not None and counter["params"] == {"value": 47}, "said counter missing or wrong")
        need(scene_fill.suggest("counter", dict(beat, value=48), words, FPS) is None, "unsaid counter accepted")
        for item in cat:
            if item["category"] != "stat-card":
                continue
            need(scene_fill.suggest(item["id"], dict(beat, value=48), words, FPS) is None,
                 "unsaid stat-card accepted")
            fill = scene_fill.suggest(item["id"], beat, words, FPS)
            need(fill is not None, "said stat-card missing")
            if "stat" in fill["slots"]:
                need(fill["slots"]["stat"] == "47", "big-number slot lost the said number")
        outside = ["47", "nothing", "numeric", "here"]
        local = dict(beat, speech_anchor={"w0": 1, "w1": 3})
        need(scene_fill.suggest("counter", local, outside, FPS) is None, "number outside beat accepted")
        need(scene_fill.suggest("counter", beat, ["forty-seven"] * len(words), FPS) is None,
             "spelled-out number accepted despite scene_check")
        for planted in (dict(counter, slots={"label": "x" * 31}), dict(counter, params={"value": 48})):
            try:
                honest(planted)
            except Fail:
                pass
            else:
                raise Fail("the same honesty assertions accepted a planted bad fill")
        scene_fill.write_catalog(reel, [beat], words, FPS)
        saved = load(reel / "scenes/catalog.json")
        fills = load(reel / "scenes/suggest.json")[beat["id"]]
        need(fills["counter"] == counter, "written counter differs")
        for item in saved:
            need(item["preview"] == f"scenes/{item['id']}.png", "preview is not reel-relative")
            need((reel / item["preview"]).read_bytes() ==
                 (scene_check.SCENES / item["id"] / "preview.png").read_bytes(), "preview copy differs")
        for fill in fills.values():
            honest(fill)
        # The CLI must use the newer board file, and always the cut transcript.
        import make_beat_map
        items = load(reel / "work/edit_map.cut.json")["words"]
        state = make_beat_map.build_doc(reel, PLAN, WORDS, items, "work/edit_map.cut.json",
                                       reel / "work/edit_map.cut.json", FPS, TOTAL_F)
        state_path, send_path = reel / "beat-map.state.json", reel / "beat-map-selection.json"
        write_json(state_path, state)
        sent = copy.deepcopy(state)
        sent["beats"][0]["speech_anchor"] = {"w0": 1, "w1": 3, "text": "big wins for"}
        write_json(send_path, sent)
        stamp = state_path.stat().st_mtime_ns
        os.utime(send_path, ns=(stamp + 2000000000, stamp + 2000000000))

        def cli(*args):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = scene_fill.main(list(args))
            return code, buf.getvalue().strip()

        args = ("--reel-dir", str(reel), "--beat", "b_001", "--scene", "callout")
        rc, out = cli("suggest", *args)
        need(rc == 0 and json.loads(out)["slots"]["text"] == "big wins for", "CLI ignored the newer Send")
        os.utime(state_path, ns=(stamp + 4000000000, stamp + 4000000000))
        rc, out = cli("suggest", *args)
        need(rc == 0 and json.loads(out)["slots"]["text"] == "Three big wins for", "CLI ignored the newer state")
        rc, out = cli("catalog", "--reel-dir", str(reel))
        need(rc == 0 and len(out.splitlines()) == 1, "catalog CLI did not print one summary line")
        need(load(reel / "scenes/suggest.json")["b_001"]["callout"]["slots"]["text"] == "Three big wins for",
             "catalog CLI did not use the cut transcript")
        for bad_args in (("catalog", "--reel-dir", str(reel / "missing")),
                         ("suggest", "--reel-dir", str(reel), "--beat", "absent", "--scene", "callout")):
            rc, out = cli(*bad_args)
            need(rc == 2 and len(out.splitlines()) == 1 and "Traceback" not in out, "CLI error is not one plain exit-2 line")
        state_path.write_bytes(b"{broken\njson")
        send_path.unlink()  # the deliberately corrupt state must be the file selected
        rc, out = cli("catalog", "--reel-dir", str(reel))
        need(rc == 2 and len(out.splitlines()) == 1, "unexpected CLI error was not flattened to one exit-2 line")


def schema_scene_case():
    sys.path.insert(0, str(CANVAS))
    import beat_schema as bs
    import make_beat_map
    with tempfile.TemporaryDirectory() as tmp:
        reel = Path(tmp) / "schema"
        reel_fixture(reel)
        items = load(reel / "work/edit_map.cut.json")["words"]
        bm = make_beat_map.build_doc(reel, PLAN, WORDS, items, bs.DEFAULT_WORDS,
                                    reel / bs.DEFAULT_WORDS, FPS, TOTAL_F)
        sketches = load(reel / "sketches.state.json")
        fills = [None, {"id": "callout", "slots": {"text": "Hi"}},
                 {"id": "counter", "slots": {"label": ""}, "params": {"value": 3, "dark": True, "font": "Inter"}}]
        for fill in fills:
            bm["beats"][0]["scene"] = fill
            bs.validate_beat_map(bm, WORDS)
            if fill is not None:
                bs.validate_sketches(dict(sketches, scenes={"b_001": fill}), bm)
        for fill, field in [({}, "id"), ({"id": " ", "slots": {}}, "id"),
                            ({"id": "x", "slots": {"text": 3}}, "slots"),
                            ({"id": "x", "slots": {}, "other": 1}, "other"),
                            ({"id": "x", "slots": {}, "params": {"x": []}}, "params")]:
            bm["beats"][0]["scene"] = fill
            for problems in [bs.beat_map_problems(bm),
                             bs.sketches_problems(dict(sketches, scenes={"b_001": fill}), bm)]:
                need(problems and any("b_001" in p and field in p and "\n" not in p for p in problems),
                     f"scene error must name beat and field: {problems}")
        problems = bs.sketches_problems(dict(sketches, scenes={"absent": fills[1]}), bm)
        need(any("absent" in p and "beat id" in p for p in problems), "unknown sketches scene beat accepted")
        need(bs.sketches_problems(dict(sketches, scenes=[]), bm), "non-object scenes accepted")
        need(bs.sketches_problems(dict(sketches, scenes={"b_001": None}), bm), "null sketches scene accepted")


def main():
    ensure_utf8_output()
    if "--schema-scene-only" in sys.argv:
        schema_scene_case()
        print("schema_scene passed")
        return 0
    if "--scene-fill-only" in sys.argv:
        scene_fill_case()
        print("scene_fill passed")
        return 0
    tools, missing = find_tools()
    if missing:
        print(f"✗ This test needs an installed editor state: set EDITOR_SE_HOME to one "
              f"(node, chrome and puppeteer-core missing: {', '.join(missing)})")
        return 1
    scratch = Path(tempfile.mkdtemp(prefix="s6a_boards_"))
    env = dict(os.environ, HOME=str(scratch), USERPROFILE=str(scratch))  # H-R16; EDITOR_SE_HOME/LOCALAPPDATA kept
    ws = scratch / "ws"
    check_deps.atomic_write(rt.config_path(ws), json.dumps({"ports": {"board": free_port()}}))
    assert check_deps.write_config(ws, engine=None, nle="none")
    videos = ws / rt.read_config(ws)["paths"]["videos"]
    reel = videos / "demo-reel"
    reel_fixture(reel)
    py = [sys.executable, "-X", "utf8", "-I"]
    S = {"server": None, "port": None, "browsers": 0}
    procs, results = [], []

    def case(name, fn):
        try:
            fn()
            results.append(True)
            print(f"✓ {name}", flush=True)
        except Exception as e:  # any crash in a case is that case's failure, the rest still run
            results.append(False)
            print(f"✗ {name}: {e.__class__.__name__ + ': ' if not isinstance(e, Fail) else ''}{e}", flush=True)

    def start(port):
        if S["server"]:
            S["server"].terminate()
            S["server"].wait(10)
        need(check_deps.write_config(ws, ports={"board": port}), "could not set the board port")
        p = subprocess.Popen(py + [str(SERVER), "--root", str(ws)], env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        procs.append(p)
        t = threading.Timer(20, p.kill)  # a hung start fails the case instead of blocking the test
        t.start()
        line = p.stdout.readline().strip()
        t.cancel()
        need(line.startswith("Editor boards: http://127.0.0.1:") and line.endswith("/"), f"server said {line!r}")
        S["server"], S["port"] = p, int(line.rsplit(":", 1)[1].rstrip("/"))
        return S["port"]

    def url(board, reel_name="demo-reel"):
        return f"http://127.0.0.1:{S['port']}/editor/{board}/?reel={reel_name}"

    def browse(page_url, actions):
        """A NEW browser (fresh profile) runs the actions; returns its reads."""
        S["browsers"] += 1
        job = scratch / f"job-{S['browsers']}.json"
        write_json(job, {"url": page_url, "userDataDir": str(scratch / f"profile-{S['browsers']}"), "actions": actions})
        p = run([tools["node"], str(CLICK), tools["pup"], tools["chrome"], str(job)])
        try:
            out = json.loads(p.stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            out = {}
        need(p.returncode == 0, f"browser: {out.get('error') or p.stderr.strip()[-500:]}; "
                                f"page showed {json.dumps(out.get('last'))[:600]}; page errors {out.get('errors')}")
        return out["reads"]

    def check(*args):
        p = run(py + [str(SCHEMA), *map(str, args)], env=env)
        return p.returncode, p.stdout + p.stderr

    def seed(*extra):
        return run(py + [str(SEED), "--reel-dir", str(reel), "--plan", "work/plan.json", "--words",
                         "work/edit_map.cut.json", "--cuts", "work/cuts.json", *extra], cwd=reel, env=env)

    state = reel / "beat-map.state.json"
    sel = reel / "beat-map-selection.json"

    # ---- forward ----
    def c1():
        p = seed()
        need(p.returncode == 0, f"make_beat_map exit {p.returncode}: {(p.stdout + p.stderr).strip()[-500:]}")
        rc, out = check("check", state)
        need(rc == 0, f"beat_schema check exit {rc}: {out.strip()[-500:]}")
        S["seeded"] = state.read_bytes()
        beats = load(state)["beats"]
        tiled = [b for b in beats if b["layout"] != "overlay"]
        need(len(tiled) == 4 and len(beats) == 5, f"{len(tiled)} tiled + {len(beats) - len(tiled)} overlay beats")
        need(tiled[0]["start_f"] == 0, f"first beat starts at {tiled[0]['start_f']}")
        gaps = [(a["id"], a["end_f"], b["start_f"]) for a, b in zip(tiled, tiled[1:]) if a["end_f"] != b["start_f"]]
        need(not gaps, f"beats don't tile: {gaps}")
        need(tiled[-1]["end_f"] == TOTAL_F, f"last beat ends at {tiled[-1]['end_f']}, not {TOTAL_F}")
        S["bid"] = beats[1]["id"]

    def edits_shown(r, bid):
        row = next((x for x in r["rows"] if x["beat"] == bid), None)
        need(row, f"no row for {bid}: {r['rows']}")
        need((row["layout"], row["value"], row["note"], row["changed"]) == ("split", "3", "tighter here", True),
             f"row {bid} shows {row}")
        need(r["marks"].get("5") == "key", f"word 5 mark is {r['marks'].get('5')!r}")
        need(r["needs"] == "logo please", f"needs shows {r['needs']!r}")
        need(not r["empty"], "#empty is showing")

    def c2():
        start(S["A"])
        bid = S["bid"]
        row = f'#beats tr[data-beat="{bid}"]'
        reads = browse(url("beat-map"), [
            {"do": "goto"}, {"do": "wait", "sel": row},
            {"do": "select", "sel": f"{row} select[name=layout]", "value": "split"},
            {"do": "type", "sel": f"{row} input[name=value]", "text": "3"},
            {"do": "type", "sel": f"{row} textarea[name=note]", "text": "tighter here"},
            {"do": "click", "sel": '#beats span.word[data-w="5"]'},
            {"do": "click", "sel": '#beats span.word[data-w="5"]'},
            {"do": "type", "sel": "#needs", "text": "logo please"},
            {"do": "waitState", "state": "saved", "change": True},
            {"do": "goto"}, {"do": "wait", "sel": row}, {"do": "read"},
            {"do": "click", "sel": "#send"}, {"do": "waitState", "state": "sent"}, {"do": "read"}])
        edits_shown(reads[0], bid)
        S["sent_read"] = reads[1]

    def c3():
        need(S.get("sent_read"), "the Send step did not run (case 2 failed first)")
        need(sel.is_file(), "no beat-map-selection.json")
        rc, out = check("check", sel)
        need(rc == 0, f"beat_schema check exit {rc}: {out.strip()[-500:]}")
        doc, bid = load(sel), S["bid"]
        beat = next((b for b in doc["beats"] if b["id"] == bid), {})
        need((beat.get("layout"), beat.get("value")) == ("split", 3), f"beat {bid} sent as {beat}")
        need(doc["notes"].get(bid) == "tighter here", f"notes sent as {doc['notes']}")
        need({"w": 5, "mark": "key"} in doc["word_marks"], f"word_marks sent as {doc['word_marks']}")
        need(doc["needs"] == "logo please", f"needs sent as {doc['needs']!r}")
        need(iso(doc.get("sent_at")), f"selection sent_at is {doc.get('sent_at')!r}")
        need(iso(load(state).get("sent_at")), f"beat-map.state.json on disk has sent_at {load(state).get('sent_at')!r}")

    def c4():
        got = start(S["B"])
        need(got != S["A"], f"restarted on port {got}, the same as before")
        reads = browse(url("beat-map"), [{"do": "goto"}, {"do": "wait", "sel": f'#beats tr[data-beat="{S["bid"]}"]'},
                                         {"do": "read"}])
        edits_shown(reads[0], S["bid"])
        need((reads[0]["status"] or {}).get("state") == "sent", f"status is {reads[0]['status']}")

    def c5():
        need(S["port"] != S["A"], "case 4 did not restart the server on a new port")
        dsel = '#directions section.direction[data-id="%s"]'
        reads = browse(url("sketches"), [
            {"do": "goto"}, {"do": "wait", "sel": dsel % D2}, {"do": "wait", "sel": "#lock"}, {"do": "read"},
            {"do": "type", "sel": (dsel % D1) + " textarea[name=note]", "text": "brighter"},
            {"do": "type", "sel": "#note", "text": "ok"},
            {"do": "click", "sel": (dsel % D2) + ' input[type=radio][name=pick]'},
            {"do": "click", "sel": "#lock"},
            {"do": "waitState", "state": "saved", "change": True},
            {"do": "click", "sel": "#send"}, {"do": "waitState", "state": "sent"}])
        need(reads[0]["lock"] == {"disabled": True}, f"before a pick #lock is {reads[0]['lock']}")
        locked = load(reel / "sketches.state.json").get("locked_at")
        need(iso(locked), f"sketches.state.json on disk has locked_at {locked!r}")
        ssel = reel / "sketches-selection.json"
        need(ssel.is_file(), "no sketches-selection.json")
        rc, out = check("check-sketches", ssel, "--beat-map", state)
        need(rc == 0, f"check-sketches exit {rc}: {out.strip()[-500:]}")
        need(load(ssel)["pick"] == D2, f"pick sent as {load(ssel)['pick']!r}")
        prev = S["port"]
        got = start(free_port(prev))
        need(got != prev, f"restarted on port {got}, the same as before")
        r = browse(url("sketches"), [{"do": "goto"}, {"do": "wait", "sel": dsel % D2}, {"do": "read"}])[0]
        picked = [d["id"] for d in r["directions"] if d["picked"]]
        need(picked == [D2], f"picked directions shown: {picked}")
        need(r["locked"], "#directions is not .locked after the restart")
        d1 = next((d for d in r["directions"] if d["id"] == D1), {})
        need(d1.get("note") == "brighter" and r["note"] == "ok", f"notes shown: {D1} {d1.get('note')!r}, page {r['note']!r}")

    def c6():
        (videos / "empty-reel").mkdir()
        reads = browse(url("beat-map", "empty-reel"), [
            {"do": "goto"}, {"do": "wait", "sel": "#empty", "visible": True}, {"do": "read"},
            {"do": "goto", "url": url("sketches", "empty-reel")}, {"do": "wait", "sel": "#empty", "visible": True},
            {"do": "read"}])
        need(reads[0]["empty"] and reads[1]["empty"], f"#empty shown: beat-map {reads[0]['empty']}, sketches {reads[1]['empty']}")

    # ---- reverse ----
    def c7():
        need(S.get("seeded"), "no seeded doc (case 1 failed)")
        good = json.loads(S["seeded"])
        planted = scratch / "planted"
        planted.mkdir()

        def plant(name, fn):
            d = copy.deepcopy(good)
            fn(d["beats"][0])
            write_json(planted / name, d)
            return check("check", planted / name)
        write_json(planted / "valid.json", good)
        rc, out = check("check", planted / "valid.json")
        need(rc == 0, f"the unplanted doc exit {rc}: {out.strip()[-300:]}")
        for name, fn, words in (("no-id.json", lambda b: b.pop("id"), ("missing id",)),
                                ("grid.json", lambda b: b.update(layout="grid"), ("layout 'grid'",)),
                                ("start-after-end.json", lambda b: b.update(start_f=b["end_f"] + 5),
                                 ("start_f", "after end_f"))):
            rc, out = plant(name, fn)
            need(rc == 1 and all(w in out for w in words), f"{name}: exit {rc}, output {out.strip()[-300:]!r}")

    def c8():
        need(S.get("seeded"), "no seeded doc (case 1 failed)")
        bad_reel = videos / "broken-reel"
        shutil.copytree(reel / "work", bad_reel / "work")
        doc = json.loads(S["seeded"])
        doc["reel"] = "broken-reel"
        doc["beats"][0]["layout"] = "grid"
        write_json(bad_reel / "beat-map.state.json", doc)
        browse(url("beat-map", "broken-reel"), [{"do": "goto"}, {"do": "wait", "sel": "#send"},
                                                {"do": "click", "sel": "#send"}, {"do": "waitState", "state": "error"}])
        need(not (bad_reel / "beat-map-selection.json").exists(), "beat-map-selection.json was written")

    def c9():
        need(state.is_file(), "no beat-map.state.json to protect (case 1 failed)")
        before = state.read_bytes()
        p = seed()
        need(p.returncode == 1, f"a second run exit {p.returncode}, not 1")
        need(state.read_bytes() == before, "the second run changed beat-map.state.json")
        p = seed("--replace")
        need(p.returncode == 0, f"--replace exit {p.returncode}: {(p.stdout + p.stderr).strip()[-300:]}")
        prev = reel / "beat-map.state.json.prev"
        need(prev.is_file() and prev.read_bytes() == before, "beat-map.state.json.prev is not the old file")

    def c10():
        port = S["port"]
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("POST", "/videos/demo-reel/__save?board=beat-map&name=other.json", body=b'{"v": 1}',
                  headers={"Origin": f"http://127.0.0.1:{port}", "Content-Type": "application/json"})
        status = c.getresponse().status
        c.close()
        need(status == 403, f"HTTP {status}, not 403")
        need(not (reel / "other.json").exists(), "other.json was written")

    def sketches_scene(skip_guard=False):
        name = "scene-reverse" if skip_guard else "scene-forward"
        sr = videos / name
        reel_fixture(sr)
        scene_fixture(sr)
        p = run(py + [str(SEED), "--reel-dir", str(sr), "--plan", str(sr / "work/plan.json")], env=env)
        need(p.returncode == 0, f"scene fixture seed: {p.stdout} {p.stderr}")
        hub = ws / rt.read_config(ws)["paths"]["editor"] / "hub"
        hub.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(__file__).parent / "fixtures/stub-hub.html", hub / "index.html")
        shutil.copyfile(DOCTOR / "boards.json", hub / "boards.json")
        S["browsers"] += 1
        job = scratch / f"scene-job-{S['browsers']}.json"
        write_json(job, {"url": url("hub", name), "userDataDir": str(scratch / f"profile-{S['browsers']}"),
                         "selection": str(sr / "sketches-selection.json"), "skipGuard": skip_guard})
        p = run([tools["node"], "-e", SCENE_BROWSER, tools["pup"], tools["chrome"], str(job)])
        try:
            result = json.loads(p.stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            result = {"error": p.stderr[-500:]}
        if skip_guard:
            need(p.returncode != 0 and result.get("error") == "overflow guard failed",
                 f"skipping the guard did not fail the overflow assertion: {result}")
        else:
            need(p.returncode == 0 and result.get("ok"), f"scene iframe: {result}")
            sent = result["sent"]
            import beat_schema
            beat_schema.validate_sketches(sent, load(sr / "beat-map.state.json"))
            beat_schema.validate_sketches(load(sr / "sketches-selection.json"), load(sr / "beat-map.state.json"))
            need(sent["scenes"]["b_001"] == {"id": "callout", "slots": {"text": "Edited words"}, "params": {}},
                 "sent scene differs")
            need(sent["directions"] == load(sr / "sketches.state.json")["directions"], "existing directions changed")
            need("b_001" not in load(sr / "sketches-selection.json")["scenes"], "scene removal not saved")

    def scene_fixture(sr):
        words = load(sr / "work/edit_map.cut.json")
        words["words"][4]["word"] = "47"
        write_json(sr / "work/edit_map.cut.json", words)
        plan = copy.deepcopy(PLAN)
        plan["beats"][1]["value"] = 47
        write_json(sr / "work/plan.json", plan)

    def beatmap_scene(skip_guard=False, source="state"):
        name = "beatmap-" + ("reverse" if skip_guard else source)
        sr = videos / name
        reel_fixture(sr)
        scene_fixture(sr)
        p = run(py + [str(SEED), "--reel-dir", str(sr), "--plan", str(sr / "work/plan.json")], env=env)
        need(p.returncode == 0, f"beatmap fixture seed: {p.stdout} {p.stderr}")
        sk = load(sr / "sketches.state.json")
        sk["scenes"] = {"b_001": {"id": "callout", "slots": {"text": "From Sketches"}, "params": {}}}
        write_json(sr / ("sketches.state.json" if source == "state" else "sketches-selection.json"), sk)
        hub = ws / rt.read_config(ws)["paths"]["editor"] / "hub"
        hub.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(__file__).parent / "fixtures/stub-hub.html", hub / "index.html")
        shutil.copyfile(DOCTOR / "boards.json", hub / "boards.json")
        S["browsers"] += 1
        job = scratch / f"beatmap-job-{S['browsers']}.json"
        write_json(job, {"url": url("hub", name), "userDataDir": str(scratch / f"profile-{S['browsers']}"),
                         "selection": str(sr / "beat-map-selection.json"), "skipGuard": skip_guard})
        p = run([tools["node"], "-e", BEATMAP_BROWSER, tools["pup"], tools["chrome"], str(job)])
        try:
            result = json.loads(p.stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            result = {"error": p.stderr[-500:]}
        if skip_guard:
            need(p.returncode != 0 and result.get("error") == "overflow guard failed", f"reverse plant: {result}")
            return
        need(p.returncode == 0 and result.get("ok"), f"beatmap iframe: {result}")
        import beat_schema, compose
        from fractions import Fraction
        heard = beat_schema.load_words(sr / beat_schema.DEFAULT_WORDS)
        sent = load(sr / "beat-map-selection.json")
        beat_schema.validate_beat_map(result["sent"], heard)
        beat_schema.validate_beat_map(sent, heard)

        def preflight(doc):
            inp = {"beats": copy.deepcopy(doc["beats"]), "rate": Fraction(FPS), "words": heard,
                   "total": TOTAL_F, "cut_frames": [120], "fps": "30/1"}
            with contextlib.redirect_stdout(io.StringIO()):
                compose.plan(inp, None)
        preflight(sent)
        # Run the actual Send through the compositor, then plant an unsaid slot number in that Send.
        sent["beats"][1]["scene"]["slots"]["label"] = "999 people"
        write_json(sr / "beat-map-selection.json", sent)
        try:
            preflight(load(sr / "beat-map-selection.json"))
        except compose.Stop as e:
            need(any("not said" in p or "not in" in p for p in e.lines), f"wrong compositor refusal: {e.lines}")
        else:
            raise Fail("compositor accepted an unsaid slot number")

    S["A"] = free_port()
    S["B"] = free_port(S["A"])
    try:
        case("schema_scene: scene shapes and Sketches beat keys", schema_scene_case)
        case("scene_fill: catalog, honest fills, timing and planted bad suggestions", scene_fill_case)
        if "--scenes-only" in sys.argv:
            start(S["A"])
            case("sketches_scene: iframe picker, maxChars, Send, restore and remove", sketches_scene)
            case("sketches_scene reverse: skipping maxChars fails the same overflow assertion", lambda: sketches_scene(True))
            case("beatmap_scene: iframe picker, Sketches state, Send and compositor", beatmap_scene)
            case("beatmap_scene: Sketches Send offered in one click", lambda: beatmap_scene(source="selection"))
            case("beatmap_scene reverse: skipping maxChars fails", lambda: beatmap_scene(True))
            return 0 if all(results) else 1
        case("1 seed: make_beat_map writes a valid map whose beats tile 0..end", c1)
        case("7 schema rejects a beat with no id, layout grid, start_f > end_f", c7)
        case("2 edit + reload: layout, value, note, word mark and needs survive a reload", c2)
        case("3 Send: beat-map-selection.json is valid and carries the edits and sent_at", c3)
        case("4 port change + new browser: the edits and sent come back from disk", c4)
        case("5 sketches: lock waits for a pick; pick, lock, notes saved, Send valid, restored on a new port", c5)
        case("6 empty: a reel with no beat map or sketches shows #empty on both pages", c6)
        case("8 the board won't send a broken doc", c8)
        case("10 __save refuses a name outside the board's writes list", c10)
        case("9 seed refuses to overwrite; --replace keeps .prev", c9)
        case("sketches_scene: iframe picker, maxChars, Send, restore and remove", sketches_scene)
        case("sketches_scene reverse: skipping maxChars fails the same overflow assertion", lambda: sketches_scene(True))
        case("beatmap_scene: iframe picker, Sketches state, Send and compositor", beatmap_scene)
        case("beatmap_scene: Sketches Send offered in one click", lambda: beatmap_scene(source="selection"))
        case("beatmap_scene reverse: skipping maxChars fails", lambda: beatmap_scene(True))
    finally:
        for p in procs:
            if p.poll() is None:
                p.kill()
                p.wait(10)
            p.stdout.close()
        shutil.rmtree(scratch, ignore_errors=True)
    passed = sum(results)
    print(f"{passed} passed, {len(results) - passed} failed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
