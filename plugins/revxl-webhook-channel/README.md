# revxl-webhook-channel

> Turn any HTTP webhook into a Claude Code session event. Two-way, with permission relay.

A custom [Channel](https://code.claude.com/docs/en/channels) for Claude Code. Listens on a local HTTP port; every POST becomes a `<channel source="revxl-webhook">` event your agents can react to.

---

## What this plugin does

`revxl-os-superengine` and other coaching superengines need event triggers that aren't chat: GoHighLevel sending a new-deal webhook, Cal.com sending a booking, Stripe sending a payment, your own Meta Graph API app sending a DM event. This channel is the receiver.

It's also the foundation for the OpenClaw-killer install path: external services push events into your Claude Code session live, no polling, no separate agent runtime.

---

## Features

- **Two-way bridge**: Claude reads inbound webhooks; agents send replies/notifications back via `reply` tool
- **Permission relay**: Approve tool use from your phone (when paired with a chat channel like Telegram)
- **Sender gating**: Allowlist senders by signature header — drops anything that doesn't match
- **Pre-wired routes**: `/ghl`, `/calcom`, `/stripe`, `/dm`, plus a generic `/event` catch-all
- **localhost only**: Bound to 127.0.0.1; expose via your own tunnel (ngrok, Cloudflare Tunnel) when you want public reach

---

## Install

```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install revxl-webhook-channel@revxl-marketplace
```

This plugin requires [Bun](https://bun.sh). Install with:
```bash
curl -fsSL https://bun.sh/install | bash
```

---

## Run

During the Channels research preview, custom channels need the dev flag:

```bash
claude --dangerously-load-development-channels plugin:revxl-webhook-channel@revxl-marketplace
```

For permission relay (recommended), also enable a chat channel:

```bash
claude \
  --channels plugin:telegram@claude-plugins-official \
  --dangerously-load-development-channels plugin:revxl-webhook-channel@revxl-marketplace
```

---

## Configure

Configuration lives at `~/.claude/channels/revxl-webhook-channel/config.json`. The `os-setup` skill from `revxl-os-superengine` writes this for you. Manual format:

```json
{
  "port": 8788,
  "allowedSenders": ["dev"],
  "routes": {
    "/ghl": { "source": "ghl", "secret": "..." },
    "/calcom": { "source": "calcom", "secret": "..." },
    "/stripe": { "source": "stripe", "secret": "..." }
  }
}
```

Each `secret` is checked against the `X-Signature` header (or platform-specific equivalent) to authenticate inbound webhooks.

---

## Status

v0.1.0 — scaffold only. Webhook server and routing not yet implemented.

This plugin is in the Channels research preview path. To run on a client machine without the `--dangerously-load-development-channels` flag, the plugin will need to be approved by Anthropic for the official allowlist OR added to your organization's `allowedChannelPlugins` managed setting.

---

## License

MIT — see `LICENSE`.

---

## See also

- [Channels reference (Anthropic)](https://code.claude.com/docs/en/channels-reference)
- [revxl-os-superengine](../revxl-os-superengine) — the superengine that consumes these events
