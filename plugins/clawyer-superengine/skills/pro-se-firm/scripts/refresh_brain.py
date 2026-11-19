#!/usr/bin/env python3
"""
INCREMENTAL refresh of the shared case index — fast enough to run on every session.
Only re-indexes files whose mtime changed (vs a full rebuild). Deletes rows for
files removed from disk. Falls back to a full build if case.db is missing.
Reads paths from firm.config.json. Output: a one-line summary (for the hook).
"""
import sqlite3, json, sys, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__import__("os").environ.get("CLAUDE_PROJECT_DIR") or __import__("os").getcwd())  # Clawyer: the client workspace, not the plugin folder
cfg = json.load(open(ROOT / "firm.config.json", encoding="utf-8"))
HOME = ROOT / cfg["paths"]["matter_home"]
DB = HOME / "00_ADMIN" / "case-index" / "case.db"
TEXT = {".md", ".txt", ".csv", ".vtt", ".json", ".log", ".html", ".htm"}
PDF = {".pdf"}; DOCX = {".docx"}; MAXBYTES = 25_000_000

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
    except Exception as ex: return f"[extract-error {ex}]"
    return ""

def main():
    if not DB.exists():
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_case_index.py")])
        return
    con = sqlite3.connect(DB)
    have = dict(con.execute("SELECT path, mtime FROM docs").fetchall())
    on_disk = {}
    for p in HOME.rglob("*"):
        if p.is_dir() or "case-index" in p.parts: continue
        e = p.suffix.lower()
        if e not in TEXT | PDF | DOCX: continue
        # markdown-first: skip a binary that already has a <name>.md sidecar twin
        if e in PDF | DOCX and p.with_name(p.name + ".md").exists(): continue
        try:
            if p.stat().st_size > MAXBYTES: continue
            on_disk[str(p)] = int(p.stat().st_mtime)
        except OSError: continue
    added = changed = removed = 0
    # new or changed
    for path, mt in on_disk.items():
        if path not in have:
            added += 1
        elif have[path] != mt:
            changed += 1
        else:
            continue
        p = Path(path)
        txt = extract(p)
        if not txt or not txt.strip(): continue
        rel = p.relative_to(HOME).parts
        folder = rel[0] if len(rel) > 1 else "_root"
        con.execute("DELETE FROM docs WHERE path=?", (path,))
        con.execute("INSERT INTO docs(path,folder,name,ext,mtime,content) VALUES (?,?,?,?,?,?)",
                    (path, folder, p.name, p.suffix.lower(), mt, txt))
    # removed
    for path in have:
        if path not in on_disk:
            con.execute("DELETE FROM docs WHERE path=?", (path,)); removed += 1
    total = con.execute("SELECT count(*) FROM docs").fetchone()[0]
    con.execute("DELETE FROM meta WHERE k IN ('built','docs')")
    con.executemany("INSERT INTO meta(k,v) VALUES(?,?)",
                    [("built", time.strftime("%Y-%m-%d %H:%M")), ("docs", str(total))])
    con.commit(); con.close()
    print(f"brain refreshed: +{added} new, ~{changed} changed, -{removed} removed → {total} docs")

if __name__ == "__main__":
    main()
