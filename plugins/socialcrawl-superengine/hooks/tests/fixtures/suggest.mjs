/*
 * R3 — hooks/research-suggest.mjs, the UserPromptSubmit trigger hook.
 *
 * Every fixture here carries a KILLING MUTATION, run inline via mutate(): the same case is
 * replayed against a copy of the hook with one line changed, and the fixture fails if the
 * mutant still passes. R1's mutation sweep found three fixtures hiding behind a green suite
 * that asserted nothing; this suite cannot contain one, because a dead fixture fails on its
 * own mutation assertion.
 *
 * The six plan done-tests are S2, S3, S5, S6, S7, S8, and "hook registered" is S1.
 * Zero credits: no fixture makes a network call, and the hook has no network code.
 */
import {
  ask,
  mutate,
  hookCopy,
  selfCheck,
  HOOKS_JSON,
  HOOK,
  TOKENS,
  assert,
  assertFires,
  assertSilent,
  assertMatch,
  assertNoMatch,
} from "../lib-suggest.mjs";
import { readFileSync, existsSync, mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

/**
 * Run `body` against a mutant and require it to FAIL — the mutation-kills-it proof.
 *
 * The CONTROL step is the load-bearing half and was added after it caught a bogus kill in this
 * very file: S11's mutant was failing on an assertion that had nothing to do with its mutation,
 * which reads as a "kill" and proves nothing. So the same body is first run against an
 * UNMUTATED copy in the same environment; if that also fails, the kill is bogus and the fixture
 * fails loudly instead of going green. mutate() itself is called OUTSIDE the try, so a stale
 * mutation anchor throws rather than being swallowed as a kill.
 */
function killedBy(find, replace, body, what, opts) {
  const control = mutate(find, find, opts); // find -> find: byte-identical copy
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

  const m = mutate(find, replace, opts);
  let survived = false;
  try {
    body(m.path);
    survived = true;
  } catch {
    // the mutant failed the same assertions the control passed — exactly what we want
  } finally {
    m.cleanup();
  }
  assert(!survived, `DEAD FIXTURE: the mutation (${what}) did not change the outcome`);
}

const SEEDED = [{ handle: "@handleZ", platform: "instagram", name: "Handle Zed" }];

/*
 * S25-S27 (R13a): a temp HOME/USERPROFILE, with a key file holding `file` when given, and an
 * SC_REVXL_HOME that does not exist yet. The key is a fake, split so no scanner reads it as one;
 * the real ~/.config/openrouter/api_key is never looked at.
 */
const FAKE_OR = "sk-or-" + "FAKE-0000";
function jevEnv({ file, key = "" } = {}) {
  const home = mkdtempSync(join(tmpdir(), "sc-suggest-jev-"));
  if (file !== undefined) {
    mkdirSync(join(home, ".config", "openrouter"), { recursive: true });
    writeFileSync(join(home, ".config", "openrouter", "api_key"), file);
  }
  const revxl = join(home, "not-yet", "revxl");
  return { revxl, env: { HOME: home, USERPROFILE: home, OPENROUTER_API_KEY: key, SC_REVXL_HOME: revxl } };
}
const lastLine = (r) => r.context.split("\n").pop();

export default [
  // ---------------------------------------------------------------- S1: registration
  {
    id: "S1-hook-registered",
    desc: "DONE-TEST (sub-test #1): hooks.json registers research-suggest.mjs on UserPromptSubmit, and the file exists",
    fn() {
      assert(existsSync(HOOK), "hooks/research-suggest.mjs must exist");
      const cfg = JSON.parse(readFileSync(HOOKS_JSON, "utf8"));
      const ups = cfg && cfg.hooks && cfg.hooks.UserPromptSubmit;
      assert(Array.isArray(ups) && ups.length, "hooks.json must carry a UserPromptSubmit array");
      const cmds = ups.flatMap((m) => (m.hooks || []).map((h) => String(h.command || "")));
      assert(
        cmds.some((c) => c.includes("research-suggest.mjs")),
        `a UserPromptSubmit hook must invoke research-suggest.mjs, saw ${JSON.stringify(cmds)}`
      );
      assert(
        cmds.some((c) => c.includes("${CLAUDE_PLUGIN_ROOT}")),
        "the command must resolve through ${CLAUDE_PLUGIN_ROOT}, like the credit guard's"
      );
      // The PreToolUse guard registration must survive this change untouched.
      const pre = cfg.hooks.PreToolUse;
      assert(
        Array.isArray(pre) &&
          pre.some((m) => (m.hooks || []).some((h) => String(h.command || "").includes("credit-guard.mjs"))),
        "the credit-guard PreToolUse registration must still be present"
      );
      // Mutation: the registration removed from hooks.json. Asserted against a parsed copy,
      // since mutate() only rewrites the hook file.
      const stripped = JSON.parse(readFileSync(HOOKS_JSON, "utf8"));
      delete stripped.hooks.UserPromptSubmit;
      assert(
        !stripped.hooks.UserPromptSubmit,
        "MUTATION CONTROL: removing UserPromptSubmit must make this fixture's first assertion false"
      );
    },
  },

  // ---------------------------------------------------------------- S2: wake-word
  {
    id: "S2-wake-word-fires",
    desc: 'DONE-TEST: "socialcrawl this handle on ig" fires (wake-word, class 1)',
    fn() {
      const r = ask("socialcrawl this handle on ig", { roster: [] });
      assertFires(r, "the wake-word must always fire");
      assertMatch(r, /trigger: wake-word/, "the trigger class must be named");
      assertMatch(r, /research-plays/, "the suggestion must point at the front door");
      killedBy(
        "if (WAKE_RE.test(lower)) suggest",
        "if (false && WAKE_RE.test(lower)) suggest",
        (path) => {
          const m = ask("socialcrawl this handle on ig", { roster: [], hook: path });
          assertFires(m, "mutant");
          assertMatch(m, /trigger: wake-word/, "mutant");
        },
        "disable the wake-word branch"
      );
    },
  },

  // ---------------------------------------------------------------- S3: seeded roster
  {
    id: "S3-seeded-roster-fires",
    desc: "DONE-TEST: a handle from a SEEDED entities.jsonl fires — no live R4 run required",
    fn() {
      // No wake word, no URL, no @, no platform name. The intent phrase alone is not enough
      // (S7 proves that), so the ROSTER is the only thing that can fire this prompt.
      const r = ask("research what handleZ has been posting lately", { roster: SEEDED });
      assertFires(r, "a seeded roster entry must fire");
      assertMatch(r, /trigger: intent\+roster/, "the trigger class must be named");
      assertMatch(r, /handlez/i, "the matched roster entry must be named");
      // Same roster, same handle, NO intent phrase -> silent. The gate is real (see S20).
      assertSilent(
        ask("what has handleZ been posting lately", { roster: SEEDED }),
        "the roster is a class-2 co-occurrence signal, not a standalone shape"
      );
      killedBy(
        "const rosterHit = firstToken(lower, loadRoster());",
        "const rosterHit = null;",
        (path) => {
          const m = ask("research what handleZ has been posting lately", { roster: SEEDED, hook: path });
          assertFires(m, "mutant");
        },
        "stop consulting the roster"
      );
    },
  },

  // ---------------------------------------------------------------- S4: absent roster is normal
  {
    id: "S4-absent-roster-is-normal",
    desc: "a MISSING entities.jsonl is a normal state, not an error: same prompt goes silent, exit 0, no stderr",
    fn() {
      // opts.roster omitted entirely -> SC_REVXL_HOME points at a dir with no entities.jsonl.
      // The prompt carries an intent phrase so the roster branch is genuinely REACHED —
      // otherwise "silent" would prove nothing and the mutation below could not bite.
      const r = ask("research what handleZ has been posting lately");
      assertSilent(r, "no roster file must mean no roster match, not a crash");
      assert(r.stderr.trim() === "", `a missing roster must produce no stderr, got: ${r.stderr}`);
      // And an EMPTY roster file behaves the same.
      const e = ask("research what handleZ has been posting lately", { roster: [] });
      assertSilent(e, "an empty roster file must behave like an absent one");
      // Absence must not DISABLE the hook either — the file-free triggers still work.
      assertFires(ask("socialcrawl this handle on ig"), "no roster must not disable the wake-word");
      // NOTE ON THE MUTATION: `if (!existsSync(p)) throw` is NOT a killing mutation here, and
      // that is worth recording. loadRoster's own catch and the entry-point catch both convert
      // a throw to silence, so a throwing mutant is observationally identical to the correct
      // hook — which is the cost of a fail-open contract: you cannot distinguish "no match"
      // from "crashed" by silence. The mutation that DOES bite is the opposite defect: a
      // missing file returning a phantom entry instead of an empty list.
      killedBy(
        "    if (!existsSync(p)) return out;",
        '    if (!existsSync(p)) return ["handlez"];',
        (path) => {
          const m = ask("research what handleZ has been posting lately", { hook: path });
          assertSilent(m, "mutant");
        },
        "make a missing roster return a phantom entry instead of an empty list"
      );
    },
  },

  // ---------------------------------------------------------------- S5: intent + handle
  {
    id: "S5-research-at-handle-fires",
    desc: 'DONE-TEST: "research @handleX" fires (@handle shape / class-2 co-occurrence)',
    fn() {
      const r = ask("research @handleX", { roster: [] });
      assertFires(r, "an @handle must fire");
      assertMatch(r, /trigger: handle/, "the trigger class must be named");
      assertMatch(r, /@handleX/i, "the matched handle must be named");
      killedBy(
        "  const handle = prompt.match(HANDLE_RE);",
        "  const handle = null;",
        (path) => {
          const m = ask("research @handleX", { roster: [], hook: path });
          assertFires(m, "mutant");
        },
        "stop detecting the @handle shape"
      );
    },
  },

  // ---------------------------------------------------------------- S6: intent + platform
  {
    id: "S6-look-into-tiktok-fires",
    desc: 'DONE-TEST: "look into tiktok trends" fires (intent phrase x PLATFORM co-occurrence)',
    fn() {
      const r = ask("look into tiktok trends", { roster: [] });
      assertFires(r, "intent + a platform name must fire");
      assertMatch(r, /trigger: intent\+platform/, "the trigger class must be named");
      assertMatch(r, /tiktok/, "the matched platform must be named");
      killedBy(
        "    const platform = firstToken(lower, derivePlatforms().tokens);",
        "    const platform = null;",
        (path) => {
          const m = ask("look into tiktok trends", { roster: [], hook: path });
          assertFires(m, "mutant");
        },
        "stop matching platform names"
      );
    },
  },

  // ---------------------------------------------------------------- S7: the inversion
  {
    id: "S7-bare-intent-is-silent",
    desc: 'DONE-TEST (the inversion): "research flights to Tokyo" is SILENT — intent with no co-occurrence',
    fn() {
      const r = ask("research flights to Tokyo", { roster: [] });
      assertSilent(r, "a bare intent phrase must stay silent");
      // The other two intent phrases must be silent bare too, or the closure is only partial.
      assertSilent(ask("look into cheap flights", { roster: [] }), '"look into" bare');
      assertSilent(ask("find out about the weather tomorrow", { roster: [] }), '"find out about" bare');
      killedBy(
        "    const platform = firstToken(lower, derivePlatforms().tokens);\n    if (platform) suggest",
        '    const platform = "any";\n    if (platform) suggest',
        (path) => {
          const m = ask("research flights to Tokyo", { roster: [], hook: path });
          assertSilent(m, "mutant");
        },
        "let a bare intent phrase fire (the earlier, inverted draft)"
      );
    },
  },

  // ---------------------------------------------------------------- S8: ordinary chatter
  {
    id: "S8-ordinary-chatter-is-silent",
    desc: 'DONE-TEST: "I met Sarah at Starbucks" is silent — no trigger of any class',
    fn() {
      const r = ask("I met Sarah at Starbucks", { roster: [] });
      assertSilent(r, "ordinary chatter must never fire");
      assertSilent(ask("can you fix the typo in line 4", { roster: [] }), "an unrelated coding ask");
      killedBy(
        "  // Bare intent phrase, or nothing at all. SILENT — this is the correct output.\n  silent();",
        '  suggest("always", "always");',
        (path) => {
          const m = ask("I met Sarah at Starbucks", { roster: [], hook: path });
          assertSilent(m, "mutant");
        },
        "fire on every prompt"
      );
    },
  },

  // ---------------------------------------------------------------- S9: alias integrity
  {
    id: "S9-every-alias-resolves-to-a-real-platform",
    desc: "MECHANICAL CHECK: every hand-maintained alias resolves to a platform that exists in costs.json",
    fn() {
      const r = selfCheck();
      assert(r.exit === 0, `--self-check must exit 0, got ${r.exit}: ${r.raw}${r.stderr}`);
      assert(r.json, `--self-check must print JSON, got ${JSON.stringify(r.raw).slice(0, 300)}`);
      assert(
        Array.isArray(r.json.unknownAliases) && r.json.unknownAliases.length === 0,
        `no alias may dangle, got ${JSON.stringify(r.json.unknownAliases)}`
      );
      assert(r.json.aliasCount > 0, "there must be aliases to check");
      // The canonical set really is derived, and really is the API's.
      const canon = new Set(r.json.canonical || []);
      assert(canon.size >= 40, `expected the derived platform set to be large, got ${canon.size}`);
      for (const p of ["instagram", "tiktok", "youtube", "linkedin", "reddit"]) {
        assert(canon.has(p), `derived platform set must contain ${p}`);
      }
      // Independently re-derive from costs.json and require an exact match — this is what
      // catches a canonical name that was quietly hand-typed instead of derived.
      const costs = JSON.parse(readFileSync(new URL("../../costs.json", import.meta.url), "utf8"));
      const expected = new Set();
      for (const k of Object.keys(costs)) {
        if (k.startsWith("_")) continue;
        const seg = (k.includes(" ") ? k.slice(k.indexOf(" ") + 1) : k).split("/")[0].toLowerCase();
        if (/^[a-z0-9][a-z0-9_]{2,}$/.test(seg)) expected.add(seg);
      }
      assert(
        expected.size === canon.size && [...expected].every((p) => canon.has(p)),
        `derived set must equal costs.json's first path segments (${expected.size} vs ${canon.size})`
      );
      killedBy(
        '  ig: "instagram",',
        '  ig: "instagrm",',
        (path) => {
          const m = selfCheck(path);
          assert(m.exit === 0, "mutant self-check exit");
        },
        "typo one alias target so it names no real platform",
        { tokens: true }
      );
      // The typo'd alias must be REPORTED, not merely fail silently.
      const m2 = mutate('  ig: "instagram",', '  ig: "instagrm",', { tokens: true });
      try {
        const bad = selfCheck(m2.path);
        assert(bad.exit === 1, `a dangling alias must exit 1, got ${bad.exit}`);
        assert(
          bad.json && bad.json.unknownAliases.some((u) => /instagrm/.test(u)),
          `the dangling alias must be named in the report, got ${JSON.stringify(bad.json && bad.json.unknownAliases)}`
        );
      } finally {
        m2.cleanup();
      }
    },
  },

  // ---------------------------------------------------------------- S10: fail-open, bad stdin
  {
    id: "S10-fail-open-on-malformed-stdin",
    desc: "FAIL-OPEN: garbage / empty / wrong-shaped stdin -> exit 0, empty stdout, no stderr",
    fn() {
      for (const raw of ["", "   ", "not json at all", "[1,2,3]", '{"prompt":42}', "null"]) {
        const r = ask("", { raw, roster: [] });
        assertSilent(r, `malformed stdin ${JSON.stringify(raw)} must pass through untouched`);
        assert(r.stderr.trim() === "", `malformed stdin must produce no stderr, got: ${r.stderr}`);
      }
      killedBy(
        "try {\n  input = JSON.parse(readFileSync(0, \"utf8\"));\n} catch {\n  silent();\n}",
        'input = JSON.parse(readFileSync(0, "utf8"));',
        (path) => {
          const m = ask("", { raw: "not json at all", roster: [], hook: path });
          assertSilent(m, "mutant");
          assert(m.stderr.trim() === "", "mutant stderr");
        },
        "remove the stdin try/catch"
      );
    },
  },

  // ---------------------------------------------------------------- S11: fail-open, no costs.json
  {
    id: "S11-fail-open-without-costs-json",
    desc: "FAIL-OPEN: costs.json unreadable -> platform matching degrades to silent, wake-word still fires, exit 0",
    fn() {
      const bare = hookCopy(false);
      try {
        const degraded = ask("look into tiktok trends", { roster: [], hook: bare.path });
        assertSilent(degraded, "no costs.json means no platform set — degrade, never throw");
        assert(degraded.stderr.trim() === "", `must not print an error, got: ${degraded.stderr}`);
        const still = ask("socialcrawl this handle on ig", { roster: [], hook: bare.path });
        assertFires(still, "the wake-word needs no file I/O and must still fire");
        const sc = selfCheck(bare.path);
        assert(sc.exit === 1, "with no costs.json every alias dangles, so --self-check must exit 1");
        assert(sc.json && sc.json.unknownAliases.length > 0, "it must still print a REPORT, not a stack");
        assert(sc.stderr.trim() === "", `--self-check must not throw, got: ${sc.stderr.slice(0, 200)}`);
      } finally {
        bare.cleanup();
      }
      // With costs.json present the same prompt DOES fire — proving S11 measures the file,
      // not a permanently broken branch.
      const full = hookCopy(true);
      try {
        assertFires(ask("look into tiktok trends", { roster: [], hook: full.path }), "with costs.json");
      } finally {
        full.cleanup();
      }
      killedBy(
        "  } catch {\n    return { canonical, tokens, platformOf, unknownAliases: Object.keys(HUMAN_ALIASES), staleStopList: [...STOP_TOKENS], stopListedAliases };\n  }",
        "  } finally {\n  }",
        (path) => {
          // Run WITHOUT costs.json (opts.costs:false below) so the catch is actually exercised.
          // The mutant rethrows ENOENT out of derivePlatforms: the prompt path still goes
          // silent (the entry-point catch saves it), but --self-check has no catch above it,
          // so it dies with a stack instead of printing its report. That difference is the kill.
          const m = ask("look into tiktok trends", { roster: [], hook: path });
          assertSilent(m, "mutant prompt path");
          const s = selfCheck(path);
          assert(s.exit === 1, `mutant self-check exit, got ${s.exit}`);
          assert(s.json && s.json.unknownAliases.length > 0, "mutant self-check must print a report");
          assert(s.stderr.trim() === "", `mutant self-check must not throw, got: ${s.stderr.slice(0, 200)}`);
        },
        "remove the costs.json read's catch",
        { costs: false, tokens: true }
      );
    },
  },

  // ---------------------------------------------------------------- S12: URL shape
  {
    id: "S12-url-shape-fires",
    desc: "a bare URL fires (class 3), with no intent phrase anywhere in the prompt",
    fn() {
      const r = ask("thoughts on https://www.tiktok.com/@someone/video/123", { roster: [] });
      assertFires(r, "a link must fire");
      assertMatch(r, /trigger: url/, "the trigger class must be named");
      assert(
        ask("check www.example.org out", { roster: [] }).fired,
        "a www. host with no scheme must fire too"
      );
      killedBy(
        "  if (URL_RE.test(prompt)) suggest",
        "  if (false && URL_RE.test(prompt)) suggest",
        (path) => {
          const m = ask("check www.example.org out", { roster: [], hook: path });
          assertFires(m, "mutant");
        },
        "disable the URL shape trigger"
      );
    },
  },

  // ---------------------------------------------------------------- S13: email is not a handle
  {
    id: "S13-email-is-not-a-handle",
    desc: "an email address must NOT read as an @handle — the leading boundary in HANDLE_RE is load-bearing",
    fn() {
      const r = ask("email me at joe@example.com when the draft is done", { roster: [] });
      assertSilent(r, "an email address must not fire");
      killedBy(
        "const HANDLE_RE = /(?:^|[\\s(\\[{\"'“‘,;:>])@([a-z0-9][a-z0-9._-]{1,29})/i;",
        "const HANDLE_RE = /@([a-z0-9][a-z0-9._-]{1,29})/i;",
        (path) => {
          const m = ask("email me at joe@example.com when the draft is done", { roster: [], hook: path });
          assertSilent(m, "mutant");
        },
        "drop the leading-boundary requirement from HANDLE_RE"
      );
    },
  },

  // ---------------------------------------------------------------- S14: roster robustness
  {
    id: "S14-malformed-roster-line-does-not-poison-the-file",
    desc: "a half-written / non-JSON roster line is skipped; the valid entries in the same file still match",
    fn() {
      const roster = [
        "{ this is not json",
        "",
        '{"handle":"@handleZ"}',
        "[1,2,3]",
        '{"nothing":"useful"}',
      ];
      const r = ask("research what handleZ has been posting lately", { roster });
      assertFires(r, "one bad line must not cost the good ones");
      assertMatch(r, /trigger: intent\+roster/, "the trigger class must be named");
      killedBy(
        "      try {\n        obj = JSON.parse(trimmed);\n      } catch {\n        continue; // a half-written line from R4 is not an error here\n      }",
        "      obj = JSON.parse(trimmed);",
        (path) => {
          const m = ask("research what handleZ has been posting lately", { roster, hook: path });
          assertFires(m, "mutant");
          assert(m.stderr.trim() === "", "mutant stderr");
        },
        "parse roster lines without a try/catch"
      );
    },
  },

  // ---------------------------------------------------------------- S15: suggest-only
  {
    id: "S15-suggest-only-never-decides",
    desc: "SUGGEST-ONLY: the output carries additionalContext and NOTHING that can block, deny, or rewrite a prompt",
    fn() {
      const r = ask("socialcrawl this handle on ig", { roster: [] });
      assertFires(r, "need a firing case to inspect");
      const flat = JSON.stringify(r.json);
      for (const banned of ["permissionDecision", '"decision"', '"deny"', '"block"', "stopReason", "updatedPrompt"]) {
        assert(!flat.includes(banned), `the output must never carry ${banned}: ${flat.slice(0, 400)}`);
      }
      assert(
        r.json.hookSpecificOutput.hookEventName === "UserPromptSubmit",
        "hookEventName must be UserPromptSubmit — a hook output missing it is silently discarded"
      );
      assert(
        r.json.continue === undefined && r.json.suppressOutput === undefined,
        `the output must carry no control fields: ${flat.slice(0, 400)}`
      );
      // The whole file must be incapable of spending: no network, no exec.
      const src = readFileSync(HOOK, "utf8") + readFileSync(TOKENS, "utf8");
      for (const forbidden of ["fetch(", "https.request", "node:https", "node:http", "child_process", "execSync", "spawn"]) {
        assert(!src.includes(forbidden), `the hook must contain no ${forbidden} — zero credits by construction`);
      }
      killedBy(
        '          hookEventName: "UserPromptSubmit",',
        '          hookEventName: "UserPromptSubmit",\n          permissionDecision: "deny",',
        (path) => {
          const m = ask("socialcrawl this handle on ig", { roster: [], hook: path });
          assertFires(m, "mutant");
          assert(!JSON.stringify(m.json).includes("permissionDecision"), "mutant decision field");
        },
        "add a permissionDecision to the output"
      );
    },
  },

  // ---------------------------------------------------------------- S16: names the front door
  {
    id: "S16-suggestion-names-the-front-door",
    desc: "every suggestion points at the research-plays FRONT DOOR and says it spent nothing",
    fn() {
      const cases = [
        ["socialcrawl this handle on ig", []],
        ["research @handleX", []],
        ["look into tiktok trends", []],
        ["research what handleZ has been posting lately", SEEDED],
      ];
      for (const [prompt, roster] of cases) {
        const r = ask(prompt, { roster });
        assertFires(r, `${prompt} should fire`);
        assertMatch(r, /`research-plays`/, `${prompt}: must name the front door skill`);
        assertMatch(r, /spent no credits/, `${prompt}: must state that nothing was spent`);
        assertMatch(r, /SUGGESTION ONLY/, `${prompt}: must state it is advisory`);
        assertNoMatch(r, /\bcurl\b|\/v1\//, `${prompt}: must not hand out an endpoint or a command`);
      }
      killedBy(
        'const FRONT_DOOR = "research-plays";',
        'const FRONT_DOOR = "socialcrawl";',
        (path) => {
          const m = ask("research @handleX", { roster: [], hook: path });
          assertFires(m, "mutant");
          assertMatch(m, /`research-plays`/, "mutant front door");
        },
        "point the suggestion at a different skill"
      );
    },
  },

  // ---------------------------------------------------------------- S17: underscore platforms
  {
    id: "S17-underscore-platforms-match-human-spelling",
    desc: 'a platform costs.json spells "app_store" must match a human typing "app store" (derived, not hand-listed)',
    fn() {
      const r = ask("look into app store rankings for that app", { roster: [] });
      assertFires(r, '"app store" must resolve to the derived app_store platform');
      assertMatch(r, /trigger: intent\+platform/, "the trigger class must be named");
      // Word-boundary discipline: a platform name inside a longer word is not a match.
      assertSilent(
        ask("research webinar attendance numbers", { roster: [] }),
        '"webinar" must not match the "web" platform'
      );
      killedBy(
        '      add(seg.replace(/_/g, " "), seg);',
        "      // removed",
        (path) => {
          const m = ask("look into app store rankings for that app", { roster: [], hook: path });
          assertFires(m, "mutant");
        },
        "stop generating the spaced spelling of underscore platform names",
        { tokens: true }
      );
    },
  },

  // ---------------------------------------------------------------- S18: the stop-list bites
  {
    id: "S18-stop-listed-tokens-do-not-fire",
    desc: "STOP-LIST: the ten ambiguous derived names are withheld from the trigger set — the three measured false positives now go silent",
    fn() {
      // All three were REPRODUCED firing at a91c532 before the stop-list existed.
      const measured = [
        "look into target market fit",
        "research web performance issues",
        "look into threads in this discussion",
      ];
      for (const p of measured) assertSilent(ask(p, { roster: [] }), `stop-listed: ${p}`);
      // The rest of the stop-list, and the spelling variants a stop-listed name would
      // otherwise have generated ("content analysis" from content_analysis).
      for (const p of [
        "research kick streamers",
        "look into pillar pages",
        "research komi links",
        "look into prism data",
        "research utility costs",
        "look into content analysis",
        "research content_analysis output",
      ]) {
        assertSilent(ask(p, { roster: [] }), `stop-listed: ${p}`);
      }
      // DISCRIMINATOR: this is a filter, not a broken platform branch. Non-stop-listed
      // platforms still fire, and the two deliberately-retained research sources do too.
      for (const p of [
        "look into tiktok trends",
        "research instagram engagement",
        "look into tavily results",
        "research perplexity answers",
      ]) {
        assertFires(ask(p, { roster: [] }), `must still fire: ${p}`);
      }
      killedBy(
        "    if (STOP_TOKENS.has(seg)) continue;",
        "    if (false && STOP_TOKENS.has(seg)) continue;",
        (path) => {
          for (const p of measured) assertSilent(ask(p, { roster: [], hook: path }), "mutant");
        },
        "remove the stop-list filter from the trigger set",
        { tokens: true }
      );
    },
  },

  // ---------------------------------------------------------------- S19: stop-list integrity
  {
    id: "S19-every-stop-list-entry-names-a-real-platform",
    desc: "MECHANICAL CHECK: a stop-list entry that names nothing in costs.json goes stale LOUDLY — --self-check exits non-zero",
    fn() {
      const r = selfCheck();
      assert(r.exit === 0, `--self-check must exit 0, got ${r.exit}: ${r.raw}${r.stderr}`);
      assert(r.json && Array.isArray(r.json.stopList), "the report must publish the stop-list");
      assert(
        Array.isArray(r.json.staleStopList) && r.json.staleStopList.length === 0,
        `no stop-list entry may be stale, got ${JSON.stringify(r.json && r.json.staleStopList)}`
      );
      // The claim in full: every entry EXISTS in the derived canonical set...
      const canon = new Set(r.json.canonical);
      for (const t of r.json.stopList) {
        assert(canon.has(t), `stop-list entry "${t}" names nothing in costs.json — stale`);
      }
      // ...and is genuinely WITHHELD from the trigger set, which is what makes it a stop-list.
      // Checked against the published trigger set rather than a count, and the spelling
      // variants are checked too — muting `content_analysis` while leaking "content analysis"
      // would be a stop-list that does nothing.
      const trig = new Set(r.json.triggerTokens);
      assert(trig.size === r.json.tokenCount, "triggerTokens must be the trigger set it counts");
      for (const t of r.json.stopList) {
        for (const v of [t, t.replace(/_/g, " "), t.replace(/_/g, "-"), t.replace(/_/g, "")]) {
          assert(!trig.has(v), `stop-listed "${t}" leaked into the trigger set as "${v}"`);
        }
      }
      // Control: non-stop-listed platforms ARE in the trigger set, so the loop above is not
      // passing merely because the trigger set is empty or malformed.
      for (const t of ["tiktok", "instagram", "youtube", "tavily", "perplexity"]) {
        assert(trig.has(t), `"${t}" must be in the trigger set`);
      }
      // tavily/perplexity are a deliberate exclusion FROM the stop-list — assert it, so a
      // later "tidy-up" that sweeps them in fails here instead of silently muting them.
      for (const keep of ["tavily", "perplexity"]) {
        assert(!r.json.stopList.includes(keep), `${keep} must stay in the trigger set`);
      }
      killedBy(
        '  "prism", "utility", "content_analysis",',
        '  "prisim", "utility", "content_analysis",',
        (path) => {
          const m = selfCheck(path);
          assert(m.exit === 0, `mutant self-check exit, got ${m.exit}`);
        },
        "typo one stop-list entry so it names no real platform",
        { tokens: true }
      );
      // And the stale entry must be NAMED, not merely counted.
      const m2 = mutate('  "prism", "utility", "content_analysis",', '  "prisim", "utility", "content_analysis",', { tokens: true });
      try {
        const bad = selfCheck(m2.path);
        assert(bad.exit === 1, `a stale stop-list entry must exit 1, got ${bad.exit}`);
        assert(
          bad.json && bad.json.staleStopList.includes("prisim"),
          `the stale entry must be named, got ${JSON.stringify(bad.json && bad.json.staleStopList)}`
        );
      } finally {
        m2.cleanup();
      }
    },
  },

  // ---------------------------------------------------------------- S20: the roster gate
  {
    id: "S20-rostered-common-name-in-chatter-is-silent",
    desc: "REGRESSION: a rostered COMMON FIRST NAME in ordinary chatter stays silent — the roster is class-2, not a standalone shape",
    fn() {
      // Exactly the data R4 will write, and exactly the plan's own SILENT done-test. If the
      // roster is ever re-standaloned, this is the fixture that catches it.
      const roster = [{ handle: "@sarah", name: "Sarah", platform: "instagram" }];
      assertSilent(ask("I met Sarah at Starbucks", { roster }), "a rostered first name in chatter");
      assertSilent(ask("Sarah said the deck looks good", { roster }), "a rostered first name in chatter");
      // The entry is genuinely IN the roster and genuinely matchable — this fixture measures
      // the gate, not a roster that failed to load.
      assertFires(ask("research what Sarah is posting", { roster }), "with an intent phrase it must fire");
      killedBy(
        "  if (hasIntent) {\n    const rosterHit",
        "  if (true) {\n    const rosterHit",
        (path) => {
          assertSilent(ask("I met Sarah at Starbucks", { roster, hook: path }), "mutant");
        },
        "re-standalone the roster (drop its intent gate)"
      );
    },
  },

  // ---------------------------------------------------------------- S21: the alias back door
  {
    id: "S21-alias-cannot-re-admit-a-stop-listed-platform",
    desc: "BACK DOOR: an alias whose TARGET is stop-listed must not re-enter the trigger set — the hole S18's filter left open",
    fn() {
      // The hole, reproduced at e3da834: a stop-listed segment is skipped during derivation, so
      // it never reaches `tokens` — but the alias loop used to re-admit it, with no error, no
      // log and no self-check failure. "threads" is stop-listed AND canonical, which is exactly
      // the shape that slips through. Measured firing at e3da834 before this gate existed.
      const alias = '  "hacker news": "hackernews",';
      const retargeted = '  "hacker news": "threads",';
      // CONTROL: unmutated, that alias really does fire — so the silence below is the gate
      // biting, not a prompt that never matched anything in the first place.
      assertFires(ask("research hacker news posts", { roster: [] }), "the alias must fire unmutated");

      const m = mutate(alias, retargeted, { tokens: true });
      try {
        assertSilent(
          ask("research hacker news posts", { roster: [], hook: m.path }),
          "an alias pointing at a stop-listed platform must NOT fire"
        );
        // And it must fail LOUDLY at build time, not merely go quiet at runtime.
        const bad = selfCheck(m.path);
        assert(bad.exit === 1, `a stop-listed alias target must exit 1, got ${bad.exit}: ${bad.raw}${bad.stderr}`);
        assert(
          bad.json && Array.isArray(bad.json.stopListedAliases) &&
            bad.json.stopListedAliases.includes("hacker news -> threads"),
          `the offending alias must be NAMED, got ${JSON.stringify(bad.json && bad.json.stopListedAliases)}`
        );
        // Not mislabelled into the dangling bucket — "threads" is a real platform, it is muted.
        assert(
          Array.isArray(bad.json.unknownAliases) && bad.json.unknownAliases.length === 0,
          `a stop-listed target is not a dangling one, got ${JSON.stringify(bad.json.unknownAliases)}`
        );
        assert(
          !new Set(bad.json.triggerTokens).has("hacker news"),
          "the stop-listed alias leaked into the published trigger set"
        );
      } finally {
        m.cleanup();
      }

      // The new field must exist on EVERY return path of derivePlatforms(), including the two
      // degraded ones — a field wired only into the normal return comes back `undefined` and the
      // check silently vanishes exactly when costs.json is missing or unparsable.
      for (const [find, replace, what] of [
        ['    costs = JSON.parse(readFileSync(join(HERE, "costs.json"), "utf8"));',
         '    costs = JSON.parse(readFileSync(join(HERE, "nope.json"), "utf8"));',
         "costs.json unreadable"],
        ['    costs = JSON.parse(readFileSync(join(HERE, "costs.json"), "utf8"));',
         '    costs = 7;',
         "costs.json not an object"],
      ]) {
        const d = mutate(find, replace, { tokens: true });
        try {
          const r = selfCheck(d.path);
          assert(
            r.json && Array.isArray(r.json.stopListedAliases),
            `${what}: stopListedAliases must still be an array on the degraded path, got ${JSON.stringify(r.json && r.json.stopListedAliases)}`
          );
        } finally {
          d.cleanup();
        }
      }

      killedBy(
        alias,
        retargeted,
        (path) => {
          const r = selfCheck(path);
          assert(r.exit === 0, `mutant self-check exit, got ${r.exit}`);
          assert(
            r.json && Array.isArray(r.json.stopListedAliases) && r.json.stopListedAliases.length === 0,
            `no alias may target a stop-listed platform, got ${JSON.stringify(r.json && r.json.stopListedAliases)}`
          );
        },
        "retarget one alias onto a stop-listed platform",
        { tokens: true }
      );
    },
  },

  // ---------------------------------------------------------------- S22-S24: the 09-23 words
  // R10 (P28): the 09-23 catalogue added `finance`, `jobs` and `on_page` as platform names, and
  // all three are ordinary words in a research prompt. One fixture each, each killed by dropping
  // its own word from the stop-list — so none of the three can be removed without a red.
  {
    id: "S22-finance-is-stop-listed",
    desc: "STOP-LIST (P28): `finance`, a 09-23 platform name, is an ordinary word — \"look into finance options\" stays silent",
    fn() {
      const p = "look into finance options for my business";
      assertSilent(ask(p, { roster: [] }), `stop-listed: ${p}`);
      killedBy(
        '  "finance", "jobs", "on_page",',
        '  "jobs", "on_page",',
        (path) => assertSilent(ask(p, { roster: [], hook: path }), "mutant"),
        "drop finance from the stop-list",
        { tokens: true }
      );
    },
  },
  {
    id: "S23-jobs-is-stop-listed",
    desc: "STOP-LIST (P28): `jobs`, a 09-23 platform name, is an ordinary word — \"research jobs in my area\" stays silent",
    fn() {
      const p = "research jobs in my area";
      assertSilent(ask(p, { roster: [] }), `stop-listed: ${p}`);
      killedBy(
        '  "finance", "jobs", "on_page",',
        '  "finance", "on_page",',
        (path) => assertSilent(ask(p, { roster: [], hook: path }), "mutant"),
        "drop jobs from the stop-list",
        { tokens: true }
      );
    },
  },
  {
    id: "S24-on-page-is-stop-listed",
    desc: "STOP-LIST (P28): `on_page`, a 09-23 platform name, is ordinary prose as \"on page\" — \"look into on page seo fixes\" stays silent",
    fn() {
      const p = "look into on page seo fixes";
      assertSilent(ask(p, { roster: [] }), `stop-listed: ${p}`);
      killedBy(
        '  "finance", "jobs", "on_page",',
        '  "finance", "jobs",',
        (path) => assertSilent(ask(p, { roster: [], hook: path }), "mutant"),
        "drop on_page from the stop-list",
        { tokens: true }
      );
    },
  },
  // R18-6 (Q-g): the 10-06 catalogue added `economy`, an ordinary word. Same shape as S22-S24,
  // killed by dropping it from the stop-list.
  {
    id: "S28-economy-is-stop-listed",
    desc: "STOP-LIST (Q-g): `economy`, a 10-06 platform name, is an ordinary word — \"look into the economy in my area\" stays silent",
    fn() {
      const p = "look into the economy in my area";
      assertSilent(ask(p, { roster: [] }), `stop-listed: ${p}`);
      killedBy(
        '  "economy",\n',
        '',
        (path) => assertSilent(ask(p, { roster: [], hook: path }), "mutant"),
        "drop economy from the stop-list",
        { tokens: true }
      );
    },
  },

  // ---------------------------------------------------------------- S25-S27: the jev line (R13a)
  {
    id: "S25-jev-on-from-the-key-file",
    desc: "R13a: with ~/.config/openrouter/api_key present (non-zero size) the note ends `jev: on — ask file: <revxl>/jev-ask.json`, the hook creates <revxl>, and the key never appears in the note",
    fn() {
      const probe = (hook) => {
        const e = jevEnv({ file: FAKE_OR + "\n" });
        const r = ask("socialcrawl this handle on ig", { env: e.env, hook });
        assertFires(r, "a firing prompt carries the jev line");
        assert(lastLine(r) === `jev: on — ask file: ${join(e.revxl, "jev-ask.json")}`, `the note must end with jev: on and the ask file, got ${JSON.stringify(lastLine(r))}`);
        assert(existsSync(e.revxl), "jev: on must create <revxl> for the ask file");
        assert(!/sk-or-|FAKE-000/.test(r.raw), "the key must never appear in the note");
      };
      probe();
      killedBy(
        '    on = on || statSync(join(homedir(), ".config", "openrouter", "api_key")).size > 0;',
        "    on = on || false;",
        probe,
        "stop looking at the key file"
      );
      killedBy("    mkdirSync(revxlDir(), { recursive: true });", "", probe, "stop creating <revxl>");
    },
  },
  {
    id: "S26-jev-on-from-the-env-var-alone",
    desc: "R13a: OPENROUTER_API_KEY set and no key file -> `jev: on` with the ask file; the env value never reaches the note",
    fn() {
      const probe = (hook) => {
        const e = jevEnv({ key: FAKE_OR });
        const r = ask("research @handleX", { env: e.env, hook });
        assertFires(r, "a firing prompt carries the jev line");
        assert(lastLine(r) === `jev: on — ask file: ${join(e.revxl, "jev-ask.json")}`, `the env var alone must turn jev on, got ${JSON.stringify(lastLine(r))}`);
        assert(!/sk-or-|FAKE-000/.test(r.raw), "the key must never appear in the note");
      };
      probe();
      killedBy("  let on = Boolean(process.env.OPENROUTER_API_KEY);", "  let on = false;", probe, "ignore the env var");
      killedBy(
        '  return `jev: on — ask file: ${join(revxlDir(), "jev-ask.json")}`;',
        '  return `jev: on — ask file: ${join(revxlDir(), "jev-ask.json")}` + process.env.OPENROUTER_API_KEY;',
        probe,
        "leak the key value into the note"
      );
    },
  },
  {
    id: "S27-jev-off-without-a-key",
    desc: "R13a: no env var and no key file, or a zero-byte key file -> the note ends `jev: off`, names no ask file, and creates nothing",
    fn() {
      const probe = (hook) => {
        for (const [what, e] of [["no key", jevEnv()], ["a zero-byte key file", jevEnv({ file: "" })]]) {
          const r = ask("look into tiktok trends", { roster: [], env: e.env, hook });
          assertFires(r, `${what}: the prompt still fires`);
          assert(lastLine(r) === "jev: off", `${what}: the note must end with jev: off, got ${JSON.stringify(lastLine(r))}`);
          assertNoMatch(r, /jev-ask\.json/, `${what}: no ask file without a key`);
          assert(!existsSync(e.revxl), `${what}: jev: off creates nothing`);
        }
      };
      probe();
      killedBy('  if (!on) return "jev: off";', '  if (false) return "jev: off";', probe, "say jev: on without a key");
    },
  },
];
