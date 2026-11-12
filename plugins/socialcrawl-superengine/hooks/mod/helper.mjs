#!/usr/bin/env node
/*
 * helper.mjs — the SocialCrawl mod's Node helper (0.4.1). The mod (register.tsx) runs it with
 * $.process.run, so the API key is read and sent in this separate process only, never inside the mod, where
 * fs.read and http.fetch are events another plugin can hook (D30 as amended by D36).
 *
 *   node helper.mjs balance          prints one JSON line: {"ok":true,"balance":<n>,"at":"<ISO UTC, whole seconds>"}
 *                                    or {"ok":false,"reason":"no-key"|"http"|"timeout"|"network"|"body"}
 *   node helper.mjs heartbeat <sid>  writes the N6 heartbeat file and prints nothing; a failure is skipped silently
 *   node helper.mjs budget-write <revxl> <json>
 *                                    saves sessionBudget (integer 1..20000 or null to delete) and/or transcripts
 *                                    ("block" or "allow"), no other keys, into <revxl>/socialcrawl-budget.json;
 *                                    omitted keys stay unchanged on an object or missing file; an existing garbled
 *                                    or non-object file defaults transcripts to "block" unless explicitly supplied, and
 *                                    prints one JSON line: {"ok":true,"budget":<the file as written>}
 *                                    or {"ok":false,"reason":"invalid"|"write"|"readback"|"busy"}
 *   node helper.mjs routes           prints {"ok":true,"routes":[...]} with available labels only, in order:
 *                                    "yt-dlp", "whisper" (files in absolute non-UNC PATH folders), "groq"
 *                                    (nonblank GROQ_API_KEY); never prints a key or PATH folder
 *
 * The key and the URL come from ledger.mjs, the same resolution and the same /v1/credits/ invariant the guard's
 * own balance read uses (credit-guard.mjs readBalance). The key is never printed, logged or written. Always exits
 * 0, through process.exitCode: an explicit exit after a fetch aborts with rc 127 on Node 24/Windows.
 */
import { mkdirSync, readdirSync, readFileSync, renameSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { delimiter, dirname, isAbsolute, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ledgerUrl, resolveKey } from "../ledger.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const PLUGIN = "socialcrawl-superengine";
const WEEK = 7 * 24 * 60 * 60 * 1000;
const isoSeconds = () => new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
const OWNER = "socialcrawl-budget-pane";
const valid = (v) => Number.isInteger(v) && v >= 1 && v <= 20000;   // credit-guard.mjs valid
const isObj = (v) => !!v && typeof v === "object" && !Array.isArray(v);
/* G:326: FF FE is UTF-16LE, else UTF-8 with one EF BB BF dropped. */
const decode = (b) => (b[0] === 0xff && b[1] === 0xfe ? b.toString("utf16le", 2) : b.toString("utf8", b[0] === 0xef && b[1] === 0xbb && b[2] === 0xbf ? 3 : 0));

/* GET /v1/credits/balance (0 credits) with a 5 s timeout; a finite number at body.data.balance is a read. */
async function balance() {
  let key;
  try {
    key = resolveKey(process.env, homedir());
  } catch {
    return { ok: false, reason: "no-key" };   // a control character in the key: nothing is sent
  }
  if (!key) return { ok: false, reason: "no-key" };
  let res;
  try {
    res = await fetch(ledgerUrl("/v1/credits/balance"), { headers: { "x-api-key": key }, signal: AbortSignal.timeout(5000) });
  } catch (e) {
    return { ok: false, reason: e && e.name === "TimeoutError" ? "timeout" : "network" };
  }
  if (!res.ok) return { ok: false, reason: "http" };
  try {
    const body = await res.json();
    const b = body && body.data ? body.data.balance : null;
    if (typeof b === "number" && Number.isFinite(b)) return { ok: true, balance: b, at: isoSeconds() };
  } catch (e) {
    if (e && e.name === "TimeoutError") return { ok: false, reason: "timeout" };
  }
  return { ok: false, reason: "body" };
}

/* The revxl folder, as the mod finds it: SC_REVXL_HOME as given when it holds more than spaces, else <home>/.claude/revxl. */
function revxl() {
  const o = process.env.SC_REVXL_HOME;
  if (o && o.trim()) return o;
  const home = process.env.USERPROFILE || process.env.HOME;
  return home ? join(home, ".claude", "revxl") : null;
}

/* N6: <revxl>/heartbeat/socialcrawl-superengine/<sid>.json, written whole to a temporary file in the same folder and
 * renamed over it (a rerun replaces it). Each write first prunes this plugin's own folder: a .json or .tmp file older
 * than 7 days is deleted; no other folder is ever touched. */
function heartbeat(raw) {
  const sid = String(raw || "nosession").replace(/[^a-z0-9_-]/gi, "");
  const root = revxl();
  if (!sid || !root) return;
  const dir = join(root, "heartbeat", PLUGIN);
  mkdirSync(dir, { recursive: true });
  const old = Date.now() - WEEK;
  for (const name of readdirSync(dir)) {
    if (!/\.(json|tmp)$/.test(name)) continue;
    try {
      const p = join(dir, name);
      const s = statSync(p);
      if (s.isFile() && s.mtimeMs < old) unlinkSync(p);
    } catch {}
  }
  let version = null;
  try {
    version = JSON.parse(readFileSync(join(ROOT, ".claude-plugin", "plugin.json"), "utf8")).version ?? null;
  } catch {}
  const rec = { v: 1, plugin: PLUGIN, version, pane_command: "/socialcrawl-budget", session_id: sid, ts: isoSeconds() };
  const tmp = join(dir, `${sid}.${process.pid}.tmp`);
  writeFileSync(tmp, JSON.stringify(rec));
  try {
    renameSync(tmp, join(dir, `${sid}.json`));
  } catch (e) {
    try { unlinkSync(tmp); } catch {}
    throw e;
  }
}

/* Validate the whole choice before writing: one or both owned keys, no others (including routines). */
function choiceOf(json) {
  let c;
  try { c = JSON.parse(json); } catch { return null; }
  if (!isObj(c)) return null;
  const keys = Object.keys(c);
  if (!keys.length || keys.some((k) => k !== "sessionBudget" && k !== "transcripts")) return null;
  if (Object.hasOwn(c, "sessionBudget") && c.sessionBudget !== null && !valid(c.sessionBudget)) return null;
  if (Object.hasOwn(c, "transcripts") && c.transcripts !== "block" && c.transcripts !== "allow") return null;
  return c;
}

/* Merges the choice into the budget file, keeping every other key it doesn't own (an old `routines` block is dropped, below), through a temporary file in the same
 * folder renamed over it, so no half-written file is ever there (a half-written one reads to the guard as no session
 * budget and, since 0.4.1, as transcripts blocked: GT §3). A
 * failure before the rename leaves the old file as it was and deletes the temporary file. Then it reads it back.
 * A lock file covers the whole read-modify-write-readback; ponytail: two savers breaking one stale lock in the same instant can both hold it. */
function budgetWrite(root, json) {
  const c = choiceOf(json);
  if (!root || !c) return { ok: false, reason: "invalid" };
  const bf = join(root, "socialcrawl-budget.json");
  const lockPath = `${bf}.save.lock`;
  try {
    mkdirSync(root, { recursive: true });
  } catch {
    return { ok: false, reason: "write" };
  }
  const start = performance.now();
  for (;;) {
    try {
      writeFileSync(lockPath, "", { flag: "wx" });
      break;
    } catch (e) {
      if (e && e.code === "ENOENT") return { ok: false, reason: "write" };
    }
    try {
      if (Date.now() - statSync(lockPath).mtimeMs > 10000) unlinkSync(lockPath);
    } catch {}
    if (performance.now() - start >= 2000) return { ok: false, reason: "busy" };
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 20);
  }
  try {
    let o = {};
    let raw = null;
    try {
      raw = readFileSync(bf);
    } catch (e) {
      if (!e || e.code !== "ENOENT") return { ok: false, reason: "write" };   // there but unreadable: never replaced blind
    }
    let garbled = raw !== null;
    if (raw !== null) {
      try {
        const p = JSON.parse(decode(raw));
        if (isObj(p)) { o = p; garbled = false; }
      } catch {}   // garbled: o stays {} and garbled stays true
    }
    if (Object.hasOwn(c, "sessionBudget")) {
      if (c.sessionBudget === null) delete o.sessionBudget;   // Automatic deletes the key (D32)
      else o.sessionBudget = c.sessionBudget;
    }
    // H-39: a garbled or non-object file imposes block unless a transcript choice is explicitly supplied.
    if (Object.hasOwn(c, "transcripts")) o.transcripts = c.transcripts;
    else if (garbled) o.transcripts = "block";
    delete o.routines;   // D55: the old routines block is never read, and every save drops it
    o.updatedAt = isoSeconds();
    o.updatedBy = OWNER;
    const text = JSON.stringify(o, null, 2) + "\n";
    const tmp = `${bf}.${process.pid}.tmp`;
    try {
      writeFileSync(tmp, text);
      renameSync(tmp, bf);
    } catch {
      try { unlinkSync(tmp); } catch {}
      return { ok: false, reason: "write" };
    }
    try {
      const back = JSON.parse(readFileSync(bf, "utf8"));
      if (JSON.stringify(back) === JSON.stringify(o)) return { ok: true, budget: back };
    } catch {}
    return { ok: false, reason: "readback" };
  } finally {
    try { unlinkSync(lockPath); } catch {}
  }
}

/* Inspect every eligible PATH folder without executing anything or disclosing its location. */
function routes() {
  const found = new Set();
  const names = new Map();
  for (const [label, bases] of [["yt-dlp", ["yt-dlp"]], ["whisper", ["whisper", "whisper-cli", "whisper.cpp", "faster-whisper", "whisperx"]]]) {
    for (const base of bases) for (const ext of ["", ".exe", ".cmd"]) names.set(base + ext, label);
  }
  for (const folder of (process.env.PATH || "").split(delimiter)) {
    if (!folder || !isAbsolute(folder) || folder.startsWith("\\\\") || folder.startsWith("//")) continue;
    try {
      for (const entry of readdirSync(folder, { withFileTypes: true })) {
        const label = names.get(entry.name.toLowerCase());
        if (!label) continue;
        try {
          if (statSync(join(folder, entry.name)).isFile()) found.add(label);
        } catch {}
      }
    } catch {}
  }
  if ((process.env.GROQ_API_KEY || "").trim()) found.add("groq");
  return { ok: true, routes: ["yt-dlp", "whisper", "groq"].filter((label) => found.has(label)) };
}

const [cmd, arg, arg2] = process.argv.slice(2);
process.exitCode = 0;
if (cmd === "balance") {
  balance()
    .catch(() => ({ ok: false, reason: "network" }))
    .then((o) => process.stdout.write(JSON.stringify(o) + "\n"));
} else if (cmd === "budget-write") {
  let o;
  try {
    o = budgetWrite(arg, arg2);
  } catch {
    o = { ok: false, reason: "write" };
  }
  process.stdout.write(JSON.stringify(o) + "\n");
} else if (cmd === "routes") {
  process.stdout.write(JSON.stringify(routes()) + "\n");
} else if (cmd === "heartbeat") {
  try {
    heartbeat(arg);
  } catch {}
}
