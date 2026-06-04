# Get-ClientClubToken.ps1
# Refreshes the Firebase ID token for clientclub.net (REVXL / Command Center)
# Usage: $env:CLIENTCLUB_COMMUNITY_TOKEN_ID = & .\Get-ClientClubToken.ps1
#
# Reads refresh token from $env:CLIENTCLUB_REFRESH_TOKEN, falling back to
# ~/.config/clientclub-pp-cli/refresh-token.txt
#
# Refresh tokens don't expire until revoked. If the call returns INVALID_REFRESH_TOKEN,
# re-run /har-capture to get a new storage-state.json and extract the new refresh token.

$ErrorActionPreference = 'Stop'

$apiKey = 'AIzaSyB_w3vXmsI7WeQtrIOkjR6xTRVN5uOieiE'
$tokenPath = Join-Path $env:USERPROFILE '.config\clientclub-pp-cli\refresh-token.txt'

$refreshToken = if ($env:CLIENTCLUB_REFRESH_TOKEN) {
    $env:CLIENTCLUB_REFRESH_TOKEN
} elseif (Test-Path $tokenPath) {
    (Get-Content $tokenPath -Raw).Trim()
} else {
    Write-Error "No refresh token found. Set CLIENTCLUB_REFRESH_TOKEN or create $tokenPath"
    exit 1
}

$resp = Invoke-RestMethod `
    -Uri "https://securetoken.googleapis.com/v1/token?key=$apiKey" `
    -Method POST `
    -Body "grant_type=refresh_token&refresh_token=$refreshToken" `
    -ContentType 'application/x-www-form-urlencoded'

# If Firebase rotated the refresh token, write the new one back to disk
if ($resp.refresh_token -and $resp.refresh_token -ne $refreshToken -and (Test-Path $tokenPath)) {
    Set-Content -Path $tokenPath -Value $resp.refresh_token -Encoding utf8 -NoNewline
}

# Output ONLY the idToken — caller assigns to env var
$resp.id_token
