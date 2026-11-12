/*
 * Phase 3b (0.4.0): the routine day file written under its own lock (R1-R3, R7-R9), and the four fixes
 * carried from the 3a check (H1 = R5, H2 = R4, H5/H7 = R6, f1 = R10). One fixture per item of List A in
 * "Phase 3b Checker Fixtures - Both Lists - 10.10.26.md"; B-A10's values join P3a-A10-A11's silent list
 * (d28.mjs) and its f1 mutant is in P3b-mutants. Each fixture here was run red against slice 3a
 * (ef8a2c6) before it was run green. Messages are checked whole, by equality (lib.mjs builds them from
 * the fixtures doc).
 *
 * Synchronous; every guard run in its own temp SC_REVXL_HOME (lib.mjs session()), but for the race,
 * whose sessions share one folder made under a session's own temp dir. Zero credits, zero network:
 * every run is offline (lib.mjs: no key, a scratch home, dead proxies).
 */
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import {
  session, V1, TSCRIPT, GUARD, COSTS, T, M_LOST, mLimit, mStateRead, mBudgetRead,
  ROUTINE, ROUTINES_ON, SRC_SESSION, srcAuto, today, assert,
} from "../lib.mjs";
import { stateFault } from "./balance.mjs";

const UN = { CLAUDE_CODE_SESSION_ATTENDED: "0" };
const M_SETTINGS = "SocialCrawl call not run: your SocialCrawl settings file can't be read, so this session's credit limit can't be checked. Re-save your limit in SocialCrawl → Settings to fix it." + T;
const RUN = { ...ROUTINE, ...UN };                               // a routine's env, unattended
const RON = { budget: ROUTINES_ON, env: ROUTINE };
const P50 = `curl -s "${V1}prism/leads?query=x"`;              // plain, flat 50
const P50N = (i) => `curl -s "${V1}prism/leads?query=r${i}"`;  // the same, one per run of a race
const P1 = `curl -s "${V1}amazon/shop?q=a"`;                    // plain, flat 1
const FREE = `curl -s "${V1}credits/balance"`;                  // plain, free: the free-plain pass
const MON = `curl -s "${V1}web/monitors"`;                      // plain, a GET twin: worst 0, committed
const COH = `curl -s "${V1}cohorts?segment=a"`;                 // plain, unpriced: worst 0, committed
const NP = `echo '${V1}prism/leads?query=x'`;                   // not plain
const KINDS = ["not-plain", "lost", "over-limit", "under-cap", "error", "transcript-locked"];
const FIELDS = ["ts", "session_id", "decision", "kind", "paths", "cmdWorst", "committed", "cap"];
const D = Number((readFileSync(GUARD, "utf8").match(/^const D = (\d+);$/m) || [])[1]);
const B50 = '{"sessionBudget":50}';
const DAY300 = () => ({ date: today(), spent: 300, sessions: { other: 300 } });
/** recorded()'s refusal, word for word (P3a-A17). */
const refusal = (sf, worst, why) =>
  `SocialCrawl call not run: the credit guard couldn't record it, and a call it can't record would run uncounted (this command's ` +
  `worst case is ~${worst} credits). Reason: ${why}. Session file: ${sf}. Nothing was sent. Run the command again; if it is ` +
  `refused again, check that the session file and its folder exist and can be written.`;
const cell = (label, parts) => `    ${label.padEnd(54)} ${parts.join(" | ")}`;
const what = (r) => r.decision || (r.raw ? "?" : "pass");
const raw = (p) => { try { return readFileSync(p, "utf8"); } catch { return null; } };
const name = (p) => String(p).split(/[\\/]/).pop();
/** The day lock and temp files, and any session lock, left in a revxl folder: none after a run that ends. */
const leftovers = (revxl) => [
  ...readdirSync(revxl).filter((n) => n.startsWith("socialcrawl-day.json.")),
  ...(existsSync(join(revxl, "sessions")) ? readdirSync(join(revxl, "sessions")).filter((n) => n.endsWith(".lock")) : []),
];

/** A session (balance 800 cached unless `balance: null`), its file seeded unless `seed: null`, with an optional budget and day file. */
function open(o = {}) {
  const s = session(o.balance === null || o.seed === null ? { balance: null } : {});
  if (o.seed !== null) s.seed(o.seed || { spent: 0 });
  if (o.budget !== undefined) s.budget(o.budget);
  if (o.day !== undefined) s.day(o.day);
  return s;
}
/** One run in a fresh session built by open(o); `prep(s)` adds run options (a preload and its env). */
function once(cmd, o = {}, prep = () => ({})) {
  const s = open(o);
  const p = prep(s);
  const before = { state: s.stateRaw(), day: raw(s.df) };
  const r = s.run(cmd, { guard: o.guard, extra: o.extra, node: p.node, env: { ...(o.env || {}), ...(p.env || {}) } });
  Object.assign(r, { s, before, state: s.state(), stateRaw: s.stateRaw(), log: s.logLines(), day: raw(s.df), left: leftovers(s.revxl) });
  s.cleanup();
  return r;
}
/** The state-file fault preload of balance.mjs, with its folder for cleanup; `on(f, file, spec)` aims it at any file. */
function faults() {
  const url = stateFault();
  return { url, dir: dirname(fileURLToPath(url)), on: (file, spec, env = {}) => ({ node: ["--import", url], env: { ...env, STATE_FAULT: JSON.stringify([spec[0], file, ...spec.slice(1)]) } }) };
}
/** A preload in a temp dir of its own, with node:fs as `fs` and the path match `same` in scope. */
function preload(id, body) {
  const d = mkdtempSync(join(tmpdir(), `sc-p3b-${id}-`));
  const f = join(d, `${id}.mjs`);
  writeFileSync(f,
    `import { createRequire, syncBuiltinESMExports } from "node:module";\n` +
    `import { resolve } from "node:path";\n` +
    `const fs = createRequire(import.meta.url)("node:fs");\n` +
    `const same = (p, f) => typeof p === "string" && resolve(p).toLowerCase() === resolve(f).toLowerCase();\n` +
    body +
    `syncBuiltinESMExports();\n`);
  return { url: pathToFileURL(f).href, dir: d };
}
const drop = (...pre) => { for (const p of pre) rmSync(p.dir, { recursive: true, force: true }); };
/** Logs every call by path under SPY_DIR (reads, writes, renames, deletes, appends, stats, folder and open calls) to SPY_LOG: [op, path, to]. */
const writeSpy = () => preload("spy",
  `const append = fs.appendFileSync, dir = resolve(process.env.SPY_DIR).toLowerCase();\n` +
  `const under = (p) => typeof p === "string" && resolve(p).toLowerCase().startsWith(dir);\n` +
  `for (const op of ["readFileSync", "writeFileSync", "renameSync", "unlinkSync", "appendFileSync", "statSync", "lstatSync", "existsSync", "mkdirSync", "readdirSync", "openSync", "rmSync", "copyFileSync", "accessSync"]) {\n` +
  `  const real = fs[op];\n` +
  `  fs[op] = (p, ...a) => { if (under(p)) append(process.env.SPY_LOG, JSON.stringify([op, resolve(p), op === "renameSync" ? resolve(a[0]) : null]) + "\\n"); return real(p, ...a); };\n` +
  `}\n`);
const spied = (log) => readFileSync(log, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
/** Makes a rename onto RENAME_FAIL throw EPERM, the target left as it was. */
const renameFails = () => preload("rename",
  `const rename = fs.renameSync;\n` +
  `fs.renameSync = (p, q, ...a) => { if (same(q, process.env.RENAME_FAIL)) throw Object.assign(new Error("EPERM, forced by P3b"), { code: "EPERM" }); return rename(p, q, ...a); };\n`);
/** A copy of the guard (costs.json beside it) with each [anchor, replacement] applied; each anchor must occur exactly once. */
function mutant(id, pairs) {
  let src = readFileSync(GUARD, "utf8");
  for (const [anchor, repl] of pairs) {
    assert(src.split(anchor).length === 2, `mutant ${id}: its anchor must occur exactly once in credit-guard.mjs, read ${src.split(anchor).length - 1} x ${JSON.stringify(anchor).slice(0, 100)}`);
    src = src.replace(anchor, () => repl);
  }
  const d = mkdtempSync(join(tmpdir(), `sc-p3b-mut-${id}-`));
  writeFileSync(join(d, "credit-guard.mjs"), src);
  copyFileSync(COSTS, join(d, "costs.json"));
  return { file: join(d, "credit-guard.mjs"), dir: d };
}
/** The guard with no time left from its start: D at 0 (a start slower than D, without the wait). */
const noTime = () => mutant("d0", [[`const D = ${D};`, "const D = 0;"]]);

export default [
  {
    id: "P3b-A1-state-then-day-commit",
    desc: "B-A1 (R1, replayed under D55): in a routine (an old routines block in the budget file), a session save that fails (EBUSY) is refused with recorded()'s words, attended and unattended (logged error), nothing saved, the day file byte-identical and nothing left behind",
    fn() {
      const rows = [];
      const f = faults();
      for (const [who, env] of [["attended", ROUTINE], ["unattended", RUN]]) {
        const r = once(P50, { ...RON, seed: { spent: 100 }, day: DAY300() }, (s) => f.on(s.stateFile, ["busy", "EBUSY"], env));
        rows.push(cell(`the session save fails (EBUSY), ${who}`, [what(r), `day file unchanged ${r.day === r.before.day}`, `left ${JSON.stringify(r.left)}`]));
        assert(r.decision === "deny" && r.message === refusal(r.s.stateFile, 50, "the session file could not be saved (EBUSY)") && r.stateRaw === r.before.state && r.day === r.before.day && !r.left.length,
          `a failed session save, ${who}: refused, nothing saved, the day file byte-identical and nothing left, read ${r.message.slice(0, 160)} / ${r.day} / ${JSON.stringify(r.left)}`, r);
        if (who === "unattended") assert(r.log.length === 1 && r.log[0].decision === "deny" && r.log[0].kind === "error", `a failed session save, unattended: one error line, read ${JSON.stringify(r.log)}`);
      }
      drop(f);
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3b-A4-zero-worst-never-over-limit",
    desc: "B-A4 (R4, H2): with 300 committed against the automatic cap of 200, GET web/monitors and cohorts (worst 0) pass silently, attended and unattended (logged under-cap at worst 0), committing nothing more, and a 1cr call is still denied with exactly M_LIMIT; in a routine beside a day file at 4500 of a perDay of 4000 (D55: never read), GET web/monitors is a silent pass committing nothing, and a 50cr call is a silent pass counted 50, the day file byte-identical",
    fn() {
      const rows = [];
      for (const [label, cmd] of [["GET web/monitors", MON], ["cohorts", COH]]) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          const r = once(cmd, { seed: { spent: 300 }, env });
          rows.push(cell(`${label} at 300 of 200, ${who}`, [what(r), `committed ${r.state.spent}`, `log ${JSON.stringify(r.log.map((l) => `${l.decision}/${l.kind}/${l.cmdWorst}`))}`]));
          assert(r.raw === "" && r.state.spent === 300, `${label} at 300 of 200, ${who}: a silent pass, nothing more committed, read ${what(r)} / ${r.message.slice(0, 120)} / ${r.stateRaw}`, r);
          if (who === "unattended") assert(r.log.length === 1 && r.log[0].decision === "pass" && r.log[0].kind === "under-cap" && r.log[0].cmdWorst === 0 && r.log[0].cap === 200, `${label}, unattended: logged under-cap at worst 0, read ${JSON.stringify(r.log)}`);
        }
      }
      const p = once(P1, { seed: { spent: 300 } });
      assert(p.decision === "deny" && p.message === mLimit({ spent: 300, worst: 1, limit: 200, src: srcAuto(800), bf: p.bf }) && p.state.spent === 300, `a 1cr call at 300 of 200: exactly M_LIMIT, read ${p.message}`, p);
      const day = { date: today(), spent: 4500 };
      const z = once(MON, { ...RON, day });
      rows.push(cell("a routine's GET web/monitors beside today's 4500", [what(z), `committed ${z.state.spent}`, `day unchanged ${z.day === z.before.day}`]));
      assert(z.raw === "" && z.state.spent === 0 && z.day === z.before.day, `a routine's 0-worst call: a silent pass, nothing committed, the day file byte-identical, read ${z.raw} / ${z.stateRaw} / ${z.day}`, z);
      const q = once(P50, { ...RON, day });
      assert(q.raw === "" && q.state.spent === 50 && q.day === q.before.day, `a routine's 50cr call beside today's 4500: a silent pass counted 50 (was M_DAYLIMIT), read ${what(q)} / ${q.message.slice(0, 120)} / ${q.stateRaw}`, q);
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3b-A5-transient-state-read",
    desc: "B-A5 (R5, H1): a session file read that fails once (EBUSY) and then works decides on the real total — 100 + 50 passes and counts 150, 190 + 50 is denied with exactly M_LIMIT naming 190 — and never saves the file as lost; 4 failures then a good read still decide, 5 failures are exactly M_STATEREAD; EBUSY, EPERM or EACCES on every read is exactly M_STATEREAD, attended and unattended (logged error, committed and cap null), the file byte-identical; damaged content (cut-off JSON) is still a lost total, saved lost; a folder at the session path is still M_LOST within 3 s; and the tries stop at D: with no time left, a read that fails once is M_STATEREAD",
    fn() {
      const rows = [];
      const f = faults();
      const a = once(P50, { seed: { spent: 100 } }, (s) => f.on(s.stateFile, ["read", "EBUSY", 1]));
      const b = once(P50, { seed: { spent: 190 } }, (s) => f.on(s.stateFile, ["read", "EBUSY", 1]));
      rows.push(cell("a read that fails once (EBUSY)", [`100 + 50: ${what(a)}, saved ${a.stateRaw}`, `190 + 50: ${what(b)}`]));
      assert(a.raw === "" && a.state.spent === 150 && !a.state.lost, `fails once, 100 + 50: decided on 100, counted 150, never lost, read ${what(a)} / ${a.stateRaw}`, a);
      assert(b.decision === "deny" && b.message === mLimit({ spent: 190, worst: 50, limit: 200, src: srcAuto(800), bf: b.bf }) && b.stateRaw === b.before.state, `fails once, 190 + 50: M_LIMIT naming 190, the file untouched, read ${b.message.slice(0, 200)} / ${b.stateRaw}`, b);
      const four = once(P50, { seed: { spent: 100 } }, (s) => f.on(s.stateFile, ["read", "EBUSY", 4]));
      const five = once(P50, { seed: { spent: 100 } }, (s) => f.on(s.stateFile, ["read", "EBUSY", 5]));
      rows.push(cell("4 failures, then 5", [`4: ${what(four)} (${four.stateRaw})`, `5: ${what(five)}`]));
      assert(four.raw === "" && four.state.spent === 150, `4 failures, then a good read: decided, read ${what(four)} / ${four.stateRaw}`, four);
      assert(five.decision === "deny" && five.message === mStateRead(five.s.stateFile) && five.stateRaw === five.before.state, `5 failures: M_STATEREAD, the file untouched, read ${five.message.slice(0, 200)}`, five);
      for (const code of ["EBUSY", "EPERM", "EACCES"]) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          const r = once(P50, { seed: { spent: 100 } }, (s) => f.on(s.stateFile, ["read", code], env));
          rows.push(cell(`every read ${code}, ${who}`, [what(r), `file unchanged ${r.stateRaw === r.before.state}`, `log ${JSON.stringify(r.log.map((l) => `${l.kind}/${l.committed}/${l.cap}`))}`]));
          assert(r.decision === "deny" && r.message === mStateRead(r.s.stateFile) && r.stateRaw === r.before.state, `every read ${code}, ${who}: exactly M_STATEREAD, the file byte-identical, read ${r.message.slice(0, 200)} / ${r.stateRaw}`, r);
          if (who === "unattended") assert(r.log.length === 1 && r.log[0].decision === "deny" && r.log[0].kind === "error" && r.log[0].committed === null && r.log[0].cap === null, `every read ${code}, unattended: one error line, read ${JSON.stringify(r.log)}`);
        }
      }
      const t = once(P50, {}, (s) => { writeFileSync(s.stateFile, '{"spent":190,"pend'); return {}; });
      assert(t.decision === "deny" && t.message === M_LOST && t.state && t.state.lost === true, `cut-off JSON: still M_LOST, saved lost, read ${t.message.slice(0, 120)} / ${t.stateRaw}`, t);
      const dir = once(P50, { seed: null }, (s) => { mkdirSync(s.stateFile); return {}; });
      rows.push(cell("damaged content, then a folder at the session path", [`${what(t)} saved ${t.stateRaw}`, `${what(dir)} after ${dir.ms} ms`]));
      assert(dir.decision === "deny" && dir.message === M_LOST && dir.ms < 3000, `a folder at the session path: M_LOST within 3 s, read ${dir.message.slice(0, 120)} after ${dir.ms} ms`, dir);
      const nt = noTime();
      const z = once(P50, { seed: { spent: 100 }, guard: nt.file }, (s) => f.on(s.stateFile, ["read", "EBUSY", 1]));
      rows.push(cell("no time left (D 0), a read that fails once", [what(z), z.message.slice(0, 70)]));
      assert(z.decision === "deny" && z.message === mStateRead(z.s.stateFile) && z.stateRaw === z.before.state, `no time left: no second try, so M_STATEREAD, read ${z.message.slice(0, 200)} / ${z.stateRaw}`, z);
      drop(f, nt);
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3b-A6-unreadable-budget",
    desc: "B-A6 (R6, H5/H7): a budget file {\"sessionBudget\":50} whose read fails once (EBUSY) and then works is the limit — 40 + 50 is denied with exactly M_LIMIT naming 50 and your session budget; 4 failures then a good read still give 50, 5 failures deny; one that fails every read (EBUSY, EPERM, EACCES) denies a paid call with exactly M_BUDGETREAD, attended and unattended (logged error), nothing counted, and lets a worst-0 call (GET web/monitors) pass silently, in a routine too (no allow); with no time left (D 0) the budget is still read: limit 50, never the automatic cap or 500; a folder at the budget path and bad JSON deny paid calls with the exact settings-file error and nothing counted; no file retains the automatic cap",
    fn() {
      const rows = [];
      const f = faults();
      const lim50 = (r) => r.decision === "deny" && r.message === mLimit({ spent: 40, worst: 50, limit: 50, src: SRC_SESSION, bf: r.bf });
      for (const [label, n] of [["fails once", 1], ["fails 4 times", 4]]) {
        const r = once(P50, { seed: { spent: 40 }, budget: B50 }, (s) => f.on(s.bf, ["read", "EBUSY", n]));
        rows.push(cell(`a budget of 50 that ${label}, 40 + 50`, [what(r), r.message.slice(0, 80)]));
        assert(lim50(r) && r.state.spent === 40, `${label}: the budget of 50 is the limit, exactly M_LIMIT, read ${r.message.slice(0, 260)}`, r);
      }
      const five = once(P50, { seed: { spent: 40 }, budget: B50 }, (s) => f.on(s.bf, ["read", "EBUSY", 5]));
      assert(five.decision === "deny" && five.message === mBudgetRead(five.bf), `fails 5 times: M_BUDGETREAD, read ${five.message.slice(0, 200)}`, five);
      for (const code of ["EBUSY", "EPERM", "EACCES"]) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          const r = once(P1, { seed: { spent: 40 }, budget: B50 }, (s) => f.on(s.bf, ["read", code], env));
          const z = once(MON, { seed: { spent: 40 }, budget: B50 }, (s) => f.on(s.bf, ["read", code], env));
          rows.push(cell(`every budget read ${code}, ${who}`, [`1cr ${what(r)}`, `GET web/monitors ${what(z)}`, `log ${JSON.stringify(r.log.map((l) => `${l.kind}/${l.committed}/${l.cap}`))}`]));
          assert(r.decision === "deny" && r.message === mBudgetRead(r.bf) && r.state.spent === 40, `every read ${code}, ${who}: a paid call gets exactly M_BUDGETREAD, nothing counted, read ${r.message.slice(0, 200)}`, r);
          assert(z.raw === "" && z.state.spent === 40, `every read ${code}, ${who}: a worst-0 call passes silently, read ${what(z)} / ${z.message.slice(0, 120)}`, z);
          if (who === "unattended") assert(r.log.length === 1 && r.log[0].decision === "deny" && r.log[0].kind === "error" && r.log[0].committed === 40 && r.log[0].cap === null, `every read ${code}, unattended: one error line, read ${JSON.stringify(r.log)}`);
        }
      }
      const rp = once(P50, { ...RON, seed: { spent: 40 } }, (s) => f.on(s.bf, ["read", "EBUSY"]));
      const rz = once(MON, { ...RON, seed: { spent: 40 } }, (s) => f.on(s.bf, ["read", "EBUSY"]));
      rows.push(cell("a routine, every budget read EBUSY", [`50cr ${what(rp)}`, `GET web/monitors ${what(rz)}`]));
      assert(rp.decision === "deny" && rp.message === mBudgetRead(rp.bf) && rz.raw === "", `a routine: M_BUDGETREAD for a paid call and a silent pass, no allow, for a worst-0 call, read ${rp.message.slice(0, 120)} / ${rz.raw}`, rp);
      const nt = noTime();
      const t = once(P50, { seed: { spent: 40 }, budget: B50, guard: nt.file });
      rows.push(cell("no time left (D 0), a budget of 50, 40 + 50", [what(t), t.message.slice(0, 80)]));
      assert(lim50(t), `no time left: the budget is still read, M_LIMIT at 50, never the automatic cap or 500, read ${t.message.slice(0, 260)}`, t);
      for (const [label, make] of [["a folder", "DIR"], ["bad JSON", "{bad"], ["no file", null]]) {
        const prep = (s) => { if (make === "DIR") mkdirSync(s.bf); else if (make !== null) s.budget(make); return {}; };
        const r = once(P1, { seed: { spent: 199 } }, prep);
        const over = once(P50, { seed: { spent: 190 } }, prep);
        if (make !== null) assert(r.decision === "deny" && r.message === M_SETTINGS && r.state.spent === 199 &&
          over.decision === "deny" && over.message === M_SETTINGS && over.state.spent === 190,
          `a budget file that is ${label}: unreadable settings deny, nothing counted`, over);
        else assert(r.raw === "" && r.state.spent === 200 && over.message === mLimit({ spent: 190, worst: 50, limit: 200, src: srcAuto(800), bf: over.bf }),
          `a budget file that is ${label}: no file, so the automatic cap of 200, read ${what(r)} / ${over.message.slice(0, 160)}`, over);
      }
      drop(f, nt);
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3g-A4-day-file-dead",
    desc: "3g A4 (D55): the day file is dead. Beside a socialcrawl-day.json valid at today's 4000, one holding {bad, a folder in its place, one whose sessions name this sid on an unseeded session, and a freshly held socialcrawl-day.json.lock, a routine's plain 50cr call (an old routines block in the budget file; CLAUDE_CODE_HOST_SCHEDULED_RUN=1, attended unset and 0) passes silently and counts 50 in under 2 s; a spy on every fs call by path sees none on any socialcrawl-day.json* name; the day file and its lock stay byte-identical and no .tmp is made",
    fn() {
      const rows = [];
      const spy = writeSpy();
      const worlds = [
        ["a day file valid at today's 4000", (s) => s.day({ date: today(), spent: 4000, sessions: { other: 4000 } }), { spent: 0 }],
        ["a day file holding {bad", (s) => s.day("{bad"), { spent: 0 }],
        ["a folder at the day file", (s) => mkdirSync(s.df), { spent: 0 }],
        ["sessions naming this sid, an unseeded session", (s) => s.day({ date: today(), spent: 120, sessions: { [s.sid]: 120, other: 5 } }), null],
        ["a freshly held day lock", (s) => { s.day(DAY300()); writeFileSync(`${s.df}.lock`, ""); }, { spent: 0 }],
      ];
      const dayNames = (s) => readdirSync(s.revxl).filter((n) => n.startsWith("socialcrawl-day.json")).sort()
        .map((n) => `${n}=${JSON.stringify(raw(join(s.revxl, n)))}`).join(",");
      for (const [label, prep, seed] of worlds) {
        for (const [who, env] of [["attended unset", ROUTINE], ["attended 0", RUN]]) {
          const s = open({ budget: ROUTINES_ON, seed });
          prep(s);
          const before = dayNames(s);
          const log = join(s.dir, "spy.log");
          writeFileSync(log, "");
          const r = s.run(P50, { node: ["--import", spy.url], env: { ...env, SPY_DIR: s.revxl, SPY_LOG: log } });
          const ops = spied(log).filter((x) => name(x[1]).startsWith("socialcrawl-day.json") || (x[2] && name(x[2]).startsWith("socialcrawl-day.json")));
          const after = dayNames(s);
          const st = s.state();
          s.cleanup();
          rows.push(cell(`${label}, ${who}`, [what(r), `counted ${st && st.spent}`, `${r.ms} ms`, `day ops ${ops.length}`, `unchanged ${after === before}`]));
          assert(r.raw === "" && r.exit === 0 && st && st.spent === 50 && !st.lost && r.ms < 2000, `${label}, ${who}: a silent pass counted 50 in under 2 s, read ${what(r)} / ${r.message.slice(0, 120)} / ${JSON.stringify(st)} / ${r.ms} ms`, r);
          assert(!ops.length, `${label}, ${who}: no fs call on a socialcrawl-day.json* name, read ${JSON.stringify(ops)}`, r);
          assert(after === before && !after.includes(".tmp"), `${label}, ${who}: the day file and its lock byte-identical, no .tmp, read ${after} vs ${before}`, r);
        }
      }
      drop(spy);
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3b-A9-routine-lost",
    desc: "B-A9 (R9, replayed under D55): in a routine (an old routines block in the budget file), no session file (an unseeded session) and today's day file counting the session above 0 is a fresh session, never lost: a silent pass counted 50, attended and unattended (logged under-cap), the day file byte-identical; so are no entry, an entry of 0, another date's entry and no day file; outside a routine the same files are a fresh session; return deny(M_LOST, \"lost\"); appears exactly once in credit-guard.mjs",
    fn() {
      const rows = [];
      const src = readFileSync(GUARD, "utf8");
      const sites = src.split('return deny(M_LOST, "lost");').length - 1;
      assert(sites === 1, `return deny(M_LOST, "lost"); appears exactly once, read ${sites}`);
      const fresh = (day) => { const s = session({ balance: null }); s.budget(ROUTINES_ON); if (day) s.day(day(s)); return s; };
      for (const [who, env] of [["attended", ROUTINE], ["unattended", RUN]]) {
        const s = fresh((x) => ({ date: today(), spent: 120, sessions: { [x.sid]: 120, other: 5 } }));
        const dayBefore = raw(s.df);
        const r1 = s.run(P50, { env });
        const st = s.state();
        const log = s.logLines();
        const dayAfter = raw(s.df);
        s.cleanup();
        rows.push(cell(`no session file, today's entry 120, ${who}`, [what(r1), `saved ${JSON.stringify(st)}`, `day file unchanged ${dayAfter === dayBefore}`]));
        assert(r1.raw === "" && st && st.spent === 50 && !st.lost && dayAfter === dayBefore, `no session file, an entry of 120, ${who}: a fresh session, a silent pass counted 50, the day file untouched, read ${what(r1)} / ${r1.message.slice(0, 100)} / ${JSON.stringify(st)}`, r1);
        if (who === "unattended") assert(log.length === 1 && log[0].decision === "pass" && log[0].kind === "under-cap", `unattended: one under-cap line, read ${JSON.stringify(log)}`);
      }
      for (const [label, day] of [
        ["no entry", (x) => ({ date: today(), spent: 120, sessions: { other: 120 } })],
        ["an entry of 0", (x) => ({ date: today(), spent: 120, sessions: { [x.sid]: 0, other: 120 } })],
        ["another date's entry of 120", (x) => ({ date: "2000-01-01", spent: 120, sessions: { [x.sid]: 120 } })],
        ["no day file", null],
      ]) {
        const s = fresh(day);
        const d0 = raw(s.df);
        const r = s.run(P50, { env: ROUTINE });
        const st = s.state();
        const d = raw(s.df);
        s.cleanup();
        rows.push(cell(`no session file, ${label}`, [what(r), `committed ${st && st.spent}`, `day unchanged ${d === d0}`]));
        assert(r.raw === "" && st && st.spent === 50 && !st.lost && d === d0, `no session file, ${label}: fresh, a silent pass counted 50, the day file untouched, read ${what(r)} / ${JSON.stringify(st)} / ${d}`, r);
      }
      const n = fresh((x) => ({ date: today(), spent: 120, sessions: { [x.sid]: 120 } }));
      const dn = raw(n.df);
      const rn = n.run(P50);
      const stn = n.state();
      const dn2 = raw(n.df);
      n.cleanup();
      rows.push(cell("not a routine, no session file, today's entry 120", [what(rn), `committed ${stn && stn.spent}`]));
      assert(rn.raw === "" && stn && stn.spent === 50 && !stn.lost && dn2 === dn, `not a routine: a fresh session, a silent pass, the day file untouched, read ${what(rn)} / ${JSON.stringify(stn)}`, rn);
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3b-A11-new-messages",
    desc: "B-A11: each 3b read deny — M_STATEREAD, M_BUDGETREAD — equals its exact string, the same text attended and unattended, ends with the D28 tail, and logs exactly one error line unattended in the 8-field order; the kinds the guard logs, driven through every deny and a pass, are exactly the 6 (D55: no day-limit or day-file)",
    fn() {
      const rows = [];
      const f = faults();
      const seen = new Set();
      for (const [id, cmd, o, prep, want, tail] of [
        ["M_STATEREAD", P50, {}, (s, env) => f.on(s.stateFile, ["read", "EACCES"], env), (s) => mStateRead(s.stateFile), true],
        ["M_BUDGETREAD", P50, { budget: B50 }, (s, env) => f.on(s.bf, ["read", "EBUSY"], env), (s) => mBudgetRead(s.bf), true],
      ]) {
        const s = open({ ...o, seed: { spent: 100 } });
        const base = o.env || {};
        const ra = s.run(cmd, prep(s, base));
        const ru = s.run(cmd, prep(s, { ...base, ...UN }));
        const l = s.logLines();
        const w = want(s);
        s.cleanup();
        for (const x of l) seen.add(x.kind);
        rows.push(cell(id, [`attended ${ra.decision}`, `unattended ${ru.decision}`, `same text ${ra.message === ru.message}`, `log ${JSON.stringify(l.map((x) => x.kind))}`]));
        assert(ra.decision === "deny" && ru.decision === "deny" && ra.message === w && ru.message === w, `${id}: the exact string, attended and unattended, read ${ra.message.slice(0, 220)} / ${ru.message.slice(0, 80)}`, ra);
        assert(tail ? w.endsWith(T) : !w.endsWith(T) && w.endsWith("credits."), `${id}: ${tail ? "ends with T" : "no T, ends at credits."}`);
        assert(l.length === 1 && l[0].decision === "deny" && l[0].kind === "error" && JSON.stringify(Object.keys(l[0])) === JSON.stringify(FIELDS), `${id}: one error line unattended, the 8 fields in order, read ${JSON.stringify(l)}`);
      }
      for (const [cmd, o] of [
        [NP, {}], [P50, { seed: { spent: 0, lost: true } }], [P50, { seed: { spent: 190 } }], [P1, {}],
        [`curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`, { budget: { transcripts: "block" } }],
      ]) {
        const r = once(cmd, { ...o, env: { ...(o.env || {}), ...UN } });
        for (const x of r.log) seen.add(x.kind);
      }
      rows.push(cell("kinds logged, every deny and a pass", [JSON.stringify([...seen].sort())]));
      assert(JSON.stringify([...seen].sort()) === JSON.stringify([...KINDS].sort()), `exactly the 6 kinds, read ${JSON.stringify([...seen].sort())}`);
      drop(f);
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3b-mutants",
    desc: "MUTANTS (B-A4, B-A5, B-A6): each mutant copy of the guard turns a probe red that this build passes — the limit test's cmdWorst > 0 gate dropped, a session file that can't be read saved as lost, and an unreadable budget read as no file",
    fn() {
      const rows = [];
      const f = faults();
      const cases = [
        ["the limit test's gate dropped", [["  if (cmdWorst > 0 && spent + cmdWorst > limit) {\n", "  if (spent + cmdWorst > limit) {\n"]], [
          ["GET web/monitors at 300 of 200", MON, { seed: { spent: 300 } }, null, (r) => r.raw === "" && r.state.spent === 300],
        ]],
        ["a read error saved as lost", [["  if (code) return null;\n", "  if (code) return { spent: 0, lost: true };\n"]], [
          ["every session read EACCES", P50, { seed: { spent: 100 } }, (s) => f.on(s.stateFile, ["read", "EACCES"]), (r) => r.message === mStateRead(r.s.stateFile) && r.stateRaw === r.before.state],
        ]],
        ["an unreadable budget read as no file", [['  if (bfRead.code && bfRead.code !== "ENOENT" && bfRead.code !== "ENOTDIR" && bfRead.code !== "EISDIR" && cmdWorst > 0) {\n', "  if (false) {\n"]], [
          ["a budget of 50 that can't be read, 40 + 50", P50, { seed: { spent: 40 }, budget: B50 }, (s) => f.on(s.bf, ["read", "EBUSY"]), (r) => r.message === mBudgetRead(r.bf)],
        ]],
      ];
      for (const [mname, pairs, probes] of cases) {
        const m = mutant(mname.replace(/[^a-z0-9]+/gi, "-").slice(0, 40), pairs);
        for (const [label, cmd, o, prep, ok] of probes) {
          const fix = once(cmd, o, prep || undefined);
          const mut = once(cmd, { ...o, guard: m.file }, prep || undefined);
          rows.push(cell(`${mname}: ${label}`, [`build ${what(fix)}`, `mutant ${what(mut)} ${mut.message.slice(0, 50)}`]));
          assert(ok(fix), `${mname}, ${label}: the build behaves, read ${what(fix)} / ${fix.message.slice(0, 160)}`, fix);
          assert(!ok(mut), `${mname}, ${label}: the mutant is caught (it behaves wrongly), read ${what(mut)} / ${mut.message.slice(0, 160)}`, mut);
        }
        drop(m);
      }
      drop(f);
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3g-A7-retired-denies-pass",
    desc: "3g A7 (D55): each world the old routine branch denied is now a silent pass counted within the one limit, in a routine (an old routines block in the budget file), attended and unattended: M_DAYLIMIT (today's 4500, 4000 and 3990 of perDay 4000; a BOM'd and a UTF-16LE budget and day file at 3990), M_DAYFILE (bad JSON, [], a string, a negative, fractional or string spent, a folder; two marks, a mark alone, a mark before garbage; UTF-16BE, two UTF-16LE marks, a lone FF FE, FF FE before garbage), M_DAYLOCK (the day lock held), M_DAYWRITE (the day rename throws EPERM; the day temp write fails ENOSPC) and R9's M_LOST (no session file, today's entry 120): each 50cr call passes, counted 50, never lost",
    fn() {
      const rows = [];
      const f = faults();
      const rn = renameFails();
      const BOM = String.fromCharCode(0xfeff);
      const u16le = (t) => Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(t, "utf16le")]);
      const u16be = (t) => Buffer.concat([Buffer.from([0xfe, 0xff]), Buffer.from(t, "utf16le").swap16()]);
      const dayAt = (spent) => JSON.stringify({ date: today(), spent, sessions: { other: spent } });
      const RT = JSON.stringify(ROUTINES_ON);
      const files = (bf, df) => (s) => { writeFileSync(s.bf, bf); writeFileSync(s.df, df); return {}; };
      const day = (v) => (s) => { if (v === "DIR") mkdirSync(s.df); else s.day(v); return {}; };
      // [old deny, label, seed, prep]
      const worlds = [
        ["M_DAYLIMIT", "today's 4500 of perDay 4000 (A13, B-A4)", { spent: 0 }, day({ date: today(), spent: 4500 })],
        ["M_DAYLIMIT", "today's 4000, a remainder of 0 (A13)", { spent: 0 }, day({ date: today(), spent: 4000 })],
        ["M_DAYLIMIT", "today's 3990, 10 short (A13)", { spent: 0 }, day({ date: today(), spent: 3990 })],
        ["M_DAYLIMIT", "a BOM'd routines budget and day file at 3990 (C-A7)", { spent: 0 }, files(BOM + RT, BOM + dayAt(3990))],
        ["M_DAYLIMIT", "a UTF-16LE routines budget and day file at 3990 (D-A8)", { spent: 0 }, files(u16le(RT), u16le(dayAt(3990)))],
        ["M_DAYFILE", "bad JSON (A13)", { spent: 0 }, day("{bad")],
        ["M_DAYFILE", "[] (A13)", { spent: 0 }, day("[]")],
        ["M_DAYFILE", "a string (A13)", { spent: 0 }, day('"x"')],
        ["M_DAYFILE", "a negative spent (A13)", { spent: 0 }, day(JSON.stringify({ date: today(), spent: -1 }))],
        ["M_DAYFILE", "a fractional spent (A13)", { spent: 0 }, day(JSON.stringify({ date: today(), spent: 1.5 }))],
        ["M_DAYFILE", "a string spent (A13)", { spent: 0 }, day(JSON.stringify({ date: today(), spent: "10" }))],
        ["M_DAYFILE", "a folder (A13)", { spent: 0 }, day("DIR")],
        ["M_DAYFILE", "two marks (C-A7)", { spent: 0 }, day(BOM + BOM + dayAt(3900))],
        ["M_DAYFILE", "a mark alone (C-A7)", { spent: 0 }, day(BOM)],
        ["M_DAYFILE", "a mark before garbage (C-A7)", { spent: 0 }, day(BOM + "{bad")],
        ["M_DAYFILE", "UTF-16BE (D-A8)", { spent: 0 }, files(RT, u16be(dayAt(3900)))],
        ["M_DAYFILE", "two UTF-16LE marks (D-A8)", { spent: 0 }, files(RT, Buffer.concat([Buffer.from([0xff, 0xfe]), u16le(dayAt(3900))]))],
        ["M_DAYFILE", "a lone FF FE (D-A8)", { spent: 0 }, files(RT, Buffer.from([0xff, 0xfe]))],
        ["M_DAYFILE", "FF FE before garbage (D-A8)", { spent: 0 }, files(RT, Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from("{bad")]))],
        ["M_DAYLOCK", "the day lock held (B-A7, B-A11)", { spent: 0 }, (s) => { s.day(DAY300()); writeFileSync(`${s.df}.lock`, ""); return {}; }],
        ["M_DAYWRITE", "the day rename throws EPERM (B-A1, B-A2)", { spent: 0 }, (s) => { s.day(DAY300()); return { node: ["--import", rn.url], env: { RENAME_FAIL: s.df } }; }],
        ["M_DAYWRITE", "the day temp write fails ENOSPC (B-A1, B-A2)", { spent: 0 }, (s) => { s.day(DAY300()); return f.on(`${s.df}.${s.sid}.tmp`, ["write"]); }],
        ["M_LOST (R9)", "no session file, today's entry 120 (B-A9)", null, (s) => { s.day({ date: today(), spent: 120, sessions: { [s.sid]: 120, other: 5 } }); return {}; }],
      ];
      for (const [old, label, seed, prep] of worlds) {
        for (const [who, env] of [["attended", ROUTINE], ["unattended", RUN]]) {
          const r = once(P50, { budget: ROUTINES_ON, seed, env }, (s) => {
            const p = prep(s) || {};
            return { node: p.node, env: { ...env, ...(p.env || {}) } };
          });
          rows.push(cell(`was ${old}: ${label}, ${who}`.slice(0, 54), [what(r), `counted ${r.state && r.state.spent}`]));
          assert(r.raw === "" && r.exit === 0 && r.state && r.state.spent === 50 && !r.state.lost,
            `was ${old}, ${label}, ${who}: a silent pass counted 50, read ${what(r)} / ${r.message.slice(0, 160)} / ${r.stateRaw}`, r);
          if (who === "unattended") assert(r.log.length === 1 && r.log[0].decision === "pass" && r.log[0].kind === "under-cap", `was ${old}, ${label}, unattended: one under-cap line, read ${JSON.stringify(r.log)}`);
        }
      }
      drop(f, rn);
      console.log(rows.join("\n"));
    },
  },
];
