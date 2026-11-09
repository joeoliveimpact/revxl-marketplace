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
    "any word left stranded between two pauses"
  ].join("\n"));
  assert.equal(translate("protected beat 10-11 held at 500 ms"), "At 0:00.00: a pause kept for timing. Is it still funny?");
  for (const t of [9, 20, 50, 90]) {
    assert.equal(translate(`protected beat ${t}-${t + 1} held at 500 ms`), "A pause kept for timing. Is it still funny?");
  }
  assert.equal(translate("LISTEN FOR THESE - nothing else\n\n"), "");
  assert.equal(translate(null), "");
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

async function lookSend() {
  const source = read("reel-captions/boards/look-picker/index.html");
  const controls = new Map(), get = id => {
    if (!controls.has(id)) controls.set(id, {disabled: true, remove() { this.removed = true; }});
    return controls.get(id);
  };
  let resolveConfig;
  const config = new Promise(resolve => { resolveConfig = resolve; });
  const context = {C: null, bc: null, S: {caption_style: {}}, window: {LP: {}},
    $: get, BoardClient: {create: () => ({load: async () => null})},
    json: name => name === "work/look-picker.json" ? config : Promise.resolve(null),
    restore() {}, render() {}, replayAll() {}, send() {}, status() {},
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
    S: state, $: get, $$: () => [], colourOK: () => true, persist() { order.push("saved"); },
    previews: [{layout: true}], caption() {
      assert.equal(get("#send").disabled, false, "Send must be usable before a preview renders");
      assert.deepEqual(order, ["saved"]); order.push("preview");
    }, replayAll() {}
  });
  pick("clean");
  assert.equal(state.caption_style.style, "clean");
  assert.deepEqual(order, ["saved", "preview"]);
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
  for (const [name, test] of [["listening notes", listenNotes], ["Beat Map scenes", () => sceneChooser("beat-map")],
    ["Sketches scenes", () => sceneChooser("sketches")], ["Grade frame labels", gradeFrame],
    ["Look Picker first Send", lookSend], ["Trial titles", trialTitle]]) {
    await test(); console.log("PASS " + name);
  }
  console.log("6 passed, 0 failed");
})().catch(error => { console.error(error); process.exitCode = 1; });
