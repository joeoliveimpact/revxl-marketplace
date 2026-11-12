/*
 * Phase 3c (0.4.0): Claude never changes the guard's own files (the tamper rule), and one leading byte
 * order mark no longer voids the budget, day or session file (carried from the 3b check, HUNT 1). One
 * fixture per item of List A in "Phase 3c Checker Fixtures - Both Lists - 10.10.26.md", C-A1 to C-A8
 * (C-A9 is the whole suite and its instruments); the C-A8 mutants are in P3c-mutants. Each fixture here
 * was run red against slice 3b (63e7ca9) before it was run green. Messages are checked whole, by equality.
 *
 * Synchronous; every guard run in its own temp SC_REVXL_HOME and HOME (lib.mjs session()). A real-shaped
 * C:/Users/x/.claude/revxl path is only text in a tool call (the guard never opens it), and no command here
 * is ever run by a shell: each is only the text the guard reads. Zero credits, zero network. Backslashes,
 * the byte order mark and newlines are built with String.fromCharCode, never typed as escapes.
 */
import { copyFileSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import {
  session, V1, GUARD, COSTS, M_NOTPLAIN, M_NOTBASH, M_LOST, mLimit, ROUTINE, ROUTINES_ON,
  SRC_SESSION, srcAuto, today, assert, T,
} from "../lib.mjs";

const UN = { CLAUDE_CODE_SESSION_ATTENDED: "0" };
const M_SETTINGS = "SocialCrawl call not run: your SocialCrawl settings file can't be read, so this session's credit limit can't be checked. Re-save your limit in SocialCrawl → Settings to fix it." + T;
const B = String.fromCharCode(92);                        // one backslash
const BOM = String.fromCharCode(0xfeff);                  // the byte order mark PowerShell 5.1 writes
const fwd = (p) => p.split(B).join("/");                  // a Windows path with forward slashes
const at = (dir, parts, sep = B) => [dir, ...parts].join(sep);
const HOOKS_JSON = resolve(dirname(GUARD), "hooks.json");
const SKILL_MD = resolve(dirname(GUARD), "..", "skills", "socialcrawl", "SKILL.md");
const URL50 = `${V1}prism/leads?query=x`;
const P50 = `curl -s "${URL50}"`;                         // plain, flat 50
const MATCHER = "Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit";
const TOOLS = ["Write", "Edit", "MultiEdit", "NotebookEdit"];
const SHELLS = ["Bash", "PowerShell"];
const REAL = ["C:", "Users", "x", ".claude", "revxl"].join(B);   // a real-shaped default <revxl>, never opened
/** K1-K5: each guarded file's place below <revxl> and its NAME. */
const K = [
  [["socialcrawl-budget.json"], "the budget file socialcrawl-budget.json"],
  [["socialcrawl-day.json"], "the old routine day file socialcrawl-day.json"],
  [["credit-guard-unattended.jsonl"], "the unattended log credit-guard-unattended.jsonl"],
  [["socialcrawl-calls.jsonl"], "the call record socialcrawl-calls.jsonl"],
  [["sessions", "socialcrawl-abc.json"], "a session file in sessions/"],
];
/** M_TAMPER, whole (no T: nothing about SocialCrawl was sent or counted). */
const mTamper = (what, k) =>
  `SocialCrawl guard file left alone: this ${what} names ${K[k][1]}, which holds the person's SocialCrawl budget or spend ` +
  `record. Claude is not to change it (the guard refuses the plain ways; a glob, a link to the folder, an MCP tool or a script can still get past it); the person sets the limit in SocialCrawl → Settings. To look at it, use the Read tool.`;
/** A tamper deny's whole stdout, as done() writes it. */
const denyOut = (m) =>
  JSON.stringify({ hookSpecificOutput: { permissionDecision: "deny", hookEventName: "PreToolUse", permissionDecisionReason: m }, systemMessage: m });
/** A write-type tool call as Claude Code sends it (NotebookEdit names notebook_path), with `more` fields added. */
const edit = (tool, path, more = {}) => ({
  tool_name: tool,
  tool_input: {
    ...(tool === "NotebookEdit" ? { notebook_path: path, new_source: "x" }
      : tool === "Edit" ? { file_path: path, old_string: "a", new_string: "b" }
      : tool === "MultiEdit" ? { file_path: path, edits: [{ old_string: "a", new_string: "b" }] }
      : { file_path: path, content: "x" }),
    ...more,
  },
});
const verdict = (r) => r.decision || (r.raw ? "?" : "pass");
const cell = (label, parts) => `    ${label.padEnd(62)} ${parts.join(" | ")}`;
const raw = (p) => { try { return readFileSync(p, "utf8"); } catch { return null; } };
/** Every file under a folder with its content, as one string: equal before and after = nothing made, changed or removed. `skip` leaves out files of that name. */
function tree(dir, skip) {
  const out = [];
  const walk = (d) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      if (e.name === skip) continue;
      const p = join(d, e.name);
      if (e.isDirectory()) { out.push(`${p}/`); walk(p); } else out.push(`${p}=${readFileSync(p, "utf8")}`);
    }
  };
  walk(dir);
  return out.sort().join(String.fromCharCode(10));
}
/**
 * One guard run in a fresh session (spent 0 and a balance of 800 seeded). `make(s)` returns [command, options]:
 * `prep(s)` seeds files first, `extra` replaces envelope fields (tool_name, tool_input), `env` and `node` as
 * lib.mjs run(). The result carries the session's state, its log, its day file and `same`: nothing under the
 * session's temp folder changed (`sameButCalls`: nothing but the 3d call record).
 */
function once(make, guard) {
  const s = session();
  const [cmd, o = {}] = make(s);
  if (o.prep) o.prep(s);
  const before = tree(s.dir);
  const r = s.run(cmd, { extra: o.extra, env: o.env, node: o.node, guard });
  Object.assign(r, { s, same: tree(s.dir) === before, sameButCalls: tree(s.dir, "socialcrawl-calls.jsonl") === before, state: s.state(), stateRaw: s.stateRaw(), log: s.logLines(), day: raw(s.df) });
  s.cleanup();
  return r;
}
/** A preload that appends [op, path] to SPY_LOG for every fs call the guard makes on a path, any path. */
function fsSpy() {
  const d = mkdtempSync(join(tmpdir(), "sc-p3c-spy-"));
  const f = join(d, "fs-spy.mjs");
  writeFileSync(f,
    `import { createRequire, syncBuiltinESMExports } from "node:module";\n` +
    `const fs = createRequire(import.meta.url)("node:fs");\n` +
    `const append = fs.appendFileSync;\n` +
    `let busy = false;\n` +
    `for (const op of ["readFileSync", "writeFileSync", "appendFileSync", "mkdirSync", "renameSync", "unlinkSync", "statSync", "existsSync", "openSync", "readdirSync", "lstatSync", "rmSync"]) {\n` +
    `  const real = fs[op];\n` +
    `  fs[op] = (p, ...a) => {\n` +
    `    if (!busy && typeof p === "string") { busy = true; try { append(process.env.SPY_LOG, JSON.stringify([op, p]) + String.fromCharCode(10)); } finally { busy = false; } }\n` +
    `    return real(p, ...a);\n` +
    `  };\n` +
    `}\n` +
    `syncBuiltinESMExports();\n`);
  return { url: pathToFileURL(f).href, dir: d, log: (i) => join(d, `run-${i}.log`) };
}
/** A copy of the guard (costs.json beside it) with each [anchor, replacement] applied; each anchor must occur exactly once. */
function mutant(id, pairs) {
  let src = readFileSync(GUARD, "utf8");
  for (const [anchor, repl] of pairs) {
    assert(src.split(anchor).length === 2, `mutant ${id}: its anchor must occur exactly once in credit-guard.mjs, read ${src.split(anchor).length - 1} x ${JSON.stringify(anchor).slice(0, 100)}`);
    src = src.replace(anchor, () => repl);
  }
  const d = mkdtempSync(join(tmpdir(), `sc-p3c-mut-${id}-`));
  writeFileSync(join(d, "credit-guard.mjs"), src);
  copyFileSync(COSTS, join(d, "costs.json"));
  return { file: join(d, "credit-guard.mjs"), dir: d };
}
const SUGGEST = [{ hooks: [{ type: "command", command: 'node "${CLAUDE_PLUGIN_ROOT}/hooks/research-suggest.mjs"', timeout: 10 }] }];
/** What C-A5 finds wrong with hooks.json; [] for the three guard registrations and unchanged suggester. */
function hooksProblems(text) {
  const bad = [];
  const cfg = JSON.parse(text);
  const entries = [];
  for (const [event, list] of Object.entries(cfg.hooks || {})) for (const m of list) for (const h of m.hooks || []) {
    if (String(h.command || "").includes("credit-guard.mjs")) entries.push({ event, matcher: m.matcher, ...h });
  }
  if (entries.length !== 3) bad.push(`${entries.length} credit-guard entries`);
  const command = 'node "${CLAUDE_PLUGIN_ROOT}/hooks/' + 'credit' + '-guard.mjs"';
  for (const [event, matcher, timeout] of [["PreToolUse", MATCHER, 10], ["PostToolUse", "Bash", 5], ["PostToolBatch", undefined, 5]]) {
    const matches = entries.filter(e => e.event === event);
    const g = matches[0] || {};
    if (matches.length !== 1 || g.matcher !== matcher || g.timeout !== timeout || g.type !== "command" || g.command !== command)
      bad.push(`the ${event} entry is ${JSON.stringify(g)}`);
  }
  if (JSON.stringify(cfg.hooks && cfg.hooks.UserPromptSubmit) !== JSON.stringify(SUGGEST)) bad.push("research-suggest changed");
  const d = String(cfg.description || "");
  if (/(?:^|[^a-z])(?:ask|asks|asked)(?:[^a-z]|$)/i.test(d)) bad.push("the description says ask");
  for (const w of [...TOOLS, "socialcrawl-budget.json", "socialcrawl-day.json", "credit-guard-unattended.jsonl", "socialcrawl-calls.jsonl", "sessions/", "budget-write"]) {
    if (!d.includes(w)) bad.push(`the description doesn't name ${w}`);
  }
  return bad;
}

export default [
  {
    id: "P3c-A1-write-tools-guarded-files",
    desc: "C-A1: a Write, Edit, MultiEdit or NotebookEdit (notebook_path) of each guarded file — K1 the budget file, K2 the routine day file, K3 the unattended log, K4 the call record, K5 a session file in sessions/ — under a real-shaped C:/Users/x/.claude/revxl written with backslashes and with forward slashes, under an upper-case REVXL folder (an upper-case file name too), and under a temp SC_REVXL_HOME not named revxl (rule ii), is denied with exactly M_TAMPER, WHAT edit and that file's NAME; so are a lock, temporary, per-session temporary and rotated name of K1-K4 and a session file's .lock",
    fn() {
      const rows = [];
      const shapes = [
        ["real-shaped, backslashes", () => ({ dir: REAL, sep: B })],
        ["real-shaped, forward slashes", () => ({ dir: fwd(REAL), sep: "/" })],
        ["an upper-case REVXL folder and file name", () => ({ dir: REAL.replace("revxl", "REVXL"), sep: B, upper: true })],
        ["a temp SC_REVXL_HOME not named revxl (rule ii)", (s) => ({ dir: join(s.dir, "home"), sep: B, env: { SC_REVXL_HOME: join(s.dir, "home") } })],
      ];
      for (let k = 0; k < K.length; k++) {
        for (const [label, shape] of shapes) {
          const seen = [];
          for (const tool of TOOLS) {
            const r = once((s) => {
              const sh = shape(s);
              return ["", { extra: edit(tool, at(sh.dir, sh.upper ? K[k][0].map((x) => x.toUpperCase()) : K[k][0], sh.sep)), env: sh.env }];
            });
            seen.push(`${tool} ${verdict(r)}`);
            assert(r.raw === denyOut(mTamper("edit", k)) && r.exit === 0, `K${k + 1}, ${label}, ${tool}: exactly M_TAMPER (edit, ${K[k][1]}), read ${verdict(r)} / ${r.message.slice(0, 200)}`, r);
          }
          rows.push(cell(`K${k + 1}, ${label}`, seen));
        }
      }
      for (const [k, parts] of [[0, ["socialcrawl-budget.json.lock"]], [0, ["socialcrawl-budget.json.tmp"]], [1, ["socialcrawl-day.json.scgt1.tmp"]],
        [2, ["credit-guard-unattended.jsonl.1"]], [3, ["socialcrawl-calls.jsonl.lock"]], [4, ["sessions", "socialcrawl-abc.json.lock"]]]) {
        const r = once(() => ["", { extra: edit("Write", at(REAL, parts)) }]);
        rows.push(cell(parts.join("/"), [verdict(r)]));
        assert(r.raw === denyOut(mTamper("edit", k)), `${parts.join("/")}: exactly M_TAMPER (${K[k][1]}), read ${verdict(r)} / ${r.message.slice(0, 160)}`, r);
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3c-A2-shell-commands-guarded-files",
    desc: "C-A2: through Bash, through PowerShell and with no tool_name (read as Bash), a command holding a revxl location and a guarded name is denied with exactly M_TAMPER, WHAT command, NAME the first of K1-K5 it names, with nothing in the session folder changed: an echo into ~/.claude/revxl/socialcrawl-budget.json, Set-Content of $env:USERPROFILE/.claude/revxl/socialcrawl-day.json (backslashes), cat of the unattended log, rm of the call record, rm of a session file and Remove-Item of one (backslashes), the same in upper case, a copy naming the day file then the budget file (the budget file's NAME), the temp SC_REVXL_HOME's own path with either slash (rule ii), and two naming socialcrawl.dev too: a plain curl -o into the budget file and an echo of a SocialCrawl URL into it (the tamper deny, never M_NOTPLAIN, M_NOTBASH or a count)",
    fn() {
      const rows = [];
      const ps = (...parts) => at("$env:USERPROFILE", [".claude", "revxl", ...parts]);
      const home = (s) => join(s.dir, "home");
      const cases = [
        [0, "an echo into the budget file", () => `echo '{"sessionBudget":20000}' > ~/.claude/revxl/socialcrawl-budget.json`],
        [1, "Set-Content of the day file", () => `Set-Content ${ps("socialcrawl-day.json")} x`],
        [2, "cat of the unattended log", () => "cat ~/.claude/revxl/credit-guard-unattended.jsonl"],
        [3, "rm of the call record", () => "rm ~/.claude/revxl/socialcrawl-calls.jsonl"],
        [4, "rm of a session file", () => "rm ~/.claude/revxl/sessions/socialcrawl-abc.json"],
        [4, "Remove-Item of a session file (backslashes)", () => `Remove-Item ${ps("sessions", "socialcrawl-abc.json")}`],
        [0, "upper case", () => "CAT ~/.CLAUDE/REVXL/SOCIALCRAWL-BUDGET.JSON"],
        [0, "the day file, then the budget file", () => "cp ~/.claude/revxl/socialcrawl-day.json ~/.claude/revxl/socialcrawl-budget.json"],
        [0, "rule ii: <revxl> with backslashes", (s) => `cat ${at(home(s), ["socialcrawl-budget.json"])}`, (s) => ({ SC_REVXL_HOME: home(s) })],
        [1, "rule ii: <revxl> with forward slashes", (s) => `cat ${fwd(at(home(s), ["socialcrawl-day.json"]))}`, (s) => ({ SC_REVXL_HOME: home(s) })],
        [0, "a plain curl -o into the budget file", () => `${P50} -o ~/.claude/revxl/socialcrawl-budget.json`],
        [0, "an echo of a SocialCrawl URL into the budget file", () => `echo '${URL50}' >> ~/.claude/revxl/socialcrawl-budget.json`],
      ];
      for (const [k, label, cmd, env] of cases) {
        const seen = [];
        for (const tool of [...SHELLS, undefined]) {
          const r = once((s) => [cmd(s), { extra: { tool_name: tool }, env: env && env(s) }]);
          seen.push(`${tool || "no tool_name"} ${verdict(r)}`);
          assert(r.raw === denyOut(mTamper("command", k)) && r.same && r.exit === 0,
            `${label}, ${tool || "no tool_name"}: exactly M_TAMPER (command, ${K[k][1]}), nothing changed, read ${verdict(r)} / ${r.message.slice(0, 200)} / unchanged ${r.same}`, r);
        }
        rows.push(cell(label, seen));
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3c-A3-ordinary-work-passes",
    desc: "C-A3: ordinary work passes untouched (no output, exit 0, nothing in the session folder changed), beside near twins that are denied: a Write of C:/proj/socialcrawl-budget.json (no revxl; twin in C:/proj/revxl); Writes in <revxl> of jev-ask.json, jev-candidates.jsonl, entities.jsonl, teach-level, tools.json, voc-contract.md and credit-guard-unattended.seen (twin: the unattended log); of socialcrawl-report.json in <revxl> and in a brand folder (a session file needs sessions; twin in <revxl>/sessions); of examplebrand/voc/x.md; an Edit of this plugin's skills/socialcrawl/SKILL.md whose new text names socialcrawl.dev, ~/.claude/revxl and socialcrawl-budget.json; a Read of the budget file; through Bash and PowerShell, git grep -n socialcrawl-day.json (no revxl; twin with -- ~/.claude/revxl), node tools/socialcrawl/lint_curated.mjs, ls ~/.claude/revxl (no name; twin: ls of the budget file), cat of <revxl>/socialcrawl-report.json (twin in sessions/) and of credit-guard-unattended.seen (twin: the log)",
    fn() {
      const rows = [];
      const pass = (label, make) => {
        const r = once(make);
        rows.push(cell(label, [verdict(r)]));
        assert(r.raw === "" && r.exit === 0 && r.same, `${label}: passes untouched, read ${verdict(r)} / ${r.message.slice(0, 160)} / unchanged ${r.same}`, r);
      };
      const twin = (label, make, w, k) => {
        const r = once(make);
        rows.push(cell(`  twin: ${label}`, [verdict(r)]));
        assert(r.raw === denyOut(mTamper(w, k)), `twin ${label}: exactly M_TAMPER (${w}, ${K[k][1]}), read ${verdict(r)} / ${r.message.slice(0, 160)}`, r);
      };
      const W = (p) => () => ["", { extra: edit("Write", p) }];
      pass("Write C:/proj/socialcrawl-budget.json", W(at("C:", ["proj", "socialcrawl-budget.json"])));
      twin("Write C:/proj/revxl/socialcrawl-budget.json", W(at("C:", ["proj", "revxl", "socialcrawl-budget.json"])), "edit", 0);
      for (const n of ["jev-ask.json", "jev-candidates.jsonl", "entities.jsonl", "teach-level", "tools.json", "voc-contract.md", "credit-guard-unattended.seen"]) {
        pass(`Write <revxl>/${n}`, W(at(REAL, [n])));
      }
      twin("Write <revxl>/credit-guard-unattended.jsonl", W(at(REAL, ["credit-guard-unattended.jsonl"])), "edit", 2);
      pass("Write <revxl>/socialcrawl-report.json", W(at(REAL, ["socialcrawl-report.json"])));
      pass("Write <revxl>/examplebrand/socialcrawl-report.json", W(at(REAL, ["examplebrand", "socialcrawl-report.json"])));
      twin("Write <revxl>/sessions/socialcrawl-report.json", W(at(REAL, ["sessions", "socialcrawl-report.json"])), "edit", 4);
      pass("Write <revxl>/examplebrand/voc/x.md", W(at(REAL, ["examplebrand", "voc", "x.md"])));
      pass("Edit skills/socialcrawl/SKILL.md naming socialcrawl.dev and the budget file", () => ["", {
        extra: { tool_name: "Edit", tool_input: { file_path: SKILL_MD, old_string: "a", new_string: `Set it in ~/.claude/revxl/socialcrawl-budget.json; see ${V1}credits/balance` } },
      }]);
      pass("Read <revxl>/socialcrawl-budget.json", () => ["", { extra: { tool_name: "Read", tool_input: { file_path: at(REAL, ["socialcrawl-budget.json"]) } } }]);
      for (const tool of SHELLS) {
        const S = (c) => () => [c, { extra: { tool_name: tool } }];
        pass(`${tool}: git grep -n socialcrawl-day.json`, S("git grep -n socialcrawl-day.json"));
        twin(`${tool}: git grep -n socialcrawl-day.json -- ~/.claude/revxl`, S("git grep -n socialcrawl-day.json -- ~/.claude/revxl"), "command", 1);
        pass(`${tool}: node tools/socialcrawl/lint_curated.mjs`, S("node tools/socialcrawl/lint_curated.mjs"));
        pass(`${tool}: ls ~/.claude/revxl`, S("ls ~/.claude/revxl"));
        twin(`${tool}: ls ~/.claude/revxl/socialcrawl-budget.json`, S("ls ~/.claude/revxl/socialcrawl-budget.json"), "command", 0);
        pass(`${tool}: cat ~/.claude/revxl/socialcrawl-report.json`, S("cat ~/.claude/revxl/socialcrawl-report.json"));
        twin(`${tool}: cat ~/.claude/revxl/sessions/socialcrawl-report.json`, S("cat ~/.claude/revxl/sessions/socialcrawl-report.json"), "command", 4);
        pass(`${tool}: cat ~/.claude/revxl/credit-guard-unattended.seen`, S("cat ~/.claude/revxl/credit-guard-unattended.seen"));
        twin(`${tool}: cat ~/.claude/revxl/credit-guard-unattended.jsonl`, S("cat ~/.claude/revxl/credit-guard-unattended.jsonl"), "command", 2);
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3c-A4-no-io-no-log",
    desc: "C-A4: with a session file at 100, a routines budget and today's day file in place, a spy on every fs call by path sees none, the session folder is left byte-identical (no lock, no log) and the unattended log gets no line, for: a Write, Edit, MultiEdit and NotebookEdit of the session's own budget file (exactly the tamper deny) and of an ordinary file (no output), each also carrying a stray command field with a plain paid curl and content naming socialcrawl.dev; and a Bash and PowerShell tamper deny of a cat of the budget file and of a plain curl -o into it; each attended, unattended and in a routine (unattended), the deny the same text in all three, so the 7 log kinds are untouched",
    fn() {
      const rows = [];
      const spy = fsSpy();
      let n = 0;
      const prep = (s) => { s.seed({ spent: 100 }); s.budget(ROUTINES_ON); s.day({ date: today(), spent: 300, sessions: { other: 300 } }); };
      const cases = [];
      for (const tool of TOOLS) {
        cases.push([`${tool} of the budget file`, (s) => edit(tool, s.bf, { command: P50, content: `see ${URL50}` }), "edit"]);
        cases.push([`${tool} of an ordinary file`, (s) => edit(tool, join(s.dir, "notes.md"), { command: P50, content: `see ${URL50}` }), null]);
      }
      for (const tool of SHELLS) {
        cases.push([`${tool}: cat of the budget file`, (s) => ({ tool_name: tool, tool_input: { command: `cat ${s.bf}` } }), "command"]);
        cases.push([`${tool}: a plain curl -o into the budget file`, (s) => ({ tool_name: tool, tool_input: { command: `${P50} -o ${fwd(s.bf)}` } }), "command"]);
      }
      for (const [who, env] of [["attended", {}], ["unattended", UN], ["a routine, unattended", { ...ROUTINE, ...UN }]]) {
        for (const [label, extra, w] of cases) {
          const log = spy.log(++n);
          const r = once((s) => ["", { prep, extra: extra(s), env: { ...env, SPY_LOG: log }, node: ["--import", spy.url] }]);
          const calls = (raw(log) || "").split(String.fromCharCode(10)).filter(Boolean);
          rows.push(cell(`${label}, ${who}`, [verdict(r), `fs calls ${calls.length}`, `unchanged ${r.same}`, `log lines ${r.log.length}`]));
          assert(w ? r.raw === denyOut(mTamper(w, 0)) : r.raw === "", `${label}, ${who}: ${w ? "exactly the tamper deny" : "no output"}, read ${r.raw.slice(0, 200)}`, r);
          assert(!calls.length && r.same && !r.log.length && r.exit === 0,
            `${label}, ${who}: no fs call, nothing changed, nothing logged, read ${JSON.stringify(calls.slice(0, 4))} / unchanged ${r.same} / ${JSON.stringify(r.log)}`, r);
        }
      }
      rmSync(spy.dir, { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3c-A5-hooks-json",
    desc: "C-A5: hooks.json holds three guard entries: PreToolUse with the exact write/shell matcher and timeout 10, PostToolUse/Bash and PostToolBatch/no matcher with timeout 5, all with the same command; suggester and guarded-file description checks remain unchanged",
    fn() {
      const bad = hooksProblems(readFileSync(HOOKS_JSON, "utf8"));
      assert(!bad.length, `hooks.json: ${bad.join("; ")}`);
    },
  },
  {
    id: "P3c-A6-other-commands-unchanged",
    desc: "C-A6: a command holding a guarded name but no revxl location, or a revxl location but no guarded name, takes the 3b flow exactly: through Bash a plain curl -o ./socialcrawl-budget.json or -o ~/.claude/revxl/out.json passes silently and counts 50, attended and unattended (one under-cap line); at 190 committed it is exactly M_LIMIT naming 190; an echo of a SocialCrawl URL into socialcrawl-day.json is exactly M_NOTPLAIN, nothing changed; through PowerShell the plain curl -o ~/.claude/revxl/out.json is exactly M_NOTBASH; in a routine (an old routines block in the budget file) a plain curl -o ./socialcrawl-calls.jsonl is a silent pass counted at 50, and no day file is made (D55); and the same plain curl -o ~/.claude/revxl/socialcrawl-budget.json is the tamper deny, nothing changed",
    fn() {
      const rows = [];
      const quiet = (label, cmd, env, wantLog) => {
        const r = once(() => [cmd, { env }]);
        rows.push(cell(label, [verdict(r), `counted ${r.state && r.state.spent}`, `log ${JSON.stringify(r.log.map((l) => l.kind))}`]));
        assert(r.raw === "" && r.state && r.state.spent === 50 && r.log.length === wantLog && (!wantLog || r.log[0].kind === "under-cap"),
          `${label}: a silent pass counted at 50, read ${verdict(r)} / ${r.stateRaw} / ${JSON.stringify(r.log)}`, r);
      };
      quiet("Bash: curl -o ./socialcrawl-budget.json", `${P50} -o ./socialcrawl-budget.json`, {}, 0);
      quiet("Bash: curl -o ./socialcrawl-budget.json, unattended", `${P50} -o ./socialcrawl-budget.json`, UN, 1);
      quiet("Bash: curl -o ~/.claude/revxl/out.json", `${P50} -o ~/.claude/revxl/out.json`, {}, 0);
      const over = once(() => [`${P50} -o ./socialcrawl-budget.json`, { prep: (s) => s.seed({ spent: 190 }) }]);
      rows.push(cell("Bash: the same at 190 committed", [verdict(over)]));
      assert(over.message === mLimit({ spent: 190, worst: 50, limit: 200, src: srcAuto(800), bf: over.bf }) && over.state.spent === 190, `at 190: exactly M_LIMIT, read ${over.message.slice(0, 200)}`, over);
      const np = once(() => [`echo '${URL50}' > socialcrawl-day.json`, {}]);
      rows.push(cell("Bash: an echo of a SocialCrawl URL into socialcrawl-day.json", [verdict(np)]));
      assert(np.decision === "deny" && np.message === M_NOTPLAIN && np.same, `the echo: exactly M_NOTPLAIN, nothing changed, read ${np.message.slice(0, 160)}`, np);
      const pw = once(() => [`${P50} -o ~/.claude/revxl/out.json`, { extra: { tool_name: "PowerShell" } }]);
      rows.push(cell("PowerShell: curl -o ~/.claude/revxl/out.json", [verdict(pw)]));
      assert(pw.decision === "deny" && pw.message === M_NOTBASH && pw.same, `PowerShell: exactly M_NOTBASH, nothing changed, read ${pw.message.slice(0, 160)}`, pw);
      const rt = once((s) => [`${P50} -o ./socialcrawl-calls.jsonl`, { prep: (x) => x.budget(ROUTINES_ON), env: ROUTINE }]);
      rows.push(cell("a routine: curl -o ./socialcrawl-calls.jsonl", [verdict(rt), `day ${rt.day}`]));
      assert(rt.raw === "" && rt.state && rt.state.spent === 50 && rt.day === null, `a routine: a silent pass counted at 50, no day file, read ${rt.raw} / ${rt.stateRaw} / ${rt.day}`, rt);
      const t = once(() => [`${P50} -o ~/.claude/revxl/socialcrawl-budget.json`, {}]);
      rows.push(cell("twin: Bash curl -o ~/.claude/revxl/socialcrawl-budget.json", [verdict(t)]));
      assert(t.raw === denyOut(mTamper("command", 0)) && t.same, `the twin: the tamper deny, nothing changed, read ${t.message.slice(0, 160)}`, t);
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3c-A7-bom",
    desc: "C-A7 (3b HUNT 1): one leading byte order mark is dropped before the budget and session files are parsed: a BOM'd {sessionBudget: 50} is the limit (40 + 50 is exactly M_LIMIT naming 50 and your session budget; 0 + 50 passes and counts 50); a BOM'd day file is never read (D55): a routine with a BOM'd routines budget and a BOM'd day file of today at 3990 passes 50 silently, counted 50, the day file byte-identical; a BOM'd session file at 100 reads as 100 (50 more passes and counts 150; at 190 a 50cr call is exactly M_LIMIT naming 190), never lost; two marks, a mark alone and a mark before garbage give a settings-file error for the budget and a lost total for the session",
    fn() {
      const rows = [];
      const stateBom = (s, spent, marks = BOM) => writeFileSync(s.stateFile, marks + JSON.stringify({ balance: 800, spent }));
      const routine = (budgetText, dayText) => (s) => [P50, { prep: (x) => { x.budget(budgetText); x.day(dayText); }, env: ROUTINE }];
      const b40 = once(() => [P50, { prep: (s) => { s.seed({ spent: 40 }); s.budget(BOM + '{"sessionBudget":50}'); } }]);
      const b0 = once(() => [P50, { prep: (s) => s.budget(BOM + '{"sessionBudget":50}') }]);
      rows.push(cell("a BOM'd budget of 50: 40 + 50, then 0 + 50", [verdict(b40), `${verdict(b0)} counted ${b0.state.spent}`]));
      assert(b40.decision === "deny" && b40.message === mLimit({ spent: 40, worst: 50, limit: 50, src: SRC_SESSION, bf: b40.bf }), `a BOM'd budget, 40 + 50: exactly M_LIMIT at 50, read ${b40.message.slice(0, 220)}`, b40);
      assert(b0.raw === "" && b0.state.spent === 50, `a BOM'd budget, 0 + 50: passes, counted 50, read ${verdict(b0)} / ${b0.stateRaw}`, b0);
      const dayAt = (spent) => JSON.stringify({ date: today(), spent, sessions: { other: spent } });
      const nr = once(routine(BOM + JSON.stringify(ROUTINES_ON), BOM + dayAt(3990)));
      rows.push(cell("a BOM'd routines budget and day file at 3990: 0 + 50", [`${verdict(nr)} counted ${nr.state && nr.state.spent}`, `day ${JSON.stringify(nr.day)}`]));
      assert(nr.raw === "" && nr.state && nr.state.spent === 50 && nr.day === BOM + dayAt(3990), `a BOM'd day file is never read: a silent pass counted 50, the day file byte-identical, read ${verdict(nr)} / ${nr.stateRaw} / ${JSON.stringify(nr.day)}`, nr);
      const s100 = once(() => [P50, { prep: (s) => stateBom(s, 100) }]);
      const s190 = once(() => [P50, { prep: (s) => stateBom(s, 190) }]);
      rows.push(cell("a BOM'd session file at 100, then at 190", [`${verdict(s100)} saved ${s100.stateRaw}`, verdict(s190)]));
      assert(s100.raw === "" && s100.state.spent === 150 && !s100.state.lost, `a BOM'd session file at 100: passes, counted 150, never lost, read ${verdict(s100)} / ${s100.stateRaw}`, s100);
      assert(s190.decision === "deny" && s190.message === mLimit({ spent: 190, worst: 50, limit: 200, src: srcAuto(800), bf: s190.bf }), `a BOM'd session file at 190: exactly M_LIMIT naming 190, read ${s190.message.slice(0, 220)}`, s190);
      // Garbled budget files fail closed; garbled session files still lose the total.
      for (const [label, marks, body] of [["two marks", BOM + BOM, null], ["a mark alone", BOM, ""], ["a mark before garbage", BOM, "{bad"]]) {
        const bb = once(() => [P50, { prep: (s) => { s.seed({ spent: 40 }); s.budget(marks + (body === null ? '{"sessionBudget":50}' : body)); } }]);
        const ss = once(() => [P50, { prep: (s) => writeFileSync(s.stateFile, marks + (body === null ? JSON.stringify({ balance: 800, spent: 100 }) : body)) }]);
        rows.push(cell(label, [`budget: ${verdict(bb)} counted ${bb.state.spent}`, `session: ${verdict(ss)}`]));
        assert(bb.decision === "deny" && bb.message === M_SETTINGS && bb.state.spent === 40, `${label}, the budget file: unreadable settings deny, nothing counted, read ${verdict(bb)} / ${bb.message.slice(0, 160)}`, bb);
        assert(ss.decision === "deny" && ss.message === M_LOST && ss.state && ss.state.lost === true, `${label}, the session file: M_LOST, saved lost, read ${ss.message.slice(0, 120)} / ${ss.stateRaw}`, ss);
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3c-mutants",
    desc: "C-A8 MUTANTS: each mutant copy of the guard (and of hooks.json) turns a probe red that this build passes — the revxl condition dropped from the write rule and from the shell rule, K5's sessions requirement dropped (whole, from the name only, and from the shell's sessions token), the shell check moved after the fast path and after the not-plain deny, MultiEdit removed from the matcher (hooks.json) and from the guard's write-type tools, the BOM strip removed for the session and budget file each, and the write-type early return removed so a Write runs on into the SocialCrawl flow",
    fn() {
      const rows = [];
      const TAMPER = 'if (tamper) return done({ hookSpecificOutput: { permissionDecision: "deny" }, systemMessage: tamper });\n';
      const writeOnly = 'if (tamper && WRITE_TOOLS.includes(input.tool_name)) return done({ hookSpecificOutput: { permissionDecision: "deny" }, systemMessage: tamper });\n';
      const FAST = 'if (!rawCmd.toLowerCase().includes("socialcrawl.dev")) return done();\n';
      const NOTPLAIN = '    return deny(NOT_BASH ? M_NOTBASH : M_NOTPLAIN, "not-plain");\n  }\n';
      const W = (p, more) => () => ["", { extra: edit("Write", p, more) }];
      const S = (c, tool = "Bash") => () => [c, { extra: { tool_name: tool } }];
      const passes = (r) => r.raw === "" && r.same;
      const denied = (w, k) => (r) => r.raw === denyOut(mTamper(w, k));
      const cases = [
        ["the write rule's revxl condition dropped", [['      if (!inRevxl && dirname(full) !== (k === 4 ? join(rx(), "sessions") : rx())) return null;\n', ""]], [
          ["Write C:/proj/socialcrawl-budget.json", W(at("C:", ["proj", "socialcrawl-budget.json"])), passes],
        ]],
        ["the shell rule's revxl condition dropped", [['      if (k >= 0 && !REVXL_AT.test(c)) {\n', "      if (false) {\n"]], [   // 3d: the location test's new line
          ["Bash: git grep -n socialcrawl-day.json", S("git grep -n socialcrawl-day.json"), passes],
        ]],
        ["K5's sessions requirement dropped", [
          [' && dirs[dirs.length - 1] === "sessions") k = 4;', ") k = 4;"],
          ['const inRevxl = k === 4 ? dirs[dirs.length - 2] === "revxl" : dirs.includes("revxl");', 'const inRevxl = dirs.includes("revxl");'],
          ['(k === 4 ? join(rx(), "sessions") : rx())', "rx()"],
        ], [
          ["Write <revxl>/socialcrawl-report.json", W(at(REAL, ["socialcrawl-report.json"])), passes],
        ]],
        ["K5's sessions parent dropped from the name only", [[' && dirs[dirs.length - 1] === "sessions") k = 4;', ") k = 4;"]], [
          ["Write <revxl>/examplebrand/socialcrawl-report.json", W(at(REAL, ["examplebrand", "socialcrawl-report.json"])), passes],
        ]],
        ["K5's sessions token dropped from the shell rule", [[`/sessions[${B}${B}/]+socialcrawl-/`, "/socialcrawl-/"]], [
          ["Bash: cat ~/.claude/revxl/socialcrawl-report.json", S("cat ~/.claude/revxl/socialcrawl-report.json"), passes],
        ]],
        ["the shell check moved after the fast path", [[TAMPER, writeOnly], [FAST, FAST + TAMPER]], [
          ["Bash: cat ~/.claude/revxl/credit-guard-unattended.jsonl", S("cat ~/.claude/revxl/credit-guard-unattended.jsonl"), denied("command", 2)],
          ["PowerShell: rm ~/.claude/revxl/sessions/socialcrawl-abc.json", S("rm ~/.claude/revxl/sessions/socialcrawl-abc.json", "PowerShell"), denied("command", 4)],
        ]],
        ["the shell check moved after the not-plain deny", [[TAMPER, writeOnly], [NOTPLAIN, NOTPLAIN + TAMPER]], [
          ["Bash: an echo of a SocialCrawl URL into the budget file", S(`echo '${URL50}' >> ~/.claude/revxl/socialcrawl-budget.json`), denied("command", 0)],
        ]],
        ["MultiEdit removed from the guard's write-type tools", [['const WRITE_TOOLS = ["Write", "Edit", "MultiEdit", "NotebookEdit"];', 'const WRITE_TOOLS = ["Write", "Edit", "NotebookEdit"];']], [
          ["MultiEdit of <revxl>/socialcrawl-budget.json", () => ["", { extra: edit("MultiEdit", at(REAL, ["socialcrawl-budget.json"])) }], denied("edit", 0)],
        ]],
        // 3d reads the three files as bytes: each one's strip is now its text() decode, and String() is UTF-8 with the mark kept.
        ["the session file's BOM strip removed", [["JSON.parse(text(raw))", "JSON.parse(String(raw))"]], [
          ["a BOM'd session file at 100, 50 more", () => [P50, { prep: (s) => writeFileSync(s.stateFile, BOM + JSON.stringify({ balance: 800, spent: 100 })) }], (r) => r.raw === "" && r.state.spent === 150],
        ]],
        ["the budget file's BOM strip removed", [["JSON.parse(text(bfRead.raw))", "JSON.parse(String(bfRead.raw))"]], [
          ["a BOM'd budget of 50, 40 + 50", () => [P50, { prep: (s) => { s.seed({ spent: 40 }); s.budget(BOM + '{"sessionBudget":50}'); } }], (r) => r.message === mLimit({ spent: 40, worst: 50, limit: 50, src: SRC_SESSION, bf: r.bf })],
        ]],
        ["the write-type early return removed", [["if (WRITE_TOOLS.includes(input && input.tool_name)) return done();\n", ""]], [
          ["a Write of an ordinary file carrying a stray command", (s) => ["", { extra: edit("Write", join(s.dir, "notes.md"), { command: P50 }) }], passes],
        ]],
      ];
      for (const [name, pairs, probes] of cases) {
        const m = mutant(name.replace(/[^a-z0-9]+/gi, "-").slice(0, 40), pairs);
        for (const [label, make, ok] of probes) {
          const fix = once(make);
          const mut = once(make, m.file);
          rows.push(cell(`${name}: ${label}`.slice(0, 62), [`build ${verdict(fix)}`, `mutant ${verdict(mut)} ${mut.message.slice(0, 40)}`]));
          assert(ok(fix), `${name}, ${label}: the build behaves, read ${verdict(fix)} / ${fix.message.slice(0, 160)}`, fix);
          assert(!ok(mut), `${name}, ${label}: the mutant is caught (it behaves wrongly), read ${verdict(mut)} / ${mut.message.slice(0, 160)}`, mut);
        }
        rmSync(m.dir, { recursive: true, force: true });
      }
      // hooks.json with MultiEdit taken out of the matcher: a copy of its text, read by C-A5's check.
      const text = readFileSync(HOOKS_JSON, "utf8");
      assert(text.split(`"${MATCHER}"`).length === 2, "hooks.json: the matcher occurs exactly once");
      const cut = hooksProblems(text.replace(`"${MATCHER}"`, '"Bash|PowerShell|Write|Edit|NotebookEdit"'));
      rows.push(cell("hooks.json, MultiEdit removed from the matcher", [`build ${hooksProblems(text).length} problems`, `mutant ${cut.length} problem(s)`]));
      assert(!hooksProblems(text).length && cut.length === 1 && cut[0].startsWith("the PreToolUse entry is "), `hooks.json without MultiEdit is caught for that reason only, read ${JSON.stringify(cut)}`);
      console.log(rows.join("\n"));
    },
  },
];
