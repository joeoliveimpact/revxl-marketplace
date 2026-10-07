#!/usr/bin/env bash
# get-clientclub-token.sh
# Refreshes the Firebase ID token for clientclub.net (REVXL / Command Center).
# Cross-platform companion to Get-ClientClubToken.ps1.
#
# Usage:
#   export CLIENTCLUB_COMMUNITY_TOKEN_ID=$(./get-clientclub-token.sh)
#   ./clientclub doctor
#
# Refresh tokens don't expire until revoked. If the call returns INVALID_REFRESH_TOKEN,
# re-run /har-capture Phase 2 to obtain a new refresh token and save to the path below.

set -euo pipefail

API_KEY="AIzaSyB_w3vXmsI7WeQtrIOkjR6xTRVN5uOieiE"
TOKEN_FILE="${CLIENTCLUB_REFRESH_TOKEN_FILE:-$HOME/.config/clientclub-pp-cli/refresh-token.txt}"

if [[ -n "${CLIENTCLUB_REFRESH_TOKEN:-}" ]]; then
    refresh_token="$CLIENTCLUB_REFRESH_TOKEN"
elif [[ -f "$TOKEN_FILE" ]]; then
    # Strip UTF-8 BOM if present (written by Windows PowerShell 5.1) then trim whitespace
    refresh_token="$(sed '1s/^\xef\xbb\xbf//' "$TOKEN_FILE" | tr -d '[:space:]')"
else
    echo "ERROR: No refresh token. Set CLIENTCLUB_REFRESH_TOKEN or create $TOKEN_FILE" >&2
    exit 1
fi

response="$(curl -sS -X POST \
    "https://securetoken.googleapis.com/v1/token?key=$API_KEY" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "grant_type=refresh_token" \
    --data-urlencode "refresh_token=$refresh_token")"

id_token="$(printf '%s' "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id_token',''))")"
new_refresh="$(printf '%s' "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('refresh_token',''))")"

if [[ -z "$id_token" ]]; then
    echo "ERROR: refresh failed. Response: $response" >&2
    exit 1
fi

# Persist rotated refresh token if Firebase issued a new one
if [[ -n "$new_refresh" && "$new_refresh" != "$refresh_token" && -f "$TOKEN_FILE" ]]; then
    printf '%s' "$new_refresh" > "$TOKEN_FILE"
fi

printf '%s' "$id_token"
