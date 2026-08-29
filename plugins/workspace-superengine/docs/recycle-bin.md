# The Recycle Bin ... quarantine, not deletion

Any superengine skill that removes a file from a workspace moves it here instead of deleting
it. The name is deliberate: users already know the desktop recycle bin's contract, so nothing
has to be taught. The behavior below exists to keep that borrowed mental model honest.

The mechanism was proven on 2026-08-29 with a byte-identical round trip: a file quarantined,
manifested, and restored with the same SHA256 at every step, including awkward content (mixed
line endings, unicode, no trailing newline).

## The contract

1. **Nothing enters without being listed.** Every move appends a row to
   `_recycle-bin/MANIFEST.md` at move time. A file in the bin with no row is a bug.
2. **Everything is recoverable until emptied.** The row records the original path, so a
   restore is a move back, not a reconstruction.
3. **Emptying is an explicit act.** Nothing is deleted on a timer. The 7 day mark makes a
   batch *eligible to be asked about*. It never makes anything disappear.

## Layout

```
_recycle-bin/
  README.md            the contract, for humans browsing the workspace
  MANIFEST.md          append-only log, one row per quarantined file
  YYYY-MM-DD/          dated batch folder; files keep their original basename
```

## The manifest

```markdown
| File | Original path | Quarantined | Eligible | Reason | Notes |
|---|---|---|---|---|---|
```

- `Original path` is workspace-relative, forward slashes.
- `Quarantined` is stamped at move time and is **the only source of truth for age**. NTFS
  last-access updates are off by default on Windows, so file timestamps cannot be trusted
  here. Never age a file from the filesystem.
- `Eligible` is quarantined + 7 days. At eligibility, one question gets asked ... move the
  batch to permanent cloud storage, or delete it ... naming every file. Silence is not
  consent; an unanswered ask means the batch stays.
- Rows are never deleted. A restore, a final deletion, or any other outcome is recorded by
  annotating the `Notes` column with a dated note.

## Scope discipline

Outside two cases, the bin is out of scope for every skill and session:

- A file that should exist in the workspace is missing ... check `MANIFEST.md` first and
  restore from the dated folder.
- The user asks about quarantined files, a restore, or the final cleanup directly.

Do not read the bin for context, do not search it when answering questions, do not count its
contents in any audit of what the workspace contains. A quarantined file is one the workspace
already decided it does not need.

## Restoring

Read the row, move the file from its dated folder back to `Original path`, then annotate the
row's `Notes` with the restore date. If the destination is now occupied, stop and ask rather
than overwriting either copy.

## Name collisions inside a batch

Two same-named files quarantined the same day get numeric suffixes on the *second* arrival
(`RULES.md`, then `RULES-1.md`), and each keeps its own manifest row. The row's `File` column
carries the name as stored in the bin; `Original path` disambiguates.

## Creating the bin

The first skill that needs to quarantine something creates `_recycle-bin/`, a `README.md`
carrying the contract above, and `MANIFEST.md` with the table header. Creation is silent; the
quarantine that triggered it is what gets reported.
