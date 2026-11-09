"use strict";
let DATA, CUR, TAB = null, layoutState = {}, queue = Promise.resolve();
const Hub = window.Hub = {ready: false, pending: 0};
const $ = id => document.getElementById(id), $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[c]));
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const current = () => DATA.reels.find(r => r.id === CUR);
const stage = () => DATA.stages[current().cur];
const pct = r => Math.round(r.lanes.reduce((n,l) => n + (l.total ? l.done/l.total : 0), 0) / r.lanes.length * 100);
const ago = at => !at ? "never" : Math.max(0, Math.round((Date.now() - new Date(at).getTime())/60000)) + " min ago";
const skillLabels = {captions:"Create captions", cover:"Pick a cover", qa:"Run QA", broll:"Add B-roll", trial:"Create a trial version", style:"Save this style", styles:"My styles", health:"Check my editor", goldmine:"Run Goldmine", handoff:"Hand off to your editor"};
const adjustments = {};

function pending(fn) {
  Hub.pending++;
  // Serialize whole-list Sends, including rapid double clicks. Re-read disk before each append.
  const work = queue.catch(() => {}).then(fn);
  queue = work.finally(() => { Hub.pending--; });
  return queue;
}
document.addEventListener("editor-controls-change", e => { $("controls").value = e.detail; });
if (window.BoardClient?.controls) $("controls").value = BoardClient.controls.mode();  // resolved before this script ran
$("controls").onchange = async e => {
  const value = e.target.value;
  try { localStorage.setItem("editor-controls", value); } catch (_) { /* blocked storage */ }
  BoardClient.controls.apply();
  await append(CUR || DATA.state_reel, "hub-requests.json", {kind:"controls", value, at:new Date().toISOString()});
};
function applyLayout(layout) {
  document.body.dataset.layout = layout === "full" ? "full" : "guided";
  $("layout").setAttribute("aria-pressed", String(layout === "full"));
}
async function saveLayout() {
  const state = {...layoutState, layout: document.body.dataset.layout === "full" ? "guided" : "full"};
  applyLayout(state.layout);
  await pending(async () => {
    try {
      const old = await HubIO.json(HubIO.base(DATA.state_reel) + "hub.state.json", {});
      Object.assign(state, old, {layout: state.layout});
      const res = await fetch(HubIO.base(DATA.state_reel) + "__state?name=hub", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(state)});
      if (!res.ok) throw new Error("State was not saved");
      layoutState = state; HubIO.status("Workspace view saved.");
    } catch (_) { HubIO.failed(DATA.state_reel, "hub.state.json", state); }
  });
}
async function append(reel, name, entry) {
  return pending(async () => {
    let body = [entry];
    try {
      const previous = await HubIO.json(HubIO.base(reel) + name, []);
      if (!Array.isArray(previous)) throw new Error("Saved list is not readable");
      const list = previous.concat(entry);
      body = list;
      await HubIO.send(reel, name, list);
      $("fallback").hidden = true; HubIO.status("Sent to Claude.");
      if (reel === CUR) await drawSaved(reel);
      return true;
    } catch (_) { HubIO.failed(reel, name, body); return false; }
  });
}

function boardFor(s) {
  // action ids are the Cockpit's; tab.stages belongs to the board's owning skill.
  if (["master", "post"].includes(s.id)) return "review";
  return DATA.boards.find(b => b.id.replace(/-board$/, "").replace(/-/g, "") === s.id)?.id ||
    DATA.boards.find(b => b.stages.includes(s.id))?.id;
}
function drawWall() {
  const reels = DATA.reels;
  $("wall").innerHTML = reels.map(r => `<button class="rc" data-reel="${esc(r.id)}" data-wait="${r.waiting_on}" aria-current="${r.id===CUR}">
    <span class="thumb">${r.frames[0] ? `<img src="${esc(r.frames[0])}" alt="">` : ""}${r.render_url ? `<video muted loop playsinline preload="none" src="${esc(r.render_url)}"></video>` : ""}<span class="bar"><i style="width:${pct(r)}%"></i></span></span>
    <span class="txt"><span class="code">${esc(r.id)}</span><span class="ttl">${esc(r.title)}</span><span class="stg">${esc(r.stage)} · ${pct(r)}%</span><span class="tag ${r.waiting_on}">${r.waiting_on === "claude" ? "Claude's move" : "Your move"}</span></span></button>`).join("") +
    '<div class="slot">Your next reel shows up here once its folder is in videos</div>';
  $$("#wall .rc").forEach(el => {
    const v = el.querySelector("video"), th = el.querySelector(".thumb");
    if (!v || reduced) return;
    const on = () => v.play().then(() => th.classList.add("playing")).catch(() => {});
    const off = () => { v.pause(); th.classList.remove("playing"); };
    el.addEventListener("mouseenter", on); el.addEventListener("mouseleave", off);
    el.addEventListener("focus", on); el.addEventListener("blur", off);
  });
  $("reel-list").innerHTML = reels.map(r => `<button class="ritem" data-reel="${esc(r.id)}" aria-current="${r.id===CUR}">${r.frames[0] ? `<img src="${esc(r.frames[0])}" alt="">` : ""}<span>${esc(r.title)}<small>${esc(r.stage)}</small></span></button>`).join("");
}
function drawHead() {
  const r = current(), s = stage();
  const hint = st => st.id === "sound" && r.sound_board === false ? "There are no sound cues to audition because this reel's sound is voice only. Ask Claude for sound effects or music to add some." : st.hint;
  $("crumb").textContent = "All reels / " + r.id;
  $("rhead").innerHTML = `<div><span class="code">${esc(r.id)}</span><h1>${esc(r.title)}</h1>${["resolve","mcp"].includes(DATA.config.nle) ? `<p id="nle">edits in ${esc(DATA.config.nle)}</p>` : ""}</div><div class="pct"><b>${pct(r)}%</b><span>of the edit done</span></div>`;
  $("baton").className = "baton " + r.waiting_on;
  $("baton").textContent = (r.waiting_on === "claude" ? "Claude's move" : "Your move") + ": " + (DATA.stages.find(st => st.id === r.open_sends[0]?.board)?.name || r.stage);
  $("lede").textContent = `${r.title} needs ${r.waiting_on === "claude" ? "Claude" : "you"} for ${r.stage.toLowerCase()}.`;
  $("steps").innerHTML = DATA.stages.map((st,i) => `<li class="${r.done[i] ? "done" : ""} ${i===r.cur ? "now" : ""}"><button class="step" data-step="${i}" ${i===r.cur ? 'aria-current="step"' : ""}><span class="n">${i+1}</span><span class="lb">${esc(st.name)}${st.optional ? " (optional)" : ""}<small>${esc(hint(st))}</small></span></button></li>`).join("");
  $("lanes").innerHTML = r.lanes.map(l => `<button class="lane" ${l.board ? `data-open="${esc(l.board)}"` : "disabled"}><span>${esc(l.label)}</span><span class="ln">${l.total > 0 && l.done >= l.total ? "done" : l.total > 0 && l.done > 0 ? `${l.done}/${l.total}` : "not started"}</span><span class="track"><i style="width:${l.total ? l.done/l.total*100 : 0}%;--c:var(--${l.layer})"></i></span></button>`).join("");
  const bid = s.id === "sound" && r.sound_board === false ? null : boardFor(s);
  $("move").className = "move " + r.waiting_on;
  $("move").innerHTML = `<div class="lead"><span class="big">${r.cur+1}</span><span class="of">Step ${r.cur+1} of ${DATA.stages.length}</span></div><h2>${esc(r.open_sends.length ? "Your Send is ready for Claude" : s.head)}</h2><p class="what">${esc(s.id === "sound" && r.sound_board === false ? hint(s) : r.open_sends.length ? "Claude picks it up when you say go. Nothing happens until then." : hint(s))}</p>${bid ? `<button class="btn primary" data-open="${esc(bid)}">Start: ${esc(bid === "review" ? "Master review" : DATA.boards.find(b=>b.id===bid)?.label)}</button>` : ""}`;
  const frames = r.frames;
  $("strip").innerHTML = frames.map(f => `<img src="${esc(f)}" alt="">`).join("") + '<span class="playhead" id="ph"></span>';
  if (r.frames[0]) { $("glowimg").src = r.frames[0]; $("glow").classList.add("on"); }
  else $("glow").classList.remove("on");
  const v = $("vid");
  if (v.getAttribute("src") !== r.render_url) { if (r.render_url) v.src = r.render_url; else { v.removeAttribute("src"); v.load(); } }
  if (r.frames[0]) v.poster = r.frames[0]; else v.removeAttribute("poster");
  $("vidcap").textContent = r.render_label;
  const cover = DATA.boards.find(b=>b.stages.includes("cover"));
  $("coverbox").innerHTML = r.cover_url ? `<img src="${esc(r.cover_url)}" alt="Your cover">` : `<button class="btn" ${cover ? `data-open="${esc(cover.id)}"` : 'data-skill="cover"'}>Pick your cover</button><p class="writes">${cover?.built ? "Open Cover Picker" : "Cover Picker is not built yet"}</p>`;
  const blocks = r.blocks;
  $("attention-card").hidden = !blocks.length;
  $("attention").innerHTML = blocks.map(b=>`<li>${esc(b.msg)}${b.where ? " · " + esc(typeof b.where === "string" ? b.where : JSON.stringify(b.where)) : ""}</li>`).join("");
  $("actions").innerHTML = ["captions", "cover", "qa", "broll", "trial"].map(k=>`<button class="act" data-skill="${k}">${skillLabels[k]}</button>`).join("");
  if (["resolve", "mcp"].includes(DATA.config.nle)) {
    const choices = DATA.config.nle === "resolve" ? ["DaVinci Resolve", "Another editor (files)"] : ["Another editor (files)"];
    $("actions").insertAdjacentHTML("beforeend", `<label for="handoff-editor">Your editor</label><select id="handoff-editor">${choices.map(c=>`<option>${esc(c)}</option>`).join("")}</select><button class="act" data-skill="handoff">${skillLabels.handoff} · Send</button>`);
    $("handoff-editor").value = adjustments[CUR]?.handoffEditor || choices[0];
    $("handoff-editor").onchange = e => { (adjustments[CUR] ||= {}).handoffEditor = e.target.value; };
  }
}
function drawTabs() {
  const tabs = DATA.boards;
  $("tabs").innerHTML = tabs.map(b=>`<a role="tab" id="tab-${esc(b.id)}" data-board="${esc(b.id)}" aria-controls="panel" aria-selected="${TAB===b.id}" tabindex="${TAB===b.id ? 0 : -1}" ${b.built ? `href="/editor/${encodeURIComponent(b.id)}/?reel=${encodeURIComponent(CUR)}"` : 'aria-disabled="true"'}>${esc(b.label)}${b.built ? "" : " · not built yet"}</a>`).join("") + `<a role="tab" id="tab-review" data-review="true" href="/editor/hub/review.html?reel=${encodeURIComponent(CUR)}" aria-controls="panel" aria-selected="${TAB==='review'}">Master review</a>`;
  const selected = $("tabs").querySelector('[aria-selected="true"]') || $("tabs").firstElementChild;
  if (selected) selected.tabIndex = 0;
  if (TAB) openBoard(TAB);
}
function openBoard(id) {
  const r = current(), b = id === "review" ? {id, label:"Master review", built:true} : DATA.boards.find(b=>b.id===id);
  if (!b) return;
  TAB = id;
  $$("#tabs [role=tab]").forEach(el=>{ const on = (el.dataset.board || (el.dataset.review ? "review" : "")) === id; el.setAttribute("aria-selected",String(on)); el.tabIndex=on ? 0 : -1; });
  const own = $("owntab"), panel = $("panel"); own.hidden = !b.built;
  if (!b.built) { own.removeAttribute("href"); panel.innerHTML = `<p class="empty">${esc(b.label)} is not built yet.</p>`; }
  else {
    const path = id === "review" ? "/editor/hub/review.html" : "/editor/" + encodeURIComponent(id) + "/";
    const src = path + "?reel=" + encodeURIComponent(CUR);
    own.href = src;
    // Preserve the board and its unsaved work whenever its URL is unchanged.
    if (panel.querySelector("iframe")?.getAttribute("src") !== src)
      panel.innerHTML = `<div class="frame"><iframe src="${esc(src)}" title="${esc(b.label)}"></iframe></div>`;
  }
  panel.setAttribute("aria-labelledby", "tab-" + id);
  const stamps = r.boards[id];
  const sent = stamps ? Math.max(0, ...Object.values(stamps.sends).filter(v=>v!=null)) : 0;
  $("bhint").textContent = `${b.label}${b.built ? " saves as you work" : " is not built yet"} · last auto-save ${ago(stamps?.saved_at)} · last sent ${ago(sent)}`;
  drawAdjust();
}
function drawAdjust() {
  const r=current(), a=adjustments[CUR] || (adjustments[CUR]={pause:0.28,music:-18,duck:true,look:"",strength:0.6});
  const stages=DATA.boards.find(b=>b.id===TAB)?.stages || [stage().id];
  let kind=stages.includes("grade") ? "grade" : stages.includes("sound") ? "sound" : stages.includes("cut") ? "cut" : null;
  $("adjust").dataset.kind = kind || "";
  const field=(label,key,min,max,step)=>`<label class="field">${label}<input type="range" data-adjust="${key}" min="${min}" max="${max}" step="${step}" value="${a[key]}"><output data-output="${key}">${a[key]}</output></label>`;
  $("adjust").innerHTML = kind === "grade" ? `<label>Look<select data-adjust="look"><option value="">Choose a look</option>${["none","natural","warm","punchy","soft-matte","mono"].map(l=>`<option value="${l}" ${a.look===l ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></label>${field("Strength", "strength",0,1,0.05)}<p class="writes">Request a look; the Grade Board shows the actual grade.</p>` :
    kind === "sound" ? `${field("Music level (dB)","music",-30,-6,1)}<label><input type="checkbox" data-adjust="duck" ${a.duck ? "checked" : ""}> Lower the music while you talk</label>` :
    kind === "cut" ? field("Pause after commas (s)","pause",0.20,0.40,0.01) : '<p class="writes">Open a board for its controls.</p>';
  if (kind) $("adjust").insertAdjacentHTML("beforeend",`<button class="btn" id="adjust-send" ${kind==='grade'&&!a.look ? "disabled" : ""}>Send adjustment</button>`);
}
async function drawSaved(reel) {
  const [notes, requests] = await Promise.all([HubIO.json(HubIO.base(reel)+"reel-notes.json",[]),HubIO.json(HubIO.base(reel)+"hub-requests.json",[])]);
  if (reel !== CUR) return;
  $("note-list").innerHTML = (Array.isArray(notes) ? notes : []).map(n=>`<li>${esc(n.kind || "Note")} · ${Math.floor(n.at||0)}s · ${esc(n.text)}</li>`).join("") || '<li class="empty">No notes yet.</li>';
  $("queue").innerHTML = (Array.isArray(requests) ? requests : []).slice().reverse().map(q=>`<li>${esc(q.ask || (q.kind === "controls" ? "Controls: " + q.value : ""))}<small>Sent · ${esc(ago(q.at))}</small></li>`).join("") || '<li class="empty">Nothing sent yet.</li>';
}
function drawPages() {
  $("styles").innerHTML = (DATA.styles || []).map(s=>`<form data-style-id="${esc(s.id)}"><p>${esc(s.label)}${s.default ? " (default)" : ""}</p><label class="dfield" for="style-${esc(s.id)}">New name for ${esc(s.label)}<input id="style-${esc(s.id)}" name="label" type="text" size="12" maxlength="40" value="${esc(s.label)}" required></label><button class="btn" type="submit">Rename</button>${s.default ? "" : '<button class="btn" type="button" data-style-action="default">Make default</button>'}${s.auto && (s.auto.ready || s.auto.on) ? `<button class="btn" type="button" data-style-action="auto" aria-pressed="${!!s.auto.on}" aria-label="Auto edit for ${esc(s.label)}">Auto edit: ${s.auto.on ? "On" : "Off"}</button>` : `<small>Auto edit unlocks after ${esc(s.auto ? s.auto.threshold : 3)} smooth reels (${esc(s.auto ? s.auto.good_in_a_row : 0)} so far)</small>`}</form>`).join("") || '<p class="empty">No saved styles yet.</p>';
  const health = DATA.health;
  $("health-list").innerHTML = health.map(h=>{
    if (typeof h === "string") { const m=h.match(/^STATUS (\S+) (ok|warn|missing) (.*)$/); h=m ? {component:m[1],level:m[2],detail:m[3]} : {detail:h}; }
    return `<li><span class="word" data-state="${h.matters === false ? "optional" : esc(h.level)}">${h.matters === false ? "Optional" : esc(({ok:"✓ OK",warn:"⚠ Needs a look",missing:"✗ Missing"})[h.level] || "Check")}</span><div><b>${esc(h.label || h.component)}</b><span class="dt">${esc(h.detail)}</span>${h.fix ? `<span class="dt">${esc(h.fix)}</span>` : ""}</div></li>`;
  }).join("") || '<li>No health check yet. Ask Claude to check my editor.</li>';
  $("healthwarn").hidden = !health.some(h=>typeof h === "string" ? / (warn|missing) /.test(h) : h.matters !== false && h.level !== "ok");
  const gold = DATA.goldmine;
  $("gold-data").innerHTML = gold ? `<p>From n = ${esc(gold.n)} reels · ${esc(gold.breakouts)} breakouts</p><table><thead><tr><th>Breakout</th><th>Compared with baseline</th><th>Comment rate</th></tr></thead><tbody>${gold.ranking.map((x,i)=>`<tr><td>${esc(x.title || x.label || (x.handle ? "@"+String(x.handle).replace(/^@+/, "") : "") || "Breakout "+(i+1))}</td><td>${x.benchmark_x == null ? "Not enough baseline reels" : esc(typeof x.benchmark_x === "number" ? x.benchmark_x.toFixed(x.benchmark_x >= 10 ? 0 : 1) : x.benchmark_x)+"×"}</td><td>${x.comment_rate == null ? "Not measured" : esc(typeof x.comment_rate === "number" ? (x.comment_rate*100).toFixed(2)+"%" : x.comment_rate)}</td></tr>`).join("")}</tbody></table><p class="writes">CTA comment rates are upper bounds.</p>` : '<div class="empty"><b>No Goldmine run yet.</b> A run uses your SocialCrawl credits; Claude shows the cost and asks first.</div>';
}
async function selectReel(id) {
  if (!DATA.reels.some(r=>r.id===id)) return;
  const changed=CUR!==id;
  CUR=id;
  if (changed) { $("note").value=""; $("request-detail").value=""; TAB=null; $("panel").innerHTML='<p class="empty">Choose a board to begin.</p>'; }
  const url=new URL(location); url.searchParams.set("reel",CUR); history.replaceState(null,"",url);
  drawWall(); drawHead(); drawTabs(); drawAdjust();
  await drawSaved(id);
}
function request(skill) {
  if (!current()) { HubIO.status("Add a reel folder before sending a request."); return; }
  const reel=CUR, a=adjustments[reel] || {}, details=$("request-detail").value.trim();
  if (["trial","broll"].includes(skill) && !details) { $("advanced-request").open=true; $("request-detail").focus(); HubIO.status("Add the details, then send."); return; }
  const ask=skill === "goldmine" ? "Run Goldmine for my niche. Show me the SocialCrawl credit cost and ask before spending anything." :
    skill === "health" ? "Check my editor and fix what's missing." : `${skillLabels[skill] || "Adjust " + skill} for ${reel}.${details ? " " + details : ""}`;
  const entry={at:new Date().toISOString(),reel,skill,ask,choices:{...a}};
  if (skill === "handoff") {
    if (!["resolve", "mcp"].includes(DATA.config.nle)) return;
    const editor = $("handoff-editor").value;
    entry.choices = {editor};
    entry.ask = `${skillLabels.handoff} for ${reel}: ${editor}.${details ? " " + details : ""}`;
  }
  return append(reel,"hub-requests.json",entry);
}
function requestStyle(form, action) {
  if (!current()) { HubIO.status("Add a reel folder before sending a request."); return; }
  const style = DATA.styles.find(s=>s.id===form.dataset.styleId), id = style.id;
  const label = action === "rename" ? form.elements.label.value.trim() : style.label;
  if (!label) { form.elements.label.focus(); return; }
  if (action === "auto") {
    const on = !style.auto.on, ask = `Turn Auto edit ${on ? "on" : "off"} for ${style.label}`;
    return append(CUR,"hub-requests.json",{at:new Date().toISOString(),reel:CUR,skill:"styles",ask,choices:{action,id,label,on}});
  }
  const ask = action === "rename" ? `Rename ${style.label} to ${label}` : `Make ${style.label} my default`;
  return append(CUR,"hub-requests.json",{at:new Date().toISOString(),reel:CUR,skill:"styles",ask,choices:{action,id,label}});
}
function route() {
  const page=["health","goldmine"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "reels";
  ["reels","health","goldmine"].forEach(k=>$("v-"+k).hidden=k!==page);
  $$(".views a").forEach(a=>a.setAttribute("aria-current",a.hash==="#"+page ? "page" : "false"));
}
async function load(first=false) {
  try {
    const next=await HubIO.json("/editor/hub/hub-data.json");
    if (!next || !Array.isArray(next.reels)) throw new Error("No hub data");
    DATA=next; $("error").hidden=true; drawPages();
    if (first && DATA.state_reel) { layoutState=await HubIO.json(HubIO.base(DATA.state_reel)+"hub.state.json",{}); applyLayout(layoutState.layout); }
    $("layout").disabled=!DATA.state_reel;
    $("controls").disabled=!DATA.state_reel;
    $("work").hidden=!DATA.reels.length;
    if (DATA.reels.length) {
      const chosen=DATA.reels.find(r=>r.id===CUR) || DATA.reels.find(r=>r.id===new URLSearchParams(location.search).get("reel")) || [...DATA.reels].sort((a,b)=>b.activity-a.activity)[0];
      await selectReel(chosen.id);
    } else { CUR=null; drawWall(); $("lede").textContent="Add your first reel folder to videos."; $("baton").textContent="Nothing in the edit"; }
    $("fresh").textContent="Refreshed " + ago(DATA.refreshed);
    route(); Hub.ready=true;
  } catch (_) { $("error").hidden=false; $("error").textContent="Couldn't read the hub's data. Ask Claude to refresh your editor hub, then press Reload."; }
}
document.addEventListener("click",e=>{
  const el=e.target.closest("[data-reel],[data-board],[data-review],[data-open],[data-skill],[data-step],[data-filter]");
  if (!el) return;
  const d=el.dataset;
  if (d.reel) { selectReel(d.reel).catch(()=>HubIO.status("Could not read saved notes.")); return; }
  if (d.board || d.review || d.open) { e.preventDefault(); openBoard(d.board || d.open || "review"); return; }
  if (d.skill) { request(d.skill); return; }
  if (d.step) { const id=boardFor(DATA.stages[+d.step]); if(id) openBoard(id); return; }
  if (d.filter) { $("wall").dataset.filter=d.filter; $$("[data-filter].chip").forEach(b=>b.setAttribute("aria-pressed",String(b===el))); }
});
$("tabs").onkeydown=e=>{
  if (!["ArrowRight","ArrowLeft","Home","End"].includes(e.key)) return;
  e.preventDefault(); const tabs=$$("#tabs [role=tab]"), i=tabs.indexOf(document.activeElement);
  const n=e.key==="Home" ? 0 : e.key==="End" ? tabs.length-1 : (i+(e.key==="ArrowRight" ? 1 : tabs.length-1))%tabs.length;
  tabs[n].focus(); tabs[n].click();
};
$("adjust").oninput=e=>{
  const k=e.target.dataset.adjust;if(!k)return;
  adjustments[CUR][k]=e.target.type==="checkbox" ? e.target.checked : ["look"].includes(k) ? e.target.value : +e.target.value;
  const out=$("adjust").querySelector(`[data-output="${k}"]`); if(out)out.textContent=adjustments[CUR][k];
  if(k==="look")$("adjust-send").disabled=!e.target.value;
};
$("adjust").onclick=e=>{if(e.target.id==="adjust-send")request("adjust-"+$("adjust").dataset.kind);};
$("notes-form").onsubmit=e=>{
  e.preventDefault();const text=$("note").value.trim();if(!text)return;
  const reel=CUR;append(reel,"reel-notes.json",{text,kind:$("note-kind").value,at:$("vid").currentTime || 0,sent_at:new Date().toISOString()}).then(ok=>{if(ok&&CUR===reel&&$("note").value.trim()===text)$("note").value="";});
};
$("styles").onsubmit=e=>{e.preventDefault();requestStyle(e.target,"rename");};
$("styles").onclick=e=>{if(e.target.dataset.styleAction)requestStyle(e.target.closest("form"),e.target.dataset.styleAction);};
$("layout").onclick=saveLayout;
$("reload").onclick=()=>load();
let key=0;
function scrub(f,play=false) {
  const v=$("vid");if(!v.duration)return;
  v.currentTime=Math.min(v.duration-0.01,Math.max(0,f)*v.duration);
  $("ph").style.left=(f*100)+"%";
  $("strip").setAttribute("aria-valuenow",String(Math.min(11,Math.floor(f*12))));
  if(play)v.play().catch(()=>{});
}
$("strip").onpointermove=e=>{ const b=$("strip").getBoundingClientRect();if($("vid").paused)scrub(Math.max(0,Math.min(1,(e.clientX-b.left)/b.width))); };
$("strip").onclick=e=>{ const b=$("strip").getBoundingClientRect();scrub(Math.max(0,Math.min(1,(e.clientX-b.left)/b.width)),true); };
$("strip").onkeydown=e=>{if(e.key==="Enter"){$("vid").play().catch(()=>{});return;}if(!["ArrowRight","ArrowLeft"].includes(e.key))return;e.preventDefault();key=Math.max(0,Math.min(11,key+(e.key==="ArrowRight"?1:-1)));scrub((key+0.5)/12);};
addEventListener("hashchange",route);
setInterval(()=>load(),15000);
load(true);
