#!/usr/bin/env node
/*
 * Fixture runner for hooks/credit-guard.mjs and hooks/research-suggest.mjs.
 *
 *   node plugins/socialcrawl-superengine/hooks/tests/run.mjs
 *   node .../run.mjs D1            # run only fixtures whose id contains "D1"
 *
 * Exits 0 only when every fixture passes; any mismatch exits 1 with the failing assertion and
 * the guard's own output. BUILD-TIME TOOLING — hooks.json names the guard by an explicit path,
 * so nothing in this directory is ever loaded by the plugin at runtime.
 *
 * Zero credits, zero network. The guard reads the balance when none is cached, so every guard run
 * is offline by default (lib.mjs: no key, a scratch home, dead proxies), and the balance fixtures
 * answer the read through the fake-fetch.mjs preload; the ledger and X1 exit fixtures talk to a
 * loopback server only. The suggester reads the prompt, costs.json, the entities roster and the
 * unattended log.
 */
import regression from "./fixtures/regression.mjs";
import defects from "./fixtures/defects.mjs";
import closeCriteria from "./fixtures/close-criteria.mjs";
import sweep from "./fixtures/sweep.mjs";
import property from "./fixtures/property.mjs";
import cap from "./fixtures/cap.mjs";
import plain from "./fixtures/plain.mjs";
import suggest from "./fixtures/suggest.mjs";
import roster from "./fixtures/roster.mjs";
import ledger from "./fixtures/ledger.mjs";
import price from "./fixtures/price.mjs";
import jev from "./fixtures/jev.mjs";
import balance from "./fixtures/balance.mjs";

const SUITES = [
  ["close-criteria", closeCriteria],
  ["regression", regression],
  ["defects", defects],
  ["sweep", sweep],
  ["property", property],
  ["cap", cap],
  ["plain", plain],
  ["suggest", suggest],
  ["roster", roster],
  ["ledger", ledger],
  ["price", price],
  ["jev", jev],
  ["balance", balance],
];

const filter = process.argv[2] || "";
let pass = 0;
const failures = [];

for (const [suite, fixtures] of SUITES) {
  const selected = fixtures.filter((f) => !filter || f.id.includes(filter));
  if (!selected.length) continue;
  console.log(`\n== ${suite} (${selected.length})`);
  for (const f of selected) {
    try {
      f.fn();
      pass++;
      console.log(`  PASS  ${f.id} — ${f.desc}`);
    } catch (e) {
      failures.push({ suite, id: f.id, desc: f.desc, err: e });
      console.log(`  FAIL  ${f.id} — ${f.desc}`);
    }
  }
}

if (failures.length) {
  console.log(`\n---- ${failures.length} FAILURE(S) ----`);
  for (const f of failures) {
    console.log(`\n[${f.suite}] ${f.id}`);
    console.log(`  ${f.err && f.err.message ? f.err.message : f.err}`);
  }
}

const total = pass + failures.length;
console.log(`\n${pass}/${total} fixtures passed.`);
if (!total) {
  console.log(`No fixture matched the filter ${JSON.stringify(filter)}.`);
  process.exit(1);
}
process.exit(failures.length ? 1 : 0);
