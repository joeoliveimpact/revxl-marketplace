"use strict";
// Data-only checks against the boards' own functions; no browser or dependencies.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const plugin = path.resolve(__dirname, "../../plugins/editor-superengine/skills");
const read = relative => fs.readFileSync(path.join(plugin, relative), "utf8");
function section(source, start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "function boundaries must exist: " + start);
  return source.slice(a, b);
}
function element(tag, attrs = {}, ...children) {
  return {tag, attrs, children, dataset: {}, append(...items) { this.children.push(...items); },
    addEventListener(event, callback) { this[event] = callback; }, setAttribute(key, value) { this.attrs[key] = value; }};
}

function listenNotes() {
  const source = read("reel-first-cuts/boards/tweak-board/index.html");
  const translate = vm.runInNewContext(section(source, "const fmt=", "// transcript") + ";listenNotes", {
    C: {ship_speed: 2, map: [[0, 5, 10, 20], [5, 15, 70, 90]]}
  });
  assert.equal(translate([
    "LISTEN FOR THESE - the automated gates cannot hear them",
    "cut9 runt 0.465s at 74.000 holds speech -> gap restored <- a gap was left long on purpose",
    "  a deletion reached -30.2 dB (above the -32.0 dB speech floor) - a word tail",
    "  may end more abruptly than recorded",
    "  protected beat 12.30-12.90 held at 600 ms - is the timing still funny?",
    "  any word left stranded between two pauses"
  ].join("\n")), [
    "At 0:07.00: a pause was left a little long on purpose so a word isn't clipped.",
    "A word's ending may sound cut short.",
    "At 0:01.15: a pause kept for timing. Is it still funny?",
    "Throughout: any word left stranded between two pauses"
  ].join("\n"));
  assert.equal(translate("protected beat 10-11 held at 500 ms"), "At 0:00.00: a pause kept for timing. Is it still funny?");
  for (const [t, expected] of [[9, "0:00.00"], [20, "0:05.00"], [50, "0:05.00"], [90, "0:15.00"]]) {
    assert.equal(translate(`protected beat ${t}-${t + 1} held at 500 ms`), `At ${expected}: a pause kept for timing. Is it still funny?`);
  }
  assert.equal(translate("cut1 runt 0.2s at 50.000 holds speech -> gap restored <- a gap was left long on purpose"),
    "At 0:05.00: a pause was left a little long on purpose so a word isn't clipped.");
  assert.equal(translate("a deletion reached -30 dB at 74.000 - a word tail\nmay end more abruptly than recorded"),
    "At 0:07.00: a word's ending may sound cut short.");
  assert.equal(translate("LISTEN FOR THESE - nothing else\n\n"), "");
  assert.equal(translate(null), "");
}

function duplicateWarning() {
  const source = read("reel-first-cuts/boards/cut-board/index.html");
  const words = ["Keep", "one", "clip."].map((w, i) => ({w, i}));
  const context = {C: {lines: [{id: "L16", attempts: [{words}]},
    {id: "L17", warn: "Line L16 already says this; keep one", attempts: [{words}]}]},
    S: {lines: [{pick: 0, rm: {}}, {pick: 0, rm: {}}]}};
  const warning = vm.runInNewContext(section(source, "function duplicateWarning(", "function render(") + ";duplicateWarning", context);
  assert.ok(warning(1));
  context.S.lines[0].rm[0] = [0, 1, 2];
  assert.equal(warning(1), "", "striking the other line clears the warning");
  context.S.lines[0].rm[0] = [];
  assert.ok(warning(1), "un-striking the other line restores it");
  context.S.lines[1].rm[0] = [0, 1, 2];
  assert.equal(warning(1), "");
  context.S.lines[1].rm[0] = [];
  context.S.lines[0].drop = true;
  assert.equal(warning(1), "");
  context.S.lines[0].drop = false;
  for (const pair of [["Keep one.", "Keep one."],
    ["We can make this great today", "We can make this really great today"]]) {
    pair.forEach((text, i) => { context.C.lines[i].attempts[0].words = text.split(" ").map((w, i) => ({w, i})); });
    assert.ok(warning(1), "existing short-repeat and retake warnings stay visible");
    context.S.lines[0].rm[0] = context.C.lines[0].attempts[0].words.map(w => w.i);
    assert.equal(warning(1), "");
    context.S.lines[0].rm[0] = [];
  }
}

function sceneChooser(board) {
  const source = read(`reel-canvas-build/boards/${board}/index.html`);
  const catalog = [
    {id: "hf-cta-end-card", title: "Your next step", preview: "still.jpg", slots: [], params: []},
    {id: "hf-hook-title", label: "Opening words", slots: [], params: []},
    {id: "hf-number-card", slots: [], params: []}
  ];
  const doc = {beats: [{id: "b1"}], scenes: {}};
  const context = {sceneCatalog: catalog, sceneSuggestions: {b1: {"hf-cta-end-card": {id: "hf-cta-end-card"}}},
    sketchScenes: {}, doc, el: element, mediaUrl: value => value, edited() {}, document: {querySelectorAll: () => []}};
  const functions = section(source, "function sceneSpec(", "function sceneProblem(");
  const result = vm.runInNewContext(functions + ";({sceneControls, sceneTitle})", context);
  assert.equal(result.sceneTitle(catalog[0]), "Your next step");
  assert.equal(result.sceneTitle(catalog[1]), "Opening words");
  assert.equal(result.sceneTitle(catalog[2]), "Number card");
  const controls = result.sceneControls("b1"), picker = controls.children[1];
  const choice = picker.children[0];
  assert.equal(choice.attrs["data-scene"], "hf-cta-end-card");
  assert.equal(choice.children[0].attrs.alt, "Your next step preview");
  assert.equal(choice.children[1].attrs.text, "Your next step");
  assert.equal(picker.children[2].disabled, true);
  choice.click();
  assert.equal(board === "beat-map" ? doc.beats[0].scene.id : doc.scenes.b1.id, "hf-cta-end-card");
}

function gradeFrame() {
  const source = read("reel-grade/boards/grade-board/index.html"), labels = {textContent: ""};
  const video = {readyState: 2, pause() {}};
  const context = {C: {frames: [{file: "grade-f75.jpg", pct: 75}]}, S: {}, srcReady: false,
    $: id => id === "#src" ? labels : id === "#frames" ? {querySelectorAll: () => []} : video,
    Image: function () {}, GDIR: "/grade/", persist() {}, draw() {}};
  const setFrame = vm.runInNewContext(section(source, "function setFrame(", "function syncTime(") + ";setFrame", context);
  setFrame("grade-f75.jpg", true); assert.equal(labels.textContent, "still at 75%");
  setFrame("video", true); assert.equal(labels.textContent, "live video");
  setFrame("other.jpg", true); assert.equal(labels.textContent, "still");
}

function brollLabels() {
  const source = read("reel-canvas-build/boards/beat-map/index.html");
  const clips = [{ledger_id: "f1", name: "My clip.MOV", src: "broll/real.mp4", frames: 900},
    {ledger_id: "f2", name: "Garden.mp4", src: "broll/generated.mp4", frames: 900, origin: "ai"}];
  const context = {brollClips: clips, el: element, doc: {fps: 30}, edited() {}, invalidBroll: new Set()};
  const controls = vm.runInNewContext(section(source, "function brollControls(", "function row(") + ";brollControls", context);
  const beat = {id: "b1", start_f: 0, end_f: 30, broll: null};
  const wrap = controls(beat, 0), select = wrap.children.find(e => e.tag === "select");
  assert.deepEqual(select.children.map(e => e.attrs.text), ["None", "My clip", "Garden (AI)"]);
  assert.equal(select.children[1].attrs.value, "f1");
  select.value = "f1"; select.change();
  assert.equal(beat.broll.src, "broll/real.mp4", "display labels cannot change the real media path sent");
  assert.equal(beat.broll.ledger_id, "f1");
}

function hubWalk() {
  const source = read("editor-doctor/boards/hub/hub.js"), nodes = new Map();
  const get = id => {
    if (!nodes.has(id)) nodes.set(id, {innerHTML: "", textContent: "", classList: {add() {}, remove() {}},
      getAttribute() { return ""; }, removeAttribute() {}, load() {}});
    return nodes.get(id);
  };
  const sound = {id: "sound", name: "Sound", hint: "Audition your sounds", head: "Sound pass"};
  const post = {id: "post", name: "Post", hint: "Write the caption and post.", head: "Post the reel"};
  const reel = {id: "reel", title: "Reel", stage: "Sound", cur: 0, done: [], sound_board: false,
    sound_pass_ran: false, sound_pack_installed: true, ready_to_post: false,
    frames: [], lanes: [{done: 3, total: 4}], open_sends: [], blocks: [], render_url: "", waiting_on: "you"};
  const data = {reels: [reel], stages: [sound, post], boards: [], config: {nle: "none"}};
  const context = {DATA: data, CUR: reel.id, $: get, $$: () => [], current: () => reel,
    stage: () => data.stages[reel.cur], pct: () => 75, esc: String, reduced: true, skillLabels: {}};
  const functions = vm.runInNewContext(section(source, "function boardFor(", "function drawTabs(") +
    ";({boardFor, drawWall, drawHead})", context);
  functions.drawHead();
  assert.match(get("move").innerHTML, /No sound pass yet/);
  assert.match(get("move").innerHTML, /starter pack/);
  assert.doesNotMatch(get("move").innerHTML, /voice only/);
  assert.match(get("steps").innerHTML, /No sound pass yet/);
  reel.sound_pass_ran = true; reel.sound_voice_only = true; functions.drawHead();
  assert.match(get("steps").innerHTML, /voice only/);
  reel.sound_voice_only = false; functions.drawHead();
  assert.doesNotMatch(get("steps").innerHTML, /voice only/);
  reel.sound_pass_ran = false; reel.sound_pack_installed = false; functions.drawHead();
  assert.match(get("steps").innerHTML, /voice only/);
  reel.ready_to_post = true; reel.cur = 1; reel.stage = "Post";
  functions.drawWall(); functions.drawHead();
  assert.equal(functions.boardFor(post), null);
  assert.match(get("wall").innerHTML, /Ready to post/);
  assert.doesNotMatch(get("wall").innerHTML, /Post · 75%/);
  assert.match(get("rhead").innerHTML, /Ready to post/);
  assert.doesNotMatch(get("move").innerHTML, /Start: Master review/);
}

async function lookSend() {
  const source = read("reel-captions/boards/look-picker/index.html");
  const controls = new Map(), get = id => {
    if (!controls.has(id)) controls.set(id, {disabled: true, remove() { this.removed = true; }});
    return controls.get(id);
  };
  let resolveConfig;
  const config = new Promise(resolve => { resolveConfig = resolve; });
  const context = {C: null, bc: null, S: {caption_style: {}}, window: {LP: {}}, dirty: false, baseline: null,
    $: get, BoardClient: {create: () => ({load: async () => null})},
    json: name => name === "work/look-picker.json" ? config : Promise.resolve(null),
    restore() {}, render() {}, syncPick() {}, choice: () => "{}", replayAll() {}, send() {}, status() {},
    document: {fonts: {ready: new Promise(() => {})}}};
  const init = vm.runInNewContext(section(source, "async function init(){", "\ninit();") + ";init", context);
  const pending = init();
  assert.equal(get("#send").disabled, true);
  assert.equal(get("#send").onclick, context.send, "Send must be wired before loading can enable it");
  resolveConfig({looks: {clean: {}}});
  let timeout;
  try {
    await Promise.race([pending, new Promise((_, reject) => {
      timeout = setTimeout(() => reject(new Error("Look Picker waited for preview fonts")), 1000);
    })]);
  } finally { clearTimeout(timeout); }
  assert.equal(context.window.LP.ready, true, "readiness must not wait on fonts or previews");
  assert.equal(get("#send [data-loading]").removed, true);
  assert.match(source, /<button id="send" disabled>[^<]+<small data-loading>Loading…<\/small>/);
  const order = [], state = {caption_style: {}};
  const pick = vm.runInNewContext(section(source, "function syncPick(", "function keyPick(") + ";pickLook", {
    S: state, window: {LP: {ready: true}}, dirty: true, sending: false,
    $: get, $$: () => [], colourOK: () => true, persist() { order.push("saved"); },
    previews: [{layout: true}], caption() {
      assert.equal(get("#send").disabled, false, "Send must be usable before a preview renders");
      assert.deepEqual(order, ["saved"]); order.push("preview");
    }, replayAll() {}
  });
  pick("clean");
  assert.equal(state.caption_style.style, "clean");
  assert.deepEqual(order, ["saved", "preview"]);
  const states = {S: {caption_style: {style: "clean"}}, window: {LP: {ready: false}},
    dirty: true, sending: false, $: get, $$: () => [], colourOK: () => true};
  const sync = vm.runInNewContext(section(source, "function syncPick(", "function pickLook(") + ";syncPick", states);
  sync(); assert.equal(get("#send").disabled, true, "loading cannot enable Send");
  states.window.LP.ready = true; states.dirty = false;
  sync(); assert.equal(get("#send").disabled, true, "unchanged picks cannot Send");
  states.dirty = true;
  sync(); assert.equal(get("#send").disabled, false);
  states.sending = true;
  sync(); assert.equal(get("#send").disabled, true, "edits during Send cannot enable a second Send");
  const posts = [], statuses = [], selection = {caption_style: {style: "clean"}, sent_at: null};
  const sendContext = {S: selection, dirty: true, sending: false, window: {LP: {ready: true}}, timer: null,
    $: get, colourOK: () => true, clearTimeout() {}, localISO: () => "now", choice: () => JSON.stringify(selection.caption_style),
    baseline: null, status: (text, bad) => statuses.push({text, bad}), saveState: async () => ({ok: true}),
    syncPick() {}, BASE: "/videos/reel/", fetch: async (url, options) => {
      posts.push(JSON.parse(options.body)); return {ok: true, json: async () => ({ok: true})};
    }};
  const send = vm.runInNewContext(section(source, "async function send(){", "async function init(){") + ";send", sendContext);
  await send();
  assert.equal(posts.length, 1, "one click sends once");
  assert.match(statuses.at(-1).text, /^Sent\b/);
  assert.equal(sendContext.dirty, false);
  sendContext.dirty = true;
  sendContext.fetch = async () => { throw new Error("offline"); };
  await send();
  assert.equal(statuses.at(-1).bad, true);
  assert.match(statuses.at(-1).text, /FAILED/);
  assert.equal(sendContext.dirty, true, "failed Sends remain retryable");
  assert.equal(selection.sent_at, null, "failure cannot leave a sent timestamp");
}

function trialTitle() {
  const source = read("reel-trials/boards/trials/index.html"), cards = element("div"), videos = [];
  const node = (tag, text) => element(tag, {text});
  const render = vm.runInNewContext(section(source, "function renderCard(", "async function watchOpening(") + ";renderCard", {
    node, baseUrl: "/videos/reel/", videos, state: {versions: [{id: "t2", choice: "keep", note: ""}]},
    $: () => cards, persist() {}
  });
  render({id: "t2", file: "trials/t2/trial.mp4"}, false);
  assert.equal(cards.children[0].dataset.id, "t2");
  assert.equal(cards.children[0].children[0].attrs.text, "Trial 2");
  assert.equal(videos[0].attrs["aria-label"], "Trial 2");
}

(async () => {
  for (const [name, test] of [["listening notes", listenNotes], ["Cut duplicate warnings", duplicateWarning], ["Beat Map scenes", () => sceneChooser("beat-map")],
    ["Sketches scenes", () => sceneChooser("sketches")], ["Beat Map clip labels", brollLabels],
    ["Hub walk guidance", hubWalk], ["Grade frame labels", gradeFrame],
    ["Look Picker first Send", lookSend], ["Trial titles", trialTitle]]) {
    await test(); console.log("PASS " + name);
  }
  console.log("9 passed, 0 failed");
})().catch(error => { console.error(error); process.exitCode = 1; });
