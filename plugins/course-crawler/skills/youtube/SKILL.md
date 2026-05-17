---
name: youtube
description: Capture content from YouTube ... a single video, an entire playlist, or all the videos on a channel. Use this skill whenever the user mentions a YouTube URL, transcripts, playlist scraping, "YouTube course", "this YouTuber", "video series", or wants to harvest content from a YouTube creator. Asks the user what they actually want (just transcripts? + slide frames extracted from the videos? + the video files themselves? + video descriptions and chapter markers?) rather than assuming, then runs the matching pipeline using yt-dlp, ffmpeg scene-detection, and Whisper. Works on private/unlisted YouTube videos too if the user is logged in (cookies via /login on youtube.com first). Use even with informal phrasing ... "get the transcripts for this playlist", "transcribe these videos", "I want everything from this channel".
---

# Capture YouTube content

YouTube is special enough to warrant its own skill: it has native captions on most videos (cheaper than Whisper), it has playlists/channels (so the scope is variable), and the user almost never wants the same combination of outputs twice.

## Prerequisites

- `/setup` has run.
- For private or unlisted videos: `/login` against `youtube.com` first.

## Step 1: Identify the input scope

Look at the URL the user provided:

| URL pattern | Scope |
|-------------|-------|
| `youtube.com/watch?v=<id>` or `youtu.be/<id>` | Single video |
| `youtube.com/playlist?list=<id>` | Whole playlist |
| `youtube.com/@handle/videos` or `youtube.com/channel/<id>` | Whole channel (could be huge) |
| `youtube.com/@handle/playlists` | Multiple playlists (pick one) |

If it's a channel, ask: "This channel has <N> videos. Do you want all of them, or a specific playlist? Channels can be hundreds of hours of audio."

## Step 2: Ask what the user actually wants

Don't assume. Offer a clear menu:

> What do you want from this?
>
> 1. **Transcripts only** ... text-only, fastest, smallest disk footprint. Good for searchable archives or feeding into AI for protocols/summaries.
> 2. **Transcripts + slide frames** ... adds unique slide images via scene detection. Good for tutorials/courses with visual content.
> 3. **Full preservation** ... videos + transcripts + slides + descriptions + chapter markers. Maximum data, biggest disk usage.
> 4. **Custom** ... pick exactly which pieces you want.

Wait for their choice. Confirm scope (number of videos) and rough disk budget if option 3 or large playlists.

## Step 3: Run the pipeline

The bundled `scripts/youtube_pull.py` takes the URL + the options dict and does the right thing. Invoke it from the venv:

```bash
~/.iss/venv/bin/python ${CLAUDE_SKILL_DIR}/../scripts/youtube_pull.py \
  "<url>" \
  --out "./scraped/<topic-slug>/" \
  --want transcript,slides,video,description       # comma-separated; subset of these
```

Output convention is the same as the rest of the plugin:

```
./scraped/<topic-slug>/
├── written/        ... description.md + chapters.json per video
├── visual/         ... slide frames per video
├── video/          ... video.mp4 + transcript.srt + transcript.txt
└── metadata/
    ├── playlist_manifest.json   ... title, channel, video IDs, durations
    └── youtube_report.json      ... per-video status
```

## Step 4: Transcript strategy

For each video, in order of preference:

1. **YouTube's native captions** (auto-generated or human) via `yt-dlp --write-subs --write-auto-subs --sub-format srt`. Free, instant, good enough for most content.
2. **Groq Whisper-large-v3-turbo** if no captions and a Groq key is in `~/.iss/.env`. Fast and high quality.
3. **Local faster-whisper (small or medium model)** as final fallback. Slower but free and offline.

The script handles this fallback chain automatically.

## Step 5: Report

After completion, show:

- Videos pulled: N of M (with reasons for any failures)
- Total transcript size (characters)
- Total disk used (MB)
- Where everything saved to

Suggest natural next steps based on what they pulled: "Want me to summarize the transcripts?" or "Want me to extract the key points from each video?"

## Edge cases

- **Age-restricted video**: yt-dlp needs cookies. If `youtube.com` cookies exist in `~/.iss/sessions/`, they're passed automatically. Otherwise tell the user to run `/login https://youtube.com` first.
- **Geo-blocked**: yt-dlp will return an error. Tell the user; we can't bypass region restrictions.
- **Live stream replay**: works, but transcripts may have stutters near the live-to-VOD transition. Note this in the report.
- **Members-only video**: needs the user's YouTube membership cookies. Same `/login` flow.
- **Massive playlist (200+ videos)**: ask the user to confirm before launching. Suggest filtering to a date range or pulling transcripts-only first.

## Why this is its own skill

YouTube has a separate auth model (Google/OAuth) from typical LMS platforms, has native captions worth using before Whisper, and its scope is bursty (a single video to a 500-video channel). A dedicated trigger lets users describe what they want in YouTube-specific terms without us having to disambiguate from "scrape this course".
