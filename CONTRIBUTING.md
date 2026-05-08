# Contributing to revxl-marketplace

Thanks for your interest. This is a curated marketplace — contributions go through review to keep quality consistent.

## What we accept

- **Bug fixes** in existing plugins
- **New skills** within an existing superengine
- **New superengines** that follow the conventions in [docs/plugin-conventions.md](docs/plugin-conventions.md)
- **Documentation** improvements
- **CI / tooling** improvements

## What we don't accept (without prior discussion)

- Skills that break the established tone for their target audience
- New superengines for domains already covered (open an issue to discuss merging instead)
- Breaking changes to existing skills' triggers (this breaks client installations)
- Adding non-MIT licensed content

## Process

1. **Open an issue first** for anything beyond a small bug fix. Briefly describe what you want to do.
2. **Fork** the repo.
3. **Create a feature branch**: `feat/<plugin-name>/<short-description>` or `fix/<plugin-name>/<short-description>`.
4. **Build** following the conventions in [docs/plugin-conventions.md](docs/plugin-conventions.md).
5. **Test locally** — install the marketplace from your fork into Claude Code:
   ```
   /plugin marketplace add <your-fork>/revxl-marketplace
   /plugin install <plugin-name>@revxl-marketplace
   ```
6. **Validate** before pushing:
   ```bash
   claude plugin validate plugins/<plugin-name>
   ```
7. **Commit** with a descriptive message.
8. **Push** and open a PR.

## Pull request checklist

- [ ] Plugin folder is fully self-contained (own README, CHANGELOG, LICENSE, plugin.json)
- [ ] All skill descriptions are precise and trigger-rich (see plugin-conventions.md)
- [ ] Tone matches target audience (default: non-technical, plain English, one-step-at-a-time)
- [ ] Plugin's CHANGELOG.md updated with a new version entry
- [ ] Marketplace's CHANGELOG.md updated if a new plugin was added
- [ ] No PII or credentials committed
- [ ] CI validation passes (workflow runs automatically)

## Code of conduct

Be useful, be kind, be honest about what your skill can and can't do.

## Questions

Open an issue or email [joe@engineforimpact.com](mailto:joe@engineforimpact.com).
