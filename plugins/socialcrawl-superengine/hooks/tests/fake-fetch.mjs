/*
 * Test-only `--import` preload for the credit guard's balance read (R14b). BUILD-TIME TOOLING —
 * never loaded by the plugin. It replaces globalThis.fetch before the guard runs, so a fixture
 * can feed and count balance reads and nothing reaches the network (the cap.mjs X1 precedent).
 *
 *   FAKE_FETCH      a JSON array of replies, one per request; the last one repeats
 *   FAKE_FETCH_LOG  a file that gets one line per request, {url, key, signal}: key and signal
 *                   are booleans (the fake key was sent; an abort signal was passed), never the key.
 *                   Its line count is also how the reply index carries across the separate guard
 *                   processes of one session.
 *
 * FAKE_FETCH also accepts {balance: [...], transactions: [...]}: independent reply lists,
 * indexed by requests to each URL, keep balance and ledger responses separate.
 * A reply is {status, body, headers?} (a string body is sent as-is, anything else as JSON),
 * {throw: true} (a network error), or {hang: true}: no answer until the caller's signal aborts,
 * holding a timer the whole time, as a real open socket keeps the process alive.
 */
import { appendFileSync, readFileSync } from "node:fs";

const replies = JSON.parse(process.env.FAKE_FETCH || "[]");
const LOG = process.env.FAKE_FETCH_LOG;

globalThis.fetch = async (url, init = {}) => {
  const transactions = new URL(url).pathname.endsWith("/transactions");
  const list = Array.isArray(replies) ? replies : replies[transactions ? "transactions" : "balance"] || [];
  let n = 0;
  try {
    const prior = readFileSync(LOG, "utf8").split("\n").filter(Boolean);
    n = Array.isArray(replies) ? prior.length : prior.map(JSON.parse).filter(r => new URL(r.url).pathname.endsWith("/transactions") === transactions).length;
  } catch {}
  const sent = new Headers(init.headers || {}).get("x-api-key");
  appendFileSync(LOG, JSON.stringify({ url: String(url), key: !!sent && sent === process.env.SOCIALCRAWL_API_KEY, signal: !!init.signal }) + "\n");
  const r = list[Math.min(n, list.length - 1)] || { throw: true };
  if (r.throw) throw new TypeError("fetch failed");
  if (r.hang) {
    return new Promise((_, reject) => {
      const t = setTimeout(() => reject(new Error("fake-fetch: no abort signal fired in 60 s")), 60000);
      if (init.signal) init.signal.addEventListener("abort", () => { clearTimeout(t); reject(init.signal.reason); });
    });
  }
  return new Response(typeof r.body === "string" ? r.body : JSON.stringify(r.body), {
    status: r.status || 200,
    headers: { "content-type": "application/json", ...r.headers },
  });
};
