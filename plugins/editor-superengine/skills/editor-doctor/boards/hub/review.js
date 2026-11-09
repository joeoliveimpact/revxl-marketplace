"use strict";
(async () => {
  const $ = id => document.getElementById(id), io = HubIO;
  const reel = new URLSearchParams(location.search).get("reel");
  try {
    const data = await io.json("/editor/hub/hub-data.json");
    const r = data.reels.find(r => r.id === reel);
    if (!r) throw new Error("This reel is not in the hub. Ask Claude to refresh your editor hub.");
    $("reel-name").textContent = r.title;
    if (r.preview_url) $("preview").src = r.preview_url;
    if (r.master_url) {
      $("master").src = r.master_url;
      $("master-section").hidden = false;
    }
    $("render-label").textContent = r.preview_name || "No finished preview yet.";
    const previous = await io.json(io.base(reel) + "review.json", {});
    $("review-note").value = previous.note || "";
    if (r.qa == null) $("qa").textContent = "QA hasn't run yet";
    else {
      const checks = Array.isArray(r.qa.checks) ? r.qa.checks : [];
      if (checks.length) {
        const ul = document.createElement("ul"); ul.className = "qa";
        checks.forEach(c => {
          const li = document.createElement("li");
          li.textContent = [c.label || c.check, c.state || c.level || c.status, c.detail || c.why || c.msg, c.value].filter(v => v != null).join(" · ");
          if (typeof c.at === "number") {
            const b = document.createElement("button"); b.className = "tchip"; b.textContent = c.at + "s";
            b.onclick = () => { $(r.master_url ? "master" : "preview").currentTime = c.at; }; li.append(" ", b);
          }
          ul.append(li);
        });
        $("qa").replaceChildren(ul);
      } else { const pre = document.createElement("pre"); pre.textContent = JSON.stringify(r.qa, null, 2); $("qa").replaceChildren(pre); }
      if (r.qa.aids) {
        const aids = document.createElement("div"); aids.id = "qa-aids";
        const url = path => io.base(reel) + path.split("/").map(encodeURIComponent).join("/");
        if (r.qa.aids.phone) {
          const p = document.createElement("p"), a = document.createElement("a");
          a.href = url(r.qa.aids.phone); a.textContent = "Phone-size copy";
          p.append(a); aids.append(p);
        }
        const strips = Array.isArray(r.qa.aids.strips) ? r.qa.aids.strips : [];
        [...strips, r.qa.aids.contact].filter(Boolean).forEach((path, i) => {
          const a = document.createElement("a"), img = document.createElement("img");
          a.href = url(path); img.src = a.href; img.loading = "lazy";
          img.alt = i < strips.length ? "Cut " + (i + 1) + " review strip" : "Contact sheet";
          img.style.cssText = "width:240px;max-width:100%;height:auto";
          a.append(img); aids.append(a, " ");
        });
        $("qa").append(aids);
      }
    }
    let pending = false;
    async function send(approve) {
      if (pending) return;
      pending = true;
      const note = $("review-note").value.trim();
      const body = {approve, preview: r.preview_name, note, sent_at: new Date().toISOString()};
      try {
        await io.send(reel, "review.json", body);
        $("fallback").hidden = true;
        io.status(approve ? "Sent. Preview approved." : "Sent. Review notes saved.");
      } catch (_) { io.failed(reel, "review.json", body); }
      finally { pending = false; }
    }
    $("approve").disabled = !r.preview_name;
    $("approve").onclick = () => send(true);
    $("send-review").onclick = () => send(false);
    window.ReviewReady = true;
  } catch (e) { $("error").textContent = e.message; }
})();
