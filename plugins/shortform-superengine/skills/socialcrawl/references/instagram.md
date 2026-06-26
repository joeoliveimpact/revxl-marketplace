# Instagram (12 endpoints)

## Endpoints

| Resource | Params | Tier | Description |
|----------|--------|------|-------------|
| profile | `handle` | standard | Get user profile |
| profile/posts | `handle` | standard | List user posts |
| post | `url` | standard | Get post details |
| post/comments | `url` | standard | List post comments |
| basic-profile | `(userId)` | standard | Get basic profile by user ID (optional) |
| profile/reels | `user_id` / `handle` | standard | List user reels (one of required) |
| highlights | `user_id` / `handle` | standard | List story highlights (one of required) |
| highlight/detail | `(id)` | standard | Get highlight detail (optional) |
| search/reels | `query` | standard | Search reels |
| media/transcript | `url` | premium | Get media transcript |
| user/embed | `handle` | standard | Get user embed HTML |
| song/reels | `audio_id` | standard | List reels using a song |

### Parameter legend

- `a, b` — both params are required.
- `a / b` — a `oneOf` group: at least one member must be provided.
- `(a)` — optional only, no required params.

## Parameter Details

- `handle`: Instagram username without @ symbol (e.g., `instagram`)
- `user_id`: Instagram numeric user ID (e.g., `25025320`)
- `userId`: Alias used by `basic-profile` for the numeric user ID
- `url`: Full Instagram post or reel URL (e.g., `https://www.instagram.com/p/CwA1234abcd/`)
- `query`: Search keyword or phrase (e.g., `workout routine`)
- `id`: Instagram highlight ID (e.g., `17854360229135492`)
- `audio_id`: Instagram audio/song ID (e.g., `243313786724210`)

## Pagination (lists)

List endpoints — `profile/posts`, `profile/reels`, `post/comments` — return one page
plus a `next_cursor` in the envelope. To page, pass it back as **`&max_id=<next_cursor>`**
and repeat until `next_cursor` is absent.

```bash
curl -s -H "x-api-key: $SOCIALCRAWL_API_KEY" \
  "https://www.socialcrawl.dev/v1/instagram/profile/reels?handle=instagram&max_id=<next_cursor>"
```

> **Only `max_id` works for IG list paging.** `cursor`, `pagination_token`, and `after`
> are silently ignored — they return page 1 again with no error, so you loop forever on
> the first page. Tested + confirmed; do not use them.

`search/reels` is the exception: it returns a **first-page sample only and does not
paginate** — breadth comes from running many diverse query seeds, not from paging one
search.

## Transient scrape failures (retry, don't hard-fail)

IG scraping can flake upstream. SocialCrawl **auto-refunds** credits on `UPSTREAM_ERROR`
(502) and `SERVICE_UNAVAILABLE` (503), so a failed call costs nothing. On either: retry
once (503 carries a `Retry-After`, default ~30s), and if it still fails, report it and
move on rather than hard-erroring the whole run. An empty/nonexistent profile returns
`RESOURCE_NOT_FOUND` with the credit refunded — treat that as "no data," not a crash.

## Field Maps

The `profile` endpoint returns an `Author` response normalized by the `instagram-author` field map, and `post` returns a `Post` normalized by `instagram-post`. Both include computed fields under `data.computed`. Use `?format=raw` to bypass both. Other Instagram endpoints are passthrough.

## Example

```bash
curl -s -H "x-api-key: $SOCIALCRAWL_API_KEY" \
  "https://www.socialcrawl.dev/v1/instagram/profile?handle=instagram"
```
