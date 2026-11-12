/*
 * Phase 3d (0.4.0): the per-call record <revxl>/socialcrawl-calls.jsonl, and four carries from the 3c check: the
 * revxl folder's delete or move (HUNT 1), a write's stream and short name (HUNT 2, 3), the shell's revxl location as
 * a path folder (HUNT 4) and UTF-16LE files (HUNT 6). One fixture per item of List A in "Phase 3d Checker Fixtures -
 * Both Lists - 10.12.26.md", D-A1 to D-A8 (D-A9's unattended log rides in D-A1; D-A11 is the whole suite and its
 * instruments); the D-A10 mutants are in P3d-mutants. Each fixture here was run red against slice 3c (4677e75)
 * before it was run green. Round 2 ("Phase 3d Round 2 Amendment - 10.12.26.md", R2-1 to R2-3): P3d-R2-* hold the
 * check's H1 to H4, the passes beside them and their mutants, each run red against the round-1 tree (and at 4677e75
 * wherever the pin lets the case through: all but H1, which the pin denied) before it was run green. Messages are
 * checked whole, by equality.
 *
 * Synchronous; every guard run in its own temp SC_REVXL_HOME and HOME (lib.mjs session()). A real-shaped
 * C:/Users/x/.claude/revxl path is only text in a tool call, and no command here is run by a shell: each is only the
 * text the guard reads. Zero credits, zero network: no run has a real key, and the one balance read is answered by
 * fake-fetch.mjs. Backslashes, byte order marks and newlines are built with String.fromCharCode or as bytes, never
 * typed as escapes. The 8.3 short name is read with `cmd /c dir /x` (Windows only; skipped with its reason elsewhere).
 */
import { spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import {
  session, V1, GUARD, COSTS, M_NOTPLAIN, M_NOTBASH, M_LOST, mError, mLimit, mStateRead, mBudgetRead,
  ROUTINE, ROUTINES_ON, SRC_SESSION, srcAuto, today, assert, T,
} from "../lib.mjs";
import { stateFault, atOnce } from "./balance.mjs";

const UN = { CLAUDE_CODE_SESSION_ATTENDED: "0" };
const M_SETTINGS = "SocialCrawl call not run: your SocialCrawl settings file can't be read, so this session's credit limit can't be checked. Re-save your limit in SocialCrawl → Settings to fix it." + T;
const RON = { budget: ROUTINES_ON, env: ROUTINE };
const NL = String.fromCharCode(10);
const B = String.fromCharCode(92);                          // one backslash
const bs = (...parts) => parts.join(B);                     // a Windows path with backslashes
const P50 = `curl -s "${V1}prism/leads?query=x"`;           // plain, flat 50
const P1 = `curl -s "${V1}amazon/shop?q=a"`;                 // plain, flat 1
const P200 = `curl -s "${V1}prism/share-of-voice?brands=a,b"`;   // plain, 200
const FREE = `curl -s "${V1}credits/balance"`;               // plain, free: the free plain pass
const NP = `echo '${V1}prism/leads?query=x'`;                // not plain
const B50 = '{"sessionBudget":50}';
const DAY300 = () => ({ date: today(), spent: 300, sessions: { other: 300 } });
const CALLS = "socialcrawl-calls.jsonl";
const MiB = 1048576;
/** The call record line's keys, in order (3d a). */
const KEYS = ["ts", "sid", "paths", "worst", "committed", "decision", "kind", "limit", "balance", "balanceAt", "routine", "tool_use_id"];
/** The unattended log line's fields, in order (unchanged since 3a). */
const FIELDS = ["ts", "session_id", "decision", "kind", "paths", "cmdWorst", "committed", "cap"];
const REAL = bs("C:", "Users", "x", ".claude", "revxl");      // a real-shaped default <revxl>, never opened
const KEY = "sc_" + "TESTKEY" + "p3d7q";                     // a sentinel, never a key: split so no scanner reads it as one
const QV = "QSECRET" + "p3d7q";                              // a sentinel query value
const REFUSAL = /^SocialCrawl call not run: the credit guard couldn't record it/;
/** recorded()'s refusal, word for word (P3a-A17), for a 50cr command. */
const refusal = (sf, why) =>
  `SocialCrawl call not run: the credit guard couldn't record it, and a call it can't record would run uncounted (this command's ` +
  `worst case is ~50 credits). Reason: ${why}. Session file: ${sf}. Nothing was sent. Run the command again; if it is ` +
  `refused again, check that the session file and its folder exist and can be written.`;
/** M_TAMPER, whole (3c d), with its NAME. */
const NAMES = ["the budget file socialcrawl-budget.json", "the old routine day file socialcrawl-day.json",
  "the unattended log credit-guard-unattended.jsonl", "the call record socialcrawl-calls.jsonl", "a session file in sessions/"];
const FOLDER = "the revxl folder";
const mTamper = (what, name) =>
  `SocialCrawl guard file left alone: this ${what} names ${name}, which holds the person's SocialCrawl budget or spend ` +
  `record. Claude is not to change it (the guard refuses the plain ways; a glob, a link to the folder, an MCP tool or a script can still get past it); the person sets the limit in SocialCrawl → Settings. To look at it, use the Read tool.`;
/** A tamper deny's whole stdout, as done() writes it. */
const denyOut = (m) =>
  JSON.stringify({ hookSpecificOutput: { permissionDecision: "deny", hookEventName: "PreToolUse", permissionDecisionReason: m }, systemMessage: m });
/** A write-type tool call as Claude Code sends it (NotebookEdit names notebook_path). */
const edit = (tool, path) => ({
  tool_name: tool,
  tool_input: tool === "NotebookEdit" ? { notebook_path: path, new_source: "x" }
    : tool === "Edit" ? { file_path: path, old_string: "a", new_string: "b" }
    : tool === "MultiEdit" ? { file_path: path, edits: [{ old_string: "a", new_string: "b" }] }
    : { file_path: path, content: "x" },
});
const TOOLS = ["Write", "Edit", "MultiEdit", "NotebookEdit"];
const verdict = (r) => r.decision || (r.raw ? "?" : "pass");
const cell = (label, parts) => `    ${label.padEnd(62)} ${parts.join(" | ")}`;
const raw = (p) => { try { return readFileSync(p, "utf8"); } catch { return null; } };
const bytes = (p) => { try { return readFileSync(p); } catch { return null; } };
/** n bytes of filler, ending in a newline. */
const fill = (n) => Buffer.from("x".repeat(n - 1) + NL);
/** A file's bytes: UTF-16LE with its mark (FF FE), UTF-16BE with its mark (FE FF), UTF-8 with its mark (EF BB BF). */
const u16le = (s) => Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(s, "utf16le")]);
const u16be = (s) => Buffer.concat([Buffer.from([0xfe, 0xff]), Buffer.from(s, "utf16le").swap16()]);
const u8bom = (s) => Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from(s, "utf8")]);

/** The call record in a revxl folder: its text (null when there is none, or a folder), its lines parsed (null if one isn't JSON), its bytes and its `.1`'s. */
function record(revxl) {
  const text = raw(join(revxl, CALLS));
  let lines = [];
  try { lines = text === null ? [] : text.split(NL).filter(Boolean).map((l) => JSON.parse(l)); } catch { lines = null; }
  return { text, lines, bytes: bytes(join(revxl, CALLS)), dot1: bytes(join(revxl, `${CALLS}.1`)) };
}
/** Every file under a folder with its content, as one string: equal before and after = nothing made, changed or removed. */
function tree(dir) {
  const out = [];
  const walk = (d) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const p = join(d, e.name);
      if (e.isDirectory()) { out.push(`${p}/`); walk(p); } else out.push(`${p}=${readFileSync(p, "utf8")}`);
    }
  };
  walk(dir);
  return out.sort().join(NL);
}
/** A session (balance 800 cached unless `balance: null`), its file seeded unless `seed: null`, with an optional budget and day file. */
function open(o = {}) {
  const s = session(o.balance === null || o.seed === null ? { balance: null } : {});
  if (o.seed !== null) s.seed(o.seed || { spent: 0 });
  if (o.budget !== undefined) s.budget(o.budget);
  if (o.day !== undefined) s.day(o.day);
  return s;
}
/**
 * One run in a fresh session built by open(o). `cmd` is the command, or a function of the session that returns it;
 * `prep(s)` may seed files and returns run options (a preload's `node` and `env`); o.post sends the command as a stray
 * PostToolUse; o.extra, o.fetch and o.guard as lib.mjs run(). The result carries the state, the unattended log, the
 * day file, the call record (`rec`), `same` (nothing under the session's folder changed) and the times t0 and t1
 * around the run.
 */
function once(cmd, o = {}, prep = () => ({})) {
  const s = open(o);
  const p = prep(s) || {};
  const before = tree(s.dir);
  const opts = { guard: o.guard, extra: o.extra, fetch: o.fetch, node: p.node, env: { ...(o.env || {}), ...(p.env || {}) } };
  const command = typeof cmd === "function" ? cmd(s) : cmd;
  const t0 = new Date().toISOString();
  const r = o.post ? s.post(command, opts) : s.run(command, opts);
  const t1 = new Date().toISOString();
  Object.assign(r, { s, t0, t1, same: tree(s.dir) === before, state: s.state(), stateRaw: s.stateRaw(), log: s.logLines(), day: raw(s.df), rec: record(s.revxl) });
  s.cleanup();
  return r;
}
/** A preload in a temp dir of its own, with node:fs as `fs` and the path match `same` in scope. */
function preload(id, body) {
  const d = mkdtempSync(join(tmpdir(), `sc-p3d-${id}-`));
  const f = join(d, `${id}.mjs`);
  writeFileSync(f,
    `import { createRequire, syncBuiltinESMExports } from "node:module";` + NL +
    `import { resolve } from "node:path";` + NL +
    `const fs = createRequire(import.meta.url)("node:fs");` + NL +
    `const same = (p, f) => typeof p === "string" && resolve(p).toLowerCase() === resolve(f).toLowerCase();` + NL +
    body +
    `syncBuiltinESMExports();` + NL);
  return { url: pathToFileURL(f).href, dir: d };
}
const drop = (...pre) => { for (const p of pre) rmSync(p.dir, { recursive: true, force: true }); };
/** The state-file fault preload of balance.mjs, with its folder for cleanup; `on(file, spec)` aims it at any file. */
function faults() {
  const url = stateFault();
  return { url, dir: dirname(fileURLToPath(url)), on: (file, spec) => ({ node: ["--import", url], env: { STATE_FAULT: JSON.stringify([spec[0], file, ...spec.slice(1)]) } }) };
}
/** CR_FAULT = JSON [op, code]: that fs call (appendFileSync, statSync or renameSync) on the call record throws `code`, and says so in CR_FAULT_LOG. */
const crFault = () => preload("cr",
  `const append = fs.appendFileSync;` + NL +
  `const [op, code] = JSON.parse(process.env.CR_FAULT);` + NL +
  `const real = fs[op];` + NL +
  `fs[op] = (p, ...a) => { if (typeof p === "string" && p.toLowerCase().endsWith("socialcrawl-calls.jsonl")) { append(process.env.CR_FAULT_LOG, op + String.fromCharCode(10)); throw Object.assign(new Error(code + ", forced by P3d"), { code }); } return real(p, ...a); };` + NL);
/** A read of ODD_FILE throws an error whose code can't be read: the guard's own error, after it holds the session lock. */
const oddRead = () => preload("odd",
  `const read = fs.readFileSync;` + NL +
  `const odd = () => Object.defineProperty(new Error("forced by P3d"), "code", { get() { throw new Error("forced by P3d: code"); } });` + NL +
  `fs.readFileSync = (p, ...a) => { if (same(p, process.env.ODD_FILE)) throw odd(); return read(p, ...a); };` + NL);
/** path.join throws on a "sessions" segment: the guard's own error, before it locks (P3a-A17's preload). */
const outerThrows = () => preload("outer",
  `const path = createRequire(import.meta.url)("node:path");` + NL +
  `const join = path.join;` + NL +
  `path.join = (...a) => { if (a.includes("sessions")) throw new Error("forced by P3d"); return join(...a); };` + NL);
/** Logs every fs call the guard makes on a path, realpath and realpath.native included, as [op, path, "ok" | code], to SPY_LOG. */
const ioSpy = () => preload("io",
  `const append = fs.appendFileSync;` + NL +
  `let busy = false;` + NL +
  `const log = (op, p, how) => { if (!busy && typeof p === "string") { busy = true; try { append(process.env.SPY_LOG, JSON.stringify([op, p, how]) + String.fromCharCode(10)); } finally { busy = false; } } };` + NL +
  `const wrap = (op, real) => (p, ...a) => { let v; try { v = real(p, ...a); } catch (e) { log(op, p, (e && e.code) || "error"); throw e; } log(op, p, "ok"); return v; };` + NL +
  `for (const op of ["readFileSync", "writeFileSync", "appendFileSync", "mkdirSync", "renameSync", "unlinkSync", "statSync", "lstatSync", "existsSync", "openSync", "readdirSync", "rmSync", "accessSync"]) fs[op] = wrap(op, fs[op]);` + NL +
  `const rp = fs.realpathSync, rpn = fs.realpathSync.native;` + NL +
  `fs.realpathSync = wrap("realpathSync", rp);` + NL +
  `fs.realpathSync.native = wrap("realpathSync.native", rpn);` + NL);
/** A copy of the guard (costs.json beside it) with each [anchor, replacement] applied; each anchor must occur exactly once. */
function mutant(id, pairs) {
  let src = readFileSync(GUARD, "utf8");
  for (const [anchor, repl] of pairs) {
    assert(src.split(anchor).length === 2, `mutant ${id}: its anchor must occur exactly once in credit-guard.mjs, read ${src.split(anchor).length - 1} x ${JSON.stringify(anchor).slice(0, 100)}`);
    src = src.replace(anchor, () => repl);
  }
  const d = mkdtempSync(join(tmpdir(), `sc-p3d-mut-${id}-`));
  writeFileSync(join(d, "credit-guard.mjs"), src);
  copyFileSync(COSTS, join(d, "costs.json"));
  return { file: join(d, "credit-guard.mjs"), dir: d };
}
/**
 * A file `name` made in a fresh temp folder named revxl, and its 8.3 short name read with `cmd /c dir /x`:
 * {dir, path} (the short-named path), or {dir, why} when there is none (not Windows, or 8.3 names off on the volume).
 */
function shortName(name) {
  const dir = mkdtempSync(join(tmpdir(), "sc-p3d-83-"));
  const rv = join(dir, "revxl");
  mkdirSync(rv);
  writeFileSync(join(rv, name), "{}");
  if (process.platform !== "win32") return { dir, why: "not Windows" };
  const r = spawnSync("cmd.exe", ["/d", "/c", "dir", "/x", rv], { encoding: "utf8", timeout: 15000 });
  const line = String(r.stdout || "").split(/\r?\n/).find((l) => l.endsWith(` ${name}`));
  const words = line ? line.trim().split(/\s+/) : [];
  const short = words.length >= 2 && words[words.length - 2].includes("~") ? words[words.length - 2] : null;
  return short ? { dir, path: join(rv, short) }
    : { dir, why: `no 8.3 name for ${name} in dir /x (8.3 names off on the temp volume?), read ${JSON.stringify(line || r.stdout || r.stderr || "").slice(0, 160)}` };
}
/** Anything of a sentinel in a call record's text: the key, the query value, a header or the curl itself. */
const leaks = (text) => ["testkey", "qsecret", "x-api-key", "authorization", "bearer", "api_key", "curl"].filter((x) => String(text || "").toLowerCase().includes(x));

// Round 2 ("Phase 3d Round 2 Amendment - 10.12.26.md"): every case through the three shell tools, in both modes.
const MODES = [["attended", {}], ["unattended", UN]];
const SHELL3 = ["Bash", "PowerShell", undefined];
const BT = String.fromCharCode(96);                          // one backtick
/** Round 2's regex texts as credit-guard.mjs spells them, for the mutants. */
const R2 = {
  at: "const REVXL_AT = /revxl(?![a-z0-9_-])/;",
  atR1: `const REVXL_AT = /(^|[${B}${B}/~"'${B}s=])revxl(?=[${B}${B}/"'${B}s;|&)]|$)/;`,
  verbLeft: "(^|[^a-z0-9_-])(rm|rmdir|",
  verbLeftR1: `(^|[${B}s;&|(${BT}{])(rm|rmdir|`,
  exe: `(${B}.exe)?`,
  alt1: `/revxl(?:[${B}${B}/]+sessions)?(?![${B}${B}/]+${B}.?[a-z0-9_])(?![a-z0-9_-])/`,
  alt2: `      if (at >= 0 && /[${B}${B}/]${B}.${B}.(?=[${B}${B}/]|$)/.test(token.slice(at + 6))) return true;`,
  alt3: `/${B}.claude(?![${B}${B}/]+${B}.?[a-z0-9_])(?![a-z0-9_-])/`,
  tail4: `/^(?:[${B}${B}/]+sessions)?(?![${B}${B}/]+${B}.?[a-z0-9_])(?![a-z0-9_-])/`,
  child: `(?![${B}${B}/]+${B}.?[a-z0-9_])`,
  use: "      if (k < 0 && MOVE_VERB.test(c) && (REVXL_FOLDER.some((re) => re.test(c)) || atRevxl(c, rx()))) k = 5;",
};
/** The amendment's required cases. H1 names a guard file ([command, K]); H4's last two are the session's own SC_REVXL_HOME. */
const H1 = [
  [`cd ~/.claude && echo '{"sessionBudget":20000}' >revxl/socialcrawl-budget.json`, 0],
  ["cd ~/.claude && echo x>>revxl/socialcrawl-day.json", 1],
  ["cd ~/.claude;cat>revxl/socialcrawl-budget.json", 0],
  ["cd ~/.claude && cp x {revxl,y}/socialcrawl-budget.json", 0],
  [`echo x > "${bs("$env:USERPROFILE", ".claude", "revxl.", "socialcrawl-budget.json")}"`, 0],
  ["curl -s -orevxl/socialcrawl-budget.json x", 0],
];
const H2 = [
  'bash -c "rm -rf ~/.claude/revxl/sessions"', "sh -c 'rm -rf ~/.claude/revxl'", `cmd /c "rd /s /q ${bs("%USERPROFILE%", ".claude", "revxl")}"`,
  'powershell -c "Remove-Item -Recurse ~/.claude/revxl/sessions"', 'pwsh -Command "rm -r ~/.claude/revxl"', `${B}rm -rf ~/.claude/revxl`,
  "/bin/rm -rf ~/.claude/revxl", "rm.exe -rf ~/.claude/revxl", '"rm" -rf ~/.claude/revxl',
  `${bs("Microsoft.PowerShell.Management", "Remove-Item")} -Recurse ~/.claude/revxl`,
];
const H3 = [
  `x=${BT}rm -rf ~/.claude/revxl${BT}`, `rd /s /q ${bs("%USERPROFILE%", ".claude", "revxl", "sessions")}>nul`,
  "Remove-Item -Recurse -Force ~/.claude/revxl/sessions,~/x", "rm -rf ~/.claude/revxl/./sessions",
  "rm -rf ~/.claude/revxl/sessions/../sessions", "rm -rf ~/.claude/revxl.",
];
/** A session's SC_REVXL_HOME not named revxl (H4; R2-3's alternative 4), and the run option that sets it. */
const homeOf = (s) => join(s.dir, "home");
const atHome = (s) => ({ env: { SC_REVXL_HOME: homeOf(s) } });
const H4 = [
  ["rm -rf ~/.claude", "rm -rf ~/.claude"], ["rm -rf ~/.claude/", "rm -rf ~/.claude/"], ["mv ~/.claude/revxl/sessions{,.bak}", "mv ~/.claude/revxl/sessions{,.bak}"],
  ["rm -rf ~/.claude/revxl/abc/../sessions", "rm -rf ~/.claude/revxl/abc/../sessions"],
  ["rm -rf <SC_REVXL_HOME not named revxl>, backslashes", (s) => `rm -rf ${homeOf(s)}`, atHome],
  ["rm -rf <SC_REVXL_HOME not named revxl>, forward slashes", (s) => `rm -rf ${homeOf(s).split(B).join("/")}`, atHome],
];
const R2PASS = [
  "mv ~/.claude/revxl/examplebrand/voc/a.md ~/.claude/revxl/examplebrand/voc/b.md", "rm ~/.claude/revxl/examplebrand/voc/old.md",
  "ls ~/.claude/revxl", "cat ~/.claude/revxl/jev-ask.json", "grep -n socialcrawl-day ~/.claude/plugins/cache/revxl-marketplace/x/credit-guard.mjs",
  "diff a b | grep revxl-marketplace", "git log --oneline", "echo removed revxl",
  "rm ~/.claude/settings.json", "rm -rf node_modules", "mv a b", "rm -rf ~/.claude/plugins/cache/revxl-marketplace/x",
  "rm ~/.claude/.credentials.bak", "rm -rf ~/.claude-backup", "git rm -r --cached src/form.md", "rm ~/.claude/revxl/examplebrand/voc/old.md",
];
/**
 * `cmd` (or a function of the session) through Bash, PowerShell and no tool_name, attended and unattended: exactly
 * M_TAMPER naming `name` (null: a pass, no output), with nothing in the session folder changed.
 */
function everywhere(rows, label, cmd, name, prep) {
  const seen = [];
  for (const [who, env] of MODES) {
    for (const tool of SHELL3) {
      const r = once(cmd, { extra: { tool_name: tool }, env }, prep);
      seen.push(`${tool || "none"}/${who === "attended" ? "att" : "un"} ${verdict(r)}`);
      const ok = name === null ? r.raw === "" : r.raw === denyOut(mTamper("command", name));
      assert(ok && r.same && r.exit === 0, `${label}, ${tool || "no tool_name"}, ${who}: ${name === null ? "passes untouched" : `exactly M_TAMPER naming ${name}`}, nothing changed, read ${verdict(r)} / ${r.message.slice(0, 160)} / unchanged ${r.same}`, r);
    }
  }
  rows.push(cell(label.slice(0, 62), seen));
}

export default [
  ...[
    ["single-quotes", "budget" + "-wr''ite", 6],
    ["double-quotes", "budget" + '-wr""ite', 6],
    ["backslash", "budget" + `-w${B}rite`, 6],
    ["continuation", "budget" + `-wr${B}${NL}ite`, 6],
    ["mixed-quotes", '"budget' + '-"write', 6],
    ["guard-file", "rm revxl/social" + "crawl-bud''get.json", 0],
  ].map(([label, split, k]) => ({
    id: `P3d-G4c-split-${label}`,
    desc: "split save-step or guard-file names deny in both shells and modes without file I/O",
    fn() {
      const spy = ioSpy();
      const failures = [];
      try {
        for (const tool of ["Bash", "PowerShell"]) for (const [mode, env] of MODES) {
          const log = join(spy.dir, `${tool}-${mode}.log`);
          const cmd = k === 6 ? `node helper.mjs ${split}` : split;
          const r = once(cmd, { env, extra: { tool_name: tool } }, () => ({
            node: ["--import", spy.url], env: { SPY_LOG: log },
          }));
          const calls = (raw(log) || "").split(NL).filter(Boolean).map((l) => JSON.parse(l))
            .filter(([, p]) => p.startsWith(r.s.dir));
          const name = k === 6 ? `the pane's budget save step (${"budget" + "-write"})` : NAMES[k];
          const ok = r.exit === 0 && r.stderr === "" && r.raw === denyOut(mTamper("command", name)) && r.same && calls.length === 0;
          console.log(`    ${tool}/${mode}: ${verdict(r)}, unchanged ${r.same}, file I/O ${calls.length}`);
          if (!ok) failures.push(`${tool}/${mode}: ${verdict(r)}`);
        }
        assert(failures.length === 0, `exact own-files deny with no I/O: ${failures.join(", ")}`);
      } finally { drop(spy); }
    },
  })),
  {
    id: "P3d-G4c-known-limit-disguised",
    desc: "KNOWN LIMIT (hub H-70): no text matcher stops a deliberately disguised shell spelling; this row flips when a caller check lands",
    fn() {
      const split = "budget" + "-wr" + "$''" + "ite";
      const r = once(`node helper.mjs ${split}`, { extra: { tool_name: "Bash" } });
      assert(r.decision === null, "documented disguised spelling is not denied", r);
    },
  },
  {
    id: "P3d-G4c-rm-spellings", desc: "quoted and escaped rm stay denied alongside boundary-sensitive rm forms",
    fn() {
      const rows = [];
      for (const cmd of ['"rm" -rf ~/.claude/revxl', `${B}rm -rf ~/.claude/revxl`, "/bin/rm -rf ~/.claude/revxl", "=rm -rf ~/.claude/revxl"]) {
        everywhere(rows, cmd, cmd, FOLDER);
      }
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-G4c-budget-controls", desc: "ordinary budget mentions and a run-on save name pass untouched",
    fn() {
      for (const tool of ["Bash", "PowerShell"]) for (const [, env] of MODES) {
        for (const cmd of ["git log --grep budget", "echo budget write", "ls " + "budget" + "-writer", 'git commit -m "update budget"']) {
          const r = once(cmd, { env, extra: { tool_name: tool } });
          assert(r.exit === 0 && r.stderr === "" && r.raw === "" && r.same, "ordinary mention passes untouched", r);
        }
      }
    },
  },
  {
    id: "P3d-G4c-strip-mutant", desc: "removing the stripped-copy test reopens the split-name bypass",
    fn() {
      const anchor = readFileSync(GUARD, "utf8").split(NL).find((line) => line.includes("for (const c of [raw,"));
      assert(anchor, "stripped-copy loop exists");
      const m = mutant("g4c-strip", [[anchor, "      for (const c of [raw]) {"]]);
      try {
        const r = once("node helper.mjs " + "budget" + "-wr''ite", { guard: m.file });
        assert(r.exit === 0 && r.stderr === "" && r.raw === "" && r.same,
          "mutant wrongly passes the split-name row instead of the exact own-files deny", r);
        console.log("    stripped-copy mutant: split-name row wrongly passes (killed)");
      } finally { rmSync(m.dir, { recursive: true, force: true }); }
    },
  },
  {
    id: "P3d-A1-call-record-lines",
    desc: "D-A1 (with D-A9's unattended log): attended and unattended, each decision a run makes holding the session lock — a pass and a routine's pass at the commit, M_STATEREAD, M_LOST, M_BUDGETREAD, M_LIMIT and recorded()'s refusal — keeps its exact output and appends exactly one line to <revxl>/socialcrawl-calls.jsonl, its keys exactly ts, sid, paths, worst, committed, decision, kind, limit, balance, balanceAt, routine in that order and each value right (routine true only in a Desktop routine, D58), the unattended log as it was beside it (one line of its 8 fields unattended, of the same decision, kind, committed and cap; an attended routine paid pass also logs once, other attended runs log nothing); the fast path, a tamper deny, a write-type call, the not-plain and not-Bash denies, the free plain pass (in a routine too), a Post input, a lock refusal (the session lock never held: it can't be made, or another run holds it the whole wait) and the guard's own error (before the lock, and while holding it) append nothing; a key in the env, in an x-api-key and an Authorization header, as a query value and in the path, the command and a query value never reach a line",
    fn() {
      const rows = [];
      const f = faults();
      const odd = oddRead();
      const outer = outerThrows();
      // [label, open options, prep, the exact output, the line's own values]
      const appended = [
        ["a pass at the commit", {}, null, (r) => r.raw === "", { decision: "pass", kind: "under-cap", committed: 50, limit: 200, balance: 800 }],
        ["a routine's pass at the commit", RON, null, (r) => r.raw === "", { decision: "pass", kind: "under-cap", committed: 50, limit: 200, balance: 800, routine: true }],
        ["M_STATEREAD (every session read EACCES)", { seed: { spent: 100 } }, (s) => f.on(s.stateFile, ["read", "EACCES"]), (r) => r.message === mStateRead(r.s.stateFile),
          { decision: "deny", kind: "error", committed: null, limit: null, balance: null }],
        ["M_LOST", { seed: { spent: 40, lost: true } }, null, (r) => r.message === M_LOST, { decision: "deny", kind: "lost", committed: 40, limit: null, balance: 800 }],
        ["M_BUDGETREAD (every budget read EBUSY)", { seed: { spent: 40 }, budget: B50 }, (s) => f.on(s.bf, ["read", "EBUSY"]), (r) => r.message === mBudgetRead(r.bf),
          { decision: "deny", kind: "error", committed: 40, limit: null, balance: 800 }],
        ["M_LIMIT", { seed: { spent: 190 } }, null, (r) => r.message === mLimit({ spent: 190, worst: 50, limit: 200, src: srcAuto(800), bf: r.bf }),
          { decision: "deny", kind: "over-limit", committed: 190, limit: 200, balance: 800 }],
        ["recorded()'s refusal (the session save EBUSY)", {}, (s) => f.on(s.stateFile, ["busy", "EBUSY"]), (r) => r.message === refusal(r.s.stateFile, "the session file could not be saved (EBUSY)"),
          { decision: "deny", kind: "error", committed: 0, limit: 200, balance: 800 }],
      ];
      for (const [label, o, prep, out, want] of appended) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          const r = once(P50, { ...o, env: { ...(o.env || {}), ...env } }, prep || undefined);
          const L = r.rec.lines || [];
          rows.push(cell(`${label}, ${who}`, [verdict(r), `lines ${L.length}`, L[0] ? `${L[0].decision}/${L[0].kind}/${L[0].committed}/${L[0].limit}/${L[0].balance}` : "-"]));
          assert(out(r) && r.exit === 0, `${label}, ${who}: the exact decision, read ${verdict(r)} / ${r.message.slice(0, 200)}`, r);
          assert(L.length === 1 && r.rec.text.endsWith(NL), `${label}, ${who}: exactly one call record line, read ${JSON.stringify(r.rec.text)}`, r);
          const l = L[0];
          assert(JSON.stringify(Object.keys(l)) === JSON.stringify(KEYS), `${label}, ${who}: exactly the keys in order, read ${JSON.stringify(Object.keys(l))}`);
          const exp = { sid: r.s.sid, paths: ["/v1/prism/leads"], worst: 50, balanceAt: null, routine: false, ...want };
          for (const k of Object.keys(exp)) {
            assert(JSON.stringify(l[k]) === JSON.stringify(exp[k]), `${label}, ${who}: ${k} is ${JSON.stringify(exp[k])}, read ${JSON.stringify(l[k])}`);
          }
          assert(typeof l.ts === "string" && new Date(l.ts).toISOString() === l.ts && l.ts >= r.t0 && l.ts <= r.t1,
            `${label}, ${who}: ts is the UTC time of the run, read ${l.ts} (run ${r.t0} to ${r.t1})`);
          if (who === "unattended" || want.routine === true) {
            const u = r.log[0];
            assert(r.log.length === 1 && JSON.stringify(Object.keys(u)) === JSON.stringify(FIELDS) && u.decision === (l.decision === "deny" ? "deny" : "pass") &&
              u.kind === l.kind && u.committed === l.committed && u.cap === l.limit && u.cmdWorst === 50,
              `${label}, unattended: the unattended log's one line, as before, read ${JSON.stringify(r.log)}`);
          } else assert(r.log.length === 0, `${label}, attended: nothing in the unattended log, read ${JSON.stringify(r.log)}`);
        }
      }
      // Nothing appended.
      const nothing = [
        ["the fast path", "ls -la", {}, null, (r) => r.raw === ""],
        ["a tamper deny", "cat ~/.claude/revxl/socialcrawl-budget.json", {}, null, (r) => r.raw === denyOut(mTamper("command", NAMES[0]))],
        ["a write-type call carrying a stray paid command", "", { extra: { tool_name: "Write", tool_input: { file_path: bs("C:", "proj", "notes.md"), content: P50, command: P50 } } }, null, (r) => r.raw === ""],
        ["the not-plain deny", NP, {}, null, (r) => r.message === M_NOTPLAIN],
        ["the not-Bash deny", P50, { extra: { tool_name: "PowerShell" } }, null, (r) => r.message === M_NOTBASH],
        ["the free plain pass", FREE, {}, null, (r) => r.raw === ""],
        ["the free plain pass in a routine", FREE, RON, null, (r) => r.raw === ""],
        ["a Post input", P50, { post: true }, null, (r) => r.raw === ""],
        ["a lock refusal: the session lock can't be made", P50, {}, (s) => f.on(s.stateFile, ["lock", "ENOENT"]), (r) => r.decision === "deny" && REFUSAL.test(r.message)],
        ["the guard's own error before the lock", P50, {}, () => ({ node: ["--import", outer.url] }), (r, who) => (who === "attended" ? r.raw === "" : r.message === mError())],
        ["the guard's own error holding the lock (the budget read)", P50, { budget: B50 }, (s) => ({ node: ["--import", odd.url], env: { ODD_FILE: s.bf } }),
          (r, who) => (who === "attended" ? r.raw === "" : r.message === mError())],
      ];
      for (const [label, cmd, o, prep, out] of nothing) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          const r = once(cmd, { ...o, env: { ...(o.env || {}), ...env } }, prep || undefined);
          rows.push(cell(`nothing: ${label}, ${who}`, [verdict(r), `record ${r.rec.text === null ? "none" : JSON.stringify(r.rec.text).slice(0, 60)}`]));
          assert(out(r, who) && r.exit === 0, `${label}, ${who}: the exact outcome, read ${verdict(r)} / ${r.message.slice(0, 200)}`, r);
          assert(r.rec.text === null, `${label}, ${who}: no call record, read ${JSON.stringify(r.rec.text)}`, r);
        }
      }
      // A lock refusal: another run holds the session lock the whole wait (both runs at once).
      const held = [["attended", {}], ["unattended", UN]].map(([who, env]) => {
        const s = open({});
        writeFileSync(`${s.stateFile}.lock`, "");
        return { s, who, env };
      });
      const now = new Date();
      for (const h of held) utimesSync(`${h.s.stateFile}.lock`, now, now);
      const hr = atOnce(held.map((h) => ({ s: h.s, command: P50, o: { env: h.env } })));
      held.forEach((h, i) => {
        const rec = record(h.s.revxl);
        rows.push(cell(`nothing: the session lock held by another run, ${h.who}`, [hr[i].decision, `${hr[i].ms} ms`, `record ${rec.text === null ? "none" : "some"}`]));
        assert(hr[i].decision === "deny" && REFUSAL.test(hr[i].message) && rec.text === null,
          `the session lock held, ${h.who}: refused, no call record, read ${hr[i].message.slice(0, 160)} / ${JSON.stringify(rec.text)}`);
        h.s.cleanup();
      });
      // The sentinel: no key, command, header or query value in a line.
      const SENT = `curl -s -H "x-api-key: ${KEY}" -H "Authorization: Bearer ${KEY}" "${V1}prism/leads?query=${QV}&api_key=${KEY}"`;
      const PATHKEY = `curl -s "${V1}prism/leads/${KEY}?query=${QV}"`;
      for (const [label, cmd, o, out] of [
        ["a pass, the key in the env and two headers", SENT, {}, (r) => r.raw === ""],
        ["M_LIMIT, the same", SENT, { seed: { spent: 190 } }, (r) => r.decision === "deny"],
        ["a pass, the key in the path", PATHKEY, {}, (r) => r.raw === ""],
      ]) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          const r = once(cmd, { ...o, env: { ...env, SOCIALCRAWL_API_KEY: KEY } });
          const L = r.rec.lines || [];
          rows.push(cell(`the sentinel: ${label}, ${who}`, [verdict(r), `lines ${L.length}`, `paths ${JSON.stringify(L[0] && L[0].paths)}`, `leaks ${JSON.stringify(leaks(r.rec.text))}`]));
          assert(out(r) && L.length === 1 && !leaks(r.rec.text).length && !String(r.rec.text).includes(cmd),
            `${label}, ${who}: one line holding no key, header, query value or command, read ${verdict(r)} / ${JSON.stringify(r.rec.text)}`, r);
        }
      }
      drop(f, odd, outer);
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-A2-balance-at",
    desc: "D-A2: when the guard reads the balance (none cached, fake-fetch answering 800) the session file keeps balanceAt, the UTC time of the read, beside balance, and the call record line has balance 800 and that balanceAt; the session's next pass and its next deny (M_LIMIT) carry the same balanceAt, and the file keeps it; an older session file with no balanceAt reads as before (a pass counted, its line's balanceAt null) and gains none; a session file with balanceAt but no balance is still a whole session (not lost: with nothing to read the balance a pass is counted at the fallback 500, its line's balance null; with a balance on offer the read happens and balanceAt is the new time)",
    fn() {
      const rows = [];
      const bal = (v) => ({ body: { data: { balance: v } } });
      const s = open({ balance: null });
      const t0 = new Date().toISOString();
      const r1 = s.run(P50, { fetch: [bal(800)] });
      const t1 = new Date().toISOString();
      const st1 = s.state();
      const r2 = s.run(P1);
      const r3 = s.run(P200);                                      // 51 + 200 is past the automatic cap of 200
      const st3 = s.state();
      const L = record(s.revxl).lines || [];
      const fetched = s.fetches().length;
      s.cleanup();
      rows.push(cell("a read, then a pass and a deny", [`${verdict(r1)}, ${verdict(r2)}, ${verdict(r3)}`, `balanceAt ${st1 && st1.balanceAt}`, `lines ${JSON.stringify(L.map((l) => [l.decision, l.balance, l.balanceAt]))}`]));
      assert(r1.raw === "" && fetched === 1 && st1 && st1.balance === 800 && typeof st1.balanceAt === "string" && new Date(st1.balanceAt).toISOString() === st1.balanceAt &&
        st1.balanceAt >= t0 && st1.balanceAt <= t1, `the read: balanceAt is its UTC time, beside balance 800, read ${JSON.stringify(st1)} / ${fetched} fetch(es)`, r1);
      assert(r2.raw === "" && r3.decision === "deny" && r3.message === mLimit({ spent: 51, worst: 200, limit: 200, src: srcAuto(800), bf: r3.bf }) && st3.balanceAt === st1.balanceAt,
        `the next pass and deny: the file keeps balanceAt, read ${verdict(r2)} / ${r3.message.slice(0, 120)} / ${JSON.stringify(st3)}`, r3);
      assert(L.length === 3 && L.every((l) => l.balance === 800 && l.balanceAt === st1.balanceAt) && L[2].decision === "deny",
        `three lines, each carrying balance 800 and that balanceAt, read ${JSON.stringify(L)}`);
      const old = once(P50, {});
      rows.push(cell("an older session file with no balanceAt", [verdict(old), `saved ${old.stateRaw}`, `line balanceAt ${old.rec.lines && old.rec.lines[0] && old.rec.lines[0].balanceAt}`]));
      assert(old.raw === "" && old.state.spent === 50 && !("balanceAt" in old.state) && old.rec.lines.length === 1 && old.rec.lines[0].balanceAt === null && old.rec.lines[0].balance === 800,
        `an older file: read as before, its line's balanceAt null, none added, read ${old.stateRaw} / ${old.rec.text}`, old);
      const AT = "2026-01-02T03:04:05.000Z";
      const nb = once(P50, { balance: null, seed: { spent: 0, balanceAt: AT } });
      const nf = once(P50, { balance: null, seed: { spent: 0, balanceAt: AT }, fetch: [bal(800)] });
      rows.push(cell("balanceAt but no balance: nothing to read it, then a read", [`${verdict(nb)} ${nb.stateRaw}`, `${verdict(nf)} ${nf.stateRaw}`]));
      assert(nb.raw === "" && nb.state.spent === 50 && !nb.state.lost && nb.rec.lines.length === 1 && nb.rec.lines[0].balance === null && nb.rec.lines[0].limit === 500,
        `balanceAt with no balance and nothing to read it: a whole session, the fallback 500, read ${nb.stateRaw} / ${nb.rec.text}`, nb);
      assert(nf.raw === "" && nf.state.balance === 800 && nf.state.balanceAt > AT && nf.rec.lines.length === 1 && nf.rec.lines[0].balanceAt === nf.state.balanceAt,
        `balanceAt with no balance, a balance on offer: read, and balanceAt is the new time, read ${nf.stateRaw} / ${nf.rec.text}`, nf);
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-A3-rotation",
    desc: "D-A3: a call record of exactly 1,048,576 bytes is moved to socialcrawl-calls.jsonl.1 byte for byte before the next line, which starts a fresh record holding only that line, for a pass and for a deny (M_LIMIT); an existing .1 is replaced; at 1,048,575 bytes nothing is moved: the line is appended after the record's bytes and no .1 is made, or an existing .1 is left as it was",
    fn() {
      const rows = [];
      const OLD1 = Buffer.from("an older rotation" + NL);
      for (const [label, size, old1, o, out, moves] of [
        ["1,048,576 bytes, a pass", MiB, null, {}, (r) => r.raw === "", true],
        ["1,048,576 bytes, a deny (M_LIMIT)", MiB, null, { seed: { spent: 190 } }, (r) => r.message === mLimit({ spent: 190, worst: 50, limit: 200, src: srcAuto(800), bf: r.bf }), true],
        ["1,048,576 bytes and an older .1", MiB, OLD1, {}, (r) => r.raw === "", true],
        ["1,048,575 bytes", MiB - 1, null, {}, (r) => r.raw === "", false],
        ["1,048,575 bytes and an older .1", MiB - 1, OLD1, {}, (r) => r.raw === "", false],
      ]) {
        const before = fill(size);
        const r = once(P50, o, (s) => {
          writeFileSync(join(s.revxl, CALLS), before);
          if (old1) writeFileSync(join(s.revxl, `${CALLS}.1`), old1);
          return {};
        });
        const now = r.rec.bytes || Buffer.alloc(0);
        let tail = null;
        try {
          const t = (moves ? now : now.subarray(before.length)).toString("utf8");
          const lines = t.split(NL).filter(Boolean);
          tail = lines.length === 1 && t.endsWith(NL) ? JSON.parse(lines[0]) : null;
        } catch {}
        rows.push(cell(label, [verdict(r), `record ${now.length} bytes`, `.1 ${r.rec.dot1 ? `${r.rec.dot1.length} bytes` : "none"}`]));
        assert(out(r), `${label}: the exact decision, read ${verdict(r)} / ${r.message.slice(0, 160)}`, r);
        assert(tail && JSON.stringify(Object.keys(tail)) === JSON.stringify(KEYS) && tail.sid === r.s.sid, `${label}: exactly one new line, read ${JSON.stringify(now.subarray(Math.max(0, now.length - 400)).toString("utf8"))}`, r);
        if (moves) {
          assert(r.rec.dot1 && r.rec.dot1.equals(before), `${label}: the old record moved to .1 byte for byte, read .1 ${r.rec.dot1 ? r.rec.dot1.length : "none"} bytes`, r);
        } else {
          assert(now.subarray(0, before.length).equals(before) && (old1 ? r.rec.dot1 && r.rec.dot1.equals(old1) : r.rec.dot1 === null),
            `${label}: nothing moved, the line appended, .1 as it was, read .1 ${r.rec.dot1 ? r.rec.dot1.length : "none"} bytes`, r);
        }
      }
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-A4-best-effort",
    desc: "D-A4: a call record that can't be written — its append failing EACCES or EPERM, a folder in its place, its stat failing EACCES, its move to .1 failing EPERM at 1 MiB — changes nothing else, attended and unattended, for a pass, a deny (M_LIMIT) and a routine's pass: the same stdout, exit 0, no stderr, the same session file, day file and unattended log line (but their time, sid and folder) as the same run with the record working, never M_ERROR, under 3 s; each fault is shown to bite (the working run appends its line; the faulted call record op threw, or the folder took no line)",
    fn() {
      const rows = [];
      const cr = crFault();
      let n = 0;
      const norm = (r) => {
        const dirJ = JSON.stringify(r.s.dir).slice(1, -1);       // the session folder as JSON writes it
        const fix = (x) => (x === null || x === undefined ? x : String(x).split(dirJ).join("<dir>").split(r.s.sid).join("<sid>"));
        return JSON.stringify([fix(r.raw), r.exit, r.stderr, fix(r.stateRaw), fix(r.day), r.log.map(({ ts, ...l }) => fix(JSON.stringify(l)))]);
      };
      const viaCR = (op, code) => (s, bite) => ({ node: ["--import", cr.url], env: { CR_FAULT: JSON.stringify([op, code]), CR_FAULT_LOG: bite } });
      const threw = (op) => (r, bite) => (raw(bite) || "").split(NL).includes(op);
      const fs = [
        ["its append fails EACCES", viaCR("appendFileSync", "EACCES"), threw("appendFileSync")],
        ["its append fails EPERM", viaCR("appendFileSync", "EPERM"), threw("appendFileSync")],
        ["a folder in its place", (s) => { mkdirSync(join(s.revxl, CALLS)); return {}; }, (r) => r.rec.text === null],
        ["its stat fails EACCES", viaCR("statSync", "EACCES"), threw("statSync")],
        ["its move to .1 fails EPERM at 1 MiB", (s, bite) => { writeFileSync(join(s.revxl, CALLS), fill(MiB)); return viaCR("renameSync", "EPERM")(s, bite); },
          (r, bite) => threw("renameSync")(r, bite) && r.rec.dot1 === null],
      ];
      for (const [label, cmd, o] of [["a pass", P50, {}], ["a deny (M_LIMIT)", P50, { seed: { spent: 190 } }], ["a routine's pass", P50, { ...RON, day: DAY300() }]]) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          const oo = { ...o, env: { ...(o.env || {}), ...env } };
          const c = once(cmd, oo);
          assert(c.rec.lines && c.rec.lines.length === 1 && c.exit === 0 && c.message !== mError(), `${label}, ${who}, the record working: one line, read ${verdict(c)} / ${JSON.stringify(c.rec.text)}`, c);
          for (const [fl, prep, bit] of fs) {
            const bite = join(cr.dir, `bite-${++n}.log`);
            const r = once(cmd, oo, (s) => prep(s, bite));
            rows.push(cell(`${label}, ${who}: ${fl}`, [verdict(r), `${r.ms} ms`, `same as working ${norm(r) === norm(c)}`, `bit ${bit(r, bite)}`]));
            assert(norm(r) === norm(c) && r.exit === 0 && r.stderr === "" && r.message !== mError() && r.ms < 3000,
              `${label}, ${who}, ${fl}: exactly as with the record working, read ${norm(r).slice(0, 300)} vs ${norm(c).slice(0, 300)} / ${r.ms} ms`, r);
            assert(bit(r, bite), `${label}, ${who}, ${fl}: the fault bit, read ${raw(bite)} / ${JSON.stringify(r.rec.text && r.rec.text.slice(0, 80))}`, r);
          }
        }
      }
      drop(cr);
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-A5-revxl-folder",
    desc: "D-A5 (3c HUNT 1): through Bash, through PowerShell and with no tool_name, attended and unattended (round 2), rm -rf ~/.claude/revxl/sessions, rm -rf ~/.claude/revxl, mv ~/.claude/revxl/sessions /tmp/x, Remove-Item -Recurse -Force $env:USERPROFILE/.claude/revxl/sessions (backslashes), rm ~/.claude/revxl/sessions/*, del %USERPROFILE%/.claude/revxl/sessions (backslashes), rd /s /q C:/Users/x/.claude/revxl (backslashes), Move-Item ~/.claude/revxl x and ren ~/.claude/revxl old are each denied with exactly M_TAMPER, WHAT command and NAME the revxl folder, with nothing in the session folder changed; a command that also names a guarded file gets that file's NAME (K1-K5 first)",
    fn() {
      const rows = [];
      const cmds = [
        "rm -rf ~/.claude/revxl/sessions",
        "rm -rf ~/.claude/revxl",
        "mv ~/.claude/revxl/sessions /tmp/x",
        `Remove-Item -Recurse -Force ${bs("$env:USERPROFILE", ".claude", "revxl", "sessions")}`,
        "rm ~/.claude/revxl/sessions/*",
        `del ${bs("%USERPROFILE%", ".claude", "revxl", "sessions")}`,
        `rd /s /q ${bs("C:", "Users", "x", ".claude", "revxl")}`,
        "Move-Item ~/.claude/revxl x",
        "ren ~/.claude/revxl old",
      ];
      for (const cmd of cmds) everywhere(rows, cmd, cmd, FOLDER);   // round 2: attended and unattended
      for (const [cmd, k] of [
        ["rm -rf ~/.claude/revxl/sessions && rm ~/.claude/revxl/socialcrawl-budget.json", 0],
        ["mv ~/.claude/revxl/socialcrawl-day.json ~/.claude/revxl/sessions", 1],
        [`Remove-Item ${bs("$env:USERPROFILE", ".claude", "revxl", "socialcrawl-calls.jsonl")}; Remove-Item ${bs("$env:USERPROFILE", ".claude", "revxl")}`, 3],
        ["rm -rf ~/.claude/revxl/sessions/socialcrawl-abc.json ~/.claude/revxl", 4],
      ]) {
        const r = once(cmd, {});
        rows.push(cell(`K first: ${cmd}`.slice(0, 62), [verdict(r), r.message.slice(43, 90)]));
        assert(r.raw === denyOut(mTamper("command", NAMES[k])) && r.same, `${cmd}: the guarded file's NAME first, ${NAMES[k]}, read ${r.message.slice(0, 160)}`, r);
      }
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-A6-ordinary-passes",
    desc: "D-A6 (3c HUNT 4): through Bash and through PowerShell these pass untouched (no output, exit 0, nothing changed): mv and rm of a file in a brand folder under ~/.claude/revxl, ls ~/.claude/revxl, cat ~/.claude/revxl/jev-ask.json, grep -n socialcrawl-day in the installed plugin cache under revxl-marketplace (no longer a revxl location), diff a b | grep revxl-marketplace, git log --oneline and echo removed revxl; beside twins that are denied: rm -rf of the brand folder's revxl, and grep -n socialcrawl-day -- ~/.claude/revxl",
    fn() {
      const rows = [];
      const pass = [
        "mv ~/.claude/revxl/examplebrand/voc/a.md ~/.claude/revxl/examplebrand/voc/b.md",
        "rm ~/.claude/revxl/examplebrand/voc/old.md",
        "ls ~/.claude/revxl",
        "cat ~/.claude/revxl/jev-ask.json",
        "grep -n socialcrawl-day ~/.claude/plugins/cache/revxl-marketplace/x/credit-guard.mjs",
        "diff a b | grep revxl-marketplace",
        "git log --oneline",
        "echo removed revxl",
      ];
      for (const tool of ["Bash", "PowerShell"]) {
        for (const cmd of pass) {
          const r = once(cmd, { extra: { tool_name: tool } });
          rows.push(cell(`${tool}: ${cmd}`.slice(0, 62), [verdict(r), `unchanged ${r.same}`]));
          assert(r.raw === "" && r.exit === 0 && r.same, `${tool}: ${cmd}: passes untouched, read ${verdict(r)} / ${r.message.slice(0, 160)} / unchanged ${r.same}`, r);
        }
        for (const [cmd, name] of [["rm -rf ~/.claude/revxl", FOLDER], ["grep -n socialcrawl-day -- ~/.claude/revxl", NAMES[1]]]) {
          const r = once(cmd, { extra: { tool_name: tool } });
          rows.push(cell(`  twin, ${tool}: ${cmd}`.slice(0, 62), [verdict(r)]));
          assert(r.raw === denyOut(mTamper("command", name)), `twin, ${tool}: ${cmd}: exactly M_TAMPER (${name}), read ${r.message.slice(0, 160)}`, r);
        }
      }
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-A7-write-stream-and-short-name",
    desc: "D-A7 (3c HUNT 2, 3): a Write, Edit, MultiEdit and NotebookEdit of C:/Users/x/.claude/revxl/socialcrawl-budget.json::$DATA (backslashes and forward slashes) and of .../socialcrawl-day.json:x are denied with exactly M_TAMPER, WHAT edit and that file's NAME; so is a Write of the real 8.3 short name of a budget file made in a temp folder named revxl (read with cmd /c dir /x), its one realpath seen by a spy; a spy on every fs call (realpath included) sees none for an ordinary Write, a Write of an ordinary file's stream and a Write under a folder holding ~, and exactly one realpath, which fails, for a ~ name that doesn't exist, which passes untouched",
    fn() {
      const rows = [];
      for (const [label, path, k] of [
        ["::$DATA, backslashes", bs(REAL, "socialcrawl-budget.json::$DATA"), 0],
        ["::$DATA, forward slashes", bs(REAL, "socialcrawl-budget.json::$DATA").split(B).join("/"), 0],
        [":x, backslashes", bs(REAL, "socialcrawl-day.json:x"), 1],
        [":x on a session file", bs(REAL, "sessions", "socialcrawl-abc.json:x"), 4],
      ]) {
        const seen = [];
        for (const tool of TOOLS) {
          const r = once("", { extra: edit(tool, path) });
          seen.push(`${tool} ${verdict(r)}`);
          assert(r.raw === denyOut(mTamper("edit", NAMES[k])) && r.same, `${label}, ${tool}: exactly M_TAMPER (edit, ${NAMES[k]}), read ${verdict(r)} / ${r.message.slice(0, 160)}`, r);
        }
        rows.push(cell(label, seen));
      }
      const spy = ioSpy();
      let n = 0;
      const spied = (label, path, env = {}) => {
        const log = join(spy.dir, `run-${++n}.log`);
        writeFileSync(log, "");
        const r = once("", { extra: edit("Write", path), env }, () => ({ node: ["--import", spy.url], env: { SPY_LOG: log } }));
        const calls = (raw(log) || "").split(NL).filter(Boolean).map((l) => JSON.parse(l));
        rows.push(cell(label, [verdict(r), `fs calls ${JSON.stringify(calls.map((c) => `${c[0]} ${c[2]}`))}`]));
        return { r, calls };
      };
      const alias = shortName("socialcrawl-budget.json");
      if (alias.path) {
        const { r, calls } = spied("a Write of the 8.3 short name of a budget file", alias.path);
        assert(r.raw === denyOut(mTamper("edit", NAMES[0])) && calls.length === 1 && calls[0][0] === "realpathSync.native" && calls[0][2] === "ok",
          `the 8.3 name ${alias.path}: exactly M_TAMPER (the budget file) after one realpath, read ${r.message.slice(0, 160)} / ${JSON.stringify(calls)}`, r);
      } else rows.push(cell("a Write of the 8.3 short name: SKIPPED", [alias.why]));
      rmSync(alias.dir, { recursive: true, force: true });
      const d = mkdtempSync(join(tmpdir(), "sc-p3d-io-"));
      for (const [label, path] of [["an ordinary Write", join(d, "notes.md")], ["a Write of an ordinary file's stream", `${join(d, "notes.md")}::$DATA`],
        ["a Write under a folder holding ~", join(d, "A~1", "notes.md")]]) {
        const { r, calls } = spied(label, path);
        assert(r.raw === "" && r.same && calls.length === 0, `${label}: passes with no fs call at all, read ${verdict(r)} / ${JSON.stringify(calls)}`, r);
      }
      const missing = join(d, "revxl", "SOCIAL~9.JSO");
      const { r, calls } = spied("a Write of a ~ name that doesn't exist", missing);
      assert(r.raw === "" && r.same && calls.length === 1 && calls[0][0] === "realpathSync.native" && calls[0][1] === missing && calls[0][2] === "ENOENT",
        `a ~ name that doesn't exist: passes, exactly one realpath, failed, and no other I/O, read ${verdict(r)} / ${JSON.stringify(calls)}`, r);
      rmSync(d, { recursive: true, force: true });
      drop(spy);
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-A8-utf16le",
    desc: "D-A8 (3c HUNT 6): a UTF-16LE budget file (FF FE, as PowerShell 5.1's > and Out-File write it) of {sessionBudget: 50} is the limit (40 + 50 is exactly M_LIMIT naming 50 and your session budget; 0 + 50 passes and counts 50); a UTF-16LE session file at 100 reads as 100 (50 more passes and it is saved at 150 as UTF-8 with no mark), never lost; a UTF-8 budget with its mark is still the limit; UTF-16BE, two UTF-16LE marks, a lone FF FE and FF FE before garbage give a settings-file error for the budget and a lost total for the session",
    fn() {
      const rows = [];
      const put = (file, buf) => (s) => { writeFileSync(file(s), buf); return {}; };
      const bfOf = (s) => s.bf;
      const lim50 = (r) => r.decision === "deny" && r.message === mLimit({ spent: 40, worst: 50, limit: 50, src: SRC_SESSION, bf: r.bf });
      const b40 = once(P50, { seed: { spent: 40 } }, put(bfOf, u16le(B50)));
      const b0 = once(P50, {}, put(bfOf, u16le(B50)));
      const b8 = once(P50, { seed: { spent: 40 } }, put(bfOf, u8bom(B50)));
      rows.push(cell("a UTF-16LE budget of 50: 40 + 50, 0 + 50; UTF-8 with its mark", [verdict(b40), `${verdict(b0)} counted ${b0.state.spent}`, verdict(b8)]));
      assert(lim50(b40), `a UTF-16LE budget, 40 + 50: exactly M_LIMIT at 50, read ${b40.message.slice(0, 220)}`, b40);
      assert(b0.raw === "" && b0.state.spent === 50, `a UTF-16LE budget, 0 + 50: passes, counted 50, read ${verdict(b0)} / ${b0.stateRaw}`, b0);
      assert(lim50(b8), `a UTF-8 budget with its mark, 40 + 50: still exactly M_LIMIT at 50, read ${b8.message.slice(0, 220)}`, b8);
      const st = once(P50, {}, (s) => { writeFileSync(s.stateFile, u16le(JSON.stringify({ balance: 800, spent: 100 }))); return {}; });
      rows.push(cell("a UTF-16LE session file at 100, 50 more", [verdict(st), `saved ${JSON.stringify(st.stateRaw)}`]));
      assert(st.raw === "" && st.stateRaw === JSON.stringify({ balance: 800, spent: 150, holds: {}, fixed: 150, usage: 0, full: 0 }), `a UTF-16LE session file at 100: passes, saved at 150 as UTF-8 with no mark, never lost, read ${verdict(st)} / ${JSON.stringify(st.stateRaw)}`, st);
      // UTF-16BE, two UTF-16LE marks, a lone mark and a mark before garbage deny paid calls and still lose a session total.
      for (const [label, enc] of [["UTF-16BE", (t) => u16be(t)], ["two UTF-16LE marks", (t) => Buffer.concat([Buffer.from([0xff, 0xfe]), u16le(t)])],
        ["a lone FF FE", () => Buffer.from([0xff, 0xfe])], ["FF FE before garbage", () => Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from("{bad")])]]) {
        const bb = once(P50, { seed: { spent: 40 } }, put(bfOf, enc(B50)));
        const ss = once(P50, {}, (s) => { writeFileSync(s.stateFile, enc(JSON.stringify({ balance: 800, spent: 100 }))); return {}; });
        rows.push(cell(label, [`budget: ${verdict(bb)} counted ${bb.state.spent}`, `session: ${verdict(ss)}`]));
        assert(bb.decision === "deny" && bb.message === M_SETTINGS && bb.state.spent === 40, `${label}, the budget file: unreadable settings deny, nothing counted, read ${verdict(bb)} / ${bb.message.slice(0, 160)}`, bb);
        assert(ss.decision === "deny" && ss.message === M_LOST && ss.state && ss.state.lost === true, `${label}, the session file: M_LOST, saved lost, read ${ss.message.slice(0, 120)} / ${ss.stateRaw}`, ss);
      }
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-mutants",
    desc: "D-A10 MUTANTS: each mutant copy of the guard turns a probe red that this build passes — a record line appended on the not-plain deny, and the session-lock gate dropped; the command, and the key, put in the line; the rotation removed; the append not wrapped (a folder at the record sends a deny and an unattended pass to the guard's own error path); the revxl folder rule dropped; the folder token widened to revxl/<anything>; the location test reverted to a substring; the stream strip removed; the short-name read removed (skipped, with its reason, when the temp volume makes no 8.3 names); and the UTF-16LE decode removed",
    fn() {
      const rows = [];
      const alias = shortName("socialcrawl-budget.json");
      const SENT = `curl -s -H "x-api-key: ${KEY}" "${V1}prism/leads?query=${QV}"`;
      const sentinel = ["the sentinel pass", SENT, { env: { SOCIALCRAWL_API_KEY: KEY } }, null, (r) => r.raw === "" && r.rec.lines && r.rec.lines.length === 1 && !leaks(r.rec.text).length && !r.rec.text.includes(SENT)];
      const notPlain = ["the not-plain deny", NP, {}, null, (r) => r.message === M_NOTPLAIN && r.rec.text === null];
      const folderAt = (s) => { mkdirSync(join(s.revxl, CALLS)); return {}; };
      const cases = [
        ["a line on the not-plain deny", [['    return deny(NOT_BASH ? M_NOTBASH : M_NOTPLAIN, "not-plain");\n', '    logCall("deny", "not-plain", null);\n    return deny(NOT_BASH ? M_NOTBASH : M_NOTPLAIN, "not-plain");\n']], [notPlain]],
        ["the session-lock gate dropped", [['    if (locked) logCall("deny", kind, st ? st.spent : null);\n', '    logCall("deny", kind, st ? st.spent : null);\n']], [notPlain]],
        ["the command in the line", [["ts: new Date().toISOString(), sid, paths: logPaths(),", "ts: new Date().toISOString(), command: cmd, sid, paths: logPaths(),"]], [sentinel]],
        ["the key in the line", [["ts: new Date().toISOString(), sid, paths: logPaths(),", "ts: new Date().toISOString(), key: process.env.SOCIALCRAWL_API_KEY, sid, paths: logPaths(),"]], [sentinel]],
        ["the rotation removed", [['      if (s && s.size >= 1048576) renameSync(CR, CR + ".1");\n', ""]], [
          ["a pass at 1 MiB", P50, {}, (s) => { writeFileSync(join(s.revxl, CALLS), fill(MiB)); return {}; }, (r) => r.raw === "" && !!r.rec.dot1 && r.rec.dot1.equals(fill(MiB)) && r.rec.lines && r.rec.lines.length === 1],
        ]],
        ["the append not wrapped", [
          ['    try {\n      const CR = join(revxl, "socialcrawl-calls.jsonl");\n', '    {\n      const CR = join(revxl, "socialcrawl-calls.jsonl");\n'],
          [`      }) + "${B}n");\n    } catch {}\n`, `      }) + "${B}n");\n    }\n`],
        ], [
          ["a folder at the record, M_LIMIT attended", P50, { seed: { spent: 190 } }, folderAt, (r) => r.message === mLimit({ spent: 190, worst: 50, limit: 200, src: srcAuto(800), bf: r.bf })],
          ["a folder at the record, a pass unattended", P50, { env: UN }, folderAt, (r) => r.raw === "" && r.state.spent === 50],
        ]],
        ["the revxl folder rule dropped", [[R2.use, "      if (false) k = 5;"]], [   // round 2: its new line
          ["rm -rf ~/.claude/revxl/sessions", "rm -rf ~/.claude/revxl/sessions", {}, null, (r) => r.raw === denyOut(mTamper("command", FOLDER))],
        ]],
        ["the folder token widened to revxl/<anything>", [[`  ${R2.alt1},`, `  /revxl([${B}${B}/][^${B}s"';|&)]*)?(?=["'${B}s;|&)]|$)/,`]], [   // round 2: alternative 1
          ["rm of a brand folder's file", "rm ~/.claude/revxl/examplebrand/voc/old.md", {}, null, (r) => r.raw === "" && r.same],
        ]],
        ["the location test reverted to a substring", [["!REVXL_AT.test(c)", '!c.includes("revxl")']], [
          ["grep in the revxl-marketplace cache", "grep -n socialcrawl-day ~/.claude/plugins/cache/revxl-marketplace/x/credit-guard.mjs", {}, null, (r) => r.raw === "" && r.same],
        ]],
        ["the stream strip removed", [["stream < 0 ? path : path.slice(0, stream)", "path"]], [
          ["a Write of the budget file's ::$DATA", "", { extra: edit("Write", bs(REAL, "socialcrawl-budget.json::$DATA")) }, null, (r) => r.raw === denyOut(mTamper("edit", NAMES[0]))],
        ]],
        ["the short-name read removed", [[`        try { base = realpathSync.native(abs).toLowerCase().split(/[${B}${B}/]+/).pop(); } catch {}\n`, ""]],
          alias.path ? [["a Write of a budget file's 8.3 name", "", { extra: edit("Write", alias.path) }, null, (r) => r.raw === denyOut(mTamper("edit", NAMES[0]))]] : []],
        ["the UTF-16LE decode removed", [['b[0] === 0xff && b[1] === 0xfe ? b.toString("utf16le", 2) : ', ""]], [
          ["a UTF-16LE budget of 50, 40 + 50", P50, { seed: { spent: 40 } }, (s) => { writeFileSync(s.bf, u16le(B50)); return {}; },
            (r) => r.message === mLimit({ spent: 40, worst: 50, limit: 50, src: SRC_SESSION, bf: r.bf })],
        ]],
      ];
      for (const [name, pairs, probes] of cases) {
        const m = mutant(name.replace(/[^a-z0-9]+/gi, "-").slice(0, 40), pairs);
        if (!probes.length) rows.push(cell(`${name}: SKIPPED`, [alias.why || "no probe"]));
        for (const [label, cmd, o, prep, ok] of probes) {
          const fix = once(cmd, o, prep || undefined);
          const mut = once(cmd, { ...o, guard: m.file }, prep || undefined);
          rows.push(cell(`${name}: ${label}`.slice(0, 62), [`build ${verdict(fix)}`, `mutant ${verdict(mut)} ${mut.message.slice(0, 40)}`]));
          assert(ok(fix), `${name}, ${label}: the build behaves, read ${verdict(fix)} / ${fix.message.slice(0, 160)} / ${JSON.stringify(fix.rec.text && fix.rec.text.slice(0, 160))}`, fix);
          assert(!ok(mut), `${name}, ${label}: the mutant is caught (it behaves wrongly), read ${verdict(mut)} / ${mut.message.slice(0, 160)} / ${JSON.stringify(mut.rec.text && mut.rec.text.slice(0, 160))}`, mut);
        }
        rmSync(m.dir, { recursive: true, force: true });
      }
      rmSync(alias.dir, { recursive: true, force: true });
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-R2-H1-location",
    desc: "Round 2, H1 (a regression from 4677e75; R2-1): through Bash, PowerShell and no tool_name, attended and unattended, a guard file named beside a revxl location with no slash or space before it — cd ~/.claude && echo '{\"sessionBudget\":20000}' >revxl/socialcrawl-budget.json, echo x>>revxl/socialcrawl-day.json, cat>revxl/socialcrawl-budget.json, cp x {revxl,y}/socialcrawl-budget.json, echo x > \"$env:USERPROFILE/.claude/revxl./socialcrawl-budget.json\" (backslashes), curl -s -orevxl/socialcrawl-budget.json x — is denied with exactly M_TAMPER naming that file (the K NAME), nothing changed, as at 4677e75; revxl-marketplace is still no location: the grep in the plugin cache and diff a b | grep revxl-marketplace pass untouched",
    fn() {
      const rows = [];
      for (const [cmd, k] of H1) everywhere(rows, cmd, cmd, NAMES[k]);
      for (const cmd of ["grep -n socialcrawl-day ~/.claude/plugins/cache/revxl-marketplace/x/credit-guard.mjs", "diff a b | grep revxl-marketplace"]) {
        everywhere(rows, `twin: ${cmd}`, cmd, null);
      }
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-R2-H2-verb",
    desc: "Round 2, H2 (R2-2): through Bash, PowerShell and no tool_name, attended and unattended, a delete wrapped or qualified — bash -c \"rm -rf ~/.claude/revxl/sessions\", sh -c 'rm -rf ~/.claude/revxl', cmd /c \"rd /s /q %USERPROFILE%/.claude/revxl\", powershell -c \"Remove-Item -Recurse ~/.claude/revxl/sessions\", pwsh -Command \"rm -r ~/.claude/revxl\", a backslash rm, /bin/rm, rm.exe, \"rm\" and Microsoft.PowerShell.Management/Remove-Item (backslashes where Windows writes them) — is denied with exactly M_TAMPER naming the revxl folder, nothing changed",
    fn() {
      const rows = [];
      for (const cmd of H2) everywhere(rows, cmd, cmd, FOLDER);
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-R2-H3-folder-token",
    desc: "Round 2, H3 (R2-3): through Bash, PowerShell and no tool_name, attended and unattended, the revxl folder followed by a backtick, a redirect, a comma, a dot segment or a dot — x=`rm -rf ~/.claude/revxl`, rd /s /q %USERPROFILE%/.claude/revxl/sessions>nul (backslashes), Remove-Item -Recurse -Force ~/.claude/revxl/sessions,~/x, rm -rf ~/.claude/revxl/./sessions, rm -rf ~/.claude/revxl/sessions/../sessions, rm -rf ~/.claude/revxl. — is denied with exactly M_TAMPER naming the revxl folder, nothing changed",
    fn() {
      const rows = [];
      for (const cmd of H3) everywhere(rows, cmd, cmd, FOLDER);
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-R2-H4-scope",
    desc: "Round 2, H4 (R2-3): through Bash, PowerShell and no tool_name, attended and unattended, rm -rf ~/.claude, rm -rf ~/.claude/, mv ~/.claude/revxl/sessions{,.bak}, rm -rf ~/.claude/revxl/abc/../sessions, and rm -rf of the session's own SC_REVXL_HOME not named revxl (with backslashes and with forward slashes) are denied with exactly M_TAMPER naming the revxl folder, nothing changed; beside twins that pass untouched: an rm of a file inside that SC_REVXL_HOME, either slash",
    fn() {
      const rows = [];
      for (const [label, cmd, prep] of H4) everywhere(rows, label, cmd, FOLDER, prep);
      everywhere(rows, "twin: rm <SC_REVXL_HOME>/examplebrand/x.md, backslashes", (s) => `rm ${bs(homeOf(s), "examplebrand", "x.md")}`, null, atHome);
      everywhere(rows, "twin: rm <SC_REVXL_HOME>/jev-ask.json, forward slashes", (s) => `rm ${bs(homeOf(s), "jev-ask.json").split(B).join("/")}`, null, atHome);
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-R2-passes",
    desc: "Round 2 (R2-1 to R2-3): through Bash, PowerShell and no tool_name, attended and unattended, ordinary work passes untouched — the 8 D-A6 commands, rm ~/.claude/settings.json, rm -rf node_modules, mv a b, rm -rf ~/.claude/plugins/cache/revxl-marketplace/x, rm ~/.claude/.credentials.bak, rm -rf ~/.claude-backup, git rm -r --cached src/form.md and rm ~/.claude/revxl/examplebrand/voc/old.md; beside near twins that round 2 denies: rm -rf ~/.claude, rm -rf ~/.claude/, rm -rf ~/.claude/., rm -rf ~/.claude/revxl. and rm -rf ~/.claude/revxl/examplebrand/../sessions",
    fn() {
      const rows = [];
      for (const cmd of R2PASS) everywhere(rows, cmd, cmd, null);
      for (const cmd of ["rm -rf ~/.claude", "rm -rf ~/.claude/", "rm -rf ~/.claude/.", "rm -rf ~/.claude/revxl.", "rm -rf ~/.claude/revxl/examplebrand/../sessions"]) {
        everywhere(rows, `twin: ${cmd}`, cmd, FOLDER);
      }
      console.log(rows.join(NL));
    },
  },
  {
    id: "P3d-R2-mutants",
    desc: "Round 2 MUTANTS: each mutant copy of the guard turns a probe red that this build passes — R2-1 reverted to r1's location regex; the verb's left boundary reverted to r1's; (.exe)? removed; each of the four folder alternatives removed (revxl or revxl/sessions with no child, a .. under revxl, the .claude folder, <revxl> itself); and the not-a-child lookahead dropped from alternatives 1, 3 and 4",
    fn() {
      const rows = [];
      const deny = (name) => (r) => r.raw === denyOut(mTamper("command", name));
      const pass = (r) => r.raw === "" && r.same;
      const cases = [
        ["R2-1 reverted to r1's location regex", [[R2.at, R2.atR1]], [[H1[0][0], null, deny(NAMES[0])], [H1[3][0], null, deny(NAMES[0])]]],
        ["the verb's left boundary reverted to r1's", [[R2.verbLeft, R2.verbLeftR1]], [["/bin/rm -rf ~/.claude/revxl", null, deny(FOLDER)], ["=rm -rf ~/.claude/revxl", null, deny(FOLDER)]]],
        ["(.exe)? removed", [[R2.exe, ""]], [["rm.exe -rf ~/.claude/revxl", null, deny(FOLDER)]]],
        ["alternative 1 removed (revxl, revxl/sessions)", [[`  ${R2.alt1},${NL}`, ""]], [["rm -rf ~/.claude/revxl/sessions", null, deny(FOLDER)]]],
        ["alternative 2 removed (a .. under revxl)", [[`${R2.alt2}${NL}`, ""]], [["rm -rf ~/.claude/revxl/abc/../sessions", null, deny(FOLDER)]]],
        ["alternative 3 removed (the .claude folder)", [[`  ${R2.alt3},${NL}`, ""]], [["rm -rf ~/.claude", null, deny(FOLDER)]]],
        ["alternative 4 removed (<revxl> itself)", [[" || atRevxl(c, rx())", ""]], [[(s) => `rm -rf ${homeOf(s)}`, atHome, deny(FOLDER)]]],
        ["the not-a-child lookahead dropped (1)", [[R2.alt1, R2.alt1.replace(R2.child, "")]], [["rm ~/.claude/revxl/examplebrand/voc/old.md", null, pass]]],
        ["the not-a-child lookahead dropped (3)", [[R2.alt3, R2.alt3.replace(R2.child, "")]], [["rm ~/.claude/settings.json", null, pass]]],
        ["the not-a-child lookahead dropped (4)", [[R2.tail4, R2.tail4.replace(R2.child, "")]], [[(s) => `rm ${bs(homeOf(s), "examplebrand", "x.md")}`, atHome, pass]]],
      ];
      for (const [name, pairs, probes] of cases) {
        const m = mutant(name.replace(/[^a-z0-9]+/gi, "-").slice(0, 40), pairs);
        for (const [cmd, prep, ok] of probes) {
          const fix = once(cmd, {}, prep || undefined);
          const mut = once(cmd, { guard: m.file }, prep || undefined);
          rows.push(cell(name.slice(0, 62), [`build ${verdict(fix)}`, `mutant ${verdict(mut)} ${mut.message.slice(0, 40)}`]));
          assert(ok(fix), `${name}: the build behaves, read ${verdict(fix)} / ${fix.message.slice(0, 160)}`, fix);
          assert(!ok(mut), `${name}: the mutant is caught (it behaves wrongly), read ${verdict(mut)} / ${mut.message.slice(0, 160)}`, mut);
        }
        rmSync(m.dir, { recursive: true, force: true });
      }
      console.log(rows.join(NL));
    },
  },
];
