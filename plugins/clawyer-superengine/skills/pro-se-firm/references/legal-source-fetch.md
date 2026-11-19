> 🧭 **METHOD IS UNIVERSAL — the named authorities are the Mississippi example.** The process in this file applies in every state. Where it names **Albright / Armstrong / Ferguson**, a **chancery/chancellor** court, **MRCP / UCCR / the MS Rules of Evidence**, or a Mississippi code section (§93-, §43-19-), that is the **Mississippi worked example** — for a non-MS case, apply the **resolved state-law profile** (its factors, its court, its rules; see `state-law-resolver.md`) instead, and never cite these Mississippi authorities in a non-MS case.

# Legal-Source Fetch — verify law verbatim yourself (the WebFetch work-around)

> **Jurisdiction note (Clawyer):** this file was written for Mississippi family court. Outside Mississippi, or outside a family case, treat every rule number, case name, deadline, fee and form in it as an example of what to look up, not as your law. Family-law steps in it do not apply to other kinds of case. Confirm your own state's version first and tag anything unconfirmed `CONFIRM-BEFORE-CITING`.

> **The firm does its own verbatim verification — it does not stop at "the source is blocked."** Built-in web fetching
> (and some statute hosts) often return **HTTP 403/500** to automated requests. A plain browser-style request usually
> gets through. This is how Research Counsel and the Local-Procedure Clerk read statutes, rules, and **local-rule PDFs**
> first-hand instead of guessing or punting to the user. Honors the doctrine "do the lawyer-grade checking yourself."
>
> **Getting the text ≠ confirming it.** Whatever you pull still runs through **citation discipline**: tag it, cite
> section + court/source + date, and confirm the pinpoint against the case's own filed documents before any filing.

## The escalation ladder (try in order, stop when you have verbatim text)
1. **Legal-research tool / MCP** (Descrybe, CourtListener, etc.), if available — best for case law + treatment.
2. **Built-in web fetch / search** — fast; but if it returns 403/500 or only snippets, escalate. (Search snippets are a
   *lead*, not verbatim — don't tag VERIFIED off a snippet.)
3. **`scripts/fetch_law.py <url>`** — the work-around, and the default. It now shells out to **`curl -sL --compressed`
   with a browser User-Agent** (the PROVEN recipe — confirmed 2026-05-29 pulling 212 KB from FindLaw case law and 182 KB
   from FindLaw codes, where WebFetch returned 57 bytes), then falls back to a urllib browser request. The flags that
   matter: **`-L`** (follow redirects — the piece WebFetch and a bare curl miss) and **`--compressed`** (gzip/brotli).
   Strips HTML to text, extracts PDF text, prints UTF-8 safe. Jump to the passage with `--find`:
   ```
   PYTHONUTF8=1 python scripts/fetch_law.py "<official-or-published-code URL>" --find "key phrase"
   ```
   If a host still resists (JS / Cloudflare): Google Scholar (`scholar.google.com`) for opinions, `govinfo.gov` for
   federal CFR/USC, courts.<state>.gov for rule PDFs, or a SeleniumBase undetected-Chrome scraper.
4. **Manual curl** (only to grab the raw file or debug) — same recipe, then run the script on the saved path:
   ```
   curl -sL --compressed -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" -o law.html "<url>"
   PYTHONUTF8=1 python scripts/fetch_law.py law.html --find "key phrase"
   ```
5. **No shell available** (degrade gracefully) — give the user the exact official URL + the phrase to look for, and ask
   them to paste the text back. Never invent the content.

## Access map — what works (confirmed 2026-05-23; re-test, sites change)
| Source | Built-in fetch | Work-around that works |
|---|---|---|
| **Justia** (`law.justia.com`) | **403 blocked** | often still blocked — prefer FindLaw |
| **FindLaw published codes** (`codes.findlaw.com`) | 403 via WebFetch | **`fetch_law.py` (curl -sL --compressed) → HTTP 200** — verbatim state code (confirmed 2026-05-29, 182 KB) |
| **FindLaw case law** (`caselaw.findlaw.com`) | 403 / empty stub via WebFetch | **`fetch_law.py` (curl -sL --compressed) → HTTP 200** — full opinion (confirmed 2026-05-29, 212 KB) |
| **Casemine** (`casemine.com`) | 403 (WebFetch + curl) | **use Google Scholar** (`scholar.google.com`) for the opinion text instead |
| **courts.ms.gov rule PDFs** (UCCR, local chancery rules) | PDF link may 500 / return a stub | **`fetch_law.py` downloads the real PDF** → extract text (confirmed: 736 KB Restyled Rules of Evidence PDF, 2026-05-29) |
| **MRCP** (the `rules_of_civil_procedure.pdf` link) | returns an HTML stub | read MRCP from the **MC Law mirror** `law-db.mc.edu/mlr/rules.php?r=civil` (matches official) |

**Generalize the method, not the URLs:** for any state, the pattern is *official code / court site → if blocked, browser-UA
request → extract → tag*. The MS rows above are the worked example.

## Finding the right official URL (when you don't have it)
- **State statutes:** search the **section number + "FindLaw" or "Justia"** (e.g., `Miss. Code 43-19-101 findlaw`), then
  fetch the FindLaw `codes.findlaw.com/...` result with the script. Cross-check the section number against a second source.
- **Court rules / local rules:** search the court system's official domain (`courts.<state>.gov`) for the rules index;
  local chancery/circuit rules are usually a PDF under a `/rules/` path. Fetch the PDF with the script.
- **Forms (e.g., financial-disclosure):** the official court rule or a district's site usually hosts the current form;
  confirm it's the **current** version before relying on it.

## What "verified" requires after you fetch
1. **Verbatim** — quote the operative words, not a paraphrase.
2. **Pinpoint** — section/subsection (statute) or rule + subpart; case: name, court, year, holding.
3. **Source + date** — the official/published host and the date you read it.
4. **Tag** — `[VERIFIED — <host>, <date>]`. If you only got a snippet or couldn't open it, `[CONFIRM]` / `[UNVERIFIED — DO
   NOT FILE]`. Local rules unread: `[CHECK LOCAL RULE]`.
5. **Log it** — write the verified text + source into the case's verified-rules reference so it isn't re-researched.

**NEXT ACTION:** When any statute, rule, local rule, deadline, fee, or form is needed and the built-in fetch is blocked,
run `scripts/fetch_law.py` on the official/published source, extract the verbatim text, tag it, and log it — then proceed.
Don't report a source as "blocked" without trying this first.
