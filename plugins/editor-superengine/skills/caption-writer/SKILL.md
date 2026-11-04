---
name: editor-superengine:caption-writer
description: Writes or audits the Instagram caption for a finished reel, built for search. Use on "write the caption", "caption this reel", "is my caption optimized", "what should the caption say", "fix my caption", "give me hook lines for the caption", "alt text for this reel", or "which hashtags". It lands real search keywords in the first two sentences, writes hook-line options, the body, alt text, emoji and hashtag picks, and checks every number, bold word and the call to action against the reel before the client sees it. NOT for scripting a reel from scratch, and NOT for the burned-in captions on the video itself.
---

# caption-writer: the caption under a finished reel

## Output contract (every run, in this order)

**Write mode**
1. Two hook-line options (the first line, the only part people see before "...more"), each scored 1-10 on: curiosity, keyword placement, and a fresh angle on the reel's spoken hook. Rewrite any option with any of its three scores under 8. Mark the ~55-character cut when that option is on.
2. The body, in the client's voice.
3. Alt text (a short picture description for screen readers and search).
4. The emoji and hashtag picks, only for those options the client turned on.
5. Every fill-in left in the caption, in plain words: "Add your real client count where it says [your number]."
6. "Saved as a draft with this reel. The final words are yours to lock."

**Audit mode** ("is this caption optimized?")
1. The checklist below, one line each: done, or what's missing.
2. Suggested fixes, shown as suggestions. Never overwrite the client's wording.

Speak to the client the way `${CLAUDE_PLUGIN_ROOT}/skills/editor-start-here/references/what-the-coach-hears.md` says: no file names, paths, script names or raw check output.

## Re-invoke guard

- If the conversation was compacted since this skill loaded, invoke it again before going on.
- Re-running is safe. It rewrites the draft only, never wording the client has locked.
- If the client has locked a caption, this run is audit mode, whatever they asked.

## Ground rules

- **The client never types a command.** Claude runs every command with the Bash tool, from the client's workspace folder.
- `<editor python>` is the editor's own Python. Windows: `"$LOCALAPPDATA/revxl/editor-superengine/venv/Scripts/python.exe"`. macOS: `"$HOME/Library/Application Support/revxl/editor-superengine/venv/bin/python"`. If it doesn't exist, run `editor-superengine:editor-doctor` first.

## Hard rules (correctness, always on)

1. **Never invent numbers or proof.** Every number, result, testimonial, client outcome or claim must be in the reel's transcript or in what the client supplied. Anything else becomes a marked fill-in like `[your number]`, never a guess.
2. **Emphasis is the smallest truthful run of words.** A bolded, capitalised or punched span keeps its negation, condition, unit and both sides of a contrast: **doesn't work**, never **work** alone. Full rule: `${CLAUDE_PLUGIN_ROOT}/skills/caption-writer/references/emphasis-span.md`.
3. **The CTA and the deliverable's name match the reel word for word.** If the reel says "Comment HOOKS for the Hook Guide", the caption says exactly that. A mismatch breaks the comment-to-DM funnel (the automation that sends the freebie when someone comments the word).
4. **Load every URL before it ships.** A link that doesn't open is removed or flagged.
5. **Never overwrite wording the client has locked.** Audit and suggest only.

## Options (the client turns these on)

Ask once, in one question, which of these the client wants, with the one-line why. Follow their own brand files where those already say. An option the client hasn't turned on isn't applied and isn't mentioned: no emoji at all when the emoji option is off, no length steering when the length option is off.

- **Use the speaker's own words** (strong suggestion): lift phrases from the transcript. It sounds like them and keeps claims honest.
- **Hook-to-CTA shape** for the body: hook line, value, a personal line, one question, the CTA.
- **No em or en dashes** (style): periods, commas and line breaks instead.
- **~55-character cut-off:** end the visible first line mid-thought, so "...more" gets tapped. Mark where the cut lands.
- **Length bands:** under about 300 characters (the CTA rides on the video) or over about 1,000 (the caption stands as value alone). Skip 301-600, where weak reels cluster. Never pad to reach a band.
- **One 👇 at the end of the CTA**, and no other emoji.
- **Hashtags:** 3-5 specific niche tags, or none.
- **Keyword count:** 2-3 keywords, each used naturally 2-3 times. Only the count is optional: the main keyword by the end of sentence 2, and every keyword inside a sentence, is the method and always applies.

## Inputs

1. **The finished reel's transcript** (from reel-first-cuts' final check if the editor cut it) and its **on-screen text**.
2. **The CTA**: the comment word and the deliverable's exact name.
3. **Search terms:** the main one, or 2-3 with the keyword-count option on. Harvest real phrases: type the broad topic into Instagram or TikTok search (or a search-suggestion site) and read the autocompletes back. Those are strings people really type. Don't invent them.
4. **Brand voice and stored keywords:** read the client's own files if they have any (ask where, don't assume a path). Voice sets tone, not substance; substance comes from the reel and what the client says.

## The method

**Instagram works as a search engine now.** The caption is where search words count most, ahead of on-screen text and then audio (spoken words and the song).

**Keyword in the first two sentences (always).** The main keyword lands by the end of sentence 2, in the words the audience already searches, and every keyword sits inside a sentence. Sentence 1 may be the CTA instead. How many keywords, and how often, is the keyword-count option. In the study (`${CLAUDE_PLUGIN_ROOT}/skills/caption-writer/references/caption-evidence.md`), a keyword by sentence 2 separated outlier reels more than opening with the CTA, and the gain stopped at sentence 2.

**Three kinds of word, three jobs.** They compete for the same opening, so know which you are placing.

| | example | job |
|---|---|---|
| Trigger word | `GUIDE`, `HOOKS` | fires the comment-to-DM automation; easy to type, unique |
| Topic keyword | `instagram hooks`, `meal prep` | earns search reach |
| Audience qualifier | `coaches`, `new moms` | tells the right person it's for them |

- A trigger word has no search value. Strip it before judging keyword coverage, even when it's the same word as a keyword.
- Keywords earn reach, qualifiers earn lead quality. Keywords in sentences 1-2, qualifiers in 3-4. A bare generic word (like `ai` in its niche) measured worse than none.
- Pick specific, searched terms, not more terms. Outliers used no more words, just better ones.

**No keyword block at the bottom.** A tail of comma-separated keywords, YouTube-tags style, reads as keyword stuffing to Instagram. Keywords go in sentences, never in a block.

## Writing it

**A. Hook line.** Two options. The main keyword lands by sentence 2 at the latest; an option that reaches sentence 3 without it scores 0 on placement. It complements the reel's spoken hook, a second angle, never a repeat.

**B. Body.** Real substance from the reel, in the client's voice. One CTA, never "comment AND DM AND save".

**C. Alt text.** 100-125 characters, one keyword, describes what's on screen. No stuffing.

**D. Emoji (only with the emoji option on).** Emoji don't lift reach (65% of outlier captions had none). The one placement with a measured edge is 👇 at the end of the CTA.

**E. Hashtags (only with the hashtag option on).** The lowest-leverage line. If the caption is weak, fix the first line, never the tags. Tight local or sub-niche tags are the one case they still help.

## Check before showing

Put the transcript text, the on-screen text and any facts the client gave in this conversation into `videos/<reel>/caption-source.txt` with the Write tool. Save the draft to `videos/<reel>/caption.md`: a first line `<!-- DRAFT -->`, a `## ` heading per part (hook options, body, alt text, hashtags), audience text only under each. Scores and notes stay in chat; the check skips headings and comments only. Then run:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/skills/caption-writer/scripts/check_caption.py" --caption videos/<reel>/caption.md --source videos/<reel>/caption-source.txt --cta "<trigger word>" --cta "<deliverable name>"`

Pass the trigger word exactly as the reel says it (e.g. `--cta "HOOKS"`) and the deliverable's name exactly as the CTA card shows it (e.g. `--cta "The 12 Opener List"`); each must appear word for word. Add `--no-dashes` when that option is on. Leave `--cta` off only when the reel has no CTA.

- Exit 0: show the caption.
- Exit 1: one line per problem (a number not in the source, a half-true bold, a CTA mismatch, a dash). Fix each, run it again, and only then show the caption. Fill-ins in `[...]` are skipped on purpose.
- Exit 2: a file couldn't be read. Check the paths and run again.

Tell the client what changed in plain words ("I took out the 10x, since the reel doesn't say it"), never the raw lines.

## Audit mode

Score the caption against this list and report gaps. Don't silently rewrite:

- [ ] Main keyword landed by the end of sentence 2 (the trigger word doesn't count)?
- [ ] No keyword or tag block at the bottom?
- [ ] Every keyword woven into a sentence, not listed?
- [ ] One CTA, word for word the reel's, and the deliverable named the same way?
- [ ] Every number and claim in the transcript or from the client?
- [ ] Every bolded span true on its own?
- [ ] Every URL loads?
- [ ] Alt text written?
- [ ] Any options the client turned on (keyword count, cut-off, length band, dashes, emoji, hashtags) met, and none applied that the client left off?

Run the check above on the existing caption too. Then offer fixes; the client locks the final words.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.1.0 --skill caption-writer --step '<check or save>' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
