# SocialCrawl — client key setup (bring-your-own-key)

> SocialCrawl is the social-data source the teardown feature runs on. Each client uses **their own**
> key + credits (so they never draw down anyone else's). Needed ONLY for `carousel-teardown` link
> pulls — `carousel-create` works without it.

## Click-path (≈2 minutes)

1. Go to **[socialcrawl.dev](https://www.socialcrawl.dev/?ref=AQNU384G)** → click **Start for free**.
   Every account starts with **100 free credits**, no credit card.
   *(That link is the RevXL referral link — signing up through it gets you bonus credits and supports
   the engine. Use it rather than a bare socialcrawl.dev.)*
2. **Sign in** — Google, GitHub, Kakao, or email + password.
3. In the dashboard, open the left sidebar → **API Keys**.
4. Click **+ Create** → give the key a name (e.g. your business name).
5. Reveal it (the 👁 eye icon) and **copy** it — the key starts with **`sc_`**.
6. Paste it back here. It gets saved to `~/.config/socialcrawl/api_key` so it's remembered every
   future session.
7. Your credit balance shows top-right of the dashboard (100 to start; top up under **Get Credits**
   when you run low).

## Where the key is stored / resolved

Resolution order (same as every REVXL engine):
1. Env var `SOCIALCRAWL_API_KEY` (if set and starts with `sc_`)
2. File `~/.config/socialcrawl/api_key`
3. Ask the user (then auto-save to the file above)

## Verify it works

- **Balance check (0 credits):**
  `curl -s -H "x-api-key: <key>" "https://www.socialcrawl.dev/v1/credits/balance"` → returns `data.balance`.
- If it returns 401/403, the key is wrong or revoked — re-copy from the dashboard's **API Keys** page.

## Credits — what teardown costs

A single-post pull (`/v1/instagram/post`) is a low-single-digit credit call. A typical teardown = one
pull. The engine states the cost before spending and never batch-pulls without asking.
