/* G2: helper save and route contracts, real child processes in disposable homes, offline. */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, dirname, join } from "node:path";
import { GUARD, V1, TSCRIPT, NOLOCAL, assert, assertCounted, mTranscript, run, session } from "../lib.mjs";

const HELPER = join(dirname(GUARD), "mod", "helper.mjs");
const SAVE = "budget" + "-write";
const DEAD = "http://127.0.0.1:9";
const SEED = { sessionBudget: 750, note: "hand-set ü", extra: { a: [1, 2.5, null] }, transcripts: "allow" };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const own = (o, k) => Object.hasOwn(o, k);

function scratch(fn) {
  const home = mkdtempSync(join(tmpdir(), "sc-helper-"));
  try { fn(home); } finally { rmSync(home, { recursive: true, force: true }); }
}
const bf = (home) => join(home, "revxl", "socialcrawl-budget.json");
function seed(home, obj = SEED) {
  mkdirSync(join(home, "revxl"), { recursive: true });
  writeFileSync(bf(home), JSON.stringify(obj));
}
function invoke(home, args, overrides = {}) {
  const env = { ...process.env };
  for (const k of Object.keys(env)) {
    if (/^(.*_api_key|no_proxy|sc_revxl_home|home|userprofile|path|node_options)$/i.test(k)) delete env[k];
  }
  Object.assign(env, {
    HOME: home, USERPROFILE: home, SC_REVXL_HOME: join(home, "revxl"),
    TEMP: home, TMP: home, TMPDIR: home, PATH: "",
    HTTPS_PROXY: DEAD, HTTP_PROXY: DEAD, ALL_PROXY: DEAD, NODE_USE_ENV_PROXY: "1",
  }, overrides);
  const r = spawnSync(process.execPath, [HELPER, ...args], { env, cwd: home, encoding: "utf8", timeout: 20000 });
  assert(r.status === 0, "helper exits 0");
  assert(r.stderr === "", "helper has no stderr");
  assert(r.stdout.endsWith("\n") && r.stdout.split("\n").length === 2, "helper prints exactly one JSON line");
  return { json: JSON.parse(r.stdout), out: r.stdout, err: r.stderr };
}
function save(home, obj) {
  const r = invoke(home, [SAVE, join(home, "revxl"), JSON.stringify(obj)]).json;
  const file = JSON.parse(readFileSync(bf(home), "utf8"));
  assert(r.ok === true && same(r.budget, file), "successful readback equals file");
  assert(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(file.updatedAt), "whole-second timestamp");
  assert(file.updatedBy === "socialcrawl-budget-pane" && !own(file, "routines"), "owner set and routines dropped");
  assert(same(readdirSync(join(home, "revxl")).sort(), ["socialcrawl-budget.json"]), "no temporary file remains");
  return file;
}
function kept(file) {
  for (const key of ["note", "extra"]) assert(same(file[key], SEED[key]), "unowned value preserved");
}
function routes(home, path, expected, extra = {}) {
  const r = invoke(home, ["routes"], { PATH: path, ...extra });
  assert(same(r.json, { ok: true, routes: expected }), "routes equal ordered labels");
  for (const folder of path.split(delimiter).filter(Boolean)) {
    assert(!r.out.includes(folder) && !r.err.includes(folder), "no PATH folder printed");
  }
  return r;
}

function lockDriver(s, preload, body) {
  const loader = join(s.dir, "preload.mjs");
  const driver = join(s.dir, "driver.mjs");
  writeFileSync(loader, preload);
  writeFileSync(driver, `
    import { spawn } from "node:child_process";
    import { readFileSync, writeFileSync, unlinkSync } from "node:fs";
    import { pathToFileURL } from "node:url";
    import assert from "node:assert/strict";
    const helper = ${JSON.stringify(HELPER)};
    const root = ${JSON.stringify(s.revxl)};
    const file = ${JSON.stringify(s.bf)};
    const loader = ${JSON.stringify(loader)};
    const children = [];
    function start(choice) {
      const child = spawn(process.execPath, ["--import", pathToFileURL(loader).href, helper,
        ${JSON.stringify(SAVE)}, root, JSON.stringify(choice)], {
        stdio: ["ignore", "pipe", "pipe", "ipc"],
      });
      let out = "", err = "";
      child.stdout.on("data", (b) => { out += b; });
      child.stderr.on("data", (b) => { err += b; });
      const done = new Promise((resolve, reject) => {
        child.on("error", reject);
        child.on("close", (code) => {
          try {
            assert.equal(code, 0, "child exits 0");
            assert.equal(err, "", "child has no stderr");
            assert.equal(out.split("\\n").length, 2, "child prints one JSON line");
            resolve(JSON.parse(out));
          } catch (e) { reject(e); }
        });
      });
      done.catch(() => {});
      children.push({ child, done });
      return { child, done };
    }
    const deadline = setTimeout(() => {
      for (const { child } of children) child.kill();
      process.exitCode = 1;
    }, 15000);
    try { ${body} }
    finally {
      clearTimeout(deadline);
      for (const { child } of children) if (child.exitCode === null) child.kill();
      await Promise.allSettled(children.map(({ done }) => done));
    }
  `);
  const env = { ...process.env };
  for (const k of Object.keys(env)) {
    if (/^(.*_api_key|no_proxy|sc_revxl_home|home|userprofile|path|node_options)$/i.test(k)) delete env[k];
  }
  Object.assign(env, {
    HOME: s.dir, USERPROFILE: s.dir, SC_REVXL_HOME: s.revxl,
    TEMP: s.dir, TMP: s.dir, TMPDIR: s.dir, PATH: "",
    HTTPS_PROXY: DEAD, HTTP_PROXY: DEAD, ALL_PROXY: DEAD, NODE_USE_ENV_PROXY: "1",
  });
  const r = spawnSync(process.execPath, [driver], { env, cwd: s.dir, encoding: "utf8", timeout: 20000 });
  assert(r.status === 0 && r.stderr === "", `lock driver succeeds: ${r.stderr || r.error || r.status}`);
  return JSON.parse(r.stdout);
}

export default [
  {
    id: "HG2-lock-busy",
    desc: "fresh locks refuse both save shapes without changing the budget or removing another saver lock",
    fn() {
      for (const choice of [{ sessionBudget: 300 }, { transcripts: "block" }]) {
        const s = session();
        try {
          s.budget(SEED);
          const before = readFileSync(s.bf);
          const lock = `${s.bf}.save.lock`;
          writeFileSync(lock, "another saver");
          const start = performance.now();
          const r = invoke(s.dir, [SAVE, s.revxl, JSON.stringify(choice)]);
          const ms = performance.now() - start;
          assert(r.out === '{"ok":false,"reason":"busy"}\n', "exact busy response");
          assert(ms >= 1500 && ms < 6000, `bounded lock wait: ${ms} ms`);
          assert(readFileSync(s.bf).equals(before), "busy leaves budget byte-identical");
          assert(readFileSync(lock, "utf8") === "another saver", "other saver lock remains");
          assert(!readdirSync(s.revxl).some((name) => name.endsWith(".tmp")), "busy leaves no temporary file");
        } finally { s.cleanup(); }
      }
    },
  },
  {
    id: "HG2-lock-stale",
    desc: "an eleven-second-old lock is broken and the save succeeds without a lock wait",
    fn() {
      const s = session();
      try {
        s.budget(SEED);
        const lock = `${s.bf}.save.lock`;
        writeFileSync(lock, "stale saver");
        const old = new Date(Date.now() - 11000);
        utimesSync(lock, old, old);
        const start = performance.now();
        const r = invoke(s.dir, [SAVE, s.revxl, '{"sessionBudget":300}']).json;
        const file = JSON.parse(readFileSync(s.bf, "utf8"));
        assert(r.ok === true && same(r.budget, file), "stale recovery succeeds with matching readback");
        assert(performance.now() - start < 1500, "stale lock does not wait for timeout");
        assert(file.sessionBudget === 300 && file.transcripts === "allow", "stale recovery writes merged file");
        assert(!existsSync(lock), "stale recovery releases lock");
      } finally { s.cleanup(); }
    },
  },
  {
    id: "HG2-lock-released",
    desc: "success and write failure release locks; invalid input creates no root or lock",
    fn() {
      const s = session();
      try {
        const guardLock = `${s.bf}.lock`;
        const guardBytes = Buffer.from("existing guard lock\n");
        writeFileSync(guardLock, guardBytes);
        const old = new Date(Date.now() - 24 * 60 * 60 * 1000);
        utimesSync(guardLock, old, old);
        const guardMtime = statSync(guardLock).mtimeMs;
        assert(invoke(s.dir, [SAVE, s.revxl, '{"sessionBudget":300}']).json.ok === true, "ordinary save succeeds");
        assert(existsSync(guardLock) && readFileSync(guardLock).equals(guardBytes), "successful save preserves guard lock bytes");
        assert(statSync(guardLock).mtimeMs === guardMtime, "successful save preserves guard lock mtime");
        assert(!existsSync(`${s.bf}.save.lock`), "success releases lock");
        const r = invoke(s.dir, [SAVE, s.revxl, '{}']);
        assert(r.out === '{"ok":false,"reason":"invalid"}\n' && !existsSync(`${s.bf}.save.lock`), "invalid leaves no lock");
        rmSync(s.revxl, { recursive: true, force: true });
        assert(invoke(s.dir, [SAVE, s.revxl, '{}']).out === '{"ok":false,"reason":"invalid"}\n', "missing-root invalid response");
        assert(!existsSync(s.revxl), "invalid does not create root");
        mkdirSync(s.bf, { recursive: true });
        assert(invoke(s.dir, [SAVE, s.revxl, '{"sessionBudget":300}']).out === '{"ok":false,"reason":"write"}\n', "folder budget fails write");
        assert(!existsSync(`${s.bf}.save.lock`), "write failure releases lock");
        assert(!readdirSync(s.revxl).some((name) => name.endsWith(".tmp")), "write failure leaves no temporary file");
        rmSync(s.revxl, { recursive: true, force: true });
        writeFileSync(s.revxl, "root is a file");
        assert(invoke(s.dir, [SAVE, s.revxl, '{"sessionBudget":300}']).out === '{"ok":false,"reason":"write"}\n', "root creation failure returns write");
        assert(readFileSync(s.revxl, "utf8") === "root is a file", "root creation failure preserves file");
      } finally { s.cleanup(); }
    },
  },
  {
    id: "HG2-lock-read-inside",
    desc: "a waiting budget saver reads the Block written before its lock is released",
    fn() {
      const s = session();
      try {
        s.budget({ transcripts: "allow", sessionBudget: 750 });
        writeFileSync(`${s.bf}.save.lock`, "fixture holds lock");
        const r = lockDriver(s, `
          import fs from "node:fs";
          import { syncBuiltinESMExports } from "node:module";
          const write = fs.writeFileSync;
          let sent = false;
          fs.writeFileSync = function(path, ...args) {
            try { return write.call(this, path, ...args); }
            catch (e) {
              if (!sent && path === ${JSON.stringify(`${s.bf}.save.lock`)} && e.code === "EEXIST") {
                sent = true;
                process.send("waiting");
              }
              throw e;
            }
          };
          syncBuiltinESMExports();
        `, `
          const saver = start({ sessionBudget: 300 });
          let waiting = false;
          saver.child.on("message", (message) => {
            if (message !== "waiting") return;
            waiting = true;
            writeFileSync(file, JSON.stringify({ transcripts: "block", sessionBudget: 750 }));
            unlinkSync(file + ".save.lock");
          });
          const result = await saver.done;
          assert(waiting, "saver encountered held lock before fixture released it");
          process.stdout.write(JSON.stringify(result));
        `);
        const file = JSON.parse(readFileSync(s.bf, "utf8"));
        assert(r.ok === true && same(r.budget, file), "waiting save succeeds with matching readback");
        assert(file.transcripts === "block" && file.sessionBudget === 300, "read after lock preserves Block and saves budget");
        assert(!existsSync(`${s.bf}.save.lock`), "waiting save releases lock");
      } finally { s.cleanup(); }
    },
  },
  {
    id: "HG2-lock-concurrent",
    desc: "twelve simultaneous pairs preserve every successful Block and always leave valid JSON",
    fn() {
      const s = session();
      try {
        const results = lockDriver(s, `
          await new Promise((resolve) => {
            process.once("message", resolve);
            process.send("ready");
          });
        `, `
          const pairs = [];
          for (let i = 0; i < 12; i++) {
            writeFileSync(file, JSON.stringify({ transcripts: "allow", sessionBudget: 750 }));
            const block = start({ transcripts: "block" });
            const budget = start({ sessionBudget: 300 });
            await Promise.all([block, budget].map(({ child, done }) => Promise.race([
              new Promise((resolve) => child.once("message", (message) => {
                assert.equal(message, "ready");
                resolve();
              })),
              done.then(() => { throw new Error("saver exited before start barrier"); }),
            ])));
            block.child.send("go");
            budget.child.send("go");
            const replies = await Promise.all([block.done, budget.done]);
            pairs.push({ replies, file: JSON.parse(readFileSync(file, "utf8")) });
          }
          process.stdout.write(JSON.stringify(pairs));
        `);
        for (const { replies: [block, budget], file } of results) {
          assert([block, budget].every((r) => r.ok === true || same(r, { ok: false, reason: "busy" })), "only success or busy responses");
          assert(block.ok === true || budget.ok === true, "at least one save succeeds");
          if (block.ok === true) assert(file.transcripts === "block", "successful pair preserves Block on disk");
          if (budget.ok === true) assert(file.sessionBudget === 300, "successful pair preserves budget on disk");
        }
        assert(!existsSync(`${s.bf}.save.lock`), "concurrent saves release lock");
      } finally { s.cleanup(); }
    },
  },
  {
    id: "HG2-transcripts-only",
    desc: "transcripts-only saves preserve the budget and unrelated values, including absent budget",
    fn() { scratch((home) => {
      seed(home);
      const file = save(home, { transcripts: "block" });
      assert(file.transcripts === "block" && own(file, "sessionBudget") && same(file.sessionBudget, SEED.sessionBudget), "budget unchanged");
      kept(file);
      const { sessionBudget, ...without } = SEED;
      seed(home, { ...without, routines: { enabled: true } });
      assert(!own(save(home, { transcripts: "block" }), "sessionBudget"), "absent budget stays absent");
    }); },
  },
  {
    id: "HG2-budget-only",
    desc: "budget saves and deletion preserve transcripts, including its absence",
    fn() { scratch((home) => {
      seed(home);
      let file = save(home, { sessionBudget: 250 });
      assert(file.sessionBudget === 250 && file.transcripts === "allow", "budget updated alone");
      kept(file);
      file = save(home, { sessionBudget: null });
      assert(!own(file, "sessionBudget") && file.transcripts === "allow", "budget deleted alone");
      kept(file);
      const { transcripts, ...without } = SEED;
      seed(home, without);
      assert(!own(save(home, { sessionBudget: 250 }), "transcripts"), "absent transcripts stays absent");
    }); },
  },
  {
    id: "HG2-budget-only-keeps-block",
    desc: "a budget-only save or Automatic preserves a stored block and the exact guard denial",
    fn() {
      const command = `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`;
      for (const choice of [{ sessionBudget: 300 }, { sessionBudget: null }]) {
        const s = session();
        try {
          s.budget({ transcripts: "block", sessionBudget: 750, note: 1 });
          const r = invoke(s.dir, [SAVE, s.revxl, JSON.stringify(choice)]).json;
          const file = JSON.parse(readFileSync(s.bf, "utf8"));
          assert(r.ok === true && same(r.budget, file) && file.transcripts === "block" && file.note === 1,
            "save preserves the stored block and unowned value");
          assert(choice.sessionBudget === null ? !own(file, "sessionBudget") : file.sessionBudget === 300,
            "budget updated or deleted");
          const before = s.stateRaw();
          const denied = s.run(command, NOLOCAL);
          assert(denied.exit === 0 && denied.decision === "deny" && denied.message === mTranscript("blocked", "youtube") &&
            !denied.stateWritten && s.stateRaw() === before, "exact blocked text and unchanged committed state");
        } finally { s.cleanup(); }
      }
    },
  },
  {
    id: "HG2-both",
    desc: "both keys save together, null deletes only budget, new keys use canonical order",
    fn() { scratch((home) => {
      let file = save(home, { transcripts: "block", sessionBudget: 300 });
      assert(file.sessionBudget === 300 && file.transcripts === "block", "both written");
      assert(same(Object.keys(file), ["sessionBudget", "transcripts", "updatedAt", "updatedBy"]), "fresh key order independent of argument order");
      file = save(home, { sessionBudget: null, transcripts: "allow" });
      assert(!own(file, "sessionBudget") && file.transcripts === "allow", "delete budget and allow transcripts");
      seed(home, { note: "kept" });
      file = save(home, { transcripts: "block", sessionBudget: 300 });
      assert(same(Object.keys(file), ["note", "sessionBudget", "transcripts", "updatedAt", "updatedBy"]), "both new keys ordered on existing file");
    }); },
  },
  {
    id: "HG2-invalid",
    desc: "invalid or missing arguments leave the seeded file byte-identical",
    fn() { scratch((home) => {
      seed(home);
      const before = readFileSync(bf(home));
      const bad = ['{}', '{"transcripts":"Block"}', '{"transcripts":""}', '{"transcripts":null}', '{"transcripts":true}',
        '{"transcripts":1}', '{"transcripts":"block","x":1}', '{"sessionBudget":0,"transcripts":"block"}',
        '{"sessionBudget":500,"transcripts":"maybe"}', '{"sessionBudget":500,"transcripts":"block","routines":{}}',
        '[]', '["transcripts"]', 'null', '"block"', 'not json'];
      const args = bad.map((text) => [SAVE, join(home, "revxl"), text]);
      args.push([SAVE, join(home, "revxl")], [SAVE], [SAVE, "", '{"transcripts":"block"}']);
      for (const a of args) {
        const r = invoke(home, a);
        assert(r.out === '{"ok":false,"reason":"invalid"}\n', "exact invalid response");
        assert(readFileSync(bf(home)).equals(before), "invalid save writes nothing");
        assert(same(readdirSync(join(home, "revxl")), ["socialcrawl-budget.json"]), "no extra file");
      }
    }); },
  },
  {
    id: "HG2-guard-reads-it",
    desc: "guard reads the helper's transcript setting: block denies, allow counts",
    fn() {
      const s = session();
      try {
        const command = `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`;
        assert(invoke(s.dir, [SAVE, s.revxl, '{"transcripts":"block"}']).json.ok, "block saved");
        const denied = s.run(command, NOLOCAL);
        assert(denied.exit === 0 && denied.decision === "deny" && denied.message === mTranscript("blocked", "youtube") && !denied.stateWritten, "exact blocked YouTube deny");
        assert(invoke(s.dir, [SAVE, s.revxl, '{"transcripts":"allow"}']).json.ok, "allow saved");
        const allowed = s.run(command, NOLOCAL);
        assertCounted({ ...allowed, state: s.state() }, 3, "allowed transcript");
      } finally { s.cleanup(); }
    },
  },
  {
    id: "HG2-garbled-keeps-block",
    desc: "budget-only repairs keep unreadable settings blocked; explicit allow wins; valid and missing files keep their meaning",
    fn() {
      const command = `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`;
      const be = Buffer.concat([Buffer.from([0xfe, 0xff]), Buffer.from('{"transcripts":"block"}', "utf16le").swap16()]);
      const bad = ['{"transcripts":"block","sessionBudget":', '', '[{"transcripts":"block"}]',
        'null', '"block"', '7', 'not json {', be, 'true', 'false'];
      const deny = (s, lead) => {
        const before = s.stateRaw();
        const r = s.run(command, NOLOCAL);
        assert(r.exit === 0 && r.decision === "deny" && r.message === mTranscript(lead, "youtube"), `exact ${lead} YouTube deny`);
        assert(!r.stateWritten && s.stateRaw() === before, "denial leaves committed state unchanged");
      };
      for (const content of bad) {
        for (const choice of [{ sessionBudget: 300 }, { sessionBudget: null }, { transcripts: "block" },
          { transcripts: "allow" }, { sessionBudget: 300, transcripts: "allow" }]) {
          const s = session();
          try {
            writeFileSync(s.bf, content);
            deny(s, "unreadable");
            const r = invoke(s.dir, [SAVE, s.revxl, JSON.stringify(choice)]).json;
            const file = JSON.parse(readFileSync(s.bf, "utf8"));
            assert(r.ok === true && same(r.budget, file), "repair succeeds with matching readback");
            const keys = choice.sessionBudget === 300
              ? ["sessionBudget", "transcripts", "updatedAt", "updatedBy"]
              : ["transcripts", "updatedAt", "updatedBy"];
            assert(same(Object.keys(file), keys), "repaired file key order");
            assert(choice.sessionBudget === 300 ? file.sessionBudget === 300 : !own(file, "sessionBudget"), "budget saved or absent");
            assert(file.transcripts === (choice.transcripts || "block"), "repair preserves block unless argument permits");
            if (choice.transcripts === "allow") {
              assertCounted({ ...s.run(command, NOLOCAL), state: s.state() }, 3, "explicit allow after repair");
            } else {
              deny(s, "blocked");
            }
          } finally { s.cleanup(); }
        }
      }
      for (const [content, keys, lead] of [
        [undefined, ["sessionBudget", "updatedAt", "updatedBy"], null],
        [{ note: 1 }, ["note", "sessionBudget", "updatedAt", "updatedBy"], null],
        [{ transcripts: "Block" }, ["transcripts", "sessionBudget", "updatedAt", "updatedBy"], "unrecognised"],
      ]) {
        const s = session();
        try {
          if (content !== undefined) s.budget(content);
          const r = invoke(s.dir, [SAVE, s.revxl, '{"sessionBudget":300}']).json;
          const file = JSON.parse(readFileSync(s.bf, "utf8"));
          assert(r.ok === true && same(r.budget, file) && file.sessionBudget === 300, "control save succeeds");
          assert(same(Object.keys(file), keys), "control key order without added transcript setting");
          if (lead) {
            assert(file.transcripts === "Block", "unrecognised stored value preserved");
            deny(s, lead);
          } else {
            assert(!own(file, "transcripts"), "absent transcripts stays absent");
            if (content) assert(file.note === 1, "unowned control value preserved");
            assertCounted({ ...s.run(command, NOLOCAL), state: s.state() }, 3, "control transcript");
          }
        } finally { s.cleanup(); }
      }
    },
  },
  {
    id: "HG2-folder-transcripts",
    desc: "a folder at the budget path refuses a transcripts save with the exact write response",
    fn() {
      for (const transcripts of ["block", "allow"]) {
        const s = session();
        try {
          mkdirSync(s.bf);
          const r = invoke(s.dir, [SAVE, s.revxl, JSON.stringify({ transcripts })]);
          assert(r.out === '{"ok":false,"reason":"write"}\n', "exact write failure");
          assert(statSync(s.bf).isDirectory(), "folder remains a folder");
        } finally { s.cleanup(); }
      }
    },
  },
  {
    id: "HG2-routes",
    desc: "all PATH entries, names and suffixes; files only; fixed labels; no key or path disclosure",
    fn() { scratch((home) => {
      const folders = Array.from({ length: 70 }, (_, i) => join(home, `p${i}`));
      folders.forEach((p) => mkdirSync(p));
      writeFileSync(join(folders[69], "whisper-cli.exe"), "");
      routes(home, folders.join(delimiter), ["whisper"]);
      for (const key of ["", "   "]) routes(home, "", [], { GROQ_API_KEY: key });
      const canary = "fixture-groq-canary";
      const r = routes(home, "", ["groq"], { GROQ_API_KEY: canary });
      assert(!r.out.includes(canary) && !r.err.includes(canary), "canary never printed");
      routes(home, "", [], { OPENAI_API_KEY: "fixture-openai-canary" });
      writeFileSync(join(folders[0], "yt-dlp.cmd"), "");
      writeFileSync(join(folders[0], "WhisperX.EXE"), "");
      routes(home, folders[0], ["yt-dlp", "whisper"]);
      routes(home, folders[0], ["yt-dlp", "whisper", "groq"], { GROQ_API_KEY: canary });
      mkdirSync(join(folders[1], "whisper"));
      routes(home, folders[1], []);
      // A relative entry would resolve to a matching file if it were incorrectly scanned.
      writeFileSync(join(home, "yt-dlp"), "");
      mkdirSync(join(home, "bin"));
      writeFileSync(join(home, "bin", "yt-dlp.exe"), "");
      const mixed = ["", ".", "bin", "\\\\nohost\\share", "//nohost/share", folders[69], ""].join(delimiter);
      routes(home, mixed, ["whisper"]);
      routes(home, [join(home, "missing"), folders[69]].join(delimiter), ["whisper"]);
      if (process.platform === "win32") {
        writeFileSync(join(folders[3], "yt-dlp.exe"), "");
        routes(home, "\\\\?\\" + folders[3], []);
        routes(home, folders[3], ["yt-dlp"]);
      }
      for (const name of ["yt-dlp", "whisper", "whisper-cli", "whisper.cpp", "faster-whisper", "whisperx"]) {
        for (const suffix of ["", ".exe", ".cmd"]) {
          const file = join(folders[2], name + suffix);
          writeFileSync(file, "");
          routes(home, folders[2], [name === "yt-dlp" ? "yt-dlp" : "whisper"]);
          rmSync(file);
        }
      }
    }); },
  },
  {
    id: "HG2-d38-still-refused",
    desc: "guard still refuses the save step through Bash and PowerShell for both new shapes",
    fn() { scratch((home) => {
      seed(home);
      const message = `SocialCrawl guard file left alone: this command names the pane's budget save step (${SAVE}), which holds the person's ` +
        "SocialCrawl budget or spend record. Claude is not to change it (the guard refuses the plain ways; a glob, a link to the folder, an MCP tool or a script can still get past it); the person sets the limit in SocialCrawl → Settings. To look at it, use the Read tool.";
      for (const json of ['{"transcripts":"block"}', '{"sessionBudget":300,"transcripts":"allow"}']) {
        for (const tool of ["Bash", "PowerShell"]) {
          const command = `${tool === "PowerShell" ? "& " : ""}node "${HELPER}" ${SAVE} "${join(home, "revxl")}" '${json}'`;
          const r = run(command, { extra: { tool_name: tool } });
          assert(r.exit === 0 && r.decision === "deny" && r.message === message, "exact save-step tamper deny");
        }
      }
    }); },
  },
];
