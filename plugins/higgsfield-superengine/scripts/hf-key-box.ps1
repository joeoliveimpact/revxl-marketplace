# hf-key-box.ps1 - masked box for the Higgsfield API key (Windows). Part of higgsfield-superengine.
# The client pastes the ONE key string the console shows ONCE: "KEY_ID:KEY_SECRET" (open.higgsfield.ai > API keys).
# Surrounding spaces/line breaks are ignored. Shape checked: a UUID-shaped key id, ":", then a secret made of the
# characters hf_rest.py accepts (8-256 of A-Z a-z 0-9 . _ ~ + / = -).
# Saves HF_API_KEY_ID / HF_API_KEY_SECRET as Windows user environment variables (HKCU\Environment), where hf_rest.py
# finds them. The key never reaches stdout, a file, or Claude.
# Launch:  powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File hf-key-box.ps1
# Prints exactly one word: saved (exit 0) | cancelled (exit 1, also when the box times out) | invalid (exit 2)
# -TimeoutSec N  how long the box stays open (default 300 = 5 minutes).
# -Test          no window: reads the pasted text from $env:HF_KEY_BOX_TEST_INPUT and saves to
#                HF_API_KEY_ID_KEYBOXTEST / HF_API_KEY_SECRET_KEYBOXTEST, so a test can never touch the real key.
param([switch]$Test, [int]$TimeoutSec = 300)
$ErrorActionPreference = 'Stop'

if ($Test) {
  $text = $env:HF_KEY_BOX_TEST_INPUT; $suffix = '_KEYBOXTEST'
} else {
  $suffix = ''
  Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing
  [Windows.Forms.Application]::EnableVisualStyles()
  $f = New-Object Windows.Forms.Form; $f.Text = 'Higgsfield API key'; $f.Size = New-Object Drawing.Size(500,230)
  $f.StartPosition = 'CenterScreen'; $f.TopMost = $true; $f.FormBorderStyle = 'FixedDialog'; $f.MaximizeBox = $false; $f.MinimizeBox = $false
  $l = New-Object Windows.Forms.Label; $l.SetBounds(12,10,470,70)
  $l.Text = "Paste your whole Higgsfield API key here (it looks like ID:SECRET).`n`n" +
            "Get it at open.higgsfield.ai > API keys > Create API key. It is shown only once, " +
            "so paste it here BEFORE you click Done there. It stays on this computer."
  $t = New-Object Windows.Forms.TextBox; $t.UseSystemPasswordChar = $true; $t.SetBounds(12,90,460,24)
  $ok = New-Object Windows.Forms.Button; $ok.Text = 'Save'; $ok.SetBounds(296,135,80,28); $ok.DialogResult = 'OK'
  $no = New-Object Windows.Forms.Button; $no.Text = 'Cancel'; $no.SetBounds(392,135,80,28); $no.DialogResult = 'Cancel'
  $f.AcceptButton = $ok; $f.CancelButton = $no; $f.Controls.AddRange(@($l,$t,$ok,$no))
  $tm = New-Object Windows.Forms.Timer; $tm.Interval = [Math]::Max(1, $TimeoutSec) * 1000
  $tm.Add_Tick({ $tm.Stop(); $f.DialogResult = 'Abort' })
  $f.Add_Shown({ $f.Activate(); [void]$t.Focus(); $tm.Start() })
  $r = $f.ShowDialog(); $text = $t.Text; $tm.Dispose(); $f.Dispose()
  if ($r -ne 'OK') { $text = $null; 'cancelled'; exit 1 }
}

$m = [regex]::Match("$text".Trim(), '^([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}):([A-Za-z0-9._~+/=-]{8,256})\z')
$text = $null
if (-not $m.Success) { 'invalid'; exit 2 }
# The user-scope SetEnvironmentVariable of .NET Framework also broadcasts WM_SETTINGCHANGE("Environment"), so programs
# started from Explorer afterwards see the key. Programs already running (Claude Code included) keep their old copy;
# hf_rest.py covers that by reading HKCU\Environment itself.
[Environment]::SetEnvironmentVariable("HF_API_KEY_ID$suffix", $m.Groups[1].Value, 'User')
[Environment]::SetEnvironmentVariable("HF_API_KEY_SECRET$suffix", $m.Groups[2].Value, 'User')
$m = $null
'saved'
