# SocialCrawl — client key setup (bring-your-own-key)

> SocialCrawl is the social-data source the engine runs on. Each client uses
> **their own** key + credits (so they never draw down anyone else's). The key
> is exposed to the paying client by necessity — never to the public.

## Click-path (≈2 minutes)

1. Go to **[socialcrawl.dev](https://www.socialcrawl.dev/?ref=AQNU384G)** → click
   **Start for free**. Every account starts with **100 free credits**, no credit card.
   *(That link is the RevXL referral link — signing up through it gets you bonus
   credits and supports the engine. Use it rather than a bare socialcrawl.dev.)*
2. **Sign in** — Google, GitHub, Kakao, or email + password.
3. In the dashboard, open the left sidebar → **API Keys**.
4. Click **+ Create** → give the key a name (e.g. your business name).
5. Reveal it (the 👁 eye icon) and **copy** it — the key starts with **`sc_`**.
6. **Do not paste the key into the chat.** Claude opens a small key box instead — paste
   it there; the field hides it, and the box saves it to `~/.config/socialcrawl/api_key`
   so it's remembered every future session. Closed the box or ran out of time? Say
   "set up my SocialCrawl key" any time and Claude opens it again.

   If the box can't open at all (no desktop, or Linux, which has no box), onboarding step 1d
   saves the key another way, with nothing typed into a terminal.

   Pasting a key into chat writes it into the conversation transcript, session logs,
   and any screenshot of them. The box keeps it off all three.
7. Your credit balance shows top-right of the dashboard (100 to start; top up
   under **Get Credits** / **Payments** when you run low).

## Where the key is stored / resolved

The engine resolves the key in this order (handled by the bundled `socialcrawl`
skill — it ships inside this plugin, so it's always available). Its API Key steps check only
presence and prefix and print a label, never the key:
1. Env var `SOCIALCRAWL_API_KEY` (if set and starts with `sc_`)
2. File `~/.config/socialcrawl/api_key`
3. Neither → the `onboarding` skill opens the key box, which saves to the file above.
   The key is never asked for in chat.

## Verify it works

Claude runs these for you in onboarding Step 2.

- **Balance check (0 credits):**
  `curl -s -H "x-api-key: $(cat ~/.config/socialcrawl/api_key)" -o /tmp/sc-balance.json "https://www.socialcrawl.dev/v1/credits/balance"`
  → read `data.balance` from that file in a separate call.
- **Live auth test (1 credit):**
  `curl -s -H "x-api-key: $(cat ~/.config/socialcrawl/api_key)" -o /tmp/sc-verify.json "https://www.socialcrawl.dev/v1/tiktok/profile?handle=tiktok"`
  → read the file in a separate call: a 200 with `success: true` confirms the key is live (`credits_remaining` is null on a
  cached answer, so don't read the key's health from it).
- Key in `SOCIALCRAWL_API_KEY` instead? Use `"x-api-key: $SOCIALCRAWL_API_KEY"`. Never put the
  key value itself in the command.

If either returns 401/403, the key is wrong or revoked — re-copy it from the
dashboard's **API Keys** page, then Claude opens the key box for it.

## Credits — rough guide

Most research plays run on 1–5 credit calls: a voice-of-customer mining pass is
~5–10 credits, an ad-library teardown ~15–35, an AI-visibility audit 2–1,605 (a quick one
billed 20 when measured). The big-gun one-shots (creator vetting, lead discovery, share of voice) cost 15–200
credits **per call**; Claude names each one's price first and runs it only on your pick (a run with
nobody there makes one only when its own prompt names it). 100 free credits
covers plenty of exploring; a real research engagement usually needs a top-up.
