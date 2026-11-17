"""Mask and draft-note checker (derived from vault-note-builder's read_source.py `mask` and `check`;
the box-specific source readers were dropped, the source kinds come from config).

mask(text): secrets, keys, long opaque ids, emails, phone numbers -> [KEY] [MASKED] [LONG-ID] [EMAIL] [PHONE].
check(note, name, ref_rx, status, schema): every reason the note fails; empty list = OK.
"""
import re

MASKS = [
    (re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_\-]{12,}|\bgh[po]_[A-Za-z0-9]{12,}|\bxox[abp]-[A-Za-z0-9\-]{10,}"
                r"|\bAKIA[A-Z0-9]{12,}|\bAIza[A-Za-z0-9_\-]{20,}|\beyJ[\w\-]+\.[\w\-]+\.[\w\-]+"), "[KEY]"),
    (re.compile(r"(?i)\b(password|passwd|pwd|passcode|pin|token|secret|api[_ -]?key|cookie|lockbox(?: code)?|"
                r"door code|gate code|combo|combination)\b(\s+(?:is|for\s+\S+))?\s*[:=]?\s+(?=\S*\d)\S+"), r"\1 [MASKED]"),
    (re.compile(r"(?i)\b(password|passwd|passcode|token|secret|api[_ -]?key|cookie)(\s+is|\s*[:=])\s*\S+"), r"\1: [MASKED]"),
    # Opaque tokens: 24+ chars, no hyphen, with a digit and a letter. Kebab names and UUIDs survive.
    (re.compile(r"\b(?=[A-Za-z0-9_]*\d)(?=[A-Za-z0-9_]*[A-Za-z])[A-Za-z0-9_]{24,}\b"), "[LONG-ID]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EMAIL]"),
    (re.compile(r"(?<!\d)(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)"), "[PHONE]"),
]
REQUIRED = ["title", "id", "aliases", "type", "status", "sot_policy", "applies_to", "sources",
            "source_date", "last_verified", "confidence", "tags"]
SOT = {"strict", "blended", "decay"}
STREET = re.compile(r"\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|"
                    r"Ln|Lane|Pl|Place|Ct|Court|Blvd|Way|Ter|Terrace|Pkwy)\b")
BODY_RULES = [
    ("masked text", re.compile(r"\[(KEY|MASKED|LONG-ID|EMAIL|PHONE|ADDRESS|NUMBER|CARD|SSN)\]")),
    ("key-shaped value", MASKS[0][0]),
    ("credential phrase", MASKS[1][0]),
    ("credential phrase", MASKS[2][0]),
    ("opaque token", MASKS[3][0]),
    ("email", MASKS[4][0]),
    ("phone", MASKS[5][0]),
    ("6+ digit number", re.compile(r"(?<!\d)\d{6,}(?!\d)")),
    ("street address", STREET),
]
ID_RX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CLAIM_RX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")   # any list item: -, *, + or 1. / 1)


def mask(text):
    for rx, rep in MASKS:
        text = rx.sub(rep, text)
    return text


def ref_rx(kinds=None):
    """Source refs: <kind>:<id>@<date>. kinds=None accepts any lowercase kind (promote reads older stagings)."""
    k = "|".join(re.escape(x) for x in kinds) if kinds else r"[a-z][a-z0-9-]*"
    return re.compile(rf"\b(?:{k}):[^\s,\])]+@[^\s,\])]+")


def split_note(text):
    m = re.match(r"\A---\n(.*?)\n---\n?(.*)\Z", text.replace("\r\n", "\n"), re.S)
    if not m:
        return None, text
    fm, key = {}, None
    for line in m.group(1).split("\n"):
        k = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if k:
            key = k.group(1)
            fm[key] = k.group(2).strip()
        elif key and line.strip().startswith("- "):
            fm[key] = (fm[key] + " " + line.strip()[2:]).strip()
    return fm, m.group(2)


def list_items(v):
    v = v.strip().strip("[]")
    return [x.strip().strip("'\"") for x in re.split(r",\s*|\s+(?=\S+:\S+@)", v) if x.strip()]


def set_field(note, key, value):
    """Sets one frontmatter field (adds it at the end of the frontmatter when missing)."""
    fm_end = note.find("\n---", 4)
    head, rest = note[:fm_end], note[fm_end:]
    if re.search(rf"^{re.escape(key)}:", head, re.M):
        head = re.sub(rf"^{re.escape(key)}:.*$", lambda _: f"{key}: {value}", head, count=1, flags=re.M)
    else:
        head += f"\n{key}: {value}"
    return head + rest


def check(note, name, refs, status="draft", schema=None):
    """Every reason the note fails; [] = OK. refs = ref_rx(...). schema = harvest.schema (types, applies_to)."""
    fm, body = split_note(note)
    if fm is None:
        return ["frontmatter: missing or malformed"]
    fails = [f"missing field: {k}" for k in REQUIRED if k not in fm]
    if not ID_RX.match(name) or len(name) > 60:
        fails.append(f"bad id {name[:40]!r}")
    if fm.get("id", "").strip("'\"") != name:
        fails.append(f"id '{fm.get('id')}' does not match the file name '{name}'")
    if re.search(r"[\[,]", fm.get("applies_to", "")):
        fails.append("applies_to must be a single value")
    if fm.get("status") != status:
        fails.append(f"status must be {status} (is '{fm.get('status')}')")
    for k in ("source_date", "last_verified"):
        if k in fm and not re.fullmatch(r"['\"]?\d{4}-\d{2}-\d{2}['\"]?", fm[k]):
            fails.append(f"{k} must be YYYY-MM-DD")
    srcs = list_items(fm.get("sources", ""))
    if not srcs:
        fails.append("no sources")
    fails += [f"source not in ref format: {s[:60]}" for s in srcs if not refs.fullmatch(s)]
    if schema:
        if fm.get("type") not in schema["types"]:
            fails.append(f"type {fm.get('type')!r}")
        if fm.get("applies_to") not in schema["applies_to"]:
            fails.append(f"applies_to {fm.get('applies_to')!r}")
    if fm.get("sot_policy") not in SOT:
        fails.append(f"sot_policy {fm.get('sot_policy')!r}")
    scan = [("title", fm.get("title", "")), ("tags", fm.get("tags", "")), ("aliases", fm.get("aliases", ""))]
    in_conflict = False
    for i, line in enumerate(body.split("\n"), 1):
        in_conflict = line.startswith("> [!conflict]") or (in_conflict and line.startswith(">"))
        scan.append((f"body:{i}", line))
        if line.rstrip().endswith("?") and not in_conflict:
            fails.append(f"body:{i}: question copied into note")
    for where, text in scan:
        text = refs.sub("", text)  # exact source refs are allowed anywhere
        for rname, rx in BODY_RULES:
            mm = rx.search(text)
            if mm:
                fails.append(f"{where}: {rname}: ...{mask(mm.group(0))[:30]}...")
    return fails
