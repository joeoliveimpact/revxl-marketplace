# Pick a caption look

When no caption accent is chosen, captions use the saved brand colour if it is valid.

| Look | Family | Weight |
|---|---|---|
| Clean | Inter | 600 |
| Bold pop | Montserrat | 900 |
| Boxed | Inter | 700 |
| Karaoke | Inter | 800 |
| Outline caps | Montserrat | 800 |

Looks use only fonts bundled in `runtime/fonts/VERSION.json`, declared once in `captions.py`; other style fonts get the nearest bundled face, with notice.
These are the client's taste:

- **Clean:** white words with a soft shadow and a small rise as they appear.
- **Bold pop:** larger uppercase words, a black outline and a quick pop in size.
- **Boxed:** white words on a rounded dark plate, with a gentle pop.
- **Karaoke:** dim words brighten in turn as they are spoken. Marked words have the accent colour.
- **Outline caps:** uppercase white words with an accent outline and a small rise.

**No captions** is also a choice. The suggested accent is yellow;
the client can choose another colour. Numbers, key words, stressed phrases and calls to action
can carry that accent.

The client can also choose these options (VES-3):

- **a. Echo suppression:** leave a caption off when a graphic already says all its words.
  Suggested off.
- **b. Under small overlays:** keep captions while a small graphic is on screen. Suggested on.
- **c. Line breaks:** break the short groups on punctuation or pauses. Suggested on.
  Turning this off groups by word count and reading time; layout changes still split groups.
- **d. Minimum reading time:** a suggestion of 0.35 seconds. Shorter groups get a note and stay in.
- **e. Marker:** choose a translucent swipe behind a whole marked phrase instead of coloured words.
  The phrase keeps its qualifiers, and the one-punch limit still applies. Suggested off.
- **f. Loudness emphasis:** suggest stress on words spoken more loudly than the rest of the reel.
  Review the suggestions for meaning before using them. Suggested off; chosen word marks win.

- Suggestion: Let the ending answer the opening, and hold your accent colour for the biggest moment.
- Suggestion: Try marker mode if a swipe behind the whole true phrase helps it stand out.
- Suggestion: Try loudness emphasis to suggest stressed phrases, then check that they say what you mean.

Groups have one to three spoken words.
When no clear spot exists, the caption stays in the safest available spot with a note.
An unusually long group uses a smaller font to fit, also with a note.
