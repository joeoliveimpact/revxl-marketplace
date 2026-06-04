# Deep Post Format — "Full Call Notes" (group channel)

Locked spec for the Full Call Notes deep post. Validated across 21 live posts (05.28.26). Canonical exemplar: `create-fathom-deep-post` references a copy of `may-4-deep-post-body.html`.

This is an **editorial** transformation, not a mechanical one. Claude renders it in-context using this spec + the exemplar. There is no converter script.

## Title

```
📝 Full Call Notes — {MonthName} {Day} {Year} ({Time}) - {DayOfWeek} Office Hours - {topic distillation}
```

- `📝` literal, then ` Full Call Notes ` then em-dash `—` (U+2014).
- `{Time}` like `12pm EST` (group-call time slot — see pipeline.md time-slot table). For 1:1-style deep posts, drop the "Office Hours" segment and use `{Client} & the operator` instead.
- `{topic distillation}` = one short clause, person+thing style. Examples: "Aaron's AI content agent + business application", "Claude memory model + Ryan's value ladder strategy". Keep under ~80 chars.

## Body structure (in order)

```
<hr>                                              ← leading hr (required)
<p>⚡ <strong>Watch:</strong> <a target="_blank" href="{fathomShareUrl}" rel="nofollow">Open recording in Fathom</a></p>
<p>⚡ <strong>Transcript:</strong> <a target="_blank" href="{driveUrl}" rel="nofollow">📜 Open in Drive</a></p>
<hr>
<p><strong>Meeting Purpose</strong></p>
<p><a target="_blank" href="{ts-link}" rel="nofollow">{purpose sentence}</a></p>      ← NO ▶️ (it's a sentence)
<hr>
<p><strong>Key Takeaways</strong></p>
<p>▶️ <a ... href="{ts}">…<strong>{bold lead if present}:</strong> {takeaway}</a><br>▶️ …</p>
<hr>
<p><strong>Topics</strong></p>
<p><strong>{Topic 1 name}</strong><br>▶️ <a ...>…</a><br>▶️ …</p>     ← first topic: NO leading hr (the Topics hr precedes it)
<hr>
<p><strong>{Topic 2 name}</strong><br>▶️ …</p>
<hr>
… (one hr before each subsequent topic) …
<hr>
<p><strong>Next Steps</strong></p>
<p>▶️ <a ...><strong>{Person}:</strong> {action}</a><br>▶️ …</p>
```

### `<hr>` rule (locked 05.28)
Leading `<hr>` at very top, then `<hr>` before each section heading (Meeting Purpose / Key Takeaways / Topics / Next Steps) AND before each Topic sub-group **except the first** (which immediately follows the `Topics` heading). Total = 1 (leading) + 4 (sections) + (N_topics − 1).

## Conversion rules (Fathom summary markdown → this HTML)

- `## Header` → `<p><strong>Header</strong></p>`
- `### Subheader` (a Topic) → `<p><strong>Subheader</strong><br>` then bullets follow via `<br>`, close `</p>` at topic end
- `- [text](url)` → `▶️ <a target="_blank" href="url" rel="nofollow">text</a><br>` (▶️ = clip/timestamp link)
- Meeting Purpose line → anchored sentence, **no ▶️**
- **Nested sub-bullets (4-space indent)** → flatten into the parent bullet's line, anchored at the parent's timestamp. Tighten/paraphrase for concision — drop redundant "for X" phrases the topic already implies. See the "Key Capabilities" / "Solution:" lines in the exemplar for the canonical flatten.
  - **Join character:** use ` / ` when the sub-items are short parallel list items (pricing tiers, tool/notebook names, enumerated steps); use `. ` or `; ` when they are full clauses/sentences. When unsure, match the exemplar's feel.
- **Next Steps with sub-bullets:** the same flatten rule applies. If one person has multiple sub-actions, keep them in one ▶️ bullet under `<strong>{Person}:</strong>` and join the actions with `; `.
- Topic names: shorten if verbose ("Technical Details" → "Technical", "Onboarding Improvement" → "Onboarding skill").
- `**bold**` markdown → `<strong>bold</strong>`. Bold the lead phrase of a bullet when the source has one (`**Plan:**`, `**Problem:**`).

## Symbol semantics (locked)
| Symbol | Meaning |
|---|---|
| ⚡ | whole-call link (Watch line) |
| ▶️ | clip / specific-timestamp link (bullets) |
| 📜 | transcript link |
| 📝 | "Full Call Notes" deep-post title prefix |

## HTML escaping
- `&` → `&amp;` everywhere in body (incl. inside Fathom timestamp URLs: `?tab=summary&amp;timestamp=N`).
- Keep straight apostrophes `'` and straight quotes `"` (no curly).
- Emojis are literal UTF-8 in the body file. When building in PowerShell, construct via `[Char]::ConvertFromUtf32(...)` — see pipeline.md traps.

## Graceful-missing
- No Drive transcript found → omit the entire Transcript header line (keep the Watch line + leading hr).
