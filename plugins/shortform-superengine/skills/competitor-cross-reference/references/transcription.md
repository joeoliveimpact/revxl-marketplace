# Transcription chain

Relocated verbatim from `SKILL.md` at 0.4.0, with one repair: the engine table
was split in half by a paragraph sitting between its two rows, so it never
rendered as a table. That paragraph now follows the table. No wording changed.

Transcription is **ON by default and runs automatically** ... no opt-in, no asking. The
spoken transcript is the **primary text** the analysis reads. A reel's post caption is
*metadata* (hashtags, CTA copy, styling) ... **it is not what the creator says on camera.
An analysis built on captions alone is a broken analysis** and must never be presented
as the real thing. Only skip transcription if the user explicitly opts out.

**Scope (automatic):** transcribe every reel the analysis deep-reads ... all of the
client's own reels, every outlier, and each competitor's top performers. Offer to
expand to the full gathered fleet (hundreds of reels ... the chain is free, the cost is
runtime, so warn about time, not credits).

**How:**

1. **Do NOT download, scrape, or "resolve" anything ... the direct video URL is already in the pulled data.** Every reel's JSON carries a signed Instagram CDN `.mp4` at `post.content.media_urls`. **Never use `yt-dlp`, `instaloader`, or any IG scraper here** ... there is nothing to resolve, and scraping adds bot-detection risk for zero gain.
2. Extract audio straight off the CDN URL ... ffmpeg streams it directly (~3s/reel):
   `ffmpeg -i "<media_urls>" -vn -ar 16000 -ac 1 <audio.wav>`
   ⚠️ **CDN URLs are signed and EXPIRE (hours-to-days). Transcribe the same day as the pull; if the pull is older, re-pull that creator's reels first (~3 credits) ... never fight a dead link.** A batch of empty-wav failures on an old pull means expired URLs, not a broken pipeline (field-proven 07.12.26: 4-day-old pull failed 20/20, same-day pull 100%).
3. Transcribe ... **launch both engines in parallel; first healthy transcript wins** (use whichever returns first, cancel the other; if only one is installed, run it alone):

   | Engine | Method | Notes |
   |---|---|---|
   | Groq cloud | `whisper-large-v3-turbo` via Groq API | Fast; needs `GROQ_API_KEY` in env. Prefer turbo over full `large-v3` ... same accuracy on names, ~3x cheaper, and safer with a prompt. |
   | Local Whisper | `faster-whisper` (local CPU/GPU) | Offline; slower but never fails. |

   **Pass a `prompt` with the niche's proper nouns.** Competitor videos are dense with
   tool and brand names Whisper has never seen, and it silently substitutes the nearest
   English phrase ("Kling 01" → "cling a one"). Build the sentence from brand-brain and
   read `brand-brain/references/transcription-vocabulary.md` first ... a prompt written as
   a bare comma list strips all punctuation from the transcript, and a prompt can drop
   repeated takes, so compare the output length against an unprompted run.

   **Save per-segment timestamps** (`[{start, end, text}]`), never just the joined text ... beat/pattern timing analysis is impossible without them. Batch scale reference: local GPU (faster-whisper `small`, cuda) ≈ 1.5s/reel transcribe + 3s ffmpeg; ~1,000 reels ≈ 40 to 50 min with ~6 parallel ffmpeg prefetch workers feeding one GPU.

4. **Fallback floor (only when both engines fail for a reel):** use the post
   caption ... and **flag that reel `caption-only` in every output that cites it**.
   Caption-only is a degrade to be surfaced, never a silent substitute.

**Never** use SocialCrawl `media/transcript` for transcription ... it costs 10 credits per reel and provides no advantage over the local transcription chain.
