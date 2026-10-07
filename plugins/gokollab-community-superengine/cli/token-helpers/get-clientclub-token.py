#!/usr/bin/env python3
"""
get-clientclub-token.py
Refreshes the Firebase ID token for clientclub.net (REVXL / Command Center).
Cross-platform companion to Get-ClientClubToken.ps1.

Usage:
    export CLIENTCLUB_COMMUNITY_TOKEN_ID=$(./get-clientclub-token.py)
    ./clientclub doctor

Refresh tokens don't expire until revoked. If the call returns INVALID_REFRESH_TOKEN,
re-run /har-capture Phase 2 to obtain a new refresh token.
"""
import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

API_KEY = "AIzaSyB_w3vXmsI7WeQtrIOkjR6xTRVN5uOieiE"
TOKEN_FILE = Path(
    os.environ.get("CLIENTCLUB_REFRESH_TOKEN_FILE")
    or (Path.home() / ".config" / "clientclub-pp-cli" / "refresh-token.txt")
)

refresh_token = os.environ.get("CLIENTCLUB_REFRESH_TOKEN")
if not refresh_token:
    if not TOKEN_FILE.exists():
        sys.stderr.write(f"ERROR: No refresh token. Set CLIENTCLUB_REFRESH_TOKEN or create {TOKEN_FILE}\n")
        sys.exit(1)
    # utf-8-sig strips a UTF-8 BOM if present (PowerShell 5.1's Set-Content writes one)
    refresh_token = TOKEN_FILE.read_text(encoding='utf-8-sig').strip()

req = urllib.request.Request(
    f"https://securetoken.googleapis.com/v1/token?key={API_KEY}",
    data=urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)

try:
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
except urllib.error.HTTPError as e:
    sys.stderr.write(f"ERROR: refresh failed ({e.code}): {e.read().decode()}\n")
    sys.exit(1)

id_token = body.get("id_token")
new_refresh = body.get("refresh_token")

if not id_token:
    sys.stderr.write(f"ERROR: no id_token in response: {body}\n")
    sys.exit(1)

# Persist rotated refresh token if Firebase issued a new one
if new_refresh and new_refresh != refresh_token and TOKEN_FILE.exists():
    TOKEN_FILE.write_text(new_refresh)

sys.stdout.write(id_token)
