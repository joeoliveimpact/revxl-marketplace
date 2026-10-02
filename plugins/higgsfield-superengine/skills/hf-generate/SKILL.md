---
name: hf-generate
description: Use this skill whenever the client wants Claude to actually make an image or video with Higgsfield. Trigger phrases include "render this prompt", "run it on Higgsfield", "make another one", "try it in Flare / Kling / Seedance". Product shots, static ads, thumbnails and video ads go to the matching use-case skill first (higgsfield-superengine:product-shots, higgsfield-superengine:static-ads, higgsfield-superengine:thumbnails, higgsfield-superengine:ugc-video-ads), which hands off here. The only skill in higgsfield-superengine that spends the client's Higgsfield credits. It picks the model, writes the prompt with the craft skills, shows the price before anything spends, runs the job through the spend guard, waits for it, and saves the files to higgsfield/<date>/ in the workspace. Needs higgsfield-setup done first.
---

# hf-generate: make an image or video (the only skill that spends)

## Output contract (every run, in this order)

1. The model picked and why, in one plain line. The client can overrule it.
2. The price before anything spends ("about $0.12").
3. The finished file(s), saved in `higgsfield/<YYYY-MM-DD>/` in the workspace, with each path named.
4. On any failure: what happened in plain words, whether anything was charged, and an offer to send Joe a report.

Nothing reaches Higgsfield except `hf_rest.py submit`, after a fresh `estimate` of the exact same request. Never call the Higgsfield API, CLI or SDK any other way; the spend guard blocks it.

## Re-invoke guard (read before step 1)

- If the conversation was compacted since this skill loaded, invoke this skill again before going on. Later steps may be missing from memory.
- **Never submit the same job twice.** Before any submit (including after a compaction, a "try again" or a re-invoke), look for an earlier submit of this job that got a `request_id`: in the conversation, or in today's `higgsfield/<YYYY-MM-DD>/log.jsonl` (a line with `"event": "submit"` and a `request_id`). Found: resume at step 5 (wait), do not submit. Submit again only for a new or changed request, or after a failure whose output says `"safe_to_resubmit": true`.
- No `higgsfield\.python` in the workspace, or the key check fails: run the `higgsfield-superengine:higgsfield-setup` skill first.

## Ground rules

- **The client never types a command.** Claude runs every command below in the PowerShell tool, from the workspace folder, as ONE plain command: no `cd` or `Set-Location` first, no `;`, `&&` or pipes. Keep every quote exactly as written. `${CLAUDE_PLUGIN_ROOT}` is the plugin's own folder.
- Claude Code may show permission pop-ups. Say what each one is before it appears; the client decides. Never promise there will be none.
- Plain English for a busy coach. Gloss each term once, e.g. "estimate (a free price quote)".
- Money decisions come from each command's JSON `class` field. Never guess. Never re-run a submit whose output says `"safe_to_resubmit": false`.
- `<key>` below = the `estimate_key` that step 3 prints (the job's ID in the spend ledger). `<endpoint>` = the model's endpoint from its model file.
- **Mac (beta, untested):** use the Bash tool and replace `& (Get-Content -Raw -Encoding UTF8 higgsfield\.python)` with `python3`. Paid submits are refused on a Mac for now (the spend guard runs only on Windows): say so, and stop after step 3.

## 1. Pick the model

Read `${CLAUDE_PLUGIN_ROOT}/references/model-picker.md` and follow it (Flare is the default for images). Then read the chosen model's file in `${CLAUDE_PLUGIN_ROOT}/references/models/` for its endpoint, settings and prompt rules, and `${CLAUDE_PLUGIN_ROOT}/references/settings-defaults.md` (always set quality explicitly). Tell the client the pick in one line.

The spend guard checks this: it refuses a submit unless this session has read the chosen model's file with the Read tool. Read it BEFORE writing the prompt, never after.

## 2. Build the prompt

Use the `higgsfield-superengine:image-prompting` skill for images or `higgsfield-superengine:video-prompting` for video (a use-case skill may have done this already).

Then show the client the full prompt text, word for word, in one message: every prompt in the request (one per shot for multi-shot), never a summary or paraphrase, even for a cheap test or a prompt the client dictated. Ask "Good to go?" and wait for their reply. A change means a new prompt: show it again.

The spend guard checks all three: it refuses a submit unless this session loaded a prompting skill (or a use-case skill), the exact prompt text appears in one of Claude's messages, and the client replied after it.

A reference image or video from the client's computer goes up first (free), and its `public_url` goes into the request. For a video, always upload the file itself: the upload records its length, so the job is priced on the real seconds instead of the 30 s maximum.

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/hf_rest.py" upload "<file path>"`

Write the request with the Write tool to `higgsfield/requests/<name>.json`: a JSON object with the prompt and the model file's settings. `<name>` uses only letters, digits and dashes. Estimate and submit must use this same file, unchanged.

## 3. Price it (free)

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/hf_rest.py" estimate <endpoint> higgsfield/requests/<name>.json`

This costs nothing. Keep the `estimate_key`. If `class` is not `ok`:
- `validation_error` or `bad_request`: a setting is wrong. Fix the request from the model file and estimate again.
- `server_error` with `record` set: Higgsfield can't quote this one. Go on; the spend guard will ask the client.
- anything else: explain its `message`, and offer a failure report.

The output's `price` is the price to show. Tell the client `price.display_usd` as "about $X". If it is `null`, say "Higgsfield can't give an exact price for this one." If `price.ask` is `true`, add "This one needs your OK in a pop-up." This only shows the price; the spend guard prices the estimate again itself at submit.

An estimate is good for 30 minutes. If more time has passed, estimate again before step 4.

## 4. Submit (this spends)

Say first: "Small jobs under your safety cap just run. Bigger ones show a pop-up with the price: Allow runs this one job, Deny spends nothing. Please answer within 60 seconds."

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/hf_rest.py" submit <endpoint> higgsfield/requests/<name>.json`

The spend guard (a safety check that runs before the command) decides one of three things:
- **Silent:** priced and under the cap. It runs with no pop-up.
- **Ask:** over the cap, or no firm price. A pop-up shows the price. Deny spends nothing, and the hold on the ledger clears itself about 90 seconds later.
- **Deny:** blocked, with a reason. "No estimate" or "stale": estimate again (step 3). "still open in the ledger": wait 90 seconds or refund (below), then submit again. "nobody can be asked in permission mode": Claude is running in a mode with no pop-ups, so only jobs under the cap can run; tell the client.

Then read submit's `class`:
- `ok`: keep the `request_id`. Go to step 5.
- `spend_gate_refused` (for example `stamp_expired`: the pop-up took over 60 seconds): refund with reason `not_sent`, then run submit again for a fresh pop-up.
- `insufficient_credits`: run `balance set 0`, then refund with reason `insufficient_credits`. Tell the client to add funds (Billing, then Add funds, on open.higgsfield.ai), then record the new balance with the `higgsfield-superengine:higgsfield-setup` skill.
- `"safe_to_resubmit": true` (Higgsfield rejected the request, so no job exists): refund with reason `not_sent`. Fix and retry, or offer a report.
- `"safe_to_resubmit": false` (connection or server trouble): do NOT submit again; the job may exist. Tell the client it may still show up on the Higgsfield website, and offer a report.

Ledger commands (`<reason>` is `not_sent`, `insufficient_credits`, `job_nsfw`, `job_failed` or `job_canceled`):

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py" refund <key> --reason <reason>`

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py" settle <key>`

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py" balance set 0`

## 5. Wait (PowerShell tool, timeout 600000 ms)

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/hf_rest.py" wait <request_id> --endpoint <endpoint> --timeout 540`

Each call waits up to 9 minutes, because one command can't run longer than 10. Read `class`:
- `wait_timeout`: still running. Say "Still working (videos can take up to an hour)" and run the same wait again. Never submit again.
- `job_completed`: settle `<key>`, then go to step 6.
- `job_nsfw`, `job_failed` or `job_canceled`: Higgsfield refunds these. Refund `<key>` with the matching reason. For `job_nsfw`, explain the content filter in plain words and offer a reworded prompt.
- anything else: the job's state is unknown. Don't submit again; run wait again later, and offer a report.

## 6. Download

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/hf_rest.py" download <request_id>`

Files land in `higgsfield/<YYYY-MM-DD>/`. Name each path for the client, and show an image with the Read tool. For a video edit, compare the file with the source (frame rate, length, size; `references/video-edit-recipes.md`) and tell the client any difference before they cut it in. `download_failed`: run it again (the links stay valid for at least 7 days).

Then offer: "Want a variation?" Any new or changed request starts again at step 2.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged. Then offer: "Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `higgsfield/reports/report-body.md`: what the client asked for, the model and endpoint, the prompt text, the step that failed, and the output's `class`, `message`, `request_id` and `correlation_id`. Never the key.
2. Draft it. Keep the summary short, in single quotes, with no apostrophes and no script names:

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin higgsfield-superengine --plugin-version 0.1.0 --summary 'Video job failed on Seedance' --body-file higgsfield/reports/report-body.md --error-code job_failed`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is so they can email it to Joe. Skip instead:

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
