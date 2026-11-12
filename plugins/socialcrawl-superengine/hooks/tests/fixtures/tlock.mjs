import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { rmSync } from "node:fs";
import {
  session, V1, TSCRIPT, GUARD, COSTS, LIMIT, NOLOCAL, M_NOTPLAIN, M_NOTBASH, M_LOST,
  mTranscript, mStateRead, mBudgetRead, mError, ROUTINE, assert, T,
} from "../lib.mjs";
import { stateFault } from "./balance.mjs";

const UN = { CLAUDE_CODE_SESSION_ATTENDED: "0" };
const M_SETTINGS = "SocialCrawl call not run: your SocialCrawl settings file can't be read, so this session's credit limit can't be checked. Re-save your limit in SocialCrawl → Settings to fix it." + T;
const SHAPES = [
  ["youtube", `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`],
  ["bolt", `curl -s "${V1}prism/creator-vet?handle=a&include=full,${TSCRIPT}"`],
  ["batch", `curl -X POST "${V1}youtube/${TSCRIPT}s" -d '{"ids":["a"]}'`],
  ["other", `curl -s "${V1}tiktok/post/${TSCRIPT}?url=X"`],
];
const P1 = `curl -s "${V1}amazon/shop?q=a"`;
const FIELDS = ["ts", "session_id", "decision", "kind", "paths", "cmdWorst", "committed", "cap"];
const ROWS = [
  { id: "absent" },
  { id: "missing", value: {} },
  { id: "allow", value: { transcripts: "allow" } },
  { id: "block", value: { transcripts: "block" }, lead: "blocked" },
  ...["Block", "", 1, true, null, {}, [], "allow\n"].map((v) => ({
    id: `unrecognised ${JSON.stringify(v)}`, value: { transcripts: v }, lead: "unrecognised",
  })),
  ...['{not json', '', '[]', '"block"', 'null', '7', 'true'].map((raw) => ({
    id: `bad ${JSON.stringify(raw)}`, raw, lead: "unreadable",
  })),
  { id: "folder", folder: true, lead: "unreadable" },
];

function prepare(s, row, roomy = false) {
  if (row.folder) mkdirSync(s.bf);
  else if (Object.hasOwn(row, "raw")) s.budget(row.raw);
  else if (row.value) s.budget({ ...row.value, ...(roomy ? { sessionBudget: 1000 } : {}) });
}

function probe(cmd, row, { roomy = false, balance, env = {}, guard, extra, seed, prep, node } = {}) {
  const s = session({ balance }).seed(seed || { spent: 0 });
  try {
    prepare(s, row, roomy);
    const added = prep ? prep(s) || {} : {};
    const before = s.stateRaw();
    const r = s.run(cmd, {
      ...NOLOCAL, unsetEnv: [...NOLOCAL.unsetEnv, "OPENAI_API_KEY"],
      env: { ...NOLOCAL.env, ...env, ...(added.env || {}) }, guard, extra, node: added.node || node,
    });
    return { ...r, state: s.state(), unchanged: s.stateRaw() === before, rec: s.callLines(), log: s.logLines() };
  } finally { s.cleanup(); }
}

function locked(r, lead, shape, limit, unattended, spent = 0) {
  assert(r.exit === 0 && r.decision === "deny" && r.message === mTranscript(lead, shape), "exact transcript deny", r);
  assert(r.state.spent === spent && r.unchanged && !r.stateWritten, "deny leaves the committed state unchanged", r);
  assert(r.rec.length === 1 && r.rec[0].decision === "deny" && r.rec[0].kind === "transcript-locked" && r.rec[0].limit === limit,
    "one transcript-locked record with the picked limit", r);
  assert(r.log.length === (unattended ? 1 : 0), "unattended or routine refusal writes the unattended log", r);
  if (unattended) assert(r.log[0].kind === "transcript-locked" && r.log[0].cap === limit && r.log[0].decision === "deny",
    "unattended transcript deny has the picked cap", r);
}

function notPlain(r) {
  assert(r.exit === 0 && r.stderr === "" && r.decision === "deny" && r.message === M_NOTPLAIN &&
    r.unchanged && !r.stateWritten && r.state.spent === 0 && r.rec.length === 0,
    "malformed URL keeps the exact not-plain denial without counting", r);
}

export default [
  {
    id: "TL-G4c-permit-newline", desc: "a permit word followed by a newline remains unrecognised",
    fn(guard) {
      for (const env of [{}, UN]) {
        locked(probe(SHAPES[0][1], { value: { transcripts: "allow" + String.fromCharCode(10) } }, { guard, env }),
          "unrecognised", "youtube", LIMIT, env === UN);
      }
    },
  },
  {
    id: "TL-guard-file-linear", desc: "long guard-file near misses finish promptly and actual parent or stream targets remain protected",
    fn(guard) {
      const parent = "rm " + "revxl/a/".repeat(37500).slice(0, 299996) + "a";
      const stream = join("synthetic", ":".repeat(299980), "file");
      const results = [
        ["parent traversal near miss", probe(parent, ROWS[3], { guard })],
        ["stream suffix near miss", probe("", ROWS[3], {
          guard, extra: { tool_name: "Write", tool_input: { file_path: stream } },
        })],
      ];
      for (const [label, r] of results) {
        console.log(`    300 KB guard-file ${label}: ${r.ms} ms`);
        assert(r.exit === 0 && r.stderr === "" && r.raw === "" && r.unchanged && !r.stateWritten &&
          r.rec.length === 0 && r.log.length === 0, `${label}: silent untouched pass`, r);
        assert(r.ms < 2000, `${label}: completes under 2000 ms`, r);
      }
      const file = "social" + "crawl-budget.json";
      for (const [cmd, extra, target] of [
        [parent + "/../child", undefined, "command names the revxl folder"],
        ["", { tool_name: "Write", tool_input: { file_path: join("revxl", file + ":stream") } }, `edit names the budget file ${file}`],
      ]) {
        const r = probe(cmd, ROWS[3], { guard, extra });
        const message = `SocialCrawl guard file left alone: this ${target}, which holds the person's SocialCrawl budget or spend record. ` +
          "Claude is not to change it (the guard refuses the plain ways; a glob, a link to the folder, an MCP tool or a script can still get past it); the person sets the limit in SocialCrawl → Settings. To look at it, use the Read tool.";
        assert(r.exit === 0 && r.decision === "deny" && r.message === message &&
          r.unchanged && !r.stateWritten && r.rec.length === 0 && r.log.length === 0,
          "actual parent traversal or stream target is still protected", r);
      }
    },
  },
  {
    id: "TL-encoded-hash", desc: "split-first query decoding preserves transcript parameters after encoded hashes and exact base counts",
    fn(guard) {
      const name = `include_${TSCRIPT}s`;
      const search = "search/everywhere?query=";
      const cases = [
        [`${search}x%23&${name}=true`, `param:${name}`, 20],
        [`${search}x%23;${name}=true`, `param:${name}`, 20],
        [`${search}%23ai&${name}=true`, `param:${name}`, 20],
        [`prism/video-intel?url=a%23&x=%zz&include=full,${TSCRIPT.slice(0, -1)}%74`, "bolt", 15, true],
        [`prism/video-intel?url=a%23&include%5B%5D=${TSCRIPT}`, "bolt", 15],
        [`${search}x%23%23&a=%23&${name}=true`, `param:${name}`, 20],
        [`${search}x%2523&${name}=true`, `param:${name}`, 20],
        [`${search}x&${name}=false%26`, `param:${name}`, 20],
        [`${search}x&${name}=0%23`, `param:${name}`, 20],
        // Decoding an encoded equals before locating the literal separator loses this name (M2).
        [`${search}x%23&note%3D${name}=true`, "bolt", 20],
        [`${search}x%23&${name}=false+`, `param:${name}`, 20],
        ...["false%3Fx", "false%00", "false%0A"].map((value) => [`${search}x&${name}=${value}`, `param:${name}`, 20]),
      ];
      const passed = (r, expected) => {
        assert(r.exit === 0 && r.stderr === "" && r.decision === null && r.raw === "" && r.state.spent === expected,
          `silent pass commits exactly ${expected}`, r);
        assert(r.rec.length === 1 && r.rec[0].decision === "pass" && r.rec[0].kind === "under-cap" &&
          r.rec[0].worst === expected && r.rec[0].committed === expected, "one record has the exact count", r);
      };
      for (const unattended of [false, true]) {
        const env = unattended ? UN : {};
        for (const [path, shape, expected, malformed] of cases) {
          const cmd = `curl -s "${V1}${path}"`;
          if (malformed) {
            for (const row of [ROWS[3], ROWS[2], ROWS[0]]) notPlain(probe(cmd, row, { env, guard }));
            continue;
          }
          locked(probe(cmd, ROWS[3], { env, guard }), "blocked", shape, LIMIT, unattended);
          for (const row of [{ value: { transcripts: "allow", sessionBudget: 1000 } }, ROWS[0]]) {
            passed(probe(cmd, row, { env, guard }), expected);
          }
        }
        for (const [path, expected] of [
          [`${search}%23ai`, 20],
          [`${search}x%23&${name}=false`, 20],
          [`amazon/shop?q=a%23${TSCRIPT}`, 1],
          [`amazon/shop?q=%23&note=${name}`, 1],
          [`amazon/shop?q=%23&note=ok%3D${name}`, 1],
        ]) passed(probe(`curl -s "${V1}${path}"`, ROWS[3], { env, guard }), expected);
      }
    },
  },
  {
    id: "TL-semicolon-value", desc: "semicolon-bearing values lock in either query or form readings while exact exemptions retain base counts",
    fn(guard) {
      const name = `include_${TSCRIPT}s`;
      const search = "search/everywhere?query=";
      const query = (tail) => `curl -s "${V1}${search}${tail}"`;
      const post = `curl -X POST "${V1}${search}x"`;
      // Both form commands committed exactly 20 in control runs at b557a7c.
      const cases = [
        ...[
          `x&${name}=false;x`, `x&${name}=0;`, `x%23&${name}=false;x`,
          `x&${name}=0;x`, `x&${name}=false;${name}=false`,
        ].map((tail) => [query(tail), 20]),
        [`${post} -d '${name}=false;x'`, 20],
        [`${post} -d 'a=1&${name}=0;'`, 20],
      ];
      const passed = (r, expected) => {
        assert(r.exit === 0 && r.stderr === "" && r.decision === null && r.raw === "" && r.state.spent === expected,
          `silent pass commits exactly ${expected}`, r);
        assert(r.rec.length === 1 && r.rec[0].decision === "pass" && r.rec[0].kind === "under-cap" &&
          r.rec[0].worst === expected && r.rec[0].committed === expected, "one record has the exact count", r);
      };
      for (const unattended of [false, true]) {
        const env = unattended ? UN : {};
        for (const [cmd, expected] of cases) {
          locked(probe(cmd, ROWS[3], { env, guard }), "blocked", `param:${name}`, LIMIT, unattended);
          for (const row of [{ value: { transcripts: "allow", sessionBudget: 1000 } }, ROWS[0]]) {
            passed(probe(cmd, row, { env, guard }), expected);
          }
        }
        for (const [cmd, expected] of [
          ...[`x&${name}=false`, `x&${name}=0`, `x&${name}=false&x=1`, `x;${name}=false`]
            .map((tail) => [query(tail), 20]),
          [query("a;b"), 20],
          [`curl -s "${V1}amazon/shop?q=a;b&c=d"`, 1],
          [`curl -s "${V1}amazon/shop?q=${TSCRIPT};x"`, 1],
          [`${post} -d '${name}=false'`, 20],
          [`${post} -d 'a=1&${name}=0'`, 20],
        ]) passed(probe(cmd, ROWS[3], { env, guard }), expected);
      }
    },
  },
  {
    id: "TL-G4c-brief-error-mutant", desc: "removing the decoded brief-check clause reopens all four error bypasses",
    fn() {
      const s = session();
      try {
        const src = readFileSync(GUARD, "utf8");
        const clause = ' || s.includes("brief-check")';
        const anchor = 'if (rawCmd.length > MAX_CMD';
        assert(src.split(clause).length === 2 && src.split(anchor).length === 2, "error mutant anchors occur once");
        const forced = src.replace(anchor, 'throw new Error("forced G4c fault");\n' + anchor);
        const fixed = join(s.dir, "fixed");
        const mutant = join(s.dir, "mutant");
        for (const [dir, code] of [[fixed, forced], [mutant, forced.replace(clause, "")]]) {
          mkdirSync(dir);
          writeFileSync(join(dir, "credit-guard.mjs"), code);
          copyFileSync(COSTS, join(dir, "costs.json"));
        }
        for (const path of ["prism/brief-check?url=X", "prism//brief-check?url=X", "prism/brief-check/?url=X", "prism/brief%2Dcheck?url=X"]) {
          const cmd = `curl -s "${V1}${path}"`;
          for (const [mode, env] of [["attended", {}], ["unattended", UN], ["routine", ROUTINE]]) {
            const good = probe(cmd, ROWS[3], { guard: join(fixed, "credit-guard.mjs"), env });
            const bad = probe(cmd, ROWS[3], { guard: join(mutant, "credit-guard.mjs"), env });
            assert(good.exit === 0 && good.stderr === "" && good.decision === "deny" && good.message === mTranscript("error"),
              "fixed clause gives the exact F5 refusal", good);
            assert(bad.exit === 0 && bad.stderr === "" && bad.message === (mode === "attended" ? "" : mError()) &&
              bad.decision === (mode === "attended" ? null : "deny") && bad.unchanged && bad.rec.length === 0,
              "mutant wrongly passes attended or gives the generic error instead of F5", bad);
            if (mode !== "attended") assert(good.log[0]?.kind === "transcript-locked" && bad.log[0]?.kind === "error",
              "mutant loses the transcript-locked log kind", bad);
            console.log(`    ${path}/${mode}: decoded-clause mutant killed`);
          }
        }
      } finally { s.cleanup(); }
    },
  },
  {
    id: "TL-guard-error", desc: "guard errors refuse decoded transcript text in every mode and preserve other error behaviour",
    fn(guard = GUARD) {
      const s = session();
      try {
        const src = readFileSync(guard, "utf8");
        const name = "credit" + "-guard.mjs";
        const costDir = join(s.dir, "cost-error");
        mkdirSync(costDir);
        const costGuard = join(costDir, name);
        const anchor = "  function costOf(url, skipGate = false, verb = VERB, gate = null) {";
        assert(src.split(anchor).length === 2, "cost fault anchor occurs exactly once");
        writeFileSync(costGuard, src.replace(anchor, anchor + '\n    throw new Error("forced cost fault");'));
        copyFileSync(COSTS, join(costDir, "costs.json"));
        const outerGuard = join(s.dir, name);
        writeFileSync(outerGuard, src);
        copyFileSync(COSTS, join(s.dir, "costs.json"));
        const preload = join(s.dir, "outer-throws.mjs");
        writeFileSync(preload,
          'import { createRequire, syncBuiltinESMExports } from "node:module";\n' +
          'const path = createRequire(import.meta.url)("node:path");\n' +
          'const real = path.join;\n' +
          'path.join = (...a) => { if (a.includes("sessions")) throw new Error("forced"); return real(...a); };\n' +
          'syncBuiltinESMExports();\n');
        const post = `curl -X POST "${V1}prism/video-intel?url=a"`;
        const cases = [
          ...SHAPES.map(([shape, cmd]) => [cmd, shape, { youtube: 3, bolt: 75, batch: 300, other: 10 }[shape]]),
          [`${post} -d 'include=${TSCRIPT}'`, "bolt", 15],
          [`curl -s "${V1}search/everywhere?query=x&include_${TSCRIPT}s=true"`, `param:include_${TSCRIPT}s`, 20],
          [`curl -s "${V1}prism/video-intel?url=a&include=trans%63ript"`, "bolt", 15],
          [`${post} -d '{"note":"${TSCRIPT}"}'`, undefined, 15],
          [`curl -s "${V1}amazon/shop?q=${TSCRIPT.toUpperCase()}"`, undefined, 1],
          [`${post} -d '{"include":"\\u0074ranscript"}'`, "bolt", 15],
          [`curl -s "${V1}prism/video-intel?url=%zz&include=trans%63ript"`, "bolt", null, true],
          [`curl -s "${V1}prism/video-intel?url=%ff%74&include=trans%63ript"`, "bolt", null, true],
          ...[
            ["prism/brief-check?url=X", 15],
            ["prism//brief-check?url=X", 50],
            ["prism/brief-check/?url=X", 50],
          ].map(([path, expected]) => [`curl -s "${V1}${path}"`, "other", expected]),
          [`curl -s "${V1}prism/brief%2Dcheck?url=X"`, "other", null, true],
          [P1, undefined, 1],
        ];
        for (const [mode, env] of [["attended", {}], ["unattended", UN], ["routine-only", ROUTINE]]) {
          const logged = mode !== "attended";
          for (const row of [ROWS[3], ROWS[2], ROWS[0]]) for (const [cmd, shape, expected, notPlain] of cases) {
            const label = `${mode}/${row.id}/${cases.findIndex((c) => c[0] === cmd)}`;
            const control = probe(cmd, row, { guard, env, balance: 2000 });
            if (notPlain) assert(control.exit === 0 && control.message === M_NOTPLAIN && control.decision === "deny" &&
              control.unchanged && control.state.spent === 0, `${label}: encoded path retains its non-plain refusal`, control);
            else if (row.lead && shape) locked(control, "blocked", shape, 500, logged);
            else assert(control.exit === 0 && control.raw === "" && control.state.spent === expected &&
              control.rec.length === 1 && control.rec[0].kind === "under-cap" && control.rec[0].worst === expected,
              `${label}: normal control retains its exact count`, control);
            for (const fault of [
              // A non-plain command's costing fault is absorbed before failed(); force its early guard error instead.
              ...(!notPlain ? [{ guard: costGuard }] : []),
              { guard: outerGuard, node: ["--import", pathToFileURL(preload).href] },
            ]) {
              const r = probe(cmd, row, { ...fault, env, balance: 2000 });
              const transcript = cmd !== P1;
              const denied = transcript || logged;
              assert(r.exit === 0 && r.stderr === "" && r.decision === (denied ? "deny" : null) &&
                r.message === (transcript ? mTranscript("error", undefined) : logged ? mError() : "") &&
                (denied || r.raw === ""), `${label}: exact guard error decision and message`, r);
              assert(r.unchanged && !r.stateWritten && r.state.spent === 0 && r.rec.length === 0,
                `${label}: error never counts or writes a call record`, r);
              assert(r.log.length === (logged ? 1 : 0), `${label}: exactly one log only when unattended or routine`, r);
              if (logged) {
                const line = r.log[0];
                assert(line.decision === "deny" && line.kind === (transcript ? "transcript-locked" : "error") &&
                  Array.isArray(line.paths) && line.paths.length === 0 &&
                  line.cmdWorst === null && line.committed === null && line.cap === null,
                  `${label}: error log has the exact kind, empty paths and null figures`, r);
              }
            }
          }
        }
      } finally { s.cleanup(); }
    },
  },
  {
    id: "TL-param-name", desc: "decoded query and body names lock individually, safe names get their own hint, and exemptions keep exact counts",
    fn(guard) {
      const name = `include_${TSCRIPT}s`;
      const search = `search/everywhere?query=x`;
      const query = (piece, path = search) => `curl -s "${V1}${path}&${piece}"`;
      const post = `curl -X POST "${V1}${search}"`;
      const json = (value) => `${post} -d '{"query":"x","${name}":${value}}'`;
      const documented = query(`${name}=true`);
      // Control runs on the base tree committed 20 for both POST JSON true and false.
      const bodyBase = 20;
      const cases = [
        [documented, name, 20],
        ...["False", "FALSE", "fALSE"].map((value) => [query(`${name}=${value}`), name, 20]),
        ...["False", "FALSE"].map((value) => [`${post} -d '${name}=${value}'`, name, bodyBase]),
        [json('"False"'), name, bodyBase],
        [query(`x_${TSCRIPT}_y=1`, "amazon/shop?q=a"), `x_${TSCRIPT}_y`, 10],
        ...["", "=", "=1", "=yes"].map((suffix) => [query(name + suffix), name, 20]),
        [query(`${name.toUpperCase()}=true`), name, 20],
        [query(`include%5F${TSCRIPT}s=true`), name, 20],
        [query(`include_trans%63ripts=true`), name, 20],
        [query(`include_transcrip%2574s=true`), name, 20],
        [`curl -s "${V1}${search};${name}=true"`, name, 20],
        [query(`${name}=false&${name}=true`), name, 20],
        [`${post} -d '${name}=true'`, name, bodyBase],
        [json("true"), name, bodyBase],
        [`${post} -d '{"opts":{"with_${TSCRIPT}":"yes"}}'`, `with_${TSCRIPT}`, bodyBase],
        ...["null", '""', "{}", "[]"].map((value) => [json(value), name, bodyBase]),
        [`${post} -d '${name}='`, name, bodyBase],
        [`${post} -d '{"include_trans\\u0063ripts":true}'`, name, bodyBase],
        [`${post} -d '[{"${name}":true}]'`, name, bodyBase],
        [query(`${TSCRIPT}%20x=1`), null, 20],
        [query(`sc_${TSCRIPT}=1`), null, 20],
        [query(`${TSCRIPT}${"x".repeat(55)}=1`), null, 20],
        [query(`${TSCRIPT}${"x".repeat(54)}=1`), TSCRIPT + "x".repeat(54), 20],
        [query(`a.${TSCRIPT}%5B0%5D-x=1`), `a.${TSCRIPT}[0]-x`, 20],
        // A newly matched name wins over an include hint, in either source.
        [query(`include%5B%5D=${TSCRIPT}&${name}=true`), name, 20],
        [query(`include=${TSCRIPT}&${name}=true`), name, 20],
        [`${post} -d '{"include":"${TSCRIPT}","${name}":true}'`, name, bodyBase],
        [query(`${name}=true&with_${TSCRIPT}=yes`), name, 20],
        [`${documented} -d '{"with_${TSCRIPT}":true}'`, name, 20],
      ];
      const passed = (r, expected) => {
        assert(r.exit === 0 && r.decision === null && r.raw === "" && r.state.spent === expected,
          `silent pass commits exactly ${expected}`, r);
        assert(r.rec.length === 1 && r.rec[0].decision === "pass" && r.rec[0].kind === "under-cap" &&
          r.rec[0].worst === expected && r.rec[0].committed === expected, "one record carries the exact count", r);
      };
      for (const unattended of [false, true]) {
        const env = unattended ? UN : {};
        for (const [cmd, param, expected] of cases) {
          locked(probe(cmd, ROWS[3], { env, guard }), "blocked", param ? `param:${param}` : "bolt", LIMIT, unattended);
          for (const row of [{ value: { transcripts: "allow", sessionBudget: 1000 } }, ROWS[0]]) {
            passed(probe(cmd, row, { env, guard }), expected);
          }
        }
        for (const [row, lead] of [[{ raw: "{not json" }, "unreadable"], [{ value: { transcripts: 7 } }, "unrecognised"]]) {
          locked(probe(documented, row, { env, guard }), lead, `param:${name}`, LIMIT, unattended);
        }
        for (const [cmd, expected] of [
          ...["false", "0", "%66alse"].map((value) => [query(`${name}=${value}`), 20]),
          ...["false", "0", '"false"', '"0"'].map((value) => [json(value), bodyBase]),
          ...["false", "0"].map((value) => [`${post} -d '${name}=${value}'`, bodyBase]),
          [`${post} -d '{"opts":{"with_${TSCRIPT}":false}}'`, bodyBase],
          [`curl -s "${V1}amazon/shop?q=${TSCRIPT}"`, 1],
          [query(`note=${name}`, "amazon/shop?q=a"), 1],
          [`curl -s "${V1}${search}"`, 20],
        ]) passed(probe(cmd, ROWS[3], { env, guard }), expected);
        // A path token retains its path sentence, even with a matched name alongside it.
        locked(probe(`curl -s "${V1}youtube/video/${TSCRIPT}?${name}=true"`, ROWS[3], { env, guard }),
          "blocked", "youtube", LIMIT, unattended);
      }
    },
  },
  {
    id: "TL-body-include", desc: "body includes lock only their own curl; readable controls retain base counts and unreadable bodies fail closed",
    fn(guard) {
      const post = `curl -X POST "${V1}prism/video-intel"`;
      const form = `include=${TSCRIPT}`;
      const json = `{"url":"a","include":"${TSCRIPT}"}`;
      const bodyCall = `${post} -d '${json}'`;
      const cases = [
        [`curl -X POST "${V1}prism/video-intel?url=a" -d '${form}'`, 15],
        [`${post} -H "Content-Type: application/json" -d '${json}'`, 15],
        [`${post} -d '{"url":"a","include":["full","${TSCRIPT}"]}'`, 15],
        [`${post} -d '{"url":"a","include":"trans\\u0063ript"}'`, 15],
        [`curl -s "${V1}prism/video-intel?url=a" -d '${form}'`, 15],
        [`curl -X GET "${V1}prism/video-intel?url=a" -d '${form}'`, 15],
        ...[
          `url=a' -d '${form}`, `url=a&INCLUDE=${TSCRIPT[0].toUpperCase() + TSCRIPT.slice(1)}`, `include%5B%5D=${TSCRIPT}`,
          `include[]=${TSCRIPT}`, `include=full%2Ctrans%63ript`, `url=a;${form}`, `x=%zz&${form}`,
          `{"options":{"include":["${TSCRIPT}"]}}`, `{"INCLUDE":"${TSCRIPT[0].toUpperCase() + TSCRIPT.slice(1)}"}`,
          ` ${json}`, `\n${json}`,
          `{"include":{"nested":[{"value":"${TSCRIPT}"}]}}`,
          `[{"include":"${TSCRIPT}"}]`, `include[a][b]=${TSCRIPT}`,
          `{"includ\\u0065":"${TSCRIPT}"}`,
        ].map((body) => [`${post} -d '${body}'`, 15]),
        [`${post} -d '{"include":{"${TSCRIPT}":true}}'`, 15, `param:${TSCRIPT}`],
        [`${P1} && ${bodyCall}`, 16], [`${bodyCall} && ${P1}`, 16],
        // Video-intel's metered ceiling already enforces 15; this flat price needs previousWorst (M7).
        [`curl -X POST "${V1}prism/leads?query=x" -d '${form}'`, 50],
      ];
      const passed = (r, expected, label) => {
        assert(r.exit === 0 && r.decision === null && r.raw === "" && r.state.spent === expected,
          `${label}: silent pass commits exactly ${expected}`, r);
        assert(r.rec.length === 1 && r.rec[0].decision === "pass" && r.rec[0].kind === "under-cap" &&
          r.rec[0].worst === expected && r.rec[0].committed === expected,
          `${label}: one under-cap record with the exact figure`, r);
      };
      let n = 0;
      for (const unattended of [false, true]) {
        const env = unattended ? UN : {};
        for (const [cmd, expected, shape = "bolt"] of cases) {
          locked(probe(cmd, ROWS[3], { env, guard }), "blocked", shape, LIMIT, unattended);
          for (const row of [{ value: { transcripts: "allow", sessionBudget: 1000 } }, ROWS[0]]) {
            passed(probe(cmd, row, { env, guard }), expected, `body case ${n}`);
          }
          n++;
        }
        for (const [cmd, expected] of [
          [`${post} -d '{"url":"a","include":"full"}'`, 15],
          [`${post} -d 'url=a&include=full'`, 15],
          [`${post} -d '{"url":"a","note":"${TSCRIPT}"}'`, 15],
          [`${post} -d 'q=${TSCRIPT}'`, 15],
          [`${P1} && ${post} -d '{"url":"a"}'`, 16],
          [`curl -X POST "${V1}web/scrape" -d '{"url":"https://example.com/${TSCRIPT}"}'`, 5],
          [`${post} -d '{"a":"b","t":":smile:","u":":"}'`, 15],
          [`${post} -d '{"a":"\\\"include\\\":","b":{"a":"ok"}}'`, 15],
          [`${post} -d 'include=full&flag&x=a+b&x=%zz'`, 15],
          [`${post} -d '{"url":"a"}' && ${P1}`, 16],
        ]) passed(probe(cmd, ROWS[3], { env, guard }), expected, "readable control");
        // A previously GATED call retains its old figure even with an include in its body.
        const oldGate = `curl -s "${V1}prism/video-intel?include=${TSCRIPT}" -d '${form}'`;
        passed(probe(oldGate, ROWS[2], { env, guard }), 15, "existing URL gate");
        for (const body of [
          `{"url":"a","include":"full","include":"${TSCRIPT}"}`,
          `{"include":"${TSCRIPT}",}`, `{include:"${TSCRIPT}"}`, '[1,2',
          '{"x":{"a":1,"a":2}}', '{"include":"full","includ\\u0065":"full"}',
        ]) for (const row of [ROWS[3], ROWS[2], ROWS[0]]) for (const path of ["prism/video-intel", "amazon/shop?q=a"]) {
          const r = probe(`curl -X POST "${V1}${path}" -d '${body}'`, row, { env, guard });
          assert(r.exit === 0 && r.decision === "deny" && r.message === M_NOTPLAIN && r.unchanged &&
            !r.stateWritten && r.rec.length === 0, "unreadable body: exact not-plain deny with no commit or record", r);
        }
      }
      console.log(`    ${n} body lock cases, allow/absent counts, readable controls and unreadable bodies`);
    },
  },
  {
    id: "TL-table", desc: "every budget state, call shape and attendance mode; exact text, records and counts",
    fn() {
      let n = 0;
      for (const row of ROWS) for (const [shape, cmd] of SHAPES) for (const unattended of [false, true]) {
        // The batch ceiling is 300. No-lock object rows use a roomy session budget.
        // An absent file must stay absent: its control and probe use balance 2000 (cap 500).
        const roomy = shape === "batch" && !row.lead;
        const balance = roomy && row.id === "absent" ? 2000 : undefined;
        const env = unattended ? UN : {};
        const r = probe(cmd, row, { roomy, balance, env });
        if (row.lead) locked(r, row.lead, shape, LIMIT, unattended);
        else {
          const expected = { youtube: 3, bolt: 75, batch: 300, other: 10 }[shape];
          assert(r.exit === 0 && r.decision === null && r.raw === "" && r.state.spent === expected,
            `${row.id}/${shape}: silent pass counts exactly ${expected}`, r);
          assert(r.rec.length === 1 && r.rec[0].decision === "pass" && r.rec[0].kind === "under-cap", "one under-cap record", r);
        }
        n++;
      }
      console.log(`    ${n} table probes`);
    },
  },
  {
    id: "TL-batch-slashes", desc: "slash variants keep the batch hint and hold at least their ungated floor",
    fn() {
      for (const [shape, path] of [
        ["batch", `youtube/${TSCRIPT}s/`], ["batch", `youtube//${TSCRIPT}s`],
        ["batch", `/youtube/${TSCRIPT}s`], ["youtube", `youtube/video/${TSCRIPT}/`],
      ]) for (const unattended of [false, true]) {
        const env = unattended ? UN : {};
        const cmd = `curl -s "${V1}${path}"`;
        locked(probe(cmd, ROWS[3], { env }), "blocked", shape, LIMIT, unattended);
        const worst = shape === "batch" ? 300 : 50;
        const r = probe(cmd, ROWS[2], { env, roomy: shape === "batch" });
        assert(r.exit === 0 && r.raw === "" && r.state.spent === worst && r.rec.length === 1 &&
          r.rec[0].kind === "under-cap" && r.rec[0].committed === worst, "allow holds the higher typed or normalized price", r);
      }
    },
  },
  {
    id: "TL-skill-form", desc: "URL then continued environment-key header locks and counts every shape",
    fn() {
      const paths = [
        `youtube/video/${TSCRIPT}?id=a`, `prism/creator-vet?handle=a&include=full,${TSCRIPT}`,
        `youtube/${TSCRIPT}s`, `tiktok/post/${TSCRIPT}?url=X`,
      ];
      for (const [i, [shape]] of SHAPES.entries()) for (const unattended of [false, true]) {
        const cmd = `curl "${V1}${paths[i]}" \\\n  -H "x-api-key: $SOCIALCRAWL_API_KEY"`;
        const env = unattended ? UN : {};
        locked(probe(cmd, ROWS[3], { env }), "blocked", shape, LIMIT, unattended);
        const r = probe(cmd, { value: { transcripts: "allow", sessionBudget: 1000 } }, { env });
        const expected = { youtube: 3, bolt: 75, batch: 300, other: 10 }[shape];
        assert(r.exit === 0 && r.raw === "" && r.state.spent === expected && r.rec.length === 1 &&
          r.rec[0].kind === "under-cap" && r.rec[0].committed === expected,
          `${shape}: skill form counts exactly ${expected}`, r);
      }
    },
  },
  {
    id: "TL-routine-log", desc: "routine-only refusals and paid passes each log once",
    fn() {
      for (const [cmd, row, kind, message, seed] of [
        [SHAPES[0][1], ROWS[3], "transcript-locked", mTranscript("blocked", "youtube")],
        [`echo ${P1}`, ROWS[0], "not-plain", M_NOTPLAIN],
        [P1, ROWS[0], "over-limit", null, { spent: LIMIT }],
        [`${P1} ${"a".repeat(65536)}`, ROWS[0], "not-plain", M_NOTPLAIN],
      ]) {
        const r = probe(cmd, row, { env: ROUTINE, seed });
        assert(r.exit === 0 && r.decision === "deny" && (!message || r.message === message) && r.unchanged,
          `${kind}: routine refusal`, r);
        assert(r.log.length === 1 && r.log[0].decision === "deny" && r.log[0].kind === kind &&
          JSON.stringify(Object.keys(r.log[0])) === JSON.stringify(FIELDS), `${kind}: exactly one log in the existing shape`, r);
      }
      const r = probe(P1, ROWS[0], { env: ROUTINE });
      assert(r.exit === 0 && r.raw === "" && r.state.spent === 1 && r.log.length === 1 &&
        r.log[0].decision === "pass" && r.log[0].kind === "under-cap" && r.log[0].cmdWorst === 1,
        "passing routine counts exactly one and adds one unattended pass log", r);
      const fault = stateFault();
      try {
        const r = probe(P1, ROWS[0], { env: ROUTINE, prep: (s) => ({
          node: ["--import", fault], env: { STATE_FAULT: JSON.stringify(["busy", s.stateFile, "EACCES"]) },
        }) });
        assert(r.exit === 0 && r.decision === "deny" && r.unchanged && r.log.length === 1 &&
          r.log[0].decision === "deny" && r.log[0].kind === "error" &&
          JSON.stringify(Object.keys(r.log[0])) === JSON.stringify(FIELDS), "recorded refusal logs once for a routine", r);
      } finally { rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true }); }
    },
  },
  {
    id: "TL-brief-check", desc: "brief-check follows every lock row and command order without changing its count",
    fn() {
      const cmd = `curl -s "${V1}prism/brief-check?url=X"`;
      const spent = 15; // HEAD's committed figure for the priced GET brief-check call.
      const passed = (r, expected) => {
        assert(r.exit === 0 && r.decision === null && r.raw === "" && r.state.spent === expected,
          `silent pass commits exactly ${expected}`, r);
        assert(r.rec.length === 1 && r.rec[0].decision === "pass" && r.rec[0].kind === "under-cap" &&
          r.rec[0].worst === expected && r.rec[0].committed === expected, "one pass / under-cap record with the exact figure", r);
      };
      for (const unattended of [false, true]) {
        const env = unattended ? UN : {};
        for (const row of ROWS) {
          const r = probe(cmd, row, { env });
          if (row.lead) locked(r, row.lead, "other", LIMIT, unattended);
          else {
            const control = probe(cmd, row.id === "absent" ? ROWS[0] : ROWS[1], { env });
            passed(control, spent);
            passed(r, control.state.spent);
          }
        }
        locked(probe(cmd, { value: { transcripts: "block", sessionBudget: 50 } }, { env }),
          "blocked", "other", 50, unattended);
        for (const [chain, shape] of [[`${cmd} && ${SHAPES[0][1]}`, "other"], [`${SHAPES[0][1]} && ${cmd}`, "youtube"]]) {
          locked(probe(chain, ROWS[3], { env }), "blocked", shape, LIMIT, unattended);
          passed(probe(chain, { value: { transcripts: "allow", sessionBudget: 1000 } }, { env }), spent + 3);
        }
        // HEAD commits 50 for each slash variant; only the lock match is normalised.
        for (const [path, expected] of [
          ["prism/brief-check/?url=X", 50],
          ["prism/brief-check/", 50],
          ["prism//brief-check?url=X", 50],
          ["/prism/brief-check?url=X", 50],
          ["prism/brief-check//?url=X", 50],
          ["prism///brief-check/?url=X", 50],
        ]) {
          const variant = `curl -s "${V1}${path}"`;
          locked(probe(variant, ROWS[3], { env }), "blocked", "other", LIMIT, unattended);
          passed(probe(variant, { value: { transcripts: "allow", sessionBudget: 1000 } }, { env }), expected);
        }
        for (const [path, expected] of [
          ["prism/brief-checks?url=X", 50],
          ["prism/brief-check-x?url=X", 50],
          ["prism/brief?url=X", 50],
          ["prism/lookup?handle=abc", 5],
          ["prism/brief-check/x?url=X", 50],
          ["prism/brief-check.json?url=X", 50],
          ["prism/brief-checks/?url=X", 50],
        ]) {
          const other = `curl -s "${V1}${path}"`;
          passed(probe(other, ROWS[1], { env }), expected);
          passed(probe(other, ROWS[3], { env }), expected);
        }
        for (const verb of ["POST", "PUT", "PATCH", "DELETE"]) {
          const otherVerb = `curl -X ${verb} "${V1}prism/brief-check?url=X"`;
          locked(probe(otherVerb, ROWS[3], { env }), "blocked", "other", LIMIT, unattended);
          passed(probe(otherVerb, ROWS[2], { env }), spent);
        }
        for (const verb of ["HEAD", "OPTIONS"]) {
          const r = probe(`curl -X ${verb} "${V1}prism/brief-check?url=X"`, ROWS[3], { env });
          assert(r.decision === "deny" && r.message === M_NOTPLAIN && r.unchanged,
            "verbs outside the existing plain grammar retain the earlier deny", r);
        }
      }
      const s = session();
      try {
        const src = readFileSync(GUARD, "utf8");
        const anchor = '      let lead = null;';
        assert(src.split(anchor).length === 2, "brief-check lock fault anchor occurs exactly once");
        const guard = join(s.dir, "credit-guard.mjs");
        writeFileSync(guard, src.replace(anchor, '      throw new Error("forced lock fault");\n' + anchor));
        copyFileSync(COSTS, join(s.dir, "costs.json"));
        for (const unattended of [false, true]) {
          const env = unattended ? UN : {};
          passed(probe(cmd, ROWS[2], { env }), spent);
          locked(probe(cmd, ROWS[2], { env, guard }), "error", "other", LIMIT, unattended);
        }
      } finally { s.cleanup(); }
    },
  },
  {
    id: "TL-limit-on-record", desc: "the transcript deny records the session budget or the automatic limit and balance",
    fn() {
      for (const unattended of [false, true]) for (const budget of [{ transcripts: "block", sessionBudget: 50 }, { transcripts: "block" }]) {
        const limit = budget.sessionBudget || LIMIT;
        const r = probe(SHAPES[0][1], { value: budget }, { env: unattended ? UN : {} });
        locked(r, "blocked", "youtube", limit, unattended);
        assert(r.rec[0].balance === 800, "cached balance is recorded", r);
      }
    },
  },
  {
    id: "TL-non-gated-untouched", desc: "readable settings leave non-gated calls unchanged; unreadable settings deny paid calls and preserve free calls",
    fn() {
      for (const row of ROWS) for (const cmd of [P1, `curl -s "${V1}prism/leads?query=x"`, `curl -s "${V1}credits/balance"`, `curl -s "${V1}youtube/video/subtitles?id=abc"`]) {
        for (const env of [{}, UN]) {
          const bare = row.value ? { value: Object.fromEntries(Object.entries(row.value).filter(([k]) => k !== "transcripts")) } : ROWS[0];
          const a = probe(cmd, row, { env }), b = probe(cmd, bare, { env });
          if (row.lead === "unreadable" && b.state.spent > 0) assert(a.exit === 0 && a.decision === "deny" && a.message === M_SETTINGS &&
            a.unchanged && a.state.spent === 0 && a.rec.length === 1 && a.rec[0].kind === "error" && a.rec[0].limit === null,
            `${row.id}: unreadable settings deny the paid non-gated call without counting`, a);
          else assert(a.raw === b.raw && a.decision === b.decision && a.message === b.message && a.state.spent === b.state.spent,
            `${row.id}: identical non-gated output and spend`, a);
        }
      }
    },
  },
  {
    id: "TL-chained", desc: "one gated leg locks a whole command; allow counts the sum; first gated shape wins",
    fn() {
      for (const [shape, gated] of SHAPES) for (const cmd of [`${gated} && ${P1}`, `${P1} && ${gated}`]) for (const unattended of [false, true]) {
        const env = unattended ? UN : {};
        const r = probe(cmd, { value: { transcripts: "block", sessionBudget: 1000 } }, { env });
        locked(r, "blocked", shape, 1000, unattended);
        const allow = probe(cmd, { value: { transcripts: "allow", sessionBudget: 1000 } }, { env });
        const single = probe(gated, { value: { sessionBudget: 1000 } });
        assert(allow.raw === "" && allow.state.spent === single.state.spent + 1, "allow counts both legs", allow);
      }
      for (const [first, second] of [[SHAPES[0], SHAPES[1]], [SHAPES[1], SHAPES[0]]]) {
        locked(probe(`${first[1]} && ${second[1]}`, ROWS[3]), "blocked", first[0], LIMIT, false);
      }
    },
  },
  {
    id: "TL-order", desc: "not-plain and lost precede the lock; the lock precedes over-limit",
    fn() {
      for (const env of [{}, UN]) {
        const np = probe(`for i in 1 2; do ${SHAPES[0][1]}; done`, ROWS[3], { env });
        assert(np.decision === "deny" && np.message === M_NOTPLAIN && np.unchanged, "not-plain remains first", np);
        const lost = probe(SHAPES[0][1], ROWS[3], { env, seed: { spent: 5, lost: true } });
        assert(lost.decision === "deny" && lost.message === M_LOST && lost.state.spent === 5, "lost remains first", lost);
        locked(probe(SHAPES[1][1], ROWS[3], { env, seed: { spent: 195 } }), "blocked", "bolt", LIMIT, env === UN, 195);
      }
      const fault = stateFault();
      try {
        for (const env of [{}, UN]) for (const [field, message] of [["stateFile", mStateRead], ["bf", mBudgetRead]]) {
          let want;
          const r = probe(SHAPES[0][1], ROWS[3], {
            env, prep: (s) => {
              want = message(s[field]);
              return { node: ["--import", fault], env: { STATE_FAULT: JSON.stringify(["read", s[field], "EACCES"]) } };
            },
          });
          assert(r.decision === "deny" && r.message === want && r.unchanged, "existing unreadable-file deny precedes the transcript lock", r);
        }
      } finally { rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true }); }
    },
  },
  {
    id: "TL-throws", desc: "early and late lock faults deny every shape attended and unattended without counting",
    fn() {
      const s = session();
      try {
        const src = readFileSync(GUARD, "utf8");
        const anchor = '    try {\n      const first = transcriptCalls[0];';
        assert(src.split(anchor).length === 2, "lock mutation anchor occurs exactly once");
        const guard = join(s.dir, "credit-guard.mjs");
        writeFileSync(guard, src.replace(anchor, '    try {\n      throw new Error("forced lock fault");\n      const first = transcriptCalls[0];'));
        copyFileSync(COSTS, join(s.dir, "costs.json"));
        const late = join(s.dir, "late"); mkdirSync(late);
        const a2 = '      let lead = null;';
        assert(src.split(a2).length === 2, "late anchor occurs exactly once");
        const lateGuard = join(late, "credit-guard.mjs");
        writeFileSync(lateGuard, src.replace(a2, '      throw new Error("forced lock fault");\n' + a2));
        copyFileSync(COSTS, join(late, "costs.json"));
        const roomy = { value: { transcripts: "allow", sessionBudget: 1000 } };
        for (const [shape, cmd] of SHAPES) for (const unattended of [false, true]) {
          const env = unattended ? UN : {};
          const control = probe(cmd, roomy, { env });
          assert(control.exit === 0 && control.raw === "" && control.state.spent ===
            { youtube: 3, bolt: 75, batch: 300, other: 10 }[shape], "unmutated shape control counts exactly", control);
          locked(probe(cmd, roomy, { env, guard: lateGuard }), "error", shape, 1000, unattended);
          locked(probe(cmd, roomy, { env, guard }), "error", undefined, 1000, unattended);
        }
      } finally { s.cleanup(); }
    },
  },
  {
    id: "TL-encodings", desc: "UTF-8 BOM and UTF-16LE BOM settings both lock transcripts",
    fn() {
      for (const encoding of ["utf8", "utf16le"]) for (const unattended of [false, true]) {
        const r = probe(SHAPES[0][1], ROWS[0], {
          env: unattended ? UN : {}, prep: (s) => writeFileSync(s.bf, '\ufeff{"transcripts":"block"}', encoding),
        });
        locked(r, "blocked", "youtube", LIMIT, unattended);
      }
    },
  },
  {
    id: "TL-polluted-env", desc: "every YouTube table row ignores local keys and fake executable files",
    fn() {
      const s = session();
      try {
        for (const name of ["whisper-cli.exe", "whisper", "yt-dlp.exe"]) writeFileSync(join(s.dir, name), "fixture");
        const preload = join(s.dir, "env-proof.mjs");
        writeFileSync(preload,
          'if (Object.keys(process.env).some((k) => k.toLowerCase() === "groq_api_key") || process.env.PATH !== "") throw new Error("environment was not cleared");\n');
        const cleared = s.run(SHAPES[0][1], {
          ...NOLOCAL, env: { ...NOLOCAL.env, gRoQ_aPi_KeY: "x" }, node: ["--import", pathToFileURL(preload).href],
        });
        assert(cleared.exit === 0 && cleared.raw === "" && s.state().spent === 3, "shared NOLOCAL clears mixed-case keys and empties PATH", cleared);
        for (const row of ROWS) for (const env of [{}, UN]) {
          const clean = probe(SHAPES[0][1], row, { env });
          const p = session().seed({ spent: 0 });
          try {
            prepare(p, row);
            const polluted = p.run(SHAPES[0][1], { env: { ...env, GROQ_API_KEY: "x", OPENAI_API_KEY: "x", PATH: s.dir } });
            assert(clean.decision === polluted.decision && clean.message === polluted.message && clean.state.spent === p.state().spent,
              `${row.id}: local availability cannot change the decision`, polluted);
          } finally { p.cleanup(); }
        }
      } finally { s.cleanup(); }
    },
  },
  {
    id: "TL-no-detection", desc: "guard has no local provider or executable detection",
    fn() {
      const src = readFileSync(GUARD, "utf8");
      assert(!/GROQ|OPENAI|whisper/.test(src), "no provider or local speech tooling detection");
      const permitted = '" Use the 1-credit subtitles endpoint, or free yt-dlp captions if yt-dlp is installed."';
      assert(src.split(permitted).length === 2 && !/yt-dlp/.test(src.replace(permitted, "")), "only the deny message mentions the free captions tool");
      assert(!/process\s*\.\s*env\s*(?:\.\s*PATH|\[\s*["']PATH["']\s*\])/.test(src), "no PATH read");
    },
  },
  {
    id: "TL-hunt-shapes", desc: "malformed escapes, include whitespace and arrays, and whole paths cannot bypass the lock",
    fn() {
      const encoded = TSCRIPT.slice(0, -1) + "%74";
      const cases = [
        ["bolt", `prism/video-intel?url=a&x=%zz&include=${encoded}`, undefined, true],
        ["bolt", `prism/video-intel?url=a&x=100%&include=full,${encoded}`, undefined, true],
        [`param:${TSCRIPT}`, `prism/video-intel?url=a&x=%zz&include=%26${TSCRIPT}`, undefined, true],
        [`param:${TSCRIPT}`, `prism/video-intel?url=a&include=full%26${TSCRIPT}`],
        ...["%c3%89%54", "%ff%54"].map((run) => ["bolt", `prism/video-intel?url=a&x=%zz&include=${run}${TSCRIPT.slice(1)}`, undefined, true]),
        ...["full,%20", "%20", "full,%09"].map((prefix) => ["bolt", `prism/video-intel?url=a&include=${prefix}${TSCRIPT}`]),
        ...["%5B%5D", "%5B0%5D", "%5B%5D%5B%5D", "%5Ba%5D%5Bb%5D"].map((suffix) => ["bolt", `prism/video-intel?url=a&include${suffix}=${TSCRIPT}`]),
        ["bolt", `prism/video-intel?url=a;include=${TSCRIPT}`],
        ...[";", ":", "~", ",", "@"].map((sep) => ["youtube", `youtube/video${sep}x/${TSCRIPT}?id=a`]),
        ["other", `tiktok/post;x/${TSCRIPT}?url=X`],
        ["batch", `youtube/${TSCRIPT}s;x`, "POST"],
        ["batch", `youtube/${TSCRIPT}s,x?ids=a`],
      ];
      for (const [shape, path, method, malformed] of cases) for (const unattended of [false, true]) {
        const cmd = method === "POST" ? `curl -X POST "${V1}${path}" -d '{}'` : `curl -s "${V1}${path}"`;
        const env = unattended ? UN : {};
        if (malformed) {
          for (const row of [ROWS[3], ROWS[2], ROWS[0]]) notPlain(probe(cmd, row, { env }));
          continue;
        }
        locked(probe(cmd, ROWS[3], { env }), "blocked", shape, LIMIT, unattended);
        const r = probe(cmd, { value: { transcripts: "allow", sessionBudget: 1000 } }, { env });
        assert(r.exit === 0 && r.decision === null && r.raw === "" && r.state.spent > 0,
          `${path}: allow silently counts the call`, r);
        assert(r.rec.length === 1 && r.rec[0].decision === "pass" && r.rec[0].kind === "under-cap", "one under-cap record", r);
        if (shape.startsWith("param:")) assert(r.state.spent === 15, "decoded name gate still commits exactly 15", r);
        if (shape !== "bolt") assert(r.state.spent >= 10, "a whole-path gate retains at least the fallback band", r);
      }
      for (const [path, spent, changed] of [
        ["prism/video-intel?url=a&include=full", 15],
        ["prism/video-intel?url=a&x=%zz", 15, "not-plain"],
        ["youtube/video/subtitles?id=abc", 1],
        ["amazon/shop?q=a%20b", 1],
        ["amazon/shop?q=a&x=%zz&deep_scan=%74rue", 15, "not-plain"],
        [`prism/video-intel?url=a&include%20=${TSCRIPT}`, 15, "bolt"],
        [`prism/video-intel?url=a&include%5B=${TSCRIPT}`, 15, "bolt"],
        [`prism/video-intel?url=a&include=${TSCRIPT.slice(0, -1)}%2574`, 15, "bolt"],
      ]) for (const env of [{}, UN]) {
        const r = probe(`curl -s "${V1}${path}"`, ROWS[3], { env });
        if (changed === "not-plain") { notPlain(r); continue; }
        if (changed === "bolt") {
          locked(r, "blocked", "bolt", LIMIT, env === UN);
          const allowed = probe(`curl -s "${V1}${path}"`, ROWS[2], { env });
          assert(allowed.exit === 0 && allowed.raw === "" && allowed.state.spent === spent,
            `${path}: normalised include keeps its exact allowed count`, allowed);
          continue;
        }
        assert(r.exit === 0 && r.decision === null && r.raw === "" && r.state.spent === spent,
          `${path}: non-gated control keeps its count under block`, r);
      }
    },
  },
  {
    id: "TL-newly-gated-count", desc: "every gate retains at least the ungated worst case",
    fn(guard) {
      const cases = [
        ["bolt", `prism/leads?query=x&include=%20${TSCRIPT}`, 50],
        ["bolt", `prism/leads?query=x&y=%zz&include=${TSCRIPT.slice(0, -1)}%74`, 50, true],
        ["other", `prism/leads;x/${TSCRIPT}?query=x`, 50],
        ["other", `prism/no-such;${TSCRIPT}?h=a`, 50],
        ["other", `youtube;x/${TSCRIPT}s?ids=a`, 50],
        ["youtube", `youtube/video;x/${TSCRIPT}?id=a`, 10],
        ["other", `amazon/shop;${TSCRIPT}?q=a`, 10],
        ["bolt", `prism/leads?query=x&include=${TSCRIPT}`, 50],
        ["youtube", `youtube/video/${TSCRIPT}?id=a`, 3],
        ["bolt", `prism/video-intel?url=a&include=full,%20${TSCRIPT}`, 15],
      ];
      for (const [shape, path, spent, malformed] of cases) for (const unattended of [false, true]) {
        const cmd = `curl -s "${V1}${path}"`;
        const env = unattended ? UN : {};
        if (malformed) {
          for (const row of [ROWS[3], ROWS[2], ROWS[0]]) notPlain(probe(cmd, row, { env, guard }));
          continue;
        }
        locked(probe(cmd, ROWS[3], { env, guard }), "blocked", shape, LIMIT, unattended);
        const r = probe(cmd, { value: { transcripts: "allow", sessionBudget: 1000 } }, { env, guard });
        assert(r.exit === 0 && r.decision === null && r.raw === "" && r.state.spent === spent,
          `${path}: exact committed figure ${spent}`, r);
        assert(r.rec.length === 1 && r.rec[0].kind === "under-cap" && r.rec[0].committed === spent,
          "one call record carries the exact committed figure", r);
      }
    },
  },
  {
    id: "TL-long-command", desc: "oversized commands deny before parsing; commands at the cap keep their exact counts",
    fn(guard) {
      const prefix = `${V1}prism/video-intel?url=a&`;
      const url = (prefix + "?include=".repeat(Math.ceil(300000 / 9))).slice(0, 300000);
      const denied = (r, message = M_NOTPLAIN, unattended = false) => {
        assert(r.exit === 0 && r.stderr === "" && r.decision === "deny" && r.message === message,
          "oversized command gets the exact not-plain deny", r);
        assert(r.unchanged && !r.stateWritten && r.rec.length === 0,
          "oversized command leaves state unchanged and writes no call record", r);
        assert(r.log.length === (unattended ? 1 : 0), "only unattended writes one log line", r);
        if (unattended) {
          const log = r.log[0];
          assert(JSON.stringify(Object.keys(log)) === JSON.stringify(FIELDS) && log.decision === "deny" &&
            log.kind === "not-plain" && log.cmdWorst === 0 && JSON.stringify(log.paths) === "[]" &&
            log.committed === null && log.cap === null, "oversized deny has the zero-cost unattended shape", r);
        }
      };
      const counted = (r) => {
        assert(r.exit === 0 && r.stderr === "" && r.decision === null && r.raw === "" && r.state.spent === 15,
          "command at exactly 65536 characters silently commits 15", r);
        assert(r.rec.length === 1 && r.rec[0].decision === "pass" && r.rec[0].kind === "under-cap" &&
          r.rec[0].worst === 15 && r.rec[0].committed === 15, "one record commits exactly 15", r);
      };
      for (const unattended of [false, true]) {
        const r = probe(`curl -s "${url}"`, ROWS[3], { env: unattended ? UN : {}, guard });
        console.log(`    300 KB include query (${unattended ? "unattended" : "attended"}): ${r.ms} ms`);
        denied(r, M_NOTPLAIN, unattended);
        assert(r.ms < 2000, "the 300 KB include query completes under 2000 ms", r);
      }
      const tail = `# ${"a".repeat(70000)}\n${SHAPES[0][1]}`;
      for (const row of [ROWS[3], ROWS[2], ROWS[0]]) for (const unattended of [false, true]) {
        denied(probe(tail, row, { env: unattended ? UN : {}, guard }), M_NOTPLAIN, unattended);
      }
      for (const unattended of [false, true]) {
        denied(probe(`curl -s "${url.toUpperCase()}"`, ROWS[3], {
          env: unattended ? UN : {}, guard, extra: { tool_name: "PowerShell" },
        }), M_NOTBASH, unattended);
      }
      const start = `curl -s "${prefix}x=`;
      const exact = start + "a".repeat(65536 - start.length - 1) + '"';
      assert(exact.length === 65536, "boundary command is exactly 65536 characters");
      counted(probe(exact, ROWS[3], { guard }));
      denied(probe(exact.slice(0, -1) + 'a"', ROWS[3], { guard }));
      const pathological = `curl -s "${url.slice(0, 65536 - 'curl -s ""'.length)}"`;
      assert(pathological.length === 65536, "pathological control is exactly 65536 characters");
      const r = probe(pathological, ROWS[3], { guard });
      console.log(`    65536-character include command: ${r.ms} ms`);
      counted(r);
      assert(r.ms < 2000, "the include command at the cap completes under 2000 ms", r);
      const getTail = `${SHAPES[0][1]} ; echo -`;
      const slowGet = getTail + "G".repeat(65536 - getTail.length - 1) + ".";
      assert(slowGet.length === 65536, "GET-flag failure command is exactly 65536 characters");
      for (const env of [{}, UN]) {
        const g = probe(slowGet, ROWS[3], { env, guard });
        console.log(`    65536-character GET-flag failure: ${g.ms} ms`);
        assert(g.exit === 0 && g.stderr === "" && g.decision === "deny" && g.message === M_NOTPLAIN &&
          g.unchanged && !g.stateWritten && g.rec.length === 0, "GET-flag failure retains the exact not-plain deny", g);
        assert(g.ms < 2000, "GET-flag failure at the cap completes under 2000 ms", g);
      }
      for (const flag of ["-sG", "-G", "-Gx=1"]) {
        const g = probe(`curl ${flag} "${V1}web/sessions"`, ROWS[3], { guard });
        assert(g.exit === 0 && g.decision === "deny" && g.message === M_NOTPLAIN &&
          g.unchanged && !g.stateWritten && g.rec.length === 0, `${flag} stays outside the plain grammar`, g);
      }
      for (const [cmd, expected] of [
        [`curl -s "${V1}web/sessions"`, 0],
        [`curl -s "${V1}web/sessions" -d '{}'`, 20],
        [`curl -s "${V1}web/sessions" -d 'a -Gx=1 b'`, 20],
        [`curl -s "${V1}web/sessions" -d 'a -G1 b'`, 20],
        [`curl -X GET "${V1}web/sessions" -d '{}'`, 0],
      ]) {
        const g = probe(cmd, ROWS[3], { guard });
        assert(g.exit === 0 && g.stderr === "" && g.raw === "" && g.decision === null && g.state.spent === expected,
          `plain verb control retains its exact ${expected}-credit count`, g);
        assert(g.rec.length === 1 && g.rec[0].decision === "pass" && g.rec[0].kind === "under-cap" &&
          g.rec[0].worst === expected && g.rec[0].committed === expected, "plain verb control retains its recording behaviour", g);
      }
      const harmless = `echo ${"a".repeat(70000 - "echo ".length)}`;
      const h = probe(harmless, ROWS[3], { guard });
      assert(h.exit === 0 && h.stderr === "" && h.raw === "" && h.unchanged && !h.stateWritten &&
        h.rec.length === 0 && h.log.length === 0, "long command without the domain passes untouched", h);
    },
  },
  {
    id: "TL-tool-use-id", desc: "validated tool use id is the last call-record key; unattended fields stay unchanged",
    fn() {
      for (const value of ["toolu_01AbC-x_9", undefined, "", 7, "x".repeat(128), "x".repeat(129), "a b"]) {
        for (const deny of [false, true]) for (const unattended of [false, true]) {
          const r = probe(SHAPES[0][1], deny ? ROWS[3] : ROWS[2], {
            env: unattended ? UN : {}, extra: value === undefined ? {} : { tool_use_id: value },
          });
          const want = value === "toolu_01AbC-x_9" || value === "x".repeat(128) ? value : null;
          const rec = r.rec[0];
          assert(r.rec.length === 1 && rec.decision === (deny ? "deny" : "pass") && Object.keys(rec).at(-1) === "tool_use_id" && rec.tool_use_id === want,
            "one record ends with the validated tool use id or null", r);
          assert(r.log.length === (unattended ? 1 : 0), "attendance log count", r);
          if (unattended) assert(JSON.stringify(Object.keys(r.log[0])) === JSON.stringify(FIELDS), "unattended key list is unchanged", r);
        }
      }
    },
  },
];
