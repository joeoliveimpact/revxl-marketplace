# Task — refresh (delta update)

Runs when a brain exists but is >7 days old (or the user asks). Cheap by design: only what's NEW since the last stamp.

## 1. Read the index
`voc/index.md` → per-bucket last-pull timestamps. Compute the delta window per source.

## 2. Pull only the delta
- Recordings connector: calls since last stamp, same buckets.
- Tier-B sources: new posts/newsletters/DM threads since stamp.
- Show the user the count first: *"~N new calls since your last update — folding them in keeps the copy matching how your prospects talk right now. ~1-3 min. Want me to?"* Decline → keep existing brain, increment decline count in the index, stop.
- Large backlog (30+ days of declines piled up): offer "top-patterns quick pass" vs "full re-rank," with an honest time estimate from the count.

## 3. Incremental merge
- Append new material to buckets; re-rank the VoC bank incrementally (do NOT re-mine the whole corpus).
- New humor candidates → score + queue for canonization (${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/signature-bits.md).
- Voice guide: refresh roughly every couple of updates, or immediately if the register mix changed (e.g. first spoken source just arrived → confidence jumps to A).
- **Rebuild weekly-content-bank from THIS delta:** expire entries >7 days old, write this week's themes/objections/questions/topical jokes/seeds.

## 4. Re-stamp + report
Update `updated_at` on every touched artifact + the index. One-line report: what came in, what aged out, new bit candidates awaiting thumbs-up.
