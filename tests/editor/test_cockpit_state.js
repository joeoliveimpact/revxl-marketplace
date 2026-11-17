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
    assert.ok(logic.BOARDS.includes("motionreview"));
    assert.equal(logic.BOARD_NAME.motionreview, "Motion review");
    assert.ok(logic.FOLDERS.includes("motion/review"));
    const motion = {name:"Motion", lists:{root:logic.ok([file("motion-review-selection.json")]),
      "motion/review":logic.ok([])}, json:{}, probe:{}};
    assert.deepEqual(logic.openSends(motion, 0, {}).map(s => s.board), ["motionreview"]);
    motion.lists["motion/review"] = logic.ok([{...file("review.json"), mtimeMs:3000}]);
    assert.deepEqual(logic.openSends(motion, 0, {}), [], "a newer nested review handles the Send");
    assert.deepEqual(logic.STAGES.map(s => s.name), ["Record", "Cut", "Ear pass", "Beat map", "Look", "Motion", "Sound", "Grade", "Master", "Post"]);
    const lookRule = logic.STAGES.find(s => s.name === "Look").rule;
    const motionRule = logic.STAGES.find(s => s.name === "Motion").rule;
    motion.json["sketches.state.json"] = logic.ok({locked_at:"now"});
    motion.json["motion-review-selection.json"] = logic.ok({sections:[{leave:true}]});
    assert.equal(logic.isDone(lookRule, motion), true, "Look ticks on lock");
    assert.equal(logic.isDone(motionRule, motion), false, "a stale selection does not tick Motion");
    motion.lists["motion/review"] = logic.ok([{...file("review.json"), mtimeMs:2000}]);
    assert.equal(logic.isDone(motionRule, motion), true, "equal timestamps are current");
    motion.lists["motion/review"] = logic.missing();
    assert.equal(logic.isDone(motionRule, motion), true, "an absent review cannot make a selection stale");
    motion.lists["motion/review"] = logic.unreadable("busy");
    assert.equal(logic.isDone(motionRule, motion), false, "an unreadable review cannot establish freshness");
    motion.lists["motion/review"] = logic.ok([]);
    for (const sections of [[{leave:true},{leave:false}], [{leave:1}], [null], "bad"]) {
      motion.json["motion-review-selection.json"] = logic.ok({sections});
      assert.equal(logic.isDone(motionRule, motion), false, "every section must be leave:true");
    }
    motion.json["motion-review-selection.json"] = logic.missing();
    motion.lists.root = logic.ok([]);
    motion.json["sketches.state.json"] = logic.missing();
    motion.json["beat-map.state.json"] = logic.ok({sent_at:0, beats:[{scene:null},{scene:null}]});
    assert.equal(logic.isDone(lookRule, motion), true, "no scenes ticks Look");
    assert.equal(logic.isDone(motionRule, motion), false, "null beat scenes do not approve Motion");
    motion.lists.root = logic.ok([file("motion-review-selection.json")]);
    motion.lists["motion/review"] = logic.ok([{...file("review.json"), mtimeMs:2000}]);
    for (const [selection, expected] of [
      [{none:true, sections:[]}, true],
      [{sections:[{leave:true},{leave:true}]}, true],
      [{sections:[{leave:true},{leave:false, note:"Larger text"}]}, false],
      [{sections:[]}, false],
      [{none:1, sections:[]}, false],
      [{none:true, sections:[{leave:false}]}, false]
    ]) {
      motion.json["motion-review-selection.json"] = logic.ok(selection);
      assert.equal(logic.isDone(motionRule, motion), expected, JSON.stringify(selection));
    }
    motion.json["motion-review-selection.json"] = logic.ok({none:true, sections:[]});
    motion.lists["motion/review"] = logic.ok([{...file("review.json"), mtimeMs:3000}]);
    assert.equal(logic.isDone(motionRule, motion), true, "explicit none does not require review freshness");
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
    console.log("ok test_cockpit_state.js: 10 stages; Look lock; current/stale Motion approvals; explicit none; null scenes and empty approvals blocked; 5 Record layouts; configured snapshot on start + ack; failures silent");
  } finally {
    fs.rmSync(temp, {recursive: true, force: true});
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
