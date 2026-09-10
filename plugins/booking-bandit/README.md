# booking-bandit

> Drafts your Instagram DM replies in your own voice, so more conversations turn into booked calls without you living in your inbox. For online coaches.

---

## Status: skeleton release (v0.0.1)

This release registers the plugin in the catalog and does nothing else yet. There is no drafting logic in it. What you get today is the plugin structure and one reserved placeholder skill, `bb-draft`, which does not draft anything.

That is deliberate. The catalog entry ships first so the plugin is installable and version-tracked, and so every later release reaches you as an update rather than a fresh install.

---

## What Booking Bandit is for

Your DMs are where the calls get booked, and answering them properly takes time you do not have. Booking Bandit is being built to read a conversation, write the next reply the way you would have written it, and queue it for you. You stay the sender. It removes the blank-page part, not your judgment.

---

## What lands in later releases

- **The drafting engine.** An agent that carries the reply rules and the DM knowledge base, and writes in the voice from your own brand profile rather than a generic one.
- **Setup.** A guided first run that connects your Instagram business inbox and asks for the few details a draft needs: your booking link, your typical price range, and your proof.
- **The inbox routine.** A scheduled check that picks up new messages and queues drafts for you to review.
- **Sending and tuning.** Sending stays off by default and behind explicit checks; a tuning skill lets you move the dials inside guardrails.

Nothing you or your prospects write is sent anywhere outside your own machine.

---

## Install

**Claude Code**

```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install booking-bandit@revxl-marketplace
```

**Claude Desktop**

Customize, then Skills, then add `joeoliveimpact/revxl-marketplace` under Personal plugins, sync, and install booking-bandit.

---

## License

MIT. See LICENSE.
