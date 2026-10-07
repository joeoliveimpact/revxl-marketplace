/*
 * R4 B5 — hooks/roster-write.mjs, the entities.jsonl roster writer.
 *
 * The suite's centre of gravity is R1, the ROUND TRIP: the writer writes, and R3's
 * research-suggest hook then FIRES on what it wrote. Writing and reading were specified
 * separately, so "the write succeeded" was never the done-test — a line under the wrong field
 * writes fine, exits 0, and never triggers anything. Only the round trip catches that, so
 * every fixture here that pins a behaviour carries a killing mutation the way suggest.mjs does.
 *
 * Zero credits: the writer has no network code and no key access (R9 asserts that
 * mechanically), and the hook is a pure function of the prompt, costs.json and this file.
 */
import { ask, assert, assertFires, assertSilent, assertMatch } from "../lib-suggest.mjs";
import { run as guardRun, assertDecision } from "../lib.mjs";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, existsSync, rmSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const WRITER = resolve(HERE, "..", "..", "roster-write.mjs");

/** A throwaway SC_REVXL_HOME. Never cleaned up mid-fixture — the assertions read it back. */
function home(nested) {
  const d = mkdtempSync(join(tmpdir(), "sc-roster-test-"));
  return nested ? join(d, "does", "not", "exist") : d;
}

/** One writer invocation against `dir` as SC_REVXL_HOME. `writer` swaps in a mutant copy. */
function write(dir, args, writer) {
  const r = spawnSync(process.execPath, [writer || WRITER, ...args], {
    encoding: "utf8",
    input: "",
    env: { ...process.env, SC_REVXL_HOME: dir },
  });
  return {
    exit: r.status,
    stdout: String(r.stdout || ""),
    stderr: String(r.stderr || ""),
  };
}

const file = (dir) => join(dir, "entities.jsonl");
const readOrNull = (dir) => (existsSync(file(dir)) ? readFileSync(file(dir), "utf8") : null);
const lineCount = (dir) => String(readOrNull(dir) || "").split(/\r?\n/).filter((l) => l.trim()).length;

/** A copy of the writer with one substitution applied. Stdlib-only, so it runs from anywhere. */
function mutate(find, replace) {
  const src = readFileSync(WRITER, "utf8");
  if (!src.includes(find)) {
    throw new Error(`mutation anchor not found in roster-write.mjs: ${JSON.stringify(find)}`);
  }
  const dir = mkdtempSync(join(tmpdir(), "sc-roster-mut-"));
  const dest = join(dir, "roster-write.mjs");
  writeFileSync(dest, src.split(find).join(replace));
  return {
    path: dest,
    cleanup() {
      try {
        rmSync(dir, { recursive: true, force: true });
      } catch {}
    },
  };
}

/**
 * Run `body` against a mutant writer and require it to FAIL. Same contract as suggest.mjs's
 * killedBy, including the load-bearing CONTROL run against a byte-identical copy: without it a
 * body that fails for an unrelated reason reads as a kill and proves nothing.
 */
function killedBy(find, replace, body, what) {
  const control = mutate(find, find);
  try {
    body(control.path);
  } catch (e) {
    throw new Error(
      `BOGUS MUTATION (${what}): the CONTROL — an unmutated copy in the same environment — ` +
        `also failed, so the "kill" measures something other than the mutation: ${e && e.message}`
    );
  } finally {
    control.cleanup();
  }

  const m = mutate(find, replace);
  let survived = false;
  try {
    body(m.path);
    survived = true;
  } catch {
    // the mutant failed the assertions the control passed — exactly what we want
  } finally {
    m.cleanup();
  }
  assert(!survived, `DEAD FIXTURE: the mutation (${what}) did not change the outcome`);
}

export default [
  // ---------------------------------------------------------------- R1: the round trip
  {
    id: "R1-round-trip-writer-to-hook",
    desc: "DONE-TEST (the plan's round trip): the writer writes a handle and research-suggest.mjs then FIRES on it — and stays silent without an intent phrase",
    fn() {
      const probe = (writer) => {
        const dir = home();
        const w = write(dir, ["--handle", "handleZ", "--platform", "instagram", "--source", "research-plays"], writer);
        assert(w.exit === 0, `the writer must exit 0, got ${w.exit}: ${w.stderr}`);
        assert(/roster: added handleZ/.test(w.stdout), `stdout must report the add, got ${JSON.stringify(w.stdout)}`);
        // The half that was never specified until now: the hook must MATCH what was written.
        const r = ask("research what handleZ has been posting lately", { env: { SC_REVXL_HOME: dir } });
        assertFires(r, "a handle written by roster-write.mjs must fire research-suggest.mjs");
        assertMatch(r, /trigger: intent\+roster/, "the trigger class must be the roster one");
        assertMatch(r, /handlez/i, "the matched roster entry must be named");
        // Class-2: the same handle with NO intent phrase stays silent (Joe's ruling 08.31.26).
        assertSilent(
          ask("what has handleZ been posting lately", { env: { SC_REVXL_HOME: dir } }),
          "the roster is a co-occurrence signal, not a standalone shape"
        );
      };
      probe();
      // The exact silent failure this slice exists to prevent: a valid-looking JSONL line
      // under a field the reader does not consult. It writes, it exits 0, it never fires.
      killedBy(
        "            handle,\n",
        "            who: handle,\n",
        probe,
        "write the handle under a field research-suggest.mjs does not match"
      );
    },
  },

  // ---------------------------------------------------------------- R2: @ stripping
  {
    id: "R2-at-prefix-is-stripped-on-write",
    desc: "`--handle @Foo` stores `Foo`, and both `research @foo` and `research foo` fire on it",
    fn() {
      const probe = (writer) => {
        const dir = home();
        assert(write(dir, ["--handle", "@Foo"], writer).exit === 0, "writing @Foo must succeed");
        const body = readOrNull(dir);
        // Asserted on the STORED BYTES, not on firing: the reader strips `@` itself, so an
        // unstripped write still fires and only the file contents can catch it.
        assert(/"handle":"Foo"/.test(body), `the stored handle must be @-free, got ${JSON.stringify(body)}`);
        assert(!body.includes("@"), `no @ may survive into the roster line, got ${JSON.stringify(body)}`);
        assertFires(ask("research @foo lately", { env: { SC_REVXL_HOME: dir } }), "@-prefixed prompt");
        assertFires(ask("research foo lately", { env: { SC_REVXL_HOME: dir } }), "bare prompt");
      };
      probe();
      killedBy(
        'String(s).trim().replace(/^@+/, "")',
        "String(s).trim()",
        probe,
        "stop stripping the leading @ before writing"
      );
    },
  },

  // ---------------------------------------------------------------- R3: dedupe
  {
    id: "R3-dedupe-is-case-insensitive-and-cross-field",
    desc: "the same handle three ways writes ONE line, and a pre-existing bare string or `alias` line counts as present",
    fn() {
      const probe = (writer) => {
        const dir = home();
        assert(write(dir, ["--handle", "Foo"], writer).exit === 0, "first write");
        const second = write(dir, ["--handle", "@foo", "--handle", "FOO"], writer);
        assert(second.exit === 0, "a duplicate is a no-op, not an error");
        assert(/already present/.test(second.stdout), `a duplicate must say so, got ${JSON.stringify(second.stdout)}`);
        assert(lineCount(dir) === 1, `three spellings must leave ONE line, got ${lineCount(dir)}`);

        // Dedupe must cover every shape the READER would extract, not just our own rows.
        const other = home();
        writeFileSync(file(other), '"foo"\n{"alias":"bar"}\n');
        const r = write(other, ["--handle", "Foo", "--handle", "@BAR"], writer);
        assert(r.exit === 0, "writing against pre-existing lines must succeed");
        assert(lineCount(other) === 2, `neither may be re-added, got ${lineCount(other)} lines`);
        assert(
          (r.stdout.match(/already present/g) || []).length === 2,
          `both must report as present, got ${JSON.stringify(r.stdout)}`
        );
      };
      probe();
      killedBy("    if (seen.has(key)) {", "    if (false) {", probe, "drop the dedupe check");
    },
  },

  // ---------------------------------------------------------------- R4: refusals
  {
    id: "R4-refuses-what-the-reader-cannot-match",
    desc: "too short, too long, a URL, or whitespace = exit 1 with a reason on stderr and the file untouched; exactly 3 and exactly 80 characters are ACCEPTED",
    fn() {
      const bad = [
        ["ab", /3-80/, "shorter than the reader's floor"],
        ["x".repeat(81), /3-80/, "longer than the reader's ceiling"],
        ["https://x.com/foo", /URL/, "a URL, which is already its own trigger shape"],
        ["has space", /whitespace/, "not one whole token"],
      ];
      const probe = (writer) => {
        for (const [h, re, why] of bad) {
          const dir = home();
          assert(write(dir, ["--handle", "seedok"], writer).exit === 0, "seed");
          const before = readOrNull(dir);
          const r = write(dir, ["--handle", h], writer);
          assert(r.exit === 1, `${why}: must exit 1, got ${r.exit} (stdout ${JSON.stringify(r.stdout)})`);
          assert(r.stderr.trim() !== "", `${why}: a refusal must say why on stderr`);
          assert(re.test(r.stderr), `${why}: stderr must name the rule, got ${JSON.stringify(r.stderr)}`);
          assert(readOrNull(dir) === before, `${why}: a refusal must leave the file byte-identical`);
        }
        // The boundaries themselves are legal — the check must refuse OUTSIDE the range only.
        for (const ok of ["abc", "y".repeat(80)]) {
          const dir = home();
          const r = write(dir, ["--handle", ok], writer);
          assert(r.exit === 0, `a ${ok.length}-character handle is legal, got exit ${r.exit}: ${r.stderr}`);
          assert(lineCount(dir) === 1, `a ${ok.length}-character handle must be written`);
        }
      };
      probe();
      killedBy(
        "    if (h.length < 3 || h.length > 80)",
        "    if (false)",
        probe,
        "drop the length check the reader's 3-80 window requires"
      );
    },
  },

  // ---------------------------------------------------------------- R5: the 2000-line cap
  {
    id: "R5-refuses-past-the-readers-2000-line-window",
    desc: "a full roster is refused by name (2000) rather than appended invisibly — and the reader is shown to be blind past that line",
    fn() {
      const seed = (dir) => {
        mkdirSync(dir, { recursive: true });
        const rows = [];
        for (let i = 0; i < 2000; i++) rows.push(JSON.stringify({ handle: `seed${String(i).padStart(4, "0")}` }));
        writeFileSync(file(dir), rows.join("\n") + "\n");
      };
      const probe = (writer) => {
        const dir = home();
        seed(dir);
        const before = readOrNull(dir);
        const r = write(dir, ["--handle", "capoverflow"], writer);
        assert(r.exit === 1, `a full roster must be refused, got exit ${r.exit}`);
        assert(/2000/.test(r.stderr), `the refusal must name the reader's 2000-line window, got ${JSON.stringify(r.stderr)}`);
        assert(readOrNull(dir) === before, "a refused write must leave the file byte-identical");
      };
      probe();

      // WHY the cap is a refusal and not a warning: the same entry, appended by hand past the
      // window, is invisible. The `fires` half is the control — it proves the silence below
      // comes from the POSITION of the line, not from a roster that failed to load at all.
      const shown = home();
      seed(shown);
      writeFileSync(file(shown), readFileSync(file(shown), "utf8").split("\n").slice(0, 10).join("\n") + '\n{"handle":"capoverflow"}\n');
      assertFires(
        ask("research what capoverflow is posting", { env: { SC_REVXL_HOME: shown } }),
        "inside the window the entry fires"
      );
      const hidden = home();
      seed(hidden);
      writeFileSync(file(hidden), readFileSync(file(hidden), "utf8") + '{"handle":"capoverflow"}\n');
      assertSilent(
        ask("research what capoverflow is posting", { env: { SC_REVXL_HOME: hidden } }),
        "past line 2000 the entry is invisible to the reader — which is what the refusal prevents"
      );

      killedBy(
        "  if (held + toWrite.length > MAX_LINES)",
        "  if (false)",
        probe,
        "drop the cap and append a line the reader will never see"
      );
    },
  },

  // ---------------------------------------------------------------- R6: hostile file states
  {
    id: "R6-missing-dir-empty-file-and-corrupt-neighbour",
    desc: "the directory is created if absent, an empty file is fine, and a corrupt neighbouring line does not stop the new handle firing",
    fn() {
      const probe = (writer) => {
        const missing = home(true);
        assert(!existsSync(missing), "precondition: the directory must not exist yet");
        assert(write(missing, ["--handle", "freshdir"], writer).exit === 0, "a missing directory must be created");
        assert(existsSync(file(missing)), "the roster file must exist after the write");

        const empty = home();
        writeFileSync(file(empty), "");
        assert(write(empty, ["--handle", "emptyfile"], writer).exit === 0, "an empty file must be appendable");
        assertFires(
          ask("research what emptyfile is posting", { env: { SC_REVXL_HOME: empty } }),
          "the handle written into an empty file"
        );

        const corrupt = home();
        writeFileSync(file(corrupt), "{not json at all\n");
        assert(write(corrupt, ["--handle", "goodneighbour"], writer).exit === 0, "a corrupt line must be tolerated");
        assertFires(
          ask("research what goodneighbour is posting", { env: { SC_REVXL_HOME: corrupt } }),
          "one bad line must not cost the good one"
        );
      };
      probe();
      killedBy(
        '  mkdirSync(dirname(p), { recursive: true });',
        "  /* no mkdir */",
        probe,
        "stop creating the roster directory"
      );
    },
  },

  // ---------------------------------------------------------------- R7: one append, one line
  {
    id: "R7-one-append-call-site-and-a-trailing-newline",
    desc: "MECHANICAL CHECK: the source has exactly ONE appendFileSync call site (whole line or nothing) and every written file ends in a newline",
    fn() {
      const probe = (writer) => {
        const src = readFileSync(writer || WRITER, "utf8");
        const sites = (src.match(/appendFileSync\s*\(/g) || []).length;
        assert(
          sites === 1,
          `a half-written line is a line the reader silently drops, so the row must go out in ONE append — found ${sites} call sites`
        );
        const dir = home();
        assert(write(dir, ["--handle", "newlineok"], writer).exit === 0, "write");
        assert(readOrNull(dir).endsWith("\n"), "the roster file must end in a newline");
        // A file left without a trailing newline must be REPAIRED, not concatenated onto.
        const ragged = home();
        writeFileSync(file(ragged), '{"handle":"ragged"}');
        assert(write(ragged, ["--handle", "secondone"], writer).exit === 0, "write onto a ragged file");
        assert(lineCount(ragged) === 2, `a missing trailing newline must be repaired, got ${JSON.stringify(readOrNull(ragged))}`);
      };
      probe();
      killedBy(
        "    appendFileSync(p, (text",
        '    appendFileSync(p, "");\n    appendFileSync(p, (text',
        probe,
        "split the write across two append call sites"
      );
      killedBy(
        '          }) + "\\n"',
        '          }) + ""',
        probe,
        "drop the row's trailing newline"
      );
    },
  },

  // ---------------------------------------------------------------- R8: the credit guard
  {
    id: "R8-credit-guard-lets-the-writer-through",
    desc: "the credit guard does not prompt on a roster-write command — it spends nothing, so a permission prompt here would be pure friction",
    fn() {
      const r = guardRun(`node "${WRITER}" --handle x`);
      assertDecision(r, null, "a local file write must not carry a permissionDecision");
      assert(r.raw.trim() === "", `the guard must stay silent, got ${JSON.stringify(r.raw)}`);
      assert(r.exit === 0, `the guard must exit 0, got ${r.exit}`);
    },
  },

  // ---------------------------------------------------------------- R9: no network, no key
  {
    id: "R9-writer-has-no-network-and-no-key-access",
    desc: "MECHANICAL CHECK: the writer imports only node:fs, node:os and node:path, and names no transport or key anywhere in its source",
    fn() {
      const src = readFileSync(WRITER, "utf8");
      const allowed = new Set(["node:fs", "node:os", "node:path"]);
      const mods = [...src.matchAll(/(?:^|\s)from\s+["']([^"']+)["']|require\(\s*["']([^"']+)["']\s*\)/g)].map(
        (m) => m[1] || m[2]
      );
      assert(mods.length > 0, "the import scan must actually find imports, or it proves nothing");
      for (const m of mods) assert(allowed.has(m), `the writer may only import stdlib fs/os/path — found ${JSON.stringify(m)}`);
      for (const banned of [
        /\bfetch\s*\(/,
        /node:https?\b/,
        /\bnode:net\b/,
        /\bchild_process\b/,
        /\bapi_key\b/i,
        /SOCIALCRAWL_API_KEY/,
        /XMLHttpRequest/,
      ]) {
        assert(!banned.test(src), `the writer must not mention /${banned.source}/ — it is a local-file tool`);
      }
      // The env it reads is exactly one name. Anything else is scope it should not have.
      const envs = [...src.matchAll(/process\.env\.([A-Za-z_][A-Za-z0-9_]*)/g)].map((m) => m[1]);
      assert(
        envs.length === 1 && envs[0] === "SC_REVXL_HOME",
        `the writer may read only SC_REVXL_HOME, found ${JSON.stringify(envs)}`
      );
    },
  },
];
