#!/usr/bin/env python3
"""style-decoder — style-spec assembler/validator/merger/indexer.

The style library holds decoded "editing design systems": per style, one canonical
style-spec.json (undated — it IS the live state, manifest doctrine) plus dated
runbook MDs, per-source measurement data, and evidence contact sheets.

Subcommands:
    init <slug> [--name "Display Name"]     scaffold style dir + skeleton spec
    add-source <slug> <file>                 register a LOCAL video as the next src-NN
    validate <slug>                          schema + evidence check; exit 1 = gate FAIL
    coverage <slug>                          mechanical completeness audit; exit 1 = gaps
    merge <slug> --source <src-id> --candidate <file>
                                             fold a new source's candidate rules in
    contact-sheet <slug> [--group <name>]    tile evidence frames per rule group (Pillow)
    heldout <slug> [--n 10] [--frames a,b]   pick uncited base frames for the held-out screen
    index                                    rebuild <library>/index.json from style dirs
    fingerprint <path>                       {exists,size,duration} via ffprobe

Doctrine (full text: stylespec-contract.md):
  - Every judgment rule carries evidence[] (paths relative to the style dir),
    confidence (provisional=1 source, confirmed=2+), observed_in[].
  - UNKNOWN is a legal param value — the spec never guesses.
  - validate is fail-closed: a rule without existing evidence is an ERROR;
    status "approved" with any ERROR refuses to validate/index.
  - merge: match -> confirm + average numerics (per-source kept); new -> provisional;
    incompatible -> both kept as variants[], flagged for the user gate.
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "_shared"))
sys.path.insert(0, _HERE)
from enginecfg import cfg  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402

SPEC_VERSION = "1.0"
SPEC_NAME = "style-spec.json"

# Rule-bearing lists: (path into spec, is_judgment). Judgment entries need
# evidence/confidence/observed_in; computed groups (pacing, audio.loudness) do not.
RULE_GROUPS = [
    ("canvas.layout_modes", True),
    ("canvas.layout_grammar", True),
    ("canvas.overlay_treatments", True),
    ("transitions", True),
    ("typography.roles", True),
    ("color.skins", True),
    ("motion.rules", True),
    ("motion.audio_synced_rules", True),
    ("structure.beats", True),
    ("structure.patterns", True),
    ("structure.screens", True),
    ("assets.recurring_motifs", True),
    ("assets.panel_content_types", True),
    ("assets.panel_treatments", True),
]

SPEC_TEMPLATE = {
    "spec_version": SPEC_VERSION,
    "style": {
        "slug": "", "name": "", "version": "0.1.0", "status": "draft",
        "created": "", "updated": "",
    },
    "sources": [],       # {id,platform:"local",file,added,duration_s,resolution,fps,fingerprint} (add-source)
    "canvas": {
        "aspect": "9:16",
        "safe_zones_px": {},          # measured off full-res frames
        "layout_modes": [],           # {id,label,zones:[{id,rect_pct,content}],evidence,confidence,observed_in}
        "layout_grammar": [],         # {rule,evidence,confidence,observed_in}
        # INLINE the shot list — a ref alone forces consumers to reverse-engineer
        # mode order (blind-test finding, 07.24.26). [{t_start,t_end,mode_id,
        # skin_id,card_content_type_id}] covering the full runtime, no gaps.
        "layout_timeline": [],
        "layout_grammar_mode_sequence": "",   # compact "A,C,A,B,..." fallback
        "layout_timeline_ref": "",    # sources/<src>/layout_timeline.json
        "overlay_treatments": [],     # {id,rule,evidence,confidence,observed_in}
    },
    "transitions": [],   # {id,from_mode,to_mode,type,duration_s,evidence,confidence,observed_in}
    "typography": {
        # each role also needs: mode_scope[] (which modes it may appear in) and
        # size_metric ("cap_height_pct_of_width"|"em_pct_of_width") — "8% of
        # width" is unbuildable without knowing which metric (blind-test finding)
        "roles": [],                  # {id,applies_to,font_guess,closest_available,weight,case,
                                      #  color_token,stroke,shadow,letter_spacing,size_pct_of_width,
                                      #  size_metric,mode_scope,evidence,confidence,observed_in}
        # a words-per-group DISTRIBUTION is not a rule — a clone needs the
        # algorithm + thresholds. observed_groups[] validates/reproduces one reel.
        "caption_mechanics": {},      # {words_per_group,position,sync,grouping_algorithm,
                                      #  group_break_pause_ms,max_group_duration_ms,
                                      #  min_group_duration_ms,max_words_per_group,
                                      #  derivation,observed_groups[]}
        # lexicon + role_precedence: "brand nouns render serif" is undecidable
        # without knowing WHICH words are brand nouns and which role wins a tie.
        # transcript_normalization: "verbatim" must mean the SPOKEN word, not the
        # ASR token stream, or a mis-heard brand name ships burned into frame.
        "caption_content_rules": {},  # {fidelity,casing,emoji,punctuation,
                                      #  lexicon{brand_nouns,pill_keywords,payoff_phrases,
                                      #          cta_keyword,unverified},
                                      #  role_precedence[],transcript_normalization{}}
    },
    "color": {
        "tokens": [],                 # {id,hex,role,coverage_note}  (computed + labeled)
        "skins": [],                  # {id,zone_colors,alternation_rule,evidence,confidence,observed_in}
    },
    "motion": {
        "rules": [],                  # {id,target,params{...,duration_s,easing_class},anchor,
                                      #  evidence,confidence,observed_in}
        "audio_synced_rules": [],     # same shape as rules[], anchored to an audio event
        "text_animation": {},         # {in,out,per_word,easing_class}
    },
    "pacing": {},        # computed: shot stats, panel-swap rhythm, speech {wpm, pause_histogram}
    "structure": {
        "beats": [],                  # {id,anchor:{type:absolute|proportional|recurring,s|pct|trigger},rule,evidence,...}
        "patterns": [],               # pass/fail patterns {id,name,pass,fail,evidence,...}
        "screens": [],                # pass/fail screens {id,name,pass,fail,evidence,...}
    },
    "assets": {
        "recurring_motifs": [],       # mascots/sprites {id,desc,evidence,confidence,observed_in}
        "panel_content_types": [],    # {id,desc,evidence,confidence,observed_in}
        "panel_treatments": [],       # {id,corner_radius_px,shadow,border,evidence,confidence,observed_in}
    },
    "audio": {
        "music": {"present": None, "ducking_db": None, "character": "HUMAN-INPUT"},
        "sfx": {"transients": [], "character": "HUMAN-INPUT"},
        "loudness": {},
    },
    "ingredients": [],   # what a clone requires: {id,desc,required:true|false}
    "adapters": {
        "hyperframes": {
            "constants": {},
            "track_map": {},          # role -> track index, filled per build stack
            "tween_recipes": [],      # {motion_rule,gsap}
            "clip_conventions": "class=clip data-start/data-duration/data-track-index, absolute seconds",
        },
        "human_editor": {"checklist": []},
    },
    "merge_log": [],     # {date,source,confirmed,new,conflicts,resolutions}
}

CONFIDENCE = {"provisional", "confirmed"}

# --- layer + resolution (templatizer, 07.28.26) -----------------------------
# LAYER answers "who owns this rule at build time": the editing style (kept) or
# the design system (repainted). Motion TIMING is always `edit` — easing and
# duration are the style being preserved; only its paint is `look`.
#   edit  design system may not touch it
#   look  design system supplies it entirely
#   both  split field-by-field (e.g. a pop's duration is edit, its colour is look)
#   ask   genuinely undecidable — the build asks, the answer is saved to a preset
LAYERS = {"edit", "look", "both", "ask"}

# RESOLUTION replaces the flat `conflict: true` for the four cases that were never
# real disagreements. `conflict` now means only "two sources
# disagree and no one has decided"; `artifact` means the decode itself is wrong.
#   invariant  one conditional rule that looked like two — needs `condition`
#   range      same rule, numeric spread     — needs `default` + `bounds`
#   choice     real either/or per build      — needs `options`
#   derived    must be computed from content — needs `compute`
#   conflict   unresolved, awaiting the user gate
#   artifact   decode error, not a style fact — re-decode, don't resolve
RESOLUTIONS = {"invariant", "range", "choice", "derived", "conflict", "artifact"}
# Kinds that mean "a human still has to look at this" — these keep `conflict: true`.
RESOLUTION_OPEN = {"conflict", "artifact"}
# Required payload per kind. `field` names which rule field the resolution governs
# (dotted for nested: "anchor.s"). A rule carries a LIST of resolutions — one rule
# can be resolved two ways at once (a `choice` about WHERE it applies and a
# `derived` about its rect), so a single object would not fit.
RESOLUTION_REQUIRED = {
    "invariant": ("field", "condition"),
    "range": ("field", "default", "bounds"),
    "choice": ("field", "options"),
    "derived": ("field", "compute"),
    "conflict": (),
    "artifact": (),
}


# ---------------------------------------------------------------- helpers

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def library_dir() -> str:
    c = cfg()
    lib = c["style"].get("library_dir") or os.path.join(c["data_dir"], "styles")
    return lib


def style_dir(slug: str) -> str:
    return os.path.join(library_dir(), slug)


def spec_path(slug: str) -> str:
    return os.path.join(style_dir(slug), SPEC_NAME)


def load_spec(slug: str) -> dict:
    p = spec_path(slug)
    if not os.path.exists(p):
        sys.exit(f"no spec at {p} — run: stylespec.py init {slug}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_spec(slug: str, spec: dict) -> None:
    spec["style"]["updated"] = now_iso()
    p = spec_path(slug)
    tmp = p + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, p)


def get_group(spec: dict, dotted: str):
    node = spec
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


_FIELD_SEL = re.compile(r"^([\w-]+)\[(.*)\]$")


def resolve_field(rule: dict, dotted: str) -> list[tuple[dict, str]]:
    """Resolve a `resolution[].field` path to [(container, leaf_key), ...].

    Grammar, as used on disk:
      params.duration_s          plain dotted walk
      zones[].rect_pct           EVERY element of the list
      zones[id=caption].rect_pct the element whose id matches — keyed by id,
                                 never positional (same doctrine as the merge
                                 comparison table: list order is authoring noise)

    Returns [] when nothing answers to the path. That case is the whole reason
    this exists: a resolution naming a field the rule does not have is a SILENT
    no-op — the consumer falls back to raw `params` and the resolution never
    fires. Two such paths once shipped unnoticed (a near-miss key name, and a
    parent object that never existed), so validate now refuses them.

    Returning (container, key) pairs rather than values lets callers WRITE, which
    is what a build needs.
    """
    parts = dotted.split(".")
    leaf, path = parts[-1], parts[:-1]
    cursors: list = [rule]
    for part in path:
        nxt: list = []
        m = _FIELD_SEL.match(part)
        for cur in cursors:
            if not isinstance(cur, dict):
                continue
            if m:
                name, sel = m.group(1), m.group(2).strip()
                lst = cur.get(name)
                if not isinstance(lst, list):
                    continue
                if sel == "":
                    nxt.extend(e for e in lst if isinstance(e, dict))
                elif sel.startswith("id="):
                    want = sel[3:]
                    nxt.extend(e for e in lst
                               if isinstance(e, dict) and e.get("id") == want)
                # any other selector is unsupported → resolves to nothing, and
                # the caller reports it rather than guessing what was meant
            else:
                v = cur.get(part)
                if isinstance(v, dict):
                    nxt.append(v)
        cursors = nxt
    return [(c, leaf) for c in cursors if isinstance(c, dict) and leaf in c]


def tool(name: str) -> str:
    """ffmpeg / ffprobe from the editor's own setup (runtime.py). Fails with a plain message."""
    try:
        p = rt.tool(name)
    except (KeyError, OSError, ValueError):
        p = ""
    if not p or not os.path.isfile(p):
        sys.exit(f"{name} isn't set up on this computer yet — run the editor setup (editor-doctor) first")
    return p


def ffprobe_duration(path: str) -> float | None:
    try:
        out = subprocess.run(
            [tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30)
        return round(float(out.stdout.strip()), 3)
    except Exception:
        return None


def fingerprint(path: str) -> dict:
    if not os.path.exists(path):
        return {"exists": False}
    return {"exists": True, "size": os.path.getsize(path),
            "duration": ffprobe_duration(path)}


# ---------------------------------------------------------------- init

def cmd_init(args) -> None:
    slug = args.slug
    d = style_dir(slug)
    if os.path.exists(spec_path(slug)):
        sys.exit(f"spec already exists: {spec_path(slug)} (refusing to overwrite)")
    for sub in ("sources", "evidence"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    spec = copy.deepcopy(SPEC_TEMPLATE)
    spec["style"]["slug"] = slug
    spec["style"]["name"] = args.name or slug.replace("-", " ").title()
    spec["style"]["created"] = now_iso()
    save_spec(slug, spec)
    print(f"scaffolded {d}")
    print(f"  {SPEC_NAME} (draft, v0.1.0)")


# ---------------------------------------------------------------- add-source

_URLISH = re.compile(r"^([a-z][a-z0-9+.-]+://|www\.)", re.I)  # a scheme of 2+ letters, so C:/ stays a path


def cmd_add_source(args) -> None:
    """Register a video file that is already on this computer. Never a link, never a download."""
    slug, src_file = args.slug, args.file
    if _URLISH.match(src_file.strip()):
        sys.exit("That is a web link. The style decoder only reads a video file saved on this "
                 "computer; save the reel to a file first, then add that file.")
    if not os.path.isfile(src_file):
        sys.exit(f"No video file at {src_file}")
    spec = load_spec(slug)
    fp = fingerprint(src_file)
    if not fp.get("duration"):
        sys.exit(f"{src_file} isn't a readable video (ffprobe found no duration)")
    for s in spec.get("sources", []):
        if (s.get("fingerprint") or {}) == {"size": fp["size"], "duration": fp["duration"]}:
            sys.exit(f"this video is already registered as {s.get('id')} in {slug}")
    src_id = f"src-{len(spec.get('sources', [])) + 1:02d}"
    if any(s.get("id") == src_id for s in spec.get("sources", [])):
        sys.exit(f"source {src_id} already registered in {slug}")

    src_dir = os.path.join(style_dir(slug), "sources", src_id)
    os.makedirs(os.path.join(src_dir, "frames"), exist_ok=True)
    dest = os.path.join(src_dir, "source.mp4")
    shutil.copy2(src_file, dest)            # byte copy: generation 0, no re-encode

    probe = subprocess.run(
        [tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,avg_frame_rate", "-of", "json", dest],
        capture_output=True, text=True, timeout=30)
    st = (json.loads(probe.stdout or "{}").get("streams") or [{}])[0]
    num, _, den = (st.get("avg_frame_rate") or "0/1").partition("/")
    fps = round(int(num) / int(den), 2) if den and int(den) else None

    record = {
        "id": src_id, "platform": "local", "file": os.path.basename(src_file),
        "added": now_iso(),
        "duration_s": fp["duration"],
        "resolution": f"{st.get('width')}x{st.get('height')}",
        "fps": fps,
        "fingerprint": {"size": fp["size"], "duration": fp["duration"]},
    }
    with open(os.path.join(src_dir, "source.json"), "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    spec["sources"].append(record)
    save_spec(slug, spec)
    print(f"added {src_id}: {dest}")
    print(f"  {record['duration_s']}s {record['resolution']} @{fps}fps · registered in spec")


# ---------------------------------------------------------------- validate

def _check_layer_resolution(rule: dict, tag: str,
                            errors: list[str], warns: list[str]) -> None:
    """Validate the templatizer fields. Both are optional — a spec decoded before
    07.28.26 stays valid — but a MALFORMED one is an error, and a missing layer is
    warned so the build knows it will have to ask."""
    layer = rule.get("layer")
    if layer is None:
        warns.append(f"{tag}: no layer tag — the build will treat it as 'ask'")
    elif layer not in LAYERS:
        errors.append(f"{tag}: layer must be one of {sorted(LAYERS)}, got {layer!r}")

    res_list = rule.get("resolution")
    if res_list is None:
        return
    if not isinstance(res_list, list):
        errors.append(f"{tag}: resolution must be a list of objects, got {type(res_list).__name__}")
        return

    any_open = False
    for n, res in enumerate(res_list):
        rtag = f"{tag}.resolution[{n}]"
        if not isinstance(res, dict):
            errors.append(f"{rtag}: must be an object, got {type(res).__name__}")
            continue
        kind = res.get("kind")
        if kind not in RESOLUTIONS:
            errors.append(f"{rtag}: kind must be one of {sorted(RESOLUTIONS)}, got {kind!r}")
            continue
        any_open = any_open or kind in RESOLUTION_OPEN
        for key in RESOLUTION_REQUIRED[kind]:
            if res.get(key) in (None, "", [], {}):
                errors.append(f"{rtag}: kind={kind} requires {key!r}")

        # A field path nothing answers to is a silent no-op, not a warning:
        # the consumer falls back to raw params and the resolution never fires.
        fld = res.get("field")
        if fld and not resolve_field(rule, fld):
            errors.append(f"{rtag}: field {fld!r} does not resolve on this rule")

        if kind == "range":
            b = res.get("bounds")
            if not (isinstance(b, list) and len(b) == 2 and all(_num(x) for x in b)):
                errors.append(f"{rtag}: bounds must be [min, max] numerics, got {b!r}")
            elif b[0] > b[1]:
                errors.append(f"{rtag}: bounds min {b[0]} > max {b[1]}")
            elif _num(res.get("default")) and not (b[0] <= res["default"] <= b[1]):
                errors.append(f"{rtag}: default {res['default']} outside bounds {b}")
        if kind == "choice":
            opts = res.get("options")
            if isinstance(opts, list) and len(opts) < 2:
                errors.append(f"{rtag}: kind=choice needs 2+ options, got {len(opts)}")

    # Open kinds are exactly the ones that keep the human gate flagged. Keeping the
    # two in sync is what stops a "resolved" rule from quietly staying a blocker.
    if any_open and not rule.get("conflict"):
        errors.append(f"{tag}: an unresolved resolution kind is present but conflict is not set")
    if res_list and not any_open and rule.get("conflict"):
        errors.append(f"{tag}: fully resolved but still flagged conflict:true")


def validate_spec(slug: str, spec: dict) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings)."""
    errors: list[str] = []
    warns: list[str] = []
    d = style_dir(slug)

    if spec.get("spec_version") != SPEC_VERSION:
        errors.append(f"spec_version {spec.get('spec_version')!r} != {SPEC_VERSION!r}")
    st = spec.get("style", {})
    if st.get("slug") != slug:
        errors.append(f"style.slug {st.get('slug')!r} != dir slug {slug!r}")
    if st.get("status") not in ("draft", "approved"):
        errors.append(f"style.status must be draft|approved, got {st.get('status')!r}")

    src_ids = {s.get("id") for s in spec.get("sources", [])}
    if not src_ids:
        warns.append("no sources registered yet")

    for dotted, judgment in RULE_GROUPS:
        group = get_group(spec, dotted)
        if group is None:
            errors.append(f"missing group: {dotted}")
            continue
        if not isinstance(group, list):
            errors.append(f"{dotted} must be a list")
            continue
        if not judgment:
            continue
        for i, rule in enumerate(group):
            tag = f"{dotted}[{i}]" + (f" ({rule.get('id')})" if rule.get("id") else "")
            ev = rule.get("evidence") or []
            if not ev:
                errors.append(f"{tag}: no evidence")
            for ref in ev:
                if not os.path.exists(os.path.join(d, ref)):
                    errors.append(f"{tag}: evidence missing on disk: {ref}")
            conf = rule.get("confidence")
            if conf not in CONFIDENCE:
                errors.append(f"{tag}: confidence must be provisional|confirmed, got {conf!r}")
            obs = set(rule.get("observed_in") or [])
            if not obs:
                errors.append(f"{tag}: observed_in empty")
            elif not obs <= src_ids:
                errors.append(f"{tag}: observed_in {sorted(obs - src_ids)} not in sources")
            elif conf == "confirmed" and len(obs) < 2:
                warns.append(f"{tag}: confirmed but observed in only {len(obs)} source")

            _check_layer_resolution(rule, tag, errors, warns)

    if st.get("status") == "approved" and errors:
        errors.append("status=approved with errors above — approved specs must be clean")
    return errors, warns


def cmd_validate(args) -> None:
    spec = load_spec(args.slug)
    errors, warns = validate_spec(args.slug, spec)
    for w in warns:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    n_rules = sum(len(get_group(spec, g) or []) for g, j in RULE_GROUPS if j)
    print(f"{args.slug}: {n_rules} rules, {len(errors)} errors, {len(warns)} warnings")
    if errors:
        sys.exit(1)
    print("VALIDATE PASS")


# ---------------------------------------------------------------- merge

# Bookkeeping the merge owns — never compared, never treated as a rule difference.
META_KEYS = {"id", "evidence", "observed_in", "confidence", "variants", "conflict",
             "params_by_source", "fields_by_source", "source",
             # templatizer bookkeeping — a human's build-time decision about a rule,
             # not an observation of it. Comparing them would make a resolved rule
             # conflict with an unresolved decode of the same thing.
             "layer", "resolution"}
# Free prose. Two sources will always word these differently; wording is not a
# style difference, so record it per-source but never conflict on it. Includes
# pass/fail criteria, targets, font descriptions and nested `content` blurbs —
# all measured on the proving merge (07.24.26) to be wording noise, while the
# machine-readable siblings (mode_scope, color_token, rect_pct, params) carry the
# real signal.
PROSE_KEYS = {"rule", "desc", "description", "applies_to", "label", "note", "notes",
              "derivation", "measured_from", "selector", "trigger", "appears_when",
              "coverage_note", "one_liner", "pass", "fail", "criteria", "target",
              "font_guess", "alternation_rule", "content"}
# Values arrive as "bg_token (measured #RRGGBB)" — the token is the value, the
# parenthetical is an annotation. Compare tokens, not annotations.
_ANNOT = re.compile(r"\s*\([^)]*\)")
_MIRROR = re.compile(r"^src[-_]?\d+[_-]")   # e.g. src02_target — decode-side workaround keys


def _semantic(rule: dict) -> dict:
    """Everything that makes this rule THIS rule: the fields a clone dereferences.
    Excludes merge bookkeeping, free prose, and per-source mirror keys."""
    return {k: v for k, v in rule.items()
            if k not in META_KEYS and k not in PROSE_KEYS and not _MIRROR.match(k)}


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _wild(v) -> bool:
    """A missing or explicitly-unknown side never conflicts (doctrine: UNKNOWN is legal)."""
    return v is None or (isinstance(v, str) and v.strip().upper() in ("UNKNOWN", "HUMAN-INPUT"))


def _compatible(a, b, tol: float) -> bool:
    """Generic value comparison: numerics within relative tol, containers recursed,
    everything else exact. Used on EVERY semantic field, not just params — a
    difference in case/color_token/mode_scope/anchor is as real as a duration."""
    if _wild(a) or _wild(b):
        return True
    if _num(a) and _num(b):
        base = max(abs(a), abs(b))
        return not (base and abs(a - b) / base > tol)
    if isinstance(a, dict) and isinstance(b, dict):
        # prose keys are skipped at every depth, not just the top level — a
        # nested `content` blurb must not make identical rect_pct look different
        return all(_compatible(a.get(k), b.get(k), tol) for k in set(a) | set(b)
                   if not _MIRROR.match(str(k)) and str(k) not in PROSE_KEYS)
    if isinstance(a, list) and isinstance(b, list):
        # numeric vectors (rect_pct, [x,y,w,h]) are POSITIONAL and need the
        # numeric tolerance — set-comparing them makes 44 vs 46.6 a hard conflict
        if a and b and all(_num(x) for x in a + b):
            return len(a) == len(b) and all(_compatible(x, y, tol) for x, y in zip(a, b))
        if all(isinstance(x, (str, bool)) for x in a + b):
            return set(map(str, a)) == set(map(str, b))    # tags/scopes: order-insensitive
        # lists of identified objects (zones, variants…): compare BY ID, never by
        # position — list order is authoring noise. An entry present in only one
        # source is absence, not contradiction (same doctrine as UNKNOWN).
        if a and b and all(isinstance(x, dict) and "id" in x for x in a + b):
            ma = {x["id"]: x for x in a}
            mb = {x["id"]: x for x in b}
            return all(_compatible(ma.get(k), mb.get(k), tol) for k in set(ma) | set(mb))
        return len(a) == len(b) and all(_compatible(x, y, tol) for x, y in zip(a, b))
    if type(a) is not type(b):
        return False
    if isinstance(a, str):
        return _ANNOT.sub("", a).strip() == _ANNOT.sub("", b).strip()
    return a == b


def _diff_fields(existing: dict, cand: dict, tol: float) -> list[str]:
    """Semantic field names where the two rules genuinely disagree."""
    ea, eb = _semantic(existing), _semantic(cand)
    return sorted(k for k in set(ea) | set(eb) if not _compatible(ea.get(k), eb.get(k), tol))


def _avg_params(a: dict, b: dict) -> dict:
    out = copy.deepcopy(a)
    for k, vb in b.items():
        va = out.get(k)
        if (isinstance(va, (int, float)) and not isinstance(va, bool)
                and isinstance(vb, (int, float)) and not isinstance(vb, bool)):
            out[k] = round((va + vb) / 2, 4)
        elif va in (None, "UNKNOWN") and vb not in (None, "UNKNOWN"):
            out[k] = copy.deepcopy(vb)  # a measurement beats an UNKNOWN
    return out


def cmd_merge(args) -> None:
    slug, src = args.slug, args.source
    spec = load_spec(slug)
    if src not in {s.get("id") for s in spec.get("sources", [])}:
        sys.exit(f"source {src!r} not registered in spec.sources — register it first")
    with open(args.candidate, encoding="utf-8") as f:
        cand = json.load(f)
    tol = cfg()["style"]["merge_tolerance"]

    confirmed = new = conflicts = 0
    conflict_tags: list[str] = []
    for dotted, judgment in RULE_GROUPS:
        if not judgment:
            continue
        cand_rules = get_group(cand, dotted)
        if not cand_rules:
            continue
        group = get_group(spec, dotted)
        by_id = {r.get("id"): r for r in group if r.get("id")}
        for cr in cand_rules:
            rid = cr.get("id")
            # drop decode-side mirror keys (srcNN_*): they were a workaround for the
            # params-only comparison this merge no longer uses. The full candidate
            # file stays on disk under sources/<src>/ as the verbatim record.
            for k in [k for k in cr if _MIRROR.match(str(k))]:
                cr.pop(k)
            if isinstance(cr.get("params"), dict):
                for k in [k for k in cr["params"] if _MIRROR.match(str(k))]:
                    cr["params"].pop(k)
            cr.setdefault("observed_in", [src])
            cr.setdefault("confidence", "provisional")
            existing = by_id.get(rid)
            if existing is None:
                group.append(cr)                       # NEW -> provisional
                new += 1
                continue

            # Compare EVERY semantic field, not just params. A role whose
            # mode_scope, color_token, case or anchor type differs is a real
            # conflict even when params are identical (or absent entirely).
            diffs = _diff_fields(existing, cr, tol)
            c_sem = _semantic(cr)
            if not diffs:                              # MATCH -> confirm
                e_par, c_par = existing.get("params", {}), cr.get("params", {})
                merged = _avg_params(e_par, c_par)
                if merged:
                    existing.setdefault("params_by_source", {})[src] = c_par
                    existing["params"] = merged
                # union, never discard: a field the candidate measured and the
                # existing rule lacks gets ADOPTED rather than dropped on the floor
                for k, v in c_sem.items():
                    if k != "params" and (k not in existing or _wild(existing.get(k))):
                        existing[k] = v
                existing.setdefault("fields_by_source", {})[src] = {
                    k: v for k, v in cr.items() if k not in META_KEYS}
                if src not in existing.setdefault("observed_in", []):
                    existing["observed_in"].append(src)
                existing["confidence"] = "confirmed"
                existing.setdefault("evidence", []).extend(
                    e for e in cr.get("evidence", []) if e not in existing["evidence"])
                confirmed += 1
            else:                                      # CONFLICT -> keep both as variants
                existing.setdefault("variants", []).append({
                    "source": src,
                    "differing_fields": diffs,
                    "fields": {k: c_sem.get(k) for k in diffs},
                    "params": cr.get("params", {}),
                    "evidence": cr.get("evidence", []),
                })
                existing["conflict"] = True
                conflicts += 1
                conflict_tags.append(f"{dotted}:{rid} [{', '.join(diffs)}]")

    if args.dry_run:
        print(f"DRY RUN — nothing written. {src} into {slug}: "
              f"{confirmed} would confirm, {new} new, {conflicts} conflicts")
        for t in conflict_tags:
            print(f"  CONFLICT {t}")
        sys.exit(2 if conflicts else 0)

    ver = spec["style"]["version"].split(".")
    ver[1] = str(int(ver[1]) + 1)
    ver[2] = "0"
    spec["style"]["version"] = ".".join(ver)
    spec["merge_log"].append({
        "date": now_iso(), "source": src,
        "confirmed": confirmed, "new": new, "conflicts": conflicts,
        "resolutions": [],  # filled at the user conflict gate
    })
    save_spec(slug, spec)
    print(f"merged {src} into {slug} v{spec['style']['version']}: "
          f"{confirmed} confirmed, {new} new (provisional), {conflicts} conflicts")
    for t in conflict_tags:
        print(f"  CONFLICT {t} — resolve at the review gate (variants kept)")
    if conflicts:
        sys.exit(2)  # distinct code: merge done, user gate required


# ---------------------------------------------------------------- contact-sheet

def cmd_contact_sheet(args) -> None:
    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow (the image library) isn't installed in this Python — contact sheets need it")
    slug = args.slug
    spec = load_spec(slug)
    d = style_dir(slug)
    out_dir = os.path.join(d, "evidence")
    os.makedirs(out_dir, exist_ok=True)
    date = datetime.now().strftime("%m.%d.%y")

    groups = [g for g, j in RULE_GROUPS if j and (not args.group or g == args.group)]
    made = 0
    for dotted in groups:
        rules = get_group(spec, dotted) or []
        entries = []  # (rule_id, frame_path)
        for r in rules:
            for ref in r.get("evidence", []):
                p = os.path.join(d, ref)
                if os.path.exists(p) and ref.lower().endswith((".jpg", ".jpeg", ".png")):
                    entries.append((r.get("id", "?"), p))
        if not entries:
            continue
        tile_w, cols = 320, 4
        imgs = []
        for _, p in entries:
            im = Image.open(p)
            h = int(im.height * tile_w / im.width)
            imgs.append(im.resize((tile_w, h)))
        rows: list[list] = [imgs[i:i + cols] for i in range(0, len(imgs), cols)]
        row_h = [max(im.height for im in row) for row in rows]
        sheet = Image.new("RGB", (tile_w * cols, sum(row_h)), (24, 24, 24))
        y = 0
        for row, rh in zip(rows, row_h):
            for x, im in enumerate(row):
                sheet.paste(im, (x * tile_w, y))
            y += rh
        base = dotted.replace(".", "-")
        sheet_path = os.path.join(out_dir, f"{base} - Contact Sheet - {date}.jpg")
        sheet.save(sheet_path, quality=88)
        # sidecar: rule text next to its frames, in tile order
        with open(os.path.join(out_dir, f"{base} - Contact Sheet - {date}.md"),
                  "w", encoding="utf-8") as f:
            f.write(f"# {dotted} — evidence sheet ({date})\n\n"
                    f"Tiles left-to-right, top-to-bottom:\n\n")
            for i, (rid, p) in enumerate(entries, 1):
                rule = next((r for r in rules if r.get("id") == rid), {})
                text = rule.get("rule") or rule.get("label") or rule.get("applies_to") or ""
                f.write(f"{i}. **{rid}** — {text} — `{os.path.relpath(p, d)}`\n")
        print(f"sheet: {sheet_path} ({len(entries)} tiles)")
        made += 1
    if not made:
        sys.exit("no evidence frames found to sheet")


# ---------------------------------------------------------------- heldout

def _norm(ref: str) -> str:
    return os.path.normpath(ref).replace(os.sep, "/")


def cmd_heldout(args) -> None:
    """Rung 3: frames the spec does NOT cite, one empty verdict slot per rule per frame.
    The scoring is Claude's judgment; this only picks the frames and lays out the sheet."""
    slug = args.slug
    spec = load_spec(slug)
    d = style_dir(slug)
    rules, cited = [], set()
    for dotted, judgment in RULE_GROUPS:
        if not judgment:
            continue
        for i, r in enumerate(get_group(spec, dotted) or []):
            if not isinstance(r, dict):
                continue
            rules.append(r.get("id") or f"{dotted}[{i}]")
            refs = list(r.get("evidence") or [])
            for v in r.get("variants") or []:
                refs += v.get("evidence") or []
            cited |= {_norm(e) for e in refs if isinstance(e, str)}
    if not rules:
        sys.exit("the spec has no rules yet — write rules before the held-out screen")

    base = sorted(_norm(os.path.relpath(p, d)) for src in spec.get("sources", [])
                  for p in glob.glob(os.path.join(d, "sources", src["id"], "frames", "base_*.jpg")))
    if args.frames:
        picked = []
        for f in (x.strip() for x in args.frames.split(",") if x.strip()):
            hits = [b for b in base if b == _norm(f) or os.path.basename(b) == f]
            if len(hits) > 1:
                sys.exit(f"{f} matches frames in {len(hits)} sources — give the full path, e.g. {hits[0]}")
            ref = hits[0] if hits else _norm(f)
            if ref in cited:
                sys.exit(f"{ref} is cited as evidence by a rule — a held-out frame must be uncited")
            if not os.path.isfile(os.path.join(d, ref)):
                sys.exit(f"no frame at {ref}")
            picked.append(ref)
    else:
        free = [b for b in base if b not in cited]
        n = min(args.n, len(free))
        if n <= 0:
            sys.exit("no uncited base frames left — run styleframes --pass base first")
        picked = [free[int(i * len(free) / n)] for i in range(n)]   # spread across the runtime

    out = os.path.join(d, "heldout.json")
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            old = json.load(f)
        if any(v is not None for fr in (old.get("verdicts") or {}).values() for v in fr.values()):
            sys.exit(f"{out} already holds scores — move it aside before picking new frames")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "created": now_iso(), "style_version": spec["style"]["version"],
            "frames": picked, "rules": rules,
            "verdicts": {fr: {rid: None for rid in rules} for fr in picked},
            "note": "null = not scored yet. Score each rule per frame: pass | fail | n/a.",
        }, f, indent=2)
        f.write("\n")
    print(f"held-out: {len(picked)} uncited frame(s) x {len(rules)} rule(s) -> {out}")
    for fr in picked:
        print(f"  {fr}")


# ---------------------------------------------------------------- coverage

def cmd_coverage(args) -> None:
    """Mechanical completeness audit — arithmetic, not opinion. Rung 2 of the
    confirmation ladder (see stylespec-contract.md)."""
    slug = args.slug
    spec = load_spec(slug)
    d = style_dir(slug)
    findings: list[str] = []

    # --- runtime coverage: does every second have a layout mode?
    for src in spec.get("sources", []):
        dur = src.get("duration_s") or 0
        tlf = os.path.join(d, "sources", src["id"], "layout_timeline.json")
        if not os.path.exists(tlf):
            findings.append(f"{src['id']}: no layout_timeline.json — runtime coverage unverifiable")
            continue
        with open(tlf, encoding="utf-8") as f:
            tlf_data = json.load(f)
        # Two legal shapes. SEGMENTS ({t_start,t_end,mode_id}) are contiguous
        # spans — a long segment is fully classified, so check CONTIGUITY.
        # POINTS ({t,mode}) are samples — there the gap between samples is the
        # only thing measurable, so check spacing. Judging segments by point
        # spacing flags every span >3s as a hole, which is a false positive.
        segs = tlf_data.get("segments") or [
            x for x in tlf_data.get("timeline", []) if "t_start" in x and "t_end" in x]
        if segs:
            segs = sorted(segs, key=lambda s: s["t_start"])
            print(f"  {src['id']}: {len(segs)} contiguous segments over {dur}s")
            if segs[0]["t_start"] > 0.1:
                findings.append(f"{src['id']}: timeline starts at {segs[0]['t_start']}s, not 0")
            for a, b in zip(segs, segs[1:]):
                if b["t_start"] - a["t_end"] > 0.05:
                    findings.append(f"{src['id']}: timeline hole "
                                    f"{a['t_end']}s->{b['t_start']}s (segments not contiguous)")
            if dur - segs[-1]["t_end"] > 0.2:
                findings.append(f"{src['id']}: timeline ends at {segs[-1]['t_end']}s, "
                                f"{dur - segs[-1]['t_end']:.2f}s short of the {dur}s runtime")
            continue
        tl = tlf_data.get("timeline", [])
        stamps = sorted(x["t"] for x in tl if "t" in x)
        if not stamps:
            findings.append(f"{src['id']}: layout_timeline has no timestamps")
            continue
        gaps = [(round(a, 2), round(b, 2)) for a, b in zip(stamps, stamps[1:]) if b - a > 3.0]
        head = stamps[0] if stamps[0] > 1.5 else None
        tail = round(dur - stamps[-1], 2) if dur - stamps[-1] > 3.0 else None
        cov = round((len(stamps) / dur) if dur else 0, 2)
        print(f"  {src['id']}: {len(stamps)} classified points over {dur}s ({cov}/s sampling)")
        if head:
            findings.append(f"{src['id']}: first classification at {head}s — opening unclassified")
        if tail:
            findings.append(f"{src['id']}: last classification {tail}s before the end — outro unclassified")
        for a, b in gaps:
            findings.append(f"{src['id']}: {b - a:.1f}s unclassified span ({a}s->{b}s)")

    # --- group population
    empty = [g for g, _ in RULE_GROUPS if not (get_group(spec, g) or [])]
    for g in empty:
        findings.append(f"rule group empty: {g}")

    # --- structural anchors
    for b in get_group(spec, "structure.beats") or []:
        a = b.get("anchor") or {}
        if a.get("type") not in ("absolute", "proportional", "recurring"):
            findings.append(f"beat {b.get('id')}: anchor type missing/invalid")
        elif a.get("type") == "absolute" and a.get("s") is None:
            findings.append(f"beat {b.get('id')}: absolute anchor without .s")
        elif a.get("type") == "proportional" and a.get("pct") is None:
            findings.append(f"beat {b.get('id')}: proportional anchor without .pct")
        elif a.get("type") == "recurring" and not a.get("trigger"):
            findings.append(f"beat {b.get('id')}: recurring anchor without .trigger")

    # --- UNKNOWN census (legal, but must be visible)
    unknowns: list[str] = []

    def scan(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                scan(v, f"{path}.{k}" if path else k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                scan(v, f"{path}[{i}]")
        elif isinstance(o, str) and o.strip().upper().startswith(("UNKNOWN", "HUMAN-INPUT")):
            # startswith, not equality: annotated values ("UNKNOWN (not measured)")
            # are still UNKNOWNs and an exact-match census hid 7 of them (07.28.26).
            # Print the value verbatim so the annotation stays visible.
            unknowns.append(f"{path} = {o.strip()}")
    scan(spec)

    # --- clone-readiness: the fields a build session dereferences
    ad = (spec.get("adapters") or {}).get("hyperframes") or {}
    if not ad.get("constants"):
        findings.append("adapters.hyperframes.constants empty — nothing for a build to import")
    if not ad.get("tween_recipes"):
        findings.append("adapters.hyperframes.tween_recipes empty — motion rules unbuildable")
    if not spec.get("ingredients"):
        findings.append("ingredients[] empty — a clone cannot check its raw materials")
    for r in get_group(spec, "typography.roles") or []:
        if not r.get("closest_available"):
            findings.append(f"typography role {r.get('id')}: no closest_available font (unbuildable)")
        if not r.get("size_metric"):
            findings.append(f"typography role {r.get('id')}: size_pct_of_width without size_metric "
                            "(cap-height vs em is a ~1.5x difference)")
        if not r.get("mode_scope"):
            findings.append(f"typography role {r.get('id')}: no mode_scope — role collisions undecidable")

    # --- determinism gates (every one of these is a blind-test finding, 07.24.26).
    # These fields are what separate "describes the video" from "two editors get
    # the same frame". A spec can pass validate and still be non-deterministic.
    typ = spec.get("typography") or {}
    ccr = typ.get("caption_content_rules") or {}
    cm = typ.get("caption_mechanics") or {}
    canvas = spec.get("canvas") or {}
    if not canvas.get("layout_timeline") and not canvas.get("layout_grammar_mode_sequence"):
        findings.append("canvas.layout_timeline AND layout_grammar_mode_sequence both empty — "
                        "mode ORDER is unrecoverable from the spec (a ref is not enough)")
    if not ccr:
        findings.append("typography.caption_content_rules empty — cannot write new captions in-style")
    else:
        if not cm.get("grouping_algorithm"):
            findings.append("caption_mechanics.grouping_algorithm missing — a words-per-group "
                            "distribution is not a rule; captions become a guess per frame")
        if not ccr.get("role_precedence"):
            findings.append("caption_content_rules.role_precedence missing — overlapping "
                            "typography roles have no tiebreaker")
        lex = ccr.get("lexicon") or {}
        if not lex.get("brand_nouns"):
            findings.append("caption_content_rules.lexicon.brand_nouns missing — a "
                            "'brand nouns render serif' rule is undecidable without the list")
        if not ccr.get("transcript_normalization"):
            findings.append("caption_content_rules.transcript_normalization missing — a verbatim "
                            "rule over a raw ASR stream burns mis-heard words into frame")

    # --- contradiction sweep: same id asserted twice, or a screen restating a
    # treatment instead of referencing it
    seen_ids: dict[str, str] = {}
    for dotted, judgment in RULE_GROUPS:
        if not judgment:
            continue
        for r in get_group(spec, dotted) or []:
            rid = r.get("id")
            if rid and rid in seen_ids:
                findings.append(f"duplicate rule id {rid!r} in {seen_ids[rid]} and {dotted}")
            elif rid:
                seen_ids[rid] = dotted

    # --- confidence posture
    all_rules = [r for g, j in RULE_GROUPS if j for r in (get_group(spec, g) or [])]
    prov = sum(1 for r in all_rules if r.get("confidence") == "provisional")
    conflicts = [r.get("id") for r in all_rules if r.get("conflict")]

    print(f"\n{slug}: {len(all_rules)} rules · {prov} provisional · "
          f"{len(unknowns)} UNKNOWN/HUMAN-INPUT · {len(conflicts)} unresolved conflict(s)")
    if unknowns:
        print("\nUNKNOWN / HUMAN-INPUT census (legal by doctrine, listed so nothing hides):")
        for u in unknowns:
            print(f"  · {u}")
    if conflicts:
        print(f"\nunresolved merge conflicts: {', '.join(str(c) for c in conflicts)}")

    # --- templatizer posture: who owns each rule, and how the resolution buckets landed
    layers: dict[str, int] = {}
    buckets: dict[str, list] = {}
    for r in all_rules:
        layers[r.get("layer") or "ask (untagged)"] = layers.get(r.get("layer") or "ask (untagged)", 0) + 1
        for res in (r.get("resolution") or []):
            kind = res.get("kind") if isinstance(res, dict) else None
            if kind:
                buckets.setdefault(kind, []).append(r.get("id"))
    print("\nlayer census (design system may repaint look/both, never edit): "
          + " · ".join(f"{k} {v}" for k, v in sorted(layers.items())))
    if buckets:
        print("resolutions: " + " · ".join(
            f"{k} {len(v)}" for k, v in sorted(buckets.items())))
        for k in sorted(buckets):
            if k in RESOLUTION_OPEN:
                print(f"  ! {k} (needs a human): {', '.join(str(i) for i in buckets[k])}")
    if findings:
        print("\nGAPS:")
        for f_ in findings:
            print(f"  GAP {f_}")
        print(f"\n{len(findings)} gap(s) — coverage INCOMPLETE")
        sys.exit(1)
    print("\nCOVERAGE PASS — no mechanical gaps")


# ---------------------------------------------------------------- index

def cmd_index(_args) -> None:
    lib = library_dir()
    os.makedirs(lib, exist_ok=True)
    entries = []
    for slug in sorted(os.listdir(lib)):
        p = os.path.join(lib, slug, SPEC_NAME)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            spec = json.load(f)
        errors, _ = validate_spec(slug, spec)
        st = spec["style"]
        status = st.get("status", "draft")
        if status == "approved" and errors:
            print(f"WARN {slug}: approved but fails validation — indexed as draft")
            status = "draft"
        entries.append({
            "slug": st["slug"], "name": st["name"], "version": st["version"],
            "status": status, "sources": len(spec.get("sources", [])),
            "updated": st.get("updated", ""),
            "one_liner": spec.get("one_liner", ""),
        })
    idx = os.path.join(lib, "index.json")
    with open(idx, "w", encoding="utf-8") as f:
        json.dump({"updated": now_iso(), "styles": entries}, f, indent=2)
        f.write("\n")
    print(f"indexed {len(entries)} style(s) -> {idx}")


# ---------------------------------------------------------------- fingerprint

def cmd_fingerprint(args) -> None:
    print(json.dumps(fingerprint(args.path), indent=2))


# ---------------------------------------------------------------- main

def main() -> None:
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="scaffold a new style dir + skeleton spec")
    p.add_argument("slug")
    p.add_argument("--name", default="")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("add-source", help="register a local video file as the next src-NN")
    p.add_argument("slug")
    p.add_argument("file", help="a video file on this computer (never a link)")
    p.set_defaults(fn=cmd_add_source)

    p = sub.add_parser("validate", help="schema + evidence gate (exit 1 = FAIL)")
    p.add_argument("slug")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("merge", help="fold a new source's candidate rules into the spec")
    p.add_argument("slug")
    p.add_argument("--source", required=True, help="source id already in spec.sources")
    p.add_argument("--candidate", required=True, help="candidate rules JSON (same shape)")
    p.add_argument("--dry-run", action="store_true",
                   help="report confirms/new/conflicts and write NOTHING (exit 2 if conflicts)")
    p.set_defaults(fn=cmd_merge)

    p = sub.add_parser("contact-sheet", help="tile evidence frames per rule group")
    p.add_argument("slug")
    p.add_argument("--group", default="", help="single dotted group (default: all)")
    p.set_defaults(fn=cmd_contact_sheet)

    p = sub.add_parser("heldout", help="pick uncited base frames + empty verdict slots")
    p.add_argument("slug")
    p.add_argument("--n", type=int, default=10, help="frames to pick (default 10)")
    p.add_argument("--frames", default="", help="comma list of frames to use instead (must be uncited)")
    p.set_defaults(fn=cmd_heldout)

    p = sub.add_parser("coverage", help="mechanical completeness audit (exit 1 = gaps)")
    p.add_argument("slug")
    p.set_defaults(fn=cmd_coverage)

    p = sub.add_parser("index", help="rebuild <library>/index.json")
    p.set_defaults(fn=cmd_index)

    p = sub.add_parser("fingerprint", help="{exists,size,duration} for a file")
    p.add_argument("path")
    p.set_defaults(fn=cmd_fingerprint)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
