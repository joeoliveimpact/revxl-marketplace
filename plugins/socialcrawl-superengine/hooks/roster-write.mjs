#!/usr/bin/env node
/*
 * roster-write.mjs — the ONLY sanctioned writer for `~/.claude/revxl/entities.jsonl`.
 *
 * The roster is the short list of accounts this user actually researches.
 * `hooks/research-suggest.mjs` READS it, so that next session "research <handle>" wakes the
 * suggestion up. This script WRITES it, and nothing else should.
 *
 * Hand-write a line and you can be wrong SILENTLY: the reader is tolerant by design, so a
 * line carrying the wrong field simply never matches — no error, no log, no warning, the
 * hook just quietly stops firing on that entity. This script exists so that cannot happen.
 *
 * THE READER'S CONTRACT, in five lines:
 *   1. One JSON value per line; an unparsable line is SKIPPED, never fatal.
 *   2. A name is read from `handle`, `username`, `name`, `entity`, `alias` or `brand`, or
 *      from a bare JSON string. `platform` is deliberately NOT one of them.
 *   3. Each value is trimmed, leading `@`s stripped, lowercased.
 *   4. It is kept only if it is 3-80 characters long.
 *   5. Only the FIRST 2000 lines of the file are read at all.
 *
 * So we write `handle` — the one matched field. `platform`, `source` and `added` are
 * informational only and the reader ignores all three. `platform` is ignored on purpose: a
 * platform name is already its own co-occurrence trigger inside the hook, and matching it
 * here would drag every entry's whole platform in with it. A platform name is never a handle.
 *
 * `SC_REVXL_HOME` overrides the directory (the same env var the reader honours), which is how
 * the fixture suite exercises this without touching a real roster.
 *
 * Stdlib only. One local file, no calls out, no key, no credits.
 */
import { appendFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";

const ROSTER_FIELDS = ["handle", "username", "name", "entity", "alias", "brand"];
const MAX_LINES = 2000;
const USAGE =
  "usage: node roster-write.mjs --handle <h> [--handle <h2> ...] [--platform <p>] [--source research-plays|onboarding]";

function rosterPath() {
  const override = process.env.SC_REVXL_HOME;
  const base =
    override && String(override).trim() ? String(override) : join(homedir(), ".claude", "revxl");
  return join(base, "entities.jsonl");
}

/** The reader's normalisation, minus the lowercasing it only does for matching. */
const norm = (s) => String(s).trim().replace(/^@+/, "");

function refuse(why) {
  process.stderr.write(`roster: refused — ${why}\n`);
  process.exit(1);
}

function parseArgs(argv) {
  const out = { handles: [], platform: "", source: "" };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") {
      process.stdout.write(USAGE + "\n");
      process.exit(0);
    } else if (a === "--handle") out.handles.push(argv[++i] ?? "");
    else if (a === "--platform") out.platform = String(argv[++i] ?? "").trim();
    else if (a === "--source") out.source = String(argv[++i] ?? "").trim();
    else refuse(`unknown argument ${JSON.stringify(a)}. ${USAGE}`);
  }
  return out;
}

/** Every name the reader would pull out of the file as it stands, normalised + lowercased. */
function existingNames(text) {
  const seen = new Set();
  for (const line of text.split(/\r?\n/)) {
    const t = line.trim();
    if (!t) continue;
    let obj;
    try {
      obj = JSON.parse(t);
    } catch {
      continue; // a corrupt neighbour is skipped here exactly as the reader skips it
    }
    const vals =
      typeof obj === "string"
        ? [obj]
        : obj && typeof obj === "object" && !Array.isArray(obj)
          ? ROSTER_FIELDS.filter((f) => typeof obj[f] === "string").map((f) => obj[f])
          : [];
    for (const v of vals) seen.add(norm(v).toLowerCase());
  }
  return seen;
}

function main() {
  const { handles, platform, source } = parseArgs(process.argv.slice(2));
  if (!handles.length) refuse(`no --handle given. ${USAGE}`);

  // Validate EVERY handle before writing ANY, so a refusal leaves the file byte-identical.
  const wanted = handles.map((raw) => {
    const h = norm(raw);
    if (!h) refuse("empty handle — the reader keeps a name only if it is 3-80 characters.");
    if (/\s/.test(h))
      refuse(
        `${JSON.stringify(h)} contains whitespace — the reader matches one whole token, so this line could never fire.`
      );
    if (h.includes("://") || (h.includes("/") && h.split("/")[0].includes(".")))
      refuse(
        `${JSON.stringify(h)} is a URL — handles only. A URL already triggers the hook on its own shape and does not belong in the roster.`
      );
    if (h.length < 3 || h.length > 80)
      refuse(
        `${JSON.stringify(h)} is ${h.length} characters — the reader keeps a name only if it is 3-80, so this line would never match.`
      );
    return h;
  });

  const p = rosterPath();
  mkdirSync(dirname(p), { recursive: true });
  const text = existsSync(p) ? readFileSync(p, "utf8") : "";
  const seen = existingNames(text);

  const toWrite = [];
  const report = [];
  for (const h of wanted) {
    const key = h.toLowerCase();
    if (seen.has(key)) {
      report.push(`roster: already present ${h}`);
      continue;
    }
    seen.add(key);
    toWrite.push(h);
    report.push(`roster: added ${h}`);
  }

  // Lines the reader can actually SEE: it slices the first 2000 of split(/\r?\n/), and a
  // trailing newline is not a line. Appending past that writes something nothing ever reads.
  const parts = text.split(/\r?\n/);
  const held = text === "" ? 0 : text.endsWith("\n") ? parts.length - 1 : parts.length;
  if (held + toWrite.length > MAX_LINES)
    refuse(
      `the roster already holds ${held} lines and the reader only ever sees the first ${MAX_LINES} — this entry would never fire. Prune the file instead.`
    );

  if (toWrite.length) {
    const added = new Date().toISOString().slice(0, 10);
    const rows = toWrite
      .map(
        (handle) =>
          JSON.stringify({
            handle,
            ...(platform ? { platform } : {}),
            ...(source ? { source } : {}),
            added,
          }) + "\n"
      )
      .join("");
    // Whole line or nothing: the rows and any repair newline go out in ONE call.
    appendFileSync(p, (text && !text.endsWith("\n") ? "\n" : "") + rows);
  }
  process.stdout.write(report.join("\n") + "\n");
}

try {
  main();
} catch (e) {
  refuse(`could not write the roster: ${(e && e.message) || e}`);
}
