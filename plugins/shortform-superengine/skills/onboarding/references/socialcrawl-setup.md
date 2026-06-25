# SocialCrawl — client key setup (bring-your-own-key)

> SocialCrawl is the social-data source the engine runs on. Each client uses
> **their own** key + credits (so they never draw down anyone else's). The key
> is exposed to the paying client by necessity — never to the public.

**📹 Video walkthrough:** `<LOOM_URL — paste the Loom here once recorded>`

## Click-path (≈2 minutes)

1. Go to **socialcrawl.dev** → click **Start for free**. Every account starts with
   **100 free credits**, no credit card.
2. **Sign in** — Google, GitHub, Kakao, or email + password.
3. In the dashboard, open the left sidebar → **API Keys**.
4. Click **+ Create** → give the key a name (e.g. your business name).
5. Reveal it (the 👁 eye icon) and **copy** it — the key starts with **`sc_`**.
6. Paste it back here. It gets saved to `~/.config/socialcrawl/api_key` so it's
   remembered every future session.
7. Your credit balance shows top-right of the dashboard (100 to start; top up
   under **Get Credits** / **Payments** when you run low).

## Where the key is stored / resolved

The engine resolves the key in this order (handled by the `socialcrawl` skill):
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

A typical competitor cross-reference run costs ~100–200 credits (profiles +
reels + search, mostly 1-credit calls; some advanced endpoints are 5). 100 free
credits is enough to try one small run; a real client engagement needs a top-up.
