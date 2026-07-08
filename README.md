# Merch Jar Copilot

The source of truth for the Merch Jar AI Copilot Pack, Segment templates, and skills.

Merch Jar (merchjar.com) is automation for Amazon Sponsored Products PPC. The
Copilot Pack lets any AI coding agent (Claude, ChatGPT via Codex, Cursor, and more)
connect to your live Merch Jar account, run preview queries, and build automation
that shows its work.

## What lives here

- `copilot-pack/` the complete Copilot Pack: the AI's operating brain, skills, docs,
  reference, Segment templates, and local API client. This is what you download.
- `copilot-pack/templates/` the validated Segment templates, organized as a library.
- `copilot-pack/skills/` the canonical skill sources.
- `manifest.json` the generated catalog of templates (id, name, path, tags,
  description, last-updated). The Copilot fetches this to list and update templates.
- `tools/` repo build tooling (manifest generator, sync scripts). No secrets, ever.

## Getting the pack

Pull released versions, not the `main` branch. The latest released catalog is always
available at a permanent URL:

```
https://github.com/merchjar/copilot/releases/latest/download/manifest.json
```

Each release also attaches the full pack as a downloadable zip.

## License

Proprietary. Use requires an active Merch Jar account. See `LICENSE`. This is not
open source, and redistribution or derivative works outside the Merch Jar service are
not permitted.
