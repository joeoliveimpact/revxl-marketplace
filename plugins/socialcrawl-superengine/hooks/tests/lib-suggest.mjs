/*
 * Test harness for hooks/research-suggest.mjs. BUILD-TIME TOOLING ONLY — nothing in this
 * directory is referenced by hooks.json or by any skill, so the plugin never loads it at
 * runtime. Run it with `node hooks/tests/run.mjs`.
 *
 * It invokes the hook exactly the way Claude Code does: a UserPromptSubmit envelope as JSON on
 * stdin, the suggestion as JSON on stdout, exit 0 always (the hook is fail-open by contract).
 *
 * SC_REVXL_HOME is redirected to a throwaway directory per case, so a fixture can seed
 * `entities.jsonl` without touching the real `~/.claude/revxl/` and so a "no roster" case is
 * genuinely rosterless rather than reading whatever the developer happens to have.
 *
 * Zero credits: the hook is a pure function of the prompt string, costs.json, and the roster
 * file. No fixture makes a network call, and the hook has no network code at all.
 */
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync, readFileSync, copyFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
export const HOOK = resolve(HERE, "..", "research-suggest.mjs");
export const HOOKS_JSON = resolve(HERE, "..", "hooks.json");
export const COSTS = resolve(HERE, "..", "costs.json");
/* The hook imports its platform derivation from here (R13a), so every copy carries it too. */
export const TOKENS = resolve(HERE, "..", "platform-tokens.mjs");

let seq = 0;

/**
 * One prompt through the hook.
 *   opts.roster   array of JSONL lines (strings, or objects that get stringified) to seed
 *                 entities.jsonl with. Omit entirely for the "no roster file" case.
 *   opts.hook     an alternative hook path (used to prove fail-open with costs.json absent).
 *   opts.raw      send this exact string on stdin instead of a well-formed envelope.
 */
export function ask(prompt, opts = {}) {
  const dir = mkdtempSync(join(tmpdir(), "sc-suggest-test-"));
  try {
    if (opts.roster !== undefined) {
      const body = opts.roster
        .map((l) => (typeof l === "string" ? l : JSON.stringify(l)))
        .join("\n");
      writeFileSync(join(dir, "entities.jsonl"), body);
    }
    // HOME/USERPROFILE and OPENROUTER_API_KEY are scrubbed too, so the note's jev line never
    // depends on the machine (a real key file is never looked at); opts.env seeds a key.
    const env = { ...process.env, SC_REVXL_HOME: dir, HOME: dir, USERPROFILE: dir, OPENROUTER_API_KEY: "", ...(opts.env || {}) };
    const stdin =
      opts.raw !== undefined
        ? opts.raw
        : JSON.stringify({
            session_id: `scst${process.pid}x${++seq}`,
            hook_event_name: "UserPromptSubmit",
            prompt,
            cwd: dir,
          });
    const r = spawnSync(process.execPath, [opts.hook || HOOK], {
      input: stdin,
      encoding: "utf8",
      env,
    });
    const raw = String(r.stdout || "");
    let parsed = null;
    if (raw.trim()) {
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = null;
      }
    }
    const hso = (parsed && parsed.hookSpecificOutput) || null;
    return {
      raw,
      stderr: String(r.stderr || ""),
      exit: r.status,
      json: parsed,
      fired: Boolean(hso && typeof hso.additionalContext === "string" && hso.additionalContext),
      context: (hso && hso.additionalContext) || "",
    };
  } finally {
    try {
      rmSync(dir, { recursive: true, force: true });
    } catch {}
  }
}

/**
 * A copy of the hook in a scratch directory. Pass `withCosts:false` to prove the hook still
 * fail-opens (and still fires its file-free triggers) when costs.json cannot be read.
 */
export function hookCopy(withCosts) {
  const dir = mkdtempSync(join(tmpdir(), "sc-suggest-copy-"));
  const dest = join(dir, "research-suggest.mjs");
  copyFileSync(HOOK, dest);
  copyFileSync(TOKENS, join(dir, "platform-tokens.mjs"));
  if (withCosts) copyFileSync(COSTS, join(dir, "costs.json"));
  return {
    path: dest,
    cleanup() {
      try {
        rmSync(dir, { recursive: true, force: true });
      } catch {}
    },
  };
}

/** Run `research-suggest.mjs --self-check` and return its parsed report plus exit code. */
export function selfCheck(hookPath) {
  const r = spawnSync(process.execPath, [hookPath || HOOK, "--self-check"], {
    encoding: "utf8",
    input: "",
  });
  let json = null;
  try {
    json = JSON.parse(String(r.stdout || ""));
  } catch {}
  return { exit: r.status, json, raw: String(r.stdout || ""), stderr: String(r.stderr || "") };
}

/**
 * A hook copy with one text substitution applied — the mutation harness. A fixture that
 * cannot be killed by a mutation is a dead fixture; this makes "the mutation kills it"
 * something a checker can RUN rather than take on trust. `opts.tokens: true` applies the
 * substitution to platform-tokens.mjs instead (the derivation, aliases and stop-list live there
 * since R13a); `path` is always the hook copy, which imports the module beside it.
 */
export function mutate(find, replace, opts = {}) {
  const dir = mkdtempSync(join(tmpdir(), "sc-suggest-mut-"));
  const [target, name] = opts.tokens ? [TOKENS, "platform-tokens.mjs"] : [HOOK, "research-suggest.mjs"];
  const src = readFileSync(target, "utf8");
  if (!src.includes(find)) {
    try {
      rmSync(dir, { recursive: true, force: true });
    } catch {}
    throw new Error(`mutation anchor not found in ${name}: ${JSON.stringify(find)}`);
  }
  const dest = join(dir, "research-suggest.mjs");
  copyFileSync(HOOK, dest);
  copyFileSync(TOKENS, join(dir, "platform-tokens.mjs"));
  writeFileSync(join(dir, name), src.split(find).join(replace));
  // `costs:false` reproduces the missing-costs.json environment, for the fail-open mutation.
  if (opts.costs !== false) copyFileSync(COSTS, join(dir, "costs.json"));
  return {
    path: dest,
    cleanup() {
      try {
        rmSync(dir, { recursive: true, force: true });
      } catch {}
    },
  };
}

/** Assertion helpers. Every failure throws with the hook's own output attached. */
export function assert(cond, msg, ctx) {
  if (!cond) {
    const extra = ctx ? `\n      hook said: ${JSON.stringify(ctx).slice(0, 900)}` : "";
    throw new Error(msg + extra);
  }
}
export function assertFires(res, msg) {
  assert(res.fired, `${msg} — expected a suggestion, got none`, {
    exit: res.exit,
    raw: res.raw,
    stderr: res.stderr,
  });
  assert(res.exit === 0, `${msg} — hook must always exit 0, got ${res.exit}`, { stderr: res.stderr });
}
export function assertSilent(res, msg) {
  assert(!res.fired, `${msg} — expected SILENCE, hook suggested instead`, {
    exit: res.exit,
    context: res.context,
  });
  assert(res.raw.trim() === "", `${msg} — silence means empty stdout, got ${JSON.stringify(res.raw)}`);
  assert(res.exit === 0, `${msg} — hook must always exit 0, got ${res.exit}`, { stderr: res.stderr });
}
export function assertMatch(res, re, msg) {
  assert(re.test(res.context), `${msg} — expected /${re.source}/ in the suggestion`, {
    context: res.context,
    raw: res.raw,
  });
}
export function assertNoMatch(res, re, msg) {
  assert(!re.test(res.context), `${msg} — did NOT expect /${re.source}/ in the suggestion`, {
    context: res.context,
  });
}
