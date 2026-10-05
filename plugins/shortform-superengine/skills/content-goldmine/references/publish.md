# Publishing the Goldmine dashboard

**Always save the HTML first, then publish it as an Artifact.** The saved file is the
copy that cannot get lost; the Artifact is the page the client opens and shares. The
`dashboard` step has already saved the file and printed its path (`Dashboard saved:`).
Never publish from anywhere else, and never edit the page by hand.

## First publish (no `goldmine.dashboard_url` in state)

Load the `artifact-capabilities` skill first: the Artifact tool asks for it before any
`capabilities` value is passed. Then call the Artifact tool:

```
Artifact
  file_path:    <the path printed after "Dashboard saved:">
  title:        Content Goldmine
  icon:         chart
  description:  What broke out in your field this pull: the reels, their hooks, topics and lead magnets.
  capabilities: {"db": {"rules": [{"path": "bank", "read": "admin", "write": "admin"}]}}
```

- `title` is a fallback only: the page carries its own `<title>`.
- `db` is the runtime capability the page's Brainstorm Bank asks for
  (`window.claude.use('db')` in the page), and `bank` is the collection it saves into,
  one document per saved item. The rule keeps the Bank to the owner.
- The Artifact starts private. Sharing it is the client's call.

Store the link the tool returns as `goldmine.dashboard_url` in state, then give it to
the client.

## A later pull (the link is in state)

Update the same Artifact, so the client keeps one link:

```
Artifact
  url:        <goldmine.dashboard_url>
  file_path:  <the new path printed after "Dashboard saved:">
  label:      Pull of <MM.DD.YY>
```

- Leave out `icon` and `capabilities`: an update keeps what the page has.
- In a chat that has not opened this Artifact yet, read it first (`action: "read"` with
  the same `url`); the tool refuses an update to a page this chat has not seen.
- The link no longer opens (deleted, or a different account): publish it as new (the
  first publish above), replace `goldmine.dashboard_url`, and tell the client the link
  changed.

## If publishing fails

Do not retry in a loop. Tell the client plainly: "Your Goldmine is saved on your
computer at <path>. Open that file in any browser to use it. The Brainstorm Bank in
that copy saves in that browser only." Leave `goldmine.dashboard_url` as it was, and
still write the other `goldmine.*` keys. Publishing can be tried again on the next run.
