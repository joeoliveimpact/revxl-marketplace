---
name: rehooks
description: 'Find where a Reel script loses viewers and write a re-hook for each drop-off: line, on-screen text, visual, timing. Use for "rehooks", "secondary hooks", "keep them watching", "retention".'
license: MIT
metadata:
  author: Engine For Impact
  version: 0.1.0
---

# ReHooks

Find where an Instagram Reel script loses viewers, and write a beat that wins them back at each of those points.

A re-hook is that beat. The opening buys the first few seconds. After that, attention slides unless something deliberate makes the viewer choose again to keep watching. The line right after the opening is the secondary hook, and every later one is a re-hook. The secondary hook is a strong default, not a requirement: it depends on what the opening says, and it quite often fits. Add it when it fits, and do not flag it when it is absent.

## What you return

1. **Drop-off map.** Every beat of the script, with an estimated time, a risk rating of low, medium or high, and the reason a viewer would leave at that beat.
2. **A re-hook for every medium and high point.** For each: the type by name, the spoken line, the on-screen text short enough to read in about a second, the visual change, and where it sits in the timeline.
3. **Pay-off check.** Where the loop the opening opened finally closes, confirmed to be the final beat, plus every new loop the re-hooks open and where each one closes.
4. **Frozen script.** If the creator says the script is final, or asks for suggestions rather than a rewrite, return proposals only, each anchored to the exact existing line it would replace or follow, quoted. Never rewrite the opening or the body lines. This overrides every rewrite, move and swap instruction in this file.
5. The one thing to check before recording.

## When NOT to use this

- The opening itself is the problem. On a retention graph that shows as an immediate drop, not a slide. A re-hook cannot rescue a wrong opening: say so plainly and hand off to `hook`.
- The whole script needs reworking. That is work for `viral`.
- There is no script yet. That is work for `angles`.
- The request is a written post, a carousel, LinkedIn or X copy. Say this skill is built for Instagram Reels, and adapt only if the creator confirms.
- The request is about a code hook, a webhook, a PreToolUse hook or any automation hook. Nothing in this skill applies. Do not respond as if it does.

Reel captions are out of scope. You work on the spoken script and the on-screen text only.

## Ask the creator for

- The full script, with any timings they already have.
- The target length.
- The retention graph, if they have one.
- What the opening promises the viewer.
- Whether the script is final.
- The visuals and B-roll they plan to shoot.

## Method

0. **Check whether the script is frozen.** If the creator says the script is final, or asks for suggestions rather than a rewrite, return proposals only, each anchored to the exact existing line it would replace or follow, quoted. Never rewrite the opening or the body lines. This overrides every rewrite, move and swap instruction below.
1. **Break the script into timed beats.** Read it aloud at recording pace and mark where each beat starts. Estimates are fine, but say they are estimates.
2. **Rate every beat low, medium or high risk,** and write the reason a viewer would leave there. The reason matters more than the rating, because it decides which re-hook type fits.
3. **Place narrative re-hooks by the clock.** A narrative re-hook reopens a loop or raises the stakes. Cadence follows length, as guidance, never a hard fail. Any length works, and the same rhythm runs the whole way:
   - The secondary hook, right after the opening, by about 10 seconds when it fits.
   - Under about 35 seconds: no mid-Reel re-hook required; micro beats alone are enough.
   - After that, about one re-hook every 30 seconds, however long the Reel runs. Count the runtime in 30 second blocks; there are no length bands.
   - A stretch of 40 seconds or more with no spoken re-hook: flag it, only in a Reel long enough to have one.

   Never place a re-hook inside the final payoff beat. If a nominal placement would land there, move it earlier, to the last beat before the payoff.
4. **Layer micro beats underneath.** A micro beat is a visual cue: anything that pulls the viewer's focus somewhere new, such as a cut, a zoom, a change of camera angle, a scene shift, an animation or a new line of on-screen text. Suggest one every 3 to 5 seconds, the whole way through, the opening included. A change of sound can ride along with one, but never stands in for it, since it is invisible on mute.
5. **Override the clock beat by beat.** At each beat ask the only question that matters: is this where the viewer swipes? With a retention graph, put re-hooks at the dips. A gradual decline means add re-hooks. An immediate drop means the opening, so hand off. A late drop means the call to action.
6. **Name a type for every re-hook you write.** Use these nine:
   1. **Restate the gap.** Remind the viewer where they are against where they want to be.
   2. **Solve, then complicate.** Give the fix, then name the new problem it creates.
   3. **Contrast pivot.** Confirm what just landed, then turn with a contrast word such as "but" or "here's the thing", promising the next part is better for a different reason.
   4. **Prediction break.** Set up what the viewer expects, then break it. The clue is planted earlier, so the break reads as fair rather than random.
   5. **Seam re-hook.** A connective line at the boundary between two sections, with no dead air in the join.
   6. **Hook stacking.** Open the next loop as the current one closes, so two loops overlap instead of one ending.
   7. **Unfinished-list checkpoint.** Number the points and hold the best for last, ranked or picked out: "my favorite is number three".
   8. **Mid-thread segment end.** End a segment on an unresolved line rather than a tidy one.
   9. **Identity line.** An early "if you're a [who], this is you" beat that makes the viewer buy in again. It counts only when it raises the stakes for the viewer. A plain audience call-out is not a re-hook.
7. **Split the surfaces.** The spoken line carries curiosity, the on-screen text carries clarity. Every narrative re-hook gets a visual change with it, every cut gets fresh text, and the text must carry the re-hook on its own, because roughly half of viewers watch muted. If you change or propose a new opening, or propose anything touching the first beat, its on-screen hook text is complete and readable at the first frame: two grabbers on screen at 0.0 seconds, not animating in. Secondary pieces may animate in later. For a final script this is a proposal, never a rewrite.
8. **Check the failure modes.** Mark any that apply and fix them:
   - The opening question is answered before the last beat. Mark where it is answered, and move it.
   - Too many interrupts. An overloaded viewer leaves as fast as a bored one.
   - A surprise with no setup, which reads as confusion rather than payoff.
   - "But" in every sentence, which sounds forced.
   - A promise the Reel never pays. Loops must close.
   - A tease with nothing learned before it. Every re-hook sits on something real the viewer just got. Two teases in a row with no value between them is an empty tease: cut one, or put value between them.
   - Negative framing the content does not call for. There is no set count: some scripts want it on many beats, some on none. Judge it by this script.
   - Sound-only interrupts, invisible on mute.
   - No breathing room anywhere.
9. **Run the delivery tests** in the section below.
10. **Say what this measures against.** Average watch time and skip rate are the signals re-hooks move, and the target shape is a flat retention line. A strong start with a stair-step down is the signature of a good opening with no re-hooks under it. Matching the last frame to the first frame loops viewers and adds views. Then name the one pre-record check.

## Does a line count as a re-hook?

Run this on every spoken line you write or check as a re-hook. A re-hook tells the viewer that something new or better is coming next, so they keep watching to get it. The test: does this line make me want the next part, or is it the point itself? Check spoken lines only. Cuts, zooms and props are micro beats, judged in step 4.

**It counts:**

- **The secondary hook,** when it digs into the opening, promises a result, or opens a second question: "I tried this for one week and my inbox blew up."
- **A reveal of something new or extra:** "and there's more", "you can also...", "here's my real secret".
- **A result promise:** "wait till you see what this did for me."
- **The turn from old to new:** "and that changes everything", "it doesn't work that way anymore".
- **A question** that opens a gap the Reel will close.
- **A line that points forward:** a warning or bold claim that opens a new problem the Reel then solves, or a turn with "but" or "therefore" toward what comes next.
- **A hand-off to what comes next.** A weak one that does not say what is coming, like "here's how", still counts, but flag it weak and rewrite it to name the payoff.
- **A list item picked out or ranked:** "the last one is my favorite".

**It does not count:**

- **The point itself:** a claim, opinion, fact or warning that ends on itself and is never paid off.
- **The setup before a turn,** like "this used to take me weeks". The turn that follows is the re-hook.
- **A plain list step or instruction,** like "first, open the app".
- **A sales push or call to action.**
- **A question to a live room.**
- **The opening itself.**

**Loop sizes.** Loops nest. The main loop is the question the opening asks, and it closes at the final beat. A side loop is a smaller question inside one point, and it closes a beat or two later. A line loop is a small pull inside one sentence, like "and here's the catch", and it closes in the next sentence. Every loop, of any size, closes inside the Reel.

## Guardrails

- Never invent retention numbers, watch times or drop-off percentages. Work from the creator's graph, or from estimates you label as estimates.
- Never rewrite a frozen script. Proposals only, each paired with the exact line it follows.
- Never invent evidence of any kind: no statistics, client results, studies or quotes the creator did not supply.
- Earnings, client-result and transformation claims appear only as supplied, with the supplied qualifier.
- Do not sanitize the creator's word choices. Blunt, funny and crude lines stay. Your guardrails limit targets and factual claims, not vocabulary.
- Audience language shapes tone and word choice by default. When a phrase from the creator or their audience is gold, strong enough to work as it is, keep it word for word.
- Hand off when the opening is the real problem, instead of stacking re-hooks on top of it.
- Do not borrow structures from templates built for written posts or paid ads.
- No em dashes and no en dashes. Use a comma, a period or a colon. Write time ranges with "to": 0:00 to 0:07.

## Tests before you deliver

- **Open-loop list.** List every candidate open loop in the script. The strongest belongs in the opening. The second strongest belongs in a narrative re-hook only if the Reel is long enough for one under the 30-second rhythm in step 3. For a Reel under about 35 seconds, no second loop is required: the output may carry micro beats only. If a stronger loop sits later than the opening, swap it into the opening, and the new opening must pass the first-frame check. For a final script the swap is a proposal, never a rewrite.
- **First-frame check.** For any changed or proposed opening, and any proposal touching the first beat: is the on-screen hook text complete and readable at the first frame, two grabbers on screen at 0.0 seconds, not animating in? Secondary pieces may animate in later.
- **Pause-anywhere test.** Stop at any point: could a viewer say where they are and what just happened?
- **Sentence test.** Every sentence is either necessary context or a distraction. Name the distractions.
- **Pay-off test.** Does each re-hook pay off inside this Reel, or is it bait? Bait gets cut.
- **Mute test.** Read only the on-screen text, start to finish. Does the Reel still hold?
- **Cadence check.** Does the number of narrative re-hooks fit the guidance in step 3, with a flag rather than a fail where it does not, and does every re-hook sit before the payoff beat?
- **Frozen check.** For a final script, are you returning proposals mapped to exact lines, and no rewrite?

## Close

End every response by naming the one thing the creator should check before recording. One line, specific to this script, usually the beat where the drop-off risk is highest.
