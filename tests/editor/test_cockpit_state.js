// Headless M9 proof of the real mod hooks; Claude's loader/UI contract is covered by plugin test in the lane.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), os = require("node:os"), path = require("node:path");
const {pathToFileURL} = require("node:url"), {stripTypeScriptTypes} = require("node:module");
const plugin = path.resolve(__dirname, "../../plugins/editor-superengine");

(async () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "editor-m9-"));
  try {
    const logicPath = path.join(temp, "logic.mjs"), registerPath = path.join(temp, "register.mjs");
    fs.writeFileSync(logicPath, stripTypeScriptTypes(fs.readFileSync(path.join(plugin, "hooks/mod/logic.ts"), "utf8")));
    fs.writeFileSync(registerPath, stripTypeScriptTypes(fs.readFileSync(path.join(plugin, "hooks/mod/register.ts"), "utf8"))
      .replace("from './logic'", "from './logic.mjs'"));
    const logic = await import(pathToFileURL(logicPath).href);
    const {register} = await import(pathToFileURL(registerPath).href);
    const file = name => ({name, kind: "file", size: 1, mtimeMs: 2000});
    for (const [top, raw, expected] of [
      [[file("RAW.mp4")], [], "Cut"], [[], [file("x.mp4")], "Cut"],
      [[], [file("x.mp4"), file("y.MOV")], "Cut"], [[], [], "Record"],
      [[file("RAW.mp4.prev")], [file("x.mp4.tmp")], "Record"]
    ]) {
      const reel = {name: "Fresh", lists: {root: logic.ok(top), raw: logic.ok(raw), work: logic.ok([]), renders: logic.ok([])}, json: {}, probe: {}};
      assert.equal(logic.STAGES[logic.reelOf(reel, 3000, 0, {}).cur].name, expected);
    }

    const root = path.join(temp, "workspace").replaceAll("\\", "/");
    fs.mkdirSync(root + "/editor", {recursive: true});
    fs.mkdirSync(root + "/media/reels/Fresh", {recursive: true});
    fs.writeFileSync(root + "/editor/editor.config.json", JSON.stringify({paths: {editor: "local/boards", videos: "media/reels"}}));
    fs.writeFileSync(root + "/media/reels/Fresh/beat-map-selection.json", "{}");
    const hooks = new Map(), store = new Map(), writes = [], logs = [];
    let refuseWrite = false;
    register((event, filter, handler) => hooks.set(event, handler || filter));
    const env = {
      session: {cwd: async () => root}, clock: {now: async () => 1000, after: () => {}, every: () => ({cancel() {}})},
      store: {get: async key => store.get(key), set: async (key, value) => store.set(key, value)},
      command: {register: async () => {}}, ui: {log: (...args) => logs.push(args), status: () => {}, open: async () => ({})},
      process: {run: async () => ({exitCode: 1, stdout: ""})},
      fs: {
        read: async p => fs.readFileSync(p, "utf8"),
        stat: async p => {const s = fs.statSync(p); return {kind: s.isFile() ? "file" : "dir", mtimeMs: s.mtimeMs, isLink: false};},
        list: async p => fs.readdirSync(p, {withFileTypes: true}).map(d => {
          const s = fs.statSync(path.join(p, d.name));
          return {name: d.name, kind: d.isDirectory() ? "dir" : "file", size: s.size, mtimeMs: s.mtimeMs, isLink: false};
        }),
        write: async (p, text) => {
          writes.push({path: p, text});
          if (refuseWrite) throw Error("refused snapshot");
          fs.mkdirSync(path.dirname(p), {recursive: true}); fs.writeFileSync(p, text);
        }
      }
    };
    const start = () => hooks.get("session.start")(env, {}, async () => ({ok: true}));
    await start();
    const snapshot = root + "/local/boards/hub/cockpit-state.json";
    assert.equal(writes.length, 1, "one snapshot write on session start");
    assert.equal(writes[0].path, snapshot);
    assert.deepEqual(JSON.parse(fs.readFileSync(snapshot, "utf8")), {baseline: 1000, acked: {}});
    store.set("editorAcked", {"old/grade-selection.json": 20});
    await start();
    assert.deepEqual(JSON.parse(writes.at(-1).text), {baseline: 1000, acked: {"old/grade-selection.json": 20}});
    assert.equal(writes.length, 2, "existing baseline also exported at session start");
    const ack = () => hooks.get("tool.call")(env, {file_path: root + "/media/reels/Fresh/beat-map-selection.json"}, async () => ({result: "read"}));
    assert.deepEqual(await ack(), {result: "read"});
    assert.equal(writes.length, 3, "one snapshot write after acknowledgement");
    const acked = store.get("editorAcked");
    assert.ok(acked["Fresh/beat-map-selection.json"] > 1000);
    assert.deepEqual(JSON.parse(fs.readFileSync(snapshot, "utf8")), {baseline: 1000, acked});
    refuseWrite = true;
    await start();
    assert.deepEqual(await ack(), {result: "read"}, "refused export never changes the successful Read result");
    assert.deepEqual(logs, [], "export failures silent");
    console.log("ok test_cockpit_state.js: 5 Record layouts; configured snapshot on start + ack; failures silent");
  } finally {
    fs.rmSync(temp, {recursive: true, force: true});
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
