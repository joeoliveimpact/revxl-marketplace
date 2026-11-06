/* All writes stay on the local board server. A paste line appears only after a failed POST. */
"use strict";
window.HubIO = (() => {
  const base = reel => "/videos/" + encodeURIComponent(reel) + "/";
  async function json(url, missing = null) {
    const r = await fetch(url, {cache: "no-store"});
    if (r.status === 404) return missing;
    if (!r.ok) throw new Error("Could not read saved work");
    return r.json();
  }
  async function post(url, body) {
    const r = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    if (!r.ok) throw new Error("Could not send (" + r.status + ")");
    return r.json();
  }
  async function send(reel, name, body) {
    return post(base(reel) + "__save?board=hub&name=" + encodeURIComponent(name), body);
  }
  function status(message) { document.getElementById("status").textContent = message; }
  function failed(reel, name, body) {
    status("Could not send. Your work is still here.");
    document.getElementById("fallback").hidden = false;
    document.getElementById("fallback-line").value = `From my editor hub, for ${reel}: save ${name} and use this Send: ${JSON.stringify(body)}`;
  }
  document.getElementById("copy").onclick = async () => {
    const line = document.getElementById("fallback-line");
    try { await navigator.clipboard.writeText(line.value); status("Copied. Paste it into Claude."); }
    catch (_) { line.focus(); line.select(); status("Select the line and copy it."); }
  };
  function heartbeat() { post("/heartbeat", {}).catch(() => {}); }
  heartbeat();
  setInterval(heartbeat, 30000);
  return {base, json, post, send, status, failed};
})();
