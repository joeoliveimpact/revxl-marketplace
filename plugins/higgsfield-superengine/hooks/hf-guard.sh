#!/bin/sh
# hf-guard.sh - starts hf_guard.py on Mac/Linux. hooks.json runs it with `sh`, beside the Windows `py -3` entry.
# Windows machines with Git can run `sh` too: there this script does nothing (and hf_guard.py --only-on posix would
# stand down anyway), so exactly one guard decides per OS.
# Python is looked for in fixed places, never via PATH (an app opened from the Dock has a minimal PATH):
#   Homebrew, /usr/local, python.org; and /usr/bin/python3 only when Apple's developer tools are installed
#   (otherwise that file opens an install pop-up, and a hook would open it on every command).
# No Python: the plugin's money paths (hf_rest, the guard, the ledger, the raw API, the SDK) are blocked (exit 2);
# everything else passes (exit 0), including setup's own find-python.sh.
case "$(uname -s 2>/dev/null)" in
  Darwin|Linux) ;;
  *) exit 0 ;;
esac
here=$(dirname "$0")
for py in /opt/homebrew/bin/python3 /usr/local/bin/python3 \
          /Library/Frameworks/Python.framework/Versions/3.*/bin/python3; do
  if [ -x "$py" ] && "$py" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
    exec "$py" -B "$here/hf_guard.py" hook --only-on posix
  fi
done
if [ "$(uname -s)" = Linux ] || xcode-select -p >/dev/null 2>&1; then
  if [ -x /usr/bin/python3 ] && /usr/bin/python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
    exec /usr/bin/python3 -B "$here/hf_guard.py" hook --only-on posix
  fi
fi
if grep -qiE 'hf_rest|hf_guard|hf-guard|ledger\.py|api\.higgsfield\.ai|higgsfield[-_]client'; then
  echo "Blocked by the higgsfield-superengine spend guard: Python is not set up for this plugin yet, so the guard cannot check this. Run Higgsfield setup first (say: set up Higgsfield)." >&2
  exit 2
fi
exit 0
