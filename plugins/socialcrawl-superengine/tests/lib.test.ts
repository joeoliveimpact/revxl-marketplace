import { expect, mock, test } from 'claude-code/testing'
import * as lib from '../hooks/mod/lib'
import REAL from './costs-real'

import { ageOf, fmt, revxlOf, sidOf, spanOf } from '../hooks/mod/lib'
import { bandDial, detailCards, sessionCard, whyOf, CALL_DECISIONS, isCall, newestFor, recordLimit, bandOf, callRows, pathsFor, lastRoutine } from '../hooks/mod/lib'
import { HOW_IT_WORKS, STYLES, changesOf, holds, customOf, storedLock, lockPick, lockToSend, parseRoutes, styleOf } from '../hooks/mod/lib'
import type { Lock } from '../hooks/mod/lib'

// Frozen M6 Pass A: optional reads keep missing Pass B exports assertion failures.
const m6 = lib as any

test('EGM B3b: real More rows classify charge-starting PATCH as unpriced and keep other zero-range writes free', () => {
  const rows = lib.moreOf(REAL, Object.keys(REAL._platforms))
  expect(rows.find(r => r.call === 'PATCH web/monitors/{monitor_id}')).toMatchObject({ kind: 'unpriced', price: null })
  for (const call of ['DELETE web/jobs/{job_id}', 'DELETE web/monitors/{monitor_id}', 'DELETE web/sessions/{session_id}', 'POST web/sessions/{session_id}/execute']) {
    expect(rows.find(r => r.call === call)).toMatchObject({ kind: 'free', price: 'free' })
  }
  expect(['priced', 'free', 'unpriced'].map(kind => rows.filter(r => r.kind === kind).length)).toEqual([584, 25, 7])
  const search = lib.moreOf(REAL, ['prism', 'search', 'tavily', 'perplexity', 'web'])
  expect(search.filter(r => r.kind === 'free').length).toBe(13)
  // Derive every row's expected kind independently from the real ranges and the frozen exception.
  for (const row of rows) {
    const range = (REAL as any)[row.call].range
    const kind = row.call === 'PATCH web/monitors/{monitor_id}' || range === null ? 'unpriced' : range[0] === 0 && range[1] === 0 ? 'free' : 'priced'
    expect(row.kind).toBe(kind)
    if (kind === 'unpriced') expect(row.price).toBeNull()
  }
})

test('EGM W: STARTS_CHARGES is exactly the monitor PATCH route', () => {
  expect((lib as any).STARTS_CHARGES).toEqual(['PATCH web/monitors/{monitor_id}'])
})

test('EGM W9: autoOf floors finite nonnegative balances and otherwise uses 500', () => {
  const balances = [4000, 2000, 1200, 1199.9, 800, 3.9, 0, -1, NaN, Infinity, null, undefined, '1200']
  expect(balances.map(b => (lib as any).autoOf?.(b))).toEqual([500, 500, 300, 299, 200, 0, 0, 500, 500, 500, 500, 500, 500])
})

test('EGM W: LOCK_HELP states blocking and the one-unit transcript floor verbatim', () => {
  expect(lib.LOCK_HELP).toBe("Paid transcripts cost far more than free captions. Blocked stops them before they run; Allowed lets them run and counts a single transcript at one unit's price, a floor, so one that bills many units is counted low; a batch is counted at its ceiling.")
})

test('EGM W: Transcript endpoints explains refused odd encodings and the floor verbatim', () => {
  expect(HOW_IT_WORKS.find(e => e.title === 'Transcript endpoints')?.text).toBe("Blocked refuses transcript calls before they run, and the guard refuses any call whose address is written in an odd encoding. Allowed lets them run and counts a single transcript at one unit's price, a floor, so one that bills many units is counted low; a batch is counted at its ceiling.")
})

test('EGM W: When credits come back pins ledger, failed-call and late-charge limits verbatim', () => {
  expect(HOW_IT_WORKS.find(e => e.title === 'When credits come back')?.text).toBe("No sooner than about two minutes after a call returns, and only once the ledger shows a charge on that endpoint this session, the guard can swap a finished call's hold for what was charged; until then the band can read high, a call with no charge there keeps its hold until one appears, and a ledger read can also push the total up. A call that fails, is interrupted, runs in the background, or is piped or chained keeps its hold and can count its hold and its charge together for the rest of the session; nothing comes back without a key, or after three failed ledger reads in a row. A charge the vendor records more than about 2 minutes after its call returns can be counted late, or not at all, so the band can also read low.")
})

test('EGM W: More options names the request-priced section verbatim', () => {
  expect(HOW_IT_WORKS.find(e => e.title === 'More options')?.text).toBe("Each group's More options lists the rest of its platforms' calls, and More platforms lists every other site's calls. A press asks Claude to make that one call with what is in the Target box and to ask you for anything else it needs. Calls under \"Price depends on the request\" can't run from here, and neither can transcript calls while they're blocked.")
})

test('EGM W: DEPENDS_HELP explains zero guard counts and states the price-first instruction verbatim', () => {
  expect(lib.DEPENDS_HELP).toBe("Ask Claude for these; the pane can't price them, and the guard counts some of them at 0, so have Claude state the price first.")
})

test('EGM W: unknown Usage has its colon while known Usage stays unchanged', () => {
  expect([null, 0, 1, 1234.5].map(lib.usageWords)).toEqual(['Usage: none read yet', 'Usage 0 cr', 'Usage 1 cr', 'Usage 1,234.5 cr'])
})

test('EGM W: LOCK_UNRECOGNISED explicitly says transcripts are blocked verbatim', () => {
  expect(lib.LOCK_UNRECOGNISED).toBe('The saved transcript setting is unrecognised, so transcripts are blocked. Save to fix it.')
})

test('EGM W: The band names the Open SocialCrawl button verbatim', () => {
  expect(HOW_IT_WORKS.find(e => e.title === 'The band')?.text).toBe('The band above the prompt shows the credits left of your session limit, or the credits counted so far when no limit is known yet. Usage sits beside it once the guard has read some. The Open SocialCrawl button opens this pane.')
})

test('EGM W: routineLines says later changes are not shown verbatim', () => {
  expect(lib.routineLines({ from: 'bad', to: 'bad', spent: 17, refused: [] })[1]).toBe('Run total at its last call: 17 cr (later changes to it are not shown)')
})

const M6_GROUPS = {
  Instagram: ['instagram'], TikTok: ['tiktok', 'tiktokshop'], YouTube: ['youtube'], LinkedIn: ['linkedin'],
  'Facebook ads': ['facebook'], Reddit: ['reddit'], Search: ['prism', 'search', 'tavily', 'perplexity', 'web'],
}

test('M6 C2: moreOf preserves runtime order, kinds, prices and verb-bearing unique keys', () => {
  const costs = {
    _platforms: { amazon: {}, web: {} }, _ignored: { range: [1, 1] },
    'GET amazon/flat': { desc: 'Get Amazon products. Extra sentence.', range: [2, 2], credits: 999 },
    'GET amazon/range': { desc: 'List Amazon reviews', range: [2, 5] },
    'GET amazon/metered': { desc: 'Fetch Amazon sellers', range: [3, 9], metered: true },
    'GET amazon/free': { desc: 'Retrieve Amazon deals', range: [0, 0] },
    'GET amazon/null': { desc: 'Get Amazon offers', range: null },
    'GET amazon/three': { desc: 'Get Amazon stock', range: [1, 2, 3] },
    'GET web/monitors': { desc: 'Get Web monitors', range: [1, 1] },
    'POST web/monitors': { desc: 'Create Web monitors', range: null },
    'GET instagram/profile': { desc: 'Short-list', range: [1, 1] },
  }
  const rows = m6.moreOf?.(costs, ['amazon', 'web', 'instagram'])
  expect(rows?.map((r: any) => [r.call, r.kind, r.price, r.metered, r.transcript])).toEqual([
    ['GET amazon/flat', 'priced', '2 cr', false, false], ['GET amazon/range', 'priced', '2–5 cr · varies', false, false],
    ['GET amazon/metered', 'priced', '3–9 cr · varies', true, false], ['GET amazon/free', 'free', 'free', false, false],
    ['GET amazon/null', 'unpriced', null, false, false], ['GET amazon/three', 'unpriced', null, false, false],
    ['GET web/monitors', 'priced', '1 cr', false, false], ['POST web/monitors', 'unpriced', null, false, false],
  ])
  expect(rows.map((r: any) => r.key)).toEqual(rows.map((r: any) => `more-${r.call.split(' ')[0].toLowerCase()}-${lib.slugOf(r.call)}`))
  expect(new Set(rows.map((r: any) => r.key)).size).toBe(8)
  expect(rows[0]).toMatchObject({ platform: 'amazon', name: 'Products' })
  expect(m6.moreOf?.(null, ['amazon'])).toEqual([])
})

test('M6 C2: callName tidies the first sentence, articles, own platform and possessive, with safe fallback', () => {
  for (const [desc, platform, want] of [
    ['Get the Instagram profile. Keep this out.', 'instagram', 'Profile'],
    ['List Instagram posts', 'instagram', 'Posts'], ['Fetch an Amazon product', 'amazon', 'Product'],
    ["Retrieve the Instagram's followers.", 'instagram', 'Followers'],
    ['Get GOOGLE NEWS headlines. More.', 'google_news', 'Headlines'],
    ['Get started in one call. More.', 'utility', 'Get started in one call'],
    ['Get Amazon products? More.', 'amazon', 'Products?'],
    ['Get Amazon', 'amazon', 'Get Amazon'], ['Get Amazon bad\u0007name', 'amazon', 'Bad name'],
  ]) expect(m6.callName?.(desc, platform)).toBe(want)
})

test('M6 C2: transcript classification mirrors the guard including normalized brief-check', () => {
  expect(m6.isTranscriptRow?.('prism//brief-check///')).toBe(true)
  expect(m6.isTranscriptRow?.('/prism/brief-check/')).toBe(true)
  for (const path of ['instagram/media/transcript', 'youtube/transcripts', 'prism/brief-check']) expect(m6.isTranscriptRow?.(path)).toBe(true)
  for (const path of ['prism/brief-check-extra', 'instagram/profile']) expect(m6.isTranscriptRow?.(path)).toBe(false)
})

test('M6 D3: shared rowPrice adds metering and option-raised ceilings while model choices stay unchanged', () => {
  expect(m6.rowPrice?.(REAL, 'GET instagram/profile/posts')).toBe('1–17 cr · varies')
  expect(m6.rowPrice?.(REAL, 'GET instagram/profile')).toBe('1 cr')
  expect(m6.rowPrice?.(REAL, 'GET web/extract')).toBe('5 cr')
  expect(m6.rowPrice?.(REAL, 'GET prism/lookup')).toBe('1–5 cr · varies')
  expect(m6.rowPrice?.({ 'GET a/b': { range: [2, 5], metered: false } }, 'GET a/b')).toBe('2–5 cr · varies')
  expect(m6.moreOf?.(REAL, ['web'])?.find((r: any) => r.call === 'GET web/extract')).toMatchObject({ price: '5 cr', metered: true })
  for (const [call, want] of [['GET google/company/ads', '5–25 cr · varies'], ['GET instagram/comment', '5–15 cr · varies'], ['GET tiktok/comment', '2–6 cr · varies']]) {
    expect(m6.rowPrice?.(REAL, call)).toBe(want)
    expect(m6.moreOf?.(REAL, [call.split(' ')[1]!.split('/')[0]])?.find((r: any) => r.call === call)?.price).toBe(want)
  }
  expect(m6.rowPrice?.({ 'GET a/b': { range: [1, 2, 3] } }, 'GET a/b')).toBeNull()
  expect(lib.choicesOf(REAL, []).find(x => x.id === 'instagram-profile-posts')?.price).toBe('1–17 cr')
  expect(lib.allowOf([]).size).toBe(29)
})

test('M6 G1: glossary exactly covers real platform ids and the supplied verbatim sentences', () => {
  const sites = m6.SITES
  expect(Object.keys(sites ?? {}).sort()).toEqual(Object.keys(REAL._platforms).sort())
  expect(sites).toEqual(M6_GLOSSARY)
  expect(Object.keys(sites)).toEqual(Object.keys(sites).sort())
  for (const [id, entry] of Object.entries(sites) as [string, any][]) {
    expect(entry.name.trim().length).toBeGreaterThan(0)
    expect(entry.line.length).toBeLessThanOrEqual(160)
    expect(entry.line).toMatch(/^[^.?!]+[.]$/)
    expect(entry.line.split(entry.name).join('')).not.toMatch(/\d/)
    expect(entry.line).not.toMatch(/\b(?:most|best|largest|leading|popular|top|biggest|world's|coach)\b/i)
    expect(m6.siteName?.(id)).toBe(entry.name)
  }
  expect(m6.siteName?.('unknown')).toBe('unknown')
})

test('M6 G2: families fold exactly, sort by display label and select only present members', () => {
  expect(m6.GROUP_PLATFORMS).toEqual(M6_GROUPS)
  const options = m6.siteOptions?.(REAL)
  expect(options?.slice(0, 2)).toEqual([{ value: '', label: 'Choose a site…' }, { value: '*', label: 'Full list' }])
  expect(options.length).toBe(63)
  expect(options.slice(2).map((o: any) => o.label)).toEqual(options.slice(2).map((o: any) => o.label).sort((a: string, b: string) => a.localeCompare(b)))
  expect(options.find((o: any) => o.value === 'google')?.label).toBe('Google (search, news, trends, shopping)')
  expect(options.find((o: any) => o.value === 'linktree')?.label).toBe('Link-in-bio pages')
  expect(m6.sitesFor?.('google', REAL)).toEqual(['google', 'google_news', 'google_trends', 'google_shopping'])
  expect(m6.sitesFor?.('linktree', REAL)).toEqual(['linktree', 'linkbio', 'linkme', 'komi', 'pillar'])
  expect(m6.sitesFor?.('tavily', REAL)).toEqual(['tavily'])
  expect(m6.sitesFor?.('', REAL)).toEqual([])
  expect(m6.sitesFor?.('*', REAL)).toEqual(Object.keys(REAL._platforms).sort((a, b) => M6_GLOSSARY[a]!.name.localeCompare(M6_GLOSSARY[b]!.name)))
  const sparse = { _platforms: { google_news: {}, amazon: {} } }
  expect(m6.sitesFor?.('google', sparse)).toEqual(['google_news'])
  expect(m6.siteOptions?.(sparse)?.map((o: any) => o.value)).toEqual(['', '*', 'amazon', 'google'])
})

test('M6 W: literal metering, lock, help and both More prompt frames are exact and safe', () => {
  expect(m6.METERED).toBe(' · varies')
  expect(m6.TRANSCRIPT_LOCKED).toBe("Transcript calls are blocked right now (see Settings), so this call can't run from here.")
  expect(m6.DEPENDS_HELP).toBe("Ask Claude for these; the pane can't price them, and the guard counts some of them at 0, so have Claude state the price first.")
  expect(HOW_IT_WORKS.length).toBe(11)
  expect(HOW_IT_WORKS[10]).toEqual({ title: 'More options', text: "Each group's More options lists the rest of its platforms' calls, and More platforms lists every other site's calls. A press asks Claude to make that one call with what is in the Target box and to ask you for anything else it needs. Calls under \"Price depends on the request\" can't run from here, and neither can transcript calls while they're blocked." })
  const row = { call: 'GET amazon/product', platform: 'amazon', name: 'Product', price: '5 cr', kind: 'priced', metered: false, transcript: false, key: 'more-get-amazon-product' }
  const head = '[SocialCrawl launcher] My pick from the Endpoints tab, priced 5 cr: make exactly one SocialCrawl call to GET amazon/product. '
  const tail = " Read what this call needs in the socialcrawl skill's reference for that platform, ask me for anything missing, then use one plain curl in the Bash tool with the API key header from the socialcrawl skill, save the reply with -o /tmp/sc-more-get-amazon-product.json, then summarise it."
  expect(m6.moreText?.(row, '  ')).toBe(head + 'The Target box is empty.' + tail)
  expect(m6.moreText?.(row, 'say "hi"\nnow')).toBe(head + 'The Target box holds "say \'hi\' now".' + tail)
  expect(m6.moreText?.(row, 'target')).not.toMatch(/http|:\/\/|curl -|socialcrawl[.]dev|[\r\n]/)
  expect(m6.moreText?.({ ...row, call: 'GET web/jobs/{job_id}', key: 'more-get-web-jobs-{job_id}' }, '')).toContain('-o /tmp/sc-more-get-web-jobs-jobid.json')
})

test('M6 W: plural and all pure grammar sites use one call or credit and retain plural after of', () => {
  expect(m6.plural?.(1, 'call')).toBe('call')
  expect(m6.plural?.(2, 'call')).toBe('calls')
  expect(m6.plural?.(2, 'person', 'people')).toBe('people')
  for (const n of [1, 2]) {
    const word = n === 1 ? 'credit' : 'credits'
    const d = lib.detailCards(n, 0, null, '', '', n, null)
    expect(d.alt).toContain(`${n} ${n === 1 ? 'call' : 'calls'} ·`)
    expect(d.source).toContain(`${n} ${n === 1 ? 'call' : 'calls'} ·`)
    expect(lib.bandDial(n, null, 'success', null).alt).toContain(`${n} ${word} counted`)
    expect(lib.bandDial(0, n, 'success', null).alt).toContain(`of ${n} credits`)
    expect(lib.summaryOf([], [], n, n, n)).toContain(`Counted: ${n} of ${n} credits.`)
    expect(lib.summaryOf([], [], n, null, n)).toContain(`Usage read from the ledger: ${n} ${word}.`)
  }
})

// Snapshot of the work order's glossary; G2's digit is allowed inside its own name.
const M6_GLOSSARY: Record<string, { name: string; line: string }> = {
  "aliexpress": {
    "name": "AliExpress",
    "line": "AliExpress product listings: look up products with prices, customer reviews, shipping fees and delivery times, hot products and promotions."
  },
  "amazon": {
    "name": "Amazon",
    "line": "Amazon products: look up a product's price and details, customer reviews, the sellers offering it, ranked category lists and current deals."
  },
  "app_store": {
    "name": "App Store",
    "line": "Apple's App Store: search apps, read an app's details and user reviews, and see the store's free, paid and grossing charts."
  },
  "apple_music": {
    "name": "Apple Music",
    "line": "Apple Music: search songs, albums and artists, look up an artist, album or track, and see a country's Apple Music charts."
  },
  "bluesky": {
    "name": "Bluesky",
    "line": "Bluesky profiles and posts: look up a user's profile and follower count, their posts, one post with its replies, or search posts by keyword."
  },
  "content_analysis": {
    "name": "Mention tracking",
    "line": "Mention tracking across the web: find news, blog, shop and forum pages that mention a keyword, with sentiment and mention volume over time."
  },
  "douyin": {
    "name": "Douyin",
    "line": "Douyin, short-form video in mainland China: search videos and creators, read video comments, and see the live hot-search board."
  },
  "ebay": {
    "name": "eBay",
    "line": "eBay listings: search listings by keyword and look up one listing's price, condition, units sold and seller."
  },
  "economy": {
    "name": "Economy",
    "line": "Spending data: household and travel spending by country, US federal spending and contract awards, and a US importer's suppliers."
  },
  "etsy": {
    "name": "Etsy",
    "line": "Etsy listings: look up a listing's price and details, the products in an Etsy shop, similar listings, and search suggestions."
  },
  "facebook": {
    "name": "Facebook",
    "line": "Facebook pages, groups and posts: look up page posts and comments, group posts, Marketplace listings, events, and ads in the Ad Library."
  },
  "finance": {
    "name": "Markets",
    "line": "Market data: look up quotes for stocks, ETFs, indices, currency and crypto pairs, plus price history, company financial statements and news."
  },
  "g2": {
    "name": "G2",
    "line": "G2 software listings: look up a software product, its written reviews, the products in a category, and the company that sells it."
  },
  "github": {
    "name": "GitHub",
    "line": "GitHub users and repositories: look up a profile, a repository's README, releases and issues, or search issues and pull requests."
  },
  "google": {
    "name": "Google",
    "line": "Google: web search results, local business profiles and their reviews, hotels, advertisers' ads, and keyword search volume by country."
  },
  "google_news": {
    "name": "Google News",
    "line": "Google News: see what is being reported about a topic, with each article's headline, outlet, link and publish time."
  },
  "google_play": {
    "name": "Google Play",
    "line": "Google Play's app store: search apps, read an app's details and user reviews, and see the store charts."
  },
  "google_shopping": {
    "name": "Google Shopping",
    "line": "Google Shopping: search products, see the sellers offering one and their prices, read reviews from several retailers, and see price history."
  },
  "google_trends": {
    "name": "Google Trends",
    "line": "Google Trends: see how search interest in keywords changes over time, related rising searches, and what a country is searching for now."
  },
  "gumtree": {
    "name": "Gumtree",
    "line": "Gumtree UK classified ads: search listings, look up an ad and its seller, and see the searches trending on Gumtree."
  },
  "hackernews": {
    "name": "Hacker News",
    "line": "Hacker News: search stories and comments, read a story's whole comment thread, and look up a user's profile."
  },
  "hm": {
    "name": "H&M",
    "line": "H&M products, stores and suppliers: search products with prices, colours and sizes, list stores in a country, and see a product's factories."
  },
  "home_depot": {
    "name": "Home Depot",
    "line": "Home Depot products: search items, look up price, stock and details, read customer reviews, and find stores near a US ZIP code."
  },
  "instagram": {
    "name": "Instagram",
    "line": "Instagram accounts and posts: look up profiles, posts and reels with likes and views, comments, followers, hashtags and trending reels."
  },
  "jobs": {
    "name": "Job listings",
    "line": "Job listings from LinkedIn, Indeed, Bing and Xing: search openings, look up one job, and see salary ranges for a job title and country."
  },
  "kick": {
    "name": "Kick",
    "line": "Kick clips: when you already have a clip's link, look up its title, views, length, category and channel."
  },
  "klarna": {
    "name": "Klarna",
    "line": "Klarna shopping: look up products, the prices different shops offer, user and expert reviews, price history and buying guides."
  },
  "kohls": {
    "name": "Kohl's",
    "line": "Kohl's products: search items with prices, read customer reviews and buyer questions, and find stores near a location."
  },
  "komi": {
    "name": "Komi",
    "line": "Komi bio-link pages: look up the links a creator lists on their Komi page, with titles, URLs and their bio."
  },
  "kwai": {
    "name": "Kwai",
    "line": "Kwai users and posts: look up a user's follower and like counts, their posts, and a post's video, views and music."
  },
  "linkbio": {
    "name": "Linkbio",
    "line": "Linkbio, a link-in-bio service: look up the links behind a creator's bio link, with titles and URLs."
  },
  "linkedin": {
    "name": "LinkedIn",
    "line": "LinkedIn members and companies: look up a person's profile and work history, company pages, posts and comments, jobs and ads."
  },
  "linkme": {
    "name": "Linkme",
    "line": "Linkme bio-link pages: look up the links a creator shows on their page, in the order they chose, with titles and URLs."
  },
  "linktree": {
    "name": "Linktree",
    "line": "Linktree pages: look up the links behind a creator's bio link, with titles and URLs, in the order the creator set them."
  },
  "naver": {
    "name": "Naver",
    "line": "Naver, Korean web search: look up its blogs, news, Q&A, community cafes, local places and Korean keyword search trends."
  },
  "on_page": {
    "name": "On-page SEO",
    "line": "On-page SEO audit: check one web page's title, meta tags, headings, HTTPS, broken links and page timing."
  },
  "perplexity": {
    "name": "Perplexity",
    "line": "Perplexity: ask a research question about the live web and get a written answer with the web pages it cited."
  },
  "pillar": {
    "name": "Pillar",
    "line": "Pillar bio-link pages: look up the links a creator lists on their Pillar page, with titles, URLs and their bio."
  },
  "pinterest": {
    "name": "Pinterest",
    "line": "Pinterest: search pins, look up a pin or a user's boards, see how often a link was saved, and see a country's Pinterest Trends."
  },
  "polymarket": {
    "name": "Polymarket",
    "line": "Polymarket prediction markets: see what people are willing to bet will happen on a topic, like whether a launch or a regulation lands."
  },
  "prism": {
    "name": "Prism (combined reports)",
    "line": "Combined reports that pull several sites into one answer, such as a brand's reputation, a product's reviews across stores, or a creator check."
  },
  "producthunt": {
    "name": "Product Hunt",
    "line": "Product Hunt's current launches: see the products it is featuring now, each with name, tagline, link and maker, narrowed by topic."
  },
  "quora": {
    "name": "Quora",
    "line": "Quora: search questions, answers, Spaces, topics and profiles by keyword."
  },
  "reddit": {
    "name": "Reddit",
    "line": "Reddit communities (subreddits): search posts and comments, read a post's full comment thread, find communities on a topic, and look up users."
  },
  "rumble": {
    "name": "Rumble",
    "line": "Rumble videos: search videos, list a channel's videos, and look up a video's views, likes and comments."
  },
  "search": {
    "name": "Social search",
    "line": "Social search: run one search across many sites at once, such as Reddit, YouTube, TikTok and Instagram, or search for creators and news."
  },
  "sephora": {
    "name": "Sephora",
    "line": "Sephora products: search items, look up price, ingredients and reviews, browse brands, and check stock at stores nearby."
  },
  "snapchat": {
    "name": "Snapchat",
    "line": "Snapchat profiles: check that a public account exists and see its display name, bio and subscriber count, plus comments on a Spotlight snap."
  },
  "spotify": {
    "name": "Spotify",
    "line": "Spotify music and podcasts: look up artists, tracks and albums, search playlists, and list a podcast's episodes."
  },
  "target": {
    "name": "Target",
    "line": "Target products: look up an item's price, rating and details, read customer reviews, browse categories, and find stores nearby."
  },
  "tavily": {
    "name": "Tavily",
    "line": "Tavily web search: search the web with an optional written answer, pull clean text from pages, and map or crawl a website."
  },
  "telegram": {
    "name": "Telegram",
    "line": "Telegram public channels and groups: look up a channel's profile and subscriber count, and its recent posts with views and reactions."
  },
  "threads": {
    "name": "Threads",
    "line": "Threads profiles and posts: look up a user's profile and recent posts, a post's replies, or search posts and users by keyword."
  },
  "tiktok": {
    "name": "TikTok",
    "line": "TikTok videos and accounts: look up profiles, videos with views and likes, comments, sounds, hashtags, trending videos and ads."
  },
  "tiktokshop": {
    "name": "TikTok Shop",
    "line": "TikTok Shop products: search products, read reviews, see a shop's products or a creator's showcase, and see units sold and estimated sales by market."
  },
  "tripadvisor": {
    "name": "TripAdvisor",
    "line": "Tripadvisor: search hotels, restaurants, attractions and cruises in a destination, and read traveler reviews of each."
  },
  "trustpilot": {
    "name": "Trustpilot",
    "line": "Trustpilot business reviews: find a company and read its customer reviews, which lean toward service, delivery, refund and support issues."
  },
  "truthsocial": {
    "name": "Truth Social",
    "line": "Truth Social profiles and posts: look up a user's profile and follower count, their recent posts, and one post's details."
  },
  "twitch": {
    "name": "Twitch",
    "line": "Twitch streamers: look up a streamer's profile, their videos and upcoming stream schedule, or one clip's details."
  },
  "twitter": {
    "name": "X (Twitter)",
    "line": "X (Twitter) accounts and posts: look up profiles, tweets and their replies, followers and communities, or search tweets and users."
  },
  "us_congress_trades": {
    "name": "US Congress trades",
    "line": "US Congress stock trades: see the trades members of Congress have disclosed, by politician, stock, party or state."
  },
  "utility": {
    "name": "Tools",
    "line": "Tools about the data service itself: list what can be looked up, find the right lookup for a task, identify a link, or explain a failed request."
  },
  "walmart": {
    "name": "Walmart",
    "line": "Walmart products: search items, look up price and details, read customer reviews, browse categories, and see every seller offering a product."
  },
  "wayfair": {
    "name": "Wayfair",
    "line": "Wayfair products: search items, look up price, stock, colour and size options and shipping estimate, and read customer reviews."
  },
  "web": {
    "name": "Web pages",
    "line": "Web pages: read a public page as clean content, search the web, list a site's pages, pull structured data from a page, or crawl a site."
  },
  "xiaohongshu": {
    "name": "Xiaohongshu (RedNote)",
    "line": "Xiaohongshu notes and creators: search notes, look up a creator and their notes, read note comments, and see the hot search board."
  },
  "yelp": {
    "name": "Yelp",
    "line": "Yelp businesses: search businesses by term and location, look up a business's rating and details, and read customer reviews."
  },
  "youtube": {
    "name": "YouTube",
    "line": "YouTube channels and videos: look up a channel, its videos and Shorts, a video's views, comments and transcript, and trending videos."
  }
}

// The pure rules beneath the status line and the paths (hooks/mod/lib.ts).
test('ageOf: just now, N min, N h up to 48 h, then days', () => {
  const MIN = 60_000
  const cases: [number, string][] = [[0, 'just now'], [59_999, 'just now'], [MIN, '1 min ago'], [59 * MIN, '59 min ago'],
    [60 * MIN, '1 h ago'], [47 * 60 * MIN + 59 * MIN, '47 h ago'], [48 * 60 * MIN, '2 days ago'], [10 * 24 * 60 * MIN, '10 days ago']]
  for (const [ms, text] of cases) expect(ageOf(ms), String(ms)).toBe(text)
})

test('spanOf: the stale warning span, with no "ago"', () => {
  expect([31 * 60_000, 3 * 3_600_000, 50 * 3_600_000].map(spanOf)).toEqual(['31 min', '3 h', '2 days'])
})

test('fmt: thousands commas', () => {
  expect([0, 999, 1000, 4210, 1234567, -1234, 1234.5].map(fmt)).toEqual(['0', '999', '1,000', '4,210', '1,234,567', '-1,234', '1,234.5'])
})

test('sidOf and revxlOf mirror the guard (G:318-320)', () => {
  expect(sidOf('a.b/c\\d e')).toBe('abcde')
  expect(sidOf(undefined)).toBe('nosession')
  expect(sidOf('')).toBe('nosession')
  expect(revxlOf('  /x  ', 'C:/h')).toBe('  /x  ')
  expect(revxlOf('   ', 'C:/h')).toBe('C:/h/.claude/revxl')
  expect(revxlOf(undefined, undefined)).toBeNull()
})

// 6a T2 (5c F-2): a reason's format and bidi characters are blanked too, as control and line-separator ones are.
test('T2 whyOf: zero-width, bidi override and isolate, BOM, BEL and U+2028 each become a space', () => {
  expect(whyOf('a\u200bb\u202ec\u2066d\ufeffe\u0007f\u2028g')).toBe('a b c d e f g')
})

// T3/T5: the cards and dial keep thousands separators in their accessible words.
test('T3 session and detail card alt: spending, counted calls, refusals and balance', () => {
  expect(sessionCard(1200, 2000, 'success').alt).toBe('This session: 1,200 of 2,000 cr counted. 800 cr left before the limit.')
  expect(detailCards(12, 2, 4210, '2 min ago', 'not checked yet', null, null).alt).toBe("Usage: none read yet. 12 calls · 2 refused on record. Account balance: 4,210 cr, checked 2 min ago.")
})

test('T5 bandDial alt: 800 of 2,000 credits left this session; Usage: none read yet', () => {
  expect(bandDial(1200, 2000, 'success', null).alt).toBe('800 of 2,000 credits left this session; Usage: none read yet')
})

test('call readers pass over settle, unknown and missing decisions to the newest guard call', () => {
  expect(CALL_DECISIONS).toEqual(['pass', 'deny', 'allow'])
  const call = { sid: 'sid', ts: '2026-10-15T12:00:00Z', paths: ['/v1/instagram/profile'], decision: 'pass', committed: 120, worst: 1, limit: 500 }
  const denied = { ...call, decision: 'deny', kind: 'over-limit' }
  const line = (o: unknown) => JSON.stringify(o) + '\n'
  const skipped = [ { sid: 'sid', decision: 'settle', paths: ['SETTLE'], limit: 9 }, { sid: 'sid', decision: 'future', paths: ['UNKNOWN'] }, { sid: 'sid' } ]
  for (const r of skipped) expect(isCall(r)).toBe(false)
  expect(isCall({ decision: 'allow' })).toBe(true)
  for (const last of [call, denied]) {
    const original = line(call) + line(last)
    const record = original + skipped.map(line).join('')
    expect(newestFor(record, 'sid')).toEqual(last)
    expect(recordLimit(newestFor(record, 'sid'))).toBe(500)
    expect(bandOf(120, 500, newestFor(record, 'sid'))).toEqual(bandOf(120, 500, last))
    expect(callRows(record, 'sid')).toEqual(callRows(original, 'sid'))
    expect(JSON.stringify(callRows(record, 'sid'))).not.toContain('SETTLE')
    expect(JSON.stringify(callRows(record, 'sid'))).not.toContain('UNKNOWN')
    expect(pathsFor(record, 'sid')).toEqual(pathsFor(original, 'sid'))
    expect(JSON.stringify(callRows(record, 'sid'))).not.toContain('undefined')
  }
  expect(recordLimit(skipped[0]!)).toBeNull()
  const routine = { ...call, sid: 'routine', routine: true }
  const original = line(routine)
  const settled = { ...routine, decision: 'settle', ts: '2026-10-15T12:05:00Z' }
  expect(lastRoutine(original + line(settled), 'sid')).toEqual({ from: routine.ts, to: routine.ts, spent: 120, refused: [] })
  expect(lastRoutine(original + line({ sid: 'future-routine', routine: true, decision: 'settle' }) + line({ ...routine, decision: 'unknown', committed: 999 }), 'sid')).toEqual(lastRoutine(original, 'sid'))
  expect(newestFor(skipped.map(line).join(''), 'sid')).toBeNull()
})

test('H-32: allow from 706f39d is counted by every call reader, never refused', () => {
  const call = { sid: 's', ts: '2026-10-15T12:00:00Z', paths: ['/v1/instagram/profile'], decision: 'allow', worst: 1, committed: 120, limit: 500 }
  const routine = { ...call, sid: 'r', routine: true }
  const record = [call, routine].map(x => JSON.stringify(x)).join('\n')
  expect(newestFor(record, 's')).toEqual(call)
  expect(recordLimit(newestFor(record, 's'))).toBe(500)
  expect(callRows(record, 's').paid.length).toBe(1)
  expect(callRows(record, 's').refused).toEqual([])
  expect(pathsFor(record, 's')).toEqual(call.paths)
  expect(lastRoutine(record, 's')).toEqual({ from: routine.ts, to: routine.ts, spent: 120, refused: [] })
  expect(bandOf(120, 500, call).tone).toBe('success')
})

test('storedLock mirrors the guard, without treating malformed values as unset', () => {
  expect(storedLock({}, false)).toBe('unset')
  expect(storedLock({ transcripts: 'block' }, false)).toBe('block')
  expect(storedLock({ transcripts: 'allow' }, false)).toBe('allow')
  for (const transcripts of ['nope', 'ALLOW', 'allow ', true, 1, null, undefined, {}, []]) expect(storedLock({ transcripts }, false)).toBe('unrecognised')
  for (const transcripts of ['allow', 'block', undefined]) expect(storedLock({ transcripts }, true)).toBe('unreadable')
})

test('lockPick and lockToSend: the full stored, pressed and routes table', () => {
  const kinds = ['block', 'allow', 'unset', 'unrecognised', 'unreadable'] as const
  // Rows are block, allow, unset, unrecognised, unreadable. Columns are no press, Blocked, Allowed.
  const noRoutePicks: Lock[][] = [['block', 'block', 'allow'], ['allow', 'block', 'allow'], ['allow', 'block', 'allow'], ['block', 'block', 'allow'], ['block', 'block', 'allow']]
  const noRouteSends: (Lock | undefined)[][] = [[undefined, undefined, 'allow'], [undefined, 'block', undefined], [undefined, 'block', 'allow'], ['block', 'block', 'allow'], [undefined, 'block', 'allow']]
  for (const routes of [null, [], ['yt-dlp']]) for (const [i, stored] of kinds.entries()) {
    for (const [j, pressed] of ([undefined, 'block', 'allow'] as const).entries()) {
      const preselected = stored === 'unset' && !!routes?.length && pressed === undefined
      expect(lockPick(pressed, stored, routes)).toBe(preselected ? 'block' : noRoutePicks[i]![j])
      expect(lockToSend(pressed, stored, routes)).toBe(preselected ? 'block' : noRouteSends[i]![j])
    }
  }
})

test('parseRoutes accepts one successful line and keeps only known labels in fixed order', () => {
  const line = (routes: unknown, ok: unknown = true) => JSON.stringify({ ok, routes }) + '\n'
  expect(parseRoutes(0, line(['groq', 'yt-dlp', 'unknown', 'groq', 'whisper', 7]))).toEqual(['yt-dlp', 'whisper', 'groq'])
  expect(parseRoutes(0, line(['unknown']))).toEqual([])
  expect(parseRoutes(0, line([]))).toEqual([])
  for (const s of ['', 'nope', 'null', '{}', line('yt-dlp'), line([], false), line([], 1), line([]) + line([])]) expect(parseRoutes(0, s)).toBeNull()
  expect(parseRoutes(1, line(['yt-dlp']))).toBeNull()
})

test('customOf accepts digits or grouped thousands with outer spaces', () => {
  for (const [text, want] of [['1', 1], ['20,000', 20000], [' 1,234 ', 1234]] as const) expect(customOf(text)).toBe(want)
  for (const text of ['0', '20001', '12.5', 'abc', '', ' ', '1e3', '0x10', '-1', '+1', 'Infinity', '1 234']) expect(customOf(text)).toBeNull()
})

test('styleOf uses exact literal names and otherwise defaults to Lantern rows', () => {
  for (const x of STYLES) expect(styleOf(x)).toBe(x)
  for (const x of [undefined, null, 7, 'chips', 'Cards ', {}, []]) expect(styleOf(x)).toBe('Lantern rows')
})

test('changesOf is the single ordered save argument; holds checks every key sent', () => {
  const saved = { session: 250 }
  expect(changesOf(saved, saved, false)).toBeNull()
  expect(changesOf(saved, saved, false, 'block')).toEqual({ transcripts: 'block' })
  expect(JSON.stringify(changesOf({ session: 500 }, saved, false, 'allow'))).toBe('{"sessionBudget":500,"transcripts":"allow"}')
  expect(changesOf(saved, saved, true)).toEqual({ sessionBudget: 250 })
  expect(holds({ sessionBudget: 250, transcripts: 'block', other: 1 }, { transcripts: 'block' })).toBe(true)
  expect(holds({ transcripts: 'allow' }, { transcripts: 'block' })).toBe(false)
  expect(holds({}, { sessionBudget: null })).toBe(true)
  expect(holds({ sessionBudget: 250 }, { sessionBudget: null })).toBe(false)
  expect(holds({ sessionBudget: 500, transcripts: 'allow' }, { sessionBudget: 500, transcripts: 'allow' })).toBe(true)
  expect(holds({ sessionBudget: 250, transcripts: 'allow' }, { sessionBudget: 500, transcripts: 'allow' })).toBe(false)
})

test('HOW_IT_WORKS: exact titles and wording in order', () => {
  expect(HOW_IT_WORKS.map(x => [x.title, x.text])).toEqual([
    ['The band', "The band above the prompt shows the credits left of your session limit, or the credits counted so far when no limit is known yet. Usage sits beside it once the guard has read some. The Open SocialCrawl button opens this pane."],
    ['What the limit counts', "Before a call runs the guard holds its counted price against the session total, and a call the guard refuses holds nothing. Usage is what SocialCrawl's ledger shows charged on the endpoints this session called while those calls were open, so it can include other spending on the account."],
    ['When credits come back', "No sooner than about two minutes after a call returns, and only once the ledger shows a charge on that endpoint this session, the guard can swap a finished call's hold for what was charged; until then the band can read high, a call with no charge there keeps its hold until one appears, and a ledger read can also push the total up. A call that fails, is interrupted, runs in the background, or is piped or chained keeps its hold and can count its hold and its charge together for the rest of the session; nothing comes back without a key, or after three failed ledger reads in a row. A charge the vendor records more than about 2 minutes after its call returns can be counted late, or not at all, so the band can also read low."],
    ['Endpoints', 'Fill the Target box with the handle, link or search phrase the call needs, then press a call. Your priced pick goes into the chat as your own message.'],
    ['Combos', 'Research packages of one or more calls. A press asks Claude to ask you for what it needs and to show the price before it runs.'],
    ['Suggested', "A few picks based on your brand notes, your last few prompts and this session's calls. After you first open this tab it refreshes as the session goes on, and each refresh is one small model call that reads them."],
    ['Round-up', "This session's calls and the files they saved. Summarize asks Claude to write up what was pulled and to make no new calls."],
    ['Session credit limit', "The most a new call may take the session's total to: the holds still counted plus Usage. A call whose counted price would take the total past it is refused before it runs, and if a ledger read lifts the total past it, every call the guard counts above 0 is refused."],
    ['Transcript endpoints', "Blocked refuses transcript calls before they run, and the guard refuses any call whose address is written in an odd encoding. Allowed lets them run and counts a single transcript at one unit's price, a floor, so one that bills many units is counted low; a batch is counted at its ceiling."],
    ['Appearance', 'How the buttons on Endpoints, Combos and Suggested are drawn. It changes nothing about what they do or cost.'],
    ['More options', "Each group's More options lists the rest of its platforms' calls, and More platforms lists every other site's calls. A press asks Claude to make that one call with what is in the Target box and to ask you for anything else it needs. Calls under \"Price depends on the request\" can't run from here, and neither can transcript calls while they're blocked."],
  ])
})

test('HOW_IT_WORKS: eleven entries with pinned sentence counts and no draft field', () => {
  expect(HOW_IT_WORKS.map(x => x.title)).toEqual(['The band', 'What the limit counts', 'When credits come back', 'Endpoints', 'Combos', 'Suggested', 'Round-up', 'Session credit limit', 'Transcript endpoints', 'Appearance', 'More options'])
  expect(HOW_IT_WORKS.every(x => !Object.prototype.hasOwnProperty.call(x, 'draft'))).toBe(true)
  for (const x of HOW_IT_WORKS) {
    expect([2, 3]).toContain(x.text.split('. ').length)
    expect(x.text.endsWith('.')).toBe(true)
    expect(JSON.stringify(x)).not.toMatch(/coach|\/\w/i)
  }
})

// Pass A keeps the older wording tests above intact; Pass B reconciles them.
test('Mfix X4: every frozen wording literal and the three revised help entries', async ($, on) => {
  const future = lib as any // Missing exports must fail assertions, never module loading.
  const pins: [unknown, unknown][] = [
    [lib.SESSION_HELP, "The most one session, or one run with no person at the prompt, may spend, as the guard counts it. Automatic = a quarter of your account balance as the guard first read it this session, up to 500; 500 while the guard has no balance it can use."],
    [lib.sessionCard(0, null, 'success').source.includes(lib.esc("Automatic cap: a quarter of your account balance as the guard first read it this session, up to 500; 500 while the guard has no balance it can use")), true],
    [lib.belowSpent(1234), '⚠ This session has already counted 1,234 cr; a limit this low stops further counted calls in this session.'],
    [lib.aboveBalance(4210), '⚠ This is above your 4,210 cr balance.'],
    [lib.toastOf({ paths: ['instagram/profile'], worst: 31, committed: 121, limit: 500 }), 'SocialCrawl: instagram/profile · counted 31 cr · 121 / 500 cr this session'],
    [lib.toastOf({ paths: ['instagram/profile'], worst: 31, committed: 121, limit: null }), 'SocialCrawl: instagram/profile · counted 31 cr · 121 cr this session'],
    [lib.callRows('{"sid":"s","ts":"bad","paths":["/v1/instagram/profile"],"decision":"pass","worst":31}\n', 's').paid, ['--:-- · instagram/profile · counted 31 cr']],
    [lib.QUOTES_NOTE, "Each row shows what the guard counted before the call ran. Usage is what the guard has read back from SocialCrawl's ledger."],
    [lib.notSaved('invalid'), 'Not saved: the helper refused that choice. Pick again and press Save.'],
    [lib.notSaved('write'), "Not saved: the settings file couldn't be written. Press Save again."],
    [lib.notSaved('readback'), "Not saved: the settings file didn't read back as chosen. Press Save again."],
    [lib.notSaved('helper'), "Not saved: the save helper didn't give a usable answer. Press Save again."],
    [lib.notSaved('weird'), 'Not saved. Press Save again.'],
    [lib.SAVE_BUSY, 'Settings are being saved in another window. Press Save again.'],
    [lib.GARBLED, "The settings file couldn't be read; saving will replace it."],
    [lib.READ_ERROR, "The settings file couldn't be read just now. Close and reopen this pane to try again."],
    [future.READ_ERROR_LOCKED, "The limit and the transcript setting can't be changed here until it can be read."],
    [future.NOTHING_TO_SAVE, 'Nothing to save: the file already holds this.'],
    [future.PRESS_SET_FIRST, 'Press set beside the Custom box first, then Save.'],
    [future.SAVING, 'Saving…'],
    [lib.LOCK_HELP, "Paid transcripts cost far more than free captions. Blocked stops them before they run; Allowed lets them run and counts a single transcript at one unit's price, a floor, so one that bills many units is counted low; a batch is counted at its ceiling."],
    [lib.CUSTOM_BAD, 'A custom limit is a whole number from 1 to 20,000.'],
    [lib.LOCK_UNRECOGNISED, "The saved transcript setting is unrecognised, so transcripts are blocked. Save to fix it."],
    [lib.APPEARANCE_HELP, 'How the Endpoints, Combos and Suggested buttons are drawn. Changes at once; no Save needed.'],
    [lib.routesFound(['yt-dlp', 'whisper']), 'Found on this computer: yt-dlp, whisper'],
    [lib.routesFound(['yt-dlp', 'whisper', 'groq']), 'Found on this computer: yt-dlp, whisper; a Groq key is set'],
    [lib.routesFound(['groq']), 'A Groq key is set'],
    [lib.routesFound([]), 'No free transcript tool found on this computer'],
    [future.lockPreselected?.(['yt-dlp']), 'Not saved yet, so paid transcripts still run until you press Save. Blocked is picked for you because a transcript tool was found on this computer.'],
    [future.lockPreselected?.(['groq']), 'Not saved yet, so paid transcripts still run until you press Save. Blocked is picked for you because a Groq key is set.'],
    [future.LOCK_PRESELECTED, undefined],
    [lib.needOf('handle', false), 'This call needs a handle, like @name in the Target box.'],
    [lib.needOf('handle', true), 'This call needs a handle, like @name in the Target box. Fill it on your computer first.'],
    [future.TYPE_ON_DESKTOP, undefined],
    [future.NO_PRICE, "This call has no listed price, so it can't be run from here."],
    [future.NOT_OPENED, undefined],
    [future.balanceState?.(null), 'not checked yet'],
    [future.balanceState?.('no-key'), 'no usable SocialCrawl key found'],
    [future.balanceState?.('network'), 'last check failed'],
    [future.PANE_FAILED, "SocialCrawl couldn't draw this pane. Close and reopen it."],
    [lib.HOW_IT_WORKS.find(x => x.title === 'Combos')?.text, 'Research packages of one or more calls. A press asks Claude to ask you for what it needs and to show the price before it runs.'],
    [lib.HOW_IT_WORKS.find(x => x.title === 'Suggested')?.text, "A few picks based on your brand notes, your last few prompts and this session's calls. After you first open this tab it refreshes as the session goes on, and each refresh is one small model call that reads them."],
    [lib.HOW_IT_WORKS.find(x => x.title === 'Round-up')?.text, "This session's calls and the files they saved. Summarize asks Claude to write up what was pulled and to make no new calls."],
  ]
  const refusals: [unknown, string, string][] = [
    ['over-limit', 'over the limit', 'over the limit. Raise the limit in Settings to go further (20,000 is the highest).'],
    ['transcript-locked', 'transcripts blocked', 'transcripts blocked. Change this in Settings.'],
    ['not-plain', 'not one plain call', 'not one plain call. Ask Claude to run it as one plain call.'],
    ['lost', 'session total lost', 'session total lost. Start a new session to continue.'],
    ['error', 'guard could not read or save its files', "guard could not read or save its files. Try the call again; if it keeps happening, ask Claude to check the guard's session and settings files."],
    ['weird', 'refused by the guard', 'refused by the guard.'],
    [undefined, 'refused by the guard', 'refused by the guard.'],
  ]
  for (const [kind, short, full] of refusals) {
    pins.push([future.refusalShort?.(kind), short], [future.refusalOf?.(kind), full])
    const record = { sid: 's', ts: 'bad', paths: ['instagram/profile'], decision: 'deny', kind }
    pins.push([lib.bandOf(0, 500, record).warn, ` · ⚠ last call refused: ${short}`])
    pins.push([lib.callRows(JSON.stringify(record) + '\n', 's').refused, [`--:-- · instagram/profile · refused: ${full}`]])
  }
  pins.push([lib.routineLines({ from: 'bad', to: 'bad', spent: 0, refused: [['lost', 2], ['weird', 1]] })[2], 'Refused: 2 session total lost, 1 refused by the guard'])
  pins.push([lib.routineLines({ from: 'bad', to: 'bad', spent: 0, refused: [] })[2], 'Refused: none'])
  expect(pins.map(([actual]) => actual)).toEqual(pins.map(([, literal]) => literal))

  // R-only wording has no L export. Pin those literals through the same in-memory engine API as MT.
  mock.clock(on, { now: Date.UTC(2026, 9, 15, 12) })
  mock.store(on)
  const root = 'C:/Users/t/.claude/revxl'
  const files: Record<string, string> = {
    [`${root}/socialcrawl-budget.json`]: '{}',
    [`${root}/socialcrawl-calls.jsonl`]: '{"sid":"s","decision":"pass","paths":[],"limit":null,"worst":1}\n' +
      '{"sid":"s","decision":"deny","kind":"lost","paths":[],"limit":null}\n',
  }
  on('env.get', (_: any, e: any) => ({ value: e.name === 'USERPROFILE' ? 'C:/Users/t' : undefined }))
  on('session.id', () => ({ value: 's' }))
  on('fs.read', (_: any, e: any) => {
    const text = files[e.path.replace(/\\/g, '/')]
    return text === undefined ? { deny: 'ENOENT' } : { value: e.as === 'bytes' ? { base64: btoa(String.fromCharCode(...new TextEncoder().encode(text))) } : text }
  })
  on('fs.exists', () => ({ value: false }))
  on('ui.invalidate', (_: any, e: any, next: any) => next(e))
  const mount = (surface: 'terminal' | 'mobile') => $.ui.mount({ plugin: 'socialcrawl-superengine', surface, component: 'Pane', requestId: 'sc-pane',
    props: { title: 'SocialCrawl', isFocused: true, bodyColumns: 100, placement: 'inline', scroll: { offset: 0, bodyRows: 40 }, view: {} } as any })
  const terminal = await mount('terminal')
  const drawn = async (ui: any) => (await ui.findAll({ type: 'Text' })).map((x: any) => x.text)
  expect(await drawn(terminal)).toContain("Automatic cap: a quarter of your account balance as the guard first read it this session, up to 500; 500 while the guard has no balance it can use")
  expect(await drawn(terminal)).toContain('1 call · 1 refused on record')
  const mobile = await mount('mobile')
  expect(await drawn(mobile)).toContain('No target yet. Fill the Target box on your computer.')
  await terminal.input({ key: 'target', text: '@nike' })
  await mobile.press({ key: 'tab-Endpoints' })
  expect(await drawn(mobile)).toContain('Target: @nike')
  await terminal.press({ key: 'tab-Round-up' })
  expect(await drawn(terminal)).toContain('Refused on record, not counted')
  await terminal.unmount()
  await mobile.unmount()
})

test('Mfix MINORs: customOf rejects malformed separators and accepts grouped thousands', () => {
  expect(['1,5', '12,34', '1 5', '1,234', ' 20,000 '].map(lib.customOf)).toEqual([null, null, null, 1234, 20000])
})

// M3: optional access keeps missing Pass B exports from turning red assertions into load errors.
const m3Settle = (o: Record<string, unknown> = {}) => JSON.stringify({ ts: '2026-10-15T12:00:00Z', sid: 'sid-1',
  decision: 'settle', kind: 'give-back', usage: 1, committed: 1, was: 17, full: 0, over: [], ...o }) + '\n'

test('M3 U1: settleFor picks newest valid own give-back, skipping malformed and unrelated lines', () => {
  const read = (text: string) => (lib as any).settleFor?.(text, 'sid-1')
  const older = m3Settle({ usage: 9, committed: 9, was: 20 })
  const newest = m3Settle({ usage: 1.5, committed: 2.5, was: 17.5 })
  const skipped = [m3Settle({ sid: 'sid-2', usage: 40 }), m3Settle({ kind: 'another-kind' }), m3Settle({ decision: 'pass' }),
    ...['usage', 'committed', 'was'].flatMap(key => ['1', -1, null, true, undefined].map(value => m3Settle({ [key]: value }))),
    ...['usage', 'committed', 'was'].map(key => m3Settle({ [key]: 1 }).replace(`"${key}":1`, `"${key}":1e400`)),
    'not json\n', '{"sid":"sid-1","decision":"settle"']
  expect(skipped.map(tail => read(older + newest + tail))).toEqual(skipped.map(() => ({ usage: 1.5, committed: 2.5, was: 17.5 })))
  expect(read(newest + older)).toEqual({ usage: 9, committed: 9, was: 20 })
  expect(read(m3Settle({ usage: 0, committed: 0, was: 0 }))).toEqual({ usage: 0, committed: 0, was: 0 })
  expect(read(m3Settle({ usage: 20, committed: 20, was: 17 }))).toEqual({ usage: 20, committed: 20, was: 17 })
  // Valid settlement records have no paths or limit, and remain invisible to every call reader.
  const call = '{"sid":"sid-1","decision":"pass","paths":["instagram/profile"],"worst":1,"limit":500}\n'
  expect(lib.CALL_DECISIONS).toEqual(['pass', 'deny', 'allow'])
  expect(lib.isCall(JSON.parse(newest))).toBe(false)
  expect(lib.newestFor(call + newest, 'sid-1')).toEqual(JSON.parse(call))
  expect(lib.callRows(call + newest, 'sid-1')).toEqual(lib.callRows(call, 'sid-1'))
})

test('M3 U1: settleFor returns null with no valid own settlement', () => {
  const texts = ['', '{}\nnull\n[]\n', m3Settle({ sid: 'sid-2' }), m3Settle({ kind: 'other' }),
    m3Settle({ usage: -1 }), '{"sid":"sid-1","decision":"settle"']
  expect(texts.map(t => (lib as any).settleFor?.(t, 'sid-1'))).toEqual(texts.map(() => null))
})

test('M3 U1: positive state Usage is known without a settlement', () => {
  expect((lib as any).usageFor?.('{"usage":12}', null)).toBe(12)
})

test('M3 U1: zero or missing state Usage stays unknown without a settlement', () => {
  expect([null, '{}', '{"usage":0}', '{"usage":-1}', '{"usage":"12"}', '{"usage":1e400}'].map(t => (lib as any).usageFor?.(t, null))).toEqual([null, null, null, null, null, null])
})

test('M3 U1: zero state Usage is known with an own settlement', () => {
  expect((lib as any).usageFor?.('{"usage":0}', { usage: 3, committed: 17, was: 20 })).toBe(0)
})

test('M3 U1: usageFor prefers finite nonnegative state usage and falls back to the settlement', () => {
  const settlement = { usage: 3, committed: 17, was: 20 }
  const states = ['{"usage":12}', '{"usage":0}', '{"usage":1.5}', null, '{}', '{', 'null', '[]',
    '{"usage":"12"}', '{"usage":-1}', '{"usage":null}', '{"usage":1e400}']
  expect(states.map(t => (lib as any).usageFor?.(t, settlement))).toEqual([12, 0, 1.5, 3, 3, 3, 3, 3, 3, 3, 3, 3])
})

test('M3 U1: fullOf accepts only a nonnegative whole state count', () => {
  const states = ['{"full":0}', '{"full":2}', null, '{}', '{', 'null', '[]', '{"full":-1}',
    '{"full":1.5}', '{"full":"2"}', '{"full":null}', '{"full":1e400}']
  expect(states.map(t => (lib as any).fullOf?.(t))).toEqual([0, 2, null, null, null, null, null, null, null, null, null, null])
})

test('M3 U1: usageWords distinguishes unknown from zero and formats credits', () => {
  expect([null, 0, 1, 1234.5].map(n => (lib as any).usageWords?.(n))).toEqual(['Usage: none read yet', 'Usage 0 cr', 'Usage 1 cr', 'Usage 1,234.5 cr'])
})

const M3_HELP = [
  { title: 'The band', text: "The band above the prompt shows the credits left of your session limit, or the credits counted so far when no limit is known yet. Usage sits beside it once the guard has read some. The Open SocialCrawl button opens this pane." },
  { title: 'What the limit counts', text: "Before a call runs the guard holds its counted price against the session total, and a call the guard refuses holds nothing. Usage is what SocialCrawl's ledger shows charged on the endpoints this session called while those calls were open, so it can include other spending on the account." },
  { title: 'When credits come back', text: "No sooner than about two minutes after a call returns, and only once the ledger shows a charge on that endpoint this session, the guard can swap a finished call's hold for what was charged; until then the band can read high, a call with no charge there keeps its hold until one appears, and a ledger read can also push the total up. A call that fails, is interrupted, runs in the background, or is piped or chained keeps its hold and can count its hold and its charge together for the rest of the session; nothing comes back without a key, or after three failed ledger reads in a row. A charge the vendor records more than about 2 minutes after its call returns can be counted late, or not at all, so the band can also read low." },
  { title: 'Endpoints', text: 'Fill the Target box with the handle, link or search phrase the call needs, then press a call. Your priced pick goes into the chat as your own message.' },
  { title: 'Combos', text: 'Research packages of one or more calls. A press asks Claude to ask you for what it needs and to show the price before it runs.' },
  { title: 'Suggested', text: "A few picks based on your brand notes, your last few prompts and this session's calls. After you first open this tab it refreshes as the session goes on, and each refresh is one small model call that reads them." },
  { title: 'Round-up', text: "This session's calls and the files they saved. Summarize asks Claude to write up what was pulled and to make no new calls." },
  { title: 'Session credit limit', text: "The most a new call may take the session's total to: the holds still counted plus Usage. A call whose counted price would take the total past it is refused before it runs, and if a ledger read lifts the total past it, every call the guard counts above 0 is refused." },
  { title: 'Transcript endpoints', text: "Blocked refuses transcript calls before they run, and the guard refuses any call whose address is written in an odd encoding. Allowed lets them run and counts a single transcript at one unit's price, a floor, so one that bills many units is counted low; a batch is counted at its ceiling." },
  { title: 'Appearance', text: 'How the buttons on Endpoints, Combos and Suggested are drawn. It changes nothing about what they do or cost.' },
  { title: 'More options', text: "Each group's More options lists the rest of its platforms' calls, and More platforms lists every other site's calls. A press asks Claude to make that one call with what is in the Target box and to ask you for anything else it needs. Calls under \"Price depends on the request\" can't run from here, and neither can transcript calls while they're blocked." },
]

test('M3 W: all eleven How it works pairs are literal and have no draft field', () => {
  expect(lib.HOW_IT_WORKS).toEqual(M3_HELP)
  expect(lib.HOW_IT_WORKS.every(x => !Object.prototype.hasOwnProperty.call(x, 'draft'))).toBe(true)
  for (const x of lib.HOW_IT_WORKS) {
    expect([2, 3]).toContain(x.text.split('. ').length)
    expect(x.text.endsWith('.')).toBe(true)
  }
})

test('M3 W: Usage lines, counted routine, automatic band and call count wording are literal', () => {
  const future = lib as any
  const pins = [
    [future.USAGE_LINE?.(1234.5), 'Usage: 1,234.5 cr read from the ledger so far'],
    [future.USAGE_LINE?.(null), 'Usage: none read yet'],
    [future.USAGE_LINE?.(0), 'Usage: 0 cr read from the ledger so far'],
    [lib.QUOTES_NOTE, "Each row shows what the guard counted before the call ran. Usage is what the guard has read back from SocialCrawl's ledger."],
    [lib.routineLines({ from: 'bad', to: 'bad', spent: 17, refused: [] })[1], 'Run total at its last call: 17 cr (later changes to it are not shown)'],
    [lib.bandOf(17, null, null).text, '17 cr counted this session · automatic cap'],
  ]
  expect(pins.map(([actual]) => actual)).toEqual(pins.map(([, literal]) => literal))
})

test('M3 W: session help, refusals, save error, key, locked read, tokens and warning literals', () => {
  const future = lib as any
  const pins = [
    [lib.SESSION_HELP, "The most one session, or one run with no person at the prompt, may spend, as the guard counts it. Automatic = a quarter of your account balance as the guard first read it this session, up to 500; 500 while the guard has no balance it can use."],
    [lib.refusalOf('over-limit'), 'over the limit. Raise the limit in Settings to go further (20,000 is the highest).'],
    [lib.refusalOf('error'), "guard could not read or save its files. Try the call again; if it keeps happening, ask Claude to check the guard's session and settings files."],
    [lib.notSaved('helper'), "Not saved: the save helper didn't give a usable answer. Press Save again."],
    [lib.balanceState('no-key'), 'no usable SocialCrawl key found'],
    [future.READ_ERROR_LOCKED, "The limit and the transcript setting can't be changed here until it can be read."],
    [lib.tokensLine(1234), 'Suggestions used 1,234 model tokens this session (not credits)'],
    [lib.statusOf({ balance: 300, at: 0 }, null, 0, { sessionBudget: 500 }), 'SC Total Balance: 300 cr (just now) · ⚠ your 500 cr limit is above it'],
  ]
  expect(pins.map(([actual]) => actual)).toEqual(pins.map(([, literal]) => literal))
})

const M3_NEEDS: [string, string][] = [['handle', 'a handle, like @name'], ['channel', 'a channel link or handle'],
  ['company', 'a company name or page id'], ['ad', 'an ad link or ad id'], ['urls', 'one or more post links'],
  ['query', 'a search phrase'], ['url', 'a link'], ['none', 'a target'], ['other', 'a target']]
for (const mobile of [false, true]) test(`M3 W: needOf names every target kind on ${mobile ? 'mobile' : 'desktop'}`, () => {
  expect(M3_NEEDS.map(([kind]) => (lib as any).needOf?.(kind, mobile))).toEqual(
    M3_NEEDS.map(([, what]) => `This call needs ${what} in the Target box.${mobile ? ' Fill it on your computer first.' : ''}`))
  expect((lib as any).NEED_TARGET).toBeUndefined()
  expect((lib as any).NEED_TARGET_MOBILE).toBeUndefined()
})

test('M3 W: Target hint literal explains region-code fallback', () => {
  expect((lib as any).TARGET_HINT).toBe('What goes here depends on the call: a handle, a link, a search phrase or a company name. A call that wants a region code reads this box as one and uses US when it is empty.')
})

for (const usage of [null, 1]) test(`M3 U7: summaryOf exact total sentence with Usage ${usage}`, () => {
  const summarize = lib.summaryOf as any // Pass A's source still has four parameters.
  const suffix = usage === null ? 'No Usage read yet.' : 'Usage read from the ledger: 1 credit.'
  for (const limit of [500, null]) {
    const text = summarize(['12:00 · instagram/profile · counted 1 cr', 'perplexity/research'], ['C:/x/ok.json', 'https://example.com/x'], 17, limit, usage)
    expect(text.endsWith(`Counted: 17 of ${limit === null ? 'automatic cap' : '500'} credits. ${suffix}`)).toBe(true)
    expect(lib.UNSAFE.some(re => re.test(text) || re.test(text.toLowerCase()))).toBe(false)
    expect(text).toContain('(1 more not listed here.)')
  }
})
