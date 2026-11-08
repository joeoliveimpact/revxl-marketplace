# Jev, or the rubric — the route an unnamed ask takes

A named ask takes the express lane in SKILL.md. Any other ask follows the suggest hook's note, whose
last line is `jev: on` (with an ask file) or `jev: off`. Jev runs as
`node "${CLAUDE_PLUGIN_ROOT}/hooks/jev.mjs" <mode> "<ask file>"`.

1. **`jev: off`** — the no-key path, no Jev call: the rubric, the router and the menu order in
   [references/elicitation.md](elicitation.md).
2. **`jev: on`, or no note** — Write `{"ask": "<their words>"}` to the ask file (no note:
   `~/.claude/revxl/jev-ask.json`) with the Write tool, then run mode `intake`. By its `next`:
   - `not_research` → leave the flow.
   - `missing` → one `AskUserQuestion` for it, then at most one re-intake with the answer
     added; then go on with what there is (still `missing` counts as `none_fit`).
   - `package` → add its `"row"` to the file with the Write tool, run mode `worth`.
   - `none_fit` → mode `cuts`; dispatch `agents/research-router.md` with the `survivors` and
     absolute `${CLAUDE_PLUGIN_ROOT}/…` paths for every file it reads; add its `options[]` to
     the file as `"options"` with the Write tool, run mode `worth`.
3. **The menu** is the go popup in SKILL.md: worth's first three `options` not `free`, in its order
   (the recommendation with its `levelText` as the reason, the strongest, one more), then
   **None of these — just the free path**, with the reason if `free` is recommended. Each: one
   sentence from its `label`, a `lo–hi cr` range from its `quote`, and "may stop to confirm
   along the way" when `mayStop`. Only `free` options: no menu, run the free path. The pick is
   the go. Goal, Depth & freshness and End product are not asked on this path.
4. **A failure** (non-zero exit): at intake, the no-key path; after it, the row's options from
   `references/packages.json` (for `none_fit`, the router's), strongest first, asking nothing
   new. Exit 3 says nothing; 4, 5 or 6 say one plain line, once per conversation: *"OpenRouter
   key rejected / out of credit / Jev unavailable — using the standard picker"*.
