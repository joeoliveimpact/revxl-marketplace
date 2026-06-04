# GoKollab Community Superengine — Operator Guide

A plain-English walkthrough for running your community with this plugin. No terminal, no code.

## What this is
A set of commands you run inside Claude Code that handle the repetitive parts of running your clientclub community: letting new members in and setting them up, turning your group-call recordings into clean recap posts, and keeping each 1:1 client's call history up to date. You talk to it in plain English; it works the community platform behind the scenes.

## Before you start (one-time)
You'll need:
- **Claude Code desktop** installed
- Your **GoHighLevel MCP** connected — this is how it reads each member's membership tier
- **Admin access** to your clientclub community

## First-time setup — run this once
Type **`/gokollab-setup`** and follow along. Here's what happens:
1. It asks you to turn on **"bypass permissions"** (one toggle) so it can work without stopping to ask on every step — it shows you exactly where.
2. It checks your computer and **installs anything missing** for you. You don't type anything.
3. It opens a browser and asks you to **log in to your community once**. That's the only login you'll do — after that it can act on your behalf.
4. It reads your community's **channels** and shows you the list to **confirm**.
5. It asks a few questions about your **membership tiers** and **welcome messages**.
6. It runs a quick **self-test**.

About 10–15 minutes. One login, a few questions, done.

## Everyday use

### Onboard a new member
Type **`/onboard Jane Doe`**. It will:
- approve Jane from your pending-requests list,
- look up her **tier** (from her GoHighLevel tag),
- add her to the **right channels** for that tier,
- if her tier includes a **1:1 channel**, create her private channel and pin her call-recording post,
- post a **welcome** in her private channel and **introduce her** in the community.

It always shows you the **plan first** and waits for your OK before posting anything.

### Post a group-call recap
Just ask — e.g. *"post the group call from Wednesday."* It turns the Fathom recording into a featured recap post.

### 1:1 call histories
Each 1:1 client's private channel has a running "call history" post. Once wired to your schedule, new calls get added automatically.

## How tiers work
Onboarding follows a simple **recipe per tier** — which channels they join, whether they get a 1:1 channel, and which welcome they get. These live in a settings file the setup created. To change what a tier gets — or add a new tier — just tell Claude; it updates the recipe. No code.

## If something stops working
- **"It can't post / not authorized"** → your login may have expired. Run **`/gokollab-setup`** again and do the one login step; everything else is remembered.
- **"It set someone up wrong"** → tell Claude what was off; tier recipes are editable.
- **Want a health check** → ask Claude to *"run the setup verify check."*

## Under the hood (optional)
It drives a small command-line tool for your community platform (clientclub, which runs on GoHighLevel) plus your GoHighLevel and Fathom connections. You never see that layer — you just give instructions in plain English.

---
Built by Joe Olive · joe@bizzfixx.com · v0.1.0
