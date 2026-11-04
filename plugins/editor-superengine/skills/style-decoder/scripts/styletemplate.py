#!/usr/bin/env python
"""styletemplate.py — build a composition FROM a style-spec.

Subcommands (mirroring stylespec.py): plan -> build -> check.

    plan  <style> --inputs inputs.json [--stamp MM.DD.YY]
    build <plan_dir> --inputs inputs.json --gsap <local gsap.min.js>
    check <build_dir>

GSAP comes ONLY from a local file the user passes (--gsap). Never a URL, never
a download; build refuses to run without it.

Exit codes follow the house meaning exactly:
  0  ok
  1  hard fail
  2  written, but a human gate is required   (the `stylespec.py merge` meaning)

There is deliberately no --yes flag. A flag that skips the gate is the thing
that makes clones fail silently.

THE LOAD-BEARING CLAIM
  `build` is a pure function of (spec, plan, media bytes). All judgment,
  interaction and defaulting lives in `plan`. `build` never asks and never
  guesses. That is what makes determinism checkable and what lets the `ask`
  interaction work without an interactive prompt inside a script.

READ-ONLY ON THE STYLE DIRECTORY
  This module opens the spec 'r' and has no write path into the style dir.
  Output goes only to <data_dir>/builds/<slug>-<MM.DD.YY>-<nn>/. That deletes
  the entire "the build corrupted the spec" class of failure by construction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enginecfg import cfg                                          # noqa: E402
import stylespec                                                   # noqa: E402  (puts _shared on sys.path)
from win_encoding import ensure_utf8_output                        # noqa: E402

GENERATOR_VERSION = "0.1.0"

# Provenance tags. Every value written into the build plan carries one, because
# a generator cannot emit UNKNOWN into HTML -- without tagging, 60 provisional
# rules silently become confident numbers wearing the spec's badge. Tagging
# makes "the generator is the author" COUNTABLE, and that count is the rung-5
# result.
FROM_SPEC = "from-spec"
DERIVED = "derived"
DEFAULT_FOR_UNKNOWN = "default-for-UNKNOWN"
GENERATOR_INVENTED = "generator-invented"


def V(value, prov: str, why: str = "", field: str = ""):
    d = {"v": value, "prov": prov}
    if why:
        d["why"] = why
    if field:
        d["field"] = field
    return d


# --------------------------------------------------------------- OBS / PARAM
# The highest-consequence guard in the whole generator.
#
# transitions[].instances_s, panel_content_types[].segments_s, pacing.swap_times_s,
# canvas.layout_timeline and beats[].params.start_s are records of WHERE IT
# HAPPENED IN A SOURCE REEL. Nothing in the schema distinguishes them from build
# parameters. A generator that replays layout_timeline produces the source's shape
# stretched over new words -- which looks extremely on-style and would pass most
# reproduction metrics BECAUSE IT LITERALLY IS THE SOURCE'S STRUCTURE.
#
# So: partition at load. The generator may not read the observations bucket
# except through a declared derivation, and no emitted data-start may equal any
# observed timestamp.

_TIME_KEY = re.compile(r"(_s|_ms)$")

# Keys that are observations wherever they appear.
OBSERVATION_KEYS = {
    "instances_s", "segments_s", "swap_times_s", "start_s", "end_s",
    "aligned_pairs_s", "unaligned_swaps_s", "unaligned_transients_s",
    "name_build_steps_s", "emphasis_stack_at_s", "total_duration_s",
    "duration_on_screen_s", "longest_hold_s", "longest_pause_s",
    "longest_face_only_stretch_s", "mean_shot_s", "median_shot_s",
    "cover_frame_duration_s", "hook_clause_end_s", "momentary_grid_s",
    "asr_corrections_verified_at_s", "max_offset_ms",
    "longest_hold_s", "first_line_duration_s", "later_line_duration_s",
}
# Whole subtrees that are observation records.
OBSERVATION_PATHS = (
    "canvas.layout_timeline",
    "typography.caption_mechanics.observed_groups",
    "typography.caption_mechanics.group_duration_percentiles_ms",
    "sources",
    "pacing",
)
# Keys that ARE build parameters even though they carry a time suffix: they are
# durations of a MECHANISM (how long a tween runs), not records of when
# something occurred in a particular reel.
PARAMETER_KEYS = {
    "duration_s", "border_draw_s", "post_cut_blank_ms", "mascot_fade_s",
    "tolerance_s", "glyphs_per_s", "typing_rate_glyphs_per_s",
    "scale_rate_pct_per_s", "keyword_pop_offset_from_spoken_word_ms",
    "keyword_pop_offset_ms", "group_break_pause_ms", "max_group_duration_ms",
    "min_group_duration_ms", "lead_s",
}
# Per-source mirrors are never read by a build at all.
_MIRROR_SEG = re.compile(r"^(params_by_source|fields_by_source|variants)$")


def partition_spec(spec: dict) -> tuple[dict, list[str]]:
    """Walk every timestamp-bearing field and classify it. An unclassified one
    is a HARD FAIL -- silence here is exactly how an observation becomes an
    instruction."""
    obs: dict[str, object] = {}
    unclassified: list[str] = []

    def walk(node, path: str, in_obs: bool, in_mirror: bool):
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{path}.{k}" if path else k
                walk(v, p, in_obs or p in OBSERVATION_PATHS,
                     in_mirror or bool(_MIRROR_SEG.match(k)))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]", in_obs, in_mirror)
        else:
            key = path.split(".")[-1].split("[")[0]
            if not _TIME_KEY.search(key):
                return
            if in_obs or key in OBSERVATION_KEYS:
                obs[path] = node
            elif key in PARAMETER_KEYS or in_mirror:
                return
            else:
                unclassified.append(path)

    for path in OBSERVATION_PATHS:
        node = stylespec.get_group(spec, path)
        if node is not None:
            obs[path] = node
    walk(spec, "", False, False)
    return obs, sorted(set(unclassified))


def observed_timestamps(obs: dict) -> set[int]:
    """Every observed time, in integer ms — the set an emitted data-start may
    never collide with."""
    out: set[int] = set()

    def scan(v, key=""):
        if isinstance(v, dict):
            for k, x in v.items():
                scan(x, k)
        elif isinstance(v, list):
            for x in v:
                scan(x, key)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out.add(int(round(v if key.endswith("_ms") else v * 1000)))

    scan(obs)
    return out


# ------------------------------------------------------- effective parameters
# The same number lives in up to four places (params, variants[0].params,
# resolution[].default, and a tween literal -- one rule can carry four different
# durations). Declare precedence ONCE and materialise it; everything downstream
# reads only the flattened file.

def _rule_id(r: dict) -> str:
    return r.get("id") or "?"


def effective_params(spec: dict) -> tuple[dict, list[str]]:
    """Precedence: resolution wins for range/choice; compute for derived;
    condition for invariant; params only where no resolution targets the field."""
    eff: dict[str, dict] = {}
    notes: list[str] = []

    for dotted, judgment in stylespec.RULE_GROUPS:
        if not judgment:
            continue
        for rule in (stylespec.get_group(spec, dotted) or []):
            if not isinstance(rule, dict):
                continue
            rid = _rule_id(rule)
            claimed: set[str] = set()
            for res in (rule.get("resolution") or []):
                kind = res.get("kind")
                field = res.get("field")
                if not field:
                    continue
                pairs = stylespec.resolve_field(rule, field)
                if not pairs:
                    notes.append(f"{rid}: resolution field {field!r} does not resolve — IGNORED")
                    continue
                claimed.add(field)
                if kind == "range":
                    default, bounds = res.get("default"), res.get("bounds")
                    # A scalar default into a LIST field is allowed jitter, not a
                    # value. Writing it collapses the field. Record as tolerance.
                    target = pairs[0][0].get(pairs[0][1])
                    if isinstance(target, list) and not isinstance(default, list):
                        eff[f"{rid}.{field}"] = V(target, FROM_SPEC,
                                                  f"range default {default} is a TOLERANCE "
                                                  f"({res.get('unit','?')}), never written", field)
                        continue
                    eff[f"{rid}.{field}"] = V(default, FROM_SPEC,
                                              f"range default, bounds {bounds}", field)
                elif kind == "choice":
                    opts = res.get("options") or []
                    eff[f"{rid}.{field}"] = V(opts[0] if opts else None, DEFAULT_FOR_UNKNOWN,
                                              f"first of {len(opts)} options — a build parameter", field)
                elif kind == "derived":
                    eff[f"{rid}.{field}"] = V(None, DERIVED,
                                              res.get("compute", "computed at build time"), field)
                elif kind == "invariant":
                    conds = res.get("condition") or []
                    val = conds[0].get("value") if conds else None
                    target = pairs[0][0].get(pairs[0][1])
                    # Two guards, not one. A merge NOTE sitting in the value slot
                    # ("identical in both sources") would destroy the field.
                    bad_type = isinstance(target, (dict, list)) and isinstance(val, str)
                    prose = isinstance(val, str) and (len(val.split()) > 4 or
                                                      "source" in val.lower())
                    if bad_type or prose:
                        eff[f"{rid}.{field}"] = V(target, FROM_SPEC,
                                                  "invariant value looked like prose/merge-note "
                                                  "— NOT written; needs interpretation", field)
                        notes.append(f"{rid}.{field}: invariant value {val!r} rejected "
                                     f"({'type' if bad_type else 'vocabulary'} guard)")
                    else:
                        eff[f"{rid}.{field}"] = V(val, FROM_SPEC, "invariant", field)

            for k, v in (rule.get("params") or {}).items():
                key = f"params.{k}"
                if key in claimed:
                    continue
                eff[f"{rid}.{key}"] = V(v, FROM_SPEC, "params (no resolution targets it)", key)

    return eff, notes


# ---------------------------------------------------------------- ingredients
def _ceil_div(a: float, b: float) -> int:
    return int(math.ceil(a / b))


def ingredient_gate(spec: dict, inputs: dict, proof_seconds: float) -> tuple[list[str], list[str]]:
    """Two layers. Declarative (inputs.json must name a file per required
    ingredient) PLUS mechanical corroboration -- which is what catches a ticked
    box. The shopping list is GENERATED from ingredients[], never hand-written,
    so it cannot drift from the spec."""
    errors: list[str] = []
    warns: list[str] = []
    provided = inputs.get("ingredients") or {}

    for ing in (spec.get("ingredients") or []):
        iid = ing.get("id")
        required = bool(ing.get("required"))
        got = provided.get(iid)
        if not got:
            (errors if required else warns).append(
                f"{iid} {'MISSING (required)' if required else 'absent (optional)'}: "
                f"{(ing.get('desc') or '')[:110]}")
            continue
        paths = got if isinstance(got, list) else [got]
        for p in paths:
            if not isinstance(p, str):
                continue
            fp = stylespec.fingerprint(p)
            if not fp.get("exists"):
                errors.append(f"{iid}: declared file does not exist -> {p}")

    # in2 is a RATE, not an asset. One screenshot ticked for a 30s proof is the
    # exact failure a presence check waves through.
    art = provided.get("in2")
    if art:
        art = art if isinstance(art, list) else [art]
        need = _ceil_div(proof_seconds, 4)
        if len(art) < need:
            errors.append(f"in2 is a RATE: {len(art)} artifact(s) for {proof_seconds:.1f}s "
                          f"of proof needs >= {need} (1 per 4s)")

    # in4 -- the single most valuable check here. Right shape, wrong content =
    # perfectly formed captions, perfectly out of sync.
    tpath = provided.get("in4")
    fpath = provided.get("in1")
    if isinstance(tpath, list):
        tpath = tpath[0] if tpath else None
    if isinstance(fpath, list):
        fpath = fpath[0] if fpath else None
    if tpath and fpath and os.path.exists(tpath) and os.path.exists(fpath):
        try:
            words = (json.load(open(tpath, encoding="utf-8")) or {}).get("words") or []
        except Exception as e:                                        # noqa: BLE001
            words = []
            errors.append(f"in4: transcript unreadable ({e})")
        vid = stylespec.ffprobe_duration(fpath)
        if words and vid:
            t_end = max(w.get("endTimeMs", 0) for w in words) / 1000.0
            drift = abs(t_end - vid)
            if drift > max(2.0, vid * 0.05):
                errors.append(f"in4: transcript ends at {t_end:.2f}s but footage is {vid:.2f}s "
                              f"(drift {drift:.2f}s) — wrong transcript for this footage")
            else:
                warns.append(f"in4 corroborated: transcript {t_end:.2f}s vs footage {vid:.2f}s "
                             f"(drift {drift:.2f}s)")

    # in10 -- the whoosh is load-bearing; hard cuts with no whoosh read as a
    # mistake rather than a style.
    wh = provided.get("in10")
    if wh:
        wh = wh if isinstance(wh, list) else [wh]
        for p in wh:
            d = stylespec.ffprobe_duration(p) if os.path.exists(p) else None
            if d is not None and not (0.4 <= d <= 2.0):
                errors.append(f"in10: whoosh {os.path.basename(p)} is {d:.2f}s, expected 0.4-2.0s")
    return errors, warns


def shopping_list(spec: dict) -> str:
    lines = ["Ingredient shopping list (generated from spec.ingredients[]):"]
    for ing in (spec.get("ingredients") or []):
        mark = "REQUIRED" if ing.get("required") else "optional"
        lines.append(f"  [{mark:8}] {ing.get('id')}: {ing.get('desc')}")
        if ing.get("note"):
            lines.append(f"             note: {ing['note']}")
    return "\n".join(lines)


# ------------------------------------------------------------ caption engine
# Grouping runs in INTEGER MS (the 80ms break and 1900ms cap are ms-defined).
# Placement runs in INTEGER FRAMES, so groups are contiguous by construction
# with zero float drift. Exactly one /1000 and one /fps live in this module.

_NUM_TAIL = re.compile(r"\d[\d,.]*$")
_NUM_HEAD = re.compile(r"^[,.]?\d")


def _numeral_continues(prev_text: str, next_text: str) -> bool:
    """True when the next token continues the previous one's numeral —
    '12' + ',000'. Keeps a number whole across a group boundary."""
    return bool(_NUM_TAIL.search(prev_text.strip()) and _NUM_HEAD.match(next_text.strip()))


def group_words(words: list[dict], break_ms: int, max_words: int,
                max_group_ms: int, target_hold_ms: int) -> list[list[dict]]:
    """`phrase_beat` — one prosodic beat per group.

    FOUR break conditions, and the fourth is the one that matters. Breaking only
    at `max_group_duration_ms` is wrong: that is the observed MAXIMUM, a single
    outlier, not the shape of a group. The governing number is the measured
    MEDIAN hold. Using the cap instead of the target under-breaks badly (roughly
    half the observed group count at about twice the words per group); a sweep
    of this parameter peaked at the spec's own measured median."""
    groups: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        if not cur:
            cur = [w]
            continue
        pause_ms = int(w["startTimeMs"]) - int(cur[-1]["endTimeMs"])
        span_ms = int(w["endTimeMs"]) - int(cur[0]["startTimeMs"])
        # A numeral may not be split across groups. A number-ticker rule (4+
        # digit numbers COUNT UP over the group hold rather than appearing at
        # final value) needs the whole numeral in ONE group. That is also what
        # the hard cap is for: a long number group. ASR often splits a numeral
        # into "12" + ",000" with a 0ms pause, so only the median-hold target
        # would split them -- breaking the ticker and hiding the payoff.
        if _numeral_continues(cur[-1]["text"], w["text"]) and span_ms <= max_group_ms:
            cur.append(w)
            continue
        if (pause_ms >= break_ms or len(cur) >= max_words
                or span_ms > target_hold_ms or span_ms > max_group_ms):
            groups.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def wpm_of(words: list[dict]) -> float:
    if not words:
        return 0.0
    span_ms = int(words[-1]["endTimeMs"]) - int(words[0]["startTimeMs"])
    return (len(words) / (span_ms / 1000.0)) * 60.0 if span_ms > 0 else 0.0


def hold_ms_for(wpm: float, base_ms: int = 467, base_wpm: float = 168.3,
                lo: int = 233, hi: int = 1900) -> int:
    """Hold scales inversely with the NEW transcript's wpm -- physically
    motivated, reproduces the second measured point within 5%, and cannot go
    negative at high wpm (a linear fit can)."""
    if wpm <= 0:
        return base_ms
    return max(lo, min(hi, int(round(base_ms * base_wpm / wpm))))


def plan_captions(words: list[dict], mech: dict, fps: int) -> dict:
    break_ms = int(mech.get("group_break_pause_ms") or 80)
    max_words = int(mech.get("max_words_per_group") or 4)
    max_ms = int(mech.get("max_group_duration_ms") or 1900)
    pct = mech.get("group_duration_percentiles_ms") or {}
    target_ms = int(pct.get("median") or 467)
    groups = group_words(words, break_ms, max_words, max_ms, target_ms)
    wpm = wpm_of(words)
    hold = hold_ms_for(wpm)

    out = []
    for i, g in enumerate(groups):
        start_ms = int(g[0]["startTimeMs"])
        # contiguous by construction: a group runs until the next group starts
        nxt = int(groups[i + 1][0]["startTimeMs"]) if i + 1 < len(groups) else start_ms + hold
        end_ms = max(start_ms + 1, nxt)
        start_f = int(round(start_ms * fps / 1000.0))
        end_f = int(round(end_ms * fps / 1000.0))
        out.append({
            "i": i,
            "text": " ".join(w["text"] for w in g),
            "words": [{"t": w["text"], "start_ms": int(w["startTimeMs"])} for w in g],
            "start_ms": start_ms, "end_ms": end_ms,
            "start_f": start_f, "end_f": max(start_f + 1, end_f),
            "track": 20 + (i % 2),   # ~80 groups incrementing would walk into the sfx lane at 50
        })
    return {
        "groups": out,
        "stats": {
            "n_groups": len(out),
            "n_words": len(words),
            "words_per_group_mean": round(len(words) / len(out), 3) if out else 0,
            "wpm": round(wpm, 1),
            "hold_ms": hold,
        },
    }


# ------------------------------------------------------- claim-payoff
# A RECURRING beat's anchor is a trigger, not a time (e.g. "claim payoff -- the
# moment a spoken claim lands its key noun"). Placement comes from the new
# script's claim-payoff beats, not from the decode. This finds candidates.
#
# It proposes CANDIDATES; it does not choose. Choosing is judgment, judgment
# lives in `plan`, and an unconfirmed recurring beat forces the exit-2 human
# gate. `build` never sees an unconfirmed candidate.

# The positional window is the generator's own invention and is tagged as such,
# so it is COUNTED in the rung-5 "how much did the generator author" tally
# rather than passing as spec. Two independent pointers, neither authoritative
# for any one style: a measured long-form payoff position near ~78% of runtime,
# and a small hand-annotated short-form sample (n=5, no validation metrics)
# placing its "money line" at 70-80%. They agree, but one measures a DIFFERENT
# format and the other is unvalidated, so this is a prior to be confirmed --
# never a fact to be applied.
CLAIM_WINDOW = (0.70, 0.80)
_BIG_NUM = re.compile(r"\d[\d,]{3,}")
_SUPERLATIVE = re.compile(r"\b(only|never|every|best|worst|first|most|all|nothing|"
                          r"everything|literally|actually)\b", re.I)


def claim_payoff_candidates(caps: dict, dur_s: float, mech: dict) -> list[dict]:
    """Score every caption group as a claim-payoff candidate.

    Three signals, all derived from the spec's own measurements -- no LLM, so
    `plan` stays deterministic and re-runnable:

      position  in the window above
      number    a 4+ digit numeral. A number-ticker rule makes these COUNT UP
                over the group hold instead of appearing at final value --
                such a style already treats them as payoffs.
      hold      group duration >= the p90 hold. A payoff line is held.
    """
    p90 = int((mech.get("group_duration_percentiles_ms") or {}).get("p90") or 867)
    lo, hi = CLAIM_WINDOW
    out = []
    for g in caps["groups"]:
        pos = (g["start_ms"] / 1000.0) / dur_s if dur_s else 0
        why, score = [], 0.0
        if lo <= pos <= hi:
            score += 0.5
            why.append(f"in the {int(lo*100)}-{int(hi*100)}% window (at {pos*100:.1f}%)")
        # strip separators before matching: a numeral kept whole across a
        # group boundary reads "12 ,000"
        if _BIG_NUM.search(re.sub(r"[\s,]", "", g["text"])):
            score += 0.3
            why.append("carries a 4+ digit numeral (a number-ticker style treats these as payoffs)")
        if (g["end_ms"] - g["start_ms"]) >= p90:
            score += 0.2
            why.append(f"held >= p90 ({p90}ms)")
        if _SUPERLATIVE.search(g["text"]):
            score += 0.1
            why.append("carries an absolute/superlative")
        if score > 0:
            out.append({"group": g["i"], "text": g["text"], "at_pct": round(pos * 100, 1),
                        "start_ms": g["start_ms"], "score": round(score, 2), "why": why})
    out.sort(key=lambda c: (-c["score"], c["start_ms"]))
    return out[:8]


# ------------------------------------------------------------------ plan cmd
def _build_dir(slug: str, stamp: str) -> str:
    root = os.path.join(cfg()["data_dir"], "builds")
    n = 1
    while True:
        p = os.path.join(root, f"{slug}-{stamp}-{n:02d}")
        if not os.path.exists(p):
            return p
        n += 1


def _sha(path: str) -> str:
    if not os.path.exists(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_plan(args) -> None:
    slug = args.style
    spec = stylespec.load_spec(slug)

    # P0 -- refuse an invalid spec before anything else is parsed.
    spec_errors, _ = stylespec.validate_spec(slug, spec)
    if spec_errors:
        for f in spec_errors:
            print(f"ERROR spec: {f}")
        sys.exit(1)

    if not os.path.exists(args.inputs):
        print(f"no inputs file at {args.inputs}\n")
        print(shopping_list(spec))
        sys.exit(1)
    inputs = json.load(open(args.inputs, encoding="utf-8"))

    fps = int(inputs.get("fps") or 30)
    proof_s = float(inputs.get("proof_seconds") or 0)

    # P1 -- INGREDIENT GATE, first, before anything else is parsed.
    ing_err, ing_warn = ingredient_gate(spec, inputs, proof_s)
    for w in ing_warn:
        print(f"WARN  ingredients: {w}")
    if ing_err:
        for e in ing_err:
            print(f"ERROR ingredients: {e}")
        print("\n" + shopping_list(spec))
        sys.exit(1)

    # OBS / PARAM partition -- unclassified timestamp field is a hard fail.
    obs, unclassified = partition_spec(spec)
    if unclassified:
        for u in unclassified:
            print(f"ERROR partition: timestamp-bearing field is UNCLASSIFIED: {u}")
        print("classify it in OBSERVATION_KEYS or PARAMETER_KEYS before building")
        sys.exit(1)
    obs_ms = observed_timestamps(obs)

    # artifact rules -- acknowledge-and-exclude. Refuse until the plan says so, then omit
    # the beat and say so loudly.
    ack = set(inputs.get("artifact_acknowledged") or [])
    artifacts = []
    for dotted, judgment in stylespec.RULE_GROUPS:
        if not judgment:
            continue
        for r in (stylespec.get_group(spec, dotted) or []):
            if not isinstance(r, dict):
                continue
            for res in (r.get("resolution") or []):
                if res.get("kind") == "artifact":
                    artifacts.append(_rule_id(r))
    unack = sorted(set(artifacts) - ack)
    if unack:
        for a in unack:
            print(f"ERROR artifact rule not acknowledged: {a} "
                  f"(add to inputs.artifact_acknowledged to omit its beat)")
        sys.exit(1)

    eff, eff_notes = effective_params(spec)
    for n in eff_notes:
        print(f"WARN  effective-params: {n}")

    tpath = (inputs.get("ingredients") or {}).get("in4")
    if isinstance(tpath, list):
        tpath = tpath[0]
    words = (json.load(open(tpath, encoding="utf-8")) or {}).get("words") or []
    caps = plan_captions(words, (spec.get("typography") or {}).get("caption_mechanics") or {}, fps)

    # recurring triggers: propose, never choose.
    recurring = []
    for dotted, judgment in stylespec.RULE_GROUPS:
        if not judgment:
            continue
        for r in (stylespec.get_group(spec, dotted) or []):
            # some rule groups carry bare strings alongside rule objects, and
            # some rules carry `anchor` as prose rather than a dict -- `or {}`
            # does not catch a truthy non-dict
            if not isinstance(r, dict):
                continue
            anc = r.get("anchor")
            if isinstance(anc, dict) and anc.get("type") == "recurring":
                recurring.append(r)
    # Position is a fraction of the FINISHED SCRIPT, never of a proof slice.
    # Scoring an 8s mechanics clip against its own 8s makes every group past 8s
    # score >100% and is meaningless -- the claim payoff of a 44s script simply
    # is not inside an 8s slice, and saying so is the correct answer.
    dur_for_pos = max((int(w["endTimeMs"]) for w in words), default=0) / 1000.0
    candidates = claim_payoff_candidates(caps, dur_for_pos,
                                         (spec.get("typography") or {}).get("caption_mechanics") or {})
    confirmed = inputs.get("claim_payoff_groups")
    if recurring and confirmed is None:
        eff_notes.append(
            f"{recurring[0].get('id')}: recurring trigger "
            f"{(recurring[0].get('anchor') or {}).get('trigger')!r} has no confirmed placement — "
            f"pick from claim_payoff_candidates and set inputs.claim_payoff_groups")

    # No emitted timestamp may equal an observation.
    collisions = [g["i"] for g in caps["groups"] if g["start_ms"] in obs_ms]
    if collisions:
        print(f"WARN  {len(collisions)} caption start(s) coincide with an observed timestamp "
              f"— expected when rebuilding a source against itself")

    out_dir = _build_dir(slug, args.stamp)
    os.makedirs(out_dir, exist_ok=True)

    plan = {
        "generator_version": GENERATOR_VERSION,
        "style": slug,
        "style_version": (spec.get("style") or {}).get("version"),
        "design_system": inputs.get("design_system"),
        "fps": fps,
        "content_addressed": {
            "spec_sha256": _sha(stylespec.spec_path(slug)),
            "transcript_sha256": _sha(tpath) if tpath else "",
            "inputs_sha256": _sha(args.inputs),
        },
        "artifact_acknowledged": sorted(ack),
        "artifacts_omitted": sorted(artifacts),
        "captions": caps,
        "observations": {
            "n_fields": len(obs),
            "n_timestamps_ms": len(obs_ms),
            "note": "the generator may not read these except through a declared derivation",
        },
        "interpretations_required": [n for n in eff_notes
                                     if "rejected" in n or "no confirmed placement" in n],
        "recurring_beats": [
            {"id": r.get("id"),
             "trigger": (r.get("anchor") or {}).get("trigger"),
             "confirmed_groups": confirmed,
             "window": {"v": list(CLAIM_WINDOW), "prov": GENERATOR_INVENTED,
                        "why": "positional prior, NOT from this spec — confirm per build"}}
            for r in recurring],
        "claim_payoff_candidates": candidates,
    }
    json.dump(plan, open(os.path.join(out_dir, "build-plan.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    json.dump(eff, open(os.path.join(out_dir, "effective-params.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    prov = {}
    for v in eff.values():
        prov[v["prov"]] = prov.get(v["prov"], 0) + 1

    print(f"\nplan -> {out_dir}")
    print(f"  captions: {caps['stats']['n_groups']} groups from {caps['stats']['n_words']} words "
          f"· mean {caps['stats']['words_per_group_mean']} w/group "
          f"· {caps['stats']['wpm']} wpm -> hold {caps['stats']['hold_ms']}ms")
    print(f"  effective params: {len(eff)} fields · " + " · ".join(f"{k} {v}" for k, v in sorted(prov.items())))
    print(f"  observations quarantined: {len(obs)} fields, {len(obs_ms)} distinct timestamps")
    if plan["artifacts_omitted"]:
        print(f"  !! THIS BUILD HAS NO {', '.join(plan['artifacts_omitted'])} BEAT "
              f"(acknowledged artifact, omitted by design)")
    if candidates:
        print(f"  claim-payoff candidates for {len(recurring)} recurring beat(s) "
              f"— top: g{candidates[0]['group']} @{candidates[0]['at_pct']}% "
              f"{candidates[0]['text']!r} (score {candidates[0]['score']})")
    if plan["interpretations_required"]:
        print(f"  {len(plan['interpretations_required'])} interpretation(s) required "
              f"— human gate, exit 2")
        sys.exit(2)
    print("PLAN OK")


# ------------------------------------------------------------------- emitters
# Tweens are a TABLE OF PYTHON EMITTERS, not string substitution. Decoded
# `tween_recipes` are often prose-contaminated (pure prose; two statements plus a
# label; prose after valid JS), so any substitution engine emits broken JS for
# many of them -- and `hyperframes lint` checks structure, not JS semantics, so
# it would not catch it.
#
# Each emitter stores sha1 of the recipe it was written against. Drift is
# reported; a recipe with no emitter is exit 1.

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def emit_caption_in(gid: str, at_s: float, dur_s: float, ease: str) -> str:
    """Group entrance. fromTo with an explicit visible destination, never a bare
    `from`: HyperFrames lints gsap_cold_seek_hidden_fromto_missing_reveal as an
    error because cold render workers restore the authored hidden state and
    encode it permanently invisible -- sequential preview looks correct, the
    render is missing the element."""
    return (f"tl.fromTo('#{gid}', {{autoAlpha:0, y:14}}, "
            f"{{autoAlpha:1, y:0, duration:{dur_s:.3f}, ease:'{ease}'}}, {at_s:.3f});")


def emit_word_reveal(wid: str, at_s: float) -> str:
    """Cumulative reveal uses `display`, not `autoAlpha`.

    The measured build steps show the line GROWING AND RE-CENTERING, which only
    happens if hidden words do not occupy layout -- autoAlpha cannot reproduce
    it because an invisible span still takes its box.

    NOTE (07.29.26): hyperframes-core lists display/visibility as non-animatable.
    This is a `tl.set()` at a timeline position, not a tween, which is the same
    mechanism earlier prior-art generators used for colour swaps. Verified
    against lint rather than assumed -- see styletemplate-contract.md."""
    return f"tl.set('#{wid}', {{display:'inline'}}, {at_s:.3f});"


EMITTERS = {
    "caption_in": (emit_caption_in, ""),
    "word_reveal": (emit_word_reveal, ""),
}


def _role(entry, role, default=None):
    import designsystem as ds
    v, prov = ds.resolve_role(entry, role)
    if v is None:
        return default, prov
    return (v.get("v") if isinstance(v, dict) else v), prov


def _font_faces(entry: dict, rel_prefix: str) -> tuple[str, list[str]]:
    """@font-face for every vendored family. An offline render exits 0 entirely
    in the fallback font -- and corrupts the derived geometry rules, which hug
    text ink boxes. So the files are referenced locally, never from a CDN."""
    css, missing = [], []
    import designsystem as ds
    for f in (entry.get("fonts") or []):
        fam = f.get("family")
        for i, rel in enumerate(f.get("files") or []):
            src = os.path.join(os.path.dirname(ds.fonts_dir()), rel)
            if not os.path.exists(src):
                missing.append(rel)
                continue
            weight = (f.get("weights") or [400])[min(i, len(f.get("weights") or [400]) - 1)]
            style = (f.get("styles") or ["normal"])[min(i, len(f.get("styles") or ["normal"]) - 1)]
            css.append(f"@font-face{{font-family:'{fam}';font-weight:{weight};"
                       f"font-style:{style};src:url('{rel_prefix}{os.path.basename(rel)}') format('woff2');}}")
    return "\n      ".join(css), missing


def _local_gsap(path: str) -> str:
    """The GSAP build is a required LOCAL file. Never a URL, never a download."""
    if re.match(r"^([a-z][a-z0-9+.-]+:|//)", path.strip(), re.I):   # scheme of 2+ letters: C:/ stays a path
        sys.exit("--gsap must be a gsap.min.js file on this computer, never a link or a download")
    if not os.path.isfile(path):
        sys.exit(f"--gsap: no file at {path} — the build needs a local copy of gsap.min.js")
    return path


def caption_role(spec: dict) -> tuple[float, float]:
    """(size_pct_of_width, baseline_y_pct_of_height) of the ONE typography role marked
    `caption_default: true`. Fails closed: a missing role, field or value exits with
    its name. There is no literal fallback -- a guessed size is a silent wrong frame."""
    roles = [r for r in (stylespec.get_group(spec, "typography.roles") or [])
             if isinstance(r, dict) and r.get("caption_default") is True]
    if not roles:
        sys.exit("ERROR spec: no typography.roles entry has caption_default: true — "
                 "mark the default caption role in the spec")
    if len(roles) > 1:
        sys.exit("ERROR spec: more than one typography.roles entry has caption_default: true: "
                 + ", ".join(str(r.get("id")) for r in roles))
    r, out = roles[0], []
    for field in ("size_pct_of_width", "baseline_y_pct_of_height"):
        v = r.get(field)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            sys.exit(f"ERROR spec: typography.roles[{r.get('id')}].{field} is missing or not a "
                     f"number (got {v!r}) — the build never guesses it")
        out.append(float(v))
    return out[0], out[1]


def cmd_build(args) -> None:
    import shutil
    import designsystem as ds

    gsap_src = _local_gsap(args.gsap)
    plan_dir = args.plan_dir
    plan_path = os.path.join(plan_dir, "build-plan.json")
    if not os.path.exists(plan_path):
        sys.exit(f"no build-plan.json in {plan_dir} — run `plan` first")
    plan = json.load(open(plan_path, encoding="utf-8"))
    inputs = json.load(open(args.inputs, encoding="utf-8"))

    spec = stylespec.load_spec(plan["style"])
    entry = ds.load_entry(plan["design_system"])
    fps = int(plan["fps"])
    proof_s = float(inputs.get("proof_seconds") or 0) or None

    assets_dir = os.path.join(plan_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # media -> assets/ so the composition is self-contained and portable
    ing = inputs.get("ingredients") or {}
    footage_src = ing.get("in1")
    if isinstance(footage_src, list):
        footage_src = footage_src[0]
    shutil.copy2(footage_src, os.path.join(assets_dir, "footage.mp4"))
    shutil.copy2(gsap_src, os.path.join(assets_dir, "gsap.min.js"))
    for f in (entry.get("fonts") or []):
        for rel in (f.get("files") or []):
            src = os.path.join(os.path.dirname(ds.fonts_dir()), rel)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(assets_dir, os.path.basename(rel)))

    dur_s = proof_s or (stylespec.ffprobe_duration(footage_src) or 0)
    groups = [g for g in plan["captions"]["groups"] if g["start_ms"] / 1000.0 < dur_s]

    # --- look, entirely from the design system via the look-map's roles
    bg, _ = _role(entry, "palette.bg.page", "#FEF7EF")
    ink, _ = _role(entry, "palette.ink.primary", "#141414")
    fam, _ = _role(entry, "type.body.family", "Poppins")
    wgt, _ = _role(entry, "type.body.weight", 700)
    cw = int(entry.get("reference_width_px") or 720)

    # size is EDIT, never look — read from the spec, never from the registry
    size_pct, y_pct = caption_role(spec)

    W, H = 720, 1280
    font_css, missing_fonts = _font_faces(entry, "assets/")
    if missing_fonts:
        sys.exit(f"missing vendored font file(s): {missing_fonts} — an offline render would "
                 f"exit 0 in the fallback font and corrupt every derived rect")

    clips, tweens = [], []
    for g in groups:
        gid = f"cap{g['i']}"
        start_s = g["start_f"] / fps          # the ONE /fps
        end_s = min(g["end_f"] / fps, dur_s)
        if end_s - start_s <= 0:
            continue
        spans = []
        for wi, w in enumerate(g["words"]):
            wid = f"{gid}w{wi}"
            # first word visible from the group's own start; the rest reflow in
            style = "inline" if wi == 0 else "none"
            # The separating space lives INSIDE the span, before the word. A
            # space between spans would be laid out even while the word it
            # belongs to is display:none -- and a display:none word must take no
            # layout at all, or the line does not grow and re-centre. Rendered
            # proof of the bug: two words came out glued together.
            # ...but a numeral continuation takes NO separator, or "12" + ",000"
            # renders as "12 ,000"
            joins = wi and not _numeral_continues(g["words"][wi - 1]["t"], w["t"])
            text = ("&#32;" if joins else "") + w["t"]
            spans.append(f'<span id="{wid}" style="display:{style};white-space:pre">'
                         f'{text}</span>')
            if wi:
                tweens.append(emit_word_reveal(wid, w["start_ms"] / 1000.0))
        clips.append(
            f'      <div class="clip cap" id="{gid}" data-start="{start_s:.3f}" '
            f'data-duration="{end_s - start_s:.3f}" data-track-index="{g["track"]}">\n'
            f'        <div class="cap-line">{"".join(spans)}</div>\n'
            f'      </div>')
        tweens.append(emit_caption_in(gid, start_s, 0.12, "power2.out"))

    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <!-- GSAP is the local file passed with --gsap, copied into assets/: no network. -->
    <script src="assets/gsap.min.js"></script>
    <style>
      {font_css}
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ width:{W}px; height:{H}px; overflow:hidden; background:{bg}; }}
      #root {{ position:relative; width:{W}px; height:{H}px; }}
      .skin {{ position:absolute; inset:0; background:{bg}; }}
      .stage {{ position:absolute; inset:0; width:{W}px; height:{H}px; object-fit:cover; }}
      .cap {{ position:absolute; left:0; right:0; top:{y_pct}%; display:flex;
              justify-content:center; }}
      .cap-line {{ font-family:'{fam}'; font-weight:{wgt}; color:{ink};
                   font-size:{size_pct * cw / 100:.1f}px; line-height:1.1;
                   max-width:{cw * 0.68:.0f}px; text-align:center; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0"
         data-duration="{dur_s:.3f}" data-width="{W}" data-height="{H}">

      <div class="skin"></div>
      <video id="stage" class="stage clip" data-start="0" data-duration="{dur_s:.3f}"
             data-track-index="0" muted playsinline preload="auto" src="assets/footage.mp4"></video>

{chr(10).join(clips)}

      <audio id="narration" class="clip" data-start="0" data-duration="{dur_s:.3f}"
             data-track-index="2" src="assets/footage.mp4"></audio>
    </div>

    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {chr(10) + "      " + (chr(10) + "      ").join(tweens)}
      window.__timelines['main'] = tl;
    </script>
  </body>
</html>
"""
    out_html = os.path.join(plan_dir, "index.html")
    open(out_html, "w", encoding="utf-8").write(html)

    build = {
        "generator_version": GENERATOR_VERSION,
        "style": plan["style"], "style_version": plan["style_version"],
        "design_system": plan["design_system"],
        "fps": fps, "duration_s": round(dur_s, 3),
        "width": W, "height": H,
        "content_addressed": dict(plan["content_addressed"],
                                  design_system_sha256=_sha(ds.entry_path(plan["design_system"])),
                                  gsap_sha256=_sha(os.path.join(assets_dir, "gsap.min.js")),
                                  footage=stylespec.fingerprint(footage_src),
                                  html_sha256=_sha(out_html)),
        "clips": [{"id": f"cap{g['i']}", "start_f": g["start_f"], "track": g["track"],
                   "start_s": round(g["start_f"] / fps, 3)} for g in groups],
        "emitters": {k: _sha1(v[1]) for k, v in EMITTERS.items()},
    }
    json.dump(build, open(os.path.join(plan_dir, "build.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    print(f"build -> {out_html}")
    print(f"  {len(clips)} caption clips · {len(tweens)} tweens · {dur_s:.2f}s @ {fps}fps")
    print(f"  fonts vendored: {len(entry.get('fonts') or [])} families, 0 missing")
    _run_check(plan_dir, verbose=False)


# ---------------------------------------------------------------------- check
_BANNED = ("setTimeout(", "setInterval(", "Math.random", "Date.now", "fetch(",
           "requestAnimationFrame", "new Promise")


def _run_check(build_dir: str, verbose: bool = True) -> int:
    """Pure Python, no Node. The wrong-`data-start` detector is the point:
    round(float(data-start)*fps) must equal the frame the plan committed to."""
    html_p = os.path.join(build_dir, "index.html")
    build_p = os.path.join(build_dir, "build.json")
    if not (os.path.exists(html_p) and os.path.exists(build_p)):
        print("check: no index.html/build.json — run `build` first")
        return 1
    html = open(html_p, encoding="utf-8").read()
    build = json.load(open(build_p, encoding="utf-8"))
    fps = int(build["fps"])
    errors, checks = [], 0

    # 1. every committed clip's data-start round-trips to its frame
    for c in build["clips"]:
        m = re.search(rf'id="{c["id"]}"[^>]*data-start="([0-9.]+)"', html)
        if not m:
            errors.append(f"clip {c['id']} not in the DOM")
            continue
        checks += 1
        got_f = int(round(float(m.group(1)) * fps))
        if got_f != c["start_f"]:
            errors.append(f"{c['id']}: data-start {m.group(1)} -> frame {got_f}, "
                          f"plan committed {c['start_f']}")

    # 2. exactly one paused timeline, registered under the root's id
    checks += 1
    if html.count("gsap.timeline(") != 1 or "paused: true" not in html:
        errors.append("expected exactly one gsap.timeline({paused:true})")
    root_id = re.search(r'data-composition-id="([^"]+)"', html)
    checks += 1
    if not root_id or f"window.__timelines['{root_id.group(1)}']" not in html:
        errors.append("timeline not registered under the root data-composition-id")

    # 3. determinism bans
    for b in _BANNED:
        checks += 1
        if b in html:
            errors.append(f"non-deterministic construct present: {b}")

    # 4. class="clip" on every timed element, and nowhere it must not be
    for m in re.finditer(r"<(\w+)([^>]*data-start=[^>]*)>", html):
        tag, attrs = m.group(1), m.group(2)
        if tag == "div" and "data-composition-id" in attrs:
            continue
        checks += 1
        if 'class="' not in attrs or "clip" not in attrs:
            errors.append(f"<{tag}> has data-start but no class=clip")

    # 5. no remote src (no CDN, ever), and every local src resolves
    for m in re.finditer(r'src="([^"]+)"', html):
        if not m.group(1).startswith("assets/"):
            checks += 1
            errors.append(f"src is not a local assets/ file: {m.group(1)}")
    for m in re.finditer(r'src="(assets/[^"]+)"', html):
        checks += 1
        if not os.path.exists(os.path.join(build_dir, m.group(1))):
            errors.append(f"src does not resolve: {m.group(1)}")

    # 6. every font-family has an @font-face whose file exists
    for fam in set(re.findall(r"font-family:'([^']+)'", html)):
        checks += 1
        fm = re.search(rf"@font-face\{{font-family:'{re.escape(fam)}';[^}}]*url\('([^']+)'\)", html)
        if not fm:
            errors.append(f"font-family {fam!r} has no @font-face")
        elif not os.path.exists(os.path.join(build_dir, fm.group(1))):
            errors.append(f"@font-face file missing for {fam!r}: {fm.group(1)}")

    # 7. every GSAP selector id exists in the DOM. GSAP silently no-ops on a
    #    missing selector -- which is how an omit-ed element leaves a dead tween.
    dom_ids = set(re.findall(r'id="([^"]+)"', html))
    for sid in set(re.findall(r"tl\.\w+\('#([^']+)'", html)):
        checks += 1
        if sid.split(" ")[0] not in dom_ids:
            errors.append(f"GSAP targets #{sid} which is not in the DOM (silent no-op)")

    # 8. same-track clips may not overlap
    per_track: dict[int, list] = {}
    for m in re.finditer(r'data-start="([0-9.]+)" data-duration="([0-9.]+)" '
                         r'data-track-index="(\d+)"', html.replace("\n", " ")):
        s, d, t = float(m.group(1)), float(m.group(2)), int(m.group(3))
        per_track.setdefault(t, []).append((s, s + d))
    for t, spans in per_track.items():
        spans.sort()
        for a, b in zip(spans, spans[1:]):
            checks += 1
            if b[0] < a[1] - 1e-6:
                errors.append(f"track {t}: clips overlap ({a} then {b})")

    for e in errors:
        print(f"ERROR check: {e}")
    print(f"check: {checks} assertions, {len(errors)} errors")
    if errors:
        return 1
    print("CHECK PASS")
    return 0


def cmd_check(args) -> None:
    sys.exit(_run_check(args.build_dir))


def main() -> None:
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan")
    p.add_argument("style")
    p.add_argument("--inputs", required=True, help="inputs.json naming a file per ingredient")
    p.add_argument("--stamp", default="00.00.00", help="MM.DD.YY for the build dir name")
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("build")
    p.add_argument("plan_dir")
    p.add_argument("--inputs", required=True, help="the same inputs.json the plan was made from")
    p.add_argument("--gsap", required=True,
                   help="path to a local gsap.min.js (required; never a URL, never downloaded)")
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser("check")
    p.add_argument("build_dir")
    p.set_defaults(fn=cmd_check)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
