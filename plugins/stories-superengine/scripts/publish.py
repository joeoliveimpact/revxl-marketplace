#!/usr/bin/env python3
"""Host story frames and schedule (or post) them, through whatever the coach already has connected.

Subcommands (run with Claude; the coach never types these):
  detect                                   which publish paths exist on this machine (composio + toolkits, gws)
  brands   [--toolkit T]                   Metricool brands: id, label, timezone, IG/FB accounts
  host     FILES... [--via composio|gws] [--folder ID] --out hosted.json
                                           upload, share "anyone with the link", verify the link serves media
  schedule --hosted hosted.json --when "YYYY-MM-DD HH:MM" --tz America/New_York --brand-id N
           [--toolkit T] [--ai] [--manual] [--networks instagram,facebook] [--payload-only] --out DIR
                                           one Metricool Story post with every frame, in order
  readback --brand-id N --date YYYY-MM-DD --tz TZ [--toolkit T]
                                           what Metricool has on that day, with per-network status
  instagram FILES... --confirm-live [--ig-user me]
                                           IG Story right now, one frame at a time (no schedule, no Facebook)
  --selftest                               offline checks (timezone offsets, payload shape, path conversion)

Rules baked in: a hosted link must answer with image/* or video/* before anything schedules; gws and
composio get their arguments as a list (never a shell string); the UTC offset is computed for the
post's own date, so daylight saving is handled; big composio responses saved to a file are read back.
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request

TIMEOUT = 180


# ---------- composio: native CLI, or the CLI inside WSL on Windows ----------

def composio_mode():
    if shutil.which("composio"):
        return "native"
    if os.name == "nt" and shutil.which("wsl.exe"):
        try:
            r = subprocess.run(["wsl.exe", "-e", "bash", "-lc", "command -v composio"],
                               capture_output=True, text=True, timeout=60)
            if r.returncode == 0 and r.stdout.strip():
                return "wsl"
        except (OSError, subprocess.TimeoutExpired):
            pass
    return None


def to_wsl(path):
    p = pathlib.Path(path).resolve()
    drive = p.drive.rstrip(":").lower()
    return f"/mnt/{drive}" + "/" + "/".join(p.parts[1:])


def composio(slug, data=None, file=None, mode=None):
    mode = mode or composio_mode()
    if not mode:
        raise SystemExit("composio is not installed here. Run the stories-setup skill to connect it.")
    args = ["execute", slug, "-d", "-"]
    if file:
        args += ["--file", to_wsl(file) if mode == "wsl" else str(pathlib.Path(file).resolve())]
    if mode == "native":
        cmd = [shutil.which("composio"), *args]
    else:
        cmd = ["wsl.exe", "-e", "bash", "-lc", "composio " + " ".join(_q(a) for a in args)]
    r = subprocess.run(cmd, input=json.dumps(data or {}), capture_output=True, text=True,
                       encoding="utf-8", timeout=TIMEOUT)
    out = r.stdout
    i = out.find("{")
    if i < 0:
        raise SystemExit(f"{slug}: no JSON back from composio. {(out + r.stderr).strip()[:400]}")
    d = json.loads(out[i:])
    inner = d.get("data") if isinstance(d.get("data"), dict) else {}
    path = d.get("outputFilePath") or inner.get("outputFilePath")
    if path:   # big responses are written to a file instead of stdout
        read = ["wsl.exe", "-e", "bash", "-lc", "cat " + _q(path)] if mode == "wsl" else None
        text = subprocess.run(read, capture_output=True, text=True, encoding="utf-8", timeout=60).stdout if read \
            else pathlib.Path(path).read_text(encoding="utf-8")
        d = json.loads(text)
    return d


def _q(s):
    return "'" + str(s).replace("'", "'\\''") + "'"


def connected_toolkits(mode):
    found = set()
    for q in ("metricool schedule post", "instagram post story", "google drive upload file"):
        cmd = [shutil.which("composio"), "search", q, "--limit", "2"] if mode == "native" else \
            ["wsl.exe", "-e", "bash", "-lc", f"composio search {_q(q)} --limit 2"]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT).stdout
            found.update(json.loads(out[out.find("{"):]).get("connected_toolkits", []))
        except (ValueError, OSError, subprocess.TimeoutExpired):
            pass
    return sorted(found)


def metricool_prefix(toolkit):
    return toolkit.upper()


# ---------- subcommands ----------

def cmd_detect(_):
    mode = composio_mode()
    kits = connected_toolkits(mode) if mode else []
    mc = next((k for k in kits if "metricool" in k), None)
    print(json.dumps({
        "composio": mode,
        "metricool_toolkit": mc,
        "instagram": "instagram" in kits,
        "googledrive": "googledrive" in kits,
        "gws": bool(shutil.which("gws")),
        "note": "The Metricool Claude connector (Customize > Connectors) is checked by Claude, not this script.",
    }, indent=1))


def cmd_brands(a):
    d = composio(f"{metricool_prefix(a.toolkit)}_GET_BRAND_SETTINGS", {})
    rows = (d.get("data") or {}).get("data") or []
    print(json.dumps([{"id": b.get("id"), "label": b.get("label"), "timezone": b.get("timezone"),
                       "instagram": (b.get("networksData") or {}).get("instagramData"),
                       "facebook": bool((b.get("networksData") or {}).get("facebookData"))} for b in rows], indent=1))


def content_type(url):
    req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.headers.get("Content-Type", "")


def cmd_host(a):
    rec = host_files(a.files, a.via, a.folder)
    pathlib.Path(a.out).write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(f"  hosted {len(rec)} file(s) -> {a.out}")


def host_files(files, via=None, folder=None):
    via = via or ("composio" if composio_mode() else "gws" if shutil.which("gws") else None)
    if not via:
        raise SystemExit("No way to host files: connect Google Drive through composio (stories-setup).")
    mode = composio_mode() if via == "composio" else None
    rec = []
    for f in files:
        f = pathlib.Path(f)
        if via == "composio":
            if f.stat().st_size > 5 * 1024 * 1024:
                raise SystemExit(f"{f.name} is over 5 MB, the composio Drive upload limit. Use --via gws or a smaller file.")
            up = composio("GOOGLEDRIVE_UPLOAD_FILE", {"folder_to_upload_to": folder} if folder else {}, file=f, mode=mode)
            fid = (up.get("data") or {}).get("id")
            if not fid:
                raise SystemExit(f"upload failed for {f.name}: {str(up)[:300]}")
            composio("GOOGLEDRIVE_CREATE_PERMISSION", {"file_id": fid, "type": "anyone", "role": "reader"}, mode=mode)
        else:
            g = shutil.which("gws")
            args = [g, "drive", "+upload", str(f), "--name", f.name] + (["--parent", folder] if folder else [])
            out = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT).stdout
            up = json.loads(out[out.find("{"):]) if "{" in out else {}
            fid = up.get("id") or (up.get("file") or {}).get("id")
            if not fid:
                raise SystemExit(f"upload failed for {f.name}: {out[:300]}")
            subprocess.run([g, "drive", "permissions", "create", "--params",
                            json.dumps({"fileId": fid, "supportsAllDrives": True}),
                            "--json", json.dumps({"type": "anyone", "role": "reader"})],
                           capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT)
        url = f"https://drive.google.com/uc?export=download&id={fid}"
        ctype = content_type(url)
        print(f"  {f.name}: {ctype}")
        if not (ctype.startswith("image/") or ctype.startswith("video/")):
            raise SystemExit(f"{f.name}: the link serves '{ctype}', not media, so the share did not take. "
                             "Stopping before anything schedules.")
        rec.append({"file": f.name, "drive_id": fid, "url": url, "content_type": ctype})
    return rec


def local_iso(when, tz):
    """'2026-11-02 10:00' in tz -> '2026-11-02T10:00:00-05:00' (offset for that date, so DST is right)."""
    try:
        from zoneinfo import ZoneInfo
        z = ZoneInfo(tz)
    except Exception as e:  # Windows without the tzdata package
        raise SystemExit(f"Can't read timezone '{tz}' ({e}). Run check_deps.py --install (adds tzdata).")
    t = dt.datetime.strptime(when, "%Y-%m-%d %H:%M").replace(tzinfo=z)
    return t.isoformat(timespec="seconds"), t.strftime("%Y-%m-%dT%H:%M:%S")


def build_payload(hosted, when, tz, brand_id, ai, manual, networks):
    iso, local = local_iso(when, tz)
    info = {"autoPublish": not manual, "draft": False, "descendants": [], "firstCommentText": "",
            "hasNotReadNotes": False, "media": [h["url"] for h in hosted],
            "providers": [{"network": n} for n in networks],
            "publicationDate": {"dateTime": local, "timezone": tz},
            "shortener": False, "smartLinkData": {"ids": []}, "text": ""}
    if "instagram" in networks:
        info["instagramData"] = {"type": "STORY", "isAiGenerated": bool(ai)}
    if "facebook" in networks:
        info["facebookData"] = {"type": "STORY"}
    return {"blogId": str(brand_id), "date": iso, "info": json.dumps(info)}


def cmd_schedule(a):
    hosted = json.loads(pathlib.Path(a.hosted).read_text(encoding="utf-8"))
    p = build_payload(hosted, a.when, a.tz, a.brand_id, a.ai, a.manual, a.networks.split(","))
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metricool-payload.json").write_text(json.dumps(p, indent=1), encoding="utf-8")
    print(f"  payload -> {out / 'metricool-payload.json'} ({len(hosted)} frames, {p['date']})")
    if a.payload_only:
        return
    d = composio(f"{metricool_prefix(a.toolkit)}_CREATE_SCHEDULED_POST", p)
    post = ((d.get("data") or {}).get("data") or {})
    (out / "publish-result.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
    if not d.get("successful") or not post.get("id"):
        raise SystemExit(f"Metricool did not take it: {str(d.get('error') or d)[:400]}")
    print(f"  post {post['id']} | {len(post.get('media') or [])} media | "
          f"{[(x.get('network'), x.get('status')) for x in post.get('providers', [])]}")
    print("  Metricool gives a post a NEW id on every edit. Read it back by date, not by this id, after any change.")


def cmd_readback(a):
    start, _ = local_iso(f"{a.date} 00:00", a.tz)
    end, _ = local_iso(f"{a.date} 23:59", a.tz)
    d = composio(f"{metricool_prefix(a.toolkit)}_GET_SCHEDULED_POSTS",
                 {"brandId": str(a.brand_id), "fromDate": start, "toDate": end, "timezone": a.tz})
    rows = (d.get("data") or {}).get("data") or d.get("data") or []
    for post in rows if isinstance(rows, list) else []:
        when = (post.get("publicationDate") or {}).get("dateTime")
        print(f"  {post.get('id')} {when} {[(x.get('network'), x.get('status')) for x in post.get('providers', [])]}"
              f" media={len(post.get('media') or [])}")
    if not rows:
        print("  nothing on that day")


def to_jpeg(png, out_dir):
    """Instagram's API takes JPEG only. Re-encode with the browser we already ship with."""
    from playwright.sync_api import sync_playwright
    import base64
    data = base64.b64encode(pathlib.Path(png).read_bytes()).decode()
    out = pathlib.Path(out_dir) / (pathlib.Path(png).stem + ".jpg")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.set_content(f"<body style='margin:0'><img src='data:image/png;base64,{data}' style='display:block'></body>")
        pg.screenshot(path=str(out), type="jpeg", quality=92, full_page=False)
        b.close()
    return out


def cmd_instagram(a):
    if not a.confirm_live:
        raise SystemExit("This posts to Instagram RIGHT NOW. Re-run with --confirm-live only after the coach says go.")
    mode = composio_mode()
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="stories-ig-"))
    try:
        media = [to_jpeg(f, tmp) if pathlib.Path(f).suffix.lower() == ".png" else pathlib.Path(f) for f in a.files]
        for h in host_files(media, a.via):
            key = "video_url" if h["content_type"].startswith("video/") else "image_url"
            c = composio("INSTAGRAM_POST_IG_USER_MEDIA",
                         {"ig_user_id": a.ig_user, "media_type": "STORIES", key: h["url"]}, mode=mode)
            cid = (c.get("data") or {}).get("id")
            if not cid:
                raise SystemExit(f"{h['file']}: Instagram did not create the story: {str(c)[:400]}")
            pub = composio("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH",
                           {"ig_user_id": a.ig_user, "creation_id": str(cid), "max_wait_seconds": 120}, mode=mode)
            print(f"  {h['file']}: container {cid} -> published {(pub.get('data') or {}).get('id', pub.get('error'))}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def selftest():
    ok = True
    summer = local_iso("2026-10-09 10:00", "America/New_York")[0]
    winter = local_iso("2026-11-09 10:00", "America/New_York")[0]
    ok &= summer.endswith("-04:00") and winter.endswith("-05:00")
    print(f"  DST offsets: {summer} / {winter}")
    p = build_payload([{"url": "u1"}, {"url": "u2"}], "2026-10-09 10:00", "America/New_York", 123, True, False,
                      ["instagram", "facebook"])
    info = json.loads(p["info"])
    shape = (p["blogId"] == "123" and info["media"] == ["u1", "u2"] and info["instagramData"]["type"] == "STORY"
             and info["facebookData"]["type"] == "STORY" and info["autoPublish"] is True
             and info["publicationDate"] == {"dateTime": "2026-10-09T10:00:00", "timezone": "America/New_York"})
    print(f"  payload shape: {'ok' if shape else 'WRONG'}")
    ok &= shape
    ig_only = json.loads(build_payload([{"url": "u"}], "2026-10-09 10:00", "UTC", 1, False, True, ["instagram"])["info"])
    ok &= "facebookData" not in ig_only and ig_only["autoPublish"] is False
    if os.name == "nt":
        w = to_wsl(r"C:\Users\x\a b\f.png")
        print(f"  wsl path: {w}")
        ok &= w == "/mnt/c/Users/x/a b/f.png"
    return ok


def main():
    if "--selftest" in sys.argv:
        ok = selftest()
        print("selftest ok" if ok else "selftest FAILED")
        sys.exit(0 if ok else 1)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("detect")
    b = sub.add_parser("brands"); b.add_argument("--toolkit", default="custom_metricool")
    h = sub.add_parser("host"); h.add_argument("files", nargs="+"); h.add_argument("--via", choices=["composio", "gws"])
    h.add_argument("--folder"); h.add_argument("--out", required=True)
    s = sub.add_parser("schedule")
    for k in ("--hosted", "--when", "--tz", "--brand-id", "--out"):
        s.add_argument(k, required=True)
    s.add_argument("--toolkit", default="custom_metricool"); s.add_argument("--ai", action="store_true")
    s.add_argument("--manual", action="store_true", help="autoPublish off: Metricool pings the phone at post time")
    s.add_argument("--networks", default="instagram,facebook"); s.add_argument("--payload-only", action="store_true")
    r = sub.add_parser("readback")
    for k in ("--brand-id", "--date", "--tz"):
        r.add_argument(k, required=True)
    r.add_argument("--toolkit", default="custom_metricool")
    i = sub.add_parser("instagram"); i.add_argument("files", nargs="+"); i.add_argument("--confirm-live", action="store_true")
    i.add_argument("--ig-user", default="me"); i.add_argument("--via", choices=["composio", "gws"])
    a = ap.parse_args()
    {"detect": cmd_detect, "brands": cmd_brands, "host": cmd_host, "schedule": cmd_schedule,
     "readback": cmd_readback, "instagram": cmd_instagram}[a.cmd](a)


if __name__ == "__main__":
    main()
