# The art-director design prompt

One paste-in prompt that turns approved copy into a design canvas. Written for a carousel;
the same shape works for a reel frame with the size swapped.

## How to use it

1. Write and approve your copy first, however you normally write it.
2. Open the design tool.
3. Paste the prompt below, with your copy pasted into the `COPY` block.

## The prompt

```text
You are an art director. Build me an Instagram carousel as a Claude Design canvas.

COPY — use exactly the copy below, as written. Never rewrite, shorten or
reorder it.

[PASTE YOUR COPY HERE]

SIZE: [WIDTH x HEIGHT].

BRAND: use my design system if one is loaded, and let it win wherever it
conflicts with the direction below. If there isn't one, pick a direction and
commit to it.

THE BAR: this is the payoff shot in a video. If the reaction is "that's clean,"
I failed. I need "wait, Claude made THAT?"

First, show me 3 covers in genuinely different directions. I pick one, then you
build the rest to match it.

Push hard on:
· one big visual idea carried across every slide
· enormous scale contrast — something should be huge
· texture, depth, layering — not flat colour fills
· a palette that commits, dominant field plus a sharp accent
· break the grid on the cover

Still has to hold: every slide reads as one set · legible at thumbnail · no text
overflow.

Before you show me anything: render it, measure the overflow, look at the
screenshots, then shrink the cover to thumbnail size. If it doesn't stop a
scroll, fix it before I see it.
```

## The variables

- **`SIZE`** ... `1080 x 1350` for a carousel, `1080 x 1920` for a reel. Substitute the
  numbers; do not leave the brackets in.
- **`COPY`** ... paste the approved copy verbatim in place of the bracket, and keep the
  "never rewrite, shorten or reorder it" clause. If the design tool can already see the copy
  from the session, point at it instead of pasting; the clause still applies.
- **`BRAND`** ... leave exactly as written. It defers to a loaded design system and forces a
  committed direction when there is not one.
- **`THE BAR`** ... kept above as the example line. Change the reaction, keep the shape.

## Swapping in your own thing

**`THE BAR`** is the line to change if you are not making a video. It works because it names
the *reaction* you want instead of a spec. **Keep that shape, change the target.**
