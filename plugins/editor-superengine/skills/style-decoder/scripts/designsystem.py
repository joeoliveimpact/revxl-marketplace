#!/usr/bin/env python3
"""style-decoder — design-system registry (the swappable LOOK layer).

An editing style says HOW a video is cut: caption grouping, cut timing, beat
structure, motion. A design system says how it LOOKS: palette, type, radii,
border weights, spacing, panel margins. This registry holds the looks, so one
decoded style can render under any of them without the cut changing.

Subcommands:
    list                                    id · kind · coverage · drift
    show <id> [--width N]                   resolved entry; *_pct_w gain *_px siblings
    capabilities <id>                       what it fills, what it aliases, what that COSTS
    validate <id|--all> [--reseal]          the fail-closed gates
    fonts <id> [--json]                     per family: vendored | MISSING
    scaffold --css <path> [--scope SEL]     print a stub entry; writes NOTHING
    index                                   rebuild <registry>/index.json

Doctrine (full text: designsystem-contract.md):
  - Two kinds. `base` can be a build's look. `enclave` never can — it paints only
    the elements it owns (e.g. an embedded product UI), and cannot be passed as --design-system.
  - NO VALUE EVER FALLS BACK FROM ONE ENTRY TO ANOTHER. Gaps close inside an entry
    (alias a sibling role) or by not drawing the element (omit). That single rule
    is what makes cross-system colour bleed structurally impossible.
  - Motion has no roles. Easing and duration are the EDIT, not the look (07.28.26).
  - Type SIZE has no roles. A caption's size as a share of frame width is what makes
    the composition read; changing it changes wrap and frame balance (07.28.26).
  - Unknown role keys are an ERROR — that is what enforces both exclusions.
  - One length unit: percent of output width, suffix `_pct_w`, converted once at
    authoring time against a declared reference_width_px.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "_shared"))
sys.path.insert(0, _HERE)
from enginecfg import cfg  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

REGISTRY_VERSION = "1.0"
KINDS = {"base", "enclave"}

# --- the role list ----------------------------------------------------------
# Every role traces to a named `look`/`both` field in a style spec. `req` = the
# floor a base entry must clear; it is set to what a THIN real-world system can
# fill, so "required" never means "unusable".
# `absent_default` documents the sane policy when a role is legitimately missing.
ROLES: dict[str, dict] = {
    # palette — 15
    "palette.bg.page":          {"req": True,  "why": "page / skin background"},
    "palette.bg.alt":           {"req": False, "why": "second skin / light panel"},
    "palette.surface.card":     {"req": True,  "why": "screenshot + document cards"},
    "palette.surface.card_alt": {"req": False, "why": "stacked-card backing"},
    "palette.ink.primary":      {"req": True,  "why": "caption ink"},
    "palette.ink.inverse":      {"req": True,  "why": "ink on accent / dark fills"},
    "palette.ink.muted":        {"req": False, "why": "second text tier, chips"},
    "palette.accent.primary":   {"req": True,  "why": "pills, frame, seam, CTA keyword"},
    "palette.accent.secondary": {"req": False, "why": "annotation ring, payoff mid-tone"},
    "palette.accent.emphasis":  {"req": False, "why": "payoff emphasis (may be a gradient)"},
    "palette.accent.hilite":    {"req": False, "why": "hook highlight bar"},
    "palette.border.accent":    {"req": True,  "why": "accent frame around panels — structural"},
    "palette.border.hairline":  {"req": False, "why": "faint card edge"},
    "palette.pill.fill":        {"req": False, "why": "caption pill, mention pill"},
    "palette.pill.quiet_fill":  {"req": False, "why": "deliberately quiet pill"},
    # type — 10. NO SIZE ROLE: size_pct_of_width is `edit` (07.28.26).
    "type.body.family":         {"req": True,  "why": "default caption face"},
    "type.body.weight":         {"req": True,  "why": "default caption weight"},
    "type.body.tracking_em":    {"req": False, "why": "caption letter_spacing"},
    "type.display.family":      {"req": False, "why": "display / serif roles"},
    "type.display.weight":      {"req": False, "why": "display weight"},
    "type.display.style":       {"req": False, "why": "italic display roles — its own axis"},
    "type.display.tracking_em": {"req": False, "why": "display tracking"},
    "type.heavy.family":        {"req": False, "why": "heavy / black payoff face"},
    "type.heavy.weight":        {"req": False, "why": "heavy weight"},
    "type.line_height":         {"req": False, "why": "multi-line role line_height"},
    # geometry — 8, all percent-of-width
    "geometry.radius.card_pct_w":        {"req": True,  "why": "card corner radius"},
    "geometry.radius.pill_pct_w":        {"req": False, "why": "pills; 'full' = half-height"},
    "geometry.border.accent_pct_w":      {"req": True,  "why": "accent border weight"},
    "geometry.border.hairline_pct_w":    {"req": False, "why": "hairline weight"},
    "geometry.space.panel_margin_pct_w": {"req": True,  "why": "panel margin"},
    "geometry.space.base_pct_w":         {"req": True,  "why": "one spacing step"},
    "geometry.space.tight_pct_w":        {"req": False, "why": "tight offset (stacked cards)"},
    "geometry.space.loose_pct_w":        {"req": False, "why": "generous step"},
    # effect — 3
    "effect.shadow.card":       {"req": False, "why": "card shadow"},
    "effect.glow.accent":       {"req": False, "why": "accent glow"},
    "effect.texture.ground":    {"req": False, "why": "background shadow / grain"},
}
REQUIRED = {k for k, v in ROLES.items() if v["req"]}
BLOCKS = ("palette", "type", "geometry", "effect")
# The entry schema is CLOSED. Anything else is refused, so a well-meaning author
# cannot add a `motion` block and get silence instead of an answer.
ENTRY_KEYS = {
    "registry_version", "id", "name", "kind", "reference_width_px", "authored",
    "provenance", "source_files", "exclusive_colors", "owns_nouns",
    "type_policy", "geometry_policy", "fonts", "absent", "notes", *BLOCKS,
}

# A spacing ramp is deliberately NOT stored. One system may define --sp-1..5 on an
# 8px base and another --sp-1..12 on a 4px base; importing the ramp would import
# that collision. The registry stores only what a video actually places.

_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_CSS_VAR = re.compile(r"^\s*(--[\w-]+)\s*:\s*([^;]+);", re.M)


# ---------------------------------------------------------------- helpers

def registry_dir() -> str:
    c = cfg()
    return c["designsystem"].get("registry_dir") or os.path.join(c["data_dir"], "designsystems")


def fonts_dir() -> str:
    return os.path.join(registry_dir(), "_fonts")


def entry_path(ds_id: str) -> str:
    return os.path.join(registry_dir(), f"{ds_id}.json")


def load_entry(ds_id: str) -> dict:
    p = entry_path(ds_id)
    if not os.path.exists(p):
        sys.exit(f"no design system {ds_id!r} at {p}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def all_ids() -> list[str]:
    d = registry_dir()
    if not os.path.isdir(d):
        return []
    return sorted(n[:-5] for n in os.listdir(d)
                  if n.endswith(".json") and n != "index.json")


def sha256_of(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_role(entry: dict, role: str):
    """Role values live under their block: 'palette.bg.page' -> entry['palette']['bg.page']."""
    block, _, rest = role.partition(".")
    return (entry.get(block) or {}).get(rest)


def iter_values(entry: dict):
    """Yield (role, value_dict) for every authored value across all blocks."""
    for block in BLOCKS:
        for rest, val in (entry.get(block) or {}).items():
            yield f"{block}.{rest}", val


def resolve_role(entry: dict, role: str, _seen=None):
    """Resolve a role to its value dict, following `absent` aliases.

    Returns (value_dict|None, provenance) where provenance is one of
    'authored' | 'aliased:<role>' | 'omitted' | 'missing'. Aliases resolve ONLY
    within this entry — there is deliberately no cross-entry fallback.
    """
    _seen = _seen or set()
    if role in _seen:
        return None, "missing"          # cycle; validate reports it separately
    v = get_role(entry, role)
    if v is not None:
        return v, "authored"
    policy = (entry.get("absent") or {}).get(role)
    if policy == "omit":
        return None, "omitted"
    if isinstance(policy, str) and policy.startswith("alias:"):
        target = policy[6:]
        val, _ = resolve_role(entry, target, _seen | {role})
        return val, f"aliased:{target}"
    return None, "missing"


# ---------------------------------------------------------------- validate

def validate_entry(entry: dict, ds_id: str, others: dict[str, dict]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []

    if entry.get("registry_version") != REGISTRY_VERSION:
        errors.append(f"registry_version {entry.get('registry_version')!r} != {REGISTRY_VERSION!r}")
    if entry.get("id") != ds_id:
        errors.append(f"id {entry.get('id')!r} != filename stem {ds_id!r}")
    kind = entry.get("kind")
    if kind not in KINDS:
        errors.append(f"kind must be one of {sorted(KINDS)}, got {kind!r}")

    enclave = kind == "enclave"
    # An enclave borrows type/geometry from whatever base frames it (an embedded
    # brand block typically reads font-family: var(--font-sans, ...)).
    inherits = {b for b in ("type", "geometry")
                if entry.get(f"{b}_policy") == "inherit_base"}

    if not enclave and not entry.get("reference_width_px"):
        errors.append("base entries need reference_width_px (a px token is meaningless without it)")
    if enclave:
        if not entry.get("exclusive_colors"):
            errors.append("enclave must declare exclusive_colors")
        if not entry.get("owns_nouns"):
            errors.append("enclave must declare owns_nouns")

    # --- unknown TOP-LEVEL keys. Without this, an author who adds a whole
    # `motion` block gets silence: iter_values only walks the four known blocks,
    # so the block is ignored rather than refused, and they believe they mapped
    # something that does nothing. Silence is the failure mode being closed here.
    for key in entry:
        if key not in ENTRY_KEYS:
            errors.append(f"unknown top-level key {key!r} — the schema is closed "
                          f"(motion is excluded by design: it is the edit, not the look)")

    # --- unknown role keys. This is the check that keeps size OUT.
    for role, _ in iter_values(entry):
        if role not in ROLES:
            errors.append(f"unknown role {role!r} — not in the schema "
                          f"(motion and type-size are excluded by design)")
    for role in (entry.get("absent") or {}):
        if role not in ROLES:
            errors.append(f"unknown role in absent: {role!r}")

    # --- completeness: every role in exactly one of {values, absent}
    authored = {r for r, _ in iter_values(entry)}
    declared_absent = set(entry.get("absent") or {})
    both = authored & declared_absent
    for r in sorted(both):
        errors.append(f"{r}: present in both values and absent — pick one")
    for role, meta in ROLES.items():
        if role in authored or role in declared_absent:
            continue
        if enclave and role.split(".")[0] in inherits:
            continue                     # legitimately supplied by the base
        if enclave and role.split(".")[0] == "effect":
            continue                     # enclaves paint colour only
        errors.append(f"{role}: neither authored nor declared in absent "
                      f"({meta['why']})")

    # --- absent policies
    for role, policy in (entry.get("absent") or {}).items():
        if role in REQUIRED and policy == "omit":
            errors.append(f"{role} is REQUIRED and cannot be omitted")
        if isinstance(policy, str) and policy.startswith("alias:"):
            target = policy[6:]
            if target not in ROLES:
                errors.append(f"{role}: alias target {target!r} is not a role")
            else:
                val, prov = resolve_role(entry, role)
                if val is None:
                    errors.append(f"{role}: alias chain resolves to nothing ({prov})")
        elif policy != "omit":
            errors.append(f"{role}: absent policy must be 'omit' or 'alias:<role>', got {policy!r}")

    # --- required roles must actually resolve
    for role in sorted(REQUIRED):
        if enclave and role.split(".")[0] in inherits:
            continue
        val, prov = resolve_role(entry, role)
        if val is None:
            errors.append(f"{role}: REQUIRED but resolves to nothing ({prov})")

    # --- value shapes
    for role, val in iter_values(entry):
        if not isinstance(val, dict) or "v" not in val:
            errors.append(f"{role}: value must be {{v, from, note?}}")
            continue
        if not val.get("from"):
            errors.append(f"{role}: missing 'from' — a value with no recorded "
                          f"source is unreviewable")
        v = val["v"]
        if role.startswith("palette.") and isinstance(v, str):
            if not (_HEX.match(v) or v.startswith(("rgba(", "rgb(", "linear-gradient("))):
                errors.append(f"{role}: {v!r} is not a hex / rgba() / gradient")
        if role.endswith("_pct_w"):
            if v == "full":
                pass
            elif not isinstance(v, (int, float)) or isinstance(v, bool) or not (0 <= v <= 50):
                errors.append(f"{role}: {v!r} must be a percent of width in [0, 50] (or 'full')")

    # --- exclusivity: a colour another entry owns cannot appear here
    mine = {str(val.get("v")).lower() for role, val in iter_values(entry)
            if role.startswith("palette.") and isinstance(val, dict)}
    for other_id, other in others.items():
        if other_id == ds_id:
            continue
        for locked in (other.get("exclusive_colors") or []):
            if locked.lower() in mine:
                errors.append(f"colour {locked} is exclusive to {other_id!r} and "
                              f"must not appear here")

    # --- fonts: declared families must be vendored, and used families declared
    declared = {f.get("family") for f in (entry.get("fonts") or [])}
    for f in (entry.get("fonts") or []):
        for rel in (f.get("files") or []):
            if not os.path.exists(os.path.join(registry_dir(), rel)):
                errors.append(f"font {f.get('family')}: file not vendored: {rel}")
        if not f.get("files"):
            errors.append(f"font {f.get('family')}: no files — a CDN-only font "
                          f"renders as a silent fallback offline")
    for role in ("type.body.family", "type.display.family", "type.heavy.family"):
        val, prov = resolve_role(entry, role)
        if val and prov == "authored":
            fam = val.get("v")
            if fam and fam not in declared:
                errors.append(f"{role}: {fam!r} is used but not declared in fonts[]")
    used = {(resolve_role(entry, r)[0] or {}).get("v")
            for r in ("type.body.family", "type.display.family", "type.heavy.family")}
    for fam in sorted(declared - used):
        warns.append(f"font {fam!r} is vendored but no role uses it")

    # --- source drift
    for sf in (entry.get("source_files") or []):
        p = os.path.join(os.getcwd(), sf.get("path", ""))
        now = sha256_of(p)
        if now is None:
            warns.append(f"source file missing: {sf.get('path')}")
        elif sf.get("sha256") and now != sf["sha256"]:
            warns.append(f"source drift — {sf['path']}\n"
                         f"     was {sf['sha256'][:12]}…  now {now[:12]}…  "
                         f"-> diff, then update the entry or re-run with --reseal")
    return errors, warns


# ---------------------------------------------------------------- commands

def cmd_validate(args) -> None:
    ids = all_ids() if args.all else [args.id]
    if not ids:
        sys.exit("no design systems in the registry")
    others = {i: load_entry(i) for i in all_ids()}
    failed = 0
    for ds_id in ids:
        entry = others.get(ds_id) or load_entry(ds_id)
        errors, warns = validate_entry(entry, ds_id, others)
        if args.reseal and not errors:
            for sf in (entry.get("source_files") or []):
                now = sha256_of(os.path.join(os.getcwd(), sf.get("path", "")))
                if now:
                    sf["sha256"] = now
            with open(entry_path(ds_id), "w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)
                f.write("\n")
            warns = [w for w in warns if "source drift" not in w]
            print(f"  resealed source hashes for {ds_id}")
        for w in warns:
            print(f"WARN  {ds_id}: {w}")
        for e in errors:
            print(f"ERROR {ds_id}: {e}")
        print(f"{ds_id}: {len(errors)} errors, {len(warns)} warnings")
        failed += 1 if errors else 0
    if failed:
        sys.exit(1)
    print("VALIDATE PASS")


FIELD_CLASSES = ("map", "edit", "observation", "omit")
# Bookkeeping and prose the look-map does not classify. Mirrors stylespec's own
# META/PROSE split — a rule's id or evidence list is not a paintable field.
_LM_SKIP = {"id", "evidence", "observed_in", "confidence", "variants", "conflict",
            "params_by_source", "fields_by_source", "source", "layer", "resolution",
            "rule", "desc", "description", "note", "notes", "derivation",
            "measured_from", "coverage_note", "one_liner"}


def _lm_leaf_paths(obj, prefix: str = "") -> list[str]:
    """Every leaf field of a rule, as a dotted path. Lists of scalars are ONE
    path (the list is the value); lists of objects recurse per index."""
    out: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _LM_SKIP:
                continue
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                out += _lm_leaf_paths(v, path)
            elif isinstance(v, list):
                if v and all(isinstance(x, (dict, list)) for x in v):
                    for i, x in enumerate(v):
                        out += _lm_leaf_paths(x, f"{path}[{i}]")
                else:
                    out.append(path)          # scalar vector = one field
            else:
                out.append(path)
    return out


def cmd_validate_map(args) -> None:
    """Gate the look-map. Fail-closed in BOTH directions: every look/both rule
    must be present, and every field of those rules must carry exactly one class.
    An unlisted field is an ERROR, never a silent default — an under-covered map
    is the exact failure mode that lets a design system quietly not repaint
    something a human believes it repaints."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import stylespec  # noqa: E402

    slug = args.style
    spec = stylespec.load_spec(slug)
    lm_path = os.path.join(stylespec.style_dir(slug), "look-map.json")
    if not os.path.exists(lm_path):
        sys.exit(f"no look-map at {lm_path} — nothing can paint a pixel without it")
    look_map = json.load(open(lm_path, encoding="utf-8"))
    mapped = look_map.get("rules") or {}

    spec_rules: dict[str, dict] = {}
    for dotted, judgment in stylespec.RULE_GROUPS:
        if not judgment:
            continue
        for r in (stylespec.get_group(spec, dotted) or []):
            if r.get("layer") in ("look", "both") and r.get("id"):
                spec_rules[r["id"]] = r

    errors: list[str] = []
    warns: list[str] = []

    missing = sorted(set(spec_rules) - set(mapped))
    for rid in missing:
        errors.append(f"look/both rule NOT in look-map: {rid} "
                      f"[{spec_rules[rid].get('layer')}]")
    for rid in sorted(set(mapped) - set(spec_rules)):
        errors.append(f"look-map entry for a rule that is not look/both: {rid}")

    roles_hit: set[str] = set()
    n_fields = n_map = 0
    for rid in sorted(set(spec_rules) & set(mapped)):
        rule, ent = spec_rules[rid], mapped[rid]
        if ent.get("layer") != rule.get("layer"):
            errors.append(f"{rid}: look-map says layer={ent.get('layer')}, "
                          f"spec says {rule.get('layer')}")
        fields = ent.get("fields") or {}
        actual = set(_lm_leaf_paths(rule))
        for path in sorted(actual - set(fields)):
            errors.append(f"{rid}: field NOT classified: {path}")
        for path in sorted(set(fields) - actual):
            errors.append(f"{rid}: look-map classifies a field the rule does not "
                          f"have: {path} (silent no-op)")
        for path, f in sorted(fields.items()):
            n_fields += 1
            cls = f.get("class")
            if cls not in FIELD_CLASSES:
                errors.append(f"{rid}.{path}: class {cls!r} not one of {FIELD_CLASSES}")
                continue
            # every classified path must actually resolve — same fail-closed
            # doctrine as stylespec's resolution field-path check
            if path in actual and not stylespec.resolve_field(rule, path):
                errors.append(f"{rid}.{path}: does not resolve (silent no-op)")
            if cls == "map":
                n_map += 1
                targets = f.get("roles") or []
                if not targets:
                    errors.append(f"{rid}.{path}: class=map with no roles")
                for role in targets:
                    if role not in ROLES:
                        errors.append(f"{rid}.{path}: unknown role {role!r}")
                    else:
                        roles_hit.add(role)
            elif cls == "omit" and not f.get("reason"):
                errors.append(f"{rid}.{path}: class=omit requires a reason")

    unreached = sorted(r for r in ROLES if r not in roles_hit)
    for role in unreached:
        if ROLES[role]["req"]:
            warns.append(f"REQUIRED role never reached by any rule: {role} "
                         f"({ROLES[role]['why']})")

    for w in warns:
        print(f"WARN  {slug}: {w}")
    for e in errors:
        print(f"ERROR {slug}: {e}")

    print(f"\n{slug} look-map: {len(mapped)} rules · {n_fields} fields classified "
          f"· {n_map} mapped · {len(roles_hit)}/{len(ROLES)} roles reached")
    if unreached:
        print(f"  roles never reached ({len(unreached)}): "
              + " · ".join(r.split(".", 1)[1] for r in unreached))
    gaps = look_map.get("known_gaps") or {}
    if gaps:
        print(f"  declared gaps ({len(gaps)}): " + " · ".join(sorted(gaps)))
    print(f"{len(errors)} errors, {len(warns)} warnings")
    if errors:
        sys.exit(1)
    print("VALIDATE-MAP PASS")


def _coverage(entry: dict) -> dict:
    """Role census. An enclave's type/geometry/effect are INHERITED from whatever
    base frames it, not missing — counting them as missing reads as a broken
    entry when it is behaving exactly as designed."""
    counts = {"authored": 0, "aliased": 0, "omitted": 0, "missing": 0, "inherited": 0}
    inherits = {b for b in ("type", "geometry")
                if entry.get(f"{b}_policy") == "inherit_base"}
    if entry.get("kind") == "enclave":
        inherits.add("effect")
    for role in ROLES:
        if role.split(".")[0] in inherits:
            counts["inherited"] += 1
            continue
        _, prov = resolve_role(entry, role)
        counts[prov.split(":")[0]] += 1
    return counts


def cmd_list(_args) -> None:
    ids = all_ids()
    if not ids:
        print(f"no design systems in the registry yet ({registry_dir()})")
        return
    for ds_id in ids:
        e = load_entry(ds_id)
        c = _coverage(e)
        drift = ""
        for sf in (e.get("source_files") or []):
            now = sha256_of(os.path.join(os.getcwd(), sf.get("path", "")))
            if now and sf.get("sha256") and now != sf["sha256"]:
                drift = " · DRIFT"
        inh = f" · {c['inherited']:2} inherited" if c["inherited"] else ""
        print(f"  {ds_id:22} {e.get('kind','?'):8} "
              f"{c['authored']:2} authored · {c['aliased']:2} aliased · "
              f"{c['omitted']:2} omitted · {c['missing']:2} missing{inh}{drift}")


def cmd_show(args) -> None:
    entry = load_entry(args.id)
    out = {"id": entry.get("id"), "kind": entry.get("kind"),
           "reference_width_px": entry.get("reference_width_px"), "roles": {}}
    for role in ROLES:
        val, prov = resolve_role(entry, role)
        if val is None:
            out["roles"][role] = {"resolved": None, "provenance": prov}
            continue
        rec = {"resolved": val.get("v"), "provenance": prov, "from": val.get("from")}
        # Expand every length so no consumer ever re-derives the scaling math.
        if args.width and role.endswith("_pct_w") and isinstance(val.get("v"), (int, float)):
            rec["px"] = round(val["v"] * args.width / 100)
        out["roles"][role] = rec
    if args.width:
        out["output_width_px"] = args.width
    print(json.dumps(out, indent=2, ensure_ascii=False))


def cmd_capabilities(args) -> None:
    entry = load_entry(args.id)
    print(f"\n{args.id}  ({entry.get('kind')}, ref {entry.get('reference_width_px')}px, "
          f"{entry.get('name')})\n")
    loud: list[str] = []
    for block in BLOCKS:
        rows = []
        for role in [r for r in ROLES if r.startswith(block + ".")]:
            val, prov = resolve_role(entry, role)
            short = role[len(block) + 1:]
            if prov == "authored":
                rows.append(f"  {short:24} authored  {str(val.get('v'))[:28]:30}"
                            f"{str(val.get('from'))[:40]}")
            elif prov.startswith("aliased"):
                tgt = prov.split(":", 1)[1]
                rows.append(f"  {short:24} ALIASED -> {tgt}")
                loud.append(f"{role} aliased -> {tgt} ({ROLES[role]['why']})")
            elif prov == "omitted":
                rows.append(f"  {short:24} OMITTED   [{ROLES[role]['why']} not drawn]")
            else:
                rows.append(f"  {short:24} MISSING")
        if rows:
            print(block.upper())
            print("\n".join(rows))
            print()
    c = _coverage(entry)
    print(f"  {c['authored']} authored · {c['aliased']} aliased · "
          f"{c['omitted']} omitted · {c['missing']} missing")
    fam_missing = [f["family"] for f in (entry.get("fonts") or [])
                   if not all(os.path.exists(os.path.join(registry_dir(), r))
                              for r in (f.get("files") or ["_"]))]
    print(f"  FONTS   " + ("all vendored" if not fam_missing
                           else "MISSING: " + ", ".join(fam_missing)))
    verdict = "USABLE as a base look." if entry.get("kind") == "base" else \
              "ENCLAVE — paints only what it owns; cannot be a build's look."
    print(f"  VERDICT {verdict}")
    if loud:
        # "10 aliased" is a number a human skims past. "every serif caption role
        # renders sans" is not. Name the visible consequence.
        print("  LOUDEST CONSEQUENCES")
        for line in loud:
            print(f"    · {line}")
    print()


def cmd_fonts(args) -> None:
    entry = load_entry(args.id)
    rows = []
    for f in (entry.get("fonts") or []):
        files = f.get("files") or []
        ok = all(os.path.exists(os.path.join(registry_dir(), r)) for r in files) and files
        rows.append({"family": f.get("family"), "weights": f.get("weights"),
                     "styles": f.get("styles"), "files": files,
                     "status": "vendored" if ok else "MISSING"})
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for r in rows:
            print(f"  {r['family']:22} {r['status']:9} {r['files']}")
    if any(r["status"] == "MISSING" for r in rows):
        sys.exit(1)


def cmd_scaffold(args) -> None:
    """Print a stub entry with candidate vars listed. Writes NOTHING — the CSS
    var -> semantic role mapping is a judgment call and a parser gets it
    confidently wrong (which of --accent-200..700 is accent.primary?)."""
    with open(args.css, encoding="utf-8") as f:
        text = f.read()
    if args.scope:
        i = text.find(args.scope)
        if i < 0:
            sys.exit(f"scope {args.scope!r} not found in {args.css}")
        text = text[i:]
    found = _CSS_VAR.findall(text)
    print(f"# candidates parsed from {args.css}"
          + (f" (scope {args.scope})" if args.scope else ""))
    for name, val in found:
        print(f"#   {name}: {val.strip()}")
    stub = {
        "registry_version": REGISTRY_VERSION, "id": "CHANGEME", "name": "CHANGEME",
        "kind": "base", "reference_width_px": args.ref_width,
        "provenance": f"hand-authored from {args.css}",
        "source_files": [{"path": args.css, "sha256": sha256_of(args.css)}],
        "exclusive_colors": [], "owns_nouns": [],
        "palette": {}, "type": {}, "geometry": {}, "effect": {},
        "fonts": [], "absent": {}, "notes": "",
    }
    for role in ROLES:
        block, _, rest = role.partition(".")
        stub[block][rest] = {"v": None, "from": "MAP ME"}
    print(json.dumps(stub, indent=2, ensure_ascii=False))


def cmd_index(_args) -> None:
    d = registry_dir()
    os.makedirs(d, exist_ok=True)
    rows = []
    for ds_id in all_ids():
        e = load_entry(ds_id)
        c = _coverage(e)
        rows.append({"id": ds_id, "name": e.get("name"), "kind": e.get("kind"),
                     "reference_width_px": e.get("reference_width_px"),
                     "coverage": c})
    p = os.path.join(d, "index.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"registry_version": REGISTRY_VERSION, "systems": rows},
                  f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"indexed {len(rows)} design system(s) -> {p}")


# ---------------------------------------------------------------- main

def main() -> None:
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list"); p.set_defaults(fn=cmd_list)

    p = sub.add_parser("show")
    p.add_argument("id")
    p.add_argument("--width", type=int, help="expand every *_pct_w to a *_px sibling")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("capabilities")
    p.add_argument("id")
    p.set_defaults(fn=cmd_capabilities)

    p = sub.add_parser("validate-map")
    p.add_argument("style", help="style slug (a folder in the style library)")
    p.set_defaults(fn=cmd_validate_map)

    p = sub.add_parser("validate")
    p.add_argument("id", nargs="?")
    p.add_argument("--all", action="store_true")
    p.add_argument("--reseal", action="store_true",
                   help="rewrite source_files[].sha256 after a human confirms the diff")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("fonts")
    p.add_argument("id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_fonts)

    p = sub.add_parser("scaffold")
    p.add_argument("--css", required=True)
    p.add_argument("--scope", help="CSS selector to parse instead of :root")
    p.add_argument("--ref-width", type=int, default=1440)
    p.set_defaults(fn=cmd_scaffold)

    p = sub.add_parser("index"); p.set_defaults(fn=cmd_index)

    args = ap.parse_args()
    if args.cmd == "validate" and not args.all and not args.id:
        ap.error("validate needs an id or --all")
    args.fn(args)


if __name__ == "__main__":
    main()
