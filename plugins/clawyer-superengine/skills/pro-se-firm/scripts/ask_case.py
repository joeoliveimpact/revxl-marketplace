#!/usr/bin/env python3
"""
ASK THE ENTIRE CASE — the firm's shared-brain query tool.

Any role/agent runs this to search across EVERY case document at once instead of
guessing which files to read. Example the firm needs:
  python scripts/ask_case.py "questions asked of the opposing party" --folder 05_WORK-PRODUCT
  python scripts/ask_case.py "forensic interview"
  python scripts/ask_case.py "8.05 retirement deduction" --n 20

Returns ranked passages with the source file + folder, so the role knows exactly
what the case already contains (e.g. what cross-exam has / has NOT been asked).
Reads the DB path from firm.config.json.
"""
import sqlite3, json, sys, argparse, re
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__import__("os").environ.get("CLAUDE_PROJECT_DIR") or __import__("os").getcwd())  # Clawyer: the client workspace, not the plugin folder
cfg = json.load(open(ROOT / "firm.config.json", encoding="utf-8"))
DB = ROOT / cfg["paths"]["matter_home"] / "00_ADMIN" / "case-index" / "case.db"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="FTS5 query (supports AND OR NOT \"phrase\" prefix*)")
    ap.add_argument("--folder", default=None, help="restrict to one top folder (e.g. 04_EVIDENCE)")
    ap.add_argument("--ext", default=None, help="restrict to extension (e.g. .vtt for transcripts)")
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--files-only", action="store_true", help="list matching files, no snippets")
    a = ap.parse_args()
    if not DB.exists():
        print(f"No index yet. Build it: python scripts/build_case_index.py"); return
    con = sqlite3.connect(DB)
    # Harden against FTS5 syntax errors: if the user isn't doing an explicit
    # phrase search, strip punctuation (., $, :, etc.) that FTS5 treats as
    # operators. Keeps word chars, spaces, * (prefix), and OR/AND/NOT.
    query = a.query
    if '"' not in query:
        query = re.sub(r"[^\w\s*]", " ", query)
        query = re.sub(r"\s+", " ", query).strip()
    where = "docs MATCH ?"; params = [query]
    if a.folder: where += " AND folder = ?"; params.append(a.folder)
    if a.ext: where += " AND ext = ?"; params.append(a.ext)
    if a.files_only:
        q = f"SELECT DISTINCT folder, path FROM docs WHERE {where} ORDER BY rank LIMIT ?"
    else:
        q = f"SELECT folder, path, snippet(docs, 5, '>>', '<<', ' … ', 18) FROM docs WHERE {where} ORDER BY rank LIMIT ?"
    params.append(a.n)
    try:
        rows = con.execute(q, params).fetchall()
    except sqlite3.OperationalError as e:
        print(f"query error: {e}\n(tip: wrap multi-word phrases in quotes)"); return
    print(f"=== {len(rows)} hit(s) for: {a.query}" + (f"  [folder={a.folder}]" if a.folder else "") + " ===")
    for r in rows:
        if a.files_only:
            print(f"  [{r[0]}] {r[1]}")
        else:
            folder, path, snip = r
            print(f"\n[{folder}] {Path(path).name}")
            print("   " + re.sub(r"\s+", " ", snip).strip()[:320])
    con.close()

if __name__ == "__main__":
    main()
