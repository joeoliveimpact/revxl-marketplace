import { readFileSync } from "node:fs";
import { session, V1, TSCRIPT, NOLOCAL, COSTS, M_NOTPLAIN, assert } from "../lib.mjs";

const curl = (path) => `curl -s "${V1}${path}"`;
function counted(cmd, expected, guard) {
  const s = session().seed({ spent: 0 });
  try {
    s.budget({ sessionBudget: 20000 });
    const r = s.run(cmd, { ...NOLOCAL, guard });
    const spent = s.state().spent;
    assert(r.exit === 0 && r.stderr === "" && r.raw === "" && r.decision === null && (expected === undefined || spent === expected),
      `silent pass commits exactly ${expected}`, { ...r, spent: s.state().spent });
    if (spent) assert(s.callLines().length === 1 && s.callLines()[0].worst === spent &&
      s.callLines()[0].committed === spent, "one record carries the exact count", r);
    return spent;
  } finally { s.cleanup(); }
}

function refused(cmd, expected, guard) {
  const s = session().seed({ spent: 0 });
  try {
    s.budget({ sessionBudget: 20000 });
    const before = s.stateRaw();
    const r = s.run(cmd, { ...NOLOCAL, guard, env: { ...NOLOCAL.env, CLAUDE_CODE_SESSION_ATTENDED: "0" } });
    const lines = s.logLines();
    assert(r.exit === 0 && r.stderr === "" && r.decision === "deny" && r.message === M_NOTPLAIN &&
      s.stateRaw() === before && s.callLines().length === 0, "malformed URL is not plain and commits nothing", r);
    assert(lines.length === 1 && lines[0].kind === "not-plain" &&
      (expected === undefined || lines[0].cmdWorst === expected), "refused URL retains its visible worst case", lines);
    return lines[0].cmdWorst;
  } finally { s.cleanup(); }
}

export default [
  ...[
    ["encoded", "q=a&x=%zz&deep_scan=%74rue"],
    ["bare-percent", "q=a&x=50%&deep_scan=%74rue"],
    ["semicolon", "q=a&x=%zz;deep_scan=%74rue"],
    ...["1", "yes", "True", "False", ""].map((value) => [value || "bare", `q=a&x=%zz&deep_scan${value ? "=" + value : ""}`]),
  ].map(([id, query]) => ({
    id: `G4A-price-${id}`, desc: "malformed URL is refused while its visible price retains the deep scan floor",
    fn(guard) { refused(curl("amazon/shop?" + query), 15, guard); },
  })),
  ...[
    ["instagram", "instagram/comment?q=a&x=%zz&deep_scan=true", 15, true],
    ["tiktok", "tiktok/comment?q=a&x=%zz&deep_scan=true", 6, true],
    ["tiktok-plain", "tiktok/comment?q=a&deep_scan=true", 6],
    ["tiktok-floor-kept", "tiktok/comment?q=a&deep_scan=true;a=1", 15],
    ["tiktok-floor-kept-glued", "tiktok/comment?q=a&deep_scan=trueX", 15],
    ["ads-true", "google/company/ads?q=a&x=%zz&get_ad_details=true", 25, true],
    ["ads-one", "google/company/ads?q=a&x=%zz&get_ad_details=1", 25, true],
  ].map(([id, path, expected, malformed]) => ({
    id: `G4A-conditional-${id}`, desc: "conditional price uses its own catalogue figure",
    fn(guard) { (malformed ? refused : counted)(curl(path), expected, guard); },
  })),
  {
    id: "G4A-price-controls", desc: "untouched guard control figures stay pinned",
    fn(guard) {
      for (const [path, expected] of [["amazon/shop", 1], ["instagram/comment", 15], ["tiktok/comment", 6], ["google/company/ads", 5]]) {
        for (const suffix of ["", "&deep_scan=false", "&deep_scan=0"]) refused(curl(path + "?q=a&x=%zz" + suffix), expected, guard);
      }
      for (const path of ["amazon/shop?q=deep_scan", "amazon/shop?q=a&nodeep_scan=true"]) counted(curl(path), 1, guard);
      counted(curl("amazon/shop?q=a"), 1, guard);
      for (const query of ["q=a&x=50%", "q=a&x=%zz;deep_scan=false", "q=a&x=%zz;deep_scan=0",
        "q=a&x=50%&deep_scan=false", "q=a&x=50%&deep_scan=0"]) refused(curl("amazon/shop?" + query), 1, guard);
      for (const value of ["false", "0"]) refused(curl("google/company/ads?q=a&x=%zz&get_ad_details=" + value), 5, guard);
    },
  },
  {
    id: "G4A-malformed-monotone", desc: "malformed URLs are refused and their visible prices never reduce 20 catalogue paths",
    fn(guard) {
      const paths = [
        "amazon/shop", "prism/leads", "prism/brief-check", "prism/video-intel", "prism/creator-vet",
        "search/everywhere", "youtube/video", "instagram/profile", "tiktok/profile", "google/company/ads",
        "instagram/comment", "tiktok/comment", "prism/comments", "prism/post-stats", "web/crawl",
        "web/scrape", "instagram/post/comments", "youtube/videos", "prism/investigate", "economy/imports",
      ];
      const catalogue = JSON.parse(readFileSync(COSTS, "utf8"));
      for (const path of paths) {
        assert(Object.keys(catalogue).some((key) => key.endsWith(" " + path)), `${path} is a catalogue path`);
        for (const suffix of ["", "&deep_scan=%74rue", "&get_ad_details=%74rue"]) {
          const cmd = curl(path + "?q=a" + suffix);
          const s = session().seed({ spent: 0 });
          try {
            s.budget({ sessionBudget: 20000 });
            const r = s.run(cmd, { ...NOLOCAL, guard });
            assert(r.exit === 0 && r.raw === "", "ordinary control passes silently", r);
            const before = s.state().spent;
            const after = refused(curl(path + "?q=a" + suffix + "&x=%zz"), undefined, guard);
            assert(after >= before, "appending malformed escape cannot lower the visible worst case");
          } finally { s.cleanup(); }
        }
      }
    },
  },
  ...[
    ["leads", curl(`prism/leads?query=x&include=${TSCRIPT}`), 50],
    ["brief", curl(`prism/brief-check?query=x&include=${TSCRIPT}`), 15],
    ["youtube", curl(`youtube/video/${TSCRIPT}?id=a`), 3],
    ["other", curl(`tiktok/post/${TSCRIPT}?url=X`), 10],
    ["batch", `curl -X POST "${V1}youtube/${TSCRIPT}s" -d '{"ids":["a"]}'`, 300],
    ["search", curl(`search/everywhere?query=x&include_${TSCRIPT}s=true`), 20],
  ].map(([id, cmd, expected]) => ({
    id: `G4A-gated-${id}`, desc: "transcript count includes the ungated floor and retains pinned controls",
    fn(guard) { counted(cmd, expected, guard); },
  })),
  ...[
    ["body-G", curl("web/sessions") + " -d 'a -G b'", 20],
    ["body-sG", curl("web/sessions") + " -d 'a -sG b'", 20],
    ["body-X", curl("web/sessions") + " -d 'x -X GET y'", 20],
    ["sibling", `curl -s -X GET "${V1}credits/balance" && ${curl("web/sessions")} -d '{"ttl_seconds":3600}'`, 20],
    ["free", curl("web/sessions"), 0],
    ["post", `curl -s -X POST "${V1}web/sessions"`, 20],
    ["post-after-get", `curl -s -X GET "${V1}credits/balance" && curl -s -X POST "${V1}web/sessions"`, 20],
    ["data", curl("web/sessions") + " -d '{}'", 20],
    ["overcount", curl("amazon/shop?q=a") + " -d 'x' && " + curl("web/sessions"), 21],
    ["gets", curl("amazon/shop?q=a") + " && " + curl("amazon/shop?q=b"), 2],
  ].map(([id, cmd, expected]) => ({
    id: `G4A-verb-${id}`, desc: "parsed per-call verb preserves both corrections and historical overcounts",
    fn(guard) { counted(cmd, expected, guard); },
  })),
];
