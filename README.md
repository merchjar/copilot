# Merch Jar Copilot

The source of truth for the Merch Jar AI Copilot Pack, Segment templates, and skills.

Merch Jar (merchjar.com) is automation for Amazon Sponsored Products PPC. The
Copilot Pack lets any AI coding agent (Claude, ChatGPT via Codex, Cursor, and
more) connect to your live Merch Jar account, run preview queries, and build
automation that shows its work.

## Status

This repo is being set up. Released packs and templates will be published here as
versioned Releases. Until the first release lands, treat this as a work in
progress.

## What lives here

- `copilot-pack/` the Copilot Pack (the AI's operating brain, skills, docs)
- `templates/` validated Segment templates, organized by category
- `skills/` canonical skill sources
- `tools/` build and sync scripts (no secrets, ever)
- `manifest.json` generated catalog of templates and packs

## Getting the pack

Customers should pull released versions, not the `main` branch. The latest
released catalog is always available at:

```
https://github.com/merchjar/copilot/releases/latest/download/manifest.json
```

## License

Proprietary. Use requires an active Merch Jar account. See `LICENSE`. This is not
open source, and redistribution or derivative works outside the Merch Jar service
are not permitted.
