#!/usr/bin/env python3
"""
BUILD THE FIRM'S SHARED BRAIN — a local full-text index over the ENTIRE case.

Adopted best-of-breed (sqlite-vec author's hybrid-search model) and rebuilt
local-first: zero cloud, one SQLite file, FTS5 keyword search over every text
document in the matter home. Any role/agent queries it with ask_case.py instead
of guessing which files to read — so the whole firm can "see the entire case."

Reads paths from firm.config.json (single source of truth). Output:
<matter_home>/00_ADMIN/case-index/case.db
"""
import sqlite3, json, sys, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__import__("os").environ.get("CLAUDE_PROJECT_DIR") or __import__("os").getcwd())  # Clawyer: the client workspace, not the plugin folder
cfg = json.load(open(ROOT / "firm.config.json", encoding="utf-8"))
HOME = ROOT / cfg["paths"]["matter_home"]
IDX = HOME / "00_ADMIN" / "case-index"
IDX.mkdir(parents=True, exist_ok=True)
DB = IDX / "case.db"

TEXT = {".md", ".txt", ".csv", ".vtt", ".json", ".log", ".html", ".htm"}
PDF = {".pdf"}
DOCX = {".docx"}
MAXBYTES = 25_000_000

def extract(p):
    e = p.suffix.lower()
    try:
        if e in TEXT: return p.read_text(encoding="utf-8", errors="ignore")
        if e in PDF:
            import fitz
            with fitz.open(p) as d: return "\n".join(pg.get_text() for pg in d)
        if e in DOCX:
            import docx
            return "\n".join(par.text for par in docx.Document(str(p)).paragraphs)
    except Exception as ex:
        return f"[extract-error {ex}]"
    return ""

def main():
    con = sqlite3.connect(DB)
    con.execute("DROP TABLE IF EXISTS docs")
    con.execute("CREATE VIRTUAL TABLE docs USING fts5("
                "path, folder, name, ext, mtime UNINDEXED, content, "
                "tokenize='porter unicode61')")
    n = skip = 0; t0 = time.time()
    for p in HOME.rglob("*"):
        if p.is_dir(): continue
        e = p.suffix.lower()
        if e not in TEXT | PDF | DOCX: continue
        if "case-index" in p.parts: continue
        # Markdown-first: if a binary has a sidecar twin (<name>.md), skip the
        # binary and let the index read the markdown instead — never re-parse a
        # PDF the firm already converted.
        if e in PDF | DOCX and p.with_name(p.name + ".md").exists(): continue
        try:
            if p.stat().st_size > MAXBYTES: skip += 1; continue
        except OSError: continue
        txt = extract(p)
        if not txt or not txt.strip(): continue
        rel = p.relative_to(HOME).parts
        folder = rel[0] if len(rel) > 1 else "_root"
        con.execute("INSERT INTO docs(path,folder,name,ext,mtime,content) VALUES (?,?,?,?,?,?)",
                    (str(p), folder, p.name, e, int(p.stat().st_mtime), txt))
        n += 1
        if n % 500 == 0: print(f"  {n} indexed... {time.time()-t0:.0f}s", flush=True)
    con.commit()
    # tiny stats table
    con.execute("CREATE TABLE IF NOT EXISTS meta(k,v)")
    con.execute("DELETE FROM meta")
    con.executemany("INSERT INTO meta(k,v) VALUES(?,?)",
                    [("built", time.strftime("%Y-%m-%d %H:%M")), ("docs", str(n))])
    con.commit()
    by = con.execute("SELECT folder,count(*) FROM docs GROUP BY folder ORDER BY 2 DESC").fetchall()
    con.close()
    print(f"\nDONE. indexed {n} documents ({skip} skipped huge) in {time.time()-t0:.0f}s")
    print(f"DB: {DB}  ({DB.stat().st_size/1e6:.1f} MB)")
    print("by folder:")
    for f, c in by: print(f"  {c:>5}  {f}")

if __name__ == "__main__":
    main()
