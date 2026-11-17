"""Threat scan and secret-path gate for model-written drafts. Any hit blocks the draft; nothing is redacted.

scan(): hidden (zero-width / bidi) characters, prompt-injection phrases, role/tool markup, commands anywhere
in a line, credential and exfiltration requests, and URLs to hosts not in harvest.known_hosts.
secret_paths(): lines that name a secret file or directory (.env files, .credentials.json, ssh private keys,
/etc/**/*key*, token/ files, secret dirs), plus any harvest.secret_patterns. Reports line numbers.
Fails closed: a false positive costs one draft (kept in blocked/ for review); a miss could reach an agent
that reads the brain.
"""
import re

HIDDEN = re.compile("[­​-‏‪-‮⁠-⁤⁦-⁩﻿]")
CMD = (r"sudo|su|rm|curl|wget|chmod|chown|bash|sh|zsh|python3?|node|nc|ncat|scp|ssh|systemctl|crontab|docker|"
       r"eval|exec|base64|mkfifo|kill|pkill|dd|mv|cp|tee|apt|pip|npm|npx|git|claude")
RULES = [
    ("injection phrase", re.compile(
        r"(?i)\b(ignore|disregard|forget|override|bypass)\b[^.\n]{0,40}\b(instructions?|rules|prompts?|guardrails?|"
        r"system|safety|polic(?:y|ies))\b|\b(system prompt|developer message|you are now|new instructions|"
        r"jailbreak|do anything now|pretend (?:to be|you are)|act as (?:root|admin|the system))\b")),
    ("role markup", re.compile(r"(?i)<\s*/?\s*(system|assistant|user|tool|function|instructions?)\b[^>]*>|\[/?INST\]")),
    ("code block", re.compile(r"^\s*(```|~~~)", re.M)),
    ("shell in backticks", re.compile(rf"`\s*(?:sudo\s+)?(?:{CMD})\s+[^`]+`")),
    ("shell prompt", re.compile(r"^\s*(?:[-*>]\s*)?\$\s+\S", re.M)),
    ("command line", re.compile(rf"^\s*(?:[-*>]\s*)?(?:{CMD})\s+(?:-{{1,2}}\w|/|~/|\./)", re.M)),
    # Commands anywhere in a line. Prose like "the user has sudo." or "restarted with systemctl" passes.
    ("command", re.compile(
        r"(?i)\bsudo\s+[\w/~.-]"
        r"|\brm\s+-\w*[rf]"
        r"|\bsystemctl\s+(?:start|stop|restart|reload|enable|disable|mask|unmask|kill|edit|daemon-reload)\b"
        r"|\b(?:curl|wget)\s+(?:-|\S+://|\S+\.\S+/)"
        r"|\bchmod\s+(?:-\w+\s+)?(?:[0-7]{3,4}|[ugoa]*[-+=][rwxXst]+)\s+\S|\bchown\s+(?:-\w+\s+)?(?:[\w.-]+:[\w.-]*\s+\S|\S+\s+/)"
        r"|\b(?:ssh|scp|rsync)\s+(?:-\w|\S+@\S+|\S+:\S*)"
        r"|\bbase64\s+(?:-d|--decode)|\beval\s*[(\"'$`]"
        r"|\b(?:bash|sh|zsh|python3?|node|perl)\s+-[ce]\b|\bnc(?:at)?\s+-\w*e"
        r"|\bdocker\s+(?:exec|run|cp)\b|\bcrontab\s+-[er]\b|\bmkfifo\b|\bdd\s+if="
        r"|/dev/tcp/|>\s*/(?:etc|root|home|opt)/")),
    ("pipe to shell", re.compile(r"\|\s*(?:sudo\s+)?(?:ba|z)?sh\b")),
    ("command substitution", re.compile(r"\$\([^)]*\)")),
    # "Paste/share/send ... password/token/key" asks someone to put a secret in chat. A rule that forbids it
    # ("Never paste passwords...", "Do not share keys...") passes.
    ("credential request", re.compile(
        r"(?i)(?<!never )(?<!not )(?<!n't )(?<!no )\b(paste|share|send|post|give|provide|type|enter|drop|dm|text|"
        r"forward|reply with|tell (?:me|us|the bot))\b[^.\n]{0,50}?\b(passwords?|passcodes?|passwd|credentials?|"
        r"tokens?|api[ -]?keys?|secret(?: keys?)?|secrets|private keys?|ssh keys?|keys|2fa codes?|otps?|mfa codes?|"
        r"verification codes?|login codes?|cookies?)\b")),
    ("exfiltration request", re.compile(
        r"(?i)\b(send|forward|post|upload|e-?mail|share|transfer|copy|leak|exfiltrate|dm|text|paste)\b[^.\n]{0,60}?"
        r"\b(?:to|at)\b\s*(?:\S+@\S+|\S+://|\[(?:EMAIL|PHONE|NUMBER)\]|\+?\d[\d\s().-]{6,}\d"
        # any bare domain, except file names ("copy it to card.md" is not a host)
        r"|[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?!(?:md|json|jsonl|py|sh|txt|log|ya?ml|toml|csv|m?js|ts|html|pdf|db)\b)"
        r"[a-z]{2,}\b|this (?:address|number|link|url))")),
]
URL = re.compile(r"(?i)\b(?:[a-z][a-z0-9+.-]*)://([^/\s:?#)>\]'\"]+)")

SECRET_PATHS = [
    (".env file", r"(?<![\w.-])\.env(?:\.[\w-]+)?(?![\w-])"),
    ("credentials file", r"\.?credentials\.json\b|\.git-credentials\b|\.netrc\b|\.pgpass\b|\.npmrc\b|\.pypirc\b"),
    ("ssh private key", r"/\.ssh/(?!\S*\.pub\b)\S+|\bid_(?:rsa|dsa|ecdsa|ed25519)(?:_sk)?\b(?!\.pub)"),
    ("key file", r"\b[\w.-]+\.(?:pem|p12|pfx|key)\b"),
    ("/etc key path", r"/etc/\S*key\S*"),
    ("token file", r"(?<![\w-])tokens?/[\w.@-]+"),
    ("secret dir", r"(?:~|/[\w.-]+)*/(?:\.aws|\.gnupg|\.kube|\.docker|\.password-store|secrets?|private)/\S*"),
]


def scan(text, known_hosts=("github.com",)):
    """Returns a list of reasons; empty means clean. Hidden characters are flagged, then removed so
    they can't split a word to slip past the patterns below."""
    hits = ["hidden characters (zero-width or bidi)"] if HIDDEN.search(text) else []
    text = HIDDEN.sub("", text)
    hits += [f"{name}: {m.group(0)[:40]!r}" for name, rx in RULES for m in [rx.search(text)] if m]
    for m in URL.finditer(text):
        host = m.group(1).lower().rstrip(".")
        if not any(host == h or host.endswith("." + h) for h in known_hosts):
            hits.append(f"unknown host: {host[:60]}")
    return hits


def secret_paths(text, extra=()):
    """[(line_number, label, matched text)] for every line naming a secret path. Never redacts."""
    rules = [(label, re.compile(rx, re.I)) for label, rx in SECRET_PATHS]
    rules += [("secret pattern", re.compile(rx, re.I)) for rx in extra or ()]
    hits = []
    for n, line in enumerate(HIDDEN.sub("", text).split("\n"), 1):
        for label, rx in rules:
            m = rx.search(line)
            if m:
                hits.append((n, label, m.group(0)[:60]))
    return hits


def secret_reasons(text, extra=()):
    return [f"secret path on line {n} ({label}): {s!r}" for n, label, s in secret_paths(text, extra)]
