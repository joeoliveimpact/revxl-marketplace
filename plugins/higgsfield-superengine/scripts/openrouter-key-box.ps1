# openrouter-key-box.ps1 - masked box for an OpenRouter API key (Windows). Part of higgsfield-superengine (Jev, optional).
# Writes the shared file %USERPROFILE%\.config\openrouter\api_key (every plugin's Jev layer reads it), readable by the
# current Windows account only (the socialcrawl setup-key.ps1 ACL pattern: inheritance off, FullControl for the
# current user). The ACL is set on the file BEFORE the key is written, and the file is moved into place whole.
# The key never reaches stdout or Claude.
# Launch:  powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File openrouter-key-box.ps1 [-Force]
# Prints exactly one word:
#   saved (exit 0) | cancelled (exit 1, also on timeout) | invalid (exit 2: not shaped like sk-or-...)
#   exists (exit 3: a key file is already there and -Force was not given; no box shown, nothing changed)
# -Force         replace an existing key file (the caller must ask the client first).
# -TimeoutSec N  how long the box stays open (default 300 = 5 minutes).
# -Test          no window: reads $env:OPENROUTER_KEY_BOX_TEST_INPUT and writes api_key_keyboxtest in the same
#                folder, never the real api_key.
param([switch]$Force, [switch]$Test, [int]$TimeoutSec = 300)
$ErrorActionPreference = 'Stop'
$dir = Join-Path $env:USERPROFILE '.config\openrouter'
$file = Join-Path $dir $(if ($Test) { 'api_key_keyboxtest' } else { 'api_key' })
if ((Test-Path -LiteralPath $file) -and -not $Force) { 'exists'; exit 3 }

if ($Test) {
  $text = $env:OPENROUTER_KEY_BOX_TEST_INPUT
} else {
  Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing
  [Windows.Forms.Application]::EnableVisualStyles()
  $f = New-Object Windows.Forms.Form; $f.Text = 'OpenRouter API key'; $f.Size = New-Object Drawing.Size(500,210)
  $f.StartPosition = 'CenterScreen'; $f.TopMost = $true; $f.FormBorderStyle = 'FixedDialog'; $f.MaximizeBox = $false; $f.MinimizeBox = $false
  $l = New-Object Windows.Forms.Label; $l.SetBounds(12,10,470,50)
  $l.Text = "Paste your OpenRouter API key here (it starts with sk-or-).`n" +
            "Get it at openrouter.ai > Keys > Create Key. It stays on this computer."
  $t = New-Object Windows.Forms.TextBox; $t.UseSystemPasswordChar = $true; $t.SetBounds(12,70,460,24)
  $ok = New-Object Windows.Forms.Button; $ok.Text = 'Save'; $ok.SetBounds(296,115,80,28); $ok.DialogResult = 'OK'
  $no = New-Object Windows.Forms.Button; $no.Text = 'Cancel'; $no.SetBounds(392,115,80,28); $no.DialogResult = 'Cancel'
  $f.AcceptButton = $ok; $f.CancelButton = $no; $f.Controls.AddRange(@($l,$t,$ok,$no))
  $tm = New-Object Windows.Forms.Timer; $tm.Interval = [Math]::Max(1, $TimeoutSec) * 1000
  $tm.Add_Tick({ $tm.Stop(); $f.DialogResult = 'Abort' })
  $f.Add_Shown({ $f.Activate(); [void]$t.Focus(); $tm.Start() })
  $r = $f.ShowDialog(); $text = $t.Text; $tm.Dispose(); $f.Dispose()
  if ($r -ne 'OK') { $text = $null; 'cancelled'; exit 1 }
}

$key = "$text".Trim(); $text = $null
if ($key -cnotmatch '^sk-or-[A-Za-z0-9_-]{16,256}\z') { $key = $null; 'invalid'; exit 2 }
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$tmp = "$file.tmp"
[IO.File]::WriteAllText($tmp, '')
$acl = Get-Acl -LiteralPath $tmp
$acl.SetAccessRuleProtection($true, $false)
$me = [Security.Principal.WindowsIdentity]::GetCurrent().User
$acl.SetAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($me, 'FullControl', 'Allow')))
Set-Acl -LiteralPath $tmp -AclObject $acl
[IO.File]::WriteAllText($tmp, $key)
$key = $null
Move-Item -LiteralPath $tmp -Destination $file -Force
'saved'
