# NotebookLM Import — Step-by-Step

1. Go to [notebooklm.google.com](https://notebooklm.google.com) and sign in with the Google account you want this notebook under.
2. Click **New notebook**.
3. Click **Add sources**. Upload **every** .md file in this bundle folder. Order doesn't matter — NotebookLM indexes them together.
4. Once sources finish processing (~30 seconds), the **Studio** panel on the right has the audio options.
5. Click **Audio Overview** → **Customize**.
6. In the customization prompt, paste the prompt from `00 - Speaker Notes for 3-Min Roadmap Video.md` (the one labeled "NotebookLM customization prompt").
7. Click **Generate**. Takes 2-5 minutes.
8. Listen back. If the tone is off, click **Regenerate** and tighten the prompt with more specific voice direction.
9. When happy, click **Download** to get the MP3.
10. (Optional) Convert MP3 → MP4 with a static cover image using any tool (e.g., `ffmpeg`, a free online converter, CapCut). Cover image should be: brand logo + offer name.

## When to regenerate
- Generic AI-narrator tone instead of the coach's voice
- Skipping the guarantees or the data layer (the moat)
- Going over 3:30
- Not hitting the application URL at the end

## Recording your own voice instead
If the audio overview doesn't land, use `00 - Speaker Notes` as an outline and record yourself with any tool (Voice Memos, Riverside, Descript, even your phone). 3-min raw audio in your own voice beats a polished generic AI narrator every time.

## Personalizing for a specific prospect
1. Duplicate this bundle folder.
2. Rename to `{{ProspectName}} - NotebookLM Bundle/`.
3. Edit `00 - Speaker Notes`: replace `{{ProspectName}}` and `{{ICA}}` with the actual prospect's name + their specific pain point from their intake.
4. Re-upload to a fresh NotebookLM notebook.
5. Send the resulting audio to the prospect via DM with one line: *"I built this for you. 3 minutes. Tell me what you think."*

Per-prospect conversion is 3-5× generic. Use this.
