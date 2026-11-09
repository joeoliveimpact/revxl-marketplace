# Five optional visual questions

Ask each question exactly once after watching the finished reel. Each answer must be `yes` or `no`.
Claude answers these itself from the finished reel's frames; to the client, say only a fix, in plain words. These are taste prompts, not permission to bypass QA.

| id | Question |
| --- | --- |
| poster | Could the strongest frame communicate its idea as a standalone still? |
| confident | Is the caption large and deliberately placed enough to read comfortably? |
| hierarchy | At thumbnail size, is the first thing to notice immediately clear? |
| handshake | Does the type respond to the footage in at least two visible ways, such as alignment and timing? |
| rests | Do the quiet moments feel deliberately composed? |

Save answers in `work/eye-test.json`:

```json
{"answers":[
  {"id":"poster","answer":"yes"},
  {"id":"confident","answer":"yes"},
  {"id":"hierarchy","answer":"no","at":2.4,"fix":"Reduce the competing label."},
  {"id":"handshake","answer":"yes"},
  {"id":"rests","answer":"yes"}
]}
```

The post check warns about every missing or duplicate id, a `no`, an invalid
answer, or an unknown id. It never blocks. Without this file it emits no rows.
Use the named fix as a proposal, then review the changed reel again.

## Optional planning choices

The Beat Map's optional `cta_reminder` records `{at_s, hold_s, gain, keyword}`
in `beat-map-selection.json`. The keyword has at most 16 characters. Times
are output seconds; gain is linear, with 0 silent and 0.10 the maximum. Place
the reminder around 60-80% of the runtime and keep its complete interval away
from any end-card beat or `cta` word mark. Overlap and excessive gain block;
timing outside the recommended window warns. The `cta-reminder` scene is a
silent corner overlay with a `keyword` slot. Placement still needs a deliberate
Beat Map choice; the controls check the proposal and do not insert a beat.
For older reels, `cta-reminder.json` in the reel folder is checked only when
the document has no `cta_reminder` key.

The Beat Map saves `holds: [{"at_f":90,"reason":"Let this comparison settle."}]`
in `beat-map-selection.json`. Reasons in an older `work/holds.json` with the
same `holds` list also count; the check uses both sources together.
A reason must have text and a frame inside the gap it explains. Cut starts,
beat starts/ends and the reel endpoints are visual events. A gap over 2.2 seconds
without a reason warns; it never changes the cut.

Use the Sketches board's "How each beat comes in and goes out (optional)" panel normally;
it saves the `storyboard` key in `sketches-selection.json`. The old way is `storyboard.json`, recording `{"beats":{"b_001":{"in":"fade","out":"slide",
"ease_in":"soft","ease_out":"soft"}}}`. In Beat Map order, an exit transform
that differs from the next entry produces one suggestion warning per boundary.
The saved key takes priority over the old file. Without either there are no rows. These choices do not animate anything.

For style origin and colour meanings, use the shared `style_intake.py` command:
`save <id> <document.json>` or `read <id>`. Its document has `origin` of `client`,
`reference` or `default`, and `colours` with `{hex, meaning}`. The sibling
`styles/<id>.intake.json` lives in editor state. More than five colours prompts
which to drop while keeping them all. This does not alter the saved style.
