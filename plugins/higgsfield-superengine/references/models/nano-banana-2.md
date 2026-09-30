# Nano Banana 2 / Pro: not available through this plugin (app only)

**Not available through this plugin (app only).** The Higgsfield REST API has no Nano Banana endpoint, so this plugin can never call it and the model picker never suggests it. This file is prompting reference only, for clients who also use the Higgsfield app. Tags: see the legend in `references/model-picker.md`.

## REST alternative
- Labels or visible text (product with a label, ad copy) → Flare (`marketing-studio-image.md`).
- Reference-faithful edit without text (swap the background, keep the pixels) → Qwen Image 3 edit (`qwen-image.md`) or Grok Image 2.0 (`grok-image.md`).

## App IDs (app catalog 09.24.26, reference only)
- `nano_banana_2` (1k/2k/4k, default 1k; `mask` + `is_inpaint`), `nano_banana_2_lite` (adds `thinking`), `nano_banana_pro` (default 2k), `nano_banana`, `nano_banana_2_shots`. Aspect ratios include 4:5 and auto.

## Prompting guidance (app route)
- Strongest at reference fidelity, many references and pixel-preserving edits without text; not for labels or dense text. [SINGLE-SOURCE: A12, D10]
- Subject first, then action, environment, style, camera. Describe how the references relate ("combine the style of the first image with the subject of the second"); keep the text on what changes. [SINGLE-SOURCE: B1, A12]
- Reference order: identity grid → outfit → context. Swap a name the model won't know (or that could trip IP filters) for a visual description; for patterns bleeding onto skin, add "NOT a tattoo, NOT body paint"; closed-mouth expressions for stability. [SINGLE-SOURCE: D12]
- Two-reference composite: "Composite the [subject] from reference 1 onto the environment in reference 2. Preserve the exact silhouette… Match lighting color temperature and direction." [SINGLE-SOURCE: D10]
- Use labeled blocks when layout matters: a short prompt invented label text; the long labeled-block prompt followed every instruction. (T14, app route only: reference, not TESTED)
- Draft at the lowest tier, then promote the winner. [SINGLE-SOURCE: B1]
