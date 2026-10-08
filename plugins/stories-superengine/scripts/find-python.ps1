# find-python.ps1 - find a Python >= 3.9 for stories-superengine on Windows; install one per-user if there is none.
# Tries, in order: py -3, python, python3. Each candidate is RUN with arguments and must print its version. The
# Microsoft Store "python.exe" alias stub only opens the Store when run bare; given arguments it prints "Python was
# not found..." and exits 9009, so it is rejected without opening anything. Each probe is killed after 20 s.
# None found -> unattended per-user install (no admin prompt):
#   winget install --id Python.Python.3.12 --exact --source winget --scope user --silent
#                  --accept-package-agreements --accept-source-agreements
# then the probes run again, with PATH re-read from the registry plus the per-user install folders.
# Run it from the client's workspace folder. On success it writes the interpreter's full path (one line, UTF-8, no
# BOM, no newline) to stories\.python and prints one JSON line, exit 0:
#   {"status":"ok","via":"py -3","version":"3.13.7","python":"C:\\...\\python.exe","tried":[...]}
# Use it as:  PowerShell  & (Get-Content -Raw -Encoding UTF8 stories\.python) script.py
#             Bash        "$(cat stories/.python)" script.py
# Otherwise one JSON line, exit 1: status not_found (winget failed to install a usable Python), no_winget,
# or dry_run (with "would_run"). "tried" lists each candidate and why it was rejected.
# Launch:  powershell.exe -NoProfile -ExecutionPolicy Bypass -File find-python.ps1 [-DryRun]
# -DryRun  never runs winget; reports the exact command it would run.
param([switch]$DryRun)

$tried = New-Object Collections.ArrayList
function Out-Result($status, $extra) {
  $o = [ordered]@{ status = $status }
  foreach ($k in $extra.Keys) { $o[$k] = $extra[$k] }
  $o['tried'] = @($tried)
  [pscustomobject]$o | ConvertTo-Json -Compress
}

function Probe($label, $exe, $pre) {
  if (-not $exe) { [void]$tried.Add("${label}: not found"); return $null }
  $psi = New-Object Diagnostics.ProcessStartInfo $exe, "$pre -c ""import sys;print(*sys.version_info[:3]);print(sys.executable)"""
  $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true
  $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
  $psi.StandardOutputEncoding = New-Object Text.UTF8Encoding $false
  $psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'  # a non-ASCII user folder must survive the pipe
  try { $p = [Diagnostics.Process]::Start($psi) } catch { [void]$tried.Add("${label}: could not start"); return $null }
  $out = $p.StandardOutput.ReadToEndAsync(); [void]$p.StandardError.ReadToEndAsync()
  if (-not $p.WaitForExit(20000)) { try { $p.Kill() } catch {}; [void]$tried.Add("${label}: no answer in 20 s"); return $null }
  $lines = @($out.Result -split "`r?`n")
  if ($p.ExitCode -ne 0 -or $lines.Count -lt 2 -or $lines[0] -notmatch '^(\d+) (\d+) (\d+)$') {
    [void]$tried.Add("${label}: did not run (exit $($p.ExitCode); the Microsoft Store alias stub exits 9009)"); return $null
  }
  $ver = "$($Matches[1]).$($Matches[2]).$($Matches[3])"; $py = $lines[1].Trim()
  if ([int]$Matches[1] -ne 3 -or [int]$Matches[2] -lt 9) { [void]$tried.Add("${label}: $ver is older than 3.9"); return $null }
  if (-not $py -or -not (Test-Path -LiteralPath $py -PathType Leaf)) { [void]$tried.Add("${label}: $ver but no usable path"); return $null }
  [void]$tried.Add("${label}: $ver ok")
  [ordered]@{ via = $label; version = $ver; python = $py }
}

function Find-Python($extra) {
  $cands = @(@('py -3', 'py', '-3'), @('python', 'python', ''), @('python3', 'python3', '')) + $extra
  foreach ($c in $cands) {
    $exe = $c[1]
    if (-not [IO.Path]::IsPathRooted($exe)) { $exe = (Get-Command $exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source }
    elseif (-not (Test-Path -LiteralPath $exe)) { $exe = $null }
    $r = Probe $c[0] $exe $c[2]
    if ($r) { return $r }
  }
  $null
}

$found = Find-Python @()
if (-not $found) {
  $wargs = @('install', '--id', 'Python.Python.3.12', '--exact', '--source', 'winget', '--scope', 'user', '--silent',
             '--accept-package-agreements', '--accept-source-agreements')
  $winget = (Get-Command winget -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
  if ($DryRun) { Out-Result 'dry_run' @{ winget_found = [bool]$winget; would_run = 'winget ' + ($wargs -join ' ') }; exit 1 }
  if (-not $winget) { Out-Result 'no_winget' @{ fix = 'Install Python 3.12 from python.org (per-user), then run this again.' }; exit 1 }
  & $winget @wargs *> $null
  $wcode = $LASTEXITCODE
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
  $base = Join-Path $env:LOCALAPPDATA 'Programs\Python'
  $found = Find-Python (@(,@('installed py -3', (Join-Path $base 'Launcher\py.exe'), '-3')) + @(,@('installed python', (Join-Path $base 'Python312\python.exe'), '')))
  if (-not $found) { Out-Result 'not_found' @{ winget_exit = $wcode }; exit 1 }
}

$dir = Join-Path $PWD.ProviderPath 'stories'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
[IO.File]::WriteAllText((Join-Path $dir '.python'), $found.python, (New-Object Text.UTF8Encoding $false))
Out-Result 'ok' $found
exit 0
