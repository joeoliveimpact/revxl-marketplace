# Pro-Se Firm — a family-law firm in a box

A managing partner that runs your whole divorce, custody, support, or property case when you do not have a lawyer. It
researches the law, drafts your filings in plain language, reads the other side's documents forensically, builds your
courtroom scripts, watches your deadlines, and walks you through every step. It also includes a **one-shot setup** that
installs the technical pieces for you.

It carries **no one's case facts** — it asks you about your case and fills in the blanks. Mississippi is the built-in
legal spine; other states are supported on the method while that state's specifics are flagged for research.

> **This is a tool, not a lawyer.** It provides legal **information**, not legal advice, and using it creates no
> attorney-client relationship. It is provided "AS IS" with **no warranty** and **no liability** — you are responsible for
> verifying everything against official sources and for your own case. See **[DISCLAIMER.md](DISCLAIMER.md)** and
> **[LICENSE](LICENSE)** (MIT) for the full terms. It always points you to free human legal help too.

## Install (two pastes)

In Claude Code, paste these two lines:

```
/plugin marketplace add <OWNER>/<REPO>
/plugin install pro-se-firm@pro-se-firm-marketplace
```

Replace `<OWNER>/<REPO>` with wherever this marketplace is hosted (a GitHub repo), or use a local path:

```
/plugin marketplace add /path/to/this/marketplace
/plugin install pro-se-firm@pro-se-firm-marketplace
```

Then start it by just talking: say what is going on (for example, "I'm going through a divorce, I need help"), or run
the setup with "set me up."

## Reviewing it without installing (for a trusted reviewer)

Load the plugin directly, no marketplace needed:

```
claude --plugin-dir /path/to/this/marketplace/plugins/pro-se-firm
```

## The three things only you can do

Almost everything is automatic. Three things must be you, because they are about accounts, security, and owning your own
files: (1) install the app and sign in, (2) sign in to your own accounts when a feature needs one, (3) hand over your own
documents. The setup does the rest.

## What's inside

- **pro-se-firm** — the firm (managing partner + ~35 specialists, auto-firing).
- **pro-se-firm:firm-setup** — the guided one-shot installer.

## Privacy

This package is checked by an automated no-leak gate before release: it contains no real party names, addresses, contact
info, cause numbers, or other personal data. Your case facts live only in your own workspace, never in the plugin.

_Version 1.0.0 · MIT License_
