#!/usr/bin/env python3
"""cite_lookup.py - check that the court cases cited in a draft are real cases, and the ones named.

Why: the most common way a self-represented person gets sanctioned is filing a brief with cases an AI made up.
This is a gate, not a suggestion: it exits 1 unless every case citation it finds was confirmed.

  python cite_lookup.py <draft.md> [--json]
  python cite_lookup.py --text "Miranda v. Arizona, 384 U.S. 436 (1966)"
  python cite_lookup.py --selftest          (no network)

How it checks: each "volume reporter page" citation (384 U.S. 436, 437 So. 2d 1003) is looked up on
CourtListener's public citation page, courtlistener.com/c/<reporter>/<volume>/<page>/, which needs no
account. Only the reporter, volume and page are sent. A real citation lands on the opinion's page; a made-up
one returns "not found". The case name written beside the citation is then compared with the case found.

Results per citation:
  FOUND        a case exists at that citation and its name matches the name in the draft
  MISMATCH     a case exists there, but it is a different case from the one the draft names
  NO_NAME      a case exists there, but the draft gives no case name beside the citation to compare,
               so it cannot be confirmed as the one meant. Add the name, or confirm it by hand.
  AMBIGUOUS    more than one case sits at that citation; a person must pick
  NOT_FOUND    no case at that citation (or a reporter CourtListener does not know)
  CANNOT_CHECK a Westlaw, Lexis or slip-opinion citation. This tool cannot look those up; a person must
               open the opinion.
  UNCHECKED    the lookup could not be completed (offline, blocked, rate limit)
Only FOUND counts as confirmed. Every other result fails the check.

Limits, stated plainly: it confirms a case EXISTS and is the one named. It does not confirm the case says
what the draft claims (read the opinion for that), that it is still good law, or anything about statutes,
rules and regulations. Short forms ("384 U.S. at 444", "Id.") are skipped: they point back at a case that
was already cited in full. Standard library only.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://www.courtlistener.com/c/"
UA = "citation-check/0.1 (self-represented litigant tool)"
MAX_CITES = 60          # lookups per run; keeps a draft polite to a free public service and bounded
PAUSE = 1.0             # seconds between lookups, for the same reason
# volume, reporter (must contain a period, e.g. "U.S.", "F.3d", "So. 2d", "N.Y.S.2d"), first page
CITE_RX = re.compile(r"\b(\d{1,4})\s+((?:[A-Z][A-Za-z]*\.\s?)+(?:\d?[a-z]{1,2}\b)?(?:\s?\d[a-z]{1,2}\b)?)\s+(\d{1,5})\b")
SHORT_RX = re.compile(r"\b\d{1,4}\s+(?:[A-Z][A-Za-z]*\.\s?)+(?:\d?[a-z]{1,2}\s)?(?:\d[a-z]{1,2}\s)?at\s+\d")   # "384 U.S. at 444"
DB_RX = re.compile(r"\b\d{4}\s+(?:WL|U\.S\.\s+(?:Dist\.\s+|App\.\s+)?LEXIS|[A-Z][A-Za-z.]*\s+LEXIS)\s+\d+")
SIGNALS = {"see", "also", "but", "cf", "accord", "compare", "and", "e.g", "in", "under", "citing", "quoting", "with",
           "later", "generally", "contra", "then", "as", "per", "following"}
STOP = {"the", "and", "of", "for", "inc", "llc", "corp", "company", "state", "united", "states", "people", "city",
        "county", "department", "board", "commission", "matter", "estate", "ex", "rel", "in", "re", "lines", "co",
        "ltd", "group", "services", "national", "american"}
VS_RX = re.compile(r"\sv\.?\s")
INRE_RX = re.compile(r"\b(?:In re|In the Matter of|Ex parte|Matter of)\s+([A-Z][^,;()]{1,60})\s*,?\s*$")


def name_before(before):
    """The case name written just before a citation, or ''. Handles commas inside party names (", Inc.")."""
    b = before.replace("\n", " ").rstrip()
    b = re.sub(r",?\s*$", "", b)
    m = INRE_RX.search(b)
    hits = list(VS_RX.finditer(b))
    if hits:
        v = hits[-1]
        right = b[v.end():]
        inner = CITE_RX.search(right)
        if inner:                            # "Miranda v. Arizona, 384 U.S. 436" before a parallel cite: keep the name only
            # ...but if more text follows that earlier cite, the name belongs to it, not to this citation
            right = right[:inner.start()] if not right[inner.end():].strip(" ,;") else ""
        right = right.strip(" ,")
        if 0 < len(right) <= 90 and right[0].isupper() and not re.search(r"[;:(]", right):
            lw = b[:v.start()].split()
            left = []
            for w in reversed(lw):           # walk back over the plaintiff's words; stop at a sentence break
                if (len(left) >= 6 or re.search(r"[\d()]", w)
                        or (re.search(r"[.;:!?,]$", w) and not re.fullmatch(r"(?:[A-Z]\.)+|[A-Z][a-z]{0,4}\.", w))):
                    break
                left.append(w)
            left = list(reversed(left))
            while left and left[0].rstrip(".,:").lower() in SIGNALS:
                left.pop(0)
            if left and left[0][0].isupper():
                return f"{' '.join(left)} v. {right}"
    if m:
        return "In re " + m.group(1).strip()
    return ""


def find_citations(text):
    """Return ([{cite, volume, reporter, page, name}], [database cites]). Each cite+name pairing is kept, so a
    second mention with a different name is checked too."""
    shorts = [m.span() for m in SHORT_RX.finditer(text)]
    out, seen, prev = [], set(), None
    for m in CITE_RX.finditer(text):
        if any(s <= m.start() < e for s, e in shorts):
            continue                           # short form: points back at a full citation
        vol, rep, page = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip(), m.group(3)
        name = name_before(text[max(0, m.start() - 220):m.start()])
        if not name and prev and re.fullmatch(r"\s*[,;]\s*", text[prev["end"]:m.start()]):
            name = prev["name"]                # parallel citation: "384 U.S. 436, 86 S. Ct. 1602"
        c = {"cite": f"{vol} {rep} {page}", "volume": vol, "reporter": rep, "page": page, "name": name, "end": m.end()}
        prev = c
        key = (vol, rep.replace(" ", "").lower(), page, name.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out, sorted({m.group(0) for m in DB_RX.finditer(text)})


def words(s):
    return {w for w in re.findall(r"[a-z]{3,}", s.lower()) if w not in STOP}


def classify(status, final_url, cited_name):
    """Pure decision from what the lookup returned. Kept separate so the selftest needs no network."""
    path = urllib.parse.urlparse(final_url).path
    if status == 404:
        return "NOT_FOUND", ""
    if "/opinion/" in path:
        found = path.rstrip("/").split("/")[-1].replace("-", " ")
        if not cited_name:
            return "NO_NAME", found            # existence alone is not confirmation: any real page number would pass
        if not (words(cited_name) & words(found)):
            return "MISMATCH", found
        return "FOUND", found
    if path.startswith("/c/") and status in (200, 202, 300):
        return "AMBIGUOUS", ""
    return "UNCHECKED", f"unexpected reply {status}"


def fetch(c):
    url = BASE + "/".join(urllib.parse.quote(x, safe="") for x in (c["reporter"], c["volume"], c["page"])) + "/"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.geturl(), ""
    except urllib.error.HTTPError as e:
        return (404, url, "") if e.code == 404 else (0, url, f"HTTP {e.code}")
    except Exception as e:  # offline, DNS, timeout: report it, never guess
        return 0, url, type(e).__name__


def run(text, as_json=False):
    cites, dbs = find_citations(text)
    rows, cache, lookups = [], {}, 0
    for c in cites:
        key = (c["volume"], c["reporter"], c["page"])
        if key not in cache:
            if lookups >= MAX_CITES:
                rows.append({**c, "result": "UNCHECKED", "found_name": "", "note": f"past the {MAX_CITES}-lookup limit; run again on the rest", "url": ""})
                continue
            if lookups:
                time.sleep(PAUSE)
            cache[key] = fetch(c)
            lookups += 1
        status, url, err = cache[key]
        result, detail = ("UNCHECKED", err) if err else classify(status, url, c["name"])
        rows.append({**c, "result": result, "found_name": detail if result in ("FOUND", "MISMATCH", "NO_NAME") else "",
                     "note": detail if result == "UNCHECKED" else "", "url": url})
    for d in dbs:
        rows.append({"cite": d, "name": "", "result": "CANNOT_CHECK", "found_name": "", "url": "",
                     "note": "Westlaw or Lexis citation: this tool cannot look it up. A person must open the opinion."})
    for r in rows:
        r.pop("end", None)
    bad = [r for r in rows if r["result"] != "FOUND"]
    if as_json:
        print(json.dumps({"checked": len(rows), "not_confirmed": len(bad), "citations": rows}, indent=2))
    else:
        for r in rows:
            extra = {"FOUND": r["found_name"], "MISMATCH": f"that citation is: {r['found_name']}",
                     "NO_NAME": f"a case is there ({r['found_name']}), but the draft names no case beside it",
                     "UNCHECKED": r["note"], "CANNOT_CHECK": r["note"]}.get(r["result"], "")
            print(f"{r['result']:<12} {r['cite']:<22} {r['name'] or '(no case name beside it)'}  {extra}")
        if not rows:
            print("NO CASE CITATIONS FOUND in this text. Statutes and rules are not checked by this tool.")
        print(f"CITE CHECK: {'PASS' if not bad else 'FAIL'} ({len(rows) - len(bad)} confirmed, {len(bad)} not confirmed)")
    return 0 if not bad else 1


def selftest():
    t = ("A suspect must be warned. See Miranda v. Arizona, 384 U.S. 436, 86 S. Ct. 1602 (1966). Also Albright v. "
         "Albright, 437 So. 2d 1003 (Miss. 1983), and Smith v. Jones, 123 F.3d 456 (5th Cir. 1997). He lives at 12 "
         "Main Street 400. Miranda, 384 U.S. at 444. Then Henderson v. Coastal Freight Lines, Inc., 512 So. 2d 1234 "
         "(Miss. 1987). Later: Henderson v. Coastal Freight, 384 U.S. 436 (1966). See 2030 WL 1234567. "
         "In re Gault, 387 U.S. 1 (1967). Venue is under 28 U.S.C. § 1332 and M.R.C.P. 4.")
    c, dbs = find_citations(t)
    got = [(x["cite"], x["name"]) for x in c]
    assert got == [("384 U.S. 436", "Miranda v. Arizona"),
                   ("86 S. Ct. 1602", "Miranda v. Arizona"),                      # parallel cite inherits the name
                   ("437 So. 2d 1003", "Albright v. Albright"),
                   ("123 F.3d 456", "Smith v. Jones"),
                   ("512 So. 2d 1234", "Henderson v. Coastal Freight Lines, Inc."),  # comma inside a party name
                   ("384 U.S. 436", "Henderson v. Coastal Freight"),              # same cite, different name: checked again
                   ("387 U.S. 1", "In re Gault")], got                             # short form and statutes skipped
    assert dbs == ["2030 WL 1234567"], dbs
    op = "https://www.courtlistener.com/opinion/107252/miranda-v-arizona/"
    assert classify(202, op, "Miranda v. Arizona") == ("FOUND", "miranda v arizona")
    assert classify(202, op, "Henderson v. Coastal Freight")[0] == "MISMATCH"    # real citation, invented case
    assert classify(202, "https://www.courtlistener.com/opinion/1/page-v-gafford/",
                    "Henderson v. Coastal Freight Lines, Inc.")[0] == "MISMATCH"
    assert classify(202, op, "")[0] == "NO_NAME"                                 # existence alone never passes
    assert classify(404, "https://www.courtlistener.com/c/us/999/9999/", "Fake v. Case")[0] == "NOT_FOUND"
    assert classify(200, "https://www.courtlistener.com/c/us/1/1/", "A v. B")[0] == "AMBIGUOUS"
    assert classify(503, "https://www.courtlistener.com/", "A v. B")[0] == "UNCHECKED"
    print("SELFTEST OK")
    return 0


def main():
    a = sys.argv[1:]
    if "--selftest" in a:
        return selftest()
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]
    if len(a) == 2 and a[0] == "--text":
        return run(a[1], as_json)
    if len(a) != 1:
        print(__doc__)
        return 2
    try:
        text = open(a[0], encoding="utf-8", errors="replace").read()
    except OSError as e:
        print(f"CITE CHECK: FAIL, could not read the file ({e.strerror}). Nothing was checked.")
        return 1
    return run(text, as_json)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
