# process-probe.ps1 -- Windows process table probe for the background process ledger.
#
# Emits a normalised TSV snapshot on stdout. ONE code path is used for both
# recording a process and re-verifying it later, so the identity strings are
# byte-for-byte comparable across runs. Changing the format here silently
# breaks every existing ledger entry, so do not reformat casually.
#
# Line 1:  #SELF<TAB>pid,pid,pid    (this process + its ancestors + its own
#                                    descendants -- never eligible to record)
# Line n:  pid<TAB>ppid<TAB>started_epoch<TAB>started_at<TAB>rss_kb<TAB>cmd
#
# started_epoch : integer seconds since 1970-01-01 UTC. Used ONLY for the
#                 "started during this tool call" window filter.
# started_at    : invariant-culture UTC string. Part of the identity triple
#                 that must match before anything is ever stopped.
# cmd           : full command line, tabs/newlines collapsed to spaces.
#
# On failure it prints a single #ERROR line and exits 3. The caller turns that
# into a visible "ledger degraded" record. It never fails silently.

$ErrorActionPreference = 'Stop'

try {
    $procs = @(Get-CimInstance -ClassName Win32_Process -Property ProcessId,ParentProcessId,CreationDate,WorkingSetSize,CommandLine,Name)
} catch {
    Write-Output ("#ERROR`tprocess enumeration failed: " + $_.Exception.Message)
    exit 3
}

if ($procs.Count -eq 0) {
    Write-Output "#ERROR`tprocess enumeration returned nothing"
    exit 3
}

$byId = @{}
$children = @{}
foreach ($p in $procs) {
    $id = [int]$p.ProcessId
    $pp = [int]$p.ParentProcessId
    $byId[$id] = $p
    if (-not $children.ContainsKey($pp)) { $children[$pp] = New-Object System.Collections.ArrayList }
    [void]$children[$pp].Add($id)
}

# --- self chain: this powershell, everything above it (bash, cmd, the Claude
# --- harness) and everything below it. None of these may ever be recorded.
$chain = New-Object 'System.Collections.Generic.HashSet[int]'
$cur = [int]$PID
$guard = 0
while ($cur -gt 0 -and $guard -lt 32) {
    if (-not $chain.Add($cur)) { break }
    $o = $byId[$cur]
    if (-not $o) { break }
    $cur = [int]$o.ParentProcessId
    $guard++
}
$queue = New-Object System.Collections.Queue
$queue.Enqueue([int]$PID)
while ($queue.Count -gt 0) {
    $n = [int]$queue.Dequeue()
    if ($children.ContainsKey($n)) {
        foreach ($c in $children[$n]) {
            if ($chain.Add([int]$c)) { $queue.Enqueue([int]$c) }
        }
    }
}

$epochBase = New-Object System.DateTime(1970, 1, 1, 0, 0, 0, [System.DateTimeKind]::Utc)
$inv = [System.Globalization.CultureInfo]::InvariantCulture
$sb = New-Object System.Text.StringBuilder

[void]$sb.AppendLine("#SELF`t" + (($chain | Sort-Object) -join ','))

foreach ($p in $procs) {
    $created = $p.CreationDate
    if ($null -eq $created) { continue }
    $utc = $created.ToUniversalTime()
    $epoch = [int64]($utc - $epochBase).TotalSeconds
    $stamp = $utc.ToString('yyyy-MM-ddTHH:mm:ssZ', $inv)
    $rss = 0
    if ($null -ne $p.WorkingSetSize) { $rss = [int64]([int64]$p.WorkingSetSize / 1024) }
    $cmd = $p.CommandLine
    if ([string]::IsNullOrWhiteSpace($cmd)) { $cmd = '(' + $p.Name + ')' }
    $cmd = ($cmd -replace "[`t`r`n]", ' ').Trim()
    [void]$sb.AppendLine(([string]$p.ProcessId) + "`t" + ([string]$p.ParentProcessId) + "`t" + ([string]$epoch) + "`t" + $stamp + "`t" + ([string]$rss) + "`t" + $cmd)
}

[Console]::Out.Write($sb.ToString())
exit 0
