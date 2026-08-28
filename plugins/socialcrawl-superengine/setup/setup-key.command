#!/usr/bin/env bash
# SocialCrawl Superengine — key setup (macOS / Linux)
# Double-click this file. Your key is typed into YOUR terminal, never into a chat.
cd "$(dirname "$0")" 2>/dev/null || true
B=$'\033[1m'; D=$'\033[2m'; G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; N=$'\033[0m'
KEY_DIR="$HOME/.config/socialcrawl"; KEY_FILE="$KEY_DIR/api_key"

clear
cat <<BANNER

  ${B}SocialCrawl Superengine${N}
  ${D}Connect your account${N}

  ${D}────────────────────────────────────────────${N}

  Your key is saved to a file on this computer.
  It is never typed into a chat and never leaves
  this machine except to call SocialCrawl itself.

  ${D}No account yet? Start here - 100 free credits, no card:${N}
  ${D}https://www.socialcrawl.dev/?ref=AQNU384G${N}

  ${D}Already have one? Your key is under API Keys:${N}
  ${D}https://www.socialcrawl.dev/dashboard${N}

  ${D}────────────────────────────────────────────${N}

BANNER

if [ -f "$KEY_FILE" ]; then
  printf "  ${Y}A key is already saved.${N} Replace it? [y/N] "
  read -r ans
  case "$ans" in [Yy]*) ;; *) printf "\n  Kept the existing key. Nothing changed.\n\n"; read -rp "  Press Enter to close. "; exit 0;; esac
  printf "\n"
fi

printf "  ${B}Paste your API key${N} ${D}(hidden as you type, then press Enter)${N}\n  > "
read -rs SC_KEY
printf "\n\n"

if [ -z "$SC_KEY" ]; then
  printf "  ${R}Nothing entered.${N} Run this again when you have your key.\n\n"
  read -rp "  Press Enter to close. "; exit 1
fi

case "$SC_KEY" in
  sc_*) ;;
  *) printf "  ${R}That doesn't look like a SocialCrawl key.${N}\n"
     printf "  ${D}Keys start with \"sc_\". Copy it again from your dashboard.${N}\n\n"
     read -rp "  Press Enter to close. "; exit 1;;
esac

printf "  ${D}Checking your key...${N}\n"
RESP=$(curl -s --max-time 20 -H "x-api-key: $SC_KEY" "https://www.socialcrawl.dev/v1/credits/balance" 2>/dev/null)

case "$RESP" in
  *'"success":true'*)
    BAL=$(printf '%s' "$RESP" | sed -n 's/.*"credits_remaining":\([0-9]*\).*/\1/p')
    mkdir -p "$KEY_DIR" && printf '%s' "$SC_KEY" > "$KEY_FILE" && chmod 600 "$KEY_FILE"
    unset SC_KEY
    printf "\n  ${G}Connected.${N} You have ${B}${BAL:-?}${N} credits.\n\n"
    printf "  ${D}Saved to: %s${N}\n" "$KEY_FILE"
    printf "  ${D}Only you can read it (permissions 600).${N}\n\n"
    printf "  You can close this window and go back to Claude.\n\n"
    ;;
  *401*|*"Invalid"*|*"invalid"*)
    unset SC_KEY
    printf "\n  ${R}That key was rejected.${N}\n"
    printf "  ${D}Copy it again from https://socialcrawl.dev/dashboard and retry.${N}\n"
    printf "  ${D}Nothing was saved.${N}\n\n";;
  "")
    unset SC_KEY
    printf "\n  ${R}Couldn't reach SocialCrawl.${N} Check your internet and try again.\n"
    printf "  ${D}Nothing was saved.${N}\n\n";;
  *)
    unset SC_KEY
    printf "\n  ${R}Unexpected response.${N} Nothing was saved.\n"
    printf "  ${D}%s${N}\n\n" "$(printf '%s' "$RESP" | head -c 160)";;
esac

read -rp "  Press Enter to close. "
