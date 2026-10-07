#!/bin/bash
# SocialCrawl Superengine - masked key box (macOS).
# bash key-box.command openrouter|socialcrawl
# The key is typed into this box, never into a chat. Prints one RESULT line, never the key.
# Exit 0 saved; 2 cancel, timeout or empty (nothing written); 3 bad kind or a step failed.
umask 077
case "$1" in
  openrouter)  title='OpenRouter key';  label='Paste your OpenRouter key (starts with sk-or-). Closes in 3 minutes.'; prefix='sk-or-' ;;
  socialcrawl) title='SocialCrawl key'; label='Paste your SocialCrawl key (starts with sc_). Closes in 3 minutes.'; prefix='sc_' ;;
  *) echo 'RESULT=FAIL step=kind'; exit 3 ;;
esac
dir="$HOME/.config/$1"
file="$dir/api_key"

# osascript prints CANCEL, TIMEOUT or OK:<key>; the key stays in a variable and is never echoed.
out=$(osascript \
  -e 'try' \
  -e "set r to display dialog \"$label\" with title \"$title\" default answer \"\" with hidden answer buttons {\"Cancel\", \"Save\"} default button \"Save\" cancel button \"Cancel\" giving up after 180" \
  -e 'on error number -128' \
  -e 'return "CANCEL"' \
  -e 'end try' \
  -e 'if gave up of r then return "TIMEOUT"' \
  -e 'return "OK:" & text returned of r' 2>/dev/null) || { echo 'RESULT=FAIL step=show'; exit 3; }

case "$out" in
  CANCEL) echo 'RESULT=CANCEL'; exit 2 ;;
  TIMEOUT) echo 'RESULT=TIMEOUT'; exit 2 ;;
  OK:*) v="${out#OK:}"; out='' ;;
  *) echo 'RESULT=FAIL step=show'; exit 3 ;;
esac
v="${v#"${v%%[![:space:]]*}"}"; v="${v%"${v##*[![:space:]]}"}"
[ -n "$v" ] || { echo 'RESULT=CANCEL'; exit 2; }

{ mkdir -p "$dir"; } 2>/dev/null || { echo 'RESULT=FAIL step=folder'; exit 3; }
{ printf '%s' "$v" > "$file"; } 2>/dev/null || { echo 'RESULT=FAIL step=write'; exit 3; }
{ chmod 600 "$file"; } 2>/dev/null || { echo 'RESULT=FAIL step=acl'; exit 3; }
case "$v" in "$prefix"*) p=True ;; *) p=False ;; esac
echo "RESULT=OK len=${#v} prefix=$p"
exit 0
