---
name: notebooklm-suggest
description: Use to audit the user's material and recommend which NotebookLM notebooks are worth building — "what notebooks should I build", "suggest notebooks from my files", "audit my drive for notebook ideas", "what knowledge bases am I missing", "look at my material and recommend notebooks", "/notebooklm-suggest". Cross-platform; recommends only — never builds or uploads. Privacy-bounded.

---

# notebooklm-suggest — Recommend What to Build (v0.1)

Audits the user's material and returns a ranked, deduped, niche-aware list of notebooks worth building, then offers a per-pick handoff to build them. **Recommends only — never builds, never uploads.** This is the deep proactive audit; the cheap in-session nudges live in the `notebook-suggest` hook, not here.

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity`. If `beginner`, emit; else skip:

> I'll look over your files (only the folders you point me at) and tell you which NotebookLM notebooks would be worth building. I just recommend — I won't create or upload anything without you choosing it. I'll also check what Claude already knows about your niche so I don't ask you things twice.

## Layer 2: Suggest before invoking

If borderline ("I have tons of files and don't know where to start", "what should I even put in NotebookLM"):

> "Want me to audit your material and recommend the notebooks worth building with `/notebooklm-suggest`? It only recommends — nothing gets created or uploaded without your say-so."

If explicitly invoked, skip the suggestion.

## Preconditions

1. `.claude/workspace.yml#environment` `cowork` → "Auditing your material needs Claude Code (the terminal app) so I can read the folders you point me at. Open this workspace there." Stop.
2. NotebookLM auth is NOT required to produce recommendations (this skill has pre-setup value). Set `NB`: Win `%USERPROFILE%\.notebooklm-venv\Scripts\notebooklm.exe` / Mac `~/.notebooklm-venv/bin/notebooklm`. If `<NB>` is missing or auth invalid, continue anyway — dedup (Phase 5) is skipped with a one-line warning and the build-offer (Phase 8) routes through `/notebooklm-setup` first.

## Phase 1 — Niche discovery (minimize manual work)

Do NOT open with an interview. Derive the niche:

1a. **From Claude context.** Read `~/.claude/CLAUDE.md`, the project `CLAUDE.md`, and Glob `~/.claude/projects/*/memory/*.md`. For memory files, only consider ones whose frontmatter has `type: user`. Extract ONLY: business/niche, audience, offer/positioning. **Hard privacy boundary (identical to super-setup Step 0.5) — never extract:** client/customer lists or contact data, secrets/API keys/credentials, feedback memories (`feedback_*` or bodies marked as complaints/preferences about Claude), internal strategy, or anything from memory files lacking `type: user`. If a file has no `type` frontmatter, skip it.

1b. **From the scans.** Folder/business names and recurring sampled topics (Phases 3–4) are themselves niche signals — fold them in; no separate step.

1c. **Confirm, don't interview.** Present the inferred niche as ONE line: "Looks like your niche is X and your audience is Y — correct? (adjust if not)". Only if 1a AND 1b yield nothing, ask at most 1–2 explicit questions.

## Phase 2 — Point at sources

Ask the user to name local folder path(s) and/or Google Drive location(s). **Never auto-pick** or scan home/Desktop/Documents wholesale. Build a scan manifest (each path + file count) and show it; confirm before any access. Local = filesystem. Drive = the `gws-drive` skills (read-only listing).

## Phase 3 — Structure pass (free, private — NO content reads)

Collect metadata only: folders, filenames, extensions, sizes, dates, counts. Cluster into candidate topics by folder + filename signals. Do not open any file in this pass.

## Phase 4 — Snippet pass (CONSENT-GATED)

For each candidate cluster, ask explicit consent before reading content. On consent, read only ~the first page of each file in that cluster to confirm topic and write an honest rationale. Stays local in this session — nothing is uploaded (uploading only happens later in `notebooklm-build`, separately consented). Drive snippet reads via `gws-drive`, same consent. If consent is declined, proceed with metadata-only recommendations for that cluster.

## Phase 5 — Dedup against existing notebooks

If `<NB>` is available: read `~/.notebooklm/notebooks.cache`; if absent/stale, refresh via `<NB> list --json` (parse `notebooks[].id`/`title`). Match candidate topics against existing notebook titles. A topic that already has a notebook → recommend "add to existing 'X'" (route later to `/notebooklm-build` add-to-existing or `/notebooklm-transcripts`), not "build new". If `<NB>` unavailable: skip dedup, warn in one line ("NotebookLM isn't set up yet, so I can't check what you already have — recommendations may overlap existing notebooks").

## Phase 6 — Rank

Score each candidate ≈ volume × niche-relevance × topical-coherence × recency. Keep a candidate only if it has ≥ ~3 related sources OR clearly high niche-relevance. Cap the final list at the top 5–7.

## Phase 7 — Present

Ranked table — columns: proposed title · sources (paths/Drive refs) · 1-line why · new vs add-to-existing. Then offer (do not force): "Want this saved as a report to `output/research/`?" — if yes, write a dated markdown audit there.

## Phase 8 — Offer to build (per-pick, soft handoff)

For each recommendation the user picks: hand off via natural language to `/notebooklm-build` (new notebook) or `/notebooklm-transcripts` / `/notebooklm-youtube` if the sources fit those better. One decision per notebook — never bulk auto-build. If NotebookLM isn't set up, say the build step will start with `/notebooklm-setup`.

## Ground rules (inherited from RULES.md)

- **Surgical Execution:** recommend-only. Never create, upload, modify, or delete anything. Read content only after explicit per-cluster consent.
- **Intent Clarification:** never auto-pick folders; confirm the inferred niche in one line rather than assuming silently.
- **Least Complexity:** metadata first; snippets only when needed and consented; top 5–7, not an exhaustive dump. Stateless re-run (re-derive against the live cache; no state file).
- **Declarative Focus:** DoD = a ranked, deduped, niche-aware recommendation list with rationales, produced with zero unconsented content reads, plus a per-pick build handoff.
