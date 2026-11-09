/* board-client.js: the shared include every editor board loads (S4a). board_sync.py copies it next to each board.

   <script src="./board-client.js"></script>
   const bc = BoardClient.create({board: "cut-board"});   // reel comes from the page's ?reel=<reel>
   const saved = await bc.load();                          // disk first, this browser's copy as the fallback
   bc.save(state);                                         // POST to the board server + mirror to this browser

   Disk is the source of truth: /videos/<reel>/<board>.state.json, written by POST
   /videos/<reel>/__state?name=<board> (board_server.py). A heartbeat keeps the server alive. When the server is
   gone, a banner shows a line to paste into Claude, holding the unsaved state, so nothing is lost.
   bannerText() and mergeCues() are pure and exported for node tests. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else {
    root.BoardClient = api;
    var start = function () { api.controls = api.initControls(root); };
    if (root.document.readyState === "loading") root.document.addEventListener("DOMContentLoaded", start);
    else start();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var HEARTBEAT_MS = 30000;
  var TRIGGER = "Restart my editor boards";

  /* One default for every board, including rows built after load. Only a mode change resets a manual toggle. */
  function initControls(env) {
    var mode = null, config = "simple", cacheWritable = true, seen = new WeakSet(), folds = new Map();
    var key = function (section) { return section.dataset && section.dataset.controlsKey; };
    var valid = function (v) { return v === "simple" || v === "advanced" ? v : null; };
    function resolve() {
      var local = null;
      try { local = valid(env.localStorage.getItem("editor-controls")); } catch (_) { /* blocked storage */ }
      return valid(new URLSearchParams(env.location.search).get("controls")) || (cacheWritable && local) || config;
    }
    function apply() {
      var next = resolve(), changed = next !== mode;
      mode = next;
      if (changed) folds.clear();
      env.document.querySelectorAll("details.advanced-controls").forEach(function (section) {
        if (changed || !seen.has(section))
          section.open = folds.has(key(section)) ? folds.get(key(section)) : mode === "advanced";
        seen.add(section);
      });
      if (changed && env.CustomEvent)
        env.document.dispatchEvent(new env.CustomEvent("editor-controls-change", {detail: mode}));
      return mode;
    }
    env.document.addEventListener("toggle", function (e) {
      if (seen.has(e.target) && key(e.target)) folds.set(key(e.target), e.target.open);
    }, true);
    env.addEventListener("storage", function (e) { if (e.key === "editor-controls" || e.key === null) apply(); });
    if (env.MutationObserver)
      new env.MutationObserver(apply).observe(env.document.documentElement, {childList: true, subtree: true});
    apply();
    var ready = Promise.resolve().then(function () {
      return env.fetch("/editor/hub/hub-data.json", {cache: "no-store"});
    }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }).then(function (data) {
      config = valid(data && data.config && data.config.controls) || "simple";
      // The workspace config wins on every load. Storage then carries live hub changes to open iframes.
      if (data) {
        try { env.localStorage.setItem("editor-controls", config); } catch (_) { cacheWritable = false; }
      }
      return apply();
    });
    return {ready: ready, apply: apply, mode: function () { return mode; }};
  }

  /* The paste-into-Claude line. Matches the editor-doctor router line ("start / restart my editor boards"). */
  function bannerText(board, reel, state) {
    if (state === undefined || state === null)
      return TRIGGER + " (the " + board + " for reel " + reel + " lost its connection).";
    return TRIGGER + " and save this " + board + " state for reel " + reel + ": " + JSON.stringify(state);
  }

  /* Refill match: every fresh cue takes the saved cue with the same id + beat, else the same beat (each saved cue
     used once; saved values win, the fresh id stays because ids are positional). A saved cue whose beat no longer
     exists is kept, flagged unmatched, never dropped. Cues the user added (user: true) are kept as they are.
     fields: optional list of the keys to carry over from a saved cue (default: all but id). */
  function mergeCues(saved, fresh, fields) {
    saved = saved || [];
    var used = saved.map(function () { return false; });
    function pick(f, sameId) {
      for (var i = 0; i < saved.length; i++) {
        var s = saved[i];
        if (!used[i] && !s.user && s.beat === f.beat && (!sameId || s.id === f.id)) { used[i] = true; return s; }
      }
      return null;
    }
    var out = (fresh || []).map(function (f) {
      var s = pick(f, true) || pick(f, false), o = {}, k;
      for (k in f) o[k] = f[k];
      if (s) {
        var keys = fields || Object.keys(s).filter(function (x) { return x !== "id" && x !== "unmatched"; });
        keys.forEach(function (x) { if (x in s) o[x] = s[x]; });
      }
      return o;
    });
    saved.forEach(function (s, i) {
      if (used[i]) return;
      var o = {}, k;
      for (k in s) o[k] = s[k];
      if (!s.user) o.unmatched = true;
      out.push(o);
    });
    return out;
  }

  function create(opts) {
    opts = opts || {};
    var board = opts.board;
    var reel = opts.reel || new URLSearchParams((typeof location !== "undefined" && location.search) || "").get("reel");
    if (!board || !reel) throw new Error("BoardClient needs a board and a reel (?reel=<reel> in the page URL)");
    var doFetch = opts.fetch || function (u, o) { return fetch(u, o); };
    var store = opts.storage !== undefined ? opts.storage : (typeof localStorage !== "undefined" ? localStorage : null);
    var onGone = opts.onGone || showBanner;
    var base = "/videos/" + encodeURIComponent(reel) + "/";
    var key = "editor-boards:" + reel + ":" + board;
    var last = null, timer = null;

    function mirror(json) { try { if (store) store.setItem(key, json); } catch (e) { /* full or blocked */ } }
    function gone() { var t = bannerText(board, reel, last); onGone(t); return t; }
    function post(url, json) {
      return doFetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: json});
    }

    function load() {
      return doFetch(base + board + ".state.json", {cache: "no-store"})
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; })   // server unreachable: this browser's copy below
        .then(function (disk) {
          if (disk === null) { try { disk = store && JSON.parse(store.getItem(key) || "null"); } catch (e) { disk = null; } }
          last = disk;
          return disk;
        });
    }

    /* Resolves {ok, status}; a server that is gone shows the banner (status 0). */
    function save(state) {
      var json = JSON.stringify(state);
      last = state;
      mirror(json);
      return post(base + "__state?name=" + encodeURIComponent(board), json)
        .then(function (r) { return {ok: r.ok, status: r.status}; })
        .catch(function () { gone(); return {ok: false, status: 0}; });
    }

    function beat() { return post("/heartbeat", "{}").catch(function () { gone(); }); }
    if (opts.heartbeat !== false) { beat(); timer = setInterval(beat, opts.heartbeatMs || HEARTBEAT_MS); }

    return {load: load, save: save, heartbeat: beat, lost: gone,
            stop: function () { if (timer) clearInterval(timer); timer = null; }};
  }

  function showBanner(text) {
    if (typeof document === "undefined") return;
    var bar = document.getElementById("board-server-gone");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "board-server-gone";
      bar.setAttribute("role", "alert");
      bar.style.cssText = "position:fixed;left:0;right:0;top:0;z-index:2147483647;padding:10px 14px;" +
        "background:#7a1f1f;color:#fff;font:14px/1.4 system-ui,sans-serif;display:flex;gap:10px;align-items:center";
      var msg = document.createElement("span");
      msg.textContent = "The editor boards stopped. Nothing is lost: copy this line and paste it into Claude.";
      var line = document.createElement("textarea");
      line.readOnly = true; line.rows = 2; line.setAttribute("aria-label", "Line to paste into Claude");
      line.style.cssText = "flex:1;font:12px/1.3 ui-monospace,monospace;color:#000";
      var btn = document.createElement("button");
      btn.type = "button"; btn.textContent = "Copy";
      btn.onclick = function () {
        var done = function () { btn.textContent = "Copied"; };
        if (navigator.clipboard && navigator.clipboard.writeText)
          navigator.clipboard.writeText(line.value).then(done, function () { line.select(); document.execCommand("copy"); done(); });
        else { line.select(); document.execCommand("copy"); done(); }
      };
      bar.appendChild(msg); bar.appendChild(line); bar.appendChild(btn);
      document.body.appendChild(bar);
    }
    bar.querySelector("textarea").value = text;   // always the latest unsaved state
  }

  return {create: create, bannerText: bannerText, mergeCues: mergeCues, initControls: initControls};
});
