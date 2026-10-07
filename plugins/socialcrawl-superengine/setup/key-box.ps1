# SocialCrawl Superengine - masked key box (Windows).
# powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File key-box.ps1 -Kind openrouter|socialcrawl
# The key is typed into this box, never into a chat. Prints one RESULT line, never the key.
# Exit 0 saved; 2 cancel, timeout or empty (nothing written); 3 bad kind or a step failed.
# A failed step leaves an existing key as it was (see the write step below).
# Read from $args, not param(): a bare "-Kind" with no value must still exit 3, not 1.
$Kind = if ($args.Count -eq 2 -and $args[0] -eq '-Kind') { [string]$args[1] } else { '' }
$ErrorActionPreference = 'Stop'

switch -CaseSensitive ($Kind) {
  'openrouter'  { $title = 'OpenRouter key';  $label = 'Paste your OpenRouter key (starts with sk-or-). Closes in 3 minutes.'; $prefix = 'sk-or-' }
  'socialcrawl' { $title = 'SocialCrawl key'; $label = 'Paste your SocialCrawl key (starts with sc_). Closes in 3 minutes.'; $prefix = 'sc_' }
  default       { 'RESULT=FAIL step=kind'; exit 3 }
}

try {
  Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing
  $f = New-Object Windows.Forms.Form; $f.Text = $title; $f.Size = New-Object Drawing.Size(540,170)
  $f.StartPosition = 'CenterScreen'; $f.TopMost = $true; $f.FormBorderStyle = 'FixedDialog'; $f.MaximizeBox = $false; $f.MinimizeBox = $false
  $l = New-Object Windows.Forms.Label; $l.Text = $label; $l.SetBounds(12,12,500,20)
  $t = New-Object Windows.Forms.TextBox; $t.UseSystemPasswordChar = $true; $t.SetBounds(12,40,500,24)
  $ok = New-Object Windows.Forms.Button; $ok.Text = 'Save'; $ok.SetBounds(336,80,80,28); $ok.DialogResult = 'OK'
  $no = New-Object Windows.Forms.Button; $no.Text = 'Cancel'; $no.SetBounds(432,80,80,28); $no.DialogResult = 'Cancel'
  $f.AcceptButton = $ok; $f.CancelButton = $no; $f.Controls.AddRange(@($l,$t,$ok,$no))
  $tm = New-Object Windows.Forms.Timer; $tm.Interval = 180000; $tm.Add_Tick({ $tm.Stop(); $f.DialogResult = 'Abort' })
  $f.Add_Shown({ $f.Activate(); [void]$t.Focus(); $tm.Start() })
  $r = $f.ShowDialog(); $v = $t.Text.Trim(); $tm.Dispose(); $f.Dispose()
} catch { 'RESULT=FAIL step=show'; exit 3 }

if ($r -eq 'Abort') { 'RESULT=TIMEOUT'; exit 2 }
if ($r -ne 'OK' -or $v.Length -eq 0) { 'RESULT=CANCEL'; exit 2 }

try {
  $dir  = Join-Path $env:USERPROFILE ('.config\' + $Kind)
  $file = Join-Path $dir 'api_key'
  [void](New-Item -ItemType Directory -Path $dir -Force)
  # New-Item returns nothing, without an error, when .config is a file.
  if (-not (Test-Path -LiteralPath $dir -PathType Container)) { throw 'no folder' }
} catch { 'RESULT=FAIL step=folder'; exit 3 }

# Only the key file is written: no temp or backup file. The old key's bytes are held in memory
# and put back if the write or the ACL step fails; a new file is deleted instead.
$had = Test-Path -LiteralPath $file -PathType Leaf
$old = $null
try { if ($had) { $old = [IO.File]::ReadAllBytes($file) } }
catch { 'RESULT=FAIL step=write'; exit 3 }
function Undo { try { if ($had) { [IO.File]::WriteAllBytes($file, $old) } else { [IO.File]::Delete($file) } } catch {} }

try { [IO.File]::WriteAllText($file, $v) }
catch { Undo; 'RESULT=FAIL step=write'; exit 3 }

# Owner-only, as setup-key.ps1, after the write so a failed step never touches the old key's ACL.
# Explicit rules are cleared too, so an extra rule on an old key file doesn't survive.
try {
  $me = [Security.Principal.WindowsIdentity]::GetCurrent().Name
  $acl = Get-Acl -LiteralPath $file
  $acl.SetAccessRuleProtection($true, $false)
  foreach ($a in @($acl.Access)) { [void]$acl.RemoveAccessRuleSpecific($a) }
  $rule = New-Object Security.AccessControl.FileSystemAccessRule($me, 'FullControl', 'Allow')
  $acl.SetAccessRule($rule)
  Set-Acl -LiteralPath $file -AclObject $acl
} catch { Undo; 'RESULT=FAIL step=acl'; exit 3 }

"RESULT=OK len=$($v.Length) prefix=$($v.StartsWith($prefix, [StringComparison]::Ordinal))"
exit 0
