# SocialCrawl — client key setup (bring-your-own-key)

> SocialCrawl is the social-data source the engine runs on. Each client uses
> **their own** key + credits (so they never draw down anyone else's). The key
> is exposed to the paying client by necessity — never to the public.

**📹 Video walkthrough:** `<LOOM_URL — paste the Loom here once recorded>`

## Click-path (≈2 minutes)

1. Go to **[socialcrawl.dev](https://www.socialcrawl.dev/?ref=AQNU384G)** → click
   **Start for free**. Every account starts with **100 free credits**, no credit card.
   *(That link is the RevXL referral link — signing up through it gets you bonus
   credits and supports the engine. Use it rather than a bare socialcrawl.dev.)*
2. **Sign in** — Google, GitHub, Kakao, or email + password.
3. In the dashboard, open the left sidebar → **API Keys**.
4. Click **+ Create** → give the key a name (e.g. your business name).
5. Reveal it (the 👁 eye icon) and **copy** it — the key starts with **`sc_`**.
6. **Do not paste the key into the chat.** Run the setup helper instead — it hides
   the key as you type, verifies it, and saves it to `~/.config/socialcrawl/api_key`
   so it's remembered every future session:
   - **Windows** — double-click `setup/setup-key.bat`
   - **macOS / Linux** — double-click `setup/setup-key.command`
     (first time only: `chmod +x setup/setup-key.command`)

   Pasting a key into chat writes it into the conversation transcript, session logs,
   and any screenshot of them. The helper keeps it off all three.
7. Your credit balance shows top-right of the dashboard (100 to start; top up
   under **Get Credits** / **Payments** when you run low).

## Where the key is stored / resolved

The engine resolves the key in this order (handled by the bundled `socialcrawl`
skill — it ships inside this plugin, so it's always available):
1. Env var `SOCIALCRAWL_API_KEY` (if set and starts with `sc_`)
2. File `~/.config/socialcrawl/api_key`
3. Ask the user (then auto-save to the file above)

## Verify it works

- **Balance check (0 credits):**
  `curl -s -H "x-api-key: <key>" "https://www.socialcrawl.dev/v1/credits/balance"`
  → returns `data.balance`.
- **Live auth test (1 credit):**
  `curl -s -H "x-api-key: <key>" "https://www.socialcrawl.dev/v1/tiktok/profile?handle=tiktok"`
  → a 200 with `credits_remaining` confirms the key is live.

If either returns 401/403, the key is wrong or revoked — re-copy from the
dashboard's **API Keys** page.

## Credits — rough guide

Most research plays run on 1–5 credit calls: a voice-of-customer mining pass is
~5–10 credits, an ad-library teardown ~15–35, an AI-visibility audit ~10. The
big-gun one-shots (creator vetting, lead discovery, share of voice) cost 15–50
credits **per call** and are always confirmed with you first. 100 free credits
covers plenty of exploring; a real research engagement usually needs a top-up.
