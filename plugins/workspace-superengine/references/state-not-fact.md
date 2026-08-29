# State is not a rule — never transcribe a fact that expires

Read this at 2b, when copying `## Verify before building` into the prompt. It is the one exception to the verbatim rule, and the evidence for why it exists. **Never dump this file at the user.**

---


**A rule stays true next month. A fact about one moment does not.** "Never `sed -i` in this repo" is a rule ... it will be just as true in November. `b38ef37` is state ... it is a claim about which commit was at the tip of a branch at one instant, and it goes stale the next time anybody commits.

**So: a commit hash or a pinned version string is never transcribed into the prompt as fact.** When a rail line contains one, keep the rail, and emit the command that re-derives the current value in place of the literal:

- Rail says `build from b38ef37` → prompt carries `build from the current tip ... re-derive it: git -C <repo> log --oneline -1`.
- Rail says `pinned at graphify 0.9.42` → prompt carries `confirm the installed version before relying on it: graphify --version`.

**Why this is worth an exception to a verbatim rule.** Yesterday this workspace's handoff named `b38ef37` when the real value was `b0b06e0`, one commit later. And in another workspace three consecutive generated prompts carried 4, then 6, then 9 hardcoded hashes ... each one built from a handoff that already contained the previous prompt's. One of them named a version that had been rolled back 81 seconds after it was written, and told the next session not to re-verify it. Copying a rail faithfully is correct. Copying a timestamped fact faithfully is how a wrong value gets laundered into an instruction.

#### The same rule for things that are claimed to exist

**The prompt may not assert that a binary, a connector, an MCP server or a service EXISTS unless it was probed at generation time.** Existence is state, exactly like a commit hash.

- **Probed and present** → say so, and say how you know: `ghl-cli is on PATH (checked at generation time).`
- **Not probed, or probe unavailable** → hand the check forward instead of the claim: `The handoff refers to ghl-cli. Confirm it is installed before building on it ... it was not probed when this prompt was written.`

A prior cold read caught a generated prompt stating that "the work runs the locally-installed ghl-cli" when that binary was not on PATH at all. The claim came from a string match on handoff prose, it read as authoritative, and nothing in the prompt marked it as unchecked.
