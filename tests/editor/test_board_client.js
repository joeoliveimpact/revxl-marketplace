// node tests/editor/test_board_client.js : board-client.js without a browser (S4a). Exit 0 = every assert held.
"use strict";
const assert = require("assert");
const path = require("path");
const BC = require(path.join(__dirname, "..", "..", "plugins", "editor-superengine", "skills", "editor-doctor", "assets", "board-client.js"));

(async () => {
  // Controls resolve once per mode change; manual disclosure choices survive same-mode events.
  async function controls(query, local, config, fail = false, refuseCacheWrite = false) {
    const sections = [{open: true}, {open: true}], events = {}, values = new Map();
    if (local !== undefined) values.set("editor-controls", local);
    let added;
    const env = {
      location: {search: query},
      localStorage: {getItem: k => values.get(k) ?? null, setItem: (k, v) => {
        if (refuseCacheWrite) throw Error("blocked storage");
        values.set(k, v);
      }},
      document: {querySelectorAll: selector => { assert.strictEqual(selector, "details.advanced-controls"); return sections; },
        documentElement: {}, dispatchEvent: () => {},
        addEventListener: (name, fn) => { events[name] = fn; }},
      addEventListener: (name, fn) => { events[name] = fn; },
      MutationObserver: class {constructor(fn) { added = fn; } observe() {}},
      fetch: async url => {
        assert.strictEqual(url, "/editor/hub/hub-data.json");
        if (fail) throw new Error("offline");
        return {ok: true, json: async () => ({config: {controls: config}})};
      }
    };
    const controller = BC.initControls(env);
    await controller.ready;
    return {controller, sections, values, events, added};
  }
  for (const [query, local, config, expected] of [
    ["?controls=simple", "advanced", "advanced", "simple"],
    ["?controls=advanced", "simple", "simple", "advanced"],
    ["", "advanced", "simple", "simple"],
    ["", "simple", "advanced", "advanced"],
    ["", undefined, "advanced", "advanced"],
    ["", undefined, undefined, "simple"],
    ["?controls=invalid", "invalid", "advanced", "advanced"],
    ["?controls=ADVANCED", "", "invalid", "simple"]
  ]) {
    const c = await controls(query, local, config);
    assert.strictEqual(c.controller.mode(), expected);
    assert.strictEqual(c.values.get("editor-controls"), config === "advanced" ? "advanced" : "simple", "config refreshes the cache even with a query override");
    assert.ok(c.sections.every(s => s.open === (expected === "advanced")));
  }
  const offline = await controls("", undefined, "advanced", true);
  assert.strictEqual(offline.controller.mode(), "simple", "fetch failure folds sections");
  const offlineLocal = await controls("", "advanced", undefined, true);
  assert.strictEqual(offlineLocal.controller.mode(), "advanced", "offline still honors a valid local default");
  const readOnlyCache = await controls("", "advanced", "simple", false, true);
  assert.strictEqual(readOnlyCache.controller.mode(), "simple", "config still wins if its cache write is refused");
  const cleared = await controls("", "simple", "advanced");
  cleared.values.delete("editor-controls"); cleared.events.storage({key: null});
  assert.strictEqual(cleared.controller.mode(), "advanced", "clearing storage falls back to config");
  const c = await controls("", "simple", "simple");
  c.sections[0].open = true;
  c.events.storage({key: "editor-controls"});
  assert.strictEqual(c.sections[0].open, true, "same mode keeps a hand-opened section");
  c.values.set("editor-controls", "advanced");
  c.events.storage({key: "unrelated"});
  assert.strictEqual(c.sections[1].open, false);
  c.events.storage({key: "editor-controls"});
  assert.ok(c.sections.every(s => s.open));
  c.sections.push({open: false}); c.added();
  assert.strictEqual(c.sections[2].open, true, "generated row inherits current mode");
  c.sections[0].open = false; c.added();
  assert.strictEqual(c.sections[0].open, false, "DOM updates keep a hand-closed section");
  c.sections[0].dataset = {controlsKey: "row-1"};
  c.events.toggle({target: c.sections[0]});
  c.sections[0] = {open: true, dataset: {controlsKey: "row-1"}};
  c.added();
  assert.strictEqual(c.sections[0].open, false, "rebuilt row keeps its manual fold");
  c.values.set("editor-controls", "simple"); c.events.storage({key: null});
  assert.ok(c.sections.every(s => !s.open), "storage clear and mode changes re-apply");
  const pinned = await controls("?controls=simple", "simple", "advanced");
  pinned.values.set("editor-controls", "advanced"); pinned.events.storage({key: "editor-controls"});
  assert.strictEqual(pinned.controller.mode(), "simple", "query wins on storage events too");
  // a server that is gone: fetch rejects, so save() raises the banner with the unsaved state in the paste line
  const shown = [], store = new Map();
  const storage = {getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, v)};
  const failing = () => Promise.reject(new TypeError("Failed to fetch"));
  const bc = BC.create({board: "cut-board", reel: "reel-07", fetch: failing, storage, heartbeat: false,
                        onGone: (t) => shown.push(t)});
  const state = {lines: [{pick: 2}], note: "keep the second take"};
  const r = await bc.save(state);
  assert.deepStrictEqual(r, {ok: false, status: 0});
  assert.strictEqual(shown.length, 1, "banner shown once");
  assert.ok(shown[0].startsWith("Restart my editor boards and save this cut-board state for reel reel-07: "), shown[0]);
  assert.ok(shown[0].includes(JSON.stringify(state)), "paste line carries the unsaved state");
  assert.strictEqual(shown[0], BC.bannerText("cut-board", "reel-07", state));
  assert.strictEqual(store.get("editor-boards:reel-07:cut-board"), JSON.stringify(state), "mirrored to localStorage");
  await bc.heartbeat();
  assert.strictEqual(shown.length, 2, "a failed heartbeat shows the banner too");
  // load() with the server gone falls back to this browser's copy
  assert.deepStrictEqual(await bc.load(), state);
  assert.ok(BC.bannerText("hub", "r", null).startsWith("Restart my editor boards"));

  // a working server: the POST carries the JSON content type to the reel's __state endpoint
  const calls = [];
  const ok = (u, o) => { calls.push([u, o]); return Promise.resolve({ok: true, status: 200, json: () => Promise.resolve({a: 1})}); };
  const bc2 = BC.create({board: "sound-board", reel: "reel 8", fetch: ok, storage, heartbeat: false, onGone: () => assert.fail()});
  assert.deepStrictEqual(await bc2.load(), {a: 1});
  await bc2.save({b: 2});
  assert.strictEqual(calls[0][0], "/videos/reel%208/sound-board.state.json");
  assert.strictEqual(calls[1][0], "/videos/reel%208/__state?name=sound-board");
  assert.strictEqual(calls[1][1].method, "POST");
  assert.strictEqual(calls[1][1].headers["Content-Type"], "application/json");

  // mergeCues: refill by beat (id+beat first), saved values win, unmatched kept + flagged, user cues kept
  const saved = [
    {id: "c01", beat: "hook", gain: -3, state: "keep"},
    {id: "c02", beat: "turn", gain: -6, state: "rej"},
    {id: "c03", beat: "gone-beat", gain: -1, state: "keep"},
    {id: "u1", beat: "user added sound 1", user: true, gain: 0},
  ];
  const fresh = [
    {id: "c01", beat: "intro", gain: 0, why: "new"},
    {id: "c02", beat: "hook", gain: 0, why: "fresh why"},
    {id: "c03", beat: "turn", gain: 0},
  ];
  const m = BC.mergeCues(saved, fresh);
  assert.strictEqual(m.length, 5, "nothing dropped");
  assert.deepStrictEqual(m[0], {id: "c01", beat: "intro", gain: 0, why: "new"}, "no saved cue for this beat");
  assert.deepStrictEqual(m[1], {id: "c02", beat: "hook", gain: -3, why: "fresh why", state: "keep"}, "matched by beat");
  assert.strictEqual(m[2].gain, -6);
  assert.deepStrictEqual(m[3], {id: "c03", beat: "gone-beat", gain: -1, state: "keep", unmatched: true});
  assert.ok(!m[4].unmatched && m[4].user, "user cue kept, not flagged");
  assert.ok(!("unmatched" in m[1]));
  const only = BC.mergeCues(saved, fresh, ["state"]);
  assert.deepStrictEqual(only[1], {id: "c02", beat: "hook", gain: 0, why: "fresh why", state: "keep"}, "fields limits the carry-over");
  assert.strictEqual(BC.mergeCues(null, fresh).length, 3);

  console.log("ok test_board_client.js: controls + banner + mergeCues checks passed");
})().catch((e) => { console.error(e); process.exit(1); });
