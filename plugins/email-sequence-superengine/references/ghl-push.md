# GHL Push (opt-in, approval-gated)

Stage the approved email copy into GoHighLevel as templates. CRUD proven via MCP (create/read/delete).
Only run when `{{GHL_PUSH}}` = on AND the coach explicitly approves this push.

## What it does
For each of the 4 emails, create a GHL email template via the GHL MCP `create_email_template`:
- `title`: named per sequence — `Precall E1 — Confirm`, `Precall E2 — Method`, `Precall E3 — Boundary`, `Precall E4 — Access`
- `html`: the email body
- `isPlainText`: true for E1/E3/E4 (text-only), false for E2 (light-HTML)

## Hard limits (baked in)
- **Workflow timing/triggers stay MANUAL** — no MCP endpoint exists to build the sequence/workflow. The coach assigns the templates to a GHL workflow by hand. Document this in the package.
- **Templates land loose in the library** — create takes no folder param. The naming convention (above) compensates.
- **Never assign to a live workflow** and **never send to live contacts** — staging only. Approval-gated per client-work rules.
- Templates create as custom-HTML / plain-text type (not drag-drop builder) — correct for plain-text nurture.

## Flow
1. Confirm `{{GHL_PUSH}}` = on and get explicit approval.
2. Confirm GHL MCP is connected (if `create_email_template` fails → reconnect, fall back to export).
3. Create the 4 templates with the names above.
4. Report back the created template names + the manual step: "assign these to your precall workflow in GHL."
