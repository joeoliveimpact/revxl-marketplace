#!/usr/bin/env python3
"""Carry a Cut Board ruling onto a REBUILT board whose words are the same words (same ids, same text)
but whose recording, islands or events changed - e.g. the take's wav was re-extracted on a corrected clock.
Indices are re-derived by WORD ID, never copied.

    <editor python> -X utf8 -I port_selection.py <old cut-selection.json> <old cut-board.config.json> \
        <new cut-board.config.json> -o <new cut-selection.json>

Refuses when a line's picked attempt no longer carries the same word ids, or a struck word id is missing.
Pause rulings (sil) are refused if present: silence indices do not survive a re-islanding.
Struck words (rm) are kept per attempt, and each attempt's word ids come from that attempt's OWN take.
"""
import argparse, json, datetime, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("selection"); ap.add_argument("old_config"); ap.add_argument("new_config")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    sel = json.loads(Path(a.selection).read_text(encoding="utf-8"))
    old = json.loads(Path(a.old_config).read_text(encoding="utf-8"))
    new = json.loads(Path(a.new_config).read_text(encoding="utf-8"))
    oby = {ln["id"]: ln for ln in old["lines"]}; nby = {ln["id"]: ln for ln in new["lines"]}

    def take_words(cfg, att):
        # attempt word records carry only the index i; the id lives on that attempt's take's board sequence
        return cfg["takes"][str(att["take"])]["words"]

    out_lines, moved = [], 0
    for l in sel["lines"]:
        if l.get("sil"):
            raise SystemExit(f"{l['id']}: has pause rulings; silence indices cannot be ported. Re-rule this line.")
        nl = dict(l)
        if l.get("pick") is None or l.get("drop"):
            out_lines.append(nl); continue
        oa = oby[l["id"]]["attempts"][l["pick"]]; na = nby[l["id"]]["attempts"][l["pick"]]
        otw, ntw = take_words(old, oa), take_words(new, na)
        oid = [otw[w["i"]].get("id") for w in oa["words"]]; nid = [ntw[w["i"]].get("id") for w in na["words"]]
        # compare WORD ids only: vocal events (v_NNNN) are re-detected on a new wav and may change count
        if [x for x in oid if x and x.startswith("w_")] != [x for x in nid if x and x.startswith("w_")] or oa["take"] != na["take"]:
            raise SystemExit(f"{l['id']} pick {l['pick']}: attempt word ids differ between boards; re-rule this line.")
        rm = {}
        for j, idxs in (l.get("rm") or {}).items():
            att_o = oby[l["id"]]["attempts"][int(j)]; att_n = nby[l["id"]]["attempts"][int(j)]
            otw_j, ntw_j = take_words(old, att_o), take_words(new, att_n)   # attempt j's own take, not the pick's
            by_id = {ntw_j[w["i"]].get("id"): w["i"] for w in att_n["words"]}
            new_idx = []
            for i in idxs:
                wid = otw_j[i].get("id")
                if wid not in by_id:
                    raise SystemExit(f"{l['id']}: struck word i={i} id={wid} not in the new attempt")
                if by_id[wid] != i: moved += 1
                new_idx.append(by_id[wid])
            rm[j] = sorted(new_idx)
        nl["rm"] = rm
        out_lines.append(nl)
    ported = {**sel, "lines": out_lines,
              "word_list_hash": {n: t["word_list_hash"] for n, t in new["takes"].items()},
              "board_hash": new["board_hash"],
              "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "ported_from": {"selection": Path(a.selection).name, "board_hash": sel.get("board_hash")}}
    Path(a.out).write_text(json.dumps(ported, indent=1), encoding="utf-8")
    print(f"ported {len(out_lines)} lines; {moved} struck-word indices moved; wrote {a.out}")


if __name__ == "__main__":
    main()
