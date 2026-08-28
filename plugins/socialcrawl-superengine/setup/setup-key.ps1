# SocialCrawl Superengine - key setup (Windows)
# Your key is typed into YOUR terminal, never into a chat.

$dir  = Join-Path $env:USERPROFILE '.config\socialcrawl'
$file = Join-Path $dir 'api_key'

Clear-Host
Write-Host ''
Write-Host '  SocialCrawl Superengine' -ForegroundColor White
Write-Host '  Connect your account' -ForegroundColor DarkGray
Write-Host ''
Write-Host '  --------------------------------------------' -ForegroundColor DarkGray
Write-Host ''
Write-Host '  Your key is saved to a file on this computer.'
Write-Host '  It is never typed into a chat and never leaves'
Write-Host '  this machine except to call SocialCrawl itself.'
Write-Host ''
Write-Host '  No account yet? Start here - 100 free credits, no card:' -ForegroundColor DarkGray
Write-Host '  https://www.socialcrawl.dev/?ref=AQNU384G' -ForegroundColor DarkGray
Write-Host ''
Write-Host '  Already have one? Your key is under API Keys:' -ForegroundColor DarkGray
Write-Host '  https://www.socialcrawl.dev/dashboard' -ForegroundColor DarkGray
Write-Host ''
Write-Host '  --------------------------------------------' -ForegroundColor DarkGray
Write-Host ''

if (Test-Path $file) {
  Write-Host '  A key is already saved.' -ForegroundColor Yellow
  $ans = Read-Host '  Replace it? [y/N]'
  if ($ans -notmatch '^[Yy]') {
    Write-Host ''
    Write-Host '  Kept the existing key. Nothing changed.'
    Write-Host ''
    Read-Host '  Press Enter to close' | Out-Null
    exit
  }
  Write-Host ''
}

Write-Host '  Paste your API key ' -NoNewline -ForegroundColor White
Write-Host '(hidden as you type, then press Enter)' -ForegroundColor DarkGray
$sec = Read-Host '  >' -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
$key  = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
Write-Host ''

if ([string]::IsNullOrWhiteSpace($key)) {
  Write-Host '  Nothing entered. Run this again when you have your key.' -ForegroundColor Red
  Write-Host ''
  Read-Host '  Press Enter to close' | Out-Null
  exit
}
if (-not $key.StartsWith('sc_')) {
  Write-Host '  That does not look like a SocialCrawl key.' -ForegroundColor Red
  Write-Host '  Keys start with sc_ - copy it again from your dashboard.' -ForegroundColor DarkGray
  Write-Host ''
  Read-Host '  Press Enter to close' | Out-Null
  exit
}

Write-Host '  Checking your key...' -ForegroundColor DarkGray
$ok = $false
try {
  $r = Invoke-RestMethod -Uri 'https://www.socialcrawl.dev/v1/credits/balance' -Headers @{ 'x-api-key' = $key } -TimeoutSec 20 -ErrorAction Stop
  $ok = $true
} catch {
  Write-Host ''
  $code = $null
  if ($_.Exception.Response) { $code = $_.Exception.Response.StatusCode.value__ }
  if ($code -eq 401) {
    Write-Host '  That key was rejected.' -ForegroundColor Red
    Write-Host '  Copy it again from https://www.socialcrawl.dev/dashboard and retry.' -ForegroundColor DarkGray
  } else {
    Write-Host '  Could not reach SocialCrawl. Check your internet and try again.' -ForegroundColor Red
  }
  Write-Host '  Nothing was saved.' -ForegroundColor DarkGray
}

if ($ok) {
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  [IO.File]::WriteAllText($file, $key)
  $acl = Get-Acl $file
  $acl.SetAccessRuleProtection($true, $false)
  $me = [Security.Principal.WindowsIdentity]::GetCurrent().Name
  $rule = New-Object Security.AccessControl.FileSystemAccessRule($me, 'FullControl', 'Allow')
  $acl.SetAccessRule($rule)
  Set-Acl -Path $file -AclObject $acl
  Write-Host ''
  Write-Host ('  Connected. You have ' + $r.credits_remaining + ' credits.') -ForegroundColor Green
  Write-Host ''
  Write-Host ('  Saved to: ' + $file) -ForegroundColor DarkGray
  Write-Host '  Only your Windows account can read it.' -ForegroundColor DarkGray
  Write-Host ''
  Write-Host '  You can close this window and go back to Claude.'
}

$key = $null
[GC]::Collect()
Write-Host ''
Read-Host '  Press Enter to close' | Out-Null
