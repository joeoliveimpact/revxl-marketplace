# 1:1 Enriched Call-History Format (private client channels)

Locked spec for a client's pinned "Call History" post. Validated live on a client 05.28.26. Canonical exemplar: `add-1on1-call-to-history` references a copy of `enriched-history-body.html`.

The history is a **running list** (one entry per call, newest-first) under a Calendly booking header. Adding a call = render ONE entry and **prepend** it; never rebuild or drop existing entries.

## Whole-post structure

```
<p>{Calendly booking header — preserve verbatim from existing post}</p>
<hr>
<p>{entry — newest call}</p>
<hr>
<p>{entry — next}</p>
<hr>
…
<p>{entry — oldest}</p>
```

Leading element is the Calendly header (NO hr above it). Then `<hr>` before every entry. Newest-first.

## Entry format

```
<a target="_blank" href="{fathomShareUrl}" rel="nofollow">⚡ {MonthName} {Day} {Year} - {topic} - </a>{one-line summary} · <a target="_blank" href="{driveUrl}" rel="nofollow">📜 Transcript</a>
```

- Date + topic live **inside** the Fathom share-link anchor (clickable). ⚡ leads.
- `{topic}` = short clause (person/thing or theme). `{one-line summary}` = 1 tight sentence of substance.
- ` · ` middot separates summary from the transcript link.
- Wrap the whole entry in one `<p>…</p>`.

## Rules

- **Going-forward only.** New entries enriched. Do NOT retroactively rewrite a client's old bare entries unless explicitly asked.
- **Preserve per-client format variants.** Some clients' existing entries use split `<a href="placeholder">⚡ </a><a href="real">Date</a>`, some inline `⚡<a>Date</a>`, some `<span class="emoji">⚡</span>`. When *adding* to an existing post, match the dominant existing entry shape if the client already has one; otherwise use the entry format above. (Surgical Execution — don't normalize other entries.)
- **Calendly header** stays pinned at top, preserved verbatim.
- **Dedup:** if the call's date or shareUrl already appears in the post, skip (no duplicate entry).
- **Graceful-missing:** no Drive transcript → drop the ` · 📜 Transcript` segment; keep ⚡ + summary.

## Symbol semantics
| Symbol | Meaning |
|---|---|
| ⚡ | whole-call Fathom link (the entry's date+topic) |
| 📜 | transcript link |
| 📞 | Calendly booking link (header only) |

## HTML escaping
- `&` → `&amp;` (e.g. "Offer &amp; business model").
- Straight quotes/apostrophes. Emojis literal UTF-8 (build via `[Char]::ConvertFromUtf32` in PowerShell — see pipeline.md).

## Safety (mandatory)
Before any UPDATE_POST that rewrites a live client post, **back up the current post content to disk** (`groups posts get … --json` → save). This is the guardrail from a prior destructive-overwrite incident where a destructive overwrite was caught only because a backup existed.
