# Cross-reference guardrails

Relocated verbatim from `SKILL.md` at 0.4.0 so the routing blocks fit inside
the compaction window. The rules are unchanged and still non-negotiable on
every run.

These rules are non-negotiable and must be observed on every run:

**IG list pagination**
Always paginate via `&max_id=<next_cursor>`. Do NOT use `cursor`, `pagination_token`, or `after` ... they silently return page 1 with no error.

**Windows / Python path safety**
- Git-bash `/tmp` is NOT the same as Python's `/tmp` on Windows. Use relative temp paths or pipe via stdin. Never rely on a shared `/tmp`.
- All `open()` calls must use `encoding='utf-8'`.
- Never `print()` non-ASCII strings to the cp1252 Windows console ... it will raise `UnicodeEncodeError`. Write to file instead.

**Credit safety ... balance + cost + confirm**
Before any credit-spending batch (the reel pull, advanced/premium endpoints, a universal search), show the user **live balance + estimated cost + the after-balance**, and get explicit confirmation. Pull the balance with the free `GET /v1/credits/balance` call. Never start a multi-credit operation silently or one that would run the balance dry mid-way. Report `credits_remaining` after big steps so the user always knows where they stand.

**SocialCrawl field constraints**
SocialCrawl drops IG saves and shares. Engagement = views, likes, comments ... only those three fields. **Never fabricate, estimate, or display saves or shares.** If a metric is missing from the API response, omit it from all outputs.

**Caption repair**
Repair latin1-mojibake captions on ingest before any analysis:
```python
caption = raw_caption.encode('latin1').decode('utf-8')
```

**Honest data caveats**
Flag every estimated or non-real number. Estimated reach, synthetic ratios, or inferred values must be labeled as such in every output. Honest data caveats are a feature, not a weakness.

## Non-Goals

- Multi-platform (TikTok, YouTube, etc.)
- Full automation without checkpoints
- SocialCrawl-based transcription (`media/transcript`)
- Generative hook-writing frameworks (BUT/THEREFORE, specificity ladder) ... those belong in the `reel-scripter` format engine, not this analysis skill
