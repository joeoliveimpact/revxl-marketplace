#!/usr/bin/env python3
"""Spell-check a filing (markdown or PDF) before it goes out.

Companion to scrub_check.py. scrub_check catches AI-tell punctuation; this
catches real misspellings while ignoring legal terms and the case's proper
nouns (so it does not cry wolf on party/counsel/judge names pulled from the
case profile, or on Latin terms like "nunc pro tunc").

Usage:
  python spell_check.py <file.md|file.pdf> [case-profile.md]

Exit code 0 = clean. Exit code 1 = possible misspellings found (review them).
Proper nouns are pulled from the case profile when given, so it adapts to any
matter. Pip: pyspellchecker (and pdfminer.six for PDFs).
"""
import sys, re, os

LEGAL = set("""
pro se uccr mrcp nunc tunc gal litem guardian ad chancery harrison mississippi ms
versus plaintiff defendant petitioner respondent esq fka aka pursuant wherefore
decretal hereto herein foregoing whereof affiant comes movant pendente lite
albright armstrong ferguson registry equitable adjudication visitation custody
afterschool co-parenting interlineation recodification subpoena duces tecum voir dire
""".split())

COMMON_TYPOS = ["martial", "micheal", "teh", "adn", "recieve", "seperate",
                "occured", "judgement", "alot", "untill", "wich", "thier",
                "definately", "neccessary", "accomodate", "begining"]


def words_from(path):
    if path.lower().endswith(".pdf"):
        from pdfminer.high_level import extract_text
        return extract_text(path)
    return open(path, encoding="utf-8").read()


def main():
    if len(sys.argv) < 2:
        print("usage: spell_check.py <file> [case-profile.md]"); sys.exit(2)
    path = sys.argv[1]
    text = words_from(path)

    allow = set(LEGAL)
    # pull proper nouns from the case profile if provided or present
    prof = sys.argv[2] if len(sys.argv) > 2 else "case-profile.md"
    if os.path.exists(prof):
        for w in re.findall(r"[A-Za-z][A-Za-z'\-]+", open(prof, encoding="utf-8").read()):
            allow.add(w.lower().strip("'-"))

    from spellchecker import SpellChecker
    spell = SpellChecker()
    raw = re.findall(r"[A-Za-z][A-Za-z'\-]+", text.lower())
    cand = set()
    for w in raw:
        w = w.strip("'-")
        if not w or "-" in w or "'" in w:
            continue            # skip hyphenates/contractions (names, compounds)
        if w in allow:
            continue
        if "@" in text and w in {"gmail", "com", "law"}:
            continue            # email fragments
        cand.add(w)
    unknown = sorted(spell.unknown(cand))

    hard_typos = [t for t in COMMON_TYPOS if re.search(r"\b" + t + r"\b", text, re.I)]

    print(f"=== spell_check: {os.path.basename(path)} ===")
    if hard_typos:
        print("KNOWN TYPOS FOUND:", ", ".join(hard_typos))
    if unknown:
        print("Possible misspellings (review against legal/proper-noun context):")
        for w in unknown:
            print(f"  {w!r} -> {spell.correction(w)!r}")
    if not unknown and not hard_typos:
        print("CLEAN")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
